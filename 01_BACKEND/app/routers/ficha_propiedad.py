# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Router M01 Ficha Propiedad
API REST para gestión de fichas técnicas de propiedades inmobiliarias
Integración SII, CBR, DOM, valorización y comparables de mercado

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum
import io
import json

# ============================================================================
# SCHEMAS PYDANTIC - ENUMS
# ============================================================================

class TipoPropiedadEnum(str, Enum):
    """Tipos de propiedad inmobiliaria"""
    DEPARTAMENTO = "departamento"
    CASA = "casa"
    OFICINA = "oficina"
    LOCAL_COMERCIAL = "local_comercial"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"
    TERRENO = "terreno"
    PARCELA = "parcela"
    SITIO_ERIAZO = "sitio_eriazo"
    INDUSTRIAL = "industrial"
    AGRICOLA = "agricola"
    MIXTO = "mixto"


class EstadoConservacionEnum(str, Enum):
    """Estado de conservación del inmueble"""
    NUEVO = "nuevo"
    EXCELENTE = "excelente"
    BUENO = "bueno"
    REGULAR = "regular"
    DETERIORADO = "deteriorado"
    EN_RUINAS = "en_ruinas"
    EN_CONSTRUCCION = "en_construccion"
    EN_REMODELACION = "en_remodelacion"


class TipoEstructuraEnum(str, Enum):
    """Tipo de estructura constructiva"""
    HORMIGON_ARMADO = "hormigon_armado"
    ALBANILERIA_REFORZADA = "albanileria_reforzada"
    ALBANILERIA_CONFINADA = "albanileria_confinada"
    ESTRUCTURA_METALICA = "estructura_metalica"
    MADERA = "madera"
    ADOBE = "adobe"
    MIXTA = "mixta"
    PREFABRICADA = "prefabricada"


class CalidadTerminacionesEnum(str, Enum):
    """Calidad de terminaciones"""
    LUJO = "lujo"
    ALTA = "alta"
    MEDIA_ALTA = "media_alta"
    MEDIA = "media"
    ECONOMICA = "economica"
    SOCIAL = "social"


class ZonaUrbanaEnum(str, Enum):
    """Zonas del Plan Regulador Comunal"""
    ZR1 = "ZR1"  # Residencial exclusiva
    ZR2 = "ZR2"  # Residencial mixta
    ZR3 = "ZR3"  # Residencial alta densidad
    ZC = "ZC"    # Comercial
    ZE = "ZE"    # Equipamiento
    ZI1 = "ZI1"  # Industrial inofensiva
    ZI2 = "ZI2"  # Industrial molesta
    ZAV = "ZAV"  # Área verde
    ZP = "ZP"    # Protección
    ZEU = "ZEU"  # Extensión urbana
    ZR = "ZR"    # Rural


class EstadoLegalEnum(str, Enum):
    """Estado legal de la propiedad"""
    LIMPIO = "limpio"
    CON_HIPOTECA = "con_hipoteca"
    CON_PROHIBICION = "con_prohibicion"
    EN_LITIGIO = "en_litigio"
    EN_SUCESION = "en_sucesion"
    IRREGULAR = "irregular"
    EXPROPIACION = "expropiacion"


class MetodologiaValoracionEnum(str, Enum):
    """Metodología de valoración"""
    COMPARABLES = "comparables"
    HEDONICO = "hedonico"
    FLUJOS = "flujos"
    COSTO = "costo"
    MIXTA = "mixta"


class TipoOperacionEnum(str, Enum):
    """Tipo de operación de mercado"""
    VENTA = "venta"
    ARRIENDO = "arriendo"


class OrdenEnum(str, Enum):
    """Orden de resultados"""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# SCHEMAS PYDANTIC - REQUESTS
# ============================================================================

class UbicacionInput(BaseModel):
    """Datos de ubicación"""
    direccion_completa: str = Field(..., description="Dirección completa")
    numero: Optional[str] = Field(None, description="Número de calle")
    departamento: Optional[str] = Field(None, description="Número de departamento")
    piso: Optional[int] = Field(None, description="Número de piso")
    comuna: str = Field(..., description="Comuna")
    region: str = Field(..., description="Región")
    codigo_postal: Optional[str] = Field(None, description="Código postal")
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class SuperficiesInput(BaseModel):
    """Superficies de la propiedad"""
    terreno_m2: Optional[float] = Field(None, ge=0, description="Superficie terreno m²")
    construida_total_m2: Optional[float] = Field(None, ge=0, description="Superficie construida total m²")
    construida_util_m2: float = Field(..., ge=0, description="Superficie útil m²")
    terraza_m2: Optional[float] = Field(None, ge=0, description="Terraza m²")
    jardin_m2: Optional[float] = Field(None, ge=0, description="Jardín m²")
    bodega_m2: Optional[float] = Field(None, ge=0, description="Bodega m²")


class CaracteristicasInput(BaseModel):
    """Características constructivas"""
    tipo_estructura: Optional[TipoEstructuraEnum] = Field(None)
    calidad_terminaciones: Optional[CalidadTerminacionesEnum] = Field(None)
    estado_conservacion: Optional[EstadoConservacionEnum] = Field(None)
    ano_construccion: Optional[int] = Field(None, ge=1800, le=2030)
    ano_remodelacion: Optional[int] = Field(None, ge=1800, le=2030)
    pisos_edificio: Optional[int] = Field(None, ge=1, le=200)
    piso_unidad: Optional[int] = Field(None, ge=-10, le=200)
    orientacion: Optional[str] = Field(None, description="N, S, E, O, NE, NO, SE, SO")


class DependenciasInput(BaseModel):
    """Dependencias de la propiedad"""
    dormitorios: int = Field(0, ge=0, le=20)
    banos: int = Field(0, ge=0, le=15)
    banos_visita: int = Field(0, ge=0, le=5)
    living: bool = Field(False)
    comedor: bool = Field(False)
    living_comedor: bool = Field(False)
    cocina: bool = Field(True)
    cocina_americana: bool = Field(False)
    logia: bool = Field(False)
    escritorio: bool = Field(False)
    sala_estar: bool = Field(False)
    walk_in_closet: bool = Field(False)
    dependencias_servicio: int = Field(0, ge=0, le=5)
    bano_servicio: int = Field(0, ge=0, le=3)


class EstacionamientosInput(BaseModel):
    """Información de estacionamientos"""
    cantidad: int = Field(0, ge=0, le=10)
    tipo: Optional[str] = Field(None, description="cubierto, descubierto, subterraneo")
    ubicacion: Optional[str] = Field(None)
    numeros: List[str] = Field(default_factory=list)
    superficie_total_m2: Optional[float] = Field(None, ge=0)
    tiene_bodega: bool = Field(False)
    bodega_m2: Optional[float] = Field(None, ge=0)
    bodega_numero: Optional[str] = Field(None)


class AmenitiesInput(BaseModel):
    """Amenities y servicios"""
    calefaccion: bool = Field(False)
    aire_acondicionado: bool = Field(False)
    chimenea: bool = Field(False)
    piso_radiante: bool = Field(False)
    alarma: bool = Field(False)
    circuito_cerrado: bool = Field(False)
    portero_electrico: bool = Field(False)
    citofono: bool = Field(False)
    control_acceso: bool = Field(False)
    conserje_24h: bool = Field(False)
    ascensor: bool = Field(False)
    cantidad_ascensores: int = Field(0, ge=0, le=20)
    piscina_comun: bool = Field(False)
    gimnasio_comun: bool = Field(False)
    quincho_comun: bool = Field(False)
    sala_eventos: bool = Field(False)
    areas_verdes_comunes: bool = Field(False)
    juegos_infantiles: bool = Field(False)


