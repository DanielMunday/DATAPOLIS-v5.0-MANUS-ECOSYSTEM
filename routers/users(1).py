"""
DATAPOLIS v3.0 - Router de Gestión de Usuarios
===============================================
Endpoints para gestión de usuarios, perfiles, roles y permisos.

Endpoints:
- GET /usuarios - Listar usuarios (admin)
- GET /usuarios/{id} - Obtener usuario específico
- PUT /usuarios/{id} - Actualizar usuario
- DELETE /usuarios/{id} - Eliminar usuario
- GET /usuarios/perfil - Perfil del usuario actual
- PUT /usuarios/perfil - Actualizar perfil propio
- PUT /usuarios/perfil/password - Cambiar contraseña
- POST /usuarios/perfil/avatar - Subir avatar
- GET /roles - Listar roles disponibles
- GET /roles/{id} - Detalle de rol
- POST /roles - Crear rol (admin)
- PUT /roles/{id} - Actualizar rol (admin)
- GET /permisos - Listar permisos del sistema
- POST /usuarios/{id}/roles - Asignar rol a usuario
- DELETE /usuarios/{id}/roles/{rol_id} - Quitar rol
- GET /equipos - Listar equipos
- POST /equipos - Crear equipo
- GET /equipos/{id}/miembros - Miembros del equipo
- POST /equipos/{id}/miembros - Agregar miembro
- GET /usuarios/actividad - Log de actividad
- GET /usuarios/estadisticas - Estadísticas de uso

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from pydantic import BaseModel, Field, EmailStr, validator
import secrets

from app.schemas.base import ResponseWrapper, ErrorResponse, PaginatedResponse


# =============================================================================
# CONFIGURACIÓN DEL ROUTER
# =============================================================================

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    responses={
        401: {"model": ErrorResponse, "description": "No autenticado"},
        403: {"model": ErrorResponse, "description": "Sin permisos"},
        404: {"model": ErrorResponse, "description": "Usuario no encontrado"}
    }
)


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================

class TipoUsuario(str, Enum):
    """Tipos de usuario en el sistema"""
    PROPIETARIO = "propietario"
    ADMINISTRADOR = "administrador"
    CORREDOR = "corredor"
    TASADOR = "tasador"
    CONTADOR = "contador"
    ABOGADO = "abogado"
    INVERSIONISTA = "inversionista"
    OTRO = "otro"


class EstadoUsuario(str, Enum):
    """Estados posibles de un usuario"""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    PENDIENTE = "pendiente"


class NivelSuscripcion(str, Enum):
    """Niveles de suscripción"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# =============================================================================
# SCHEMAS
# =============================================================================

class PerfilUsuario(BaseModel):
    """Perfil completo de usuario"""
    id: str
    email: EmailStr
    nombre: str
    apellido: str
    nombre_completo: str
    tipo_usuario: TipoUsuario
    empresa: Optional[str]
    rut_empresa: Optional[str]
    cargo: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    comuna: Optional[str]
    region: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    linkedin_url: Optional[str]
    website: Optional[str]
    
    # Estado y verificación
    estado: EstadoUsuario
    email_verificado: bool
    telefono_verificado: bool
    identidad_verificada: bool
    tiene_2fa: bool
    
    # Suscripción
    nivel_suscripcion: NivelSuscripcion
    suscripcion_expira: Optional[datetime]
    
    # Roles y permisos
    roles: List[str]
    permisos: List[str]
    
    # Metadata
    creado_en: datetime
    actualizado_en: datetime
    ultimo_login: Optional[datetime]
    
    # Estadísticas
    total_propiedades: int = 0
    total_valorizaciones: int = 0
    total_due_diligence: int = 0


class ActualizarPerfilRequest(BaseModel):
    """Request para actualizar perfil"""
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, min_length=2, max_length=100)
    tipo_usuario: Optional[TipoUsuario] = None
    empresa: Optional[str] = Field(None, max_length=200)
    rut_empresa: Optional[str] = None
    cargo: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = Field(None, max_length=300)
    comuna: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = None
    website: Optional[str] = None


