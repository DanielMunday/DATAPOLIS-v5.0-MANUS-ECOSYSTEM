"""
DATAPOLIS v3.0 - Router M17 GIRES (GIS Real Estate Services)
============================================================
API REST para integración geoespacial con ArcGIS/Esri.

Endpoints:
- Geocodificación directa e inversa
- Análisis de proximidad y accesibilidad
- Capas temáticas (riesgo, zonificación, servicios)
- Análisis territoriales avanzados
- Integración con Feature Services Esri

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2025
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
import io

# ============================================================================
# CONFIGURACIÓN DEL ROUTER
# ============================================================================

router = APIRouter(
    prefix="/gires",
    tags=["M17 - GIRES (GIS Real Estate Services)"],
    responses={
        400: {"description": "Parámetros inválidos"},
        404: {"description": "Recurso no encontrado"},
        500: {"description": "Error interno del servidor"},
        503: {"description": "Servicio ArcGIS no disponible"}
    }
)

# ============================================================================
# ENUMS Y MODELOS
# ============================================================================

class TipoGeometria(str, Enum):
    """Tipos de geometría soportados"""
    POINT = "point"
    POLYGON = "polygon"
    POLYLINE = "polyline"
    MULTIPOINT = "multipoint"
    ENVELOPE = "envelope"

class SistemaReferencia(str, Enum):
    """Sistemas de referencia espacial"""
    WGS84 = "4326"
    UTM19S = "32719"
    SIRGAS = "4674"
    PSAD56 = "24879"

class TipoAnalisis(str, Enum):
    """Tipos de análisis territorial"""
    PROXIMIDAD = "proximidad"
    ACCESIBILIDAD = "accesibilidad"
    ISOCRONAS = "isocronas"
    CUENCA_VISUAL = "cuenca_visual"
    DENSIDAD = "densidad"
    INTERPOLACION = "interpolacion"

class CapaTematica(str, Enum):
    """Capas temáticas disponibles"""
    RIESGO_INUNDACION = "riesgo_inundacion"
    RIESGO_REMOCION = "riesgo_remocion"
    RIESGO_SISMICO = "riesgo_sismico"
    RIESGO_TSUNAMI = "riesgo_tsunami"
    ZONIFICACION_PRC = "zonificacion_prc"
    USO_SUELO = "uso_suelo"
    AREAS_VERDES = "areas_verdes"
    EQUIPAMIENTO = "equipamiento"
    TRANSPORTE = "transporte"
    SERVICIOS_BASICOS = "servicios_basicos"
    VALOR_SUELO = "valor_suelo"
    DENSIDAD_POBLACIONAL = "densidad_poblacional"

class TipoServicio(str, Enum):
    """Tipos de servicios para análisis de proximidad"""
    METRO = "metro"
    BUS = "bus"
    SALUD = "salud"
    EDUCACION = "educacion"
    COMERCIO = "comercio"
    SEGURIDAD = "seguridad"
    AREAS_VERDES = "areas_verdes"
    CULTURA = "cultura"
    DEPORTE = "deporte"
    FINANCIERO = "financiero"

class ModoTransporte(str, Enum):
    """Modos de transporte para análisis"""
    CAMINANDO = "walking"
    BICICLETA = "cycling"
    AUTO = "driving"
    TRANSPORTE_PUBLICO = "transit"

class FormatoExportacion(str, Enum):
    """Formatos de exportación geoespacial"""
    GEOJSON = "geojson"
    KML = "kml"
    SHAPEFILE = "shp"
    GEOPACKAGE = "gpkg"
    CSV = "csv"

# ============================================================================
# MODELOS PYDANTIC - REQUEST
# ============================================================================

class CoordenadaRequest(BaseModel):
    """Coordenada geográfica"""
    latitud: float = Field(..., ge=-90, le=90, description="Latitud WGS84")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud WGS84")
    altitud: Optional[float] = Field(None, description="Altitud en metros")

class DireccionRequest(BaseModel):
    """Dirección para geocodificación"""
    calle: str = Field(..., min_length=3, max_length=200)
    numero: Optional[str] = Field(None, max_length=20)
    comuna: str = Field(..., min_length=3, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    pais: str = Field(default="Chile")

class BoundingBoxRequest(BaseModel):
    """Bounding box para consultas espaciales"""
    min_lat: float = Field(..., ge=-90, le=90)
    min_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    
    @validator('max_lat')
    def validar_latitudes(cls, v, values):
        if 'min_lat' in values and v <= values['min_lat']:
            raise ValueError('max_lat debe ser mayor que min_lat')
        return v
    
    @validator('max_lon')
    def validar_longitudes(cls, v, values):
        if 'min_lon' in values and v <= values['min_lon']:
            raise ValueError('max_lon debe ser mayor que min_lon')
        return v

class PoligonoRequest(BaseModel):
    """Polígono para análisis espacial"""
    tipo: TipoGeometria = Field(default=TipoGeometria.POLYGON)
    coordenadas: List[List[float]] = Field(..., min_items=3)
    srid: SistemaReferencia = Field(default=SistemaReferencia.WGS84)

class AnalisisProximidadRequest(BaseModel):
    """Request para análisis de proximidad"""
    ubicacion: CoordenadaRequest
    tipos_servicio: List[TipoServicio] = Field(..., min_items=1, max_items=10)
    radio_metros: int = Field(default=1000, ge=100, le=10000)
    max_resultados_por_tipo: int = Field(default=5, ge=1, le=20)
    incluir_tiempo_viaje: bool = Field(default=True)
    modo_transporte: ModoTransporte = Field(default=ModoTransporte.CAMINANDO)

class AnalisisIsochronaRequest(BaseModel):
    """Request para análisis de isócronas"""
    ubicacion: CoordenadaRequest
    tiempos_minutos: List[int] = Field(default=[5, 10, 15, 20], min_items=1, max_items=6)
    modo_transporte: ModoTransporte = Field(default=ModoTransporte.CAMINANDO)
    hora_partida: Optional[datetime] = Field(None, description="Hora para análisis con TP")
    incluir_estadisticas: bool = Field(default=True)

class AnalisisAccesibilidadRequest(BaseModel):
    """Request para análisis de accesibilidad"""
    ubicacion: CoordenadaRequest
    destinos: List[CoordenadaRequest] = Field(..., min_items=1, max_items=50)
    modo_transporte: ModoTransporte = Field(default=ModoTransporte.AUTO)
    hora_partida: Optional[datetime] = None
    calcular_alternativas: bool = Field(default=False)

class ConsultaCapaRequest(BaseModel):
    """Request para consulta de capa temática"""
    capa: CapaTematica
    geometria: Optional[PoligonoRequest] = None
    bbox: Optional[BoundingBoxRequest] = None
    where: Optional[str] = Field(None, max_length=500, description="Filtro SQL")
    campos: Optional[List[str]] = Field(None, description="Campos a retornar")
    max_registros: int = Field(default=1000, ge=1, le=10000)

class AnalisisZonificacionRequest(BaseModel):
    """Request para análisis de zonificación"""
    ubicacion: CoordenadaRequest
    incluir_normativa: bool = Field(default=True)
    incluir_usos_permitidos: bool = Field(default=True)
    incluir_parametros_edificacion: bool = Field(default=True)
    radio_contexto_metros: int = Field(default=500, ge=100, le=2000)

class AnalisisRiesgosRequest(BaseModel):
    """Request para análisis de riesgos territoriales"""
    ubicacion: CoordenadaRequest
    tipos_riesgo: Optional[List[str]] = Field(
        None, 
        description="Tipos específicos o None para todos"
    )
    incluir_mitigaciones: bool = Field(default=True)
    incluir_historico: bool = Field(default=False)
    radio_analisis_metros: int = Field(default=1000, ge=100, le=5000)

class ExportacionRequest(BaseModel):
    """Request para exportación de datos geoespaciales"""
    geometrias: List[Dict[str, Any]]
    formato: FormatoExportacion = Field(default=FormatoExportacion.GEOJSON)
    srid_salida: SistemaReferencia = Field(default=SistemaReferencia.WGS84)
    incluir_atributos: bool = Field(default=True)
    simplificar_tolerancia: Optional[float] = Field(None, ge=0, le=100)

# ============================================================================
# MODELOS PYDANTIC - RESPONSE
# ============================================================================

class GeocodificacionResponse(BaseModel):
    """Respuesta de geocodificación"""
    direccion_normalizada: str
    coordenadas: CoordenadaRequest
    precision: str
    score_confianza: float = Field(ge=0, le=100)
    fuente: str
    metadata: Dict[str, Any] = {}

class ProximidadResultado(BaseModel):
    """Resultado individual de proximidad"""
    nombre: str
    tipo: TipoServicio
    coordenadas: CoordenadaRequest
    distancia_metros: float
    tiempo_minutos: Optional[float]
    direccion: Optional[str]
    atributos: Dict[str, Any] = {}

class AnalisisProximidadResponse(BaseModel):
    """Respuesta de análisis de proximidad"""
    ubicacion_analisis: CoordenadaRequest
    radio_metros: int
    total_servicios: int
    servicios_por_tipo: Dict[str, int]
    resultados: List[ProximidadResultado]
    score_accesibilidad: float = Field(ge=0, le=100)
    timestamp: datetime

class IsochronaResponse(BaseModel):
    """Respuesta de análisis de isócronas"""
    ubicacion_origen: CoordenadaRequest
    modo_transporte: ModoTransporte
    isocronas: List[Dict[str, Any]]
    estadisticas: Optional[Dict[str, Any]]
    area_total_km2: float
    timestamp: datetime

class ZonificacionResponse(BaseModel):
    """Respuesta de análisis de zonificación"""
    ubicacion: CoordenadaRequest
    zona_prc: str
    nombre_zona: str
    usos_permitidos: List[str]
    usos_prohibidos: List[str]
    parametros_edificacion: Dict[str, Any]
    normativa_aplicable: List[Dict[str, str]]
    observaciones: List[str]
    timestamp: datetime

class RiesgoTerritorial(BaseModel):
    """Riesgo territorial individual"""
    tipo: str
    nivel: str
    probabilidad: float
    impacto_potencial: str
    descripcion: str
    fuente_dato: str
    fecha_actualizacion: date
    mitigaciones: Optional[List[str]]

class AnalisisRiesgosResponse(BaseModel):
    """Respuesta de análisis de riesgos"""
    ubicacion: CoordenadaRequest
    nivel_riesgo_global: str
    score_riesgo: float = Field(ge=0, le=100)
    riesgos: List[RiesgoTerritorial]
    recomendaciones: List[str]
    timestamp: datetime

class CapaResponse(BaseModel):
    """Respuesta de consulta de capa"""
    capa: CapaTematica
    total_registros: int
    features: List[Dict[str, Any]]
    bbox: Optional[List[float]]
    srid: str
    timestamp: datetime

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

# Importación lazy del servicio
_servicio_gires = None

async def get_servicio_gires():
    """Obtener instancia del servicio GIRES"""
    global _servicio_gires
    if _servicio_gires is None:
        try:
            from app.services.m17_gires import ServicioGIRES
            _servicio_gires = ServicioGIRES()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Servicio GIRES no disponible"
            )
    return _servicio_gires

# ============================================================================
# ENDPOINTS - GEOCODIFICACIÓN
# ============================================================================

@router.post(
    "/geocodificar",
    response_model=GeocodificacionResponse,
    summary="Geocodificar dirección",
    description="Convierte una dirección textual en coordenadas geográficas"
)
async def geocodificar_direccion(
    request: DireccionRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Geocodificación directa de dirección a coordenadas.
    
    Utiliza múltiples fuentes:
    - ArcGIS World Geocoder
    - API IDE Chile
    - OpenStreetMap Nominatim
    """
    try:
        resultado = await servicio.geocodificar(
            calle=request.calle,
            numero=request.numero,
            comuna=request.comuna,
            region=request.region,
            pais=request.pais
        )
        return GeocodificacionResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en geocodificación: {str(e)}")

