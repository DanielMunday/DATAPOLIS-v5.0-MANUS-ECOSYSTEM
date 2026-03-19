# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Valorización
=====================================
Modelos Pydantic para M04 Valorización
Compliance: IVS 2022, NCh 3499
Versión: 3.0.0
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import (
    BaseSchema, ResponseBase, GeoPoint, Direccion, 
    TipoPropiedad, EstadoPropiedad, Moneda, RangoValor,
    ROLPropiedad, InscripcionCBR
)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class PropositoValorizacion(str, Enum):
    """Propósito de la valorización (IVS 104)"""
    COMPRAVENTA = "compraventa"
    GARANTIA_HIPOTECARIA = "garantia_hipotecaria"
    GARANTIA_BANCARIA = "garantia_bancaria"
    CONTABLE = "contable"
    TRIBUTARIO = "tributario"
    SEGURO = "seguro"
    EXPROPIACION = "expropiacion"
    LIQUIDACION = "liquidacion"
    FUSION_ADQUISICION = "fusion_adquisicion"
    SUCESION = "sucesion"
    ARRIENDO = "arriendo"
    INVERSION = "inversion"


class MetodoValorizacion(str, Enum):
    """Métodos de valorización IVS"""
    COMPARACION_MERCADO = "comparacion_mercado"
    CAPITALIZACION_RENTAS = "capitalizacion_rentas"
    COSTO_REPOSICION = "costo_reposicion"
    RESIDUAL = "residual"
    FLUJO_CAJA_DESCONTADO = "flujo_caja_descontado"
    HIBRIDO = "hibrido"


class TipoValor(str, Enum):
    """Tipo de valor determinado"""
    MERCADO = "mercado"
    INVERSION = "inversion"
    LIQUIDACION = "liquidacion"
    JUSTO = "justo"
    ESPECIAL = "especial"
    SINERGICO = "sinergico"


class NivelConfianza(str, Enum):
    """Nivel de confianza de la valorización"""
    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"


