# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Credit Score
=====================================
Modelos Pydantic para M03 Credit Score Inmobiliario
Scoring multidimensional con explicabilidad SHAP
Versión: 3.0.0
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import (
    BaseSchema, ResponseBase, GeoPoint, TipoPropiedad, 
    NivelRiesgo, ROLPropiedad
)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class CategoriaScore(str, Enum):
    """Categorías de score crediticio inmobiliario"""
    AAA = "AAA"  # 900-1000: Excelente
    AA = "AA"    # 800-899: Muy bueno
    A = "A"      # 700-799: Bueno
    BBB = "BBB"  # 600-699: Aceptable
    BB = "BB"    # 500-599: Regular
    B = "B"      # 400-499: Inferior
    CCC = "CCC"  # 300-399: Débil
    CC = "CC"    # 200-299: Muy débil
    C = "C"      # 100-199: Extremadamente débil
    D = "D"      # 0-99: Default/Inaceptable


class DimensionScore(str, Enum):
    """Dimensiones de evaluación"""
    UBICACION = "ubicacion"
    LEGAL = "legal"
    FINANCIERO = "financiero"
    TECNICO = "tecnico"
    MERCADO = "mercado"


class TipoRiesgo(str, Enum):
    """Tipos de riesgo identificados"""
    TITULO = "titulo"
    GRAVAMEN = "gravamen"
    LITIGIO = "litigio"
    URBANISTICO = "urbanistico"
    AMBIENTAL = "ambiental"
    ESTRUCTURAL = "estructural"
    MERCADO = "mercado"
    LIQUIDEZ = "liquidez"
    REGULATORIO = "regulatorio"
    SISMICO = "sismico"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class DatosUbicacionScore(BaseSchema):
    """Datos de ubicación para scoring"""
    comuna: str
    region: str
    ubicacion: Optional[GeoPoint] = None
    
    # Accesibilidad
    distancia_metro_km: Optional[float] = Field(None, ge=0)
    distancia_centro_km: Optional[float] = Field(None, ge=0)
    
    # Servicios
    indice_servicios: Optional[float] = Field(None, ge=0, le=1)
    
    # Plusvalía histórica
    plusvalia_anual_pct: Optional[float] = None
    
    # Seguridad
    indice_seguridad: Optional[float] = Field(None, ge=0, le=1)
    
    # Riesgo natural
    zona_sismica: Optional[str] = None
    zona_inundacion: bool = False
    zona_tsunami: bool = False


class DatosLegalesScore(BaseSchema):
    """Datos legales para scoring"""
    rol: Optional[ROLPropiedad] = None
    
    # Títulos
    titulo_status: str = Field(
        default="limpio",
        description="limpio, con_observaciones, irregular"
    )
    años_dominio_actual: Optional[int] = Field(None, ge=0)
    
    # Gravámenes
    tiene_hipoteca: bool = False
    monto_hipoteca_uf: Optional[Decimal] = Field(None, ge=0)
    ltv_pct: Optional[float] = Field(None, ge=0, le=200)
    
    # Prohibiciones
    prohibiciones_vigentes: bool = False
    tipo_prohibiciones: List[str] = []
    
    # Embargos
    embargos_vigentes: bool = False
    
    # Litigios
    litigios_pendientes: bool = False
    tipo_litigios: List[str] = []
    
    # Permisos
    tiene_permiso_edificacion: bool = True
    tiene_recepcion_final: bool = True
    cumple_normativa_urbanistica: bool = True


class DatosFinancierosScore(BaseSchema):
    """Datos financieros para scoring"""
    # Valor
    valor_propiedad_uf: Decimal = Field(..., gt=0)
    valor_mercado_uf: Optional[Decimal] = Field(None, gt=0)
    
    # Rentabilidad
    arriendo_mensual_uf: Optional[Decimal] = Field(None, ge=0)
    cap_rate_pct: Optional[float] = Field(None, ge=0, le=20)
    
    # Liquidez
    dias_promedio_mercado: Optional[int] = Field(None, ge=0)
    
    # Morosidad
    morosidad_contribuciones: bool = False
    meses_morosidad: Optional[int] = Field(None, ge=0)
    
    # Gastos
    gastos_comunes_uf: Optional[Decimal] = Field(None, ge=0)
    contribuciones_uf: Optional[Decimal] = Field(None, ge=0)
    
    # Deuda asociada
    deuda_total_uf: Optional[Decimal] = Field(None, ge=0)


class DatosTecnicosScore(BaseSchema):
    """Datos técnicos para scoring"""
    # Construcción
    año_construccion: int = Field(..., ge=1800, le=2100)
    superficie_m2: float = Field(..., gt=0)
    
    # Estado
    estado_conservacion: str = Field(
        default="bueno",
        description="excelente, bueno, regular, malo"
    )
    
    # Calidad
    calidad_construccion: str = Field(
        default="media",
        description="economica, media, buena, muy_buena, lujo"
    )
    
    # Eficiencia
    certificacion_energetica: Optional[str] = None
    
    # Instalaciones
    estado_electrica: str = Field(default="bueno")
    estado_sanitaria: str = Field(default="bueno")
    estado_gas: Optional[str] = None
    
    # Mantención
    ultima_renovacion_año: Optional[int] = None
    requiere_reparaciones: bool = False
    costo_reparaciones_uf: Optional[Decimal] = None


