"""
DATAPOLIS v3.0 - Router M06 Mantenciones
=========================================
API REST completa para gestión de mantenciones preventivas y correctivas
de propiedades inmobiliarias, con programación, seguimiento y reporting.

Endpoints (26):
- Gestión de Planes (6): CRUD planes de mantenimiento
- Gestión de Tareas (6): CRUD tareas de mantenimiento
- Ejecución y Seguimiento (6): Programación, asignación, cierre
- Proveedores (4): Gestión de prestadores de servicios
- Reportes y Estadísticas (4): KPIs, costos, cumplimiento

Normativa aplicable:
- NCh 3562:2020 - Gestión de activos inmobiliarios
- Ley 21.442 - Copropiedad inmobiliaria (áreas comunes)
- ISO 41001:2018 - Facility Management

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2025
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Path, Body
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(
    prefix="/mantenciones",
    tags=["M06 - Mantenciones"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Sin permisos"},
        404: {"description": "Recurso no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)

# =============================================================================
# ENUMS
# =============================================================================

class TipoMantencion(str, Enum):
    """Tipos de mantención según naturaleza"""
    preventiva = "preventiva"  # Programada para evitar fallas
    correctiva = "correctiva"  # Reparación de fallas
    predictiva = "predictiva"  # Basada en análisis de condición
    mejorativa = "mejorativa"  # Mejoras y upgrades

class CategoriaMantencion(str, Enum):
    """Categorías de sistemas/áreas de mantención"""
    estructura = "estructura"  # Muros, fundaciones, losas
    techumbre = "techumbre"  # Techo, impermeabilización
    fachada = "fachada"  # Revestimientos exteriores
    electricidad = "electricidad"  # Sistema eléctrico
    gasfiteria = "gasfiteria"  # Agua potable, alcantarillado
    climatizacion = "climatizacion"  # HVAC, calefacción
    gas = "gas"  # Instalaciones de gas
    ascensores = "ascensores"  # Elevadores, escaleras mecánicas
    incendio = "incendio"  # Sistemas contra incendio
    seguridad = "seguridad"  # Alarmas, CCTV, control acceso
    areas_verdes = "areas_verdes"  # Jardines, riego
    piscina = "piscina"  # Piscinas, spa
    estacionamientos = "estacionamientos"  # Portones, demarcación
    limpieza = "limpieza"  # Aseo general
    plagas = "plagas"  # Control de plagas
    pintura = "pintura"  # Pintura interior/exterior
    pisos = "pisos"  # Revestimientos de piso
    ventanas = "ventanas"  # Ventanas, cristales
    otro = "otro"

class PrioridadTarea(str, Enum):
    """Prioridades de tareas de mantención"""
    critica = "critica"  # Atención inmediata (<24h)
    alta = "alta"  # Atención urgente (1-3 días)
    media = "media"  # Atención normal (1-2 semanas)
    baja = "baja"  # Puede esperar (1 mes+)
    programada = "programada"  # Según calendario

class EstadoTarea(str, Enum):
    """Estados del ciclo de vida de una tarea"""
    pendiente = "pendiente"  # Creada, sin asignar
    programada = "programada"  # Con fecha asignada
    asignada = "asignada"  # Asignada a proveedor/técnico
    en_proceso = "en_proceso"  # Trabajo en ejecución
    en_revision = "en_revision"  # Esperando aprobación
    completada = "completada"  # Finalizada exitosamente
    cancelada = "cancelada"  # Anulada
    rechazada = "rechazada"  # No aprobada en revisión

class FrecuenciaMantencion(str, Enum):
    """Frecuencias para mantenciones preventivas"""
    diaria = "diaria"
    semanal = "semanal"
    quincenal = "quincenal"
    mensual = "mensual"
    bimensual = "bimensual"
    trimestral = "trimestral"
    semestral = "semestral"
    anual = "anual"
    bianual = "bianual"
    por_uso = "por_uso"  # Por horas de uso, km, etc.
    por_condicion = "por_condicion"  # Según inspección

class TipoProveedor(str, Enum):
    """Tipos de proveedores de servicios"""
    empresa = "empresa"  # Empresa de servicios
    contratista = "contratista"  # Contratista independiente
    tecnico = "tecnico"  # Técnico individual
    interno = "interno"  # Personal propio
    especialista = "especialista"  # Servicio especializado

class EstadoProveedor(str, Enum):
    """Estados de proveedores"""
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"  # Por incumplimiento
    evaluacion = "evaluacion"  # En período de prueba

class OrdenEnum(str, Enum):
    """Orden de resultados"""
    asc = "asc"
    desc = "desc"

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class CrearPlanMantencionRequest(BaseModel):
    """Request para crear plan de mantención"""
    nombre: str = Field(..., min_length=3, max_length=200, description="Nombre del plan")
    descripcion: Optional[str] = Field(None, max_length=1000, description="Descripción detallada")
    propiedad_id: Optional[str] = Field(None, description="ID de propiedad específica")
    condominio_id: Optional[str] = Field(None, description="ID de condominio (para áreas comunes)")
    tipo: TipoMantencion = Field(..., description="Tipo de mantención")
    categorias: List[CategoriaMantencion] = Field(..., min_items=1, description="Categorías incluidas")
    frecuencia: FrecuenciaMantencion = Field(..., description="Frecuencia de ejecución")
    fecha_inicio: date = Field(..., description="Fecha de inicio del plan")
    fecha_termino: Optional[date] = Field(None, description="Fecha de término (None = indefinido)")
    presupuesto_anual_uf: Optional[Decimal] = Field(None, ge=0, description="Presupuesto anual en UF")
    responsable_id: Optional[str] = Field(None, description="ID del responsable del plan")
    proveedor_preferido_id: Optional[str] = Field(None, description="Proveedor preferido")
    checklist_base: Optional[List[str]] = Field(None, description="Items de checklist por defecto")
    notificar_anticipacion_dias: int = Field(7, ge=1, le=90, description="Días de anticipación para notificar")
    activo: bool = Field(True, description="Plan activo/inactivo")
    
    @validator('fecha_termino')
    def validar_fecha_termino(cls, v, values):
        if v and 'fecha_inicio' in values and v <= values['fecha_inicio']:
            raise ValueError('Fecha de término debe ser posterior a fecha de inicio')
        return v

class ActualizarPlanRequest(BaseModel):
    """Request para actualizar plan de mantención"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    frecuencia: Optional[FrecuenciaMantencion] = None
    fecha_termino: Optional[date] = None
    presupuesto_anual_uf: Optional[Decimal] = Field(None, ge=0)
    responsable_id: Optional[str] = None
    proveedor_preferido_id: Optional[str] = None
    checklist_base: Optional[List[str]] = None
    notificar_anticipacion_dias: Optional[int] = Field(None, ge=1, le=90)
    activo: Optional[bool] = None

class CrearTareaRequest(BaseModel):
    """Request para crear tarea de mantención"""
    titulo: str = Field(..., min_length=3, max_length=200, description="Título de la tarea")
    descripcion: str = Field(..., max_length=2000, description="Descripción detallada")
    plan_id: Optional[str] = Field(None, description="ID del plan origen (si aplica)")
    propiedad_id: Optional[str] = Field(None, description="ID de propiedad")
    condominio_id: Optional[str] = Field(None, description="ID de condominio")
    unidad_id: Optional[str] = Field(None, description="ID de unidad específica")
    tipo: TipoMantencion = Field(..., description="Tipo de mantención")
    categoria: CategoriaMantencion = Field(..., description="Categoría")
    prioridad: PrioridadTarea = Field(PrioridadTarea.media, description="Prioridad")
    fecha_programada: Optional[date] = Field(None, description="Fecha programada de ejecución")
    hora_inicio: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$', description="Hora inicio (HH:MM)")
    hora_fin: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$', description="Hora fin (HH:MM)")
    duracion_estimada_horas: Optional[Decimal] = Field(None, ge=0.5, le=720, description="Duración estimada en horas")
    proveedor_id: Optional[str] = Field(None, description="ID del proveedor asignado")
    presupuesto_uf: Optional[Decimal] = Field(None, ge=0, description="Presupuesto en UF")
    requiere_acceso_unidad: bool = Field(False, description="Requiere acceso a unidad privada")
    requiere_corte_servicios: bool = Field(False, description="Requiere corte de servicios")
    servicios_afectados: Optional[List[str]] = Field(None, description="Servicios que se cortarán")
    checklist: Optional[List[str]] = Field(None, description="Items de checklist")
    archivos_adjuntos: Optional[List[str]] = Field(None, description="URLs de archivos adjuntos")
    solicitante_id: Optional[str] = Field(None, description="ID del solicitante")
    notas_internas: Optional[str] = Field(None, max_length=1000, description="Notas internas")

class ActualizarTareaRequest(BaseModel):
    """Request para actualizar tarea"""
    titulo: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)
    prioridad: Optional[PrioridadTarea] = None
    fecha_programada: Optional[date] = None
    hora_inicio: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$')
    hora_fin: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$')
    duracion_estimada_horas: Optional[Decimal] = Field(None, ge=0.5, le=720)
    proveedor_id: Optional[str] = None
    presupuesto_uf: Optional[Decimal] = Field(None, ge=0)
    checklist: Optional[List[str]] = None
    notas_internas: Optional[str] = Field(None, max_length=1000)

