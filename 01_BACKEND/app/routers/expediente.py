# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Router M00 Expediente Universal
API REST para gestión documental centralizada de propiedades
Endpoints para expedientes, documentos, workflows y alertas
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum
import io
import json

# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class TipoExpedienteEnum(str, Enum):
    """Tipos de expediente soportados"""
    PROPIEDAD_INDIVIDUAL = "propiedad_individual"
    UNIDAD_COPROPIEDAD = "unidad_copropiedad"
    CONDOMINIO = "condominio"
    TERRENO = "terreno"
    PROYECTO_INMOBILIARIO = "proyecto_inmobiliario"
    PARCELA_AGRICOLA = "parcela_agricola"
    LOCAL_COMERCIAL = "local_comercial"
    OFICINA = "oficina"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"


class EstadoExpedienteEnum(str, Enum):
    """Estados del ciclo de vida del expediente"""
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    PENDIENTE_DOCUMENTOS = "pendiente_documentos"
    COMPLETO = "completo"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    ARCHIVADO = "archivado"
    CERRADO = "cerrado"


class TipoDocumentoEnum(str, Enum):
    """Tipos de documento inmobiliario"""
    ESCRITURA_PROPIEDAD = "escritura_propiedad"
    CERTIFICADO_DOMINIO = "certificado_dominio"
    CERTIFICADO_GRAVAMENES = "certificado_gravamenes"
    CERTIFICADO_HIPOTECAS = "certificado_hipotecas"
    CERTIFICADO_PROHIBICIONES = "certificado_prohibiciones"
    PLANO_PROPIEDAD = "plano_propiedad"
    PLANO_SUBDIVISION = "plano_subdivision"
    PLANO_FUSION = "plano_fusion"
    PERMISO_EDIFICACION = "permiso_edificacion"
    RECEPCION_FINAL = "recepcion_final"
    CERTIFICADO_INFORMACIONES_PREVIAS = "certificado_informaciones_previas"
    AVALUO_COMERCIAL = "avaluo_comercial"
    TASACION_BANCARIA = "tasacion_bancaria"
    CONTRATO_ARRIENDO = "contrato_arriendo"
    CONTRATO_PROMESA = "contrato_promesa"
    PODER_NOTARIAL = "poder_notarial"
    CERTIFICADO_DEUDA_CONTRIBUCIONES = "certificado_deuda_contribuciones"
    CERTIFICADO_NUMERO = "certificado_numero"
    CERTIFICADO_EXPROPIACION = "certificado_expropiacion"
    REGLAMENTO_COPROPIEDAD = "reglamento_copropiedad"
    ACTA_ASAMBLEA = "acta_asamblea"
    BALANCE_CONDOMINIO = "balance_condominio"
    POLIZA_SEGURO = "poliza_seguro"
    INFORME_INSPECCION = "informe_inspeccion"
    FOTOGRAFIA = "fotografia"
    OTRO = "otro"


class EstadoDocumentoEnum(str, Enum):
    """Estados del documento"""
    PENDIENTE = "pendiente"
    CARGADO = "cargado"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    VENCIDO = "vencido"
    REEMPLAZADO = "reemplazado"


class NivelConfidencialidadEnum(str, Enum):
    """Niveles de acceso al documento"""
    PUBLICO = "publico"
    INTERNO = "interno"
    CONFIDENCIAL = "confidencial"
    RESTRINGIDO = "restringido"


class TipoWorkflowEnum(str, Enum):
    """Tipos de workflow de aprobación"""
    REVISION_SIMPLE = "revision_simple"
    APROBACION_LEGAL = "aprobacion_legal"
    APROBACION_TECNICA = "aprobacion_tecnica"
    APROBACION_MULTIPLE = "aprobacion_multiple"
    VALIDACION_EXTERNA = "validacion_externa"


