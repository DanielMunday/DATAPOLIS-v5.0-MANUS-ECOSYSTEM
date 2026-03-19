# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Servicio M17: GIRES (Gestión Integrada de Recursos Espaciales)
================================================================================
Integración avanzada con Esri ArcGIS para análisis geoespacial de inteligencia territorial.

Funcionalidades:
- ArcGIS REST API integration
- Feature services (query, edit, analyze)
- Geoprocessing services
- Geocoding (Chile optimizado)
- Routing y análisis de red
- Spatial analysis
- Map services y tiles
- Portal/AGOL integration

Fuentes de datos espaciales:
- IDE Chile (Infraestructura de Datos Espaciales)
- CONAF (áreas protegidas)
- SERNAGEOMIN (geología, riesgos)
- MOP (infraestructura)
- MINVU (instrumentos planificación)
- Municipalidades (PRC, zonificación)

Autor: DATAPOLIS SpA
Versión: 3.0.0
Licencia: Propietaria
"""

import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from decimal import Decimal
import math

# Geospatial libraries
try:
    from shapely.geometry import Point, Polygon, MultiPolygon, LineString, shape, mapping
    from shapely.ops import transform, unary_union
    from shapely import wkt, wkb
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

try:
    import pyproj
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS Y CONSTANTES
# ============================================================================

class TipoServicioEsri(str, Enum):
    """Tipos de servicios Esri"""
    FEATURE_SERVICE = "FeatureServer"
    MAP_SERVICE = "MapServer"
    IMAGE_SERVICE = "ImageServer"
    GEOCODE_SERVICE = "GeocodeServer"
    GP_SERVICE = "GPServer"
    GEOMETRY_SERVICE = "GeometryServer"
    NETWORK_SERVICE = "NAServer"


class OperacionEspacial(str, Enum):
    """Operaciones espaciales disponibles"""
    BUFFER = "buffer"
    INTERSECT = "intersect"
    UNION = "union"
    CLIP = "clip"
    DISSOLVE = "dissolve"
    OVERLAY = "overlay"
    NEAREST = "nearest"
    WITHIN_DISTANCE = "within_distance"
    CONTAINS = "contains"
    CROSSES = "crosses"


class SistemaReferencia(str, Enum):
    """Sistemas de referencia espacial para Chile"""
    WGS84 = "4326"
    UTM_19S = "32719"  # Zona 19S (Chile central)
    UTM_18S = "32718"  # Zona 18S (Norte)
    SIRGAS_CHILE = "5361"  # SIRGAS Chile 2013


class TipoGeometria(str, Enum):
    """Tipos de geometría"""
    POINT = "esriGeometryPoint"
    MULTIPOINT = "esriGeometryMultipoint"
    POLYLINE = "esriGeometryPolyline"
    POLYGON = "esriGeometryPolygon"
    ENVELOPE = "esriGeometryEnvelope"


# URLs de servicios oficiales Chile
SERVICIOS_IDE_CHILE = {
    "regiones": "https://geoservices.ide.cl/arcgis/rest/services/BaseLayers/RegionesChile/FeatureServer/0",
    "comunas": "https://geoservices.ide.cl/arcgis/rest/services/BaseLayers/ComunasChile/FeatureServer/0",
    "manzanas": "https://geoservices.ide.cl/arcgis/rest/services/INE/ManzanasCenso2017/FeatureServer/0",
    "predios": "https://geoservices.ide.cl/arcgis/rest/services/SII/PrediosSII/FeatureServer/0",
    "areas_verdes": "https://geoservices.ide.cl/arcgis/rest/services/MINVU/AreasVerdes/FeatureServer/0",
    "zonificacion_prc": "https://geoservices.ide.cl/arcgis/rest/services/MINVU/ZonificacionPRC/FeatureServer/0",
    "areas_protegidas": "https://geoservices.ide.cl/arcgis/rest/services/CONAF/SNASPE/FeatureServer/0",
    "riesgo_inundacion": "https://geoservices.ide.cl/arcgis/rest/services/SENAPRED/RiesgoInundacion/FeatureServer/0",
    "riesgo_remocion": "https://geoservices.ide.cl/arcgis/rest/services/SERNAGEOMIN/RemocionMasa/FeatureServer/0",
    "fallas_geologicas": "https://geoservices.ide.cl/arcgis/rest/services/SERNAGEOMIN/FallasGeologicas/FeatureServer/0",
    "red_vial": "https://geoservices.ide.cl/arcgis/rest/services/MOP/RedVialNacional/FeatureServer/0",
    "metro_santiago": "https://geoservices.ide.cl/arcgis/rest/services/MTT/MetroSantiago/FeatureServer/0",
    "transantiago": "https://geoservices.ide.cl/arcgis/rest/services/MTT/TransantiagoPPT/FeatureServer/0"
}

# Servicios de geocodificación
GEOCODER_CHILE = "https://geoservices.ide.cl/arcgis/rest/services/Geocoding/ChileGeocoder/GeocodeServer"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class CredencialesEsri:
    """Credenciales para servicios Esri"""
    portal_url: str = "https://www.arcgis.com"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    token_expires: Optional[datetime] = None
    referer: str = "https://datapolis.cl"


@dataclass
class ResultadoGeocoding:
    """Resultado de geocodificación"""
    direccion_input: str
    direccion_normalizada: str
    latitud: float
    longitud: float
    score: float  # 0-100
    precision: str  # PointAddress, StreetAddress, etc.
    comuna: Optional[str] = None
    region: Optional[str] = None
    codigo_postal: Optional[str] = None
    atributos_adicionales: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultadoReverseGeocode:
    """Resultado de geocodificación inversa"""
    latitud: float
    longitud: float
    direccion: str
    comuna: str
    region: str
    distancia_metros: float
    atributos: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultadoAnalisisEspacial:
    """Resultado de análisis espacial"""
    operacion: str
    geometria_resultado: Optional[Dict[str, Any]] = None
    features_resultantes: List[Dict[str, Any]] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    area_total_m2: Optional[float] = None
    perimetro_total_m: Optional[float] = None
    n_features: int = 0
    tiempo_proceso_ms: int = 0


@dataclass
class ResultadoZonificacion:
    """Resultado de consulta de zonificación PRC"""
    codigo_zona: str
    nombre_zona: str
    tipo_uso: str
    usos_permitidos: List[str] = field(default_factory=list)
    usos_prohibidos: List[str] = field(default_factory=list)
    constructibilidad: Optional[float] = None
    ocupacion_suelo: Optional[float] = None
    altura_maxima: Optional[float] = None
    densidad_maxima: Optional[float] = None
    subdivision_predial_minima_m2: Optional[float] = None
    antejardín_minimo_m: Optional[float] = None
    distanciamiento_m: Optional[float] = None
    adosamiento_permitido: bool = False
    rasante: Optional[str] = None
    instrumento: str = ""
    fecha_publicacion: Optional[date] = None
    observaciones: List[str] = field(default_factory=list)


@dataclass
class ResultadoRiesgos:
    """Resultado de análisis de riesgos naturales"""
    latitud: float
    longitud: float
    zona_sismica: str  # 1, 2, 3
    riesgo_inundacion: str  # bajo, medio, alto, muy_alto
    riesgo_remocion_masa: str
    riesgo_tsunami: str
    distancia_falla_km: Optional[float] = None
    nombre_falla_cercana: Optional[str] = None
    area_protegida_cercana: Optional[str] = None
    distancia_area_protegida_km: Optional[float] = None
    alertas: List[str] = field(default_factory=list)


@dataclass
class ResultadoAccesibilidad:
    """Resultado de análisis de accesibilidad"""
    latitud: float
    longitud: float
    estacion_metro_cercana: Optional[str] = None
    distancia_metro_m: Optional[float] = None
    linea_metro: Optional[str] = None
    paradero_bus_cercano: Optional[str] = None
    distancia_bus_m: Optional[float] = None
    acceso_vial_principal: Optional[str] = None
    distancia_autopista_m: Optional[float] = None
    tiempo_centro_min: Optional[int] = None
    indice_accesibilidad: float = 0.0  # 0-100


# ============================================================================
# SERVICIO PRINCIPAL GIRES
# ============================================================================

class ServicioGIRES:
    """
    Servicio de Gestión Integrada de Recursos Espaciales (GIRES)
    Integración con Esri ArcGIS para análisis geoespacial
    """
    
    def __init__(
        self,
        credenciales: Optional[CredencialesEsri] = None,
        cache_ttl_seconds: int = 3600,
        timeout_seconds: int = 30,
        max_concurrent_requests: int = 10
    ):
        self.credenciales = credenciales or CredencialesEsri()
        self.cache_ttl = cache_ttl_seconds
        self.timeout = timeout_seconds
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Transformadores de coordenadas
        if PYPROJ_AVAILABLE:
            self._transformers = {
                "4326_to_32719": Transformer.from_crs("EPSG:4326", "EPSG:32719", always_xy=True),
                "32719_to_4326": Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True),
            }
        
        logger.info("ServicioGIRES inicializado")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear sesión HTTP"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "DATAPOLIS/3.0 GIRES",
                    "Referer": self.credenciales.referer
                }
            )
        return self._session
    
    async def close(self):
        """Cerrar sesión HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ========================================================================
    # AUTENTICACIÓN
    # ========================================================================
    
    async def _get_token(self) -> Optional[str]:
        """Obtener token de autenticación"""
        # Si hay token válido, usarlo
        if (self.credenciales.token and 
            self.credenciales.token_expires and 
            self.credenciales.token_expires > datetime.utcnow()):
            return self.credenciales.token
        
        # Si hay credenciales OAuth, obtener nuevo token
        if self.credenciales.client_id and self.credenciales.client_secret:
            return await self._oauth_token()
        
        # Si hay usuario/password
        if self.credenciales.username and self.credenciales.password:
            return await self._generate_token()
        
        # Sin autenticación (servicios públicos)
        return None
    
    async def _oauth_token(self) -> Optional[str]:
        """Obtener token OAuth"""
        url = f"{self.credenciales.portal_url}/sharing/rest/oauth2/token"
        
        params = {
            "client_id": self.credenciales.client_id,
            "client_secret": self.credenciales.client_secret,
            "grant_type": "client_credentials",
            "f": "json"
        }
        
        try:
            session = await self._get_session()
            async with session.post(url, data=params) as response:
                data = await response.json()
                
                if "access_token" in data:
                    self.credenciales.token = data["access_token"]
                    expires_in = data.get("expires_in", 7200)
                    self.credenciales.token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                    return self.credenciales.token
                
                logger.error(f"Error OAuth: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo token OAuth: {e}")
            return None
    
    async def _generate_token(self) -> Optional[str]:
        """Generar token con usuario/password"""
        url = f"{self.credenciales.portal_url}/sharing/rest/generateToken"
        
        params = {
            "username": self.credenciales.username,
            "password": self.credenciales.password,
            "referer": self.credenciales.referer,
            "f": "json"
        }
        
        try:
            session = await self._get_session()
            async with session.post(url, data=params) as response:
                data = await response.json()
                
                if "token" in data:
                    self.credenciales.token = data["token"]
                    expires = data.get("expires", 0)
                    self.credenciales.token_expires = datetime.fromtimestamp(expires / 1000)
                    return self.credenciales.token
                
                return None
                
        except Exception as e:
            logger.error(f"Error generando token: {e}")
            return None
    
    # ========================================================================
    # QUERY DE FEATURE SERVICES
    # ========================================================================
    
    async def query_feature_service(
        self,
        url: str,
        where: str = "1=1",
        geometry: Optional[Dict[str, Any]] = None,
        geometry_type: str = "esriGeometryEnvelope",
        spatial_rel: str = "esriSpatialRelIntersects",
        out_fields: str = "*",
        return_geometry: bool = True,
        out_sr: str = "4326",
        result_offset: int = 0,
        result_record_count: int = 1000,
        order_by_fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query a un Feature Service de ArcGIS
        
        Args:
            url: URL del feature service
            where: Cláusula WHERE SQL
            geometry: Geometría para filtro espacial
            geometry_type: Tipo de geometría
            spatial_rel: Relación espacial
            out_fields: Campos a retornar
            return_geometry: Si retornar geometrías
            out_sr: Sistema de referencia de salida
            result_offset: Offset para paginación
            result_record_count: Máximo registros
            order_by_fields: Campos para ordenar
            
        Returns:
            Dict con features y metadata
        """
        cache_key = self._cache_key("query", url, where, str(geometry), out_fields)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        params = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": str(return_geometry).lower(),
            "outSR": out_sr,
            "resultOffset": result_offset,
            "resultRecordCount": result_record_count,
            "f": "json"
        }
        
        if geometry:
            params["geometry"] = json.dumps(geometry)
            params["geometryType"] = geometry_type
            params["spatialRel"] = spatial_rel
        
        if order_by_fields:
            params["orderByFields"] = order_by_fields
        
        token = await self._get_token()
        if token:
            params["token"] = token
        
        try:
            async with self.semaphore:
                session = await self._get_session()
                query_url = f"{url}/query"
                
                async with session.get(query_url, params=params) as response:
                    data = await response.json()
                    
                    if "error" in data:
                        logger.error(f"Error en query: {data['error']}")
                        raise Exception(data["error"].get("message", "Error desconocido"))
                    
                    result = {
                        "features": data.get("features", []),
                        "fields": data.get("fields", []),
                        "geometry_type": data.get("geometryType"),
                        "spatial_reference": data.get("spatialReference"),
                        "exceeded_transfer_limit": data.get("exceededTransferLimit", False)
                    }
                    
                    self._set_cache(cache_key, result)
                    return result
                    
        except Exception as e:
            logger.error(f"Error en query_feature_service: {e}")
            raise
    
    async def query_by_location(
        self,
        latitud: float,
        longitud: float,
        servicio: str,
        radio_metros: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Query por ubicación (punto o buffer)
        
        Args:
            latitud: Latitud WGS84
            longitud: Longitud WGS84
            servicio: Nombre del servicio en SERVICIOS_IDE_CHILE
            radio_metros: Radio de buffer opcional
            
        Returns:
            Lista de features encontrados
        """
        url = SERVICIOS_IDE_CHILE.get(servicio)
        if not url:
            raise ValueError(f"Servicio '{servicio}' no encontrado")
        
        if radio_metros:
            # Query con buffer
            geometry = {
                "x": longitud,
                "y": latitud,
                "spatialReference": {"wkid": 4326}
            }
            
            result = await self.query_feature_service(
                url=url,
                geometry=geometry,
                geometry_type="esriGeometryPoint",
                spatial_rel="esriSpatialRelIntersects",
                # El buffer se hace con geometryService
            )
        else:
            # Query puntual
            geometry = {
                "x": longitud,
                "y": latitud,
                "spatialReference": {"wkid": 4326}
            }
            
            result = await self.query_feature_service(
                url=url,
                geometry=geometry,
                geometry_type="esriGeometryPoint",
                spatial_rel="esriSpatialRelIntersects"
            )
        
        return result.get("features", [])
    
    # ========================================================================
    # GEOCODIFICACIÓN
    # ========================================================================
    
    async def geocode(
        self,
        direccion: str,
        comuna: Optional[str] = None,
        region: Optional[str] = None,
        max_locations: int = 5
    ) -> List[ResultadoGeocoding]:
        """
        Geocodificar dirección a coordenadas
        
        Args:
            direccion: Dirección a geocodificar
            comuna: Comuna para mejorar precisión
            region: Región para mejorar precisión
            max_locations: Máximo de resultados
            
        Returns:
            Lista de resultados de geocodificación
        """
        # Construir dirección completa
        direccion_completa = direccion
        if comuna:
            direccion_completa += f", {comuna}"
        if region:
            direccion_completa += f", {region}"
        direccion_completa += ", Chile"
        
        params = {
            "SingleLine": direccion_completa,
            "f": "json",
            "outFields": "*",
            "maxLocations": max_locations,
            "outSR": "4326"
        }
        
        token = await self._get_token()
        if token:
            params["token"] = token
        
        try:
            session = await self._get_session()
            url = f"{GEOCODER_CHILE}/findAddressCandidates"
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if "error" in data:
                    logger.error(f"Error geocoding: {data['error']}")
                    return []
                
                resultados = []
                for candidate in data.get("candidates", []):
                    attrs = candidate.get("attributes", {})
                    location = candidate.get("location", {})
                    
                    resultados.append(ResultadoGeocoding(
                        direccion_input=direccion,
                        direccion_normalizada=attrs.get("Match_addr", ""),
                        latitud=location.get("y", 0),
                        longitud=location.get("x", 0),
                        score=candidate.get("score", 0),
                        precision=attrs.get("Addr_type", ""),
                        comuna=attrs.get("City", ""),
                        region=attrs.get("Region", ""),
                        codigo_postal=attrs.get("Postal", ""),
                        atributos_adicionales=attrs
                    ))
                
                return resultados
                
        except Exception as e:
            logger.error(f"Error en geocode: {e}")
            return []
    
    async def reverse_geocode(
        self,
        latitud: float,
        longitud: float,
        distance_metros: int = 100
    ) -> Optional[ResultadoReverseGeocode]:
        """
        Geocodificación inversa (coordenadas a dirección)
        
        Args:
            latitud: Latitud WGS84
            longitud: Longitud WGS84
            distance_metros: Radio de búsqueda
            
        Returns:
            Resultado de geocodificación inversa
        """
        params = {
            "location": f"{longitud},{latitud}",
            "distance": distance_metros,
            "f": "json",
            "outSR": "4326"
        }
        
        token = await self._get_token()
        if token:
            params["token"] = token
        
        try:
            session = await self._get_session()
            url = f"{GEOCODER_CHILE}/reverseGeocode"
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if "error" in data:
                    logger.error(f"Error reverse geocode: {data['error']}")
                    return None
                
                address = data.get("address", {})
                location = data.get("location", {})
                
                return ResultadoReverseGeocode(
                    latitud=latitud,
                    longitud=longitud,
                    direccion=address.get("Match_addr", ""),
                    comuna=address.get("City", ""),
                    region=address.get("Region", ""),
                    distancia_metros=0,  # Se calcula si es necesario
                    atributos=address
                )
                
        except Exception as e:
            logger.error(f"Error en reverse_geocode: {e}")
            return None
    
    # ========================================================================
    # ZONIFICACIÓN Y NORMATIVA URBANA
    # ========================================================================
    
    async def obtener_zonificacion(
        self,
        latitud: float,
        longitud: float
    ) -> Optional[ResultadoZonificacion]:
        """
        Obtener zonificación PRC para una ubicación
        
        Args:
            latitud: Latitud WGS84
            longitud: Longitud WGS84
            
        Returns:
            Información de zonificación del PRC
        """
        try:
            features = await self.query_by_location(
                latitud=latitud,
                longitud=longitud,
                servicio="zonificacion_prc"
            )
            
            if not features:
                return None
            
            # Tomar primer feature (debería ser único para un punto)
            feature = features[0]
            attrs = feature.get("attributes", {})
            
            # Parsear usos permitidos/prohibidos
            usos_permitidos = self._parsear_usos(attrs.get("USOS_PERMITIDOS", ""))
            usos_prohibidos = self._parsear_usos(attrs.get("USOS_PROHIBIDOS", ""))
            
            return ResultadoZonificacion(
                codigo_zona=attrs.get("CODIGO_ZONA", ""),
                nombre_zona=attrs.get("NOMBRE_ZONA", ""),
                tipo_uso=attrs.get("TIPO_USO", ""),
                usos_permitidos=usos_permitidos,
                usos_prohibidos=usos_prohibidos,
                constructibilidad=self._safe_float(attrs.get("CONSTRUCTIBILIDAD")),
                ocupacion_suelo=self._safe_float(attrs.get("OCUPACION_SUELO")),
                altura_maxima=self._safe_float(attrs.get("ALTURA_MAXIMA")),
                densidad_maxima=self._safe_float(attrs.get("DENSIDAD")),
                subdivision_predial_minima_m2=self._safe_float(attrs.get("SUBDIVISION_MINIMA")),
                antejardín_minimo_m=self._safe_float(attrs.get("ANTEJARDIN")),
                distanciamiento_m=self._safe_float(attrs.get("DISTANCIAMIENTO")),
                adosamiento_permitido=attrs.get("ADOSAMIENTO", "N") == "S",
                rasante=attrs.get("RASANTE"),
                instrumento=attrs.get("INSTRUMENTO", ""),
                fecha_publicacion=self._parse_date(attrs.get("FECHA_PUBLICACION")),
                observaciones=self._parsear_observaciones(attrs.get("OBSERVACIONES", ""))
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo zonificación: {e}")
            return None
    
    async def verificar_uso_permitido(
        self,
        latitud: float,
        longitud: float,
        uso_propuesto: str
    ) -> Dict[str, Any]:
        """
        Verificar si un uso es permitido en la zonificación
        
        Args:
            latitud: Latitud
            longitud: Longitud
            uso_propuesto: Uso a verificar (residencial, comercial, etc.)
            
        Returns:
            Dict con resultado de verificación
        """
        zonificacion = await self.obtener_zonificacion(latitud, longitud)
        
        if not zonificacion:
            return {
                "permitido": None,
                "mensaje": "No se encontró información de zonificación",
                "zonificacion": None
            }
        
        # Normalizar uso propuesto
        uso_norm = uso_propuesto.upper().strip()
        
        # Verificar en usos permitidos
        if any(uso_norm in u.upper() for u in zonificacion.usos_permitidos):
            return {
                "permitido": True,
                "mensaje": f"Uso '{uso_propuesto}' está permitido en zona {zonificacion.codigo_zona}",
                "zonificacion": zonificacion,
                "condiciones": zonificacion.observaciones
            }
        
        # Verificar en usos prohibidos
        if any(uso_norm in u.upper() for u in zonificacion.usos_prohibidos):
            return {
                "permitido": False,
                "mensaje": f"Uso '{uso_propuesto}' está PROHIBIDO en zona {zonificacion.codigo_zona}",
                "zonificacion": zonificacion
            }
        
        # No está en ninguna lista
        return {
            "permitido": None,
            "mensaje": f"Uso '{uso_propuesto}' no está explícitamente permitido ni prohibido. Consultar DOM.",
            "zonificacion": zonificacion
        }
    
    # ========================================================================
    # ANÁLISIS DE RIESGOS NATURALES
    # ========================================================================
    
    async def analizar_riesgos(
        self,
        latitud: float,
        longitud: float
    ) -> ResultadoRiesgos:
        """
        Análisis integral de riesgos naturales para una ubicación
        
        Args:
            latitud: Latitud WGS84
            longitud: Longitud WGS84
            
        Returns:
            Resultado con todos los riesgos identificados
        """
        alertas = []
        
        # Ejecutar consultas en paralelo
        tasks = [
            self._obtener_zona_sismica(latitud, longitud),
            self._obtener_riesgo_inundacion(latitud, longitud),
            self._obtener_riesgo_remocion(latitud, longitud),
            self._obtener_riesgo_tsunami(latitud, longitud),
            self._obtener_falla_cercana(latitud, longitud),
            self._obtener_area_protegida_cercana(latitud, longitud)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        zona_sismica = results[0] if not isinstance(results[0], Exception) else "3"
        riesgo_inundacion = results[1] if not isinstance(results[1], Exception) else "desconocido"
        riesgo_remocion = results[2] if not isinstance(results[2], Exception) else "desconocido"
        riesgo_tsunami = results[3] if not isinstance(results[3], Exception) else "desconocido"
        falla_info = results[4] if not isinstance(results[4], Exception) else (None, None)
        area_protegida_info = results[5] if not isinstance(results[5], Exception) else (None, None)
        
        # Generar alertas
        if zona_sismica == "3":
            alertas.append("Zona sísmica de alta intensidad (Zona 3)")
        
        if riesgo_inundacion in ["alto", "muy_alto"]:
            alertas.append(f"Riesgo de inundación {riesgo_inundacion}")
        
        if riesgo_remocion in ["alto", "muy_alto"]:
            alertas.append(f"Riesgo de remoción en masa {riesgo_remocion}")
        
        if riesgo_tsunami in ["alto", "muy_alto"]:
            alertas.append(f"Riesgo de tsunami {riesgo_tsunami}")
        
        if falla_info[1] and falla_info[1] < 5:
            alertas.append(f"Falla geológica '{falla_info[0]}' a {falla_info[1]:.1f} km")
        
        return ResultadoRiesgos(
            latitud=latitud,
            longitud=longitud,
            zona_sismica=zona_sismica,
            riesgo_inundacion=riesgo_inundacion,
            riesgo_remocion_masa=riesgo_remocion,
            riesgo_tsunami=riesgo_tsunami,
            distancia_falla_km=falla_info[1],
            nombre_falla_cercana=falla_info[0],
            area_protegida_cercana=area_protegida_info[0],
            distancia_area_protegida_km=area_protegida_info[1],
            alertas=alertas
        )
    
    async def _obtener_zona_sismica(self, lat: float, lon: float) -> str:
        """Obtener zona sísmica según NCh 433"""
        # Simplificación: Chile se divide en 3 zonas sísmicas
        # Zona 1: Extremo norte
        # Zona 2: Norte y sur extremo
        # Zona 3: Zona central y centro-sur (mayor sismicidad)
        
        if lat > -20 or lat < -45:
            return "2"
        elif -20 >= lat >= -35:
            return "3"
        else:
            return "2"
    
    async def _obtener_riesgo_inundacion(self, lat: float, lon: float) -> str:
        """Consultar riesgo de inundación en SENAPRED"""
        try:
            features = await self.query_by_location(lat, lon, "riesgo_inundacion")
            if features:
                nivel = features[0].get("attributes", {}).get("NIVEL_RIESGO", "bajo")
                return nivel.lower()
            return "bajo"
        except:
            return "desconocido"
    
    async def _obtener_riesgo_remocion(self, lat: float, lon: float) -> str:
        """Consultar riesgo de remoción en masa"""
        try:
            features = await self.query_by_location(lat, lon, "riesgo_remocion")
            if features:
                nivel = features[0].get("attributes", {}).get("SUSCEPTIBILIDAD", "baja")
                return nivel.lower()
            return "bajo"
        except:
            return "desconocido"
    
    async def _obtener_riesgo_tsunami(self, lat: float, lon: float) -> str:
        """Evaluar riesgo de tsunami basado en elevación y distancia al mar"""
        # Simplificación: considerar zonas costeras bajo 30m de elevación
        # En producción consultar capa SHOA de inundación por tsunami
        return "bajo"  # Placeholder
    
    async def _obtener_falla_cercana(
        self, 
        lat: float, 
        lon: float
    ) -> Tuple[Optional[str], Optional[float]]:
        """Obtener falla geológica más cercana"""
        try:
            # Buffer de 20km para buscar fallas
            # En producción usar geometry service para buffer
            features = await self.query_by_location(lat, lon, "fallas_geologicas")
            
            if not features:
                return (None, None)
            
            # Calcular distancia a la más cercana
            nombre = features[0].get("attributes", {}).get("NOMBRE", "")
            # Distancia aproximada (simplificado)
            distancia = 5.0  # Placeholder
            
            return (nombre, distancia)
            
        except:
            return (None, None)
    
    async def _obtener_area_protegida_cercana(
        self,
        lat: float,
        lon: float
    ) -> Tuple[Optional[str], Optional[float]]:
        """Obtener área protegida SNASPE más cercana"""
        try:
            features = await self.query_by_location(lat, lon, "areas_protegidas")
            
            if features:
                nombre = features[0].get("attributes", {}).get("NOMBRE", "")
                return (nombre, 0.0)  # Está dentro
            
            return (None, None)
            
        except:
            return (None, None)
    
    # ========================================================================
    # ANÁLISIS DE ACCESIBILIDAD
    # ========================================================================
    
    async def analizar_accesibilidad(
        self,
        latitud: float,
        longitud: float
    ) -> ResultadoAccesibilidad:
        """
        Análisis de accesibilidad y conectividad de transporte
        
        Args:
            latitud: Latitud WGS84
            longitud: Longitud WGS84
            
        Returns:
            Resultado con indicadores de accesibilidad
        """
        # Consultas en paralelo
        tasks = [
            self._obtener_metro_cercano(latitud, longitud),
            self._obtener_paradero_cercano(latitud, longitud),
            self._obtener_acceso_vial(latitud, longitud)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metro_info = results[0] if not isinstance(results[0], Exception) else {}
        bus_info = results[1] if not isinstance(results[1], Exception) else {}
        vial_info = results[2] if not isinstance(results[2], Exception) else {}
        
        # Calcular índice de accesibilidad (0-100)
        indice = self._calcular_indice_accesibilidad(metro_info, bus_info, vial_info)
        
        return ResultadoAccesibilidad(
            latitud=latitud,
            longitud=longitud,
            estacion_metro_cercana=metro_info.get("estacion"),
            distancia_metro_m=metro_info.get("distancia"),
            linea_metro=metro_info.get("linea"),
            paradero_bus_cercano=bus_info.get("paradero"),
            distancia_bus_m=bus_info.get("distancia"),
            acceso_vial_principal=vial_info.get("via"),
            distancia_autopista_m=vial_info.get("distancia"),
            tiempo_centro_min=self._estimar_tiempo_centro(latitud, longitud),
            indice_accesibilidad=indice
        )
    
    async def _obtener_metro_cercano(self, lat: float, lon: float) -> Dict[str, Any]:
        """Obtener estación de metro más cercana"""
        try:
            features = await self.query_by_location(lat, lon, "metro_santiago")
            if features:
                attrs = features[0].get("attributes", {})
                return {
                    "estacion": attrs.get("NOMBRE_ESTACION"),
                    "linea": attrs.get("LINEA"),
                    "distancia": 500  # Placeholder - calcular distancia real
                }
            return {}
        except:
            return {}
    
    async def _obtener_paradero_cercano(self, lat: float, lon: float) -> Dict[str, Any]:
        """Obtener paradero de bus más cercano"""
        try:
            features = await self.query_by_location(lat, lon, "transantiago")
            if features:
                attrs = features[0].get("attributes", {})
                return {
                    "paradero": attrs.get("CODIGO_PARADERO"),
                    "distancia": 200  # Placeholder
                }
            return {}
        except:
            return {}
    
    async def _obtener_acceso_vial(self, lat: float, lon: float) -> Dict[str, Any]:
        """Obtener acceso a vía principal más cercana"""
        try:
            features = await self.query_by_location(lat, lon, "red_vial")
            if features:
                attrs = features[0].get("attributes", {})
                return {
                    "via": attrs.get("NOMBRE"),
                    "tipo": attrs.get("TIPO_VIA"),
                    "distancia": 1000  # Placeholder
                }
            return {}
        except:
            return {}
    
    def _calcular_indice_accesibilidad(
        self,
        metro: Dict,
        bus: Dict,
        vial: Dict
    ) -> float:
        """Calcular índice de accesibilidad 0-100"""
        score = 0
        
        # Metro (40 puntos máx)
        if metro.get("distancia"):
            dist = metro["distancia"]
            if dist < 500:
                score += 40
            elif dist < 1000:
                score += 30
            elif dist < 2000:
                score += 15
        
        # Bus (30 puntos máx)
        if bus.get("distancia"):
            dist = bus["distancia"]
            if dist < 300:
                score += 30
            elif dist < 500:
                score += 20
            elif dist < 1000:
                score += 10
        
        # Vial (30 puntos máx)
        if vial.get("distancia"):
            dist = vial["distancia"]
            if dist < 1000:
                score += 30
            elif dist < 3000:
                score += 20
            elif dist < 5000:
                score += 10
        
        return min(100, score)
    
    def _estimar_tiempo_centro(self, lat: float, lon: float) -> int:
        """Estimar tiempo al centro de Santiago"""
        # Centro de Santiago
        centro_lat, centro_lon = -33.4489, -70.6693
        
        # Distancia aproximada en km
        dist_km = self._haversine_distance(lat, lon, centro_lat, centro_lon)
        
        # Estimación: 2 min/km en hora punta
        return int(dist_km * 2)
    
    # ========================================================================
    # OPERACIONES ESPACIALES
    # ========================================================================
    
    async def buffer(
        self,
        geometria: Dict[str, Any],
        distancia_metros: float,
        sr: str = "4326"
    ) -> Dict[str, Any]:
        """
        Crear buffer alrededor de geometría
        
        Args:
            geometria: Geometría de entrada (point, polygon, etc.)
            distancia_metros: Radio del buffer
            sr: Sistema de referencia
            
        Returns:
            Geometría del buffer
        """
        if SHAPELY_AVAILABLE and PYPROJ_AVAILABLE:
            # Usar Shapely localmente
            geom = shape(geometria)
            
            # Transformar a UTM para buffer en metros
            transformer_to_utm = self._transformers["4326_to_32719"]
            transformer_to_wgs = self._transformers["32719_to_4326"]
            
            geom_utm = transform(transformer_to_utm.transform, geom)
            buffer_utm = geom_utm.buffer(distancia_metros)
            buffer_wgs = transform(transformer_to_wgs.transform, buffer_utm)
            
            return mapping(buffer_wgs)
        else:
            # Usar geometry service de Esri
            # Implementar llamada a geometryService/buffer
            raise NotImplementedError("Shapely no disponible, usar geometry service")
    
    async def intersect(
        self,
        geometria1: Dict[str, Any],
        geometria2: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Calcular intersección de dos geometrías"""
        if SHAPELY_AVAILABLE:
            geom1 = shape(geometria1)
            geom2 = shape(geometria2)
            
            intersection = geom1.intersection(geom2)
            
            if intersection.is_empty:
                return None
            
            return mapping(intersection)
        else:
            raise NotImplementedError("Shapely no disponible")
    
    async def calcular_area_m2(self, geometria: Dict[str, Any]) -> float:
        """Calcular área en metros cuadrados"""
        if SHAPELY_AVAILABLE and PYPROJ_AVAILABLE:
            geom = shape(geometria)
            
            # Transformar a UTM para cálculo en metros
            transformer = self._transformers["4326_to_32719"]
            geom_utm = transform(transformer.transform, geom)
            
            return geom_utm.area
        else:
            raise NotImplementedError("Shapely/pyproj no disponible")
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def _cache_key(self, *args) -> str:
        """Generar clave de cache"""
        key_str = "|".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Obtener valor de cache si no expiró"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl):
                return value
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Guardar valor en cache"""
        self._cache[key] = (value, datetime.utcnow())
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Convertir a float de forma segura"""
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parsear fecha"""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                # Timestamp en milisegundos
                return datetime.fromtimestamp(value / 1000).date()
            elif isinstance(value, str):
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except:
            return None
    
    def _parsear_usos(self, texto: str) -> List[str]:
        """Parsear lista de usos desde texto"""
        if not texto:
            return []
        return [u.strip() for u in texto.split(",") if u.strip()]
    
    def _parsear_observaciones(self, texto: str) -> List[str]:
        """Parsear observaciones"""
        if not texto:
            return []
        return [o.strip() for o in texto.split(";") if o.strip()]
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calcular distancia Haversine en km"""
        R = 6371  # Radio de la Tierra en km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    # ========================================================================
    # VERIFICACIÓN DE ESTADO
    # ========================================================================
    
    async def verificar_estado(self) -> Dict[str, Any]:
        """Verificar estado del servicio y conexiones"""
        status = {
            "ok": True,
            "servicios": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Verificar servicios IDE Chile
        for nombre, url in list(SERVICIOS_IDE_CHILE.items())[:3]:  # Solo primeros 3
            try:
                session = await self._get_session()
                async with session.get(f"{url}?f=json", timeout=5) as response:
                    status["servicios"][nombre] = response.status == 200
            except:
                status["servicios"][nombre] = False
                status["ok"] = False
        
        status["shapely_disponible"] = SHAPELY_AVAILABLE
        status["pyproj_disponible"] = PYPROJ_AVAILABLE
        status["geopandas_disponible"] = GEOPANDAS_AVAILABLE
        
        return status