class AsignarTareaRequest(BaseModel):
    """Request para asignar tarea a proveedor"""
    proveedor_id: str = Field(..., description="ID del proveedor")
    fecha_programada: date = Field(..., description="Fecha de ejecución")
    hora_inicio: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$', description="Hora inicio")
    hora_fin: Optional[str] = Field(None, regex=r'^\d{2}:\d{2}$', description="Hora fin")
    presupuesto_acordado_uf: Optional[Decimal] = Field(None, ge=0, description="Presupuesto acordado")
    instrucciones_especiales: Optional[str] = Field(None, max_length=1000, description="Instrucciones")
    notificar_proveedor: bool = Field(True, description="Enviar notificación al proveedor")
    notificar_residentes: bool = Field(False, description="Notificar a residentes afectados")

class CerrarTareaRequest(BaseModel):
    """Request para cerrar/completar tarea"""
    resultado: str = Field(..., description="Descripción del resultado")
    costo_real_uf: Decimal = Field(..., ge=0, description="Costo real en UF")
    duracion_real_horas: Decimal = Field(..., ge=0, description="Duración real en horas")
    checklist_completado: Optional[Dict[str, bool]] = Field(None, description="Estado de checklist")
    observaciones: Optional[str] = Field(None, max_length=2000, description="Observaciones")
    evidencia_fotografica: Optional[List[str]] = Field(None, description="URLs de fotos")
    materiales_utilizados: Optional[List[Dict[str, Any]]] = Field(None, description="Lista de materiales")
    fecha_completado: Optional[datetime] = Field(None, description="Fecha/hora de completado")
    requiere_seguimiento: bool = Field(False, description="Requiere seguimiento posterior")
    fecha_seguimiento: Optional[date] = Field(None, description="Fecha de seguimiento")
    calificacion_proveedor: Optional[int] = Field(None, ge=1, le=5, description="Calificación 1-5")

class CrearProveedorRequest(BaseModel):
    """Request para crear proveedor"""
    rut: str = Field(..., regex=r'^\d{1,2}\.\d{3}\.\d{3}[-][0-9kK]$', description="RUT formato XX.XXX.XXX-X")
    razon_social: str = Field(..., min_length=3, max_length=200, description="Razón social")
    nombre_fantasia: Optional[str] = Field(None, max_length=200, description="Nombre de fantasía")
    tipo: TipoProveedor = Field(..., description="Tipo de proveedor")
    giro: str = Field(..., max_length=200, description="Giro comercial")
    categorias_servicio: List[CategoriaMantencion] = Field(..., min_items=1, description="Categorías que atiende")
    email: str = Field(..., description="Email de contacto")
    telefono: str = Field(..., description="Teléfono de contacto")
    telefono_emergencia: Optional[str] = Field(None, description="Teléfono emergencias 24/7")
    direccion: str = Field(..., max_length=300, description="Dirección")
    comuna: str = Field(..., max_length=100, description="Comuna")
    region: str = Field(..., max_length=100, description="Región")
    representante_legal: Optional[str] = Field(None, max_length=200, description="Representante legal")
    contacto_operativo: Optional[str] = Field(None, max_length=200, description="Contacto operativo")
    email_operativo: Optional[str] = Field(None, description="Email operativo")
    sitio_web: Optional[str] = Field(None, description="Sitio web")
    tiempo_respuesta_horas: Optional[int] = Field(None, ge=1, description="SLA respuesta en horas")
    horario_atencion: Optional[str] = Field(None, description="Horario de atención")
    atiende_emergencias: bool = Field(False, description="Disponible para emergencias 24/7")
    tarifa_hora_uf: Optional[Decimal] = Field(None, ge=0, description="Tarifa por hora en UF")
    tarifa_visita_uf: Optional[Decimal] = Field(None, ge=0, description="Tarifa por visita en UF")
    certificaciones: Optional[List[str]] = Field(None, description="Certificaciones vigentes")
    seguros_vigentes: Optional[List[str]] = Field(None, description="Pólizas de seguro")
    notas: Optional[str] = Field(None, max_length=1000, description="Notas adicionales")

class ActualizarProveedorRequest(BaseModel):
    """Request para actualizar proveedor"""
    razon_social: Optional[str] = Field(None, min_length=3, max_length=200)
    nombre_fantasia: Optional[str] = Field(None, max_length=200)
    giro: Optional[str] = Field(None, max_length=200)
    categorias_servicio: Optional[List[CategoriaMantencion]] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    telefono_emergencia: Optional[str] = None
    direccion: Optional[str] = Field(None, max_length=300)
    comuna: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    contacto_operativo: Optional[str] = Field(None, max_length=200)
    email_operativo: Optional[str] = None
    tiempo_respuesta_horas: Optional[int] = Field(None, ge=1)
    atiende_emergencias: Optional[bool] = None
    tarifa_hora_uf: Optional[Decimal] = Field(None, ge=0)
    tarifa_visita_uf: Optional[Decimal] = Field(None, ge=0)
    certificaciones: Optional[List[str]] = None
    seguros_vigentes: Optional[List[str]] = None
    estado: Optional[EstadoProveedor] = None
    notas: Optional[str] = Field(None, max_length=1000)

class EvaluarProveedorRequest(BaseModel):
    """Request para evaluar proveedor"""
    tarea_id: str = Field(..., description="ID de tarea completada")
    calificacion_calidad: int = Field(..., ge=1, le=5, description="Calidad del trabajo 1-5")
    calificacion_puntualidad: int = Field(..., ge=1, le=5, description="Puntualidad 1-5")
    calificacion_precio: int = Field(..., ge=1, le=5, description="Relación precio/calidad 1-5")
    calificacion_comunicacion: int = Field(..., ge=1, le=5, description="Comunicación 1-5")
    calificacion_limpieza: int = Field(..., ge=1, le=5, description="Limpieza post-trabajo 1-5")
    recomendaria: bool = Field(..., description="¿Recomendaría este proveedor?")
    comentario: Optional[str] = Field(None, max_length=1000, description="Comentario de evaluación")

# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class PlanMantencionResponse(BaseModel):
    """Response de plan de mantención"""
    id: str
    codigo: str  # PM-YYYY-NNNNNN
    nombre: str
    descripcion: Optional[str]
    propiedad_id: Optional[str]
    condominio_id: Optional[str]
    tipo: TipoMantencion
    categorias: List[CategoriaMantencion]
    frecuencia: FrecuenciaMantencion
    fecha_inicio: date
    fecha_termino: Optional[date]
    proxima_ejecucion: Optional[date]
    presupuesto_anual_uf: Optional[Decimal]
    gasto_acumulado_uf: Decimal
    porcentaje_presupuesto_usado: Optional[Decimal]
    responsable_id: Optional[str]
    responsable_nombre: Optional[str]
    proveedor_preferido_id: Optional[str]
    proveedor_nombre: Optional[str]
    checklist_base: Optional[List[str]]
    notificar_anticipacion_dias: int
    activo: bool
    tareas_programadas: int
    tareas_completadas: int
    tareas_pendientes: int
    cumplimiento_porcentaje: Decimal
    creado_en: datetime
    actualizado_en: datetime
    version: int

class TareaMantencionResponse(BaseModel):
    """Response de tarea de mantención"""
    id: str
    codigo: str  # TM-YYYY-NNNNNN
    titulo: str
    descripcion: str
    plan_id: Optional[str]
    plan_nombre: Optional[str]
    propiedad_id: Optional[str]
    propiedad_direccion: Optional[str]
    condominio_id: Optional[str]
    condominio_nombre: Optional[str]
    unidad_id: Optional[str]
    unidad_codigo: Optional[str]
    tipo: TipoMantencion
    categoria: CategoriaMantencion
    prioridad: PrioridadTarea
    estado: EstadoTarea
    fecha_creacion: datetime
    fecha_programada: Optional[date]
    hora_inicio: Optional[str]
    hora_fin: Optional[str]
    fecha_asignacion: Optional[datetime]
    fecha_inicio_real: Optional[datetime]
    fecha_completado: Optional[datetime]
    duracion_estimada_horas: Optional[Decimal]
    duracion_real_horas: Optional[Decimal]
    proveedor_id: Optional[str]
    proveedor_nombre: Optional[str]
    presupuesto_uf: Optional[Decimal]
    costo_real_uf: Optional[Decimal]
    variacion_costo_porcentaje: Optional[Decimal]
    requiere_acceso_unidad: bool
    requiere_corte_servicios: bool
    servicios_afectados: Optional[List[str]]
    checklist: Optional[List[Dict[str, Any]]]  # [{item, completado}]
    resultado: Optional[str]
    observaciones: Optional[str]
    evidencia_fotografica: Optional[List[str]]
    materiales_utilizados: Optional[List[Dict[str, Any]]]
    requiere_seguimiento: bool
    fecha_seguimiento: Optional[date]
    calificacion_proveedor: Optional[int]
    solicitante_id: Optional[str]
    solicitante_nombre: Optional[str]
    asignado_por_id: Optional[str]
    cerrado_por_id: Optional[str]