class SeveridadAlertaEnum(str, Enum):
    """Severidad de alertas"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# --- Request/Response Schemas ---

class PropiedadBasicaSchema(BaseModel):
    """Información básica de propiedad para expediente"""
    rol_sii: str = Field(..., description="Rol SII de la propiedad")
    direccion: str = Field(..., description="Dirección completa")
    comuna: str = Field(..., description="Comuna")
    region: str = Field(default="Metropolitana", description="Región")
    tipo_propiedad: Optional[str] = None
    superficie_terreno_m2: Optional[float] = None
    superficie_construida_m2: Optional[float] = None
    ano_construccion: Optional[int] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    avaluo_fiscal_uf: Optional[float] = None


class CrearExpedienteRequest(BaseModel):
    """Request para crear expediente"""
    tipo: TipoExpedienteEnum
    titulo: str = Field(..., min_length=5, max_length=200)
    descripcion: Optional[str] = None
    propiedad: PropiedadBasicaSchema
    propietario_id: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_rut: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ActualizarExpedienteRequest(BaseModel):
    """Request para actualizar expediente"""
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    propietario_id: Optional[str] = None
    propietario_nombre: Optional[str] = None
    administrador_id: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CambiarEstadoRequest(BaseModel):
    """Request para cambiar estado del expediente"""
    nuevo_estado: EstadoExpedienteEnum
    comentario: Optional[str] = None


class DocumentoUploadRequest(BaseModel):
    """Metadata para carga de documento"""
    tipo: TipoDocumentoEnum
    nombre: str = Field(..., min_length=3, max_length=200)
    descripcion: Optional[str] = None
    fecha_emision: Optional[date] = None
    numero_documento: Optional[str] = None
    emisor: Optional[str] = None
    confidencialidad: NivelConfidencialidadEnum = NivelConfidencialidadEnum.INTERNO
    metadata: Optional[Dict[str, Any]] = None


class ActualizarDocumentoRequest(BaseModel):
    """Request para actualizar documento"""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_emision: Optional[date] = None
    numero_documento: Optional[str] = None
    emisor: Optional[str] = None
    confidencialidad: Optional[NivelConfidencialidadEnum] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AccionDocumentoRequest(BaseModel):
    """Request para aprobar/rechazar documento"""
    comentario: Optional[str] = None
    motivo: Optional[str] = None


class IniciarWorkflowRequest(BaseModel):
    """Request para iniciar workflow de aprobación"""
    documento_id: str
    tipo_workflow: TipoWorkflowEnum
    aprobadores: List[str] = Field(..., min_items=1)
    comentarios: Optional[str] = None


class AvanzarWorkflowRequest(BaseModel):
    """Request para avanzar en workflow"""
    accion: str = Field(..., pattern="^(aprobar|rechazar)$")
    comentario: Optional[str] = None


class ResolverAlertaRequest(BaseModel):
    """Request para resolver alerta"""
    resolucion: str = Field(..., min_length=5)


class VincularModuloRequest(BaseModel):
    """Request para vincular expediente a módulo"""
    modulo: str = Field(..., description="Código módulo (M01, M03, etc.)")
    referencia_id: str = Field(..., description="ID referencia en el módulo")
    metadata: Optional[Dict[str, Any]] = None


class BusquedaExpedientesRequest(BaseModel):
    """Request para búsqueda avanzada de expedientes"""
    query: Optional[str] = None
    tipo: Optional[TipoExpedienteEnum] = None
    estado: Optional[EstadoExpedienteEnum] = None
    propietario_id: Optional[str] = None
    comuna: Optional[str] = None
    region: Optional[str] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    completitud_minima: Optional[int] = Field(None, ge=0, le=100)
    tiene_alertas: Optional[bool] = None
    tags: Optional[List[str]] = None
    ordenar_por: Optional[str] = "fecha_creacion"
    orden: Optional[str] = "desc"
    limite: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class GenerarReporteRequest(BaseModel):
    """Request para generar reporte de expediente"""
    formato: str = Field(default="json", pattern="^(json|pdf|xlsx)$")
    secciones: Optional[List[str]] = None


# --- Response Schemas ---

class DocumentoResponse(BaseModel):
    """Documento en respuesta"""
    id: str
    tipo: str
    nombre: str
    archivo_url: Optional[str] = None
    tamano_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    estado: str
    confidencialidad: str
    version: int
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    emisor: Optional[str] = None
    numero_documento: Optional[str] = None
    esta_vigente: bool = True
    dias_para_vencer: Optional[int] = None
    creado_en: datetime
    aprobado_por: Optional[str] = None
    tags: List[str] = []

    class Config:
        from_attributes = True


class AlertaResponse(BaseModel):
    """Alerta en respuesta"""
    id: str
    tipo: str
    titulo: str
    mensaje: str
    severidad: str
    fecha_generacion: datetime
    fecha_vencimiento: Optional[datetime] = None
    documento_id: Optional[str] = None
    leida: bool = False
    resuelta: bool = False
    acciones: List[str] = []

    class Config:
        from_attributes = True


class WorkflowResponse(BaseModel):
    """Workflow en respuesta"""
    id: str
    tipo: str
    documento_id: str
    estado: str
    etapa_actual: int
    etapas: List[Dict[str, Any]]
    creado_por: str
    creado_en: datetime
    completado_en: Optional[datetime] = None
    resultado: Optional[str] = None

    class Config:
        from_attributes = True


class EventoResponse(BaseModel):
    """Evento de auditoría"""
    id: str
    tipo: str
    descripcion: str
    detalle: Optional[Dict[str, Any]] = None
    usuario_id: str
    timestamp: datetime
    documento_id: Optional[str] = None

    class Config:
        from_attributes = True


class ExpedienteResponse(BaseModel):
    """Expediente completo en respuesta"""
    id: str
    codigo: str
    tipo: str
    estado: str
    titulo: str
    descripcion: Optional[str] = None
    
    # Propiedad
    rol_sii: str
    direccion: str
    comuna: str
    region: str
    
    # Propietario
    propietario_id: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_rut: Optional[str] = None
    administrador_id: Optional[str] = None
    
    # Métricas
    completitud_pct: int = 0
    documentos_pendientes: List[str] = []
    documentos_vencidos: List[str] = []
    alertas_activas: int = 0
    
    # Colecciones (opcionales según include)
    documentos: Optional[List[DocumentoResponse]] = None
    alertas: Optional[List[AlertaResponse]] = None
    workflows: Optional[List[WorkflowResponse]] = None
    eventos: Optional[List[EventoResponse]] = None
    
    # Metadata
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    modulos_vinculados: List[str] = []
    
    # Timestamps
    creado_en: datetime
    actualizado_en: datetime
    creado_por: str

    class Config:
        from_attributes = True


class ExpedienteListResponse(BaseModel):
    """Respuesta lista de expedientes"""
    expedientes: List[ExpedienteResponse]
    total: int
    pagina: int
    paginas: int
    limite: int


class BusquedaResultadoResponse(BaseModel):
    """Resultado de búsqueda"""
    expediente_id: str
    codigo: str
    titulo: str
    tipo: str
    estado: str
    rol_sii: str
    direccion: str
    comuna: str
    completitud_pct: int
    alertas_activas: int
    relevancia_score: float
    fragmentos_relevantes: List[str] = []

    class Config:
        from_attributes = True


class EstadisticasExpedientesResponse(BaseModel):
    """Estadísticas de expedientes"""
    total_expedientes: int
    por_tipo: Dict[str, int]
    por_estado: Dict[str, int]
    completitud_promedio: float
    documentos_totales: int
    documentos_pendientes: int
    documentos_vencidos: int
    alertas_activas: int
    tendencia_creacion: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


# ============================================================================
# ROUTER DEFINITION
# ============================================================================

router = APIRouter(
    prefix="/expedientes",
    tags=["M00 - Expediente Universal"],
    responses={
        404: {"description": "Expediente no encontrado"},
        403: {"description": "Acceso denegado"},
        422: {"description": "Error de validación"}
    }
)


# ============================================================================
# ENDPOINTS - GESTIÓN DE EXPEDIENTES
# ============================================================================

@router.post(
    "",
    response_model=ExpedienteResponse,
    status_code=201,
    summary="Crear nuevo expediente",
    description="Crea un nuevo expediente documental para una propiedad"
)
async def crear_expediente(
    request: CrearExpedienteRequest,
    usuario_id: str = Query(default="usr_sistema", description="ID usuario creador")
):
    """
    Crear nuevo expediente con información de propiedad.
    
    El expediente se crea en estado BORRADOR y se determinan automáticamente
    los documentos requeridos según el tipo de expediente.
    
    - **tipo**: Tipo de expediente (propiedad_individual, condominio, etc.)
    - **titulo**: Título descriptivo del expediente
    - **propiedad**: Información básica de la propiedad
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    # Construir objeto propiedad
    propiedad_data = {
        "rol_sii": request.propiedad.rol_sii,
        "direccion": request.propiedad.direccion,
        "comuna": request.propiedad.comuna,
        "region": request.propiedad.region,
        "tipo_propiedad": request.propiedad.tipo_propiedad,
        "superficies": {
            "terreno_m2": request.propiedad.superficie_terreno_m2,
            "construida_m2": request.propiedad.superficie_construida_m2
        },
        "ano_construccion": request.propiedad.ano_construccion,
        "coordenadas": {
            "latitud": request.propiedad.latitud,
            "longitud": request.propiedad.longitud
        } if request.propiedad.latitud else None,
        "avaluo_fiscal_uf": request.propiedad.avaluo_fiscal_uf
    }
    
    expediente = await service.crear_expediente(
        tipo=request.tipo.value,
        titulo=request.titulo,
        propiedad=propiedad_data,
        propietario={
            "id": request.propietario_id,
            "nombre": request.propietario_nombre,
            "rut": request.propietario_rut
        } if request.propietario_id or request.propietario_nombre else None,
        creado_por=usuario_id,
        descripcion=request.descripcion,
        tags=request.tags,
        metadata=request.metadata
    )
    
    return _expediente_to_response(expediente)