class DatosMercadoScore(BaseSchema):
    """Datos de mercado para scoring"""
    # Demanda
    indice_demanda_zona: Optional[float] = Field(None, ge=0, le=2)
    
    # Tendencia
    tendencia_precios_12m: str = Field(
        default="estable",
        description="alza, baja, estable"
    )
    variacion_precios_12m_pct: Optional[float] = None
    
    # Oferta
    meses_inventario: Optional[float] = Field(None, ge=0)
    competencia_zona: Optional[int] = Field(None, ge=0)
    
    # Proyectos
    proyectos_nuevos_zona: Optional[int] = Field(None, ge=0)
    
    # Tasas
    tasa_hipotecaria_actual: Optional[float] = Field(None, ge=0, le=30)


class CreditScoreRequest(BaseSchema):
    """Request para cálculo de Credit Score"""
    # Identificación
    propiedad_id: Optional[UUID] = None
    referencia: Optional[str] = Field(None, max_length=50)
    
    # Tipo
    tipo_propiedad: TipoPropiedad
    
    # Datos por dimensión
    ubicacion: DatosUbicacionScore
    legal: DatosLegalesScore
    financiero: DatosFinancierosScore
    tecnico: DatosTecnicosScore
    mercado: Optional[DatosMercadoScore] = None
    
    # Configuración
    incluir_explicaciones_shap: bool = True
    incluir_recomendaciones: bool = True
    
    # Fecha evaluación
    fecha_evaluacion: date = Field(default_factory=date.today)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class FactorContribuyente(BaseSchema):
    """Factor que contribuye al score de una dimensión"""
    nombre: str
    valor: float
    impacto: str = Field(..., description="positivo, negativo, neutro")
    puntos: float
    descripcion: Optional[str] = None


class ComponenteScore(BaseSchema):
    """Score de una dimensión"""
    dimension: DimensionScore
    nombre: str
    score: float = Field(..., ge=0, le=1000)
    peso: float = Field(..., ge=0, le=1)
    score_ponderado: float
    
    # Factores
    factores_positivos: List[FactorContribuyente]
    factores_negativos: List[FactorContribuyente]
    
    # Metadata
    completitud_datos_pct: float = Field(..., ge=0, le=100)


class RiesgoIdentificado(BaseSchema):
    """Riesgo identificado en la evaluación"""
    tipo: TipoRiesgo
    severidad: NivelRiesgo
    descripcion: str
    impacto_score: float = Field(..., description="Puntos restados")
    mitigacion_sugerida: Optional[str] = None
    requiere_accion_inmediata: bool = False


class ExplicacionSHAP(BaseSchema):
    """Explicación SHAP de feature importance"""
    feature: str
    valor: float
    shap_value: float
    impacto: str = Field(..., description="positivo, negativo")
    importancia_ranking: int
    descripcion: str


class ResultadoCreditScore(BaseSchema):
    """Resultado completo del Credit Score"""
    # Identificación
    id: UUID
    propiedad_id: Optional[UUID] = None
    fecha_evaluacion: date
    fecha_calculo: datetime
    
    # Score principal
    score_total: float = Field(..., ge=0, le=1000)
    categoria: CategoriaScore
    descripcion_categoria: str
    
    # Componentes
    componentes: List[ComponenteScore]
    
    # Riesgos
    riesgos_identificados: List[RiesgoIdentificado]
    total_riesgos: int
    riesgos_criticos: int
    
    # Explicabilidad SHAP
    explicaciones_shap: Optional[List[ExplicacionSHAP]] = None
    
    # Recomendaciones
    recomendaciones: List[str]
    
    # Confianza
    nivel_confianza: str = Field(..., description="alto, medio, bajo")
    completitud_datos_pct: float
    
    # Comparación
    percentil_mercado: Optional[float] = Field(None, ge=0, le=100)
    score_promedio_zona: Optional[float] = None
    
    # Validación
    requiere_validacion_humana: bool
    motivos_validacion: List[str] = []
    
    # Procesamiento
    tiempo_procesamiento_ms: float
    version_modelo: str


class HistorialScore(BaseSchema):
    """Historial de scores de una propiedad"""
    propiedad_id: UUID
    
    evaluaciones: List[Dict] = Field(
        ...,
        description="Lista de {fecha, score, categoria, cambios}"
    )
    
    tendencia: str = Field(..., description="mejorando, empeorando, estable")
    variacion_ultimo_año: Optional[float] = None


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

class CreditScoreResponse(ResponseBase[ResultadoCreditScore]):
    """Respuesta de Credit Score"""
    pass


class HistorialScoreResponse(ResponseBase[HistorialScore]):
    """Respuesta de historial de scores"""
    pass


class ComparativoScoreResponse(ResponseBase[Dict]):
    """Respuesta de comparativo de scores"""
    pass


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "CategoriaScore",
    "DimensionScore",
    "TipoRiesgo",
    
    # Input schemas
    "DatosUbicacionScore",
    "DatosLegalesScore",
    "DatosFinancierosScore",
    "DatosTecnicosScore",
    "DatosMercadoScore",
    
    # Request
    "CreditScoreRequest",
    
    # Data schemas
    "FactorContribuyente",
    "ComponenteScore",
    "RiesgoIdentificado",
    "ExplicacionSHAP",
    "ResultadoCreditScore",
    "HistorialScore",
    
    # Responses
    "CreditScoreResponse",
    "HistorialScoreResponse",
    "ComparativoScoreResponse",
]