class CrearFichaRequest(BaseModel):
    """Request para crear ficha de propiedad"""
    rol_sii: str = Field(..., description="Rol SII de la propiedad", pattern=r"^\d+-\d+$")
    tipo_propiedad: TipoPropiedadEnum = Field(..., description="Tipo de propiedad")
    nombre: Optional[str] = Field(None, description="Nombre descriptivo")
    descripcion: Optional[str] = Field(None, description="Descripción detallada")
    ubicacion: UbicacionInput = Field(..., description="Datos de ubicación")
    superficies: Optional[SuperficiesInput] = Field(None)
    caracteristicas: Optional[CaracteristicasInput] = Field(None)
    dependencias: Optional[DependenciasInput] = Field(None)
    estacionamientos: Optional[EstacionamientosInput] = Field(None)
    amenities: Optional[AmenitiesInput] = Field(None)
    expediente_id: Optional[str] = Field(None, description="ID expediente asociado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rol_sii": "1234-567",
                "tipo_propiedad": "departamento",
                "nombre": "Depto 3D2B Las Condes",
                "ubicacion": {
                    "direccion_completa": "Av. Apoquindo 4500, Depto 1201",
                    "comuna": "Las Condes",
                    "region": "Metropolitana",
                    "latitud": -33.4103,
                    "longitud": -70.5831
                },
                "superficies": {
                    "construida_util_m2": 85.5
                }
            }
        }


