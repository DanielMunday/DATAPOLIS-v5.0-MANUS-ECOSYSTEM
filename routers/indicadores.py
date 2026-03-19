"""
DATAPOLIS v3.0 - Router API Indicadores Económicos
Endpoints REST para servicio IE_Indicadores (BCCh, UF, IPC, tasas)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
import asyncio

from app.schemas.indicadores import (
    IndicadorRequest, IndicadorResponse, SerieHistoricaResponse,
    ProyeccionResponse, AlertaIndicadorResponse, IndicadorBulkRequest,
    ComparativoResponse
)
from app.schemas.base import ResponseWrapper, PaginatedResponse, ErrorResponse
from app.services.ie_indicadores import ServicioIndicadoresEconomicos
from app.config import get_settings

router = APIRouter(
    prefix="/indicadores",
    tags=["Indicadores Económicos"],
    responses={
        404: {"model": ErrorResponse, "description": "Indicador no encontrado"},
        422: {"model": ErrorResponse, "description": "Error de validación"},
        500: {"model": ErrorResponse, "description": "Error interno"}
    }
)

settings = get_settings()

# Instancia global del servicio (singleton pattern)
_servicio_indicadores: Optional[ServicioIndicadoresEconomicos] = None

async def get_servicio_indicadores() -> ServicioIndicadoresEconomicos:
    """Dependency injection para servicio indicadores"""
    global _servicio_indicadores
    if _servicio_indicadores is None:
        _servicio_indicadores = ServicioIndicadoresEconomicos()
    return _servicio_indicadores


# ============================================================================
# ENDPOINTS UF (Unidad de Fomento)
# ============================================================================

@router.get(
    "/uf/actual",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Obtener valor UF actual",
    description="Retorna el valor vigente de la UF para hoy"
)
async def get_uf_actual(
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene el valor UF vigente del día.
    
    **Fuente**: Banco Central de Chile (BCCh)
    
    **Actualización**: Diaria (publicada mes anterior)
    """
    try:
        resultado = await servicio.obtener_uf_actual()
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="UF",
                nombre="Unidad de Fomento",
                valor=resultado["valor"],
                fecha=resultado["fecha"],
                variacion_diaria=resultado.get("variacion_diaria"),
                variacion_mensual=resultado.get("variacion_mensual"),
                variacion_anual=resultado.get("variacion_anual"),
                fuente="BCCh",
                unidad="CLP"
            ),
            message="UF obtenida correctamente"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo UF: {str(e)}")