class ProveedorResponse(BaseModel):
    """Response de proveedor"""
    id: str
    rut: str
    razon_social: str
    nombre_fantasia: Optional[str]
    tipo: TipoProveedor
    estado: EstadoProveedor
    giro: str
    categorias_servicio: List[CategoriaMantencion]
    email: str
    telefono: str
    telefono_emergencia: Optional[str]
    direccion: str
    comuna: str
    region: str
    representante_legal: Optional[str]
    contacto_operativo: Optional[str]
    email_operativo: Optional[str]
    sitio_web: Optional[str]
    tiempo_respuesta_horas: Optional[int]
    horario_atencion: Optional[str]
    atiende_emergencias: bool
    tarifa_hora_uf: Optional[Decimal]
    tarifa_visita_uf: Optional[Decimal]
    certificaciones: Optional[List[str]]
    seguros_vigentes: Optional[List[str]]
    # Métricas de desempeño
    tareas_completadas: int
    calificacion_promedio: Optional[Decimal]
    calificacion_calidad: Optional[Decimal]
    calificacion_puntualidad: Optional[Decimal]
    calificacion_precio: Optional[Decimal]
    evaluaciones_totales: int
    tasa_recomendacion: Optional[Decimal]
    tiempo_respuesta_promedio_horas: Optional[Decimal]
    costo_promedio_por_tarea_uf: Optional[Decimal]
    ultima_evaluacion: Optional[datetime]
    notas: Optional[str]
    creado_en: datetime
    actualizado_en: datetime