class ActualizarFichaRequest(BaseModel):
    """Request para actualizar ficha"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    ubicacion: Optional[UbicacionInput] = None
    superficies: Optional[SuperficiesInput] = None
    caracteristicas: Optional[CaracteristicasInput] = None
    dependencias: Optional[DependenciasInput] = None
    estacionamientos: Optional[EstacionamientosInput] = None
    amenities: Optional[AmenitiesInput] = None
    expediente_id: Optional[str] = None


class BuscarComparablesRequest(BaseModel):
    """Request para búsqueda de comparables"""
    radio_km: float = Field(1.0, ge=0.1, le=10.0, description="Radio de búsqueda en km")
    max_resultados: int = Field(10, ge=1, le=50, description="Máximo de resultados")
    solo_venta: bool = Field(True, description="Solo propiedades en venta")
    antiguedad_max_dias: int = Field(180, ge=1, le=365, description="Antigüedad máxima publicación")
    precio_min_uf: Optional[float] = Field(None, ge=0)
    precio_max_uf: Optional[float] = Field(None, ge=0)
    superficie_min_m2: Optional[float] = Field(None, ge=0)
    superficie_max_m2: Optional[float] = Field(None, ge=0)


class EstimarValorRequest(BaseModel):
    """Request para estimación de valor"""
    metodologia: MetodologiaValoracionEnum = Field(
        MetodologiaValoracionEnum.COMPARABLES,
        description="Metodología de valoración"
    )
    forzar_recalculo: bool = Field(False, description="Forzar recálculo ignorando caché")
    incluir_detalle_ajustes: bool = Field(True, description="Incluir detalle de ajustes")


# ============================================================================
# SCHEMAS PYDANTIC - RESPONSES
# ============================================================================

class UbicacionResponse(BaseModel):
    """Response de ubicación"""
    direccion_completa: str
    numero: Optional[str] = None
    departamento: Optional[str] = None
    piso: Optional[int] = None
    comuna: str
    region: str
    codigo_postal: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    manzana: Optional[str] = None
    sitio: Optional[str] = None
    unidad_vecinal: Optional[str] = None
    distrito_censal: Optional[str] = None


class IdentificacionSIIResponse(BaseModel):
    """Response identificación SII"""
    rol_sii: str
    rol_avaluo: Optional[str] = None
    rol_matriz: Optional[str] = None
    comuna_sii: Optional[str] = None
    manzana_sii: Optional[str] = None
    predio_sii: Optional[str] = None
    serie: Optional[str] = None
    destino_sii: Optional[str] = None
    destino_descripcion: Optional[str] = None
    propietario_rut: Optional[str] = None
    propietario_nombre: Optional[str] = None
    fecha_ultimo_avaluo: Optional[date] = None


class SuperficiesResponse(BaseModel):
    """Response de superficies"""
    terreno_m2: Optional[float] = None
    terreno_escritura_m2: Optional[float] = None
    terreno_municipal_m2: Optional[float] = None
    terreno_sii_m2: Optional[float] = None
    construida_total_m2: Optional[float] = None
    construida_util_m2: Optional[float] = None
    construida_comun_m2: Optional[float] = None
    construida_sii_m2: Optional[float] = None
    terraza_m2: Optional[float] = None
    jardin_m2: Optional[float] = None
    estacionamientos_m2: Optional[float] = None
    bodega_m2: Optional[float] = None
    piscina_m2: Optional[float] = None
    coeficiente_copropiedad: Optional[float] = None
    alicuota: Optional[float] = None


class CaracteristicasResponse(BaseModel):
    """Response características constructivas"""
    tipo_estructura: Optional[str] = None
    calidad_terminaciones: Optional[str] = None
    estado_conservacion: Optional[str] = None
    ano_construccion: Optional[int] = None
    ano_remodelacion: Optional[int] = None
    pisos_edificio: Optional[int] = None
    piso_unidad: Optional[int] = None
    orientacion: Optional[str] = None
    vista: Optional[str] = None
    iluminacion_natural: Optional[str] = None
    ventilacion: Optional[str] = None
    aislacion_termica: Optional[str] = None
    aislacion_acustica: Optional[str] = None
    eficiencia_energetica: Optional[str] = None
    certificacion_energetica_id: Optional[str] = None


class DependenciasResponse(BaseModel):
    """Response dependencias"""
    dormitorios: int = 0
    banos: int = 0
    banos_visita: int = 0
    living: bool = False
    comedor: bool = False
    living_comedor: bool = False
    cocina: bool = True
    cocina_americana: bool = False
    logia: bool = False
    escritorio: bool = False
    sala_estar: bool = False
    walk_in_closet: bool = False
    despensa: bool = False
    lavadero: bool = False
    quincho: bool = False
    sala_juegos: bool = False
    gimnasio_privado: bool = False
    sauna: bool = False
    dependencias_servicio: int = 0
    bano_servicio: int = 0


class EstacionamientosResponse(BaseModel):
    """Response estacionamientos"""
    cantidad: int = 0
    tipo: Optional[str] = None
    ubicacion: Optional[str] = None
    numeros: List[str] = []
    superficie_total_m2: Optional[float] = None
    tiene_bodega: bool = False
    bodega_m2: Optional[float] = None
    bodega_numero: Optional[str] = None


class AmenitiesResponse(BaseModel):
    """Response amenities"""
    calefaccion: bool = False
    aire_acondicionado: bool = False
    chimenea: bool = False
    piso_radiante: bool = False
    agua_caliente: Optional[str] = None
    gas: Optional[str] = None
    alarma: bool = False
    circuito_cerrado: bool = False
    portero_electrico: bool = False
    citofono: bool = False
    control_acceso: bool = False
    conserje_24h: bool = False
    ascensor: bool = False
    cantidad_ascensores: int = 0
    piscina_comun: bool = False
    gimnasio_comun: bool = False
    quincho_comun: bool = False
    sala_eventos: bool = False
    areas_verdes_comunes: bool = False
    juegos_infantiles: bool = False
    cancha_deportiva: bool = False
    sauna_comun: bool = False
    lavanderia_comun: bool = False
    bicicletero: bool = False
    salon_multiuso: bool = False


class InformacionUrbanisticaResponse(BaseModel):
    """Response información urbanística"""
    zona: Optional[str] = None
    zona_secundaria: Optional[str] = None
    uso_suelo_permitido: List[str] = []
    uso_suelo_prohibido: List[str] = []
    coeficiente_constructibilidad: Optional[float] = None
    coeficiente_ocupacion_suelo: Optional[float] = None
    densidad_maxima: Optional[float] = None
    altura_maxima_m: Optional[float] = None
    pisos_maximos: Optional[int] = None
    antejardin_minimo_m: Optional[float] = None
    rasante: Optional[str] = None
    adosamiento_permitido: Optional[bool] = None
    distancia_medianeros_m: Optional[float] = None
    zona_inundable: bool = False
    zona_proteccion: bool = False
    zona_patrimonial: bool = False
    zona_riesgo: bool = False
    restricciones_adicionales: List[str] = []
    plan_regulador_vigente: Optional[str] = None
    fecha_aprobacion_prc: Optional[date] = None


class GravamenResponse(BaseModel):
    """Response gravamen"""
    tipo: str
    institucion: Optional[str] = None
    monto_uf: Optional[float] = None
    fecha_inscripcion: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    numero_inscripcion: Optional[str] = None
    foja: Optional[int] = None
    numero: Optional[int] = None
    ano: Optional[int] = None
    vigente: bool = True
    observaciones: Optional[str] = None


class InformacionLegalResponse(BaseModel):
    """Response información legal"""
    estado: str
    inscripcion_dominio: Optional[str] = None
    foja: Optional[int] = None
    numero: Optional[int] = None
    ano: Optional[int] = None
    conservador: Optional[str] = None
    fecha_inscripcion: Optional[date] = None
    titulo_anterior: Optional[str] = None
    gravamenes: List[GravamenResponse] = []
    prohibiciones: List[str] = []
    litigios_pendientes: bool = False
    litigios_detalle: Optional[str] = None
    expropiacion_afecta: bool = False
    expropiacion_detalle: Optional[str] = None
    limitaciones_dominio: List[str] = []
    servidumbres: List[str] = []


class TransaccionResponse(BaseModel):
    """Response transacción histórica"""
    tipo: str
    fecha: date
    precio_uf: Optional[float] = None
    precio_clp: Optional[int] = None
    comprador: Optional[str] = None
    vendedor: Optional[str] = None
    notaria: Optional[str] = None
    repertorio: Optional[str] = None
    inscripcion_cbr: Optional[str] = None
    fuente: str
    observaciones: Optional[str] = None


class AvaluoFiscalResponse(BaseModel):
    """Response avalúo fiscal"""
    avaluo_total_clp: Optional[int] = None
    avaluo_terreno_clp: Optional[int] = None
    avaluo_construccion_clp: Optional[int] = None
    avaluo_total_uf: Optional[float] = None
    avaluo_terreno_uf: Optional[float] = None
    avaluo_construccion_uf: Optional[float] = None
    fecha_avaluo: Optional[date] = None
    exento_contribuciones: bool = False
    monto_contribuciones_semestral: Optional[int] = None
    destino_catastral: Optional[str] = None
    material_predominante: Optional[str] = None
    calidad_construccion: Optional[str] = None


class ValorMercadoResponse(BaseModel):
    """Response valor de mercado estimado"""
    valor_uf: float
    valor_uf_m2: float
    valor_clp: int
    fecha_estimacion: datetime
    metodologia: str
    fuente: str
    confianza: float = Field(..., ge=0, le=1, description="Nivel de confianza 0-1")
    rango_inferior_uf: float
    rango_superior_uf: float
    comparables_utilizados: int
    ajustes_aplicados: Dict[str, float] = {}


class ComparableMercadoResponse(BaseModel):
    """Response comparable de mercado"""
    id: str
    direccion: str
    comuna: str
    distancia_m: float
    tipo_propiedad: str
    superficie_util_m2: float
    dormitorios: int
    banos: int
    estacionamientos: int
    ano_construccion: Optional[int] = None
    precio_uf: float
    precio_uf_m2: float
    tipo_operacion: str
    fecha_publicacion: date
    dias_publicado: int
    fuente: str
    url: Optional[str] = None
    similitud_score: float = Field(..., ge=0, le=1)


class IndicadoresMercadoResponse(BaseModel):
    """Response indicadores de mercado"""
    precio_m2_promedio_uf: float
    precio_m2_mediana_uf: float
    precio_m2_min_uf: float
    precio_m2_max_uf: float
    desviacion_estandar: float
    oferta_activa: int
    transacciones_ultimo_ano: int
    dias_promedio_venta: int
    tasa_absorcion: Optional[float] = None
    tendencia_precios: str
    variacion_anual_pct: float
    segmento_mercado: str
    liquidez: str
    fecha_actualizacion: datetime


class DepreciacionResponse(BaseModel):
    """Response depreciación"""
    depreciacion_acumulada_pct: float
    vida_util_remanente_anos: int
    valor_reposicion_uf: Optional[float] = None
    ano_construccion: int
    antiguedad_anos: int
    tipo_estructura: str
    tasa_depreciacion_anual: float


class FichaResponse(BaseModel):
    """Response completo de ficha de propiedad"""
    id: str
    codigo: str
    rol_sii: str
    tipo_propiedad: str
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    ubicacion: UbicacionResponse
    identificacion_sii: Optional[IdentificacionSIIResponse] = None
    superficies: SuperficiesResponse
    caracteristicas: Optional[CaracteristicasResponse] = None
    dependencias: Optional[DependenciasResponse] = None
    estacionamientos: Optional[EstacionamientosResponse] = None
    amenities: Optional[AmenitiesResponse] = None
    informacion_urbanistica: Optional[InformacionUrbanisticaResponse] = None
    informacion_legal: Optional[InformacionLegalResponse] = None
    historial_transacciones: List[TransaccionResponse] = []
    avaluo_fiscal: Optional[AvaluoFiscalResponse] = None
    valor_mercado: Optional[ValorMercadoResponse] = None
    comparables: List[ComparableMercadoResponse] = []
    indicadores_mercado: Optional[IndicadoresMercadoResponse] = None
    depreciacion: Optional[DepreciacionResponse] = None
    expediente_id: Optional[str] = None
    fuentes_datos: List[str] = []
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    actualizado_por: Optional[str] = None
    version: int = 1
    completitud_pct: float = 0.0


class FichaResumenResponse(BaseModel):
    """Response resumen de ficha (para listados)"""
    id: str
    codigo: str
    rol_sii: str
    tipo_propiedad: str
    nombre: Optional[str] = None
    direccion: str
    comuna: str
    region: str
    superficie_util_m2: Optional[float] = None
    dormitorios: Optional[int] = None
    banos: Optional[int] = None
    estacionamientos: Optional[int] = None
    ano_construccion: Optional[int] = None
    valor_uf: Optional[float] = None
    valor_uf_m2: Optional[float] = None
    completitud_pct: float
    fecha_actualizacion: datetime


class BusquedaFichasResponse(BaseModel):
    """Response búsqueda de fichas"""
    resultados: List[FichaResumenResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


class SincronizacionResponse(BaseModel):
    """Response sincronización con fuente externa"""
    exito: bool
    fuente: str
    datos_actualizados: Dict[str, Any]
    campos_modificados: List[str]
    fecha_sincronizacion: datetime
    mensaje: Optional[str] = None


class ReporteFichaResponse(BaseModel):
    """Response reporte de ficha"""
    ficha_id: str
    codigo: str
    formato: str
    secciones: List[str]
    contenido: Dict[str, Any]
    generado_en: datetime
    url_descarga: Optional[str] = None


class EstadisticasFichasResponse(BaseModel):
    """Response estadísticas de fichas"""
    total_fichas: int
    por_tipo: Dict[str, int]
    por_comuna: Dict[str, int]
    por_estado_legal: Dict[str, int]
    completitud_promedio: float
    valor_total_uf: float
    valor_promedio_uf: float
    superficie_total_m2: float
    fichas_con_gravamenes: int
    fichas_sincronizadas_sii: int
    fichas_sincronizadas_cbr: int
    fecha_calculo: datetime


# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(
    prefix="/ficha-propiedad",
    tags=["Ficha Propiedad - M01"],
    responses={
        400: {"description": "Datos inválidos"},
        401: {"description": "No autenticado"},
        403: {"description": "Sin permisos"},
        404: {"description": "Ficha no encontrada"},
        500: {"description": "Error interno"}
    }
)


# ============================================================================
# MOCK SERVICE (Simulación para desarrollo)
# ============================================================================

class MockFichaService:
    """Servicio mock para desarrollo - Será reemplazado por importación real"""
    
    def __init__(self):
        self.fichas = {}
        self._init_datos_ejemplo()
    
    def _init_datos_ejemplo(self):
        """Inicializa datos de ejemplo"""
        from datetime import datetime
        
        ficha_ejemplo = {
            "id": "fp-001",
            "codigo": "FP-2026-000001",
            "rol_sii": "1234-567",
            "tipo_propiedad": "departamento",
            "nombre": "Depto 3D2B Las Condes",
            "descripcion": "Departamento de 3 dormitorios en Las Condes",
            "ubicacion": {
                "direccion_completa": "Av. Apoquindo 4500, Depto 1201",
                "numero": "4500",
                "departamento": "1201",
                "piso": 12,
                "comuna": "Las Condes",
                "region": "Metropolitana",
                "codigo_postal": "7550000",
                "latitud": -33.4103,
                "longitud": -70.5831
            },
            "identificacion_sii": {
                "rol_sii": "1234-567",
                "rol_avaluo": "1234-567-001",
                "comuna_sii": "Las Condes",
                "manzana_sii": "1234",
                "predio_sii": "567",
                "destino_sii": "H",
                "destino_descripcion": "Habitacional",
                "propietario_nombre": "Juan Pérez González",
                "fecha_ultimo_avaluo": "2024-01-15"
            },
            "superficies": {
                "terreno_m2": None,
                "construida_total_m2": 98.5,
                "construida_util_m2": 85.5,
                "construida_comun_m2": 13.0,
                "terraza_m2": 12.0,
                "bodega_m2": 4.0
            },
            "caracteristicas": {
                "tipo_estructura": "hormigon_armado",
                "calidad_terminaciones": "alta",
                "estado_conservacion": "excelente",
                "ano_construccion": 2018,
                "pisos_edificio": 25,
                "piso_unidad": 12,
                "orientacion": "NO",
                "vista": "Cordillera",
                "eficiencia_energetica": "B"
            },
            "dependencias": {
                "dormitorios": 3,
                "banos": 2,
                "banos_visita": 1,
                "living": True,
                "comedor": True,
                "cocina": True,
                "cocina_americana": False,
                "logia": True,
                "escritorio": True
            },
            "estacionamientos": {
                "cantidad": 2,
                "tipo": "subterraneo",
                "numeros": ["E-1201A", "E-1201B"],
                "tiene_bodega": True,
                "bodega_m2": 4.0,
                "bodega_numero": "B-1201"
            },
            "amenities": {
                "calefaccion": True,
                "aire_acondicionado": True,
                "alarma": True,
                "circuito_cerrado": True,
                "portero_electrico": True,
                "citofono": True,
                "control_acceso": True,
                "conserje_24h": True,
                "ascensor": True,
                "cantidad_ascensores": 4,
                "piscina_comun": True,
                "gimnasio_comun": True,
                "quincho_comun": True,
                "sala_eventos": True,
                "areas_verdes_comunes": True,
                "juegos_infantiles": True
            },
            "informacion_urbanistica": {
                "zona": "ZR2",
                "uso_suelo_permitido": ["residencial", "equipamiento_menor"],
                "uso_suelo_prohibido": ["industrial", "comercio_mayor"],
                "coeficiente_constructibilidad": 4.0,
                "coeficiente_ocupacion_suelo": 0.6,
                "densidad_maxima": 1200,
                "altura_maxima_m": 80,
                "pisos_maximos": 25,
                "zona_inundable": False,
                "zona_proteccion": False,
                "plan_regulador_vigente": "PRC Las Condes 2019"
            },
            "informacion_legal": {
                "estado": "con_hipoteca",
                "inscripcion_dominio": "Foja 1234 N° 567 Año 2018",
                "foja": 1234,
                "numero": 567,
                "ano": 2018,
                "conservador": "Santiago",
                "fecha_inscripcion": "2018-03-15",
                "gravamenes": [
                    {
                        "tipo": "hipoteca",
                        "institucion": "Banco de Chile",
                        "monto_uf": 3500,
                        "fecha_inscripcion": "2018-03-15",
                        "vigente": True
                    }
                ],
                "prohibiciones": [],
                "litigios_pendientes": False,
                "expropiacion_afecta": False
            },
            "avaluo_fiscal": {
                "avaluo_total_uf": 4200,
                "avaluo_terreno_uf": 1800,
                "avaluo_construccion_uf": 2400,
                "fecha_avaluo": "2024-01-15",
                "exento_contribuciones": False,
                "monto_contribuciones_semestral": 450000,
                "destino_catastral": "H",
                "material_predominante": "Hormigón",
                "calidad_construccion": "Superior"
            },
            "valor_mercado": {
                "valor_uf": 8500,
                "valor_uf_m2": 99.42,
                "valor_clp": 310250000,
                "fecha_estimacion": datetime.now().isoformat(),
                "metodologia": "comparables",
                "fuente": "DATAPOLIS",
                "confianza": 0.85,
                "rango_inferior_uf": 7650,
                "rango_superior_uf": 9350,
                "comparables_utilizados": 8,
                "ajustes_aplicados": {
                    "conservacion": 1.05,
                    "antiguedad": 0.98,
                    "terminaciones": 1.12,
                    "estacionamientos": 1.04
                }
            },
            "comparables": [
                {
                    "id": "comp-001",
                    "direccion": "Av. Apoquindo 4200",
                    "comuna": "Las Condes",
                    "distancia_m": 300,
                    "tipo_propiedad": "departamento",
                    "superficie_util_m2": 82.0,
                    "dormitorios": 3,
                    "banos": 2,
                    "estacionamientos": 2,
                    "ano_construccion": 2017,
                    "precio_uf": 8200,
                    "precio_uf_m2": 100.0,
                    "tipo_operacion": "venta",
                    "fecha_publicacion": "2026-01-15",
                    "dias_publicado": 17,
                    "fuente": "Portal Inmobiliario",
                    "similitud_score": 0.92
                }
            ],
            "indicadores_mercado": {
                "precio_m2_promedio_uf": 98.5,
                "precio_m2_mediana_uf": 97.2,
                "precio_m2_min_uf": 85.0,
                "precio_m2_max_uf": 115.0,
                "desviacion_estandar": 8.5,
                "oferta_activa": 45,
                "transacciones_ultimo_ano": 120,
                "dias_promedio_venta": 65,
                "tasa_absorcion": 2.7,
                "tendencia_precios": "alza",
                "variacion_anual_pct": 4.2,
                "segmento_mercado": "premium",
                "liquidez": "alta",
                "fecha_actualizacion": datetime.now().isoformat()
            },
            "depreciacion": {
                "depreciacion_acumulada_pct": 5.6,
                "vida_util_remanente_anos": 73,
                "valor_reposicion_uf": 2540,
                "ano_construccion": 2018,
                "antiguedad_anos": 7,
                "tipo_estructura": "hormigon_armado",
                "tasa_depreciacion_anual": 0.8
            },
            "expediente_id": "exp-001",
            "fuentes_datos": ["sii", "cbr", "portal_inmobiliario"],
            "fecha_creacion": datetime.now().isoformat(),
            "fecha_actualizacion": datetime.now().isoformat(),
            "actualizado_por": "sistema",
            "version": 3,
            "completitud_pct": 92.5
        }
        
        self.fichas["fp-001"] = ficha_ejemplo
        self.fichas["1234-567"] = ficha_ejemplo  # Index por rol
    
    def crear_ficha(self, datos: dict) -> dict:
        from datetime import datetime
        import uuid
        
        ficha_id = f"fp-{uuid.uuid4().hex[:8]}"
        codigo = f"FP-2026-{len(self.fichas):06d}"
        
        ficha = {
            "id": ficha_id,
            "codigo": codigo,
            "rol_sii": datos["rol_sii"],
            "tipo_propiedad": datos["tipo_propiedad"],
            "nombre": datos.get("nombre"),
            "descripcion": datos.get("descripcion"),
            "ubicacion": datos["ubicacion"],
            "superficies": datos.get("superficies", {}),
            "caracteristicas": datos.get("caracteristicas", {}),
            "dependencias": datos.get("dependencias", {}),
            "estacionamientos": datos.get("estacionamientos", {}),
            "amenities": datos.get("amenities", {}),
            "expediente_id": datos.get("expediente_id"),
            "fuentes_datos": ["usuario"],
            "fecha_creacion": datetime.now().isoformat(),
            "fecha_actualizacion": datetime.now().isoformat(),
            "version": 1,
            "completitud_pct": 25.0
        }
        
        self.fichas[ficha_id] = ficha
        self.fichas[datos["rol_sii"]] = ficha
        
        return ficha
    
    def obtener_ficha(self, ficha_id: str) -> Optional[dict]:
        return self.fichas.get(ficha_id)
    
    def actualizar_ficha(self, ficha_id: str, datos: dict) -> Optional[dict]:
        if ficha_id not in self.fichas:
            return None
        
        ficha = self.fichas[ficha_id]
        for key, value in datos.items():
            if value is not None:
                if isinstance(value, dict) and key in ficha and isinstance(ficha[key], dict):
                    ficha[key].update(value)
                else:
                    ficha[key] = value
        
        ficha["fecha_actualizacion"] = datetime.now().isoformat()
        ficha["version"] = ficha.get("version", 1) + 1
        
        return ficha
    
    def eliminar_ficha(self, ficha_id: str) -> bool:
        if ficha_id in self.fichas:
            del self.fichas[ficha_id]
            return True
        return False
    
    def buscar_fichas(self, **filtros) -> tuple:
        resultados = list(self.fichas.values())
        # Eliminar duplicados por ID
        vistos = set()
        unicos = []
        for f in resultados:
            if f["id"] not in vistos:
                vistos.add(f["id"])
                unicos.append(f)
        
        return unicos[:filtros.get("limite", 20)], len(unicos)
    
    def sincronizar_sii(self, ficha_id: str) -> dict:
        return {
            "exito": True,
            "fuente": "SII",
            "datos_actualizados": {
                "rol_avaluo": "1234-567-001",
                "destino_sii": "H",
                "avaluo_total_uf": 4200
            },
            "campos_modificados": ["identificacion_sii", "avaluo_fiscal"],
            "fecha_sincronizacion": datetime.now().isoformat()
        }
    
    def sincronizar_cbr(self, ficha_id: str) -> dict:
        return {
            "exito": True,
            "fuente": "CBR",
            "datos_actualizados": {
                "inscripcion_dominio": "Foja 1234 N° 567 Año 2018",
                "estado_legal": "con_hipoteca",
                "gravamenes_count": 1
            },
            "campos_modificados": ["informacion_legal"],
            "fecha_sincronizacion": datetime.now().isoformat()
        }
    
    def buscar_comparables(self, ficha_id: str, params: dict) -> List[dict]:
        return self.fichas.get("fp-001", {}).get("comparables", [])
    
    def estimar_valor(self, ficha_id: str, metodologia: str) -> dict:
        ficha = self.fichas.get(ficha_id, self.fichas.get("fp-001", {}))
        return ficha.get("valor_mercado", {})
    
    def obtener_indicadores(self, ficha_id: str) -> dict:
        ficha = self.fichas.get(ficha_id, self.fichas.get("fp-001", {}))
        return ficha.get("indicadores_mercado", {})


# Instancia global del servicio mock
_mock_service = MockFichaService()


def get_ficha_service():
    """Dependency injection para servicio de fichas"""
    return _mock_service


# ============================================================================
# ENDPOINTS - GESTIÓN DE FICHAS
# ============================================================================

@router.post(
    "/",
    response_model=FichaResponse,
    status_code=201,
    summary="Crear nueva ficha de propiedad",
    description="Crea una nueva ficha técnica de propiedad inmobiliaria"
)
async def crear_ficha(
    request: CrearFichaRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_ficha_service)
):
    """
    Crear nueva ficha de propiedad.
    
    Genera automáticamente:
    - Código único FP-YYYY-NNNNNN
    - Cálculo de completitud inicial
    - Vinculación a expediente si se proporciona
    """
    try:
        ficha = service.crear_ficha(request.model_dump())
        
        # Programar sincronización automática en background
        # background_tasks.add_task(sync_external_sources, ficha["id"])
        
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": f"Ficha {ficha['codigo']} creada exitosamente",
                "data": ficha
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{ficha_id}",
    response_model=FichaResponse,
    summary="Obtener ficha por ID",
    description="Recupera una ficha de propiedad por su ID o código"
)
async def obtener_ficha(
    ficha_id: str = Path(..., description="ID o código de la ficha"),
    incluir_comparables: bool = Query(True, description="Incluir comparables de mercado"),
    incluir_historial: bool = Query(True, description="Incluir historial de transacciones"),
    service = Depends(get_ficha_service)
):
    """
    Obtener ficha de propiedad.
    
    Acepta:
    - ID interno (fp-xxxxxxxx)
    - Código (FP-2026-NNNNNN)
    - Rol SII (NNNN-NNN)
    """
    ficha = service.obtener_ficha(ficha_id)
    
    if not ficha:
        raise HTTPException(
            status_code=404,
            detail=f"Ficha {ficha_id} no encontrada"
        )
    
    # Filtrar secciones si no se requieren
    if not incluir_comparables:
        ficha = {**ficha, "comparables": []}
    if not incluir_historial:
        ficha = {**ficha, "historial_transacciones": []}
    
    return ficha


@router.get(
    "/rol/{rol_sii}",
    response_model=FichaResponse,
    summary="Obtener ficha por Rol SII",
    description="Recupera una ficha de propiedad por su Rol SII"
)
async def obtener_ficha_por_rol(
    rol_sii: str = Path(..., description="Rol SII de la propiedad", pattern=r"^\d+-\d+$"),
    service = Depends(get_ficha_service)
):
    """Obtener ficha por Rol SII (ej: 1234-567)"""
    ficha = service.obtener_ficha(rol_sii)
    
    if not ficha:
        raise HTTPException(
            status_code=404,
            detail=f"Ficha con Rol SII {rol_sii} no encontrada"
        )
    
    return ficha


@router.put(
    "/{ficha_id}",
    response_model=FichaResponse,
    summary="Actualizar ficha",
    description="Actualiza una ficha de propiedad existente"
)
async def actualizar_ficha(
    ficha_id: str = Path(..., description="ID de la ficha"),
    request: ActualizarFichaRequest = Body(...),
    service = Depends(get_ficha_service)
):
    """
    Actualizar ficha de propiedad.
    
    Solo actualiza los campos proporcionados.
    Incrementa automáticamente la versión.
    """
    ficha = service.actualizar_ficha(ficha_id, request.model_dump(exclude_none=True))
    
    if not ficha:
        raise HTTPException(
            status_code=404,
            detail=f"Ficha {ficha_id} no encontrada"
        )
    
    return ficha


@router.delete(
    "/{ficha_id}",
    status_code=204,
    summary="Eliminar ficha",
    description="Elimina una ficha de propiedad (soft delete)"
)
async def eliminar_ficha(
    ficha_id: str = Path(..., description="ID de la ficha"),
    service = Depends(get_ficha_service)
):
    """Eliminar ficha de propiedad (marca como eliminada)"""
    eliminado = service.eliminar_ficha(ficha_id)
    
    if not eliminado:
        raise HTTPException(
            status_code=404,
            detail=f"Ficha {ficha_id} no encontrada"
        )
    
    return None


# ============================================================================
# ENDPOINTS - BÚSQUEDA
# ============================================================================

@router.get(
    "/",
    response_model=BusquedaFichasResponse,
    summary="Buscar fichas",
    description="Búsqueda avanzada de fichas de propiedades"
)
async def buscar_fichas(
    q: Optional[str] = Query(None, description="Búsqueda por texto"),
    tipo_propiedad: Optional[TipoPropiedadEnum] = Query(None, description="Filtrar por tipo"),
    comuna: Optional[str] = Query(None, description="Filtrar por comuna"),
    region: Optional[str] = Query(None, description="Filtrar por región"),
    precio_min_uf: Optional[float] = Query(None, ge=0, description="Precio mínimo UF"),
    precio_max_uf: Optional[float] = Query(None, ge=0, description="Precio máximo UF"),
    superficie_min_m2: Optional[float] = Query(None, ge=0, description="Superficie mínima m²"),
    superficie_max_m2: Optional[float] = Query(None, ge=0, description="Superficie máxima m²"),
    dormitorios_min: Optional[int] = Query(None, ge=0, description="Dormitorios mínimo"),
    ano_construccion_min: Optional[int] = Query(None, description="Año construcción mínimo"),
    estado_conservacion: Optional[EstadoConservacionEnum] = Query(None),
    estado_legal: Optional[EstadoLegalEnum] = Query(None),
    ordenar_por: str = Query("fecha_actualizacion", description="Campo para ordenar"),
    orden: OrdenEnum = Query(OrdenEnum.DESC, description="Orden"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    service = Depends(get_ficha_service)
):
    """
    Búsqueda avanzada de fichas de propiedades.
    
    Filtros combinables:
    - Texto libre (dirección, nombre, descripción)
    - Tipo de propiedad
    - Ubicación (comuna, región)
    - Rango de precios
    - Rango de superficies
    - Características (dormitorios, año, estado)
    """
    resultados, total = service.buscar_fichas(
        query=q,
        tipo_propiedad=tipo_propiedad.value if tipo_propiedad else None,
        comuna=comuna,
        region=region,
        precio_min_uf=precio_min_uf,
        precio_max_uf=precio_max_uf,
        superficie_min_m2=superficie_min_m2,
        superficie_max_m2=superficie_max_m2,
        dormitorios_min=dormitorios_min,
        ano_construccion_min=ano_construccion_min,
        ordenar_por=ordenar_por,
        orden=orden.value,
        limite=por_pagina,
        offset=(pagina - 1) * por_pagina
    )
    
    # Convertir a resumen
    resumenes = []
    for r in resultados:
        ubicacion = r.get("ubicacion", {})
        superficies = r.get("superficies", {})
        dependencias = r.get("dependencias", {})
        estacionamientos = r.get("estacionamientos", {})
        valor = r.get("valor_mercado", {})
        caracteristicas = r.get("caracteristicas", {})
        
        resumenes.append(FichaResumenResponse(
            id=r["id"],
            codigo=r["codigo"],
            rol_sii=r["rol_sii"],
            tipo_propiedad=r["tipo_propiedad"],
            nombre=r.get("nombre"),
            direccion=ubicacion.get("direccion_completa", ""),
            comuna=ubicacion.get("comuna", ""),
            region=ubicacion.get("region", ""),
            superficie_util_m2=superficies.get("construida_util_m2"),
            dormitorios=dependencias.get("dormitorios"),
            banos=dependencias.get("banos"),
            estacionamientos=estacionamientos.get("cantidad"),
            ano_construccion=caracteristicas.get("ano_construccion"),
            valor_uf=valor.get("valor_uf"),
            valor_uf_m2=valor.get("valor_uf_m2"),
            completitud_pct=r.get("completitud_pct", 0),
            fecha_actualizacion=datetime.fromisoformat(r.get("fecha_actualizacion", datetime.now().isoformat()))
        ))
    
    total_paginas = (total + por_pagina - 1) // por_pagina if total > 0 else 1
    
    return BusquedaFichasResponse(
        resultados=resumenes,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas
    )


# ============================================================================
# ENDPOINTS - SINCRONIZACIÓN EXTERNA
# ============================================================================

@router.post(
    "/{ficha_id}/sincronizar/sii",
    response_model=SincronizacionResponse,
    summary="Sincronizar con SII",
    description="Sincroniza datos de la ficha con el Servicio de Impuestos Internos"
)
async def sincronizar_sii(
    ficha_id: str = Path(..., description="ID de la ficha"),
    forzar: bool = Query(False, description="Forzar sincronización aunque datos estén actualizados"),
    service = Depends(get_ficha_service)
):
    """
    Sincroniza información con el SII:
    - Avalúo fiscal (terreno, construcción)
    - Rol de avalúo
    - Destino catastral
    - Datos del propietario
    - Contribuciones
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    resultado = service.sincronizar_sii(ficha_id)
    
    return SincronizacionResponse(
        exito=resultado["exito"],
        fuente=resultado["fuente"],
        datos_actualizados=resultado["datos_actualizados"],
        campos_modificados=resultado["campos_modificados"],
        fecha_sincronizacion=datetime.fromisoformat(resultado["fecha_sincronizacion"]),
        mensaje="Sincronización exitosa con SII"
    )


