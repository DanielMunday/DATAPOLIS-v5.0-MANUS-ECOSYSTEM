"""
DATAPOLIS v3.0 - Servicio de Indicadores Económicos (IE)
Integración con Banco Central de Chile + Predicciones ARIMA/SARIMA
"""

import httpx
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
import json
import logging
from dataclasses import dataclass
from enum import Enum

from ..config import settings, SERIES_BCCH
from ..database import IndicadorEconomico, PrediccionIndicador

logger = logging.getLogger(__name__)


# =====================================================
# CONSTANTES Y CONFIGURACIÓN
# =====================================================

class SerieIndicador(str, Enum):
    """Series disponibles del Banco Central"""
    UF = "UF"
    UTM = "UTM"
    IPC = "IPC"
    DOLAR_OBSERVADO = "DOLAR_OBSERVADO"
    TASA_POLITICA_MONETARIA = "TPM"
    IMACEC = "IMACEC"


@dataclass
class IndicadorResponse:
    """Respuesta de indicador económico"""
    codigo: str
    nombre: str
    valor: Decimal
    fecha: date
    unidad: str
    variacion_diaria: Optional[float] = None
    variacion_mensual: Optional[float] = None
    variacion_anual: Optional[float] = None


@dataclass
class PrediccionResponse:
    """Respuesta de predicción"""
    codigo: str
    fecha_prediccion: date
    horizonte_dias: int
    valor_predicho: Decimal
    intervalo_inferior: Decimal
    intervalo_superior: Decimal
    confianza_pct: float
    modelo: str


# =====================================================
# CLIENTE BANCO CENTRAL DE CHILE
# =====================================================