class BusquedaPlanesResponse(BaseModel):
    """Response de búsqueda de planes"""
    planes: List[PlanMantencionResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    filtros_aplicados: Dict[str, Any]

class BusquedaTareasResponse(BaseModel):
    """Response de búsqueda de tareas"""
    tareas: List[TareaMantencionResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    filtros_aplicados: Dict[str, Any]

class BusquedaProveedoresResponse(BaseModel):
    """Response de búsqueda de proveedores"""
    proveedores: List[ProveedorResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int

class CalendarioMantencionResponse(BaseModel):
    """Response de calendario de mantenciones"""
    mes: int
    ano: int
    tareas_por_dia: Dict[str, List[Dict[str, Any]]]  # {fecha_iso: [tareas]}
    total_tareas_mes: int
    tareas_pendientes: int
    tareas_completadas: int
    presupuesto_mes_uf: Decimal
    gasto_mes_uf: Decimal
    proximas_urgentes: List[TareaMantencionResponse]

class EstadisticasMantencionResponse(BaseModel):
    """Response de estadísticas de mantención"""
    periodo: str  # "2024-01" a "2024-12"
    # Conteos
    total_planes_activos: int
    total_tareas_periodo: int
    tareas_preventivas: int
    tareas_correctivas: int
    tareas_completadas: int
    tareas_pendientes: int
    tareas_vencidas: int
    # Tiempos
    tiempo_promedio_resolucion_horas: Decimal
    tiempo_promedio_respuesta_horas: Decimal
    cumplimiento_sla_porcentaje: Decimal
    # Costos
    presupuesto_total_uf: Decimal
    gasto_total_uf: Decimal
    variacion_presupuesto_porcentaje: Decimal
    costo_promedio_tarea_uf: Decimal
    ahorro_preventivo_estimado_uf: Optional[Decimal]
    # Por categoría
    distribucion_por_categoria: Dict[str, int]
    costos_por_categoria: Dict[str, Decimal]
    # Por prioridad
    distribucion_por_prioridad: Dict[str, int]
    # Proveedores
    proveedor_mas_usado: Optional[Dict[str, Any]]
    proveedor_mejor_calificado: Optional[Dict[str, Any]]
    # Tendencias
    tendencia_tareas_mensual: List[Dict[str, Any]]
    tendencia_costos_mensual: List[Dict[str, Any]]
    # KPIs
    indice_mantenimiento_preventivo: Decimal  # % preventivas vs total
    tasa_resolucion_primera_visita: Decimal
    satisfaccion_promedio: Optional[Decimal]

class ReporteMantencionResponse(BaseModel):
    """Response de reporte de mantención"""
    id: str
    tipo_reporte: str
    titulo: str
    periodo_desde: date
    periodo_hasta: date
    generado_en: datetime
    generado_por: str
    formato: str  # pdf, excel, html
    url_descarga: str
    secciones_incluidas: List[str]
    resumen_ejecutivo: Dict[str, Any]
    hallazgos_principales: List[str]
    recomendaciones: List[str]

class KPIsMantencionResponse(BaseModel):
    """KPIs clave de mantención"""
    fecha_calculo: datetime
    periodo: str
    # Indicadores principales
    mtbf_horas: Optional[Decimal]  # Mean Time Between Failures
    mttr_horas: Optional[Decimal]  # Mean Time To Repair
    disponibilidad_porcentaje: Decimal
    confiabilidad_porcentaje: Decimal
    oee_porcentaje: Optional[Decimal]  # Overall Equipment Effectiveness
    # Financieros
    costo_mantencion_por_m2_uf: Decimal
    roi_mantencion_preventiva: Optional[Decimal]
    backlog_mantencion_uf: Decimal
    # Operacionales
    cumplimiento_plan_porcentaje: Decimal
    tareas_vencidas_count: int
    emergencias_mes: int
    # Tendencia
    variacion_vs_mes_anterior: Dict[str, Decimal]

# =============================================================================
# MOCK SERVICE
# =============================================================================

class MockMantencionesService:
    """Servicio mock para desarrollo"""
    
    def __init__(self):
        self.planes: Dict[str, Dict] = {}
        self.tareas: Dict[str, Dict] = {}
        self.proveedores: Dict[str, Dict] = {}
        self._init_datos_ejemplo()
    
    def _init_datos_ejemplo(self):
        """Inicializa datos de ejemplo"""
        # Plan ejemplo
        plan_id = str(uuid.uuid4())
        self.planes[plan_id] = {
            "id": plan_id,
            "codigo": "PM-2024-000001",
            "nombre": "Mantención Preventiva Ascensores 2024",
            "descripcion": "Plan de mantención preventiva mensual para ascensores del edificio",
            "propiedad_id": None,
            "condominio_id": "cond-001",
            "tipo": TipoMantencion.preventiva,
            "categorias": [CategoriaMantencion.ascensores],
            "frecuencia": FrecuenciaMantencion.mensual,
            "fecha_inicio": date(2024, 1, 1),
            "fecha_termino": date(2024, 12, 31),
            "proxima_ejecucion": date(2024, 2, 15),
            "presupuesto_anual_uf": Decimal("120"),
            "gasto_acumulado_uf": Decimal("10"),
            "porcentaje_presupuesto_usado": Decimal("8.33"),
            "responsable_id": "user-001",
            "responsable_nombre": "Carlos Mendoza",
            "proveedor_preferido_id": "prov-001",
            "proveedor_nombre": "Ascensores Chile SpA",
            "checklist_base": [
                "Verificar sistema de frenos",
                "Revisar cables de tracción",
                "Lubricar guías",
                "Verificar sistema eléctrico",
                "Probar sistema de emergencia",
                "Verificar nivelación de pisos"
            ],
            "notificar_anticipacion_dias": 7,
            "activo": True,
            "tareas_programadas": 12,
            "tareas_completadas": 1,
            "tareas_pendientes": 11,
            "cumplimiento_porcentaje": Decimal("8.33"),
            "creado_en": datetime.now(),
            "actualizado_en": datetime.now(),
            "version": 1
        }
        
        # Tarea ejemplo
        tarea_id = str(uuid.uuid4())
        self.tareas[tarea_id] = {
            "id": tarea_id,
            "codigo": "TM-2024-000001",
            "titulo": "Mantención mensual ascensor Torre A",
            "descripcion": "Mantención preventiva mensual según plan PM-2024-000001",
            "plan_id": plan_id,
            "plan_nombre": "Mantención Preventiva Ascensores 2024",
            "propiedad_id": None,
            "propiedad_direccion": None,
            "condominio_id": "cond-001",
            "condominio_nombre": "Edificio Los Aromos",
            "unidad_id": None,
            "unidad_codigo": None,
            "tipo": TipoMantencion.preventiva,
            "categoria": CategoriaMantencion.ascensores,
            "prioridad": PrioridadTarea.programada,
            "estado": EstadoTarea.programada,
            "fecha_creacion": datetime.now(),
            "fecha_programada": date(2024, 2, 15),
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
            "fecha_asignacion": datetime.now(),
            "fecha_inicio_real": None,
            "fecha_completado": None,
            "duracion_estimada_horas": Decimal("3"),
            "duracion_real_horas": None,
            "proveedor_id": "prov-001",
            "proveedor_nombre": "Ascensores Chile SpA",
            "presupuesto_uf": Decimal("10"),
            "costo_real_uf": None,
            "variacion_costo_porcentaje": None,
            "requiere_acceso_unidad": False,
            "requiere_corte_servicios": True,
            "servicios_afectados": ["Ascensor Torre A"],
            "checklist": [
                {"item": "Verificar sistema de frenos", "completado": False},
                {"item": "Revisar cables de tracción", "completado": False},
                {"item": "Lubricar guías", "completado": False},
                {"item": "Verificar sistema eléctrico", "completado": False},
                {"item": "Probar sistema de emergencia", "completado": False},
                {"item": "Verificar nivelación de pisos", "completado": False}
            ],
            "resultado": None,
            "observaciones": None,
            "evidencia_fotografica": None,
            "materiales_utilizados": None,
            "requiere_seguimiento": False,
            "fecha_seguimiento": None,
            "calificacion_proveedor": None,
            "solicitante_id": None,
            "solicitante_nombre": None,
            "asignado_por_id": "user-001",
            "cerrado_por_id": None
        }
        
        # Proveedor ejemplo
        prov_id = "prov-001"
        self.proveedores[prov_id] = {
            "id": prov_id,
            "rut": "76.543.210-K",
            "razon_social": "Ascensores Chile SpA",
            "nombre_fantasia": "AscenChile",
            "tipo": TipoProveedor.empresa,
            "estado": EstadoProveedor.activo,
            "giro": "Mantención y reparación de ascensores",
            "categorias_servicio": [CategoriaMantencion.ascensores],
            "email": "contacto@ascenchile.cl",
            "telefono": "+56 2 2345 6789",
            "telefono_emergencia": "+56 9 8765 4321",
            "direccion": "Av. Industrial 1234",
            "comuna": "San Joaquín",
            "region": "Metropolitana",
            "representante_legal": "Roberto Fuentes",
            "contacto_operativo": "María González",
            "email_operativo": "operaciones@ascenchile.cl",
            "sitio_web": "www.ascenchile.cl",
            "tiempo_respuesta_horas": 4,
            "horario_atencion": "Lunes a Viernes 08:00-18:00",
            "atiende_emergencias": True,
            "tarifa_hora_uf": Decimal("1.5"),
            "tarifa_visita_uf": Decimal("3.0"),
            "certificaciones": ["ISO 9001:2015", "Certificación SEC"],
            "seguros_vigentes": ["Responsabilidad Civil", "Accidentes Laborales"],
            "tareas_completadas": 45,
            "calificacion_promedio": Decimal("4.5"),
            "calificacion_calidad": Decimal("4.6"),
            "calificacion_puntualidad": Decimal("4.4"),
            "calificacion_precio": Decimal("4.3"),
            "evaluaciones_totales": 42,
            "tasa_recomendacion": Decimal("95.2"),
            "tiempo_respuesta_promedio_horas": Decimal("3.2"),
            "costo_promedio_por_tarea_uf": Decimal("8.5"),
            "ultima_evaluacion": datetime.now(),
            "notas": "Proveedor confiable, preferido para ascensores",
            "creado_en": datetime.now(),
            "actualizado_en": datetime.now()
        }

# Instancia global del servicio mock
mock_service = MockMantencionesService()

# =============================================================================
# ENDPOINTS - GESTIÓN DE PLANES (6)
# =============================================================================

@router.post(
    "/planes",
    response_model=PlanMantencionResponse,
    status_code=201,
    summary="Crear plan de mantención",
    description="Crea un nuevo plan de mantención preventiva o programada"
)
async def crear_plan(
    request: CrearPlanMantencionRequest,
    background_tasks: BackgroundTasks
):
    """
    Crea un plan de mantención con:
    - Configuración de frecuencia y categorías
    - Presupuesto anual
    - Checklist base
    - Generación automática de tareas programadas
    """
    plan_id = str(uuid.uuid4())
    codigo = f"PM-{datetime.now().year}-{len(mock_service.planes) + 1:06d}"
    
    plan = {
        "id": plan_id,
        "codigo": codigo,
        "nombre": request.nombre,
        "descripcion": request.descripcion,
        "propiedad_id": request.propiedad_id,
        "condominio_id": request.condominio_id,
        "tipo": request.tipo,
        "categorias": request.categorias,
        "frecuencia": request.frecuencia,
        "fecha_inicio": request.fecha_inicio,
        "fecha_termino": request.fecha_termino,
        "proxima_ejecucion": request.fecha_inicio,
        "presupuesto_anual_uf": request.presupuesto_anual_uf,
        "gasto_acumulado_uf": Decimal("0"),
        "porcentaje_presupuesto_usado": Decimal("0"),
        "responsable_id": request.responsable_id,
        "responsable_nombre": None,
        "proveedor_preferido_id": request.proveedor_preferido_id,
        "proveedor_nombre": None,
        "checklist_base": request.checklist_base or [],
        "notificar_anticipacion_dias": request.notificar_anticipacion_dias,
        "activo": request.activo,
        "tareas_programadas": 0,
        "tareas_completadas": 0,
        "tareas_pendientes": 0,
        "cumplimiento_porcentaje": Decimal("0"),
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now(),
        "version": 1
    }
    
    mock_service.planes[plan_id] = plan
    
    # Background: generar tareas programadas según frecuencia
    background_tasks.add_task(lambda: None)  # Placeholder
    
    return PlanMantencionResponse(**plan)

@router.get(
    "/planes/{plan_id}",
    response_model=PlanMantencionResponse,
    summary="Obtener plan de mantención",
    description="Obtiene un plan por su ID o código"
)
async def obtener_plan(
    plan_id: str = Path(..., description="ID o código del plan")
):
    """Retorna detalle completo del plan incluyendo métricas de cumplimiento"""
    # Buscar por ID o código
    plan = mock_service.planes.get(plan_id)
    if not plan:
        for p in mock_service.planes.values():
            if p["codigo"] == plan_id:
                plan = p
                break
    
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} no encontrado")
    
    return PlanMantencionResponse(**plan)

@router.get(
    "/planes",
    response_model=BusquedaPlanesResponse,
    summary="Buscar planes de mantención",
    description="Búsqueda con filtros múltiples"
)
async def buscar_planes(
    texto: Optional[str] = Query(None, description="Búsqueda en nombre/descripción"),
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    tipo: Optional[TipoMantencion] = Query(None, description="Tipo de mantención"),
    categoria: Optional[CategoriaMantencion] = Query(None, description="Categoría"),
    frecuencia: Optional[FrecuenciaMantencion] = Query(None, description="Frecuencia"),
    activo: Optional[bool] = Query(None, description="Solo activos/inactivos"),
    con_presupuesto_excedido: Optional[bool] = Query(None, description="Presupuesto excedido"),
    pagina: int = Query(1, ge=1, description="Página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    ordenar_por: str = Query("creado_en", description="Campo de ordenamiento"),
    orden: OrdenEnum = Query(OrdenEnum.desc, description="Dirección")
):
    """Búsqueda de planes con filtros y paginación"""
    planes = list(mock_service.planes.values())
    
    # Aplicar filtros
    if texto:
        texto_lower = texto.lower()
        planes = [p for p in planes if texto_lower in p["nombre"].lower() or 
                  (p["descripcion"] and texto_lower in p["descripcion"].lower())]
    if propiedad_id:
        planes = [p for p in planes if p["propiedad_id"] == propiedad_id]
    if condominio_id:
        planes = [p for p in planes if p["condominio_id"] == condominio_id]
    if tipo:
        planes = [p for p in planes if p["tipo"] == tipo]
    if categoria:
        planes = [p for p in planes if categoria in p["categorias"]]
    if frecuencia:
        planes = [p for p in planes if p["frecuencia"] == frecuencia]
    if activo is not None:
        planes = [p for p in planes if p["activo"] == activo]
    if con_presupuesto_excedido:
        planes = [p for p in planes if p["porcentaje_presupuesto_usado"] and 
                  p["porcentaje_presupuesto_usado"] > 100]
    
    total = len(planes)
    total_paginas = (total + por_pagina - 1) // por_pagina
    
    # Paginación
    inicio = (pagina - 1) * por_pagina
    planes_pagina = planes[inicio:inicio + por_pagina]
    
    return BusquedaPlanesResponse(
        planes=[PlanMantencionResponse(**p) for p in planes_pagina],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        filtros_aplicados={
            "texto": texto,
            "tipo": tipo.value if tipo else None,
            "categoria": categoria.value if categoria else None,
            "activo": activo
        }
    )

@router.put(
    "/planes/{plan_id}",
    response_model=PlanMantencionResponse,
    summary="Actualizar plan de mantención",
    description="Actualiza configuración del plan"
)
async def actualizar_plan(
    plan_id: str = Path(..., description="ID del plan"),
    request: ActualizarPlanRequest = Body(...)
):
    """Actualiza plan y regenera tareas si cambia frecuencia"""
    plan = mock_service.planes.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} no encontrado")
    
    # Aplicar actualizaciones
    actualizaciones = request.dict(exclude_unset=True)
    for campo, valor in actualizaciones.items():
        plan[campo] = valor
    
    plan["actualizado_en"] = datetime.now()
    plan["version"] += 1
    
    return PlanMantencionResponse(**plan)

@router.delete(
    "/planes/{plan_id}",
    status_code=204,
    summary="Eliminar plan de mantención",
    description="Desactiva un plan (soft delete)"
)
async def eliminar_plan(
    plan_id: str = Path(..., description="ID del plan"),
    cancelar_tareas_pendientes: bool = Query(True, description="Cancelar tareas pendientes")
):
    """Desactiva plan y opcionalmente cancela tareas pendientes"""
    plan = mock_service.planes.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} no encontrado")
    
    plan["activo"] = False
    plan["actualizado_en"] = datetime.now()
    
    # Cancelar tareas pendientes si se indica
    if cancelar_tareas_pendientes:
        for tarea in mock_service.tareas.values():
            if tarea["plan_id"] == plan_id and tarea["estado"] in [EstadoTarea.pendiente, EstadoTarea.programada]:
                tarea["estado"] = EstadoTarea.cancelada
    
    return None

@router.post(
    "/planes/{plan_id}/generar-tareas",
    response_model=List[TareaMantencionResponse],
    summary="Generar tareas del plan",
    description="Genera tareas programadas según frecuencia del plan"
)
async def generar_tareas_plan(
    plan_id: str = Path(..., description="ID del plan"),
    fecha_desde: date = Query(..., description="Fecha inicio generación"),
    fecha_hasta: date = Query(..., description="Fecha fin generación"),
    sobrescribir: bool = Query(False, description="Sobrescribir tareas existentes")
):
    """
    Genera tareas para el período indicado:
    - Calcula fechas según frecuencia
    - Asigna checklist base
    - Notifica responsables
    """
    plan = mock_service.planes.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} no encontrado")
    
    # Simulación: crear una tarea de ejemplo
    tarea_id = str(uuid.uuid4())
    codigo = f"TM-{datetime.now().year}-{len(mock_service.tareas) + 1:06d}"
    
    tarea = {
        "id": tarea_id,
        "codigo": codigo,
        "titulo": f"Tarea generada de {plan['nombre']}",
        "descripcion": plan["descripcion"] or "Tarea generada automáticamente",
        "plan_id": plan_id,
        "plan_nombre": plan["nombre"],
        "propiedad_id": plan["propiedad_id"],
        "propiedad_direccion": None,
        "condominio_id": plan["condominio_id"],
        "condominio_nombre": None,
        "unidad_id": None,
        "unidad_codigo": None,
        "tipo": plan["tipo"],
        "categoria": plan["categorias"][0] if plan["categorias"] else CategoriaMantencion.otro,
        "prioridad": PrioridadTarea.programada,
        "estado": EstadoTarea.programada,
        "fecha_creacion": datetime.now(),
        "fecha_programada": fecha_desde,
        "hora_inicio": None,
        "hora_fin": None,
        "fecha_asignacion": None,
        "fecha_inicio_real": None,
        "fecha_completado": None,
        "duracion_estimada_horas": Decimal("2"),
        "duracion_real_horas": None,
        "proveedor_id": plan["proveedor_preferido_id"],
        "proveedor_nombre": plan["proveedor_nombre"],
        "presupuesto_uf": None,
        "costo_real_uf": None,
        "variacion_costo_porcentaje": None,
        "requiere_acceso_unidad": False,
        "requiere_corte_servicios": False,
        "servicios_afectados": None,
        "checklist": [{"item": item, "completado": False} for item in (plan["checklist_base"] or [])],
        "resultado": None,
        "observaciones": None,
        "evidencia_fotografica": None,
        "materiales_utilizados": None,
        "requiere_seguimiento": False,
        "fecha_seguimiento": None,
        "calificacion_proveedor": None,
        "solicitante_id": None,
        "solicitante_nombre": None,
        "asignado_por_id": None,
        "cerrado_por_id": None
    }
    
    mock_service.tareas[tarea_id] = tarea
    plan["tareas_programadas"] += 1
    plan["tareas_pendientes"] += 1
    
    return [TareaMantencionResponse(**tarea)]