@router.post(
    "/{ficha_id}/sincronizar/cbr",
    response_model=SincronizacionResponse,
    summary="Sincronizar con CBR",
    description="Sincroniza datos de la ficha con el Conservador de Bienes Raíces"
)
async def sincronizar_cbr(
    ficha_id: str = Path(..., description="ID de la ficha"),
    service = Depends(get_ficha_service)
):
    """
    Sincroniza información con el CBR:
    - Inscripción de dominio
    - Gravámenes e hipotecas
    - Prohibiciones
    - Historial de transacciones
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    resultado = service.sincronizar_cbr(ficha_id)
    
    return SincronizacionResponse(
        exito=resultado["exito"],
        fuente=resultado["fuente"],
        datos_actualizados=resultado["datos_actualizados"],
        campos_modificados=resultado["campos_modificados"],
        fecha_sincronizacion=datetime.fromisoformat(resultado["fecha_sincronizacion"]),
        mensaje="Sincronización exitosa con CBR"
    )


@router.post(
    "/{ficha_id}/sincronizar/dom",
    response_model=SincronizacionResponse,
    summary="Sincronizar con DOM",
    description="Sincroniza información urbanística con la Dirección de Obras Municipales"
)
async def sincronizar_dom(
    ficha_id: str = Path(..., description="ID de la ficha"),
    service = Depends(get_ficha_service)
):
    """
    Sincroniza información con la DOM:
    - Zona del PRC
    - Usos de suelo permitidos/prohibidos
    - Coeficientes de constructibilidad
    - Restricciones urbanísticas
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    return SincronizacionResponse(
        exito=True,
        fuente="DOM",
        datos_actualizados={
            "zona": "ZR2",
            "coeficiente_constructibilidad": 4.0,
            "usos_permitidos": ["residencial", "equipamiento_menor"]
        },
        campos_modificados=["informacion_urbanistica"],
        fecha_sincronizacion=datetime.now(),
        mensaje="Sincronización exitosa con DOM"
    )


