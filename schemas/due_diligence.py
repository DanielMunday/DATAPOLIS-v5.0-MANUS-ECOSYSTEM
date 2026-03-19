# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Due Diligence
======================================
Modelos Pydantic para M12 Due Diligence Inmobiliario
150+ checks automatizados con HITL
Versión: 3.0.0
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from .base import (
    BaseSchema, ResponseBase, GeoPoint, TipoPropiedad,
    NivelRiesgo, ROLPropiedad, InscripcionCBR, Direccion
)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class EstadoDueDiligence(str, Enum):
    """Estado del proceso de Due Diligence"""
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    CON_OBSERVACIONES = "con_observaciones"
    RECHAZADO = "rechazado"
    CANCELADO = "cancelado"


class AreaDueDiligence(str, Enum):
    """Áreas de evaluación Due Diligence"""
    LEGAL = "legal"
    FINANCIERO = "financiero"
    TECNICO = "tecnico"
    AMBIENTAL = "ambiental"
    URBANISTICO = "urbanistico"
    COMERCIAL = "comercial"


class CriticidadCheck(str, Enum):
    """Nivel de criticidad de un check"""
    CRITICO = "critico"      # Deal breaker
    ALTO = "alto"            # Riesgo significativo
    MEDIO = "medio"          # Requiere atención
    BAJO = "bajo"            # Menor importancia
    INFORMATIVO = "informativo"  # Solo contexto


class EstadoCheck(str, Enum):
    """Estado resultado de un check"""
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    OBSERVADO = "observado"
    PENDIENTE = "pendiente"
    NO_APLICA = "no_aplica"
    ERROR = "error"


class TipoValidacion(str, Enum):
    """Tipo de validación requerida"""
    AUTOMATICA = "automatica"
    SEMI_AUTOMATICA = "semi_automatica"
    MANUAL = "manual"
    EXTERNA = "externa"


class CategoriaDueDiligence(str, Enum):
    """Categoría final del Due Diligence"""
    A = "A"   # Score >= 85%: Apto sin condiciones
    B = "B"   # Score >= 70%: Apto con condiciones menores
    C = "C"   # Score >= 55%: Apto con condiciones mayores
    D = "D"   # Score >= 40%: No recomendado
    F = "F"   # Score < 40% o deal breakers: Rechazado


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class DatosLegalesDueDiligence(BaseSchema):
    """Datos legales para Due Diligence"""
    # Identificación
    rol: ROLPropiedad
    inscripcion_cbr: Optional[InscripcionCBR] = None
    
    # Dominio
    propietario_actual: str
    rut_propietario: str
    tipo_propietario: str = Field(default="natural", description="natural, juridica")
    años_dominio: Optional[int] = None
    
    # Títulos
    escritura_numero: Optional[int] = None
    escritura_fecha: Optional[date] = None
    notaria: Optional[str] = None
    
    # Gravámenes
    hipotecas: List[Dict] = Field(
        default=[],
        description="Lista de {acreedor, monto_uf, fecha_inscripcion}"
    )
    prohibiciones: List[Dict] = Field(
        default=[],
        description="Lista de {tipo, beneficiario, fecha}"
    )
    embargos: List[Dict] = Field(
        default=[],
        description="Lista de {tribunal, causa, fecha}"
    )
    
    # Litigios
    litigios: List[Dict] = Field(
        default=[],
        description="Lista de {tribunal, rit, materia, estado}"
    )
    
    # Arriendos
    arriendos_vigentes: List[Dict] = Field(
        default=[],
        description="Lista de {arrendatario, canon, vencimiento}"
    )


class DatosFinancierosDueDiligence(BaseSchema):
    """Datos financieros para Due Diligence"""
    # Valor
    precio_transaccion_uf: Decimal = Field(..., gt=0)
    avaluo_fiscal_uf: Optional[Decimal] = None
    tasacion_comercial_uf: Optional[Decimal] = None
    
    # Tributario
    contribuciones_anuales_uf: Optional[Decimal] = None
    contribuciones_al_dia: bool = True
    meses_morosidad_contribuciones: int = Field(default=0, ge=0)
    
    # Gastos comunes
    gastos_comunes_uf: Optional[Decimal] = None
    gastos_comunes_al_dia: bool = True
    meses_morosidad_gc: int = Field(default=0, ge=0)
    
    # Ingresos (si aplica)
    arriendo_mensual_uf: Optional[Decimal] = None
    vacancia_pct: Optional[float] = Field(None, ge=0, le=100)


