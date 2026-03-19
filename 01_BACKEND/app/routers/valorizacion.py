"""
DATAPOLIS v3.0 - Router API Valorización Inmobiliaria
Endpoints REST para M04_Valorizacion (IVS 2022, ML, comparables)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import json
import io

from app.schemas.valorizacion import (
    ValorizacionRequest, ValorizacionResponse, ValorizacionRapidaRequest,
    ComparablesRequest, ComparablesResponse, InformeValorizacionRequest,
    HistorialValorizacionResponse, AjusteRequest, MetodologiaDetalle,
    ValorizacionMasivaRequest, ResultadoMasivoResponse
)
from app.schemas.base import ResponseWrapper, PaginatedResponse, ErrorResponse
from app.services.m04_valorizacion import ServicioValorizacion
from app.config import get_settings

router = APIRouter(
    prefix="/valorizacion",
    tags=["Valorización Inmobiliaria"],
    responses={
        404: {"model": ErrorResponse, "description": "Propiedad no encontrada"},
        422: {"model": ErrorResponse, "description": "Error de validación"},
        500: {"model": ErrorResponse, "description": "Error interno"}
    }
)

settings = get_settings()
_servicio_valorizacion: Optional[ServicioValorizacion] = None

async def get_servicio_valorizacion() -> ServicioValorizacion:
    """Dependency injection para servicio valorización"""
    global _servicio_valorizacion
    if _servicio_valorizacion is None:
        _servicio_valorizacion = ServicioValorizacion()
    return _servicio_valorizacion


# ============================================================================
# VALORIZACIÓN COMPLETA (IVS 2022)
# ============================================================================

@router.post(
    "/completa",
    response_model=ResponseWrapper[ValorizacionResponse],
    summary="Valorización completa IVS 2022",
    description="Genera valorización profesional según estándares IVS 2022"
)
async def valorizar_propiedad(
    request: ValorizacionRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Valorización inmobiliaria profesional cumpliendo IVS 2022.
    
    **Metodologías aplicadas**:
    - Comparación de mercado (sales comparison approach)
    - Costo de reposición depreciado
    - Capitalización de ingresos (income approach)
    - Machine Learning (XGBoost ensemble)
    
    **Tiempo estimado**: 2-5 segundos
    """
    try:
        resultado = await servicio.valorizar_completa(request)
        
        # Log asíncrono para auditoría
        background_tasks.add_task(
            _log_valorizacion,
            resultado.id_valorizacion,
            request.dict()
        )
        
        return ResponseWrapper(
            success=True,
            data=resultado,
            message="Valorización completada exitosamente"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en valorización: {str(e)}")


@router.post(
    "/rapida",
    response_model=ResponseWrapper[dict],
    summary="Valorización rápida (AVM)",
    description="Estimación automatizada instantánea"
)
async def valorizar_rapida(
    request: ValorizacionRapidaRequest,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Valorización AVM (Automated Valuation Model) instantánea.
    
    **Uso recomendado**: 
    - Pre-evaluación rápida
    - Filtrado masivo de propiedades
    - Estimación inicial para clientes
    
    **Precisión típica**: ±10-15%
    """
    try:
        resultado = await servicio.valorizar_rapida(
            direccion=request.direccion,
            comuna=request.comuna,
            tipo_propiedad=request.tipo_propiedad,
            superficie_terreno=request.superficie_terreno,
            superficie_construida=request.superficie_construida,
            dormitorios=request.dormitorios,
            banos=request.banos,
            antiguedad=request.antiguedad
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "valor_estimado_uf": resultado["valor_uf"],
                "valor_estimado_clp": resultado["valor_clp"],
                "rango_minimo_uf": resultado["rango_min_uf"],
                "rango_maximo_uf": resultado["rango_max_uf"],
                "confianza": resultado["confianza"],
                "uf_referencia": resultado["uf_valor"],
                "fecha_estimacion": datetime.now().isoformat(),
                "tipo": "AVM",
                "disclaimer": "Estimación automatizada. Para valoración oficial, solicite valorización completa."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metodologias",
    response_model=ResponseWrapper[List[MetodologiaDetalle]],
    summary="Metodologías disponibles"
)
async def listar_metodologias():
    """
    Lista metodologías de valorización disponibles con descripción.
    """
    metodologias = [
        MetodologiaDetalle(
            codigo="COMPARACION_MERCADO",
            nombre="Comparación de Mercado",
            descripcion="Análisis de ventas comparables ajustadas por diferencias físicas y de ubicación",
            estandar_ivs="IVS 105 - Enfoques y Métodos de Valoración",
            aplicabilidad=["viviendas", "departamentos", "terrenos"],
            precision_tipica="±5-10%",
            requiere=["datos_mercado", "comparables_recientes"]
        ),
        MetodologiaDetalle(
            codigo="COSTO_REPOSICION",
            nombre="Costo de Reposición Depreciado",
            descripcion="Valor terreno + costo construcción nueva - depreciación acumulada",
            estandar_ivs="IVS 105.50 - Enfoque de Costo",
            aplicabilidad=["construcciones_especiales", "inmuebles_nuevos", "sin_mercado_activo"],
            precision_tipica="±10-15%",
            requiere=["costos_construccion", "tablas_depreciacion"]
        ),
        MetodologiaDetalle(
            codigo="CAPITALIZACION_INGRESOS",
            nombre="Capitalización de Ingresos",
            descripcion="Valor presente de flujos futuros de arriendo descontados",
            estandar_ivs="IVS 105.40 - Enfoque de Ingresos",
            aplicabilidad=["propiedades_renta", "comercial", "multifamily"],
            precision_tipica="±8-12%",
            requiere=["datos_arriendo", "tasas_capitalizacion"]
        ),
        MetodologiaDetalle(
            codigo="ML_XGBOOST",
            nombre="Machine Learning Ensemble",
            descripcion="Modelo XGBoost entrenado con transacciones históricas y features geoespaciales",
            estandar_ivs="N/A - Complementario",
            aplicabilidad=["todas"],
            precision_tipica="±7-12%",
            requiere=["modelo_entrenado", "features_completas"]
        )
    ]
    
    return ResponseWrapper(success=True, data=metodologias)


# ============================================================================
# COMPARABLES DE MERCADO
# ============================================================================

@router.post(
    "/comparables/buscar",
    response_model=ResponseWrapper[ComparablesResponse],
    summary="Buscar propiedades comparables"
)
async def buscar_comparables(
    request: ComparablesRequest,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Busca propiedades comparables para análisis de mercado.
    
    **Criterios de búsqueda**:
    - Radio geográfico configurable
    - Mismo tipo de propiedad
    - Rango de superficie ±20%
    - Transacciones últimos 12 meses (configurable)
    
    **Máximo**: 20 comparables ordenados por similitud
    """
    try:
        resultado = await servicio.buscar_comparables(
            latitud=request.latitud,
            longitud=request.longitud,
            tipo_propiedad=request.tipo_propiedad,
            superficie_terreno=request.superficie_terreno,
            superficie_construida=request.superficie_construida,
            radio_km=request.radio_km or 1.5,
            meses_antiguedad=request.meses_antiguedad or 12,
            max_resultados=request.max_resultados or 20
        )
        
        return ResponseWrapper(
            success=True,
            data=ComparablesResponse(
                total_encontrados=resultado["total"],
                comparables=resultado["comparables"],
                estadisticas={
                    "valor_promedio_uf": resultado["promedio_uf"],
                    "valor_mediana_uf": resultado["mediana_uf"],
                    "valor_m2_promedio": resultado["m2_promedio"],
                    "desviacion_estandar": resultado["std_dev"],
                    "coeficiente_variacion": resultado["cv"]
                },
                criterios_aplicados=resultado["criterios"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/comparables/{rol_sii}",
    response_model=ResponseWrapper[ComparablesResponse],
    summary="Comparables para propiedad específica"
)
async def get_comparables_por_rol(
    rol_sii: str,
    radio_km: float = Query(1.5, ge=0.1, le=10),
    max_resultados: int = Query(10, ge=1, le=50),
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Busca comparables para una propiedad identificada por ROL SII.
    
    **Formato ROL**: COMUNA-MANZANA-PREDIO (ej: 13101-00123-00045)
    """
    try:
        resultado = await servicio.comparables_por_rol(rol_sii, radio_km, max_resultados)
        
        return ResponseWrapper(
            success=True,
            data=resultado
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"ROL inválido: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AJUSTES Y RECONCILIACIÓN
# ============================================================================

@router.post(
    "/ajuste/calcular",
    response_model=ResponseWrapper[dict],
    summary="Calcular factor de ajuste"
)
async def calcular_ajuste(
    request: AjusteRequest,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Calcula factor de ajuste entre propiedad sujeto y comparable.
    
    **Factores de ajuste**:
    - Ubicación (zona, accesibilidad)
    - Superficie (terreno y construida)
    - Antigüedad y estado
    - Calidad construcción
    - Amenities y extras
    - Fecha transacción (actualización temporal)
    """
    try:
        resultado = await servicio.calcular_ajuste(
            valor_comparable=request.valor_comparable,
            sujeto=request.datos_sujeto,
            comparable=request.datos_comparable
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "valor_original": request.valor_comparable,
                "valor_ajustado": resultado["valor_ajustado"],
                "factor_total": resultado["factor_total"],
                "desglose_ajustes": resultado["desglose"],
                "confiabilidad": resultado["confiabilidad"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reconciliar",
    response_model=ResponseWrapper[dict],
    summary="Reconciliar múltiples valoraciones"
)
async def reconciliar_valores(
    valores: List[dict],
    pesos: Optional[List[float]] = Query(None),
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Reconcilia valores de diferentes metodologías según IVS 105.
    
    **Input**: Lista de valoraciones con metodología y confianza
    
    **Output**: Valor final reconciliado con justificación
    """
    try:
        resultado = await servicio.reconciliar_valores(valores, pesos)
        
        return ResponseWrapper(
            success=True,
            data={
                "valor_reconciliado_uf": resultado["valor_final_uf"],
                "metodologia_predominante": resultado["metodologia_principal"],
                "ponderaciones_aplicadas": resultado["ponderaciones"],
                "rango_valores": {
                    "minimo": resultado["valor_min"],
                    "maximo": resultado["valor_max"]
                },
                "justificacion": resultado["justificacion"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INFORMES Y EXPORTACIÓN
# ============================================================================

@router.post(
    "/informe/generar",
    response_model=ResponseWrapper[dict],
    summary="Generar informe de valorización"
)
async def generar_informe(
    request: InformeValorizacionRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Genera informe profesional de valorización en PDF.
    
    **Formatos**: PDF, DOCX, HTML
    
    **Contenido**:
    - Resumen ejecutivo
    - Descripción propiedad
    - Análisis de mercado
    - Metodologías aplicadas
    - Conclusión de valor
    - Anexos (comparables, fotos, mapas)
    """
    try:
        resultado = await servicio.generar_informe(
            id_valorizacion=request.id_valorizacion,
            formato=request.formato or "pdf",
            incluir_fotos=request.incluir_fotos,
            incluir_mapas=request.incluir_mapas,
            idioma=request.idioma or "es"
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "informe_id": resultado["informe_id"],
                "url_descarga": resultado["url"],
                "formato": request.formato or "pdf",
                "paginas": resultado["paginas"],
                "generado_at": datetime.now().isoformat(),
                "expira_at": resultado["expira_at"]
            },
            message="Informe generado correctamente"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/informe/{informe_id}/descargar",
    summary="Descargar informe generado"
)
async def descargar_informe(
    informe_id: str,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """Descarga informe de valorización previamente generado"""
    try:
        contenido, filename, media_type = await servicio.obtener_informe(informe_id)
        
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Informe no encontrado o expirado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HISTORIAL Y TRACKING
# ============================================================================

@router.get(
    "/historial/{rol_sii}",
    response_model=ResponseWrapper[HistorialValorizacionResponse],
    summary="Historial de valoraciones"
)
async def get_historial(
    rol_sii: str,
    limite: int = Query(10, ge=1, le=100),
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Obtiene historial de valoraciones para una propiedad.
    
    **Incluye**: Valoraciones propias y de terceros (si disponibles)
    """
    try:
        resultado = await servicio.obtener_historial(rol_sii, limite)
        
        return ResponseWrapper(
            success=True,
            data=HistorialValorizacionResponse(
                rol_sii=rol_sii,
                total_valoraciones=resultado["total"],
                valoraciones=resultado["valoraciones"],
                tendencia=resultado.get("tendencia"),
                variacion_anual_promedio=resultado.get("variacion_anual")
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_valorizacion}",
    response_model=ResponseWrapper[ValorizacionResponse],
    summary="Obtener valorización por ID"
)
async def get_valorizacion(
    id_valorizacion: str,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """Recupera valorización existente por su ID único"""
    try:
        resultado = await servicio.obtener_valorizacion(id_valorizacion)
        if resultado is None:
            raise HTTPException(status_code=404, detail="Valorización no encontrada")
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VALORIZACIÓN MASIVA
# ============================================================================

@router.post(
    "/masiva",
    response_model=ResponseWrapper[dict],
    summary="Valorización masiva (batch)"
)
async def valorizar_masiva(
    request: ValorizacionMasivaRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Procesa valorización de múltiples propiedades en batch.
    
    **Límites**:
    - Máximo 100 propiedades por request
    - Tiempo máximo: 5 minutos
    
    **Modo**: Async con callback opcional
    """
    if len(request.propiedades) > 100:
        raise HTTPException(status_code=400, detail="Máximo 100 propiedades por batch")
    
    try:
        # Iniciar proceso batch
        batch_id = await servicio.iniciar_batch(
            propiedades=request.propiedades,
            tipo_valoracion=request.tipo_valoracion or "rapida",
            callback_url=request.callback_url
        )
        
        # Ejecutar en background
        background_tasks.add_task(
            servicio.ejecutar_batch,
            batch_id
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "batch_id": batch_id,
                "total_propiedades": len(request.propiedades),
                "estado": "procesando",
                "tiempo_estimado_segundos": len(request.propiedades) * 2,
                "url_resultado": f"/api/v1/valorizacion/masiva/{batch_id}/resultado"
            },
            message="Proceso batch iniciado"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/masiva/{batch_id}/estado",
    response_model=ResponseWrapper[dict],
    summary="Estado de valorización masiva"
)
async def get_estado_batch(
    batch_id: str,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """Consulta estado de proceso batch"""
    try:
        estado = await servicio.estado_batch(batch_id)
        if estado is None:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        return ResponseWrapper(success=True, data=estado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/masiva/{batch_id}/resultado",
    response_model=ResponseWrapper[ResultadoMasivoResponse],
    summary="Resultado valorización masiva"
)
async def get_resultado_batch(
    batch_id: str,
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """Obtiene resultados de proceso batch completado"""
    try:
        resultado = await servicio.resultado_batch(batch_id)
        if resultado is None:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        if resultado["estado"] != "completado":
            raise HTTPException(
                status_code=409,
                detail=f"Batch aún en proceso: {resultado['estado']}"
            )
        
        return ResponseWrapper(
            success=True,
            data=ResultadoMasivoResponse(
                batch_id=batch_id,
                total_procesadas=resultado["total"],
                exitosas=resultado["exitosas"],
                fallidas=resultado["fallidas"],
                resultados=resultado["resultados"],
                resumen_estadistico=resultado.get("resumen")
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INDICES DE MERCADO
# ============================================================================

@router.get(
    "/indices/comunales",
    response_model=ResponseWrapper[List[dict]],
    summary="Índices de valor por comuna"
)
async def get_indices_comunales(
    region: Optional[str] = Query(None),
    tipo_propiedad: Optional[str] = Query(None),
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """
    Índices de valor UF/m² por comuna.
    
    **Datos**: Promedio últimos 6 meses con tendencia
    """
    try:
        indices = await servicio.obtener_indices_comunales(region, tipo_propiedad)
        return ResponseWrapper(success=True, data=indices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/indices/tendencia/{comuna}",
    response_model=ResponseWrapper[dict],
    summary="Tendencia de valores por comuna"
)
async def get_tendencia_comuna(
    comuna: str,
    meses: int = Query(12, ge=3, le=60),
    servicio: ServicioValorizacion = Depends(get_servicio_valorizacion)
):
    """Análisis de tendencia de valores para una comuna específica"""
    try:
        resultado = await servicio.tendencia_comuna(comuna, meses)
        return ResponseWrapper(success=True, data=resultado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILIDADES
# ============================================================================

async def _log_valorizacion(id_valorizacion: str, request_data: dict):
    """Log asíncrono para auditoría de valoraciones"""
    # Implementar logging a base de datos o sistema externo
    pass


@router.get("/health", include_in_schema=False)
async def health_check():
    return {
        "status": "healthy",
        "service": "valorizacion",
        "timestamp": datetime.now().isoformat()
    }