@router.post(
    "/{ficha_id}/sincronizar/todos",
    summary="Sincronizar todas las fuentes",
    description="Sincroniza la ficha con todas las fuentes externas disponibles"
)
async def sincronizar_todos(
    ficha_id: str = Path(..., description="ID de la ficha"),
    background_tasks: BackgroundTasks = None,
    service = Depends(get_ficha_service)
):
    """
    Sincroniza con todas las fuentes externas:
    - SII (avalúo fiscal)
    - CBR (información legal)
    - DOM (información urbanística)
    
    La sincronización se ejecuta en background.
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    return {
        "status": "processing",
        "message": "Sincronización iniciada con todas las fuentes",
        "ficha_id": ficha_id,
        "fuentes": ["SII", "CBR", "DOM"],
        "estimado_minutos": 2
    }


# ============================================================================
# ENDPOINTS - VALORIZACIÓN Y MERCADO
# ============================================================================

@router.post(
    "/{ficha_id}/comparables",
    response_model=List[ComparableMercadoResponse],
    summary="Buscar comparables",
    description="Busca propiedades comparables en el mercado"
)
async def buscar_comparables(
    ficha_id: str = Path(..., description="ID de la ficha"),
    request: BuscarComparablesRequest = Body(...),
    service = Depends(get_ficha_service)
):
    """
    Busca comparables de mercado para la propiedad.
    
    Fuentes:
    - Portal Inmobiliario
    - Yapo
    - TocToc
    - Transacciones CBR
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    comparables = service.buscar_comparables(ficha_id, request.model_dump())
    
    return [ComparableMercadoResponse(
        id=c["id"],
        direccion=c["direccion"],
        comuna=c["comuna"],
        distancia_m=c["distancia_m"],
        tipo_propiedad=c["tipo_propiedad"],
        superficie_util_m2=c["superficie_util_m2"],
        dormitorios=c["dormitorios"],
        banos=c["banos"],
        estacionamientos=c["estacionamientos"],
        ano_construccion=c.get("ano_construccion"),
        precio_uf=c["precio_uf"],
        precio_uf_m2=c["precio_uf_m2"],
        tipo_operacion=c["tipo_operacion"],
        fecha_publicacion=date.fromisoformat(c["fecha_publicacion"]),
        dias_publicado=c["dias_publicado"],
        fuente=c["fuente"],
        url=c.get("url"),
        similitud_score=c["similitud_score"]
    ) for c in comparables]