@router.post(
    "/geocodificar/inversa",
    response_model=GeocodificacionResponse,
    summary="Geocodificación inversa",
    description="Convierte coordenadas en dirección textual"
)
async def geocodificar_inversa(
    coordenadas: CoordenadaRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Geocodificación inversa de coordenadas a dirección.
    
    Retorna la dirección más cercana y su nivel de precisión.
    """
    try:
        resultado = await servicio.geocodificar_inversa(
            latitud=coordenadas.latitud,
            longitud=coordenadas.longitud
        )
        return GeocodificacionResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en geocodificación inversa: {str(e)}")

@router.post(
    "/geocodificar/batch",
    response_model=List[GeocodificacionResponse],
    summary="Geocodificación masiva",
    description="Geocodifica múltiples direcciones en una sola llamada"
)
async def geocodificar_batch(
    direcciones: List[DireccionRequest] = Body(..., max_items=100),
    servicio = Depends(get_servicio_gires)
):
    """
    Geocodificación masiva de hasta 100 direcciones.
    
    Optimizado para procesamiento paralelo.
    """
    try:
        resultados = await servicio.geocodificar_batch(
            direcciones=[d.dict() for d in direcciones]
        )
        return [GeocodificacionResponse(**r) for r in resultados]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en geocodificación batch: {str(e)}")

# ============================================================================
# ENDPOINTS - ANÁLISIS DE PROXIMIDAD
# ============================================================================

@router.post(
    "/proximidad/analizar",
    response_model=AnalisisProximidadResponse,
    summary="Análisis de proximidad",
    description="Analiza servicios cercanos a una ubicación"
)
async def analizar_proximidad(
    request: AnalisisProximidadRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Análisis de proximidad a servicios urbanos.
    
    Calcula:
    - Servicios más cercanos por tipo
    - Distancia y tiempo de viaje
    - Score de accesibilidad agregado
    """
    try:
        resultado = await servicio.analizar_proximidad(
            latitud=request.ubicacion.latitud,
            longitud=request.ubicacion.longitud,
            tipos_servicio=[t.value for t in request.tipos_servicio],
            radio_metros=request.radio_metros,
            max_resultados=request.max_resultados_por_tipo,
            incluir_tiempo=request.incluir_tiempo_viaje,
            modo_transporte=request.modo_transporte.value
        )
        return AnalisisProximidadResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de proximidad: {str(e)}")

@router.get(
    "/proximidad/servicios/{rol_sii}",
    response_model=AnalisisProximidadResponse,
    summary="Proximidad por ROL SII",
    description="Análisis de proximidad para propiedad identificada por ROL"
)
async def proximidad_por_rol(
    rol_sii: str = Path(..., regex=r"^\d+-\d+$"),
    tipos_servicio: List[TipoServicio] = Query(
        default=[TipoServicio.METRO, TipoServicio.SALUD, TipoServicio.EDUCACION]
    ),
    radio_metros: int = Query(default=1000, ge=100, le=5000),
    servicio = Depends(get_servicio_gires)
):
    """
    Análisis de proximidad automático para una propiedad.
    
    Obtiene coordenadas del ROL y ejecuta análisis completo.
    """
    try:
        resultado = await servicio.proximidad_por_rol(
            rol_sii=rol_sii,
            tipos_servicio=[t.value for t in tipos_servicio],
            radio_metros=radio_metros
        )
        return AnalisisProximidadResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis por ROL: {str(e)}")

@router.get(
    "/proximidad/tipos-servicio",
    response_model=List[Dict[str, Any]],
    summary="Tipos de servicio disponibles",
    description="Lista todos los tipos de servicio para análisis de proximidad"
)
async def listar_tipos_servicio():
    """
    Catálogo de tipos de servicio disponibles para análisis.
    """
    tipos = [
        {
            "codigo": TipoServicio.METRO.value,
            "nombre": "Estaciones de Metro",
            "icono": "subway",
            "categoria": "transporte"
        },
        {
            "codigo": TipoServicio.BUS.value,
            "nombre": "Paraderos de Bus",
            "icono": "bus",
            "categoria": "transporte"
        },
        {
            "codigo": TipoServicio.SALUD.value,
            "nombre": "Centros de Salud",
            "icono": "hospital",
            "categoria": "servicios_basicos"
        },
        {
            "codigo": TipoServicio.EDUCACION.value,
            "nombre": "Establecimientos Educacionales",
            "icono": "school",
            "categoria": "servicios_basicos"
        },
        {
            "codigo": TipoServicio.COMERCIO.value,
            "nombre": "Centros Comerciales",
            "icono": "shopping_cart",
            "categoria": "comercio"
        },
        {
            "codigo": TipoServicio.SEGURIDAD.value,
            "nombre": "Comisarías y Bomberos",
            "icono": "shield",
            "categoria": "seguridad"
        },
        {
            "codigo": TipoServicio.AREAS_VERDES.value,
            "nombre": "Parques y Plazas",
            "icono": "park",
            "categoria": "recreacion"
        },
        {
            "codigo": TipoServicio.CULTURA.value,
            "nombre": "Centros Culturales",
            "icono": "theater_masks",
            "categoria": "cultura"
        },
        {
            "codigo": TipoServicio.DEPORTE.value,
            "nombre": "Recintos Deportivos",
            "icono": "sports",
            "categoria": "recreacion"
        },
        {
            "codigo": TipoServicio.FINANCIERO.value,
            "nombre": "Bancos y Cajeros",
            "icono": "account_balance",
            "categoria": "servicios"
        }
    ]
    return tipos

# ============================================================================
# ENDPOINTS - ISÓCRONAS Y ACCESIBILIDAD
# ============================================================================

@router.post(
    "/isocronas/generar",
    response_model=IsochronaResponse,
    summary="Generar isócronas",
    description="Genera polígonos de tiempo de viaje desde una ubicación"
)
async def generar_isocronas(
    request: AnalisisIsochronaRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Generación de isócronas de accesibilidad.
    
    Crea polígonos representando áreas alcanzables en los
    tiempos especificados según modo de transporte.
    """
    try:
        resultado = await servicio.generar_isocronas(
            latitud=request.ubicacion.latitud,
            longitud=request.ubicacion.longitud,
            tiempos_minutos=request.tiempos_minutos,
            modo_transporte=request.modo_transporte.value,
            hora_partida=request.hora_partida,
            incluir_estadisticas=request.incluir_estadisticas
        )
        return IsochronaResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando isócronas: {str(e)}")

@router.post(
    "/accesibilidad/matriz",
    summary="Matriz de accesibilidad",
    description="Calcula tiempos/distancias entre múltiples orígenes y destinos"
)
async def calcular_matriz_accesibilidad(
    request: AnalisisAccesibilidadRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Matriz origen-destino de tiempos y distancias.
    
    Útil para:
    - Análisis de conectividad
    - Optimización de rutas
    - Estudios de accesibilidad urbana
    """
    try:
        resultado = await servicio.calcular_matriz_od(
            origen={
                "latitud": request.ubicacion.latitud,
                "longitud": request.ubicacion.longitud
            },
            destinos=[
                {"latitud": d.latitud, "longitud": d.longitud}
                for d in request.destinos
            ],
            modo_transporte=request.modo_transporte.value,
            hora_partida=request.hora_partida,
            alternativas=request.calcular_alternativas
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en matriz OD: {str(e)}")

@router.get(
    "/accesibilidad/score/{rol_sii}",
    summary="Score de accesibilidad",
    description="Calcula score de accesibilidad para una propiedad"
)
async def score_accesibilidad(
    rol_sii: str = Path(..., regex=r"^\d+-\d+$"),
    ponderaciones: Optional[Dict[str, float]] = None,
    servicio = Depends(get_servicio_gires)
):
    """
    Score compuesto de accesibilidad 0-100.
    
    Considera:
    - Transporte público (40%)
    - Servicios básicos (30%)
    - Comercio y equipamiento (20%)
    - Áreas verdes (10%)
    """
    try:
        resultado = await servicio.calcular_score_accesibilidad(
            rol_sii=rol_sii,
            ponderaciones=ponderaciones
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando score: {str(e)}")

# ============================================================================
# ENDPOINTS - ZONIFICACIÓN Y NORMATIVA
# ============================================================================

@router.post(
    "/zonificacion/analizar",
    response_model=ZonificacionResponse,
    summary="Análisis de zonificación",
    description="Analiza zonificación PRC y normativa aplicable"
)
async def analizar_zonificacion(
    request: AnalisisZonificacionRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Análisis completo de zonificación territorial.
    
    Retorna:
    - Zona PRC (Plan Regulador Comunal)
    - Usos permitidos y prohibidos
    - Parámetros de edificación
    - Normativa aplicable
    """
    try:
        resultado = await servicio.analizar_zonificacion(
            latitud=request.ubicacion.latitud,
            longitud=request.ubicacion.longitud,
            incluir_normativa=request.incluir_normativa,
            incluir_usos=request.incluir_usos_permitidos,
            incluir_parametros=request.incluir_parametros_edificacion,
            radio_contexto=request.radio_contexto_metros
        )
        return ZonificacionResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis zonificación: {str(e)}")

@router.get(
    "/zonificacion/{rol_sii}",
    response_model=ZonificacionResponse,
    summary="Zonificación por ROL",
    description="Obtiene zonificación para propiedad identificada por ROL"
)
async def zonificacion_por_rol(
    rol_sii: str = Path(..., regex=r"^\d+-\d+$"),
    servicio = Depends(get_servicio_gires)
):
    """
    Consulta rápida de zonificación por ROL SII.
    """
    try:
        resultado = await servicio.zonificacion_por_rol(rol_sii=rol_sii)
        return ZonificacionResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando zonificación: {str(e)}")

@router.get(
    "/zonificacion/zonas/{comuna}",
    summary="Zonas PRC de comuna",
    description="Lista todas las zonas del Plan Regulador Comunal"
)
async def listar_zonas_prc(
    comuna: str = Path(..., min_length=3, max_length=100),
    servicio = Depends(get_servicio_gires)
):
    """
    Catálogo de zonas del PRC de una comuna.
    """
    try:
        resultado = await servicio.listar_zonas_prc(comuna=comuna)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando zonas: {str(e)}")

# ============================================================================
# ENDPOINTS - ANÁLISIS DE RIESGOS
# ============================================================================

@router.post(
    "/riesgos/analizar",
    response_model=AnalisisRiesgosResponse,
    summary="Análisis de riesgos territoriales",
    description="Evalúa riesgos naturales y antrópicos en una ubicación"
)
async def analizar_riesgos(
    request: AnalisisRiesgosRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Análisis integral de riesgos territoriales.
    
    Evalúa:
    - Riesgo sísmico (fallas, licuefacción)
    - Riesgo de inundación
    - Riesgo de remoción en masa
    - Riesgo de tsunami
    - Riesgos antrópicos (contaminación, ruido)
    """
    try:
        resultado = await servicio.analizar_riesgos(
            latitud=request.ubicacion.latitud,
            longitud=request.ubicacion.longitud,
            tipos_riesgo=request.tipos_riesgo,
            incluir_mitigaciones=request.incluir_mitigaciones,
            incluir_historico=request.incluir_historico,
            radio_metros=request.radio_analisis_metros
        )
        return AnalisisRiesgosResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de riesgos: {str(e)}")

@router.get(
    "/riesgos/{rol_sii}",
    response_model=AnalisisRiesgosResponse,
    summary="Riesgos por ROL",
    description="Análisis de riesgos para propiedad identificada por ROL"
)
async def riesgos_por_rol(
    rol_sii: str = Path(..., regex=r"^\d+-\d+$"),
    servicio = Depends(get_servicio_gires)
):
    """
    Análisis de riesgos automático para una propiedad.
    """
    try:
        resultado = await servicio.riesgos_por_rol(rol_sii=rol_sii)
        return AnalisisRiesgosResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando riesgos: {str(e)}")

@router.get(
    "/riesgos/tipos",
    summary="Tipos de riesgo",
    description="Catálogo de tipos de riesgo evaluados"
)
async def listar_tipos_riesgo():
    """
    Catálogo de tipos de riesgo territorial.
    """
    tipos = [
        {
            "codigo": "sismico",
            "nombre": "Riesgo Sísmico",
            "descripcion": "Evaluación de amenaza sísmica, fallas activas y licuefacción",
            "fuentes": ["CSN", "SHOA", "SERNAGEOMIN"]
        },
        {
            "codigo": "inundacion",
            "nombre": "Riesgo de Inundación",
            "descripcion": "Zonas inundables, cauces, napas freáticas",
            "fuentes": ["DGA", "MOP", "CONAF"]
        },
        {
            "codigo": "remocion",
            "nombre": "Riesgo de Remoción en Masa",
            "descripcion": "Deslizamientos, aluviones, derrumbes",
            "fuentes": ["SERNAGEOMIN", "MOP"]
        },
        {
            "codigo": "tsunami",
            "nombre": "Riesgo de Tsunami",
            "descripcion": "Zonas de inundación por tsunami",
            "fuentes": ["SHOA", "ONEMI"]
        },
        {
            "codigo": "volcanico",
            "nombre": "Riesgo Volcánico",
            "descripcion": "Zonas de influencia volcánica",
            "fuentes": ["SERNAGEOMIN", "OVDAS"]
        },
        {
            "codigo": "incendio",
            "nombre": "Riesgo de Incendio Forestal",
            "descripcion": "Interfaz urbano-forestal",
            "fuentes": ["CONAF", "SAF"]
        },
        {
            "codigo": "contaminacion",
            "nombre": "Riesgo de Contaminación",
            "descripcion": "Sitios contaminados, PRAS, áreas industriales",
            "fuentes": ["SMA", "SEA", "MINSAL"]
        }
    ]
    return tipos

# ============================================================================
# ENDPOINTS - CAPAS TEMÁTICAS
# ============================================================================

@router.post(
    "/capas/consultar",
    response_model=CapaResponse,
    summary="Consultar capa temática",
    description="Consulta datos de una capa temática con filtros espaciales"
)
async def consultar_capa(
    request: ConsultaCapaRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Consulta flexible de capas temáticas.
    
    Soporta:
    - Filtro por bounding box
    - Filtro por polígono
    - Filtro por atributos (WHERE)
    """
    try:
        resultado = await servicio.consultar_capa(
            capa=request.capa.value,
            geometria=request.geometria.dict() if request.geometria else None,
            bbox=request.bbox.dict() if request.bbox else None,
            where=request.where,
            campos=request.campos,
            max_registros=request.max_registros
        )
        return CapaResponse(**resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando capa: {str(e)}")

@router.get(
    "/capas/disponibles",
    summary="Capas disponibles",
    description="Lista todas las capas temáticas disponibles"
)
async def listar_capas():
    """
    Catálogo de capas temáticas disponibles.
    """
    capas = [
        {
            "codigo": CapaTematica.RIESGO_INUNDACION.value,
            "nombre": "Zonas de Riesgo de Inundación",
            "descripcion": "Áreas con riesgo de inundación fluvial y pluvial",
            "fuente": "DGA/MOP",
            "actualizacion": "Anual"
        },
        {
            "codigo": CapaTematica.RIESGO_REMOCION.value,
            "nombre": "Zonas de Remoción en Masa",
            "descripcion": "Áreas susceptibles a deslizamientos",
            "fuente": "SERNAGEOMIN",
            "actualizacion": "Anual"
        },
        {
            "codigo": CapaTematica.ZONIFICACION_PRC.value,
            "nombre": "Zonificación PRC",
            "descripcion": "Zonas de los Planes Reguladores Comunales",
            "fuente": "Municipalidades/MINVU",
            "actualizacion": "Variable"
        },
        {
            "codigo": CapaTematica.USO_SUELO.value,
            "nombre": "Uso de Suelo",
            "descripcion": "Clasificación de uso de suelo actual",
            "fuente": "IDE Chile",
            "actualizacion": "Anual"
        },
        {
            "codigo": CapaTematica.AREAS_VERDES.value,
            "nombre": "Áreas Verdes",
            "descripcion": "Parques, plazas y espacios verdes públicos",
            "fuente": "Municipalidades",
            "actualizacion": "Semestral"
        },
        {
            "codigo": CapaTematica.TRANSPORTE.value,
            "nombre": "Red de Transporte",
            "descripcion": "Metro, buses, ciclovías",
            "fuente": "MTT/Metro",
            "actualizacion": "Mensual"
        },
        {
            "codigo": CapaTematica.VALOR_SUELO.value,
            "nombre": "Valor de Suelo",
            "descripcion": "Valores de referencia por zona",
            "fuente": "SII/Análisis propio",
            "actualizacion": "Trimestral"
        }
    ]
    return capas

@router.get(
    "/capas/{capa}/metadata",
    summary="Metadata de capa",
    description="Obtiene metadata detallada de una capa"
)
async def metadata_capa(
    capa: CapaTematica = Path(...),
    servicio = Depends(get_servicio_gires)
):
    """
    Metadata completa de una capa temática.
    """
    try:
        resultado = await servicio.obtener_metadata_capa(capa=capa.value)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo metadata: {str(e)}")

# ============================================================================
# ENDPOINTS - EXPORTACIÓN
# ============================================================================

@router.post(
    "/exportar",
    summary="Exportar datos geoespaciales",
    description="Exporta geometrías a diversos formatos"
)
async def exportar_datos(
    request: ExportacionRequest,
    servicio = Depends(get_servicio_gires)
):
    """
    Exportación de datos a formatos geoespaciales.
    
    Formatos soportados:
    - GeoJSON
    - KML
    - Shapefile (ZIP)
    - GeoPackage
    - CSV (con WKT)
    """
    try:
        contenido, filename, media_type = await servicio.exportar(
            geometrias=request.geometrias,
            formato=request.formato.value,
            srid=request.srid_salida.value,
            incluir_atributos=request.incluir_atributos,
            simplificar=request.simplificar_tolerancia
        )
        
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en exportación: {str(e)}")

@router.get(
    "/exportar/formatos",
    summary="Formatos de exportación",
    description="Lista formatos de exportación disponibles"
)
async def listar_formatos_exportacion():
    """
    Formatos de exportación soportados.
    """
    formatos = [
        {
            "codigo": FormatoExportacion.GEOJSON.value,
            "nombre": "GeoJSON",
            "extension": ".geojson",
            "mime_type": "application/geo+json",
            "descripcion": "Formato estándar web para datos geoespaciales"
        },
        {
            "codigo": FormatoExportacion.KML.value,
            "nombre": "KML",
            "extension": ".kml",
            "mime_type": "application/vnd.google-earth.kml+xml",
            "descripcion": "Formato Google Earth"
        },
        {
            "codigo": FormatoExportacion.SHAPEFILE.value,
            "nombre": "Shapefile",
            "extension": ".zip",
            "mime_type": "application/zip",
            "descripcion": "Formato Esri (comprimido)"
        },
        {
            "codigo": FormatoExportacion.GEOPACKAGE.value,
            "nombre": "GeoPackage",
            "extension": ".gpkg",
            "mime_type": "application/geopackage+sqlite3",
            "descripcion": "Formato OGC moderno"
        },
        {
            "codigo": FormatoExportacion.CSV.value,
            "nombre": "CSV con WKT",
            "extension": ".csv",
            "mime_type": "text/csv",
            "descripcion": "CSV con geometría en formato WKT"
        }
    ]
    return formatos

# ============================================================================
# ENDPOINTS - UTILIDADES
# ============================================================================

@router.post(
    "/transformar-coordenadas",
    summary="Transformar coordenadas",
    description="Transforma coordenadas entre sistemas de referencia"
)
async def transformar_coordenadas(
    coordenadas: CoordenadaRequest,
    srid_origen: SistemaReferencia = Query(default=SistemaReferencia.WGS84),
    srid_destino: SistemaReferencia = Query(...),
    servicio = Depends(get_servicio_gires)
):
    """
    Transformación de coordenadas entre SRID.
    """
    try:
        resultado = await servicio.transformar_coordenadas(
            latitud=coordenadas.latitud,
            longitud=coordenadas.longitud,
            srid_origen=srid_origen.value,
            srid_destino=srid_destino.value
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en transformación: {str(e)}")

@router.get(
    "/sistemas-referencia",
    summary="Sistemas de referencia",
    description="Lista sistemas de referencia espacial soportados"
)
async def listar_sistemas_referencia():
    """
    Catálogo de sistemas de referencia espacial.
    """
    sistemas = [
        {
            "codigo": SistemaReferencia.WGS84.value,
            "nombre": "WGS 84",
            "descripcion": "Sistema global GPS",
            "unidades": "grados",
            "uso": "Estándar web, GPS"
        },
        {
            "codigo": SistemaReferencia.UTM19S.value,
            "nombre": "UTM Zona 19S",
            "descripcion": "Proyección UTM para Chile central",
            "unidades": "metros",
            "uso": "Cartografía técnica Chile"
        },
        {
            "codigo": SistemaReferencia.SIRGAS.value,
            "nombre": "SIRGAS-Chile",
            "descripcion": "Sistema oficial de Chile",
            "unidades": "grados",
            "uso": "Cartografía oficial"
        },
        {
            "codigo": SistemaReferencia.PSAD56.value,
            "nombre": "PSAD 56",
            "descripcion": "Sistema antiguo (legacy)",
            "unidades": "grados",
            "uso": "Documentos históricos"
        }
    ]
    return sistemas

@router.get(
    "/validar-geometria",
    summary="Validar geometría",
    description="Valida si una geometría es correcta"
)
async def validar_geometria(
    wkt: str = Query(..., description="Geometría en formato WKT"),
    servicio = Depends(get_servicio_gires)
):
    """
    Validación de geometría WKT.
    
    Verifica:
    - Sintaxis correcta
    - Geometría válida (no auto-intersecciones)
    - Orientación correcta
    """
    try:
        resultado = await servicio.validar_geometria(wkt=wkt)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validando geometría: {str(e)}")

@router.get(
    "/health",
    summary="Estado del servicio GIRES",
    description="Verifica conectividad con servicios geoespaciales"
)
async def health_check(servicio = Depends(get_servicio_gires)):
    """
    Health check del módulo GIRES.
    
    Verifica conectividad con:
    - ArcGIS Online
    - IDE Chile
    - PostgreSQL/PostGIS
    """
    try:
        estado = await servicio.health_check()
        return {
            "status": "healthy" if estado["all_ok"] else "degraded",
            "servicios": estado["servicios"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