class DatosTecnicosDueDiligence(BaseSchema):
    """Datos técnicos para Due Diligence"""
    # Construcción
    año_construccion: int = Field(..., ge=1800, le=2100)
    superficie_terreno_m2: Optional[float] = None
    superficie_construida_m2: float = Field(..., gt=0)
    
    # Estado
    estado_conservacion: str = Field(
        default="bueno",
        description="excelente, bueno, regular, malo"
    )
    
    # Estructura
    tipo_estructura: str = Field(
        default="hormigon",
        description="hormigon, albanileria, madera, metalica, mixta"
    )
    pisos: int = Field(default=1, ge=1)
    
    # Certificaciones
    tiene_cip: bool = True  # Certificado Instalación Eléctrica
    tiene_certificacion_gas: Optional[bool] = None
    tiene_informe_sanitario: bool = True
    
    # Mantención
    ultima_inspeccion_estructural: Optional[date] = None
    ultima_renovacion: Optional[int] = None  # Año


class DatosAmbientalesDueDiligence(BaseSchema):
    """Datos ambientales para Due Diligence"""
    # Ubicación respecto a riesgos
    zona_sismica: str = Field(default="2", description="Zona sísmica NCh 433")
    en_zona_inundacion: bool = False
    en_zona_tsunami: bool = False
    en_zona_remocion: bool = False
    
    # Contaminación
    suelo_contaminado: Optional[bool] = None
    pasivos_ambientales: List[str] = []
    
    # Permisos ambientales
    requiere_rca: bool = False
    tiene_rca: Optional[bool] = None
    rca_numero: Optional[str] = None


class DatosUrbanisticosDueDiligence(BaseSchema):
    """Datos urbanísticos para Due Diligence"""
    # Permisos
    numero_permiso_edificacion: Optional[str] = None
    fecha_permiso: Optional[date] = None
    tiene_recepcion_final: bool = True
    fecha_recepcion: Optional[date] = None
    
    # Zonificación
    zona_prc: Optional[str] = None
    uso_suelo_permitido: List[str] = []
    uso_actual: Optional[str] = None
    
    # Edificabilidad
    coef_constructibilidad: Optional[float] = None
    coef_ocupacion_suelo: Optional[float] = None
    altura_maxima_m: Optional[float] = None
    
    # Afectaciones
    afecto_expropiacion: bool = False
    afecto_utilidad_publica: bool = False
    servidumbres: List[str] = []


class DatosComercialesDueDiligence(BaseSchema):
    """Datos comerciales para Due Diligence"""
    # Mercado
    precio_m2_zona_uf: Optional[Decimal] = None
    dias_promedio_venta_zona: Optional[int] = None
    indice_demanda: Optional[float] = Field(None, ge=0, le=2)
    
    # Comparables recientes
    comparables_disponibles: int = Field(default=0, ge=0)
    
    # Proyección
    tendencia_zona: str = Field(
        default="estable",
        description="alza, baja, estable"
    )


class DueDiligenceRequest(BaseSchema):
    """Request completo para Due Diligence"""
    # Identificación
    propiedad_id: Optional[UUID] = None
    referencia_transaccion: Optional[str] = Field(None, max_length=50)
    
    # Tipo
    tipo_propiedad: TipoPropiedad
    direccion: Direccion
    
    # Datos por área
    legal: DatosLegalesDueDiligence
    financiero: DatosFinancierosDueDiligence
    tecnico: DatosTecnicosDueDiligence
    ambiental: Optional[DatosAmbientalesDueDiligence] = None
    urbanistico: Optional[DatosUrbanisticosDueDiligence] = None
    comercial: Optional[DatosComercialesDueDiligence] = None
    
    # Configuración
    nivel_profundidad: str = Field(
        default="estandar",
        description="basico, estandar, completo"
    )
    areas_evaluar: Optional[List[AreaDueDiligence]] = None
    timeout_por_check_ms: int = Field(default=30000, ge=5000, le=120000)
    
    # Fecha
    fecha_cierre_prevista: Optional[date] = None


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ResultadoCheck(BaseSchema):
    """Resultado de un check individual"""
    codigo: str = Field(..., description="Ej: LEG-001")
    nombre: str
    area: AreaDueDiligence
    criticidad: CriticidadCheck
    
    # Resultado
    estado: EstadoCheck
    score: float = Field(..., ge=0, le=100)
    
    # Detalle
    hallazgos: List[str]
    observaciones: Optional[str] = None
    fuente_datos: Optional[str] = None
    
    # Validación
    tipo_validacion: TipoValidacion
    validado_por_humano: bool = False
    validador_humano: Optional[str] = None
    fecha_validacion: Optional[datetime] = None
    
    # Tiempo
    tiempo_ejecucion_ms: float


