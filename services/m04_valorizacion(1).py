"""
DATAPOLIS v3.0 - Servicio de Valorización (M04)
Implementación IVS 2022 (International Valuation Standards)
Métodos: Comparación, Costo, Ingreso (DCF), Residual, Hedonic ML
"""

import numpy as np
import pandas as pd
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_SetSRID, ST_MakePoint
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error, r2_score
import shap
import joblib
import logging
import json

from ..config import settings
from ..database import (
    Propiedad, Valorizacion, Comparable, TipoPropiedad,
    MetodoValorizacion
)
from .ie_indicadores import IndicadoresService

logger = logging.getLogger(__name__)


# =====================================================
# CONSTANTES DE VALORIZACIÓN
# =====================================================

# Tasas de depreciación por tipo de construcción
TASAS_DEPRECIACION = {
    "hormigon_armado": 0.010,  # 1% anual
    "albañileria": 0.015,      # 1.5% anual
    "madera": 0.020,           # 2% anual
    "mixto": 0.0175,           # 1.75% anual
}

# Vida útil estimada
VIDA_UTIL_ANOS = {
    "hormigon_armado": 80,
    "albañileria": 60,
    "madera": 40,
    "mixto": 50,
}

# Costos de construcción por m2 (UF) - Chile 2024
COSTOS_CONSTRUCCION_UF_M2 = {
    TipoPropiedad.DEPARTAMENTO: {
        "economico": 18,
        "medio": 25,
        "alto": 35,
        "premium": 50
    },
    TipoPropiedad.CASA: {
        "economico": 15,
        "medio": 22,
        "alto": 32,
        "premium": 45
    },
    TipoPropiedad.OFICINA: {
        "economico": 20,
        "medio": 28,
        "alto": 40,
        "premium": 55
    },
    TipoPropiedad.LOCAL_COMERCIAL: {
        "economico": 16,
        "medio": 24,
        "alto": 35,
        "premium": 48
    }
}

# Cap rates por zona y tipo
CAP_RATES_REFERENCIA = {
    "santiago_oriente": {
        "residencial": 0.045,  # 4.5%
        "oficinas": 0.055,     # 5.5%
        "comercial": 0.065    # 6.5%
    },
    "santiago_centro": {
        "residencial": 0.055,
        "oficinas": 0.060,
        "comercial": 0.070
    },
    "santiago_poniente": {
        "residencial": 0.060,
        "oficinas": 0.065,
        "comercial": 0.075
    },
    "regiones": {
        "residencial": 0.065,
        "oficinas": 0.070,
        "comercial": 0.080
    }
}


# =====================================================
# DATA CLASSES
# =====================================================

@dataclass
class ComparableAjustado:
    """Comparable con ajustes aplicados"""
    id: str
    direccion: str
    distancia_m: float
    precio_uf: Decimal
    precio_uf_m2: Decimal
    superficie_m2: float
    fecha_transaccion: date
    
    # Ajustes aplicados
    ajuste_ubicacion: float = 0.0
    ajuste_superficie: float = 0.0
    ajuste_antiguedad: float = 0.0
    ajuste_tiempo: float = 0.0
    ajuste_caracteristicas: float = 0.0
    
    @property
    def precio_ajustado_uf_m2(self) -> Decimal:
        factor_total = 1 + self.ajuste_ubicacion + self.ajuste_superficie + \
                      self.ajuste_antiguedad + self.ajuste_tiempo + self.ajuste_caracteristicas
        return self.precio_uf_m2 * Decimal(str(factor_total))
    
    @property
    def ajuste_total(self) -> float:
        return self.ajuste_ubicacion + self.ajuste_superficie + \
               self.ajuste_antiguedad + self.ajuste_tiempo + self.ajuste_caracteristicas


@dataclass
class ResultadoValorizacion:
    """Resultado completo de valorización"""
    propiedad_id: str
    fecha_valoracion: date
    
    # Valores por método
    valor_comparacion_uf: Optional[Decimal] = None
    valor_costo_uf: Optional[Decimal] = None
    valor_ingreso_uf: Optional[Decimal] = None
    valor_residual_uf: Optional[Decimal] = None
    valor_hedonic_uf: Optional[Decimal] = None
    
    # Valor final reconciliado
    valor_final_uf: Decimal = Decimal("0")
    metodo_principal: MetodoValorizacion = MetodoValorizacion.COMPARACION
    
    # Rango
    valor_minimo_uf: Decimal = Decimal("0")
    valor_maximo_uf: Decimal = Decimal("0")
    
    # Ponderaciones
    ponderaciones: Dict[str, float] = field(default_factory=dict)
    
    # Confianza
    confianza_pct: float = 0.0
    
    # Detalles
    comparables_usados: List[ComparableAjustado] = field(default_factory=list)
    detalle_costo: Dict[str, Any] = field(default_factory=dict)
    detalle_dcf: Dict[str, Any] = field(default_factory=dict)
    shap_values: Dict[str, float] = field(default_factory=dict)


