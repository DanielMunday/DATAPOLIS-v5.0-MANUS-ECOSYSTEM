"""
DATAPOLIS v3.0 - Router de Mercado de Suelo
============================================
API REST para análisis de mercado inmobiliario.

Endpoints:
- GET /mercado/oferta - Obtener oferta actual del mercado
- GET /mercado/zona/{comuna} - Análisis de zona específica
- GET /mercado/clusters - Clustering espacial de precios
- POST /mercado/valorizacion-hedonica - Cálculo modelo hedónico
- GET /mercado/oportunidades - Detectar oportunidades de inversión
- GET /mercado/proyeccion/{zona} - Proyecciones de mercado
- POST /mercado/reporte - Generar reporte completo
- GET /mercado/estadisticas - Estadísticas globales
- GET /mercado/comparar-zonas - Comparar múltiples zonas
- GET /mercado/tendencias - Tendencias históricas

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.ms_mercado_suelo import (
    ServicioMercadoSuelo,
    get_servicio_mercado,
    TipoPropiedad,
    TipoOperacion,
    PropiedadMercado,
    ClusterEspacial,
    AnalisisZona,
    ModeloHedonicoResultado,
    ProyeccionMercado,
    OportunidadInversion,
    ReporteMercado,
    SegmentoMercado,
    TendenciaMercado
)
from app.schemas.base import ResponseWrapper, ErrorResponse, PaginatedResponse


# =============================================================================
# CONFIGURACIÓN DEL ROUTER
# =============================================================================

router = APIRouter(
    prefix="/mercado",
    tags=["Mercado de Suelo"],
    responses={
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"},
        404: {"model": ErrorResponse, "description": "Recurso no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno"}
    }
)


# =============================================================================
# SCHEMAS DE REQUEST/RESPONSE
# =============================================================================

class FiltrosOferta(BaseModel):
    """Filtros para búsqueda de oferta"""
    comuna: Optional[str] = None
    region: str = "Metropolitana"
    tipo_propiedad: Optional[TipoPropiedad] = None
    operacion: TipoOperacion = TipoOperacion.VENTA
    precio_min_uf: Optional[float] = Field(None, ge=0)
    precio_max_uf: Optional[float] = Field(None, ge=0)
    superficie_min: Optional[float] = Field(None, ge=0)
    superficie_max: Optional[float] = Field(None, ge=0)
    dormitorios_min: Optional[int] = Field(None, ge=0)


class ValorizacionHedonicoRequest(BaseModel):
    """Request para valorización hedónica"""
    propiedad_id: str = Field(..., description="ID de la propiedad a valorar")
    incluir_comparables: bool = Field(True, description="Incluir lista de comparables")


class GenerarReporteRequest(BaseModel):
    """Request para generar reporte de mercado"""
    comunas: List[str] = Field(..., min_items=1, max_items=10)
    tipo_propiedad: Optional[TipoPropiedad] = None
    incluir_proyecciones: bool = True
    incluir_oportunidades: bool = True
    formato: str = Field("json", regex="^(json|pdf|xlsx)$")


class ComparacionZonasResponse(BaseModel):
    """Response de comparación de zonas"""
    zonas: List[AnalisisZona]
    resumen_comparativo: dict
    recomendacion: str


class TendenciaHistorica(BaseModel):
    """Tendencia histórica de precios"""
    fecha: date
    precio_m2_promedio: float
    variacion_mensual_pct: float
    volumen_transacciones: int


# =============================================================================
# DEPENDENCIAS
# =============================================================================

async def get_servicio() -> ServicioMercadoSuelo:
    """Dependencia para obtener servicio de mercado."""
    return get_servicio_mercado()


# =============================================================================
# ENDPOINTS DE OFERTA DE MERCADO
# =============================================================================

@router.get(
    "/oferta",
    response_model=ResponseWrapper[PaginatedResponse[PropiedadMercado]],
    summary="Obtener oferta del mercado",
    description="Busca propiedades disponibles en el mercado con filtros."
)
async def obtener_oferta(
    comuna: Optional[str] = Query(None, description="Filtrar por comuna"),
    region: str = Query("Metropolitana", description="Región"),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None, description="Tipo de propiedad"),
    operacion: TipoOperacion = Query(TipoOperacion.VENTA, description="Venta o arriendo"),
    precio_min_uf: Optional[float] = Query(None, ge=0, description="Precio mínimo UF"),
    precio_max_uf: Optional[float] = Query(None, ge=0, description="Precio máximo UF"),
    superficie_min: Optional[float] = Query(None, ge=0, description="Superficie mínima m²"),
    superficie_max: Optional[float] = Query(None, ge=0, description="Superficie máxima m²"),
    dormitorios_min: Optional[int] = Query(None, ge=0, description="Dormitorios mínimos"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Obtiene oferta actual del mercado inmobiliario.
    
    Fuentes: Portal Inmobiliario, Yapo, Toctoc, SII.
    """
    try:
        propiedades = await servicio.obtener_oferta_mercado(
            comuna=comuna,
            region=region,
            tipo_propiedad=tipo_propiedad,
            operacion=operacion,
            precio_min_uf=precio_min_uf,
            precio_max_uf=precio_max_uf,
            superficie_min=superficie_min,
            superficie_max=superficie_max,
            dormitorios_min=dormitorios_min,
            limite=page_size * page
        )
        
        # Paginación simple
        start = (page - 1) * page_size
        end = start + page_size
        pagina = propiedades[start:end]
        
        return ResponseWrapper(
            success=True,
            data=PaginatedResponse(
                items=pagina,
                total=len(propiedades),
                page=page,
                page_size=page_size,
                total_pages=(len(propiedades) + page_size - 1) // page_size
            ),
            message=f"{len(propiedades)} propiedades encontradas"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/oferta/{propiedad_id}",
    response_model=ResponseWrapper[PropiedadMercado],
    summary="Obtener propiedad específica",
    description="Obtiene detalles de una propiedad por su ID."
)
async def obtener_propiedad(
    propiedad_id: str,
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """Obtiene una propiedad específica del mercado."""
    # Mock - en producción buscaría en BD
    propiedades = await servicio.obtener_oferta_mercado(limite=100)
    
    for prop in propiedades:
        if prop.id == propiedad_id:
            return ResponseWrapper(
                success=True,
                data=prop,
                message="Propiedad encontrada"
            )
    
    raise HTTPException(status_code=404, detail="Propiedad no encontrada")


# =============================================================================
# ENDPOINTS DE ANÁLISIS DE ZONAS
# =============================================================================

@router.get(
    "/zona/{comuna}",
    response_model=ResponseWrapper[AnalisisZona],
    summary="Analizar zona",
    description="Análisis completo de una zona (comuna/sector)."
)
async def analizar_zona(
    comuna: str,
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    operacion: Optional[TipoOperacion] = Query(None),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Realiza análisis completo de una zona geográfica.
    
    Incluye:
    - Estadísticas de oferta
    - Precios promedio, mediana, rangos
    - Tendencias de variación
    - Indicadores de liquidez y absorción
    """
    try:
        propiedades = await servicio.obtener_oferta_mercado(
            comuna=comuna,
            tipo_propiedad=tipo_propiedad,
            limite=500
        )
        
        if not propiedades:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron propiedades en {comuna}"
            )
        
        if operacion:
            propiedades = [p for p in propiedades if p.operacion == operacion]
        
        analisis = await servicio.analizar_zona(propiedades, comuna, "comuna")
        
        return ResponseWrapper(
            success=True,
            data=analisis,
            message=f"Análisis de {comuna}: {len(propiedades)} propiedades"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/comparar-zonas",
    response_model=ResponseWrapper[ComparacionZonasResponse],
    summary="Comparar zonas",
    description="Compara métricas de múltiples zonas."
)
async def comparar_zonas(
    comunas: List[str] = Query(..., min_length=2, max_length=5),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Compara múltiples zonas geográficas.
    
    Incluye:
    - Análisis individual de cada zona
    - Tabla comparativa
    - Recomendación de inversión
    """
    try:
        zonas = []
        for comuna in comunas:
            propiedades = await servicio.obtener_oferta_mercado(
                comuna=comuna,
                tipo_propiedad=tipo_propiedad,
                limite=200
            )
            if propiedades:
                analisis = await servicio.analizar_zona(propiedades, comuna)
                zonas.append(analisis)
        
        if len(zonas) < 2:
            raise HTTPException(
                status_code=400,
                detail="Se requieren al menos 2 zonas con datos para comparar"
            )
        
        # Resumen comparativo
        import statistics
        precios = [z.precio_m2_mediana_venta for z in zonas]
        
        resumen = {
            "zona_mas_cara": max(zonas, key=lambda z: z.precio_m2_mediana_venta).nombre,
            "zona_mas_barata": min(zonas, key=lambda z: z.precio_m2_mediana_venta).nombre,
            "diferencia_precio_pct": round((max(precios) / min(precios) - 1) * 100, 1),
            "zona_mas_liquida": max(zonas, key=lambda z: z.indice_liquidez).nombre,
            "zona_mejor_cap_rate": max(zonas, key=lambda z: z.cap_rate_promedio).nombre,
            "promedio_precio_m2": round(statistics.mean(precios), 2)
        }
        
        # Recomendación
        mejor_zona = max(zonas, key=lambda z: z.indice_liquidez * (1/z.inventario_meses))
        recomendacion = f"Para inversión, se recomienda {mejor_zona.nombre} por su mejor equilibrio entre liquidez e inventario."
        
        return ResponseWrapper(
            success=True,
            data=ComparacionZonasResponse(
                zonas=zonas,
                resumen_comparativo=resumen,
                recomendacion=recomendacion
            ),
            message=f"Comparación de {len(zonas)} zonas"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE CLUSTERING ESPACIAL
# =============================================================================

@router.get(
    "/clusters",
    response_model=ResponseWrapper[List[ClusterEspacial]],
    summary="Clustering espacial",
    description="Identifica clusters de precios altos/bajos (hot/cold spots)."
)
async def obtener_clusters(
    comunas: List[str] = Query(None, description="Comunas a analizar"),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    metodo: str = Query("getis_ord", regex="^(getis_ord|lisa)$"),
    distancia_km: float = Query(1.0, ge=0.1, le=5.0),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Identifica clusters espaciales de precios.
    
    Métodos:
    - getis_ord: Getis-Ord Gi* (hot/cold spots)
    - lisa: Local Moran's I (clusters y outliers)
    
    Retorna zonas con precios significativamente altos o bajos.
    """
    try:
        propiedades = []
        if comunas:
            for comuna in comunas:
                props = await servicio.obtener_oferta_mercado(comuna=comuna, limite=100)
                propiedades.extend(props)
        else:
            propiedades = await servicio.obtener_oferta_mercado(limite=500)
        
        clusters = await servicio.analizar_clusters_espaciales(
            propiedades=propiedades,
            metodo=metodo,
            distancia_km=distancia_km
        )
        
        return ResponseWrapper(
            success=True,
            data=clusters,
            message=f"{len(clusters)} clusters identificados"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE MODELO HEDÓNICO
# =============================================================================

@router.post(
    "/valorizacion-hedonica",
    response_model=ResponseWrapper[ModeloHedonicoResultado],
    summary="Valorización hedónica",
    description="Calcula valor usando modelo hedónico de precios."
)
async def calcular_valor_hedonico(
    propiedad_id: str,
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Calcula valor de una propiedad usando modelo hedónico.
    
    Descompone el precio en:
    - Contribución de características físicas
    - Factor de ubicación
    - Factor de condición/antigüedad
    
    Retorna valor estimado con intervalo de confianza.
    """
    try:
        # Obtener propiedad
        propiedades = await servicio.obtener_oferta_mercado(limite=200)
        propiedad = None
        comparables = []
        
        for prop in propiedades:
            if prop.id == propiedad_id:
                propiedad = prop
            else:
                comparables.append(prop)
        
        if not propiedad:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        
        # Filtrar comparables por comuna y tipo
        comparables = [
            c for c in comparables 
            if c.comuna == propiedad.comuna and c.tipo == propiedad.tipo
        ]
        
        if len(comparables) < 5:
            # Ampliar a comunas cercanas
            comparables = [
                c for c in propiedades 
                if c.tipo == propiedad.tipo and c.id != propiedad_id
            ][:20]
        
        resultado = await servicio.calcular_valor_hedonico(propiedad, comparables)
        
        return ResponseWrapper(
            success=True,
            data=resultado,
            message=f"Valor estimado: {resultado.valor_estimado:,.0f} UF"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE OPORTUNIDADES
# =============================================================================

@router.get(
    "/oportunidades",
    response_model=ResponseWrapper[List[OportunidadInversion]],
    summary="Detectar oportunidades",
    description="Identifica oportunidades de inversión en el mercado."
)
async def detectar_oportunidades(
    comunas: List[str] = Query(None, description="Comunas a analizar"),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    umbral_descuento_pct: float = Query(10.0, ge=5, le=50),
    cap_rate_minimo: float = Query(5.0, ge=0, le=15),
    max_resultados: int = Query(20, ge=1, le=50),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Detecta oportunidades de inversión inmobiliaria.
    
    Criterios:
    - Descuento vs valor de mercado
    - Cap rate atractivo
    - Potencial de plusvalía
    - Tiempo en mercado
    
    Retorna lista ordenada por score de oportunidad.
    """
    try:
        propiedades = []
        if comunas:
            for comuna in comunas:
                props = await servicio.obtener_oferta_mercado(
                    comuna=comuna,
                    tipo_propiedad=tipo_propiedad,
                    limite=100
                )
                propiedades.extend(props)
        else:
            propiedades = await servicio.obtener_oferta_mercado(
                tipo_propiedad=tipo_propiedad,
                limite=500
            )
        
        oportunidades = await servicio.detectar_oportunidades(
            propiedades=propiedades,
            umbral_descuento_pct=umbral_descuento_pct,
            cap_rate_minimo=cap_rate_minimo
        )
        
        return ResponseWrapper(
            success=True,
            data=oportunidades[:max_resultados],
            message=f"{len(oportunidades)} oportunidades detectadas"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/oportunidades/{oportunidad_id}",
    response_model=ResponseWrapper[OportunidadInversion],
    summary="Detalle de oportunidad",
    description="Obtiene detalle completo de una oportunidad de inversión."
)
async def detalle_oportunidad(
    oportunidad_id: str,
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """Obtiene detalle de una oportunidad específica."""
    # En producción buscaría en BD/cache
    raise HTTPException(
        status_code=501,
        detail="Endpoint en desarrollo. Use /oportunidades para obtener lista."
    )


# =============================================================================
# ENDPOINTS DE PROYECCIONES
# =============================================================================

@router.get(
    "/proyeccion/{zona}",
    response_model=ResponseWrapper[ProyeccionMercado],
    summary="Proyección de mercado",
    description="Genera proyección de precios para una zona."
)
async def proyectar_mercado(
    zona: str,
    horizonte_meses: int = Query(12, ge=1, le=36),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Genera proyección de precios para una zona.
    
    Metodología:
    - Tendencia histórica (60%)
    - Factores macroeconómicos (25%)
    - Oferta/demanda local (15%)
    
    Incluye escenarios optimista/pesimista.
    """
    try:
        proyeccion = await servicio.proyectar_mercado(
            zona=zona,
            horizonte_meses=horizonte_meses,
            tipo_propiedad=tipo_propiedad
        )
        
        return ResponseWrapper(
            success=True,
            data=proyeccion,
            message=f"Proyección a {horizonte_meses} meses para {zona}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE REPORTES
# =============================================================================

@router.post(
    "/reporte",
    response_model=ResponseWrapper[ReporteMercado],
    summary="Generar reporte de mercado",
    description="Genera reporte completo de mercado para comunas seleccionadas."
)
async def generar_reporte(
    request: GenerarReporteRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Genera reporte completo de mercado.
    
    Incluye:
    - Análisis por zona
    - Clusters espaciales
    - Proyecciones
    - Oportunidades de inversión
    - Recomendaciones
    """
    try:
        reporte = await servicio.generar_reporte_mercado(
            comunas=request.comunas,
            tipo_propiedad=request.tipo_propiedad,
            incluir_proyecciones=request.incluir_proyecciones,
            incluir_oportunidades=request.incluir_oportunidades
        )
        
        # Si se solicita PDF/XLSX, generar en background
        if request.formato != "json":
            background_tasks.add_task(
                _generar_archivo_reporte,
                reporte.id,
                request.formato
            )
        
        return ResponseWrapper(
            success=True,
            data=reporte,
            message=f"Reporte generado: {reporte.id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _generar_archivo_reporte(reporte_id: str, formato: str):
    """Genera archivo de reporte en background."""
    # TODO: Implementar generación PDF/XLSX
    print(f"[BACKGROUND] Generando {formato} para reporte {reporte_id}")


# =============================================================================
# ENDPOINTS DE ESTADÍSTICAS
# =============================================================================

@router.get(
    "/estadisticas",
    response_model=ResponseWrapper[dict],
    summary="Estadísticas globales",
    description="Obtiene estadísticas globales del mercado."
)
async def obtener_estadisticas(
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Obtiene estadísticas globales del mercado.
    
    Incluye:
    - Total propiedades activas
    - Precios promedio venta/arriendo
    - Distribución por tipo
    - Top comunas
    """
    try:
        stats = await servicio.obtener_estadisticas_globales()
        
        return ResponseWrapper(
            success=True,
            data=stats,
            message="Estadísticas globales actualizadas"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tendencias/{comuna}",
    response_model=ResponseWrapper[List[TendenciaHistorica]],
    summary="Tendencias históricas",
    description="Obtiene tendencias históricas de precios de una comuna."
)
async def obtener_tendencias(
    comuna: str,
    meses: int = Query(12, ge=1, le=60),
    tipo_propiedad: Optional[TipoPropiedad] = Query(None),
    servicio: ServicioMercadoSuelo = Depends(get_servicio)
):
    """
    Obtiene serie histórica de precios.
    
    Incluye:
    - Precio promedio por mes
    - Variación mensual
    - Volumen de transacciones
    """
    try:
        # Mock de tendencias históricas
        from datetime import timedelta
        import random
        
        tendencias = []
        precio_base = 75.0
        
        for i in range(meses, 0, -1):
            fecha = date.today() - timedelta(days=i*30)
            variacion = random.uniform(-3, 5)
            precio_base *= (1 + variacion/100)
            
            tendencias.append(TendenciaHistorica(
                fecha=fecha,
                precio_m2_promedio=round(precio_base, 2),
                variacion_mensual_pct=round(variacion, 2),
                volumen_transacciones=random.randint(50, 200)
            ))
        
        return ResponseWrapper(
            success=True,
            data=tendencias,
            message=f"Tendencias de {meses} meses para {comuna}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS DE SEGMENTOS
# =============================================================================

@router.get(
    "/segmentos",
    response_model=ResponseWrapper[dict],
    summary="Definición de segmentos",
    description="Obtiene definición de segmentos de mercado."
)
async def obtener_segmentos():
    """Retorna definición de segmentos de mercado."""
    from app.services.ms_mercado_suelo import SEGMENTOS_PRECIO_UF_M2
    
    segmentos = {
        seg.value: {
            "nombre": seg.value.replace("_", " ").title(),
            "precio_min_uf_m2": rango[0],
            "precio_max_uf_m2": rango[1] if rango[1] != float('inf') else None,
            "descripcion": _descripcion_segmento(seg)
        }
        for seg, rango in SEGMENTOS_PRECIO_UF_M2.items()
    }
    
    return ResponseWrapper(
        success=True,
        data=segmentos,
        message=f"{len(segmentos)} segmentos definidos"
    )


def _descripcion_segmento(segmento: SegmentoMercado) -> str:
    """Retorna descripción de un segmento."""
    descripciones = {
        SegmentoMercado.ECONOMICO: "Viviendas económicas, generalmente subsidio estatal",
        SegmentoMercado.MEDIO_BAJO: "Primer hogar, sectores emergentes",
        SegmentoMercado.MEDIO: "Clase media consolidada, barrios tradicionales",
        SegmentoMercado.MEDIO_ALTO: "Profesionales, sectores bien conectados",
        SegmentoMercado.ALTO: "Ejecutivos, comunas premium",
        SegmentoMercado.PREMIUM: "Alto patrimonio, ubicaciones exclusivas",
        SegmentoMercado.LUJO: "Ultra lujo, propiedades excepcionales"
    }
    return descripciones.get(segmento, "")


# =============================================================================
# ENDPOINT DE SALUD
# =============================================================================

@router.get(
    "/health",
    response_model=dict,
    summary="Health check",
    include_in_schema=False
)
async def health_check():
    """Health check del servicio de mercado."""
    return {
        "status": "healthy",
        "service": "mercado_suelo",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0"
    }