# =============================================================================
# ENDPOINTS - GESTIÓN DE TAREAS (6)
# =============================================================================

@router.post(
    "/tareas",
    response_model=TareaMantencionResponse,
    status_code=201,
    summary="Crear tarea de mantención",
    description="Crea una nueva tarea (correctiva, preventiva, etc.)"
)
async def crear_tarea(
    request: CrearTareaRequest,
    background_tasks: BackgroundTasks
):
    """
    Crea tarea de mantención:
    - Asigna prioridad y categoría
    - Opcionalmente vincula a plan
    - Notifica según configuración
    """
    tarea_id = str(uuid.uuid4())
    codigo = f"TM-{datetime.now().year}-{len(mock_service.tareas) + 1:06d}"
    
    tarea = {
        "id": tarea_id,
        "codigo": codigo,
        "titulo": request.titulo,
        "descripcion": request.descripcion,
        "plan_id": request.plan_id,
        "plan_nombre": None,
        "propiedad_id": request.propiedad_id,
        "propiedad_direccion": None,
        "condominio_id": request.condominio_id,
        "condominio_nombre": None,
        "unidad_id": request.unidad_id,
        "unidad_codigo": None,
        "tipo": request.tipo,
        "categoria": request.categoria,
        "prioridad": request.prioridad,
        "estado": EstadoTarea.pendiente,
        "fecha_creacion": datetime.now(),
        "fecha_programada": request.fecha_programada,
        "hora_inicio": request.hora_inicio,
        "hora_fin": request.hora_fin,
        "fecha_asignacion": None,
        "fecha_inicio_real": None,
        "fecha_completado": None,
        "duracion_estimada_horas": request.duracion_estimada_horas,
        "duracion_real_horas": None,
        "proveedor_id": request.proveedor_id,
        "proveedor_nombre": None,
        "presupuesto_uf": request.presupuesto_uf,
        "costo_real_uf": None,
        "variacion_costo_porcentaje": None,
        "requiere_acceso_unidad": request.requiere_acceso_unidad,
        "requiere_corte_servicios": request.requiere_corte_servicios,
        "servicios_afectados": request.servicios_afectados,
        "checklist": [{"item": item, "completado": False} for item in (request.checklist or [])],
        "resultado": None,
        "observaciones": None,
        "evidencia_fotografica": None,
        "materiales_utilizados": None,
        "requiere_seguimiento": False,
        "fecha_seguimiento": None,
        "calificacion_proveedor": None,
        "solicitante_id": request.solicitante_id,
        "solicitante_nombre": None,
        "asignado_por_id": None,
        "cerrado_por_id": None
    }
    
    mock_service.tareas[tarea_id] = tarea
    
    return TareaMantencionResponse(**tarea)

@router.get(
    "/tareas/{tarea_id}",
    response_model=TareaMantencionResponse,
    summary="Obtener tarea de mantención",
    description="Obtiene una tarea por su ID o código"
)
async def obtener_tarea(
    tarea_id: str = Path(..., description="ID o código de la tarea")
):
    """Retorna detalle completo de la tarea"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        for t in mock_service.tareas.values():
            if t["codigo"] == tarea_id:
                tarea = t
                break
    
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    return TareaMantencionResponse(**tarea)

@router.get(
    "/tareas",
    response_model=BusquedaTareasResponse,
    summary="Buscar tareas de mantención",
    description="Búsqueda con múltiples filtros"
)
async def buscar_tareas(
    texto: Optional[str] = Query(None, description="Búsqueda en título/descripción"),
    plan_id: Optional[str] = Query(None, description="Filtrar por plan"),
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    unidad_id: Optional[str] = Query(None, description="Filtrar por unidad"),
    tipo: Optional[TipoMantencion] = Query(None, description="Tipo"),
    categoria: Optional[CategoriaMantencion] = Query(None, description="Categoría"),
    prioridad: Optional[PrioridadTarea] = Query(None, description="Prioridad"),
    estado: Optional[EstadoTarea] = Query(None, description="Estado"),
    proveedor_id: Optional[str] = Query(None, description="Proveedor asignado"),
    fecha_desde: Optional[date] = Query(None, description="Programadas desde"),
    fecha_hasta: Optional[date] = Query(None, description="Programadas hasta"),
    solo_vencidas: bool = Query(False, description="Solo vencidas"),
    pagina: int = Query(1, ge=1, description="Página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Por página"),
    ordenar_por: str = Query("fecha_programada", description="Ordenar por"),
    orden: OrdenEnum = Query(OrdenEnum.asc, description="Dirección")
):
    """Búsqueda de tareas con filtros y paginación"""
    tareas = list(mock_service.tareas.values())
    
    # Aplicar filtros
    if texto:
        texto_lower = texto.lower()
        tareas = [t for t in tareas if texto_lower in t["titulo"].lower() or 
                  texto_lower in t["descripcion"].lower()]
    if plan_id:
        tareas = [t for t in tareas if t["plan_id"] == plan_id]
    if propiedad_id:
        tareas = [t for t in tareas if t["propiedad_id"] == propiedad_id]
    if condominio_id:
        tareas = [t for t in tareas if t["condominio_id"] == condominio_id]
    if unidad_id:
        tareas = [t for t in tareas if t["unidad_id"] == unidad_id]
    if tipo:
        tareas = [t for t in tareas if t["tipo"] == tipo]
    if categoria:
        tareas = [t for t in tareas if t["categoria"] == categoria]
    if prioridad:
        tareas = [t for t in tareas if t["prioridad"] == prioridad]
    if estado:
        tareas = [t for t in tareas if t["estado"] == estado]
    if proveedor_id:
        tareas = [t for t in tareas if t["proveedor_id"] == proveedor_id]
    if fecha_desde:
        tareas = [t for t in tareas if t["fecha_programada"] and t["fecha_programada"] >= fecha_desde]
    if fecha_hasta:
        tareas = [t for t in tareas if t["fecha_programada"] and t["fecha_programada"] <= fecha_hasta]
    if solo_vencidas:
        hoy = date.today()
        tareas = [t for t in tareas if t["fecha_programada"] and t["fecha_programada"] < hoy and 
                  t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada]]
    
    total = len(tareas)
    total_paginas = (total + por_pagina - 1) // por_pagina
    
    # Paginación
    inicio = (pagina - 1) * por_pagina
    tareas_pagina = tareas[inicio:inicio + por_pagina]
    
    return BusquedaTareasResponse(
        tareas=[TareaMantencionResponse(**t) for t in tareas_pagina],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        filtros_aplicados={
            "texto": texto,
            "tipo": tipo.value if tipo else None,
            "categoria": categoria.value if categoria else None,
            "estado": estado.value if estado else None,
            "prioridad": prioridad.value if prioridad else None
        }
    )

@router.put(
    "/tareas/{tarea_id}",
    response_model=TareaMantencionResponse,
    summary="Actualizar tarea de mantención",
    description="Actualiza datos de la tarea"
)
async def actualizar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    request: ActualizarTareaRequest = Body(...)
):
    """Actualiza tarea (solo campos permitidos según estado)"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    # Validar que no esté completada/cancelada
    if tarea["estado"] in [EstadoTarea.completada, EstadoTarea.cancelada]:
        raise HTTPException(status_code=400, detail="No se puede modificar tarea completada/cancelada")
    
    # Aplicar actualizaciones
    actualizaciones = request.dict(exclude_unset=True)
    for campo, valor in actualizaciones.items():
        tarea[campo] = valor
    
    return TareaMantencionResponse(**tarea)