class CertificacionEnergetica(str, Enum):
    """Certificación energética CEV"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    SIN_CERTIFICAR = "sin_certificar"


# =============================================================================
# SCHEMAS DE ENTRADA - PROPIEDAD
# =============================================================================

class CaracteristicasTerreno(BaseSchema):
    """Características del terreno"""
    superficie_m2: float = Field(..., gt=0)
    forma: str = Field(default="regular", description="regular, irregular, esquina")
    frente_ml: Optional[float] = Field(None, gt=0)
    fondo_ml: Optional[float] = Field(None, gt=0)
    topografia: str = Field(default="plano", description="plano, pendiente, accidentado")
    pendiente_pct: Optional[float] = Field(None, ge=0, le=100)
    
    # Urbanización
    urbanizado: bool = True
    servicios: List[str] = Field(
        default=["agua", "alcantarillado", "electricidad"],
        description="Servicios disponibles"
    )
    
    # Restricciones
    linea_edificacion: Optional[float] = None
    rasante: Optional[float] = None
    afectaciones: List[str] = []


class CaracteristicasConstruccion(BaseSchema):
    """Características de la construcción"""
    superficie_construida_m2: float = Field(..., gt=0)
    superficie_util_m2: Optional[float] = Field(None, gt=0)
    
    # Distribución
    dormitorios: int = Field(default=0, ge=0)
    baños: int = Field(default=0, ge=0)
    estacionamientos: int = Field(default=0, ge=0)
    bodegas: int = Field(default=0, ge=0)
    
    # Características
    año_construccion: int = Field(..., ge=1800, le=2100)
    pisos: int = Field(default=1, ge=1)
    piso_ubicacion: Optional[int] = Field(None, ge=0)
    orientacion: Optional[str] = None
    vista: Optional[str] = None
    
    # Calidad
    calidad_construccion: str = Field(
        default="media",
        description="economica, media, buena, muy_buena, lujo"
    )
    estado_conservacion: EstadoPropiedad = EstadoPropiedad.BUENO
    
    # Eficiencia
    certificacion_energetica: Optional[CertificacionEnergetica] = None
    
    # Terminaciones
    terminaciones: Dict[str, str] = Field(
        default={},
        description="Ej: {pisos: porcelanato, cocina: equipada}"
    )
    
    # Amenities
    amenities: List[str] = Field(
        default=[],
        description="Ej: piscina, quincho, gimnasio"
    )


class DatosUbicacion(BaseSchema):
    """Datos de ubicación para valorización"""
    direccion: Direccion
    ubicacion: Optional[GeoPoint] = None
    
    # Zonificación
    zona_prc: Optional[str] = Field(None, description="Zona según PRC")
    uso_suelo: Optional[str] = None
    densidad_permitida: Optional[float] = None
    coeficiente_constructibilidad: Optional[float] = None
    coeficiente_ocupacion: Optional[float] = None
    altura_maxima: Optional[float] = None
    
    # Entorno
    nivel_socioeconomico: Optional[str] = Field(None, description="ABC1, C2, C3, D, E")
    cercania_metro: Optional[float] = Field(None, description="Distancia en metros")
    cercania_comercio: Optional[float] = None
    cercania_areas_verdes: Optional[float] = None
    
    # Riesgos zona
    zona_inundacion: bool = False
    zona_sismica: Optional[str] = Field(None, description="Zona sísmica NCh 433")
    zona_tsunami: bool = False


class DatosLegales(BaseSchema):
    """Datos legales de la propiedad"""
    rol: ROLPropiedad
    inscripcion_cbr: Optional[InscripcionCBR] = None
    
    # Estado títulos
    titulo_saneado: bool = True
    gravamenes: List[str] = []
    hipotecas_vigentes: int = Field(default=0, ge=0)
    monto_hipotecas_uf: Optional[Decimal] = None
    prohibiciones: List[str] = []
    litigios_pendientes: bool = False
    
    # Permisos
    permiso_edificacion: Optional[str] = None
    recepcion_municipal: bool = True
    fecha_recepcion: Optional[date] = None


class DatosArriendo(BaseSchema):
    """Datos de arriendo actual o potencial"""
    arrendado: bool = False
    canon_mensual: Optional[Decimal] = Field(None, gt=0)
    moneda_canon: Moneda = Moneda.CLP
    
    # Contrato
    fecha_inicio_contrato: Optional[date] = None
    fecha_termino_contrato: Optional[date] = None
    tipo_contrato: Optional[str] = Field(None, description="plazo_fijo, indefinido")
    
    # Arrendatario
    tipo_arrendatario: Optional[str] = Field(None, description="persona, empresa")
    antiguedad_arrendatario_meses: Optional[int] = None
    
    # Historial
    vacancia_historica_pct: Optional[float] = Field(None, ge=0, le=100)
    morosidad_historica_pct: Optional[float] = Field(None, ge=0, le=100)


# =============================================================================
# REQUEST PRINCIPAL
# =============================================================================

class ValorizacionRequest(BaseSchema):
    """Request para valorización de propiedad"""
    # Identificación
    propiedad_id: Optional[UUID] = None
    referencia_cliente: Optional[str] = Field(None, max_length=50)
    
    # Tipo y propósito
    tipo_propiedad: TipoPropiedad
    proposito: PropositoValorizacion
    tipo_valor: TipoValor = TipoValor.MERCADO
    
    # Datos propiedad
    ubicacion: DatosUbicacion
    terreno: Optional[CaracteristicasTerreno] = None
    construccion: CaracteristicasConstruccion
    legal: Optional[DatosLegales] = None
    arriendo: Optional[DatosArriendo] = None
    
    # Configuración
    metodos_preferidos: List[MetodoValorizacion] = Field(
        default=[MetodoValorizacion.COMPARACION_MERCADO]
    )
    incluir_analisis_mercado: bool = True
    incluir_proyeccion: bool = False
    horizonte_proyeccion_años: int = Field(default=5, ge=1, le=30)
    
    # Fecha
    fecha_valoracion: date = Field(default_factory=date.today)
    
    @model_validator(mode="after")
    def validate_terreno_for_types(self):
        """Terreno requerido para casas, parcelas, terrenos"""
        if self.tipo_propiedad in [TipoPropiedad.CASA, TipoPropiedad.TERRENO, TipoPropiedad.PARCELA]:
            if not self.terreno:
                raise ValueError(f"terreno es requerido para tipo {self.tipo_propiedad}")
        return self


class ComparablesRequest(BaseSchema):
    """Request para búsqueda de comparables"""
    propiedad_id: Optional[UUID] = None
    
    # Ubicación
    ubicacion: GeoPoint
    radio_km: float = Field(default=1.0, ge=0.1, le=10.0)
    
    # Filtros
    tipo_propiedad: TipoPropiedad
    superficie_min: Optional[float] = None
    superficie_max: Optional[float] = None
    dormitorios: Optional[int] = None
    antiguedad_maxima_años: Optional[int] = None
    
    # Período
    meses_atras: int = Field(default=12, ge=3, le=36)
    
    # Configuración
    max_comparables: int = Field(default=10, ge=5, le=50)
    incluir_ofertas: bool = True


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ComparableEncontrado(BaseSchema):
    """Comparable encontrado en el mercado"""
    id: str
    fuente: str = Field(..., description="portal_inmobiliario, toc_toc, yapo, cbr")
    
    # Ubicación
    direccion: str
    comuna: str
    distancia_km: float
    
    # Características
    tipo_propiedad: TipoPropiedad
    superficie_util_m2: float
    superficie_terreno_m2: Optional[float] = None
    dormitorios: int
    baños: int
    estacionamientos: int
    año_construccion: Optional[int] = None
    
    # Precio
    precio_uf: Decimal
    precio_m2_uf: Decimal
    tipo_operacion: str = Field(..., description="venta, arriendo")
    
    # Fecha
    fecha_publicacion: date
    fecha_transaccion: Optional[date] = None
    es_transaccion_real: bool = False
    
    # Ajustes
    factor_ajuste: float = Field(default=1.0)
    precio_ajustado_uf: Optional[Decimal] = None
    
    # Similitud
    score_similitud: float = Field(..., ge=0, le=1)


class ResultadoMetodo(BaseSchema):
    """Resultado de un método de valorización"""
    metodo: MetodoValorizacion
    
    # Valor
    valor_uf: Decimal
    valor_clp: Decimal
    valor_m2_uf: Decimal
    
    # Confianza
    nivel_confianza: NivelConfianza
    peso_ponderacion: float = Field(..., ge=0, le=1)
    
    # Rango
    valor_minimo_uf: Decimal
    valor_maximo_uf: Decimal
    
    # Detalle método
    parametros: Dict[str, any] = {}
    comparables_usados: Optional[int] = None
    tasa_capitalizacion: Optional[float] = None
    factor_obsolescencia: Optional[float] = None


class AnalisisMercado(BaseSchema):
    """Análisis de mercado de la zona"""
    # Oferta/demanda
    total_ofertas_zona: int
    oferta_similar: int
    dias_promedio_mercado: float
    absorcion_mensual: float
    
    # Precios zona
    precio_m2_promedio_uf: Decimal
    precio_m2_mediana_uf: Decimal
    precio_m2_min_uf: Decimal
    precio_m2_max_uf: Decimal
    
    # Tendencia
    tendencia_12m: str = Field(..., description="alza, baja, estable")
    variacion_12m_pct: float
    
    # Competencia
    proyectos_nuevos_zona: int
    stock_nuevo_unidades: int


class ProyeccionValor(BaseSchema):
    """Proyección de valor futuro"""
    año: int
    valor_proyectado_uf: Decimal
    valor_minimo_uf: Decimal
    valor_maximo_uf: Decimal
    tasa_apreciacion_anual: float
    
    # Escenarios
    escenario: str = Field(default="base", description="pesimista, base, optimista")


class FactorRiesgoValorizacion(BaseSchema):
    """Factor de riesgo identificado"""
    tipo: str
    descripcion: str
    impacto: str = Field(..., description="bajo, medio, alto")
    ajuste_valor_pct: Optional[float] = None


class ResultadoValorizacion(BaseSchema):
    """Resultado completo de valorización"""
    # Identificación
    id: UUID
    fecha_valoracion: date
    fecha_emision: datetime
    
    # Propiedad
    propiedad_id: Optional[UUID] = None
    direccion_completa: str
    tipo_propiedad: TipoPropiedad
    
    # Valores principales
    valor_mercado_uf: Decimal
    valor_mercado_clp: Decimal
    valor_m2_uf: Decimal
    
    # Rango de valor
    valor_minimo_uf: Decimal
    valor_maximo_uf: Decimal
    rango_confianza_pct: float = Field(default=95.0)
    
    # Métodos aplicados
    metodos_aplicados: List[ResultadoMetodo]
    metodo_principal: MetodoValorizacion
    
    # Comparables
    comparables: List[ComparableEncontrado]
    total_comparables_analizados: int
    
    # Análisis
    analisis_mercado: Optional[AnalisisMercado] = None
    proyecciones: Optional[List[ProyeccionValor]] = None
    
    # Riesgos
    riesgos_identificados: List[FactorRiesgoValorizacion]
    
    # Confianza
    nivel_confianza: NivelConfianza
    score_confianza: float = Field(..., ge=0, le=1)
    completitud_datos_pct: float
    
    # Compliance
    cumple_ivs: bool = True
    version_ivs: str = "2022"
    disclaimer: str
    
    # Tasador
    requiere_validacion_humana: bool
    tasador_asignado: Optional[str] = None
    
    # Procesamiento
    tiempo_procesamiento_ms: float


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

class ValorizacionResponse(ResponseBase[ResultadoValorizacion]):
    """Respuesta de valorización"""
    pass


class ComparablesResponse(ResponseBase[List[ComparableEncontrado]]):
    """Respuesta de búsqueda de comparables"""
    pass


class AnalisisMercadoResponse(ResponseBase[AnalisisMercado]):
    """Respuesta de análisis de mercado"""
    pass


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "PropositoValorizacion",
    "MetodoValorizacion",
    "TipoValor",
    "NivelConfianza",
    "CertificacionEnergetica",
    
    # Input schemas
    "CaracteristicasTerreno",
    "CaracteristicasConstruccion",
    "DatosUbicacion",
    "DatosLegales",
    "DatosArriendo",
    
    # Requests
    "ValorizacionRequest",
    "ComparablesRequest",
    
    # Data schemas
    "ComparableEncontrado",
    "ResultadoMetodo",
    "AnalisisMercado",
    "ProyeccionValor",
    "FactorRiesgoValorizacion",
    "ResultadoValorizacion",
    
    # Responses
    "ValorizacionResponse",
    "ComparablesResponse",
    "AnalisisMercadoResponse",
]