class CambiarPasswordRequest(BaseModel):
    """Request para cambiar contraseña"""
    password_actual: str = Field(..., min_length=1)
    nueva_password: str = Field(..., min_length=8)
    confirmar_password: str
    
    @validator('confirmar_password')
    def passwords_match(cls, v, values):
        if 'nueva_password' in values and v != values['nueva_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


class UsuarioResumen(BaseModel):
    """Resumen de usuario para listados"""
    id: str
    email: str
    nombre_completo: str
    tipo_usuario: TipoUsuario
    empresa: Optional[str]
    estado: EstadoUsuario
    nivel_suscripcion: NivelSuscripcion
    ultimo_login: Optional[datetime]
    creado_en: datetime


class CrearUsuarioRequest(BaseModel):
    """Request para crear usuario (admin)"""
    email: EmailStr
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    tipo_usuario: TipoUsuario = TipoUsuario.OTRO
    empresa: Optional[str] = None
    rol_ids: List[str] = Field(default_factory=list)
    nivel_suscripcion: NivelSuscripcion = NivelSuscripcion.FREE
    enviar_invitacion: bool = True


class RolResponse(BaseModel):
    """Respuesta de rol"""
    id: str
    nombre: str
    codigo: str
    descripcion: str
    permisos: List[str]
    es_sistema: bool
    usuarios_count: int
    creado_en: datetime


class CrearRolRequest(BaseModel):
    """Request para crear rol"""
    nombre: str = Field(..., min_length=2, max_length=100)
    codigo: str = Field(..., min_length=2, max_length=50, regex="^[a-z_]+$")
    descripcion: str = Field(..., max_length=500)
    permisos: List[str] = Field(..., min_items=1)


class PermisoResponse(BaseModel):
    """Respuesta de permiso"""
    id: str
    codigo: str
    nombre: str
    descripcion: str
    modulo: str
    categoria: str


class EquipoResponse(BaseModel):
    """Respuesta de equipo"""
    id: str
    nombre: str
    descripcion: Optional[str]
    propietario_id: str
    propietario_nombre: str
    miembros_count: int
    creado_en: datetime


class CrearEquipoRequest(BaseModel):
    """Request para crear equipo"""
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class MiembroEquipo(BaseModel):
    """Miembro de un equipo"""
    id: str
    usuario_id: str
    nombre_completo: str
    email: str
    rol_equipo: str  # admin, member, viewer
    agregado_en: datetime
    agregado_por: str


class AgregarMiembroRequest(BaseModel):
    """Request para agregar miembro a equipo"""
    usuario_id: str
    rol_equipo: str = Field("member", regex="^(admin|member|viewer)$")


class ActividadUsuario(BaseModel):
    """Registro de actividad"""
    id: str
    tipo: str  # login, logout, crear, actualizar, eliminar, ver, descargar
    recurso: str  # propiedad, valorizacion, due_diligence, etc
    recurso_id: Optional[str]
    descripcion: str
    ip: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


class EstadisticasUsuario(BaseModel):
    """Estadísticas de uso del usuario"""
    periodo: str
    fecha_inicio: date
    fecha_fin: date
    
    # Actividad general
    total_logins: int
    dias_activos: int
    tiempo_promedio_sesion_minutos: int
    
    # Uso de módulos
    valorizaciones_realizadas: int
    due_diligence_ejecutados: int
    credit_scores_calculados: int
    propiedades_consultadas: int
    informes_generados: int
    
    # Tendencias
    tendencia_uso: str  # aumentando, estable, disminuyendo
    modulo_mas_usado: str
    hora_pico_actividad: int


# =============================================================================
# DEPENDENCIAS
# =============================================================================

class UsuarioActual(BaseModel):
    """Usuario actual mock para dependencias"""
    id: str
    email: str
    nombre: str
    apellido: str
    roles: List[str]
    permisos: List[str]
    es_admin: bool


async def get_current_user() -> UsuarioActual:
    """Obtiene usuario actual (mock)"""
    return UsuarioActual(
        id="usr_demo_001",
        email="demo@datapolis.cl",
        nombre="Usuario",
        apellido="Demo",
        roles=["admin"],
        permisos=["*"],
        es_admin=True
    )


async def require_admin(current_user: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
    """Requiere permisos de administrador"""
    if not current_user.es_admin and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


# =============================================================================
# ENDPOINTS DE LISTADO Y BÚSQUEDA
# =============================================================================

@router.get(
    "",
    response_model=ResponseWrapper[PaginatedResponse[UsuarioResumen]],
    summary="Listar usuarios",
    description="Lista usuarios con filtros y paginación. Requiere permisos de administrador."
)
async def listar_usuarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    buscar: Optional[str] = Query(None, description="Buscar por nombre o email"),
    tipo: Optional[TipoUsuario] = Query(None),
    estado: Optional[EstadoUsuario] = Query(None),
    nivel: Optional[NivelSuscripcion] = Query(None),
    rol: Optional[str] = Query(None, description="Filtrar por rol"),
    ordenar_por: str = Query("creado_en", regex="^(nombre|email|creado_en|ultimo_login)$"),
    orden: str = Query("desc", regex="^(asc|desc)$"),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Lista usuarios del sistema.
    
    Filtros disponibles:
    - buscar: texto en nombre o email
    - tipo: tipo de usuario
    - estado: activo, inactivo, suspendido, pendiente
    - nivel: nivel de suscripción
    - rol: rol específico
    """
    # Mock de usuarios
    usuarios = [
        UsuarioResumen(
            id="usr_001",
            email="admin@datapolis.cl",
            nombre_completo="Administrador Principal",
            tipo_usuario=TipoUsuario.ADMINISTRADOR,
            empresa="DATAPOLIS SpA",
            estado=EstadoUsuario.ACTIVO,
            nivel_suscripcion=NivelSuscripcion.ENTERPRISE,
            ultimo_login=datetime.utcnow() - timedelta(hours=1),
            creado_en=datetime.utcnow() - timedelta(days=365)
        ),
        UsuarioResumen(
            id="usr_002",
            email="corredor@ejemplo.cl",
            nombre_completo="Juan Corredor Silva",
            tipo_usuario=TipoUsuario.CORREDOR,
            empresa="Corredora ABC",
            estado=EstadoUsuario.ACTIVO,
            nivel_suscripcion=NivelSuscripcion.PROFESSIONAL,
            ultimo_login=datetime.utcnow() - timedelta(days=2),
            creado_en=datetime.utcnow() - timedelta(days=180)
        ),
        UsuarioResumen(
            id="usr_003",
            email="tasador@ejemplo.cl",
            nombre_completo="María Tasadora López",
            tipo_usuario=TipoUsuario.TASADOR,
            empresa="Tasaciones Chile",
            estado=EstadoUsuario.ACTIVO,
            nivel_suscripcion=NivelSuscripcion.PROFESSIONAL,
            ultimo_login=datetime.utcnow() - timedelta(hours=5),
            creado_en=datetime.utcnow() - timedelta(days=90)
        )
    ]
    
    return ResponseWrapper(
        success=True,
        data=PaginatedResponse(
            items=usuarios,
            total=len(usuarios),
            page=page,
            page_size=page_size,
            total_pages=1
        ),
        message=f"{len(usuarios)} usuarios encontrados"
    )


@router.get(
    "/{usuario_id}",
    response_model=ResponseWrapper[PerfilUsuario],
    summary="Obtener usuario",
    description="Obtiene información detallada de un usuario específico."
)
async def obtener_usuario(
    usuario_id: str,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Obtiene perfil completo de un usuario.
    
    Usuarios normales solo pueden ver su propio perfil.
    Administradores pueden ver cualquier perfil.
    """
    # Verificar permisos
    if usuario_id != current_user.id and not current_user.es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este usuario"
        )
    
    # Mock de perfil
    perfil = PerfilUsuario(
        id=usuario_id,
        email="demo@datapolis.cl",
        nombre="Usuario",
        apellido="Demo",
        nombre_completo="Usuario Demo",
        tipo_usuario=TipoUsuario.ADMINISTRADOR,
        empresa="DATAPOLIS SpA",
        rut_empresa="76.XXX.XXX-X",
        cargo="Arquitecto Senior",
        telefono="+56 9 XXXX XXXX",
        direccion="Av. Principal 123",
        comuna="Santiago",
        region="Metropolitana",
        avatar_url=None,
        bio="Profesional con 18 años de experiencia",
        linkedin_url="https://linkedin.com/in/demo",
        website="https://datapolis.cl",
        estado=EstadoUsuario.ACTIVO,
        email_verificado=True,
        telefono_verificado=True,
        identidad_verificada=True,
        tiene_2fa=True,
        nivel_suscripcion=NivelSuscripcion.ENTERPRISE,
        suscripcion_expira=datetime.utcnow() + timedelta(days=365),
        roles=["admin", "tasador"],
        permisos=["*"],
        creado_en=datetime.utcnow() - timedelta(days=365),
        actualizado_en=datetime.utcnow() - timedelta(days=1),
        ultimo_login=datetime.utcnow() - timedelta(hours=2),
        total_propiedades=150,
        total_valorizaciones=87,
        total_due_diligence=23
    )
    
    return ResponseWrapper(
        success=True,
        data=perfil,
        message="Perfil obtenido"
    )


# =============================================================================
# ENDPOINTS DE PERFIL PROPIO
# =============================================================================

@router.get(
    "/perfil/me",
    response_model=ResponseWrapper[PerfilUsuario],
    summary="Mi perfil",
    description="Obtiene el perfil del usuario autenticado."
)
async def mi_perfil(
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtiene el perfil del usuario actual."""
    # Reutiliza el endpoint de obtener usuario
    return await obtener_usuario(current_user.id, current_user)


@router.put(
    "/perfil/me",
    response_model=ResponseWrapper[PerfilUsuario],
    summary="Actualizar mi perfil",
    description="Actualiza el perfil del usuario autenticado."
)
async def actualizar_mi_perfil(
    request: ActualizarPerfilRequest,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Actualiza el perfil propio.
    
    Solo se actualizan los campos proporcionados.
    """
    # TODO: Actualizar en BD
    
    # Mock de respuesta
    perfil = PerfilUsuario(
        id=current_user.id,
        email=current_user.email,
        nombre=request.nombre or current_user.nombre,
        apellido=request.apellido or current_user.apellido,
        nombre_completo=f"{request.nombre or current_user.nombre} {request.apellido or current_user.apellido}",
        tipo_usuario=request.tipo_usuario or TipoUsuario.ADMINISTRADOR,
        empresa=request.empresa,
        rut_empresa=request.rut_empresa,
        cargo=request.cargo,
        telefono=request.telefono,
        direccion=request.direccion,
        comuna=request.comuna,
        region=request.region,
        avatar_url=None,
        bio=request.bio,
        linkedin_url=request.linkedin_url,
        website=request.website,
        estado=EstadoUsuario.ACTIVO,
        email_verificado=True,
        telefono_verificado=True,
        identidad_verificada=True,
        tiene_2fa=True,
        nivel_suscripcion=NivelSuscripcion.ENTERPRISE,
        suscripcion_expira=datetime.utcnow() + timedelta(days=365),
        roles=["admin"],
        permisos=["*"],
        creado_en=datetime.utcnow() - timedelta(days=365),
        actualizado_en=datetime.utcnow(),
        ultimo_login=datetime.utcnow() - timedelta(hours=2),
        total_propiedades=150,
        total_valorizaciones=87,
        total_due_diligence=23
    )
    
    return ResponseWrapper(
        success=True,
        data=perfil,
        message="Perfil actualizado correctamente"
    )


@router.put(
    "/perfil/password",
    response_model=ResponseWrapper[dict],
    summary="Cambiar contraseña",
    description="Cambia la contraseña del usuario autenticado."
)
async def cambiar_password(
    request: CambiarPasswordRequest,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Cambia la contraseña propia.
    
    - Verifica contraseña actual
    - Valida complejidad de nueva contraseña
    - Cierra otras sesiones opcionalmente
    """
    # TODO: Verificar contraseña actual y actualizar
    
    return ResponseWrapper(
        success=True,
        data={"password_cambiado": True},
        message="Contraseña actualizada correctamente"
    )


@router.post(
    "/perfil/avatar",
    response_model=ResponseWrapper[dict],
    summary="Subir avatar",
    description="Sube o actualiza la imagen de avatar del usuario."
)
async def subir_avatar(
    archivo: UploadFile = File(...),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Sube imagen de avatar.
    
    - Formatos: JPG, PNG, GIF, WebP
    - Tamaño máximo: 5MB
    - Se redimensiona a 256x256
    """
    # Validar tipo de archivo
    tipos_permitidos = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if archivo.content_type not in tipos_permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Usa: {', '.join(tipos_permitidos)}"
        )
    
    # Validar tamaño (5MB max)
    contenido = await archivo.read()
    if len(contenido) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo excede el tamaño máximo de 5MB"
        )
    
    # TODO: Guardar archivo y procesar
    
    return ResponseWrapper(
        success=True,
        data={
            "avatar_url": f"/avatars/{current_user.id}.webp",
            "tamaño_original": len(contenido),
            "formato": archivo.content_type
        },
        message="Avatar actualizado correctamente"
    )


# =============================================================================
# ENDPOINTS DE ADMINISTRACIÓN DE USUARIOS
# =============================================================================

@router.post(
    "",
    response_model=ResponseWrapper[UsuarioResumen],
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un nuevo usuario en el sistema. Requiere permisos de administrador."
)
async def crear_usuario(
    request: CrearUsuarioRequest,
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Crea un nuevo usuario.
    
    - Valida que el email no exista
    - Asigna roles indicados
    - Opcionalmente envía invitación por email
    """
    # TODO: Verificar email único y crear usuario
    
    nuevo_id = f"usr_{secrets.token_hex(8)}"
    
    usuario = UsuarioResumen(
        id=nuevo_id,
        email=request.email,
        nombre_completo=f"{request.nombre} {request.apellido}",
        tipo_usuario=request.tipo_usuario,
        empresa=request.empresa,
        estado=EstadoUsuario.PENDIENTE,
        nivel_suscripcion=request.nivel_suscripcion,
        ultimo_login=None,
        creado_en=datetime.utcnow()
    )
    
    return ResponseWrapper(
        success=True,
        data=usuario,
        message="Usuario creado. Se ha enviado invitación por email." if request.enviar_invitacion else "Usuario creado."
    )


@router.put(
    "/{usuario_id}",
    response_model=ResponseWrapper[PerfilUsuario],
    summary="Actualizar usuario",
    description="Actualiza un usuario existente. Requiere permisos de administrador."
)
async def actualizar_usuario(
    usuario_id: str,
    request: ActualizarPerfilRequest,
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Actualiza información de un usuario (admin).
    
    Permite modificar campos que el usuario no puede cambiar por sí mismo.
    """
    # TODO: Actualizar en BD
    
    return ResponseWrapper(
        success=True,
        data=None,  # Retornaría el perfil actualizado
        message="Usuario actualizado"
    )


@router.delete(
    "/{usuario_id}",
    response_model=ResponseWrapper[dict],
    summary="Eliminar usuario",
    description="Elimina o desactiva un usuario. Requiere permisos de administrador."
)
async def eliminar_usuario(
    usuario_id: str,
    permanente: bool = Query(False, description="Eliminación permanente (irreversible)"),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Elimina o desactiva un usuario.
    
    - Por defecto solo desactiva (soft delete)
    - Con permanente=true elimina datos (cumplimiento GDPR)
    """
    if usuario_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo"
        )
    
    # TODO: Eliminar/desactivar en BD
    
    return ResponseWrapper(
        success=True,
        data={
            "usuario_id": usuario_id,
            "eliminado_permanente": permanente
        },
        message="Usuario eliminado permanentemente" if permanente else "Usuario desactivado"
    )


@router.put(
    "/{usuario_id}/estado",
    response_model=ResponseWrapper[dict],
    summary="Cambiar estado de usuario",
    description="Activa, suspende o desactiva un usuario."
)
async def cambiar_estado_usuario(
    usuario_id: str,
    nuevo_estado: EstadoUsuario,
    razon: Optional[str] = Query(None, description="Razón del cambio de estado"),
    current_user: UsuarioActual = Depends(require_admin)
):
    """
    Cambia el estado de un usuario.
    
    Estados:
    - activo: puede usar el sistema
    - inactivo: desactivado temporalmente
    - suspendido: suspendido por violación de términos
    - pendiente: esperando verificación
    """
    # TODO: Actualizar estado y enviar notificación
    
    return ResponseWrapper(
        success=True,
        data={
            "usuario_id": usuario_id,
            "estado_anterior": "activo",
            "estado_nuevo": nuevo_estado.value,
            "razon": razon
        },
        message=f"Estado cambiado a {nuevo_estado.value}"
    )


# =============================================================================
# ENDPOINTS DE ROLES Y PERMISOS
# =============================================================================

@router.get(
    "/roles",
    response_model=ResponseWrapper[List[RolResponse]],
    summary="Listar roles",
    description="Lista todos los roles disponibles en el sistema."
)
async def listar_roles(
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista roles del sistema."""
    roles = [
        RolResponse(
            id="rol_admin",
            nombre="Administrador",
            codigo="admin",
            descripcion="Acceso completo al sistema",
            permisos=["*"],
            es_sistema=True,
            usuarios_count=3,
            creado_en=datetime.utcnow() - timedelta(days=365)
        ),
        RolResponse(
            id="rol_tasador",
            nombre="Tasador",
            codigo="tasador",
            descripcion="Puede crear y gestionar valorizaciones",
            permisos=["valorizar:crear", "valorizar:ver", "valorizar:editar", "informes:generar"],
            es_sistema=True,
            usuarios_count=15,
            creado_en=datetime.utcnow() - timedelta(days=365)
        ),
        RolResponse(
            id="rol_corredor",
            nombre="Corredor",
            codigo="corredor",
            descripcion="Acceso a módulos de corretaje",
            permisos=["propiedades:ver", "valorizar:ver", "creditscore:ver"],
            es_sistema=True,
            usuarios_count=42,
            creado_en=datetime.utcnow() - timedelta(days=365)
        ),
        RolResponse(
            id="rol_viewer",
            nombre="Solo Lectura",
            codigo="viewer",
            descripcion="Solo puede ver información",
            permisos=["propiedades:ver", "informes:ver"],
            es_sistema=True,
            usuarios_count=28,
            creado_en=datetime.utcnow() - timedelta(days=365)
        )
    ]
    
    return ResponseWrapper(
        success=True,
        data=roles,
        message=f"{len(roles)} roles encontrados"
    )


@router.get(
    "/roles/{rol_id}",
    response_model=ResponseWrapper[RolResponse],
    summary="Obtener rol",
    description="Obtiene detalles de un rol específico."
)
async def obtener_rol(
    rol_id: str,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Obtiene detalle de un rol."""
    # Mock
    rol = RolResponse(
        id=rol_id,
        nombre="Tasador",
        codigo="tasador",
        descripcion="Puede crear y gestionar valorizaciones",
        permisos=["valorizar:crear", "valorizar:ver", "valorizar:editar", "informes:generar"],
        es_sistema=True,
        usuarios_count=15,
        creado_en=datetime.utcnow() - timedelta(days=365)
    )
    
    return ResponseWrapper(
        success=True,
        data=rol,
        message="Rol obtenido"
    )


@router.post(
    "/roles",
    response_model=ResponseWrapper[RolResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Crear rol",
    description="Crea un nuevo rol personalizado. Requiere permisos de administrador."
)
async def crear_rol(
    request: CrearRolRequest,
    current_user: UsuarioActual = Depends(require_admin)
):
    """Crea un rol personalizado."""
    nuevo_id = f"rol_{secrets.token_hex(8)}"
    
    rol = RolResponse(
        id=nuevo_id,
        nombre=request.nombre,
        codigo=request.codigo,
        descripcion=request.descripcion,
        permisos=request.permisos,
        es_sistema=False,
        usuarios_count=0,
        creado_en=datetime.utcnow()
    )
    
    return ResponseWrapper(
        success=True,
        data=rol,
        message="Rol creado correctamente"
    )


@router.get(
    "/permisos",
    response_model=ResponseWrapper[List[PermisoResponse]],
    summary="Listar permisos",
    description="Lista todos los permisos disponibles en el sistema."
)
async def listar_permisos(
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista permisos del sistema agrupados por módulo."""
    permisos = [
        PermisoResponse(
            id="perm_001",
            codigo="propiedades:ver",
            nombre="Ver Propiedades",
            descripcion="Puede ver listado de propiedades",
            modulo="propiedades",
            categoria="lectura"
        ),
        PermisoResponse(
            id="perm_002",
            codigo="propiedades:crear",
            nombre="Crear Propiedades",
            descripcion="Puede registrar nuevas propiedades",
            modulo="propiedades",
            categoria="escritura"
        ),
        PermisoResponse(
            id="perm_003",
            codigo="valorizar:crear",
            nombre="Crear Valorizaciones",
            descripcion="Puede crear nuevas valorizaciones",
            modulo="valorizacion",
            categoria="escritura"
        ),
        PermisoResponse(
            id="perm_004",
            codigo="valorizar:ver",
            nombre="Ver Valorizaciones",
            descripcion="Puede ver valorizaciones existentes",
            modulo="valorizacion",
            categoria="lectura"
        ),
        PermisoResponse(
            id="perm_005",
            codigo="duediligence:ejecutar",
            nombre="Ejecutar Due Diligence",
            descripcion="Puede ejecutar análisis de due diligence",
            modulo="due_diligence",
            categoria="escritura"
        ),
        PermisoResponse(
            id="perm_006",
            codigo="informes:generar",
            nombre="Generar Informes",
            descripcion="Puede generar informes en PDF/DOCX",
            modulo="informes",
            categoria="escritura"
        )
    ]
    
    if modulo:
        permisos = [p for p in permisos if p.modulo == modulo]
    
    return ResponseWrapper(
        success=True,
        data=permisos,
        message=f"{len(permisos)} permisos encontrados"
    )


@router.post(
    "/{usuario_id}/roles",
    response_model=ResponseWrapper[dict],
    summary="Asignar rol a usuario",
    description="Asigna un rol a un usuario."
)
async def asignar_rol(
    usuario_id: str,
    rol_id: str,
    current_user: UsuarioActual = Depends(require_admin)
):
    """Asigna un rol a un usuario."""
    return ResponseWrapper(
        success=True,
        data={
            "usuario_id": usuario_id,
            "rol_id": rol_id,
            "asignado": True
        },
        message="Rol asignado correctamente"
    )


@router.delete(
    "/{usuario_id}/roles/{rol_id}",
    response_model=ResponseWrapper[dict],
    summary="Quitar rol de usuario",
    description="Remueve un rol de un usuario."
)
async def quitar_rol(
    usuario_id: str,
    rol_id: str,
    current_user: UsuarioActual = Depends(require_admin)
):
    """Remueve un rol de un usuario."""
    return ResponseWrapper(
        success=True,
        data={
            "usuario_id": usuario_id,
            "rol_id": rol_id,
            "removido": True
        },
        message="Rol removido correctamente"
    )


# =============================================================================
# ENDPOINTS DE EQUIPOS
# =============================================================================

@router.get(
    "/equipos",
    response_model=ResponseWrapper[List[EquipoResponse]],
    summary="Listar equipos",
    description="Lista equipos del usuario actual."
)
async def listar_equipos(
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista equipos donde el usuario es miembro o propietario."""
    equipos = [
        EquipoResponse(
            id="eq_001",
            nombre="Equipo Tasaciones",
            descripcion="Equipo de tasadores certificados",
            propietario_id=current_user.id,
            propietario_nombre=f"{current_user.nombre} {current_user.apellido}",
            miembros_count=5,
            creado_en=datetime.utcnow() - timedelta(days=180)
        ),
        EquipoResponse(
            id="eq_002",
            nombre="Proyecto Inmobiliario ABC",
            descripcion="Equipo para proyecto específico",
            propietario_id="usr_002",
            propietario_nombre="Otro Usuario",
            miembros_count=8,
            creado_en=datetime.utcnow() - timedelta(days=90)
        )
    ]
    
    return ResponseWrapper(
        success=True,
        data=equipos,
        message=f"{len(equipos)} equipos encontrados"
    )


@router.post(
    "/equipos",
    response_model=ResponseWrapper[EquipoResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Crear equipo",
    description="Crea un nuevo equipo."
)
async def crear_equipo(
    request: CrearEquipoRequest,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Crea un nuevo equipo con el usuario actual como propietario."""
    nuevo_id = f"eq_{secrets.token_hex(8)}"
    
    equipo = EquipoResponse(
        id=nuevo_id,
        nombre=request.nombre,
        descripcion=request.descripcion,
        propietario_id=current_user.id,
        propietario_nombre=f"{current_user.nombre} {current_user.apellido}",
        miembros_count=1,
        creado_en=datetime.utcnow()
    )
    
    return ResponseWrapper(
        success=True,
        data=equipo,
        message="Equipo creado correctamente"
    )


@router.get(
    "/equipos/{equipo_id}/miembros",
    response_model=ResponseWrapper[List[MiembroEquipo]],
    summary="Listar miembros de equipo",
    description="Lista los miembros de un equipo."
)
async def listar_miembros_equipo(
    equipo_id: str,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Lista miembros de un equipo."""
    miembros = [
        MiembroEquipo(
            id="mem_001",
            usuario_id=current_user.id,
            nombre_completo=f"{current_user.nombre} {current_user.apellido}",
            email=current_user.email,
            rol_equipo="admin",
            agregado_en=datetime.utcnow() - timedelta(days=180),
            agregado_por=current_user.id
        ),
        MiembroEquipo(
            id="mem_002",
            usuario_id="usr_002",
            nombre_completo="Juan Pérez",
            email="juan@ejemplo.cl",
            rol_equipo="member",
            agregado_en=datetime.utcnow() - timedelta(days=90),
            agregado_por=current_user.id
        )
    ]
    
    return ResponseWrapper(
        success=True,
        data=miembros,
        message=f"{len(miembros)} miembros en el equipo"
    )


@router.post(
    "/equipos/{equipo_id}/miembros",
    response_model=ResponseWrapper[MiembroEquipo],
    status_code=status.HTTP_201_CREATED,
    summary="Agregar miembro a equipo",
    description="Agrega un usuario como miembro del equipo."
)
async def agregar_miembro_equipo(
    equipo_id: str,
    request: AgregarMiembroRequest,
    current_user: UsuarioActual = Depends(get_current_user)
):
    """Agrega un miembro al equipo."""
    miembro = MiembroEquipo(
        id=f"mem_{secrets.token_hex(8)}",
        usuario_id=request.usuario_id,
        nombre_completo="Nuevo Miembro",  # Se obtendría de BD
        email="nuevo@ejemplo.cl",
        rol_equipo=request.rol_equipo,
        agregado_en=datetime.utcnow(),
        agregado_por=current_user.id
    )
    
    return ResponseWrapper(
        success=True,
        data=miembro,
        message="Miembro agregado al equipo"
    )


# =============================================================================
# ENDPOINTS DE ACTIVIDAD Y ESTADÍSTICAS
# =============================================================================

@router.get(
    "/actividad",
    response_model=ResponseWrapper[List[ActividadUsuario]],
    summary="Log de actividad",
    description="Obtiene el log de actividad del usuario actual."
)
async def obtener_actividad(
    dias: int = Query(7, ge=1, le=90, description="Días de historial"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de actividad"),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Obtiene log de actividad del usuario.
    
    Tipos: login, logout, crear, actualizar, eliminar, ver, descargar
    """
    actividades = [
        ActividadUsuario(
            id="act_001",
            tipo="login",
            recurso="auth",
            recurso_id=None,
            descripcion="Inicio de sesión desde Chrome en Windows",
            ip="192.168.1.100",
            user_agent="Chrome/120.0",
            timestamp=datetime.utcnow() - timedelta(hours=2)
        ),
        ActividadUsuario(
            id="act_002",
            tipo="crear",
            recurso="valorizacion",
            recurso_id="val_12345",
            descripcion="Creó valorización para propiedad ROL 1234-5",
            ip="192.168.1.100",
            user_agent="Chrome/120.0",
            timestamp=datetime.utcnow() - timedelta(hours=1)
        ),
        ActividadUsuario(
            id="act_003",
            tipo="descargar",
            recurso="informe",
            recurso_id="inf_67890",
            descripcion="Descargó informe de valorización en PDF",
            ip="192.168.1.100",
            user_agent="Chrome/120.0",
            timestamp=datetime.utcnow() - timedelta(minutes=30)
        )
    ]
    
    if tipo:
        actividades = [a for a in actividades if a.tipo == tipo]
    
    return ResponseWrapper(
        success=True,
        data=actividades,
        message=f"{len(actividades)} actividades en los últimos {dias} días"
    )


@router.get(
    "/estadisticas",
    response_model=ResponseWrapper[EstadisticasUsuario],
    summary="Estadísticas de uso",
    description="Obtiene estadísticas de uso del usuario actual."
)
async def obtener_estadisticas(
    periodo: str = Query("mes", regex="^(semana|mes|trimestre|año)$"),
    current_user: UsuarioActual = Depends(get_current_user)
):
    """
    Obtiene estadísticas de uso del usuario.
    
    Periodos: semana, mes, trimestre, año
    """
    dias_periodo = {"semana": 7, "mes": 30, "trimestre": 90, "año": 365}
    dias = dias_periodo.get(periodo, 30)
    
    stats = EstadisticasUsuario(
        periodo=periodo,
        fecha_inicio=date.today() - timedelta(days=dias),
        fecha_fin=date.today(),
        total_logins=45,
        dias_activos=22,
        tiempo_promedio_sesion_minutos=38,
        valorizaciones_realizadas=12,
        due_diligence_ejecutados=3,
        credit_scores_calculados=8,
        propiedades_consultadas=156,
        informes_generados=15,
        tendencia_uso="aumentando",
        modulo_mas_usado="valorizacion",
        hora_pico_actividad=10
    )
    
    return ResponseWrapper(
        success=True,
        data=stats,
        message=f"Estadísticas del último {periodo}"
    )


# =============================================================================
# ENDPOINT DE SALUD
# =============================================================================

@router.get(
    "/health",
    response_model=dict,
    include_in_schema=False
)
async def health_check():
    """Health check del módulo de usuarios."""
    return {
        "status": "healthy",
        "service": "usuarios",
        "timestamp": datetime.utcnow().isoformat()
    }