@router.delete(
    "/tareas/{tarea_id}",
    status_code=204,
    summary="Cancelar tarea de mantención",
    description="Cancela una tarea pendiente"
)
async def cancelar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    motivo: str = Query(..., min_length=10, description="Motivo de cancelación")
):
    """Cancela tarea y registra motivo"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    if tarea["estado"] == EstadoTarea.completada:
        raise HTTPException(status_code=400, detail="No se puede cancelar tarea completada")
    
    tarea["estado"] = EstadoTarea.cancelada
    tarea["observaciones"] = f"CANCELADA: {motivo}"
    
    return None

@router.get(
    "/tareas/{tarea_id}/historial",
    response_model=List[Dict[str, Any]],
    summary="Historial de cambios de tarea",
    description="Obtiene el historial de cambios de una tarea"
)
async def historial_tarea(
    tarea_id: str = Path(..., description="ID de la tarea")
):
    """Retorna historial de cambios de estado y modificaciones"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    # Simulación de historial
    return [
        {
            "fecha": tarea["fecha_creacion"].isoformat(),
            "accion": "creacion",
            "usuario": "Sistema",
            "detalle": "Tarea creada"
        }
    ]

# =============================================================================
# ENDPOINTS - EJECUCIÓN Y SEGUIMIENTO (6)
# =============================================================================

@router.post(
    "/tareas/{tarea_id}/asignar",
    response_model=TareaMantencionResponse,
    summary="Asignar tarea a proveedor",
    description="Asigna tarea a un proveedor con fecha programada"
)
async def asignar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    request: AsignarTareaRequest = Body(...),
    background_tasks: BackgroundTasks = None
):
    """
    Asigna tarea:
    - Verifica disponibilidad proveedor
    - Notifica según configuración
    - Actualiza estado a 'asignada'
    """
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    # Verificar proveedor
    proveedor = mock_service.proveedores.get(request.proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail=f"Proveedor {request.proveedor_id} no encontrado")
    
    if proveedor["estado"] != EstadoProveedor.activo:
        raise HTTPException(status_code=400, detail="Proveedor no está activo")
    
    # Actualizar tarea
    tarea["proveedor_id"] = request.proveedor_id
    tarea["proveedor_nombre"] = proveedor["razon_social"]
    tarea["fecha_programada"] = request.fecha_programada
    tarea["hora_inicio"] = request.hora_inicio
    tarea["hora_fin"] = request.hora_fin
    tarea["presupuesto_uf"] = request.presupuesto_acordado_uf or tarea["presupuesto_uf"]
    tarea["estado"] = EstadoTarea.asignada
    tarea["fecha_asignacion"] = datetime.now()
    
    if request.instrucciones_especiales:
        tarea["observaciones"] = request.instrucciones_especiales
    
    return TareaMantencionResponse(**tarea)