@router.post(
    "/{ficha_id}/valoracion",
    response_model=ValorMercadoResponse,
    summary="Estimar valor de mercado",
    description="Calcula el valor de mercado estimado de la propiedad"
)
async def estimar_valor(
    ficha_id: str = Path(..., description="ID de la ficha"),
    request: EstimarValorRequest = Body(...),
    service = Depends(get_ficha_service)
):
    """
    Estima el valor de mercado usando metodología seleccionada.
    
    Metodologías:
    - comparables: Análisis de propiedades similares
    - hedonico: Modelo de regresión hedónica
    - flujos: Descuento de flujos para inversión
    - costo: Costo de reposición depreciado
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    valor = service.estimar_valor(ficha_id, request.metodologia.value)
    
    return ValorMercadoResponse(
        valor_uf=valor["valor_uf"],
        valor_uf_m2=valor["valor_uf_m2"],
        valor_clp=valor["valor_clp"],
        fecha_estimacion=datetime.fromisoformat(valor["fecha_estimacion"]),
        metodologia=valor["metodologia"],
        fuente=valor["fuente"],
        confianza=valor["confianza"],
        rango_inferior_uf=valor["rango_inferior_uf"],
        rango_superior_uf=valor["rango_superior_uf"],
        comparables_utilizados=valor["comparables_utilizados"],
        ajustes_aplicados=valor.get("ajustes_aplicados", {})
    )


@router.get(
    "/{ficha_id}/indicadores-mercado",
    response_model=IndicadoresMercadoResponse,
    summary="Obtener indicadores de mercado",
    description="Obtiene indicadores agregados del mercado inmobiliario local"
)
async def obtener_indicadores_mercado(
    ficha_id: str = Path(..., description="ID de la ficha"),
    service = Depends(get_ficha_service)
):
    """
    Obtiene indicadores de mercado para la zona de la propiedad:
    - Precios promedio/mediana/rango
    - Oferta activa
    - Transacciones históricas
    - Días promedio en mercado
    - Tendencia de precios
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    indicadores = service.obtener_indicadores(ficha_id)
    
    return IndicadoresMercadoResponse(
        precio_m2_promedio_uf=indicadores["precio_m2_promedio_uf"],
        precio_m2_mediana_uf=indicadores["precio_m2_mediana_uf"],
        precio_m2_min_uf=indicadores["precio_m2_min_uf"],
        precio_m2_max_uf=indicadores["precio_m2_max_uf"],
        desviacion_estandar=indicadores["desviacion_estandar"],
        oferta_activa=indicadores["oferta_activa"],
        transacciones_ultimo_ano=indicadores["transacciones_ultimo_ano"],
        dias_promedio_venta=indicadores["dias_promedio_venta"],
        tasa_absorcion=indicadores.get("tasa_absorcion"),
        tendencia_precios=indicadores["tendencia_precios"],
        variacion_anual_pct=indicadores["variacion_anual_pct"],
        segmento_mercado=indicadores["segmento_mercado"],
        liquidez=indicadores["liquidez"],
        fecha_actualizacion=datetime.fromisoformat(indicadores["fecha_actualizacion"])
    )