@router.get(
    "",
    response_model=ExpedienteListResponse,
    summary="Listar expedientes",
    description="Obtiene lista paginada de expedientes con filtros opcionales"
)
async def listar_expedientes(
    tipo: Optional[TipoExpedienteEnum] = None,
    estado: Optional[EstadoExpedienteEnum] = None,
    comuna: Optional[str] = None,
    propietario_id: Optional[str] = None,
    tiene_alertas: Optional[bool] = None,
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100)
):
    """
    Lista expedientes con filtros y paginación.
    
    - **tipo**: Filtrar por tipo de expediente
    - **estado**: Filtrar por estado
    - **comuna**: Filtrar por comuna
    - **propietario_id**: Filtrar por propietario
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    offset = (pagina - 1) * limite
    
    resultados, total = await service.buscar_expedientes(
        tipo=tipo.value if tipo else None,
        estado=estado.value if estado else None,
        comuna=comuna,
        propietario_id=propietario_id,
        tiene_alertas=tiene_alertas,
        limite=limite,
        offset=offset
    )
    
    paginas = (total + limite - 1) // limite
    
    # Convertir a respuesta
    expedientes_response = []
    for exp in resultados:
        expedientes_response.append(_expediente_to_response(exp))
    
    return ExpedienteListResponse(
        expedientes=expedientes_response,
        total=total,
        pagina=pagina,
        paginas=paginas,
        limite=limite
    )


@router.get(
    "/estadisticas",
    response_model=EstadisticasExpedientesResponse,
    summary="Estadísticas de expedientes",
    description="Obtiene métricas agregadas de expedientes"
)
async def obtener_estadisticas(
    usuario_id: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None
):
    """
    Obtiene estadísticas agregadas de expedientes.
    
    Incluye:
    - Total de expedientes por tipo y estado
    - Completitud promedio
    - Documentos totales, pendientes y vencidos
    - Alertas activas
    - Tendencia de creación
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    stats = await service.obtener_estadisticas(
        usuario_id=usuario_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )
    
    return EstadisticasExpedientesResponse(
        total_expedientes=stats.total,
        por_tipo=stats.por_tipo,
        por_estado=stats.por_estado,
        completitud_promedio=stats.completitud_promedio,
        documentos_totales=stats.documentos_totales,
        documentos_pendientes=stats.documentos_pendientes,
        documentos_vencidos=stats.documentos_vencidos,
        alertas_activas=stats.alertas_activas,
        tendencia_creacion=stats.tendencia_creacion
    )