class ResultadoArea(BaseSchema):
    """Resultado agregado de un área"""
    area: AreaDueDiligence
    nombre: str
    
    # Scores
    score: float = Field(..., ge=0, le=100)
    peso: float = Field(..., ge=0, le=1)
    score_ponderado: float
    
    # Checks
    total_checks: int
    checks_aprobados: int
    checks_rechazados: int
    checks_observados: int
    checks_pendientes: int
    
    # Resultados
    resultados_checks: List[ResultadoCheck]
    
    # Resumen
    hallazgos_principales: List[str]
    riesgos_area: List[str]
    recomendaciones_area: List[str]
    
    # Completitud
    completitud_pct: float


class DealBreaker(BaseSchema):
    """Deal breaker identificado"""
    check_codigo: str
    descripcion: str
    severidad: str = "critico"
    puede_mitigarse: bool
    condiciones_mitigacion: Optional[str] = None


class CondicionCierre(BaseSchema):
    """Condición para el cierre de la transacción"""
    tipo: str = Field(..., description="precedente, concurrente, subsecuente")
    descripcion: str
    responsable: str
    plazo_dias: Optional[int] = None
    prioridad: str = Field(default="alta", description="alta, media, baja")


class ResultadoDueDiligence(BaseSchema):
    """Resultado completo del Due Diligence"""
    # Identificación
    id: UUID
    propiedad_id: Optional[UUID] = None
    referencia: Optional[str] = None
    
    # Estado
    estado: EstadoDueDiligence
    
    # Score global
    score_global: float = Field(..., ge=0, le=100)
    categoria: CategoriaDueDiligence
    descripcion_categoria: str
    
    # Resultados por área
    resultados_areas: List[ResultadoArea]
    
    # Totales
    total_checks_ejecutados: int
    checks_aprobados: int
    checks_rechazados: int
    checks_observados: int
    checks_pendientes_validacion: int
    
    # Riesgos
    riesgos_criticos: List[str]
    riesgos_altos: List[str]
    
    # Deal breakers
    deal_breakers: List[DealBreaker]
    tiene_deal_breakers: bool
    
    # Recomendaciones
    recomendaciones: List[str]
    condiciones_cierre: List[CondicionCierre]
    
    # Validación humana
    requiere_validacion_humana: bool
    validadores_requeridos: List[str]
    checks_pendientes_hitl: int
    
    # Integridad
    hash_resultado: str = Field(..., description="SHA-256 del resultado")
    
    # Tiempo
    tiempo_total_ms: float
    fecha_inicio: datetime
    fecha_fin: datetime
    
    # Metadata
    version_proceso: str = "1.0.0"


class ResumenEjecutivo(BaseSchema):
    """Resumen ejecutivo del Due Diligence"""
    # Identificación
    due_diligence_id: UUID
    direccion: str
    
    # Veredicto
    categoria: CategoriaDueDiligence
    recomendacion_general: str
    
    # Scores por área
    scores_areas: Dict[str, float]
    
    # Hallazgos clave
    fortalezas: List[str]
    debilidades: List[str]
    oportunidades: List[str]
    amenazas: List[str]
    
    # Deal breakers
    deal_breakers_resumen: List[str]
    
    # Condiciones
    condiciones_minimas: List[str]
    
    # Fecha
    fecha_emision: datetime


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

class DueDiligenceResponse(ResponseBase[ResultadoDueDiligence]):
    """Respuesta de Due Diligence completo"""
    pass


class CheckResponse(ResponseBase[ResultadoCheck]):
    """Respuesta de check individual"""
    pass


class ResumenEjecutivoResponse(ResponseBase[ResumenEjecutivo]):
    """Respuesta de resumen ejecutivo"""
    pass


class ValidacionHITLResponse(ResponseBase[Dict]):
    """Respuesta de validación HITL"""
    pass


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "EstadoDueDiligence",
    "AreaDueDiligence",
    "CriticidadCheck",
    "EstadoCheck",
    "TipoValidacion",
    "CategoriaDueDiligence",
    
    # Input schemas
    "DatosLegalesDueDiligence",
    "DatosFinancierosDueDiligence",
    "DatosTecnicosDueDiligence",
    "DatosAmbientalesDueDiligence",
    "DatosUrbanisticosDueDiligence",
    "DatosComercialesDueDiligence",
    
    # Request
    "DueDiligenceRequest",
    
    # Data schemas
    "ResultadoCheck",
    "ResultadoArea",
    "DealBreaker",
    "CondicionCierre",
    "ResultadoDueDiligence",
    "ResumenEjecutivo",
    
    # Responses
    "DueDiligenceResponse",
    "CheckResponse",
    "ResumenEjecutivoResponse",
    "ValidacionHITLResponse",
]