class BCChClient:
    """Cliente para API del Banco Central de Chile"""
    
    BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    
    def __init__(self, user: Optional[str] = None, password: Optional[str] = None):
        self.user = user or settings.BCCH_API_USER
        self.password = password or settings.BCCH_API_PASSWORD
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Realizar petición a la API del BCCh"""
        params.update({
            "user": self.user,
            "pass": self.password,
            "format": "json"
        })
        
        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error en petición BCCh: {e}")
            raise
    
    async def get_series(
        self,
        series_codes: List[str],
        fecha_inicio: date,
        fecha_fin: date
    ) -> Dict[str, List[Dict]]:
        """Obtener múltiples series de datos"""
        
        params = {
            "function": "GetSeries",
            "timeseries": ",".join(series_codes),
            "firstdate": fecha_inicio.strftime("%Y-%m-%d"),
            "lastdate": fecha_fin.strftime("%Y-%m-%d")
        }
        
        data = await self._request(params)
        
        # Parsear respuesta
        result = {}
        if "Series" in data:
            for serie in data["Series"]["Serie"]:
                codigo = serie.get("seriesId", "UNKNOWN")
                observaciones = serie.get("Obs", [])
                
                if not isinstance(observaciones, list):
                    observaciones = [observaciones]
                
                result[codigo] = [
                    {
                        "fecha": datetime.strptime(obs["indexDateString"], "%d-%m-%Y").date(),
                        "valor": Decimal(str(obs["value"]).replace(",", "."))
                    }
                    for obs in observaciones
                    if obs.get("value") is not None
                ]
        
        return result
    
    async def get_uf(self, fecha: Optional[date] = None) -> Decimal:
        """Obtener valor UF para una fecha"""
        fecha = fecha or date.today()
        fecha_inicio = fecha - timedelta(days=7)  # Buffer por feriados
        
        data = await self.get_series(
            [SERIES_BCCH["UF"]],
            fecha_inicio,
            fecha
        )
        
        if SERIES_BCCH["UF"] in data and data[SERIES_BCCH["UF"]]:
            # Obtener el valor más reciente
            valores = sorted(data[SERIES_BCCH["UF"]], key=lambda x: x["fecha"], reverse=True)
            return valores[0]["valor"]
        
        # Fallback a valor por defecto
        logger.warning(f"No se pudo obtener UF para {fecha}, usando valor por defecto")
        return Decimal(str(settings.DEFAULT_UF_VALUE))
    
    async def get_utm(self, fecha: Optional[date] = None) -> Decimal:
        """Obtener valor UTM para un mes"""
        fecha = fecha or date.today()
        # UTM es mensual, obtener primer día del mes
        fecha_inicio = fecha.replace(day=1)
        fecha_fin = fecha
        
        data = await self.get_series(
            [SERIES_BCCH["UTM"]],
            fecha_inicio,
            fecha_fin
        )
        
        if SERIES_BCCH["UTM"] in data and data[SERIES_BCCH["UTM"]]:
            return data[SERIES_BCCH["UTM"]][0]["valor"]
        
        return Decimal(str(settings.DEFAULT_UTM_VALUE))
    
    async def get_dolar(self, fecha: Optional[date] = None) -> Decimal:
        """Obtener dólar observado"""
        fecha = fecha or date.today()
        fecha_inicio = fecha - timedelta(days=7)
        
        data = await self.get_series(
            [SERIES_BCCH["DOLAR_OBSERVADO"]],
            fecha_inicio,
            fecha
        )
        
        if SERIES_BCCH["DOLAR_OBSERVADO"] in data and data[SERIES_BCCH["DOLAR_OBSERVADO"]]:
            valores = sorted(data[SERIES_BCCH["DOLAR_OBSERVADO"]], key=lambda x: x["fecha"], reverse=True)
            return valores[0]["valor"]
        
        raise ValueError("No se pudo obtener el dólar observado")


# =====================================================
# SERVICIO DE INDICADORES
# =====================================================

class IndicadoresService:
    """Servicio principal de indicadores económicos"""
    
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.bcch = BCChClient()
    
    async def close(self):
        await self.bcch.close()
    
    # -------------------------------------------------
    # CACHE
    # -------------------------------------------------
    
    async def _get_cache(self, key: str) -> Optional[Dict]:
        """Obtener valor de cache Redis"""
        if not self.redis:
            return None
        
        try:
            data = await self.redis.get(f"indicador:{key}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Error leyendo cache: {e}")
        
        return None
    
    async def _set_cache(self, key: str, value: Dict, ttl: int = 3600):
        """Guardar valor en cache Redis"""
        if not self.redis:
            return
        
        try:
            await self.redis.setex(
                f"indicador:{key}",
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.warning(f"Error escribiendo cache: {e}")
    
    # -------------------------------------------------
    # OBTENCIÓN DE INDICADORES
    # -------------------------------------------------
    
    async def get_uf(self, fecha: Optional[date] = None) -> IndicadorResponse:
        """Obtener UF con cache"""
        fecha = fecha or date.today()
        cache_key = f"UF:{fecha.isoformat()}"
        
        # Intentar cache
        cached = await self._get_cache(cache_key)
        if cached:
            return IndicadorResponse(**cached)
        
        # Obtener de BCCh
        valor = await self.bcch.get_uf(fecha)
        
        # Calcular variaciones
        variacion_diaria = await self._calcular_variacion(SerieIndicador.UF, fecha, 1)
        variacion_mensual = await self._calcular_variacion(SerieIndicador.UF, fecha, 30)
        variacion_anual = await self._calcular_variacion(SerieIndicador.UF, fecha, 365)
        
        response = IndicadorResponse(
            codigo="UF",
            nombre="Unidad de Fomento",
            valor=valor,
            fecha=fecha,
            unidad="CLP",
            variacion_diaria=variacion_diaria,
            variacion_mensual=variacion_mensual,
            variacion_anual=variacion_anual
        )
        
        # Guardar en cache
        await self._set_cache(cache_key, response.__dict__)
        
        # Guardar en BD
        await self._save_indicador(response)
        
        return response
    
    async def get_utm(self, fecha: Optional[date] = None) -> IndicadorResponse:
        """Obtener UTM con cache"""
        fecha = fecha or date.today()
        cache_key = f"UTM:{fecha.strftime('%Y-%m')}"
        
        cached = await self._get_cache(cache_key)
        if cached:
            return IndicadorResponse(**cached)
        
        valor = await self.bcch.get_utm(fecha)
        
        response = IndicadorResponse(
            codigo="UTM",
            nombre="Unidad Tributaria Mensual",
            valor=valor,
            fecha=fecha,
            unidad="CLP"
        )
        
        await self._set_cache(cache_key, response.__dict__, ttl=86400)  # 24h
        await self._save_indicador(response)
        
        return response
    
    async def get_dolar(self, fecha: Optional[date] = None) -> IndicadorResponse:
        """Obtener dólar observado"""
        fecha = fecha or date.today()
        cache_key = f"DOLAR:{fecha.isoformat()}"
        
        cached = await self._get_cache(cache_key)
        if cached:
            return IndicadorResponse(**cached)
        
        valor = await self.bcch.get_dolar(fecha)
        variacion_diaria = await self._calcular_variacion(SerieIndicador.DOLAR_OBSERVADO, fecha, 1)
        
        response = IndicadorResponse(
            codigo="DOLAR",
            nombre="Dólar Observado",
            valor=valor,
            fecha=fecha,
            unidad="CLP/USD",
            variacion_diaria=variacion_diaria
        )
        
        await self._set_cache(cache_key, response.__dict__)
        await self._save_indicador(response)
        
        return response
    
    async def get_all_current(self) -> Dict[str, IndicadorResponse]:
        """Obtener todos los indicadores actuales"""
        return {
            "UF": await self.get_uf(),
            "UTM": await self.get_utm(),
            "DOLAR": await self.get_dolar()
        }
    
    # -------------------------------------------------
    # HISTÓRICOS
    # -------------------------------------------------
    
    async def get_historico(
        self,
        codigo: str,
        fecha_inicio: date,
        fecha_fin: date
    ) -> List[Dict[str, Any]]:
        """Obtener serie histórica de un indicador"""
        
        # Buscar en BD primero
        stmt = select(IndicadorEconomico).where(
            and_(
                IndicadorEconomico.codigo_serie == codigo,
                IndicadorEconomico.fecha >= fecha_inicio,
                IndicadorEconomico.fecha <= fecha_fin
            )
        ).order_by(IndicadorEconomico.fecha)
        
        result = await self.db.execute(stmt)
        registros = result.scalars().all()
        
        if registros:
            return [
                {
                    "fecha": r.fecha,
                    "valor": float(r.valor),
                    "variacion_diaria": r.variacion_diaria
                }
                for r in registros
            ]
        
        # Si no hay en BD, obtener de BCCh y guardar
        series_code = SERIES_BCCH.get(codigo)
        if not series_code:
            raise ValueError(f"Serie no reconocida: {codigo}")
        
        data = await self.bcch.get_series([series_code], fecha_inicio, fecha_fin)
        
        if series_code in data:
            for item in data[series_code]:
                await self._save_indicador(IndicadorResponse(
                    codigo=codigo,
                    nombre=codigo,
                    valor=item["valor"],
                    fecha=item["fecha"],
                    unidad="CLP"
                ))
            
            return [
                {"fecha": item["fecha"], "valor": float(item["valor"])}
                for item in data[series_code]
            ]
        
        return []
    
    # -------------------------------------------------
    # PREDICCIONES ARIMA/SARIMA
    # -------------------------------------------------
    
    async def predecir(
        self,
        codigo: str,
        horizonte_dias: int = 30,
        intervalo_confianza: float = 0.95
    ) -> List[PrediccionResponse]:
        """Generar predicciones SARIMA para un indicador"""
        
        logger.info(f"Generando predicción {codigo} para {horizonte_dias} días")
        
        # Obtener datos históricos (mínimo 2 años)
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=730)
        
        historico = await self.get_historico(codigo, fecha_inicio, fecha_fin)
        
        if len(historico) < 60:
            raise ValueError(f"Datos insuficientes para predicción: {len(historico)} registros")
        
        # Convertir a DataFrame
        df = pd.DataFrame(historico)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.set_index('fecha')
        df = df.sort_index()
        
        # Rellenar valores faltantes (fines de semana/feriados)
        df = df.asfreq('D', method='ffill')
        
        # Entrenar modelo SARIMA
        try:
            # Parámetros para UF/indicadores diarios
            if codigo in ["UF", "DOLAR"]:
                # ARIMA simple para series diarias
                model = ARIMA(
                    df['valor'],
                    order=(5, 1, 2)
                )
            else:
                # SARIMA para series con estacionalidad mensual
                model = SARIMAX(
                    df['valor'],
                    order=settings.ARIMA_ORDER,
                    seasonal_order=settings.ARIMA_SEASONAL_ORDER
                )
            
            fitted = model.fit(disp=False)
            
            # Generar predicciones
            forecast = fitted.get_forecast(steps=horizonte_dias)
            pred_mean = forecast.predicted_mean
            pred_ci = forecast.conf_int(alpha=1 - intervalo_confianza)
            
            # Calcular métricas
            residuals = fitted.resid
            mape = np.mean(np.abs(residuals / df['valor'].iloc[-len(residuals):])) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            predicciones = []
            for i in range(horizonte_dias):
                fecha_pred = fecha_fin + timedelta(days=i + 1)
                
                pred = PrediccionResponse(
                    codigo=codigo,
                    fecha_prediccion=fecha_pred,
                    horizonte_dias=i + 1,
                    valor_predicho=Decimal(str(round(pred_mean.iloc[i], 2))),
                    intervalo_inferior=Decimal(str(round(pred_ci.iloc[i, 0], 2))),
                    intervalo_superior=Decimal(str(round(pred_ci.iloc[i, 1], 2))),
                    confianza_pct=intervalo_confianza * 100,
                    modelo="SARIMA" if codigo not in ["UF", "DOLAR"] else "ARIMA"
                )
                predicciones.append(pred)
                
                # Guardar en BD
                await self._save_prediccion(pred, mape, rmse, fitted.params.tolist())
            
            return predicciones
            
        except Exception as e:
            logger.error(f"Error en predicción ARIMA: {e}")
            raise
    
    # -------------------------------------------------
    # CONVERSIONES
    # -------------------------------------------------
    
    async def convertir_uf_a_clp(self, monto_uf: Decimal, fecha: Optional[date] = None) -> Decimal:
        """Convertir UF a CLP"""
        uf = await self.get_uf(fecha)
        return monto_uf * uf.valor
    
    async def convertir_clp_a_uf(self, monto_clp: Decimal, fecha: Optional[date] = None) -> Decimal:
        """Convertir CLP a UF"""
        uf = await self.get_uf(fecha)
        return monto_clp / uf.valor
    
    async def convertir_usd_a_clp(self, monto_usd: Decimal, fecha: Optional[date] = None) -> Decimal:
        """Convertir USD a CLP"""
        dolar = await self.get_dolar(fecha)
        return monto_usd * dolar.valor
    
    async def convertir_uf_a_usd(self, monto_uf: Decimal, fecha: Optional[date] = None) -> Decimal:
        """Convertir UF a USD"""
        uf = await self.get_uf(fecha)
        dolar = await self.get_dolar(fecha)
        clp = monto_uf * uf.valor
        return clp / dolar.valor
    
    # -------------------------------------------------
    # HELPERS PRIVADOS
    # -------------------------------------------------
    
    async def _calcular_variacion(
        self,
        codigo: SerieIndicador,
        fecha: date,
        dias: int
    ) -> Optional[float]:
        """Calcular variación porcentual"""
        fecha_anterior = fecha - timedelta(days=dias)
        
        stmt = select(IndicadorEconomico.valor).where(
            and_(
                IndicadorEconomico.codigo_serie == codigo.value,
                IndicadorEconomico.fecha <= fecha_anterior
            )
        ).order_by(IndicadorEconomico.fecha.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        valor_anterior = result.scalar()
        
        if valor_anterior:
            stmt_actual = select(IndicadorEconomico.valor).where(
                and_(
                    IndicadorEconomico.codigo_serie == codigo.value,
                    IndicadorEconomico.fecha <= fecha
                )
            ).order_by(IndicadorEconomico.fecha.desc()).limit(1)
            
            result_actual = await self.db.execute(stmt_actual)
            valor_actual = result_actual.scalar()
            
            if valor_actual and valor_anterior:
                return float((valor_actual - valor_anterior) / valor_anterior * 100)
        
        return None
    
    async def _save_indicador(self, indicador: IndicadorResponse):
        """Guardar indicador en BD"""
        try:
            registro = IndicadorEconomico(
                fecha=datetime.combine(indicador.fecha, datetime.min.time()),
                codigo_serie=indicador.codigo,
                valor=indicador.valor,
                fuente="BCCH",
                unidad=indicador.unidad,
                variacion_diaria=indicador.variacion_diaria,
                variacion_mensual=indicador.variacion_mensual,
                variacion_anual=indicador.variacion_anual
            )
            self.db.add(registro)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning(f"Error guardando indicador: {e}")
    
    async def _save_prediccion(
        self,
        pred: PrediccionResponse,
        mape: float,
        rmse: float,
        parametros: List
    ):
        """Guardar predicción en BD"""
        try:
            registro = PrediccionIndicador(
                codigo_serie=pred.codigo,
                fecha_prediccion=pred.fecha_prediccion,
                horizonte_dias=pred.horizonte_dias,
                valor_predicho=pred.valor_predicho,
                intervalo_confianza_inferior=pred.intervalo_inferior,
                intervalo_confianza_superior=pred.intervalo_superior,
                modelo=pred.modelo,
                mape=mape,
                rmse=rmse,
                parametros_modelo={"params": parametros}
            )
            self.db.add(registro)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.warning(f"Error guardando predicción: {e}")


# =====================================================
# FUNCIONES DE UTILIDAD
# =====================================================

def calcular_reajuste_uf(
    monto_original: Decimal,
    uf_original: Decimal,
    uf_actual: Decimal
) -> Decimal:
    """Calcular monto reajustado por UF"""
    return monto_original * (uf_actual / uf_original)


def calcular_interes_mora(
    monto_uf: Decimal,
    dias_mora: int,
    tasa_anual: float = 0.12  # 12% anual por defecto
) -> Decimal:
    """Calcular interés por mora"""
    tasa_diaria = tasa_anual / 365
    return monto_uf * Decimal(str(tasa_diaria)) * Decimal(str(dias_mora))


def convertir_uta_a_uf(uta: Decimal, utm: Decimal, uf: Decimal) -> Decimal:
    """Convertir UTA (12 UTM) a UF"""
    uta_clp = uta * (utm * 12)
    return uta_clp / uf