@router.post(
    "/buscar",
    response_model=Dict[str, Any],
    summary="Búsqueda avanzada",
    description="Búsqueda avanzada de expedientes con múltiples criterios"
)
async def buscar_expedientes(
    request: BusquedaExpedientesRequest
):
    """
    Búsqueda avanzada de expedientes.
    
    Permite buscar por:
    - Texto libre (query)
    - Tipo, estado, propietario
    - Comuna, región
    - Rango de fechas
    - Completitud mínima
    - Presencia de alertas
    - Tags
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultados, total = await service.buscar_expedientes(
        query=request.query,
        tipo=request.tipo.value if request.tipo else None,
        estado=request.estado.value if request.estado else None,
        propietario_id=request.propietario_id,
        comuna=request.comuna,
        region=request.region,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        completitud_minima=request.completitud_minima,
        tiene_alertas=request.tiene_alertas,
        tags=request.tags,
        ordenar_por=request.ordenar_por,
        orden=request.orden,
        limite=request.limite,
        offset=request.offset
    )
    
    return {
        "resultados": [_resultado_to_response(r) for r in resultados],
        "total": total,
        "limite": request.limite,
        "offset": request.offset
    }


@router.get(
    "/{expediente_id}",
    response_model=ExpedienteResponse,
    summary="Obtener expediente",
    description="Obtiene un expediente por su ID"
)
async def obtener_expediente(
    expediente_id: str = Path(..., description="ID del expediente"),
    incluir_documentos: bool = Query(default=True),
    incluir_alertas: bool = Query(default=True),
    incluir_workflows: bool = Query(default=False),
    incluir_eventos: bool = Query(default=False)
):
    """
    Obtiene expediente completo por ID.
    
    Parámetros opcionales para incluir colecciones relacionadas:
    - incluir_documentos: Lista de documentos
    - incluir_alertas: Lista de alertas activas
    - incluir_workflows: Workflows de aprobación
    - incluir_eventos: Historial de eventos
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    expediente = await service.obtener_expediente(
        expediente_id=expediente_id,
        incluir_documentos=incluir_documentos,
        incluir_eventos=incluir_eventos,
        incluir_alertas=incluir_alertas
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    return _expediente_to_response(expediente, incluir_workflows)


@router.patch(
    "/{expediente_id}",
    response_model=ExpedienteResponse,
    summary="Actualizar expediente",
    description="Actualiza información del expediente"
)
async def actualizar_expediente(
    expediente_id: str = Path(..., description="ID del expediente"),
    request: ActualizarExpedienteRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Actualiza campos del expediente.
    
    Solo se actualizan los campos proporcionados.
    Los cambios se registran en el historial de eventos.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    actualizaciones = request.model_dump(exclude_unset=True, exclude_none=True)
    
    if not actualizaciones:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos a actualizar")
    
    expediente = await service.actualizar_expediente(
        expediente_id=expediente_id,
        actualizaciones=actualizaciones,
        usuario_id=usuario_id
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    return _expediente_to_response(expediente)


@router.post(
    "/{expediente_id}/estado",
    response_model=ExpedienteResponse,
    summary="Cambiar estado",
    description="Cambia el estado del expediente"
)
async def cambiar_estado_expediente(
    expediente_id: str = Path(..., description="ID del expediente"),
    request: CambiarEstadoRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Cambia el estado del expediente.
    
    Estados permitidos:
    - borrador → en_revision, pendiente_documentos
    - en_revision → completo, pendiente_documentos, rechazado
    - pendiente_documentos → en_revision
    - completo → activo
    - activo → suspendido, archivado
    - suspendido → activo, archivado
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    try:
        expediente = await service.cambiar_estado(
            expediente_id=expediente_id,
            nuevo_estado=request.nuevo_estado.value,
            usuario_id=usuario_id,
            comentario=request.comentario
        )
        
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        return _expediente_to_response(expediente)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{expediente_id}",
    status_code=204,
    summary="Eliminar expediente",
    description="Elimina (archiva) un expediente"
)
async def eliminar_expediente(
    expediente_id: str = Path(..., description="ID del expediente"),
    hard_delete: bool = Query(default=False, description="Eliminación permanente"),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Elimina un expediente.
    
    Por defecto realiza soft-delete (archivado).
    Con hard_delete=true, elimina permanentemente.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultado = await service.eliminar_expediente(
        expediente_id=expediente_id,
        usuario_id=usuario_id,
        hard_delete=hard_delete
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    return None


# ============================================================================
# ENDPOINTS - GESTIÓN DE DOCUMENTOS
# ============================================================================

@router.post(
    "/{expediente_id}/documentos",
    response_model=DocumentoResponse,
    status_code=201,
    summary="Cargar documento",
    description="Carga un nuevo documento al expediente"
)
async def cargar_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    archivo: UploadFile = File(..., description="Archivo a cargar"),
    tipo: TipoDocumentoEnum = Form(...),
    nombre: str = Form(..., min_length=3, max_length=200),
    descripcion: Optional[str] = Form(None),
    fecha_emision: Optional[str] = Form(None),
    numero_documento: Optional[str] = Form(None),
    emisor: Optional[str] = Form(None),
    confidencialidad: NivelConfidencialidadEnum = Form(NivelConfidencialidadEnum.INTERNO),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Carga documento al expediente.
    
    El sistema:
    - Calcula hash SHA256 del contenido
    - Determina fecha de vencimiento según tipo
    - Versiona automáticamente si ya existe documento del mismo tipo
    - Actualiza completitud del expediente
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    # Leer contenido del archivo
    contenido = await archivo.read()
    
    # Parsear fecha si viene
    fecha_emision_date = None
    if fecha_emision:
        try:
            fecha_emision_date = date.fromisoformat(fecha_emision)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido")
    
    documento = await service.agregar_documento(
        expediente_id=expediente_id,
        tipo=tipo.value,
        nombre=nombre,
        archivo_url=f"/storage/expedientes/{expediente_id}/{archivo.filename}",
        archivo_contenido=contenido,
        mime_type=archivo.content_type,
        usuario_id=usuario_id,
        descripcion=descripcion,
        fecha_emision=fecha_emision_date,
        numero_documento=numero_documento,
        emisor=emisor,
        confidencialidad=confidencialidad.value
    )
    
    if not documento:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    return _documento_to_response(documento)


@router.get(
    "/{expediente_id}/documentos",
    response_model=List[DocumentoResponse],
    summary="Listar documentos",
    description="Lista todos los documentos del expediente"
)
async def listar_documentos(
    expediente_id: str = Path(..., description="ID del expediente"),
    tipo: Optional[TipoDocumentoEnum] = None,
    estado: Optional[EstadoDocumentoEnum] = None
):
    """
    Lista documentos del expediente con filtros opcionales.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    expediente = await service.obtener_expediente(
        expediente_id=expediente_id,
        incluir_documentos=True
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    documentos = expediente.documentos
    
    # Filtrar
    if tipo:
        documentos = [d for d in documentos if d.tipo == tipo.value]
    if estado:
        documentos = [d for d in documentos if d.estado == estado.value]
    
    return [_documento_to_response(d) for d in documentos]


@router.get(
    "/{expediente_id}/documentos/{documento_id}",
    response_model=DocumentoResponse,
    summary="Obtener documento",
    description="Obtiene un documento específico"
)
async def obtener_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    documento_id: str = Path(..., description="ID del documento")
):
    """
    Obtiene información de un documento específico.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    documento = await service.obtener_documento(
        expediente_id=expediente_id,
        documento_id=documento_id
    )
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return _documento_to_response(documento)


@router.patch(
    "/{expediente_id}/documentos/{documento_id}",
    response_model=DocumentoResponse,
    summary="Actualizar documento",
    description="Actualiza metadata del documento"
)
async def actualizar_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    documento_id: str = Path(..., description="ID del documento"),
    request: ActualizarDocumentoRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Actualiza metadata de un documento.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    actualizaciones = request.model_dump(exclude_unset=True, exclude_none=True)
    
    documento = await service.actualizar_documento(
        expediente_id=expediente_id,
        documento_id=documento_id,
        actualizaciones=actualizaciones,
        usuario_id=usuario_id
    )
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return _documento_to_response(documento)


@router.post(
    "/{expediente_id}/documentos/{documento_id}/aprobar",
    response_model=DocumentoResponse,
    summary="Aprobar documento",
    description="Aprueba un documento en revisión"
)
async def aprobar_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    documento_id: str = Path(..., description="ID del documento"),
    request: AccionDocumentoRequest = Body(default=None),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Aprueba un documento, cambiando su estado a APROBADO.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    comentario = request.comentario if request else None
    
    documento = await service.aprobar_documento(
        expediente_id=expediente_id,
        documento_id=documento_id,
        usuario_id=usuario_id,
        comentario=comentario
    )
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return _documento_to_response(documento)


@router.post(
    "/{expediente_id}/documentos/{documento_id}/rechazar",
    response_model=DocumentoResponse,
    summary="Rechazar documento",
    description="Rechaza un documento en revisión"
)
async def rechazar_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    documento_id: str = Path(..., description="ID del documento"),
    request: AccionDocumentoRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Rechaza un documento, requiere motivo.
    Genera alerta de alta prioridad.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    if not request.motivo:
        raise HTTPException(status_code=400, detail="Debe proporcionar motivo de rechazo")
    
    documento = await service.rechazar_documento(
        expediente_id=expediente_id,
        documento_id=documento_id,
        usuario_id=usuario_id,
        motivo=request.motivo
    )
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return _documento_to_response(documento)


@router.get(
    "/{expediente_id}/documentos/{documento_id}/versiones",
    response_model=List[DocumentoResponse],
    summary="Historial de versiones",
    description="Obtiene historial de versiones de un tipo de documento"
)
async def obtener_versiones_documento(
    expediente_id: str = Path(..., description="ID del expediente"),
    tipo_documento: TipoDocumentoEnum = Query(..., description="Tipo de documento")
):
    """
    Obtiene todas las versiones de un tipo de documento.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    versiones = await service.obtener_versiones_documento(
        expediente_id=expediente_id,
        tipo_documento=tipo_documento.value
    )
    
    return [_documento_to_response(v) for v in versiones]


# ============================================================================
# ENDPOINTS - WORKFLOWS
# ============================================================================

@router.post(
    "/{expediente_id}/workflows",
    response_model=WorkflowResponse,
    status_code=201,
    summary="Iniciar workflow",
    description="Inicia un workflow de aprobación para un documento"
)
async def iniciar_workflow(
    expediente_id: str = Path(..., description="ID del expediente"),
    request: IniciarWorkflowRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Inicia workflow de aprobación.
    
    Tipos disponibles:
    - revision_simple: Una etapa, un aprobador
    - aprobacion_legal: Dos etapas (revisión legal + aprobación final)
    - aprobacion_tecnica: Dos etapas (revisión técnica + aprobación final)
    - aprobacion_multiple: N etapas según cantidad de aprobadores
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    workflow = await service.iniciar_workflow(
        expediente_id=expediente_id,
        documento_id=request.documento_id,
        tipo_workflow=request.tipo_workflow.value,
        usuario_id=usuario_id,
        aprobadores=request.aprobadores
    )
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Expediente o documento no encontrado")
    
    return _workflow_to_response(workflow)


@router.get(
    "/{expediente_id}/workflows",
    response_model=List[WorkflowResponse],
    summary="Listar workflows",
    description="Lista workflows del expediente"
)
async def listar_workflows(
    expediente_id: str = Path(..., description="ID del expediente"),
    estado: Optional[str] = Query(None, pattern="^(pendiente|en_proceso|completado|cancelado)$")
):
    """
    Lista workflows del expediente con filtro opcional por estado.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    expediente = await service.obtener_expediente(
        expediente_id=expediente_id,
        incluir_documentos=False
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    workflows = expediente.workflows or []
    
    if estado:
        workflows = [w for w in workflows if w.estado == estado]
    
    return [_workflow_to_response(w) for w in workflows]


@router.post(
    "/{expediente_id}/workflows/{workflow_id}/avanzar",
    response_model=WorkflowResponse,
    summary="Avanzar workflow",
    description="Aprueba o rechaza la etapa actual del workflow"
)
async def avanzar_workflow(
    expediente_id: str = Path(..., description="ID del expediente"),
    workflow_id: str = Path(..., description="ID del workflow"),
    request: AvanzarWorkflowRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Avanza el workflow aprobando o rechazando la etapa actual.
    
    - accion: "aprobar" o "rechazar"
    - comentario: Opcional, comentarios del aprobador
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    workflow = await service.avanzar_workflow(
        expediente_id=expediente_id,
        workflow_id=workflow_id,
        usuario_id=usuario_id,
        accion=request.accion,
        comentario=request.comentario
    )
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    
    return _workflow_to_response(workflow)


# ============================================================================
# ENDPOINTS - ALERTAS
# ============================================================================

@router.get(
    "/{expediente_id}/alertas",
    response_model=List[AlertaResponse],
    summary="Listar alertas",
    description="Lista alertas del expediente"
)
async def listar_alertas(
    expediente_id: str = Path(..., description="ID del expediente"),
    severidad: Optional[SeveridadAlertaEnum] = None,
    solo_no_leidas: bool = Query(default=False),
    solo_activas: bool = Query(default=True)
):
    """
    Lista alertas del expediente con filtros.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    alertas = await service.obtener_alertas(
        expediente_id=expediente_id,
        severidad=severidad.value if severidad else None,
        solo_no_leidas=solo_no_leidas,
        solo_activas=solo_activas
    )
    
    return [_alerta_to_response(a) for a in alertas]


@router.post(
    "/{expediente_id}/alertas/{alerta_id}/leer",
    status_code=204,
    summary="Marcar alerta como leída",
    description="Marca una alerta como leída"
)
async def marcar_alerta_leida(
    expediente_id: str = Path(..., description="ID del expediente"),
    alerta_id: str = Path(..., description="ID de la alerta"),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Marca una alerta como leída.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultado = await service.marcar_alerta_leida(
        expediente_id=expediente_id,
        alerta_id=alerta_id,
        usuario_id=usuario_id
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    return None


@router.post(
    "/{expediente_id}/alertas/{alerta_id}/resolver",
    status_code=204,
    summary="Resolver alerta",
    description="Resuelve una alerta con descripción de la resolución"
)
async def resolver_alerta(
    expediente_id: str = Path(..., description="ID del expediente"),
    alerta_id: str = Path(..., description="ID de la alerta"),
    request: ResolverAlertaRequest = Body(...),
    usuario_id: str = Query(default="usr_sistema")
):
    """
    Resuelve una alerta proporcionando descripción de la resolución.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultado = await service.resolver_alerta(
        expediente_id=expediente_id,
        alerta_id=alerta_id,
        usuario_id=usuario_id,
        resolucion=request.resolucion
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    return None


@router.get(
    "/{expediente_id}/documentos-vencidos",
    response_model=List[Dict[str, Any]],
    summary="Documentos vencidos",
    description="Lista documentos vencidos o próximos a vencer"
)
async def verificar_documentos_vencidos(
    expediente_id: str = Path(..., description="ID del expediente"),
    dias_anticipacion: int = Query(default=30, ge=1, le=90)
):
    """
    Verifica documentos vencidos o próximos a vencer.
    
    Retorna documentos cuya fecha de vencimiento:
    - Ya pasó (vencidos)
    - Está dentro de los próximos N días (por vencer)
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultado = await service.verificar_documentos_vencidos(
        expediente_id=expediente_id
    )
    
    return resultado


# ============================================================================
# ENDPOINTS - INTEGRACIONES
# ============================================================================

@router.post(
    "/{expediente_id}/vincular-modulo",
    status_code=201,
    summary="Vincular a módulo",
    description="Vincula el expediente a otro módulo DATAPOLIS"
)
async def vincular_modulo(
    expediente_id: str = Path(..., description="ID del expediente"),
    request: VincularModuloRequest = Body(...)
):
    """
    Vincula el expediente a otro módulo del sistema.
    
    Módulos disponibles:
    - M01: Ficha Propiedad
    - M03: Credit Score
    - M04: Valorización
    - M05: Arriendos
    - M12: Due Diligence
    - etc.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    resultado = await service.vincular_modulo(
        expediente_id=expediente_id,
        modulo=request.modulo,
        referencia_id=request.referencia_id,
        metadata=request.metadata
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    return {"status": "vinculado", "modulo": request.modulo, "referencia_id": request.referencia_id}


@router.get(
    "/{expediente_id}/modulos",
    response_model=Dict[str, List[str]],
    summary="Módulos vinculados",
    description="Obtiene módulos vinculados al expediente"
)
async def obtener_modulos_vinculados(
    expediente_id: str = Path(..., description="ID del expediente")
):
    """
    Obtiene referencias a otros módulos vinculados al expediente.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    referencias = await service.obtener_referencias_modulos(
        expediente_id=expediente_id
    )
    
    return referencias


# ============================================================================
# ENDPOINTS - REPORTES
# ============================================================================

@router.post(
    "/{expediente_id}/reporte",
    summary="Generar reporte",
    description="Genera reporte del expediente en formato seleccionado"
)
async def generar_reporte(
    expediente_id: str = Path(..., description="ID del expediente"),
    request: GenerarReporteRequest = Body(default=None),
    background_tasks: BackgroundTasks = None
):
    """
    Genera reporte completo del expediente.
    
    Formatos disponibles:
    - json: Datos estructurados
    - pdf: Documento PDF
    - xlsx: Hoja de cálculo
    
    Secciones:
    - general: Información básica
    - documentos: Lista de documentos
    - eventos: Historial de eventos
    - alertas: Alertas activas y resueltas
    - cumplimiento: Análisis de cumplimiento documental
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    formato = request.formato if request else "json"
    secciones = request.secciones if request else None
    
    reporte = await service.generar_reporte_expediente(
        expediente_id=expediente_id,
        formato=formato,
        secciones=secciones
    )
    
    if not reporte:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    if formato == "json":
        return JSONResponse(content=reporte)
    else:
        # Para PDF/XLSX retornar metadata del archivo generado
        return {
            "formato": formato,
            "expediente_id": expediente_id,
            "archivo_url": reporte.get("archivo_url"),
            "generado_en": datetime.now().isoformat()
        }


@router.get(
    "/{expediente_id}/eventos",
    response_model=List[EventoResponse],
    summary="Historial de eventos",
    description="Obtiene historial de eventos del expediente"
)
async def obtener_eventos(
    expediente_id: str = Path(..., description="ID del expediente"),
    tipo: Optional[str] = None,
    limite: int = Query(default=50, ge=1, le=200)
):
    """
    Obtiene historial de eventos (auditoría) del expediente.
    """
    from ..services.m00_expediente import ExpedienteUniversalService
    
    service = ExpedienteUniversalService()
    
    expediente = await service.obtener_expediente(
        expediente_id=expediente_id,
        incluir_eventos=True
    )
    
    if not expediente:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    eventos = expediente.eventos or []
    
    if tipo:
        eventos = [e for e in eventos if e.tipo == tipo]
    
    # Limitar y ordenar por más reciente
    eventos = sorted(eventos, key=lambda e: e.timestamp, reverse=True)[:limite]
    
    return [_evento_to_response(e) for e in eventos]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _expediente_to_response(expediente, incluir_workflows: bool = False) -> ExpedienteResponse:
    """Convierte expediente a response schema"""
    return ExpedienteResponse(
        id=expediente.id,
        codigo=expediente.codigo,
        tipo=expediente.tipo.value if hasattr(expediente.tipo, 'value') else expediente.tipo,
        estado=expediente.estado.value if hasattr(expediente.estado, 'value') else expediente.estado,
        titulo=expediente.titulo,
        descripcion=expediente.descripcion,
        rol_sii=expediente.propiedad.rol_sii if expediente.propiedad else "",
        direccion=expediente.propiedad.direccion if expediente.propiedad else "",
        comuna=expediente.propiedad.comuna if expediente.propiedad else "",
        region=expediente.propiedad.region if expediente.propiedad else "Metropolitana",
        propietario_id=expediente.propietario.get("id") if expediente.propietario else None,
        propietario_nombre=expediente.propietario.get("nombre") if expediente.propietario else None,
        propietario_rut=expediente.propietario.get("rut") if expediente.propietario else None,
        administrador_id=expediente.administrador_id,
        completitud_pct=expediente.completitud_pct,
        documentos_pendientes=expediente.documentos_pendientes,
        documentos_vencidos=expediente.documentos_vencidos,
        alertas_activas=len([a for a in (expediente.alertas or []) if not a.resuelta]),
        documentos=[_documento_to_response(d) for d in (expediente.documentos or [])],
        alertas=[_alerta_to_response(a) for a in (expediente.alertas or [])],
        workflows=[_workflow_to_response(w) for w in (expediente.workflows or [])] if incluir_workflows else None,
        eventos=[_evento_to_response(e) for e in (expediente.eventos or [])[:20]] if expediente.eventos else None,
        tags=expediente.tags or [],
        metadata=expediente.metadata or {},
        modulos_vinculados=expediente.modulos_vinculados or [],
        creado_en=expediente.fecha_creacion,
        actualizado_en=expediente.fecha_actualizacion,
        creado_por=expediente.creado_por
    )


def _documento_to_response(documento) -> DocumentoResponse:
    """Convierte documento a response schema"""
    return DocumentoResponse(
        id=documento.id,
        tipo=documento.tipo.value if hasattr(documento.tipo, 'value') else documento.tipo,
        nombre=documento.nombre,
        archivo_url=documento.archivo_url,
        tamano_bytes=documento.tamano_bytes,
        mime_type=documento.mime_type,
        estado=documento.estado.value if hasattr(documento.estado, 'value') else documento.estado,
        confidencialidad=documento.confidencialidad.value if hasattr(documento.confidencialidad, 'value') else documento.confidencialidad,
        version=documento.version,
        fecha_emision=documento.fecha_emision,
        fecha_vencimiento=documento.fecha_vencimiento,
        emisor=documento.emisor,
        numero_documento=documento.numero_documento,
        esta_vigente=documento.esta_vigente(),
        dias_para_vencer=documento.dias_para_vencer(),
        creado_en=documento.creado_en,
        aprobado_por=documento.aprobado_por,
        tags=documento.tags or []
    )


def _alerta_to_response(alerta) -> AlertaResponse:
    """Convierte alerta a response schema"""
    return AlertaResponse(
        id=alerta.id,
        tipo=alerta.tipo,
        titulo=alerta.titulo,
        mensaje=alerta.mensaje,
        severidad=alerta.severidad,
        fecha_generacion=alerta.fecha_generacion,
        fecha_vencimiento=alerta.fecha_vencimiento,
        documento_id=alerta.documento_id,
        leida=alerta.leida,
        resuelta=alerta.resuelta,
        acciones=alerta.acciones or []
    )


def _workflow_to_response(workflow) -> WorkflowResponse:
    """Convierte workflow a response schema"""
    return WorkflowResponse(
        id=workflow.id,
        tipo=workflow.tipo.value if hasattr(workflow.tipo, 'value') else workflow.tipo,
        documento_id=workflow.documento_id,
        estado=workflow.estado,
        etapa_actual=workflow.etapa_actual,
        etapas=workflow.etapas,
        creado_por=workflow.creado_por,
        creado_en=workflow.creado_en,
        completado_en=workflow.completado_en,
        resultado=workflow.resultado
    )


def _evento_to_response(evento) -> EventoResponse:
    """Convierte evento a response schema"""
    return EventoResponse(
        id=evento.id,
        tipo=evento.tipo.value if hasattr(evento.tipo, 'value') else evento.tipo,
        descripcion=evento.descripcion,
        detalle=evento.detalle,
        usuario_id=evento.usuario_id,
        timestamp=evento.timestamp,
        documento_id=evento.documento_id
    )


def _resultado_to_response(resultado) -> BusquedaResultadoResponse:
    """Convierte resultado búsqueda a response schema"""
    return BusquedaResultadoResponse(
        expediente_id=resultado.expediente_id,
        codigo=resultado.codigo,
        titulo=resultado.titulo,
        tipo=resultado.tipo,
        estado=resultado.estado,
        rol_sii=resultado.rol_sii,
        direccion=resultado.direccion,
        comuna=resultado.comuna,
        completitud_pct=resultado.completitud_pct,
        alertas_activas=resultado.alertas_activas,
        relevancia_score=resultado.relevancia_score,
        fragmentos_relevantes=resultado.fragmentos_relevantes
    )