# ============================================================================
# ENDPOINTS - REPORTES
# ============================================================================

@router.get(
    "/{ficha_id}/reporte",
    response_model=ReporteFichaResponse,
    summary="Generar reporte",
    description="Genera un reporte detallado de la ficha de propiedad"
)
async def generar_reporte(
    ficha_id: str = Path(..., description="ID de la ficha"),
    formato: str = Query("json", description="Formato: json, pdf, xlsx"),
    secciones: List[str] = Query(
        default=["general", "ubicacion", "superficies", "caracteristicas", "legal", "valoracion"],
        description="Secciones a incluir"
    ),
    service = Depends(get_ficha_service)
):
    """
    Genera reporte detallado de la ficha.
    
    Secciones disponibles:
    - general: Datos básicos
    - ubicacion: Ubicación y coordenadas
    - superficies: Superficies detalladas
    - caracteristicas: Características constructivas
    - legal: Información legal y gravámenes
    - valoracion: Avalúo y valor de mercado
    """
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    contenido = {}
    
    if "general" in secciones:
        contenido["general"] = {
            "codigo": ficha.get("codigo"),
            "rol_sii": ficha.get("rol_sii"),
            "tipo_propiedad": ficha.get("tipo_propiedad"),
            "nombre": ficha.get("nombre"),
            "completitud_pct": ficha.get("completitud_pct"),
            "fuentes_datos": ficha.get("fuentes_datos", []),
            "version": ficha.get("version")
        }
    
    if "ubicacion" in secciones:
        contenido["ubicacion"] = ficha.get("ubicacion", {})
    
    if "superficies" in secciones:
        contenido["superficies"] = ficha.get("superficies", {})
    
    if "caracteristicas" in secciones:
        contenido["caracteristicas"] = {
            **ficha.get("caracteristicas", {}),
            **ficha.get("dependencias", {}),
            **ficha.get("estacionamientos", {}),
            **ficha.get("amenities", {})
        }
    
    if "legal" in secciones:
        contenido["legal"] = ficha.get("informacion_legal", {})
    
    if "valoracion" in secciones:
        contenido["valoracion"] = {
            "avaluo_fiscal": ficha.get("avaluo_fiscal", {}),
            "valor_mercado": ficha.get("valor_mercado", {}),
            "indicadores_mercado": ficha.get("indicadores_mercado", {}),
            "depreciacion": ficha.get("depreciacion", {})
        }
    
    return ReporteFichaResponse(
        ficha_id=ficha_id,
        codigo=ficha.get("codigo", ""),
        formato=formato,
        secciones=secciones,
        contenido=contenido,
        generado_en=datetime.now(),
        url_descarga=f"/api/v1/ficha-propiedad/{ficha_id}/reporte/download?formato={formato}" if formato != "json" else None
    )