@router.get(
    "/uf/fecha/{fecha}",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Obtener UF por fecha específica"
)
async def get_uf_fecha(
    fecha: date,
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene el valor UF para una fecha específica.
    
    **Parámetros**:
    - **fecha**: Fecha en formato YYYY-MM-DD
    
    **Nota**: Fechas futuras retornan proyección
    """
    try:
        resultado = await servicio.obtener_uf_fecha(fecha)
        if resultado is None:
            raise HTTPException(status_code=404, detail=f"UF no disponible para fecha {fecha}")
        
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="UF",
                nombre="Unidad de Fomento",
                valor=resultado["valor"],
                fecha=fecha,
                es_proyeccion=resultado.get("es_proyeccion", False),
                fuente="BCCh",
                unidad="CLP"
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/uf/serie",
    response_model=ResponseWrapper[SerieHistoricaResponse],
    summary="Obtener serie histórica UF"
)
async def get_uf_serie(
    fecha_inicio: date = Query(..., description="Fecha inicio serie"),
    fecha_fin: date = Query(None, description="Fecha fin serie (default: hoy)"),
    frecuencia: str = Query("diaria", regex="^(diaria|mensual|anual)$"),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene serie histórica de valores UF.
    
    **Frecuencias disponibles**:
    - diaria: Valores día a día
    - mensual: Promedio mensual
    - anual: Promedio anual
    """
    if fecha_fin is None:
        fecha_fin = date.today()
    
    try:
        resultado = await servicio.obtener_serie_uf(fecha_inicio, fecha_fin, frecuencia)
        return ResponseWrapper(
            success=True,
            data=SerieHistoricaResponse(
                codigo="UF",
                nombre="Unidad de Fomento",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                frecuencia=frecuencia,
                total_registros=len(resultado["valores"]),
                valores=resultado["valores"],
                estadisticas=resultado.get("estadisticas"),
                fuente="BCCh"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/uf/convertir",
    response_model=ResponseWrapper[dict],
    summary="Convertir monto CLP a UF o viceversa"
)
async def convertir_uf(
    monto: float = Query(..., description="Monto a convertir"),
    direccion: str = Query("clp_to_uf", regex="^(clp_to_uf|uf_to_clp)$"),
    fecha: Optional[date] = Query(None, description="Fecha UF (default: hoy)"),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Convierte montos entre CLP y UF.
    
    **Direcciones**:
    - clp_to_uf: Pesos chilenos a UF
    - uf_to_clp: UF a pesos chilenos
    """
    try:
        if fecha is None:
            fecha = date.today()
        
        resultado = await servicio.convertir_uf(monto, direccion, fecha)
        
        return ResponseWrapper(
            success=True,
            data={
                "monto_original": monto,
                "moneda_original": "CLP" if direccion == "clp_to_uf" else "UF",
                "monto_convertido": resultado["monto_convertido"],
                "moneda_destino": "UF" if direccion == "clp_to_uf" else "CLP",
                "uf_utilizada": resultado["uf_valor"],
                "fecha_uf": str(fecha)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS IPC (Índice de Precios al Consumidor)
# ============================================================================

@router.get(
    "/ipc/actual",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Obtener IPC actual"
)
async def get_ipc_actual(
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene el último valor IPC disponible.
    
    **Fuente**: INE Chile
    
    **Publicación**: Día 8 de cada mes
    """
    try:
        resultado = await servicio.obtener_ipc_actual()
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="IPC",
                nombre="Índice de Precios al Consumidor",
                valor=resultado["valor"],
                fecha=resultado["fecha"],
                variacion_mensual=resultado.get("variacion_mensual"),
                variacion_anual=resultado.get("variacion_12_meses"),
                variacion_acumulada=resultado.get("variacion_acumulada"),
                fuente="INE",
                unidad="índice base 2018=100"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ipc/serie",
    response_model=ResponseWrapper[SerieHistoricaResponse],
    summary="Serie histórica IPC"
)
async def get_ipc_serie(
    fecha_inicio: date = Query(...),
    fecha_fin: Optional[date] = Query(None),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """Serie histórica mensual del IPC"""
    if fecha_fin is None:
        fecha_fin = date.today()
    
    try:
        resultado = await servicio.obtener_serie_ipc(fecha_inicio, fecha_fin)
        return ResponseWrapper(
            success=True,
            data=SerieHistoricaResponse(
                codigo="IPC",
                nombre="Índice de Precios al Consumidor",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                frecuencia="mensual",
                total_registros=len(resultado["valores"]),
                valores=resultado["valores"],
                estadisticas=resultado.get("estadisticas"),
                fuente="INE"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS TASAS DE INTERÉS
# ============================================================================

@router.get(
    "/tasas/hipotecarias",
    response_model=ResponseWrapper[List[IndicadorResponse]],
    summary="Tasas hipotecarias vigentes"
)
async def get_tasas_hipotecarias(
    tipo_credito: Optional[str] = Query(None, regex="^(vivienda|comercial|consumo)$"),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene tasas hipotecarias promedio del sistema financiero.
    
    **Tipos**:
    - vivienda: Créditos habitacionales
    - comercial: Créditos comerciales
    - consumo: Créditos de consumo
    
    **Fuente**: CMF / BCCh
    """
    try:
        resultado = await servicio.obtener_tasas_hipotecarias(tipo_credito)
        
        tasas = [
            IndicadorResponse(
                codigo=f"TASA_{t['tipo'].upper()}",
                nombre=f"Tasa {t['tipo'].title()}",
                valor=t["tasa_promedio"],
                fecha=t["fecha"],
                metadata={
                    "tasa_minima": t.get("tasa_minima"),
                    "tasa_maxima": t.get("tasa_maxima"),
                    "spread": t.get("spread"),
                    "plazo_tipico": t.get("plazo_tipico")
                },
                fuente="CMF",
                unidad="% anual"
            )
            for t in resultado["tasas"]
        ]
        
        return ResponseWrapper(success=True, data=tasas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tasas/tpm",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Tasa de Política Monetaria"
)
async def get_tpm(
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene la TPM vigente del Banco Central.
    
    **Actualización**: Reuniones mensuales del Consejo BCCh
    """
    try:
        resultado = await servicio.obtener_tpm()
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="TPM",
                nombre="Tasa de Política Monetaria",
                valor=resultado["valor"],
                fecha=resultado["fecha"],
                variacion_anterior=resultado.get("variacion_anterior"),
                metadata={
                    "proxima_reunion": resultado.get("proxima_reunion"),
                    "tendencia": resultado.get("tendencia")
                },
                fuente="BCCh",
                unidad="% anual"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS TIPO DE CAMBIO
# ============================================================================

@router.get(
    "/dolar/observado",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Dólar observado BCCh"
)
async def get_dolar_observado(
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Tipo de cambio dólar observado oficial.
    
    **Fuente**: Banco Central de Chile
    """
    try:
        resultado = await servicio.obtener_dolar_observado()
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="USD_CLP",
                nombre="Dólar Observado",
                valor=resultado["valor"],
                fecha=resultado["fecha"],
                variacion_diaria=resultado.get("variacion_diaria"),
                variacion_mensual=resultado.get("variacion_mensual"),
                variacion_anual=resultado.get("variacion_anual"),
                fuente="BCCh",
                unidad="CLP/USD"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/euro",
    response_model=ResponseWrapper[IndicadorResponse],
    summary="Tipo cambio Euro"
)
async def get_euro(
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """Tipo de cambio Euro oficial BCCh"""
    try:
        resultado = await servicio.obtener_euro()
        return ResponseWrapper(
            success=True,
            data=IndicadorResponse(
                codigo="EUR_CLP",
                nombre="Euro",
                valor=resultado["valor"],
                fecha=resultado["fecha"],
                variacion_diaria=resultado.get("variacion_diaria"),
                fuente="BCCh",
                unidad="CLP/EUR"
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROYECCIONES (ARIMA/ML)
# ============================================================================

@router.get(
    "/proyeccion/{indicador}",
    response_model=ResponseWrapper[ProyeccionResponse],
    summary="Proyección indicador"
)
async def get_proyeccion(
    indicador: str,
    horizonte_meses: int = Query(12, ge=1, le=60, description="Meses a proyectar"),
    modelo: str = Query("arima", regex="^(arima|prophet|ensemble)$"),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Genera proyección de indicador usando modelos ML.
    
    **Indicadores disponibles**: UF, IPC, USD, EUR, TPM
    
    **Modelos**:
    - arima: ARIMA(p,d,q) optimizado
    - prophet: Facebook Prophet
    - ensemble: Combinación ponderada
    """
    indicador_upper = indicador.upper()
    if indicador_upper not in ["UF", "IPC", "USD", "EUR", "TPM"]:
        raise HTTPException(status_code=400, detail=f"Indicador no soportado: {indicador}")
    
    try:
        resultado = await servicio.generar_proyeccion(
            indicador_upper,
            horizonte_meses,
            modelo
        )
        
        return ResponseWrapper(
            success=True,
            data=ProyeccionResponse(
                indicador=indicador_upper,
                modelo_utilizado=modelo,
                fecha_generacion=datetime.now(),
                horizonte_meses=horizonte_meses,
                proyecciones=resultado["proyecciones"],
                intervalo_confianza=resultado.get("intervalo_confianza", 0.95),
                metricas_modelo={
                    "mape": resultado.get("mape"),
                    "rmse": resultado.get("rmse"),
                    "aic": resultado.get("aic")
                },
                disclaimer="Proyección estimativa. No constituye asesoría financiera."
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ALERTAS Y MONITOREO
# ============================================================================

@router.post(
    "/alertas/configurar",
    response_model=ResponseWrapper[dict],
    summary="Configurar alerta indicador"
)
async def configurar_alerta(
    indicador: str = Query(...),
    tipo_alerta: str = Query(..., regex="^(umbral_superior|umbral_inferior|variacion_porcentual)$"),
    valor_umbral: float = Query(...),
    webhook_url: Optional[str] = Query(None),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Configura alerta para cuando indicador alcance umbral.
    
    **Tipos**:
    - umbral_superior: Notifica si valor > umbral
    - umbral_inferior: Notifica si valor < umbral
    - variacion_porcentual: Notifica si variación > umbral%
    """
    try:
        alerta_id = await servicio.configurar_alerta(
            indicador=indicador.upper(),
            tipo=tipo_alerta,
            umbral=valor_umbral,
            webhook=webhook_url
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "alerta_id": alerta_id,
                "indicador": indicador.upper(),
                "tipo": tipo_alerta,
                "umbral": valor_umbral,
                "estado": "activa"
            },
            message="Alerta configurada correctamente"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BULK / COMPARATIVOS
# ============================================================================

@router.post(
    "/bulk",
    response_model=ResponseWrapper[List[IndicadorResponse]],
    summary="Obtener múltiples indicadores"
)
async def get_indicadores_bulk(
    request: IndicadorBulkRequest,
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Obtiene múltiples indicadores en una sola llamada.
    
    **Máximo**: 10 indicadores por request
    """
    if len(request.indicadores) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 indicadores por request")
    
    try:
        resultados = await servicio.obtener_bulk(request.indicadores, request.fecha)
        
        return ResponseWrapper(
            success=True,
            data=[
                IndicadorResponse(
                    codigo=r["codigo"],
                    nombre=r["nombre"],
                    valor=r["valor"],
                    fecha=r["fecha"],
                    fuente=r["fuente"],
                    unidad=r["unidad"]
                )
                for r in resultados
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/comparativo",
    response_model=ResponseWrapper[ComparativoResponse],
    summary="Comparativo temporal indicadores"
)
async def get_comparativo(
    indicadores: str = Query(..., description="Códigos separados por coma: UF,IPC,USD"),
    periodos: str = Query("1m,3m,6m,1y", description="Períodos: 1m,3m,6m,1y,3y,5y"),
    servicio: ServicioIndicadoresEconomicos = Depends(get_servicio_indicadores)
):
    """
    Genera comparativo de variaciones para múltiples indicadores y períodos.
    
    **Útil para**: Análisis de correlaciones, benchmarking, reportes
    """
    lista_indicadores = [i.strip().upper() for i in indicadores.split(",")]
    lista_periodos = [p.strip() for p in periodos.split(",")]
    
    try:
        resultado = await servicio.generar_comparativo(lista_indicadores, lista_periodos)
        
        return ResponseWrapper(
            success=True,
            data=ComparativoResponse(
                indicadores=lista_indicadores,
                periodos=lista_periodos,
                fecha_base=date.today(),
                matriz_variaciones=resultado["matriz"],
                correlaciones=resultado.get("correlaciones"),
                tendencias=resultado.get("tendencias")
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", include_in_schema=False)
async def health_check():
    """Health check del servicio indicadores"""
    return {
        "status": "healthy",
        "service": "indicadores_economicos",
        "timestamp": datetime.now().isoformat()
    }