# =====================================================
# SERVICIO DE VALORIZACIÓN
# =====================================================

class ValorizacionService:
    """Servicio principal de valorización IVS 2022"""
    
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.indicadores = IndicadoresService(db, redis_client)
        self.modelo_hedonic: Optional[xgb.XGBRegressor] = None
        self.shap_explainer: Optional[shap.TreeExplainer] = None
    
    async def close(self):
        await self.indicadores.close()
    
    # =====================================================
    # MÉTODO PRINCIPAL DE VALORIZACIÓN
    # =====================================================
    
    async def valorizar(
        self,
        propiedad_id: str,
        proposito: str = "mercado",
        metodos: Optional[List[str]] = None,
        fecha_valoracion: Optional[date] = None
    ) -> ResultadoValorizacion:
        """
        Valorización completa de una propiedad usando múltiples métodos
        
        Args:
            propiedad_id: ID de la propiedad
            proposito: Propósito (mercado, liquidacion, inversion, asegurable)
            metodos: Lista de métodos a aplicar (None = todos)
            fecha_valoracion: Fecha de valoración (None = hoy)
        
        Returns:
            ResultadoValorizacion con todos los valores y reconciliación
        """
        fecha_valoracion = fecha_valoracion or date.today()
        metodos = metodos or ["comparacion", "costo", "ingreso", "hedonic"]
        
        logger.info(f"Iniciando valorización de propiedad {propiedad_id}")
        
        # Obtener propiedad
        propiedad = await self._get_propiedad(propiedad_id)
        if not propiedad:
            raise ValueError(f"Propiedad no encontrada: {propiedad_id}")
        
        resultado = ResultadoValorizacion(
            propiedad_id=propiedad_id,
            fecha_valoracion=fecha_valoracion
        )
        
        # Aplicar cada método
        if "comparacion" in metodos:
            resultado.valor_comparacion_uf, resultado.comparables_usados = \
                await self.metodo_comparacion(propiedad, fecha_valoracion)
        
        if "costo" in metodos:
            resultado.valor_costo_uf, resultado.detalle_costo = \
                await self.metodo_costo(propiedad, fecha_valoracion)
        
        if "ingreso" in metodos and self._es_apto_para_renta(propiedad):
            resultado.valor_ingreso_uf, resultado.detalle_dcf = \
                await self.metodo_ingreso_dcf(propiedad, fecha_valoracion)
        
        if "hedonic" in metodos:
            resultado.valor_hedonic_uf, resultado.shap_values = \
                await self.metodo_hedonic_ml(propiedad, fecha_valoracion)
        
        # Reconciliación
        resultado = await self._reconciliar(resultado, propiedad, proposito)
        
        # Guardar en BD
        await self._save_valorizacion(resultado, propiedad)
        
        logger.info(f"Valorización completada: {resultado.valor_final_uf} UF")
        
        return resultado
    
    # =====================================================
    # MÉTODO DE COMPARACIÓN (Market Approach)
    # =====================================================
    
    async def metodo_comparacion(
        self,
        propiedad: Propiedad,
        fecha_valoracion: date,
        radio_busqueda_m: int = 1000,
        max_comparables: int = 10,
        meses_antiguedad: int = 12
    ) -> Tuple[Optional[Decimal], List[ComparableAjustado]]:
        """
        Método de comparación de mercado
        Busca propiedades similares vendidas recientemente y aplica ajustes
        """
        logger.info(f"Aplicando método de comparación para {propiedad.id}")
        
        # Buscar comparables cercanos
        fecha_minima = fecha_valoracion - timedelta(days=meses_antiguedad * 30)
        
        stmt = select(Comparable).where(
            and_(
                Comparable.tipo == propiedad.tipo,
                Comparable.comuna == propiedad.comuna,
                Comparable.fecha_transaccion >= fecha_minima,
                Comparable.fecha_transaccion <= fecha_valoracion
            )
        )
        
        # Si hay coordenadas, filtrar por distancia
        if propiedad.latitud and propiedad.longitud:
            punto_propiedad = ST_SetSRID(
                ST_MakePoint(propiedad.longitud, propiedad.latitud),
                4326
            )
            stmt = stmt.where(
                ST_DWithin(
                    Comparable.geometria,
                    punto_propiedad,
                    radio_busqueda_m
                )
            ).add_columns(
                ST_Distance(Comparable.geometria, punto_propiedad).label('distancia')
            )
        
        stmt = stmt.limit(max_comparables * 2)  # Obtener extras para filtrar
        
        result = await self.db.execute(stmt)
        comparables_raw = result.all()
        
        if not comparables_raw:
            logger.warning("No se encontraron comparables")
            return None, []
        
        # Procesar y ajustar comparables
        comparables_ajustados = []
        
        for row in comparables_raw:
            if hasattr(row, 'distancia'):
                comparable, distancia = row.Comparable, row.distancia
            else:
                comparable = row
                distancia = 500  # Valor por defecto si no hay geometría
            
            ajustado = await self._ajustar_comparable(
                comparable, propiedad, distancia, fecha_valoracion
            )
            
            # Filtrar ajustes extremos (>30% total)
            if abs(ajustado.ajuste_total) <= 0.30:
                comparables_ajustados.append(ajustado)
        
        if not comparables_ajustados:
            return None, []
        
        # Ordenar por relevancia (menor ajuste total)
        comparables_ajustados.sort(key=lambda x: abs(x.ajuste_total))
        comparables_ajustados = comparables_ajustados[:max_comparables]
        
        # Calcular valor por ponderación inversa al ajuste
        pesos = []
        valores = []
        
        for comp in comparables_ajustados:
            peso = 1 / (1 + abs(comp.ajuste_total))
            pesos.append(peso)
            valores.append(float(comp.precio_ajustado_uf_m2))
        
        # Normalizar pesos
        suma_pesos = sum(pesos)
        pesos_norm = [p / suma_pesos for p in pesos]
        
        # Valor ponderado por m2
        valor_uf_m2 = sum(v * p for v, p in zip(valores, pesos_norm))
        
        # Valor total
        valor_total = Decimal(str(valor_uf_m2)) * Decimal(str(propiedad.superficie_construida_m2))
        
        return valor_total.quantize(Decimal("0.01")), comparables_ajustados
    
    async def _ajustar_comparable(
        self,
        comparable: Comparable,
        propiedad: Propiedad,
        distancia: float,
        fecha_valoracion: date
    ) -> ComparableAjustado:
        """Aplicar ajustes a un comparable"""
        
        ajustado = ComparableAjustado(
            id=str(comparable.id),
            direccion=comparable.direccion,
            distancia_m=distancia,
            precio_uf=comparable.precio_uf,
            precio_uf_m2=comparable.precio_uf_m2,
            superficie_m2=comparable.superficie_m2,
            fecha_transaccion=comparable.fecha_transaccion
        )
        
        # Ajuste por ubicación (distancia)
        # -0.5% por cada 100m de distancia
        ajustado.ajuste_ubicacion = -0.005 * (distancia / 100)
        
        # Ajuste por superficie
        # Diferencia % en superficie, factor 0.5
        diff_superficie = (propiedad.superficie_construida_m2 - comparable.superficie_m2) / comparable.superficie_m2
        ajustado.ajuste_superficie = -diff_superficie * 0.5  # Negativo porque más m2 = menor precio/m2
        
        # Ajuste por antigüedad
        if comparable.ano_construccion and propiedad.ano_construccion:
            diff_anos = propiedad.ano_construccion - comparable.ano_construccion
            ajustado.ajuste_antiguedad = diff_anos * 0.01  # 1% por año
        
        # Ajuste por tiempo de transacción
        # +0.3% por mes (inflación inmobiliaria promedio)
        meses_diferencia = (fecha_valoracion - comparable.fecha_transaccion).days / 30
        ajustado.ajuste_tiempo = meses_diferencia * 0.003
        
        # Ajuste por características (dormitorios, baños)
        ajuste_caract = 0.0
        if comparable.dormitorios and propiedad.dormitorios:
            diff_dorm = propiedad.dormitorios - comparable.dormitorios
            ajuste_caract += diff_dorm * 0.02  # 2% por dormitorio
        
        if comparable.banos and propiedad.banos:
            diff_banos = propiedad.banos - comparable.banos
            ajuste_caract += diff_banos * 0.015  # 1.5% por baño
        
        ajustado.ajuste_caracteristicas = ajuste_caract
        
        return ajustado
    
    # =====================================================
    # MÉTODO DEL COSTO (Cost Approach)
    # =====================================================
    
    async def metodo_costo(
        self,
        propiedad: Propiedad,
        fecha_valoracion: date
    ) -> Tuple[Optional[Decimal], Dict[str, Any]]:
        """
        Método del costo de reposición depreciado
        Valor = Terreno + (Costo Construcción - Depreciación)
        """
        logger.info(f"Aplicando método del costo para {propiedad.id}")
        
        detalle = {}
        
        # 1. Valor del terreno
        valor_terreno_uf = await self._estimar_valor_terreno(propiedad)
        detalle["valor_terreno_uf"] = float(valor_terreno_uf)
        
        # 2. Determinar estándar de construcción
        estandar = self._determinar_estandar_construccion(propiedad)
        detalle["estandar_construccion"] = estandar
        
        # 3. Costo de reposición nuevo
        tipo_prop = propiedad.tipo if propiedad.tipo in COSTOS_CONSTRUCCION_UF_M2 else TipoPropiedad.DEPARTAMENTO
        costo_m2 = COSTOS_CONSTRUCCION_UF_M2[tipo_prop][estandar]
        costo_reposicion = Decimal(str(costo_m2)) * Decimal(str(propiedad.superficie_construida_m2))
        detalle["costo_m2_uf"] = costo_m2
        detalle["costo_reposicion_nuevo_uf"] = float(costo_reposicion)
        
        # 4. Calcular depreciación
        if propiedad.ano_construccion:
            antiguedad = fecha_valoracion.year - propiedad.ano_construccion
            vida_util = VIDA_UTIL_ANOS.get("hormigon_armado", 60)
            
            # Método de línea recta con depreciación máxima 80%
            depreciacion_pct = min(antiguedad / vida_util, 0.80)
            depreciacion_uf = costo_reposicion * Decimal(str(depreciacion_pct))
        else:
            depreciacion_pct = 0.20  # Asumir 20% si no hay datos
            depreciacion_uf = costo_reposicion * Decimal("0.20")
        
        detalle["antiguedad_anos"] = antiguedad if propiedad.ano_construccion else "N/D"
        detalle["depreciacion_pct"] = float(depreciacion_pct)
        detalle["depreciacion_uf"] = float(depreciacion_uf)
        
        # 5. Valor de las mejoras depreciado
        valor_mejoras = costo_reposicion - depreciacion_uf
        detalle["valor_mejoras_depreciado_uf"] = float(valor_mejoras)
        
        # 6. Valor total
        valor_total = valor_terreno_uf + valor_mejoras
        detalle["valor_total_uf"] = float(valor_total)
        
        return valor_total.quantize(Decimal("0.01")), detalle
    
    async def _estimar_valor_terreno(self, propiedad: Propiedad) -> Decimal:
        """Estimar valor del terreno basado en transacciones de la zona"""
        
        if not propiedad.superficie_terreno_m2:
            # Si es departamento, estimar según prorrateo típico
            if propiedad.tipo == TipoPropiedad.DEPARTAMENTO:
                # Prorrateo típico: 15-20% de la superficie construida
                superficie_terreno = propiedad.superficie_construida_m2 * 0.17
            else:
                superficie_terreno = propiedad.superficie_construida_m2 * 1.5  # Asumir ratio
        else:
            superficie_terreno = propiedad.superficie_terreno_m2
        
        # Buscar precio de suelo en la zona
        from ..database import TransaccionSuelo
        
        stmt = select(func.avg(TransaccionSuelo.precio_uf_m2)).where(
            and_(
                TransaccionSuelo.comuna == propiedad.comuna,
                TransaccionSuelo.fecha_transaccion >= date.today() - timedelta(days=365)
            )
        )
        
        result = await self.db.execute(stmt)
        precio_m2 = result.scalar()
        
        if not precio_m2:
            # Valores de referencia por comuna (simplificado)
            precios_referencia = {
                "Las Condes": 50,
                "Providencia": 55,
                "Vitacura": 60,
                "Lo Barnechea": 45,
                "Ñuñoa": 40,
                "Santiago": 35,
                "La Reina": 42,
                "Maipú": 15,
                "Puente Alto": 12,
                "La Florida": 18
            }
            precio_m2 = precios_referencia.get(propiedad.comuna, 20)
        
        return Decimal(str(precio_m2)) * Decimal(str(superficie_terreno))
    
    def _determinar_estandar_construccion(self, propiedad: Propiedad) -> str:
        """Determinar estándar de construcción basado en características"""
        
        # Heurística basada en comuna y características
        comunas_premium = ["Vitacura", "Las Condes", "Lo Barnechea"]
        comunas_alto = ["Providencia", "La Reina", "Ñuñoa"]
        
        if propiedad.comuna in comunas_premium:
            base = "alto"
        elif propiedad.comuna in comunas_alto:
            base = "medio"
        else:
            base = "economico"
        
        # Ajustar por m2/dormitorio
        if propiedad.dormitorios and propiedad.dormitorios > 0:
            m2_por_dorm = propiedad.superficie_construida_m2 / propiedad.dormitorios
            if m2_por_dorm > 40:
                base = "alto" if base == "medio" else ("premium" if base == "alto" else base)
            elif m2_por_dorm < 20:
                base = "economico" if base == "medio" else base
        
        return base
    
    # =====================================================
    # MÉTODO DEL INGRESO (Income Approach - DCF)
    # =====================================================
    
    async def metodo_ingreso_dcf(
        self,
        propiedad: Propiedad,
        fecha_valoracion: date,
        horizonte_anos: int = 10
    ) -> Tuple[Optional[Decimal], Dict[str, Any]]:
        """
        Método del ingreso - Flujo de Caja Descontado (DCF)
        Valor = Σ(FCt / (1+r)^t) + VR / (1+r)^n
        """
        logger.info(f"Aplicando método DCF para {propiedad.id}")
        
        detalle = {}
        
        # 1. Estimar renta de mercado
        renta_mensual_uf = await self._estimar_renta_mercado(propiedad)
        detalle["renta_mensual_estimada_uf"] = float(renta_mensual_uf)
        
        # 2. Estimar vacancia y gastos
        vacancia_pct = 0.05  # 5% vacancia
        gastos_operacion_pct = 0.10  # 10% gastos (administración, mantención, seguros)
        
        detalle["vacancia_pct"] = vacancia_pct
        detalle["gastos_operacion_pct"] = gastos_operacion_pct
        
        # 3. Ingreso Operacional Neto anual
        ingreso_bruto_anual = renta_mensual_uf * 12
        vacancia = ingreso_bruto_anual * Decimal(str(vacancia_pct))
        ingreso_efectivo = ingreso_bruto_anual - vacancia
        gastos = ingreso_efectivo * Decimal(str(gastos_operacion_pct))
        noi = ingreso_efectivo - gastos
        
        detalle["ingreso_bruto_anual_uf"] = float(ingreso_bruto_anual)
        detalle["noi_anual_uf"] = float(noi)
        
        # 4. Determinar tasa de descuento y cap rate
        zona = self._determinar_zona_caprate(propiedad)
        tipo_uso = "residencial" if propiedad.tipo in [TipoPropiedad.DEPARTAMENTO, TipoPropiedad.CASA] else "oficinas"
        
        cap_rate = CAP_RATES_REFERENCIA.get(zona, CAP_RATES_REFERENCIA["regiones"])[tipo_uso]
        tasa_descuento = cap_rate + 0.02  # Prima de riesgo 2%
        
        detalle["zona"] = zona
        detalle["cap_rate"] = cap_rate
        detalle["tasa_descuento"] = tasa_descuento
        
        # 5. Tasa de crecimiento rentas
        tasa_crecimiento = 0.025  # 2.5% anual real
        detalle["tasa_crecimiento_rentas"] = tasa_crecimiento
        
        # 6. Calcular flujos descontados
        flujos = []
        valor_presente_flujos = Decimal("0")
        
        for t in range(1, horizonte_anos + 1):
            noi_t = noi * Decimal(str((1 + tasa_crecimiento) ** t))
            factor_descuento = Decimal(str(1 / ((1 + tasa_descuento) ** t)))
            vp_flujo = noi_t * factor_descuento
            
            flujos.append({
                "ano": t,
                "noi": float(noi_t),
                "factor_descuento": float(factor_descuento),
                "valor_presente": float(vp_flujo)
            })
            
            valor_presente_flujos += vp_flujo
        
        detalle["flujos"] = flujos
        
        # 7. Valor residual (perpetuidad)
        noi_terminal = noi * Decimal(str((1 + tasa_crecimiento) ** horizonte_anos))
        valor_terminal = noi_terminal / Decimal(str(cap_rate))
        factor_descuento_terminal = Decimal(str(1 / ((1 + tasa_descuento) ** horizonte_anos)))
        vp_terminal = valor_terminal * factor_descuento_terminal
        
        detalle["valor_terminal_uf"] = float(valor_terminal)
        detalle["vp_terminal_uf"] = float(vp_terminal)
        
        # 8. Valor total DCF
        valor_total = valor_presente_flujos + vp_terminal
        detalle["valor_total_dcf_uf"] = float(valor_total)
        
        return valor_total.quantize(Decimal("0.01")), detalle
    
    async def _estimar_renta_mercado(self, propiedad: Propiedad) -> Decimal:
        """Estimar renta de mercado basada en comparables de arriendo"""
        
        # Búsqueda simplificada - en producción usar datos reales
        # Ratio renta/precio típico por zona
        ratios_renta = {
            "Las Condes": 0.0035,      # 0.35% mensual
            "Providencia": 0.0038,
            "Vitacura": 0.0032,
            "Ñuñoa": 0.0042,
            "Santiago": 0.0045,
            "La Florida": 0.0048,
            "Maipú": 0.0050,
            "default": 0.0045
        }
        
        ratio = ratios_renta.get(propiedad.comuna, ratios_renta["default"])
        
        # Estimar valor de la propiedad para calcular renta
        # Si hay avalúo fiscal, usarlo como base
        if propiedad.avaluo_fiscal_uf:
            valor_base = propiedad.avaluo_fiscal_uf * Decimal("1.5")  # Avalúo suele ser 60-70% del valor comercial
        else:
            # Estimación rápida por m2
            precio_m2_ref = {
                TipoPropiedad.DEPARTAMENTO: 65,
                TipoPropiedad.CASA: 55,
                TipoPropiedad.OFICINA: 70,
            }
            precio_m2 = precio_m2_ref.get(propiedad.tipo, 50)
            valor_base = Decimal(str(precio_m2 * propiedad.superficie_construida_m2))
        
        return (valor_base * Decimal(str(ratio))).quantize(Decimal("0.01"))
    
    def _determinar_zona_caprate(self, propiedad: Propiedad) -> str:
        """Determinar zona para cap rate"""
        
        if propiedad.region != "RM":
            return "regiones"
        
        comunas_oriente = ["Las Condes", "Vitacura", "Lo Barnechea", "La Reina", "Providencia"]
        comunas_centro = ["Santiago", "Ñuñoa", "San Miguel"]
        
        if propiedad.comuna in comunas_oriente:
            return "santiago_oriente"
        elif propiedad.comuna in comunas_centro:
            return "santiago_centro"
        else:
            return "santiago_poniente"
    
    def _es_apto_para_renta(self, propiedad: Propiedad) -> bool:
        """Verificar si la propiedad es apta para método de ingreso"""
        return propiedad.tipo in [
            TipoPropiedad.DEPARTAMENTO,
            TipoPropiedad.CASA,
            TipoPropiedad.OFICINA,
            TipoPropiedad.LOCAL_COMERCIAL,
            TipoPropiedad.BODEGA
        ]
    
    # =====================================================
    # MÉTODO HEDONIC ML (XGBoost)
    # =====================================================
    
    async def metodo_hedonic_ml(
        self,
        propiedad: Propiedad,
        fecha_valoracion: date
    ) -> Tuple[Optional[Decimal], Dict[str, float]]:
        """
        Método Hedonic Pricing con XGBoost y explicabilidad SHAP
        """
        logger.info(f"Aplicando método hedonic ML para {propiedad.id}")
        
        # Cargar modelo si no está en memoria
        if self.modelo_hedonic is None:
            await self._cargar_modelo_hedonic()
        
        if self.modelo_hedonic is None:
            logger.warning("Modelo hedonic no disponible, entrenando...")
            await self.entrenar_modelo_hedonic()
        
        # Preparar features
        features = self._preparar_features_hedonic(propiedad)
        
        # Predicción
        try:
            X = pd.DataFrame([features])
            prediccion = self.modelo_hedonic.predict(X)[0]
            
            # SHAP para explicabilidad
            shap_values = {}
            if self.shap_explainer:
                shap_vals = self.shap_explainer.shap_values(X)
                for i, col in enumerate(X.columns):
                    shap_values[col] = float(shap_vals[0][i])
            
            valor_uf = Decimal(str(prediccion)) * Decimal(str(propiedad.superficie_construida_m2))
            
            return valor_uf.quantize(Decimal("0.01")), shap_values
            
        except Exception as e:
            logger.error(f"Error en predicción hedonic: {e}")
            return None, {}
    
    def _preparar_features_hedonic(self, propiedad: Propiedad) -> Dict[str, Any]:
        """Preparar features para modelo hedonic"""
        
        return {
            "superficie_m2": propiedad.superficie_construida_m2,
            "dormitorios": propiedad.dormitorios or 2,
            "banos": propiedad.banos or 1,
            "estacionamientos": propiedad.estacionamientos or 0,
            "antiguedad": (date.today().year - propiedad.ano_construccion) if propiedad.ano_construccion else 15,
            "piso": propiedad.piso or 1,
            "es_departamento": 1 if propiedad.tipo == TipoPropiedad.DEPARTAMENTO else 0,
            "es_casa": 1 if propiedad.tipo == TipoPropiedad.CASA else 0,
            "latitud": propiedad.latitud or -33.45,
            "longitud": propiedad.longitud or -70.65,
            # Encodings de comuna (simplificado)
            "comuna_premium": 1 if propiedad.comuna in ["Vitacura", "Las Condes", "Lo Barnechea"] else 0,
            "comuna_alta": 1 if propiedad.comuna in ["Providencia", "La Reina", "Ñuñoa"] else 0,
        }
    
    async def entrenar_modelo_hedonic(self):
        """Entrenar modelo XGBoost con datos históricos"""
        
        logger.info("Entrenando modelo hedonic pricing...")
        
        # Obtener datos de entrenamiento
        stmt = select(Comparable).where(
            Comparable.fecha_transaccion >= date.today() - timedelta(days=730)
        )
        result = await self.db.execute(stmt)
        comparables = result.scalars().all()
        
        if len(comparables) < 100:
            logger.warning(f"Datos insuficientes para entrenar: {len(comparables)}")
            return
        
        # Preparar dataset
        data = []
        for c in comparables:
            data.append({
                "precio_uf_m2": float(c.precio_uf_m2),
                "superficie_m2": c.superficie_m2,
                "dormitorios": c.dormitorios or 2,
                "banos": c.banos or 1,
                "antiguedad": (date.today().year - c.ano_construccion) if c.ano_construccion else 15,
                "es_departamento": 1 if c.tipo == TipoPropiedad.DEPARTAMENTO else 0,
                "es_casa": 1 if c.tipo == TipoPropiedad.CASA else 0,
            })
        
        df = pd.DataFrame(data)
        
        # Split
        X = df.drop("precio_uf_m2", axis=1)
        y = df["precio_uf_m2"]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Entrenar
        self.modelo_hedonic = xgb.XGBRegressor(
            n_estimators=settings.XGBOOST_N_ESTIMATORS,
            max_depth=settings.XGBOOST_MAX_DEPTH,
            learning_rate=settings.XGBOOST_LEARNING_RATE,
            random_state=42
        )
        
        self.modelo_hedonic.fit(X_train, y_train)
        
        # Evaluar
        y_pred = self.modelo_hedonic.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"Modelo entrenado - MAPE: {mape:.2%}, R²: {r2:.4f}")
        
        # SHAP explainer
        self.shap_explainer = shap.TreeExplainer(self.modelo_hedonic)
        
        # Guardar modelo
        model_path = f"{settings.ML_MODELS_PATH}/hedonic_v1.joblib"
        joblib.dump({
            "model": self.modelo_hedonic,
            "features": list(X.columns),
            "mape": mape,
            "r2": r2
        }, model_path)
    
    async def _cargar_modelo_hedonic(self):
        """Cargar modelo hedonic desde archivo"""
        try:
            model_path = f"{settings.ML_MODELS_PATH}/hedonic_v1.joblib"
            data = joblib.load(model_path)
            self.modelo_hedonic = data["model"]
            self.shap_explainer = shap.TreeExplainer(self.modelo_hedonic)
            logger.info("Modelo hedonic cargado correctamente")
        except Exception as e:
            logger.warning(f"No se pudo cargar modelo hedonic: {e}")
            self.modelo_hedonic = None
    
    # =====================================================
    # RECONCILIACIÓN DE MÉTODOS
    # =====================================================
    
    async def _reconciliar(
        self,
        resultado: ResultadoValorizacion,
        propiedad: Propiedad,
        proposito: str
    ) -> ResultadoValorizacion:
        """
        Reconciliar valores de diferentes métodos
        Ponderación basada en tipo de propiedad, propósito y confiabilidad de datos
        """
        
        valores_disponibles = {}
        
        if resultado.valor_comparacion_uf:
            valores_disponibles["comparacion"] = resultado.valor_comparacion_uf
        if resultado.valor_costo_uf:
            valores_disponibles["costo"] = resultado.valor_costo_uf
        if resultado.valor_ingreso_uf:
            valores_disponibles["ingreso"] = resultado.valor_ingreso_uf
        if resultado.valor_hedonic_uf:
            valores_disponibles["hedonic"] = resultado.valor_hedonic_uf
        
        if not valores_disponibles:
            raise ValueError("No se pudo calcular ningún valor")
        
        # Ponderaciones base según propósito
        ponderaciones_base = {
            "mercado": {"comparacion": 0.45, "hedonic": 0.30, "ingreso": 0.15, "costo": 0.10},
            "liquidacion": {"comparacion": 0.60, "costo": 0.25, "hedonic": 0.10, "ingreso": 0.05},
            "inversion": {"ingreso": 0.50, "comparacion": 0.25, "hedonic": 0.20, "costo": 0.05},
            "asegurable": {"costo": 0.70, "comparacion": 0.20, "hedonic": 0.10, "ingreso": 0.00}
        }
        
        pesos = ponderaciones_base.get(proposito, ponderaciones_base["mercado"])
        
        # Ajustar pesos según disponibilidad
        pesos_ajustados = {}
        suma = 0
        for metodo, peso in pesos.items():
            if metodo in valores_disponibles:
                pesos_ajustados[metodo] = peso
                suma += peso
        
        # Normalizar
        for metodo in pesos_ajustados:
            pesos_ajustados[metodo] /= suma
        
        resultado.ponderaciones = pesos_ajustados
        
        # Calcular valor ponderado
        valor_ponderado = Decimal("0")
        for metodo, valor in valores_disponibles.items():
            if metodo in pesos_ajustados:
                valor_ponderado += valor * Decimal(str(pesos_ajustados[metodo]))
        
        resultado.valor_final_uf = valor_ponderado.quantize(Decimal("0.01"))
        
        # Determinar método principal
        metodo_max = max(pesos_ajustados, key=pesos_ajustados.get)
        resultado.metodo_principal = MetodoValorizacion(metodo_max)
        
        # Calcular rango (±10% del valor medio)
        valores_list = list(valores_disponibles.values())
        resultado.valor_minimo_uf = min(valores_list) * Decimal("0.90")
        resultado.valor_maximo_uf = max(valores_list) * Decimal("1.10")
        
        # Calcular confianza basada en dispersión
        if len(valores_list) > 1:
            valores_float = [float(v) for v in valores_list]
            coef_variacion = np.std(valores_float) / np.mean(valores_float)
            resultado.confianza_pct = max(0, min(100, (1 - coef_variacion) * 100))
        else:
            resultado.confianza_pct = 70.0  # Valor por defecto si solo hay un método
        
        return resultado
    
    # =====================================================
    # HELPERS
    # =====================================================
    
    async def _get_propiedad(self, propiedad_id: str) -> Optional[Propiedad]:
        """Obtener propiedad por ID"""
        from uuid import UUID
        stmt = select(Propiedad).where(Propiedad.id == UUID(propiedad_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _save_valorizacion(
        self,
        resultado: ResultadoValorizacion,
        propiedad: Propiedad
    ):
        """Guardar valorización en BD"""
        try:
            from uuid import UUID
            
            valorizacion = Valorizacion(
                propiedad_id=UUID(resultado.propiedad_id),
                tipo_valor="mercado",
                proposito="Valorización automática DATAPOLIS",
                fecha_valoracion=resultado.fecha_valoracion,
                valor_comparacion_uf=resultado.valor_comparacion_uf,
                valor_costo_uf=resultado.valor_costo_uf,
                valor_ingreso_uf=resultado.valor_ingreso_uf,
                valor_hedonic_uf=resultado.valor_hedonic_uf,
                valor_final_uf=resultado.valor_final_uf,
                metodo_principal=resultado.metodo_principal,
                ponderaciones=resultado.ponderaciones,
                valor_minimo_uf=resultado.valor_minimo_uf,
                valor_maximo_uf=resultado.valor_maximo_uf,
                comparables_ids=[c.id for c in resultado.comparables_usados],
                tasa_descuento=resultado.detalle_dcf.get("tasa_descuento"),
                cap_rate=resultado.detalle_dcf.get("cap_rate"),
                flujos_proyectados=resultado.detalle_dcf.get("flujos"),
                confianza_pct=resultado.confianza_pct,
                modelo_ml_version="v1.0" if resultado.valor_hedonic_uf else None
            )
            
            self.db.add(valorizacion)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error guardando valorización: {e}")