@router.post(
    "/tareas/{tarea_id}/iniciar",
    response_model=TareaMantencionResponse,
    summary="Iniciar ejecución de tarea",
    description="Marca tarea como en ejecución"
)
async def iniciar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    notas_inicio: Optional[str] = Query(None, max_length=500, description="Notas de inicio")
):
    """Marca inicio de ejecución de la tarea"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    if tarea["estado"] not in [EstadoTarea.asignada, EstadoTarea.programada]:
        raise HTTPException(status_code=400, detail=f"Tarea en estado {tarea['estado']} no puede iniciarse")
    
    tarea["estado"] = EstadoTarea.en_proceso
    tarea["fecha_inicio_real"] = datetime.now()
    
    if notas_inicio:
        tarea["observaciones"] = (tarea["observaciones"] or "") + f"\nINICIO: {notas_inicio}"
    
    return TareaMantencionResponse(**tarea)

@router.post(
    "/tareas/{tarea_id}/completar",
    response_model=TareaMantencionResponse,
    summary="Completar tarea",
    description="Marca tarea como completada con resultado"
)
async def completar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    request: CerrarTareaRequest = Body(...),
    background_tasks: BackgroundTasks = None
):
    """
    Completa tarea:
    - Registra resultado y costos
    - Actualiza checklist
    - Evalúa proveedor si se indica
    - Programa seguimiento si necesario
    """
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    if tarea["estado"] not in [EstadoTarea.en_proceso, EstadoTarea.asignada]:
        raise HTTPException(status_code=400, detail=f"Tarea en estado {tarea['estado']} no puede completarse")
    
    # Actualizar tarea
    tarea["resultado"] = request.resultado
    tarea["costo_real_uf"] = request.costo_real_uf
    tarea["duracion_real_horas"] = request.duracion_real_horas
    tarea["observaciones"] = request.observaciones
    tarea["evidencia_fotografica"] = request.evidencia_fotografica
    tarea["materiales_utilizados"] = request.materiales_utilizados
    tarea["fecha_completado"] = request.fecha_completado or datetime.now()
    tarea["estado"] = EstadoTarea.completada
    tarea["requiere_seguimiento"] = request.requiere_seguimiento
    tarea["fecha_seguimiento"] = request.fecha_seguimiento
    tarea["calificacion_proveedor"] = request.calificacion_proveedor
    
    # Calcular variación de costo
    if tarea["presupuesto_uf"] and tarea["presupuesto_uf"] > 0:
        variacion = ((request.costo_real_uf - tarea["presupuesto_uf"]) / tarea["presupuesto_uf"]) * 100
        tarea["variacion_costo_porcentaje"] = round(variacion, 2)
    
    # Actualizar checklist
    if request.checklist_completado and tarea["checklist"]:
        for item in tarea["checklist"]:
            if item["item"] in request.checklist_completado:
                item["completado"] = request.checklist_completado[item["item"]]
    
    # Actualizar plan si existe
    if tarea["plan_id"] and tarea["plan_id"] in mock_service.planes:
        plan = mock_service.planes[tarea["plan_id"]]
        plan["tareas_completadas"] += 1
        plan["tareas_pendientes"] = max(0, plan["tareas_pendientes"] - 1)
        plan["gasto_acumulado_uf"] += request.costo_real_uf
        if plan["presupuesto_anual_uf"]:
            plan["porcentaje_presupuesto_usado"] = (plan["gasto_acumulado_uf"] / plan["presupuesto_anual_uf"]) * 100
        plan["cumplimiento_porcentaje"] = (plan["tareas_completadas"] / plan["tareas_programadas"]) * 100 if plan["tareas_programadas"] > 0 else 0
    
    return TareaMantencionResponse(**tarea)

@router.post(
    "/tareas/{tarea_id}/rechazar",
    response_model=TareaMantencionResponse,
    summary="Rechazar trabajo de tarea",
    description="Rechaza el trabajo realizado (requiere corrección)"
)
async def rechazar_tarea(
    tarea_id: str = Path(..., description="ID de la tarea"),
    motivo: str = Query(..., min_length=20, description="Motivo del rechazo"),
    nueva_fecha: Optional[date] = Query(None, description="Nueva fecha programada")
):
    """Rechaza trabajo y devuelve a estado asignada"""
    tarea = mock_service.tareas.get(tarea_id)
    if not tarea:
        raise HTTPException(status_code=404, detail=f"Tarea {tarea_id} no encontrada")
    
    tarea["estado"] = EstadoTarea.rechazada
    tarea["observaciones"] = (tarea["observaciones"] or "") + f"\nRECHAZADA: {motivo}"
    
    if nueva_fecha:
        tarea["fecha_programada"] = nueva_fecha
    
    return TareaMantencionResponse(**tarea)

@router.get(
    "/calendario",
    response_model=CalendarioMantencionResponse,
    summary="Calendario de mantenciones",
    description="Vista de calendario mensual de tareas"
)
async def calendario_mantenciones(
    mes: int = Query(..., ge=1, le=12, description="Mes"),
    ano: int = Query(..., ge=2020, le=2030, description="Año"),
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio")
):
    """Retorna calendario mensual con tareas por día"""
    tareas = list(mock_service.tareas.values())
    
    # Filtrar por mes/año y propiedad/condominio
    tareas_mes = [t for t in tareas if t["fecha_programada"] and 
                  t["fecha_programada"].month == mes and 
                  t["fecha_programada"].year == ano]
    
    if propiedad_id:
        tareas_mes = [t for t in tareas_mes if t["propiedad_id"] == propiedad_id]
    if condominio_id:
        tareas_mes = [t for t in tareas_mes if t["condominio_id"] == condominio_id]
    
    # Agrupar por día
    tareas_por_dia = {}
    for t in tareas_mes:
        fecha_str = t["fecha_programada"].isoformat()
        if fecha_str not in tareas_por_dia:
            tareas_por_dia[fecha_str] = []
        tareas_por_dia[fecha_str].append({
            "id": t["id"],
            "codigo": t["codigo"],
            "titulo": t["titulo"],
            "categoria": t["categoria"],
            "prioridad": t["prioridad"],
            "estado": t["estado"],
            "hora_inicio": t["hora_inicio"]
        })
    
    # Calcular métricas
    pendientes = sum(1 for t in tareas_mes if t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada])
    completadas = sum(1 for t in tareas_mes if t["estado"] == EstadoTarea.completada)
    presupuesto = sum(t["presupuesto_uf"] or 0 for t in tareas_mes)
    gasto = sum(t["costo_real_uf"] or 0 for t in tareas_mes if t["costo_real_uf"])
    
    # Urgentes próximas
    hoy = date.today()
    urgentes = [t for t in tareas_mes if t["fecha_programada"] and 
                t["fecha_programada"] >= hoy and 
                t["prioridad"] in [PrioridadTarea.critica, PrioridadTarea.alta] and
                t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada]]
    
    return CalendarioMantencionResponse(
        mes=mes,
        ano=ano,
        tareas_por_dia=tareas_por_dia,
        total_tareas_mes=len(tareas_mes),
        tareas_pendientes=pendientes,
        tareas_completadas=completadas,
        presupuesto_mes_uf=presupuesto,
        gasto_mes_uf=gasto,
        proximas_urgentes=[TareaMantencionResponse(**t) for t in urgentes[:5]]
    )

@router.get(
    "/tareas/vencidas",
    response_model=List[TareaMantencionResponse],
    summary="Tareas vencidas",
    description="Lista tareas con fecha programada pasada sin completar"
)
async def tareas_vencidas(
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    dias_vencimiento: Optional[int] = Query(None, ge=1, description="Mínimo días vencidas")
):
    """Lista tareas vencidas ordenadas por antigüedad"""
    hoy = date.today()
    tareas = list(mock_service.tareas.values())
    
    vencidas = [t for t in tareas if t["fecha_programada"] and 
                t["fecha_programada"] < hoy and
                t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada]]
    
    if propiedad_id:
        vencidas = [t for t in vencidas if t["propiedad_id"] == propiedad_id]
    if condominio_id:
        vencidas = [t for t in vencidas if t["condominio_id"] == condominio_id]
    if dias_vencimiento:
        fecha_limite = hoy - timedelta(days=dias_vencimiento)
        vencidas = [t for t in vencidas if t["fecha_programada"] <= fecha_limite]
    
    # Ordenar por antigüedad (más vencidas primero)
    vencidas.sort(key=lambda t: t["fecha_programada"])
    
    return [TareaMantencionResponse(**t) for t in vencidas]

# =============================================================================
# ENDPOINTS - PROVEEDORES (4)
# =============================================================================

@router.post(
    "/proveedores",
    response_model=ProveedorResponse,
    status_code=201,
    summary="Registrar proveedor",
    description="Registra un nuevo proveedor de servicios"
)
async def crear_proveedor(
    request: CrearProveedorRequest
):
    """
    Registra proveedor:
    - Valida RUT único
    - Verifica certificaciones
    - Inicia período de evaluación
    """
    # Verificar RUT único
    for prov in mock_service.proveedores.values():
        if prov["rut"] == request.rut:
            raise HTTPException(status_code=400, detail=f"Ya existe proveedor con RUT {request.rut}")
    
    prov_id = str(uuid.uuid4())
    
    proveedor = {
        "id": prov_id,
        "rut": request.rut,
        "razon_social": request.razon_social,
        "nombre_fantasia": request.nombre_fantasia,
        "tipo": request.tipo,
        "estado": EstadoProveedor.evaluacion,  # Inicia en evaluación
        "giro": request.giro,
        "categorias_servicio": request.categorias_servicio,
        "email": request.email,
        "telefono": request.telefono,
        "telefono_emergencia": request.telefono_emergencia,
        "direccion": request.direccion,
        "comuna": request.comuna,
        "region": request.region,
        "representante_legal": request.representante_legal,
        "contacto_operativo": request.contacto_operativo,
        "email_operativo": request.email_operativo,
        "sitio_web": request.sitio_web,
        "tiempo_respuesta_horas": request.tiempo_respuesta_horas,
        "horario_atencion": request.horario_atencion,
        "atiende_emergencias": request.atiende_emergencias,
        "tarifa_hora_uf": request.tarifa_hora_uf,
        "tarifa_visita_uf": request.tarifa_visita_uf,
        "certificaciones": request.certificaciones,
        "seguros_vigentes": request.seguros_vigentes,
        "tareas_completadas": 0,
        "calificacion_promedio": None,
        "calificacion_calidad": None,
        "calificacion_puntualidad": None,
        "calificacion_precio": None,
        "evaluaciones_totales": 0,
        "tasa_recomendacion": None,
        "tiempo_respuesta_promedio_horas": None,
        "costo_promedio_por_tarea_uf": None,
        "ultima_evaluacion": None,
        "notas": request.notas,
        "creado_en": datetime.now(),
        "actualizado_en": datetime.now()
    }
    
    mock_service.proveedores[prov_id] = proveedor
    
    return ProveedorResponse(**proveedor)

@router.get(
    "/proveedores/{proveedor_id}",
    response_model=ProveedorResponse,
    summary="Obtener proveedor",
    description="Obtiene detalle de un proveedor"
)
async def obtener_proveedor(
    proveedor_id: str = Path(..., description="ID del proveedor")
):
    """Retorna proveedor con métricas de desempeño"""
    proveedor = mock_service.proveedores.get(proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail=f"Proveedor {proveedor_id} no encontrado")
    
    return ProveedorResponse(**proveedor)

@router.get(
    "/proveedores",
    response_model=BusquedaProveedoresResponse,
    summary="Buscar proveedores",
    description="Búsqueda de proveedores con filtros"
)
async def buscar_proveedores(
    texto: Optional[str] = Query(None, description="Búsqueda en nombre/giro"),
    categoria: Optional[CategoriaMantencion] = Query(None, description="Categoría de servicio"),
    tipo: Optional[TipoProveedor] = Query(None, description="Tipo de proveedor"),
    estado: Optional[EstadoProveedor] = Query(None, description="Estado"),
    comuna: Optional[str] = Query(None, description="Comuna"),
    atiende_emergencias: Optional[bool] = Query(None, description="Disponible emergencias"),
    calificacion_minima: Optional[Decimal] = Query(None, ge=1, le=5, description="Calificación mínima"),
    ordenar_por: str = Query("calificacion_promedio", description="Ordenar por"),
    orden: OrdenEnum = Query(OrdenEnum.desc, description="Dirección"),
    pagina: int = Query(1, ge=1, description="Página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Por página")
):
    """Búsqueda de proveedores con filtros y paginación"""
    proveedores = list(mock_service.proveedores.values())
    
    # Aplicar filtros
    if texto:
        texto_lower = texto.lower()
        proveedores = [p for p in proveedores if texto_lower in p["razon_social"].lower() or 
                       (p["nombre_fantasia"] and texto_lower in p["nombre_fantasia"].lower()) or
                       texto_lower in p["giro"].lower()]
    if categoria:
        proveedores = [p for p in proveedores if categoria in p["categorias_servicio"]]
    if tipo:
        proveedores = [p for p in proveedores if p["tipo"] == tipo]
    if estado:
        proveedores = [p for p in proveedores if p["estado"] == estado]
    if comuna:
        proveedores = [p for p in proveedores if p["comuna"].lower() == comuna.lower()]
    if atiende_emergencias is not None:
        proveedores = [p for p in proveedores if p["atiende_emergencias"] == atiende_emergencias]
    if calificacion_minima:
        proveedores = [p for p in proveedores if p["calificacion_promedio"] and 
                       p["calificacion_promedio"] >= calificacion_minima]
    
    total = len(proveedores)
    total_paginas = (total + por_pagina - 1) // por_pagina
    
    # Paginación
    inicio = (pagina - 1) * por_pagina
    proveedores_pagina = proveedores[inicio:inicio + por_pagina]
    
    return BusquedaProveedoresResponse(
        proveedores=[ProveedorResponse(**p) for p in proveedores_pagina],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas
    )

@router.post(
    "/proveedores/{proveedor_id}/evaluar",
    response_model=ProveedorResponse,
    summary="Evaluar proveedor",
    description="Registra evaluación de desempeño"
)
async def evaluar_proveedor(
    proveedor_id: str = Path(..., description="ID del proveedor"),
    request: EvaluarProveedorRequest = Body(...)
):
    """
    Evalúa proveedor:
    - Registra calificaciones por dimensión
    - Actualiza promedios
    - Ajusta estado según desempeño
    """
    proveedor = mock_service.proveedores.get(proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail=f"Proveedor {proveedor_id} no encontrado")
    
    # Calcular nuevos promedios
    n = proveedor["evaluaciones_totales"]
    
    def nuevo_promedio(actual, nuevo, n):
        if actual is None:
            return Decimal(str(nuevo))
        return (actual * n + nuevo) / (n + 1)
    
    proveedor["calificacion_calidad"] = nuevo_promedio(proveedor["calificacion_calidad"], request.calificacion_calidad, n)
    proveedor["calificacion_puntualidad"] = nuevo_promedio(proveedor["calificacion_puntualidad"], request.calificacion_puntualidad, n)
    proveedor["calificacion_precio"] = nuevo_promedio(proveedor["calificacion_precio"], request.calificacion_precio, n)
    
    # Promedio general
    proveedor["calificacion_promedio"] = (
        proveedor["calificacion_calidad"] + 
        proveedor["calificacion_puntualidad"] + 
        proveedor["calificacion_precio"] +
        request.calificacion_comunicacion +
        request.calificacion_limpieza
    ) / 5
    
    proveedor["evaluaciones_totales"] = n + 1
    proveedor["ultima_evaluacion"] = datetime.now()
    
    # Actualizar tasa de recomendación
    if proveedor["tasa_recomendacion"] is None:
        proveedor["tasa_recomendacion"] = Decimal("100") if request.recomendaria else Decimal("0")
    else:
        recomendaciones = proveedor["tasa_recomendacion"] * n / 100
        if request.recomendaria:
            recomendaciones += 1
        proveedor["tasa_recomendacion"] = (recomendaciones / (n + 1)) * 100
    
    # Cambiar estado de evaluación a activo si tiene suficientes evaluaciones positivas
    if proveedor["estado"] == EstadoProveedor.evaluacion and proveedor["evaluaciones_totales"] >= 3:
        if proveedor["calificacion_promedio"] >= 3.5:
            proveedor["estado"] = EstadoProveedor.activo
    
    proveedor["actualizado_en"] = datetime.now()
    
    return ProveedorResponse(**proveedor)

# =============================================================================
# ENDPOINTS - REPORTES Y ESTADÍSTICAS (4)
# =============================================================================

@router.get(
    "/estadisticas",
    response_model=EstadisticasMantencionResponse,
    summary="Estadísticas de mantención",
    description="Métricas agregadas del período"
)
async def estadisticas_mantencion(
    periodo_desde: date = Query(..., description="Fecha inicio período"),
    periodo_hasta: date = Query(..., description="Fecha fin período"),
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio")
):
    """Retorna estadísticas completas del período"""
    tareas = list(mock_service.tareas.values())
    planes = list(mock_service.planes.values())
    
    # Filtrar por período
    tareas_periodo = [t for t in tareas if t["fecha_creacion"].date() >= periodo_desde and 
                      t["fecha_creacion"].date() <= periodo_hasta]
    
    if propiedad_id:
        tareas_periodo = [t for t in tareas_periodo if t["propiedad_id"] == propiedad_id]
    if condominio_id:
        tareas_periodo = [t for t in tareas_periodo if t["condominio_id"] == condominio_id]
    
    # Calcular métricas
    total = len(tareas_periodo)
    preventivas = sum(1 for t in tareas_periodo if t["tipo"] == TipoMantencion.preventiva)
    correctivas = sum(1 for t in tareas_periodo if t["tipo"] == TipoMantencion.correctiva)
    completadas = sum(1 for t in tareas_periodo if t["estado"] == EstadoTarea.completada)
    pendientes = sum(1 for t in tareas_periodo if t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada])
    
    hoy = date.today()
    vencidas = sum(1 for t in tareas_periodo if t["fecha_programada"] and 
                   t["fecha_programada"] < hoy and 
                   t["estado"] not in [EstadoTarea.completada, EstadoTarea.cancelada])
    
    # Costos
    presupuesto = sum(t["presupuesto_uf"] or 0 for t in tareas_periodo)
    gasto = sum(t["costo_real_uf"] or 0 for t in tareas_periodo if t["costo_real_uf"])
    
    # Distribución por categoría
    dist_categoria = {}
    costos_categoria = {}
    for t in tareas_periodo:
        cat = t["categoria"].value if hasattr(t["categoria"], 'value') else str(t["categoria"])
        dist_categoria[cat] = dist_categoria.get(cat, 0) + 1
        if t["costo_real_uf"]:
            costos_categoria[cat] = costos_categoria.get(cat, Decimal("0")) + t["costo_real_uf"]
    
    # Distribución por prioridad
    dist_prioridad = {}
    for t in tareas_periodo:
        pri = t["prioridad"].value if hasattr(t["prioridad"], 'value') else str(t["prioridad"])
        dist_prioridad[pri] = dist_prioridad.get(pri, 0) + 1
    
    return EstadisticasMantencionResponse(
        periodo=f"{periodo_desde.isoformat()} a {periodo_hasta.isoformat()}",
        total_planes_activos=sum(1 for p in planes if p["activo"]),
        total_tareas_periodo=total,
        tareas_preventivas=preventivas,
        tareas_correctivas=correctivas,
        tareas_completadas=completadas,
        tareas_pendientes=pendientes,
        tareas_vencidas=vencidas,
        tiempo_promedio_resolucion_horas=Decimal("4.5"),
        tiempo_promedio_respuesta_horas=Decimal("2.1"),
        cumplimiento_sla_porcentaje=Decimal("92.5"),
        presupuesto_total_uf=presupuesto,
        gasto_total_uf=gasto,
        variacion_presupuesto_porcentaje=((gasto - presupuesto) / presupuesto * 100) if presupuesto > 0 else Decimal("0"),
        costo_promedio_tarea_uf=(gasto / completadas) if completadas > 0 else Decimal("0"),
        ahorro_preventivo_estimado_uf=Decimal("50"),
        distribucion_por_categoria=dist_categoria,
        costos_por_categoria=costos_categoria,
        distribucion_por_prioridad=dist_prioridad,
        proveedor_mas_usado={"nombre": "Ascensores Chile SpA", "tareas": 15},
        proveedor_mejor_calificado={"nombre": "Ascensores Chile SpA", "calificacion": 4.5},
        tendencia_tareas_mensual=[
            {"mes": "2024-01", "total": 12, "completadas": 10},
            {"mes": "2024-02", "total": 15, "completadas": 12}
        ],
        tendencia_costos_mensual=[
            {"mes": "2024-01", "presupuesto": 100, "gasto": 95},
            {"mes": "2024-02", "presupuesto": 120, "gasto": 115}
        ],
        indice_mantenimiento_preventivo=(preventivas / total * 100) if total > 0 else Decimal("0"),
        tasa_resolucion_primera_visita=Decimal("85.5"),
        satisfaccion_promedio=Decimal("4.3")
    )

@router.get(
    "/kpis",
    response_model=KPIsMantencionResponse,
    summary="KPIs de mantención",
    description="Indicadores clave de desempeño"
)
async def kpis_mantencion(
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    periodo: str = Query("ultimo_mes", description="Período: ultimo_mes, ultimo_trimestre, ultimo_ano")
):
    """Retorna KPIs técnicos de mantención"""
    return KPIsMantencionResponse(
        fecha_calculo=datetime.now(),
        periodo=periodo,
        mtbf_horas=Decimal("720"),  # 30 días entre fallas
        mttr_horas=Decimal("4.5"),  # 4.5 horas promedio reparación
        disponibilidad_porcentaje=Decimal("99.4"),
        confiabilidad_porcentaje=Decimal("98.2"),
        oee_porcentaje=Decimal("87.5"),
        costo_mantencion_por_m2_uf=Decimal("0.015"),
        roi_mantencion_preventiva=Decimal("2.5"),  # 250% retorno
        backlog_mantencion_uf=Decimal("25"),
        cumplimiento_plan_porcentaje=Decimal("92.3"),
        tareas_vencidas_count=3,
        emergencias_mes=2,
        variacion_vs_mes_anterior={
            "disponibilidad": Decimal("0.2"),
            "cumplimiento": Decimal("-1.5"),
            "costos": Decimal("5.2")
        }
    )

@router.post(
    "/reportes/generar",
    response_model=ReporteMantencionResponse,
    summary="Generar reporte de mantención",
    description="Genera reporte PDF/Excel del período"
)
async def generar_reporte(
    tipo_reporte: str = Query(..., description="ejecutivo, operativo, financiero, proveedor"),
    periodo_desde: date = Query(..., description="Fecha inicio"),
    periodo_hasta: date = Query(..., description="Fecha fin"),
    propiedad_id: Optional[str] = Query(None, description="Filtrar por propiedad"),
    condominio_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    formato: str = Query("pdf", regex="^(pdf|excel|html)$", description="Formato salida"),
    secciones: Optional[List[str]] = Query(None, description="Secciones a incluir"),
    background_tasks: BackgroundTasks = None
):
    """
    Genera reporte con secciones seleccionadas:
    - Resumen ejecutivo
    - Planes y cumplimiento
    - Tareas detalladas
    - Análisis de costos
    - Desempeño proveedores
    - Recomendaciones
    """
    reporte_id = str(uuid.uuid4())
    
    return ReporteMantencionResponse(
        id=reporte_id,
        tipo_reporte=tipo_reporte,
        titulo=f"Reporte de Mantención {tipo_reporte.title()} - {periodo_desde} a {periodo_hasta}",
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        generado_en=datetime.now(),
        generado_por="Sistema",
        formato=formato,
        url_descarga=f"/api/v1/mantenciones/reportes/{reporte_id}/download",
        secciones_incluidas=secciones or ["resumen", "planes", "tareas", "costos", "proveedores"],
        resumen_ejecutivo={
            "total_tareas": 45,
            "cumplimiento": 92.5,
            "gasto_vs_presupuesto": -5.2,
            "incidencias_criticas": 0
        },
        hallazgos_principales=[
            "Cumplimiento general sobre objetivo del 90%",
            "Reducción de emergencias vs período anterior",
            "Proveedor de ascensores mantiene excelente desempeño"
        ],
        recomendaciones=[
            "Incrementar frecuencia mantención preventiva área verde",
            "Evaluar nuevo proveedor para servicios eléctricos",
            "Programar revisión integral sistema contra incendio"
        ]
    )

@router.get(
    "/reportes/{reporte_id}/download",
    summary="Descargar reporte",
    description="Descarga reporte generado"
)
async def descargar_reporte(
    reporte_id: str = Path(..., description="ID del reporte")
):
    """Retorna archivo del reporte generado"""
    # En implementación real, retornar FileResponse
    raise HTTPException(status_code=501, detail="Generación de reportes en desarrollo")

# =============================================================================
# IMPORTACIÓN TIMEDELTA PARA TAREAS VENCIDAS
# =============================================================================

from datetime import timedelta