@router.get(
    "/{ficha_id}/reporte/download",
    summary="Descargar reporte",
    description="Descarga el reporte en el formato especificado"
)
async def descargar_reporte(
    ficha_id: str = Path(..., description="ID de la ficha"),
    formato: str = Query("pdf", description="Formato: pdf, xlsx"),
    service = Depends(get_ficha_service)
):
    """Descarga el reporte en PDF o Excel"""
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    # En producción, generar archivo real
    contenido = json.dumps(ficha, default=str, indent=2)
    
    if formato == "pdf":
        return StreamingResponse(
            io.BytesIO(contenido.encode()),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="ficha_{ficha_id}.pdf"'}
        )
    else:
        return StreamingResponse(
            io.BytesIO(contenido.encode()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="ficha_{ficha_id}.xlsx"'}
        )


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================================================

@router.get(
    "/estadisticas/global",
    response_model=EstadisticasFichasResponse,
    summary="Estadísticas globales",
    description="Obtiene estadísticas agregadas de todas las fichas"
)
async def obtener_estadisticas(
    usuario_id: Optional[str] = Query(None, description="Filtrar por usuario"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin"),
    service = Depends(get_ficha_service)
):
    """
    Obtiene estadísticas agregadas:
    - Total de fichas
    - Distribución por tipo y comuna
    - Completitud promedio
    - Valor total del portafolio
    - Fichas con gravámenes
    """
    return EstadisticasFichasResponse(
        total_fichas=150,
        por_tipo={
            "departamento": 85,
            "casa": 35,
            "oficina": 15,
            "local_comercial": 10,
            "terreno": 5
        },
        por_comuna={
            "Las Condes": 45,
            "Providencia": 30,
            "Vitacura": 25,
            "Ñuñoa": 20,
            "Santiago": 15,
            "Otras": 15
        },
        por_estado_legal={
            "limpio": 95,
            "con_hipoteca": 45,
            "con_prohibicion": 8,
            "en_sucesion": 2
        },
        completitud_promedio=78.5,
        valor_total_uf=1250000,
        valor_promedio_uf=8333,
        superficie_total_m2=15000,
        fichas_con_gravamenes=53,
        fichas_sincronizadas_sii=140,
        fichas_sincronizadas_cbr=125,
        fecha_calculo=datetime.now()
    )


# ============================================================================
# ENDPOINTS - VINCULACIÓN CON EXPEDIENTES
# ============================================================================

@router.post(
    "/{ficha_id}/vincular-expediente/{expediente_id}",
    summary="Vincular con expediente",
    description="Vincula la ficha de propiedad con un expediente"
)
async def vincular_expediente(
    ficha_id: str = Path(..., description="ID de la ficha"),
    expediente_id: str = Path(..., description="ID del expediente"),
    service = Depends(get_ficha_service)
):
    """Vincula la ficha con un expediente del módulo M00"""
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    service.actualizar_ficha(ficha_id, {"expediente_id": expediente_id})
    
    return {
        "status": "success",
        "message": f"Ficha {ficha_id} vinculada a expediente {expediente_id}",
        "ficha_id": ficha_id,
        "expediente_id": expediente_id
    }


@router.delete(
    "/{ficha_id}/vincular-expediente",
    summary="Desvincular expediente",
    description="Desvincula la ficha de su expediente asociado"
)
async def desvincular_expediente(
    ficha_id: str = Path(..., description="ID de la ficha"),
    service = Depends(get_ficha_service)
):
    """Desvincula la ficha de su expediente"""
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    expediente_anterior = ficha.get("expediente_id")
    service.actualizar_ficha(ficha_id, {"expediente_id": None})
    
    return {
        "status": "success",
        "message": f"Ficha {ficha_id} desvinculada del expediente {expediente_anterior}",
        "ficha_id": ficha_id,
        "expediente_anterior": expediente_anterior
    }


# ============================================================================
# ENDPOINTS - HISTORIAL Y AUDITORÍA
# ============================================================================

@router.get(
    "/{ficha_id}/historial",
    summary="Historial de cambios",
    description="Obtiene el historial de cambios de la ficha"
)
async def obtener_historial(
    ficha_id: str = Path(..., description="ID de la ficha"),
    limite: int = Query(50, ge=1, le=200, description="Máximo de registros"),
    service = Depends(get_ficha_service)
):
    """Obtiene el historial de cambios de la ficha"""
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    return {
        "ficha_id": ficha_id,
        "version_actual": ficha.get("version", 1),
        "historial": [
            {
                "version": 3,
                "fecha": "2026-01-30T10:30:00",
                "usuario": "sistema",
                "accion": "sincronizacion_sii",
                "campos_modificados": ["avaluo_fiscal"],
                "detalle": "Actualización automática avalúo fiscal"
            },
            {
                "version": 2,
                "fecha": "2026-01-25T14:20:00",
                "usuario": "admin",
                "accion": "actualizacion",
                "campos_modificados": ["caracteristicas", "amenities"],
                "detalle": "Actualización datos constructivos"
            },
            {
                "version": 1,
                "fecha": "2026-01-15T09:00:00",
                "usuario": "admin",
                "accion": "creacion",
                "campos_modificados": ["todos"],
                "detalle": "Creación inicial de ficha"
            }
        ],
        "total": 3
    }


@router.get(
    "/{ficha_id}/version/{version}",
    summary="Obtener versión específica",
    description="Obtiene una versión específica de la ficha"
)
async def obtener_version(
    ficha_id: str = Path(..., description="ID de la ficha"),
    version: int = Path(..., ge=1, description="Número de versión"),
    service = Depends(get_ficha_service)
):
    """Obtiene una versión específica de la ficha para comparación"""
    ficha = service.obtener_ficha(ficha_id)
    if not ficha:
        raise HTTPException(status_code=404, detail=f"Ficha {ficha_id} no encontrada")
    
    if version > ficha.get("version", 1):
        raise HTTPException(
            status_code=404,
            detail=f"Versión {version} no existe. Versión actual: {ficha.get('version', 1)}"
        )
    
    # En producción, recuperar versión histórica
    return {
        "ficha_id": ficha_id,
        "version": version,
        "datos": ficha,
        "nota": "Datos de la versión actual (histórico no implementado en mock)"
    }
