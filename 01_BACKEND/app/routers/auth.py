"""
DATAPOLIS v3.0 - Router de Autenticación
=========================================
Endpoints para autenticación JWT, OAuth2, gestión de sesiones.

Endpoints:
- POST /auth/registro - Registro de nuevos usuarios
- POST /auth/login - Autenticación y obtención de tokens
- POST /auth/refresh - Renovación de access token
- POST /auth/logout - Cierre de sesión
- POST /auth/recuperar-password - Solicitud recuperación
- POST /auth/reset-password - Cambio de contraseña
- GET /auth/verificar-email/{token} - Verificación de email
- POST /auth/oauth/{provider} - OAuth2 con Google/Microsoft
- GET /auth/sesiones - Sesiones activas del usuario
- DELETE /auth/sesiones/{id} - Cerrar sesión específica
- POST /auth/2fa/activar - Activar autenticación 2FA
- POST /auth/2fa/verificar - Verificar código 2FA
- GET /auth/me - Información del usuario autenticado

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr, validator
import secrets
import hashlib
import re

from app.schemas.auth import (
    TokenResponse,
    UserCreate,
    UserResponse,
    PasswordReset,
    TwoFactorSetup
)
from app.schemas.base import ResponseWrapper, ErrorResponse


# =============================================================================
# CONFIGURACIÓN DEL ROUTER
# =============================================================================

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
    responses={
        401: {"model": ErrorResponse, "description": "No autenticado"},
        403: {"model": ErrorResponse, "description": "Sin permisos"},
        422: {"model": ErrorResponse, "description": "Error de validación"}
    }
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# =============================================================================
# SCHEMAS ESPECÍFICOS DE AUTH
# =============================================================================

class ProveedorOAuth(str, Enum):
    """Proveedores OAuth2 soportados"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"


class RegistroRequest(BaseModel):
    """Request para registro de usuario"""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña (mín 8 caracteres)")
    password_confirm: str = Field(..., description="Confirmación de contraseña")
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    empresa: Optional[str] = Field(None, max_length=200)
    rut_empresa: Optional[str] = Field(None, description="RUT empresa (formato XX.XXX.XXX-X)")
    telefono: Optional[str] = Field(None, max_length=20)
    acepta_terminos: bool = Field(..., description="Aceptación de términos y condiciones")
    acepta_privacidad: bool = Field(..., description="Aceptación de política de privacidad")
    
    @validator('password')
    def validar_password(cls, v):
        """Validar complejidad de contraseña"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        """Validar que las contraseñas coincidan"""
        if 'password' in values and v != values['password']:
            raise ValueError('Las contraseñas no coinciden')
        return v
    
    @validator('rut_empresa')
    def validar_rut(cls, v):
        """Validar formato RUT chileno"""
        if v is None:
            return v
        # Remover puntos y guión
        rut_limpio = v.replace(".", "").replace("-", "")
        if len(rut_limpio) < 8 or len(rut_limpio) > 9:
            raise ValueError('RUT inválido')
        return v


class LoginRequest(BaseModel):
    """Request para login"""
    email: EmailStr
    password: str
    recordar: bool = Field(False, description="Mantener sesión iniciada")
    codigo_2fa: Optional[str] = Field(None, description="Código 2FA si está activado")


class RefreshRequest(BaseModel):
    """Request para refresh token"""
    refresh_token: str = Field(..., description="Token de refresco")


class RecuperarPasswordRequest(BaseModel):
    """Request para recuperar contraseña"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request para resetear contraseña"""
    token: str = Field(..., description="Token de recuperación")
    nueva_password: str = Field(..., min_length=8)
    confirmar_password: str
    
    @validator('nueva_password')
    def validar_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v
    
    @validator('confirmar_password')
    def passwords_match(cls, v, values):
        if 'nueva_password' in values and v != values['nueva_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


class OAuthRequest(BaseModel):
    """Request para OAuth"""
    code: str = Field(..., description="Código de autorización OAuth")
    redirect_uri: str = Field(..., description="URI de redirección")
    state: Optional[str] = Field(None, description="State para CSRF")


class Activar2FARequest(BaseModel):
    """Request para activar 2FA"""
    metodo: str = Field("totp", regex="^(totp|sms|email)$")
    telefono: Optional[str] = Field(None, description="Teléfono para SMS")


class Verificar2FARequest(BaseModel):
    """Request para verificar 2FA"""
    codigo: str = Field(..., min_length=6, max_length=6)
    token_temporal: str = Field(..., description="Token temporal del setup")


class SesionResponse(BaseModel):
    """Response de sesión activa"""
    id: str
    dispositivo: str
    navegador: str
    ip: str
    ubicacion: Optional[str]
    ultimo_acceso: datetime
    es_actual: bool


class TokensResponse(BaseModel):
    """Response con tokens JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Segundos hasta expiración")
    scope: List[str] = Field(default_factory=list)


class UsuarioAutenticado(BaseModel):
    """Usuario autenticado actual"""
    id: str
    email: str
    nombre: str
    apellido: str
    empresa: Optional[str]
    rol: str
    permisos: List[str]
    email_verificado: bool
    tiene_2fa: bool
    ultimo_login: Optional[datetime]
    creado_en: datetime


class Setup2FAResponse(BaseModel):
    """Response del setup 2FA"""
    secret: str
    qr_code_url: str
    token_temporal: str
    backup_codes: List[str]


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _generar_token_verificacion() -> str:
    """Genera token seguro para verificación"""
    return secrets.token_urlsafe(32)


def _hash_password(password: str) -> str:
    """Hash de contraseña con salt"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def _verificar_password(password: str, hash_almacenado: str) -> bool:
    """Verifica contraseña contra hash"""
    try:
        salt, hash_esperado = hash_almacenado.split('$')
        hash_calculado = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_calculado.hex() == hash_esperado
    except:
        return False


async def _enviar_email_verificacion(email: str, token: str):
    """Envía email de verificación (mock)"""
    # TODO: Integrar con servicio de email real
    print(f"[EMAIL] Verificación enviada a {email} con token {token[:8]}...")


async def _enviar_email_recuperacion(email: str, token: str):
    """Envía email de recuperación (mock)"""
    print(f"[EMAIL] Recuperación enviada a {email} con token {token[:8]}...")


async def _registrar_sesion(user_id: str, request: Request, recordar: bool) -> dict:
    """Registra nueva sesión"""
    return {
        "id": secrets.token_hex(16),
        "user_id": user_id,
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "creado_en": datetime.utcnow(),
        "expira_en": datetime.utcnow() + timedelta(days=30 if recordar else 1)
    }


async def _generar_tokens(user_id: str, email: str, rol: str, permisos: List[str]) -> TokensResponse:
    """Genera par de tokens JWT"""
    # TODO: Usar librería JWT real (python-jose)
    access_token = secrets.token_urlsafe(64)
    refresh_token = secrets.token_urlsafe(64)
    
    return TokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,  # 1 hora
        scope=permisos
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UsuarioAutenticado:
    """Dependencia para obtener usuario actual"""
    # TODO: Decodificar JWT real
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    # Mock user para desarrollo
    if token:
        return UsuarioAutenticado(
            id="usr_demo_001",
            email="demo@datapolis.cl",
            nombre="Usuario",
            apellido="Demo",
            empresa="DATAPOLIS SpA",
            rol="admin",
            permisos=["read", "write", "admin"],
            email_verificado=True,
            tiene_2fa=False,
            ultimo_login=datetime.utcnow() - timedelta(hours=2),
            creado_en=datetime.utcnow() - timedelta(days=90)
        )
    
    raise credentials_exception


# =============================================================================
# ENDPOINTS DE REGISTRO Y LOGIN
# =============================================================================

@router.post(
    "/registro",
    response_model=ResponseWrapper[UsuarioAutenticado],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea una nueva cuenta de usuario. Envía email de verificación."
)
async def registrar_usuario(
    request: RegistroRequest,
    background_tasks: BackgroundTasks
):
    """
    Registro de nuevo usuario con validación completa.
    
    - Valida complejidad de contraseña
    - Verifica términos y condiciones aceptados
    - Envía email de verificación
    - Crea cuenta en estado pendiente
    """
    # Validar aceptación de términos
    if not request.acepta_terminos or not request.acepta_privacidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe aceptar los términos y condiciones y la política de privacidad"
        )
    
    # TODO: Verificar que email no existe en BD
    
    # Generar token de verificación
    token_verificacion = _generar_token_verificacion()
    
    # Hash de contraseña
    password_hash = _hash_password(request.password)
    
    # Crear usuario (mock)
    nuevo_usuario = UsuarioAutenticado(
        id=f"usr_{secrets.token_hex(8)}",
        email=request.email,
        nombre=request.nombre,
        apellido=request.apellido,
        empresa=request.empresa,
        rol="usuario",
        permisos=["read"],
        email_verificado=False,
        tiene_2fa=False,
        ultimo_login=None,
        creado_en=datetime.utcnow()
    )
    
    # Enviar email de verificación en background
    background_tasks.add_task(_enviar_email_verificacion, request.email, token_verificacion)
    
    return ResponseWrapper(
        success=True,
        data=nuevo_usuario,
        message="Usuario registrado. Por favor verifica tu email."
    )


@router.post(
    "/login",
    response_model=ResponseWrapper[TokensResponse],
    summary="Iniciar sesión",
    description="Autenticación con email/contraseña. Retorna tokens JWT."
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Autenticación de usuario.
    
    - Valida credenciales
    - Verifica 2FA si está activado
    - Genera tokens JWT
    - Registra sesión
    """
    # TODO: Buscar usuario en BD y verificar contraseña
    
    # Mock de validación
    if form_data.username != "demo@datapolis.cl" or form_data.password != "Demo123!":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Generar tokens
    tokens = await _generar_tokens(
        user_id="usr_demo_001",
        email=form_data.username,
        rol="admin",
        permisos=["read", "write", "admin"]
    )
    
    # Registrar sesión
    await _registrar_sesion("usr_demo_001", request, recordar=False)
    
    return ResponseWrapper(
        success=True,
        data=tokens,
        message="Sesión iniciada correctamente"
    )


@router.post(
    "/login/json",
    response_model=ResponseWrapper[TokensResponse],
    summary="Iniciar sesión (JSON)",
    description="Autenticación con body JSON en lugar de form-data."
)
async def login_json(
    request: Request,
    login_data: LoginRequest,
    background_tasks: BackgroundTasks
):
    """
    Login alternativo con JSON body.
    Soporta código 2FA y opción de recordar.
    """
    # TODO: Implementar lógica real
    
    # Mock
    if login_data.email != "demo@datapolis.cl":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )
    
    tokens = await _generar_tokens(
        user_id="usr_demo_001",
        email=login_data.email,
        rol="admin",
        permisos=["read", "write", "admin"]
    )
    
    return ResponseWrapper(
        success=True,
        data=tokens,
        message="Sesión iniciada correctamente"
    )


@router.post(
    "/refresh",
    response_model=ResponseWrapper[TokensResponse],
    summary="Renovar token",
    description="Obtiene nuevo access token usando refresh token."
)
async def refresh_token(request: RefreshRequest):
    """
    Renueva access token.
    
    - Valida refresh token
    - Genera nuevo par de tokens
    - Invalida refresh token anterior
    """
    # TODO: Validar refresh token en BD
    
    # Mock
    if len(request.refresh_token) < 32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )
    
    tokens = await _generar_tokens(
        user_id="usr_demo_001",
        email="demo@datapolis.cl",
        rol="admin",
        permisos=["read", "write", "admin"]
    )
    
    return ResponseWrapper(
        success=True,
        data=tokens,
        message="Token renovado"
    )


@router.post(
    "/logout",
    response_model=ResponseWrapper[dict],
    summary="Cerrar sesión",
    description="Invalida tokens y cierra sesión actual."
)
async def logout(
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Cierra sesión actual.
    
    - Invalida access token
    - Invalida refresh token
    - Registra logout
    """
    # TODO: Invalidar tokens en BD/cache
    
    return ResponseWrapper(
        success=True,
        data={"logged_out": True},
        message="Sesión cerrada correctamente"
    )


# =============================================================================
# ENDPOINTS DE RECUPERACIÓN DE CONTRASEÑA
# =============================================================================

@router.post(
    "/recuperar-password",
    response_model=ResponseWrapper[dict],
    summary="Solicitar recuperación de contraseña",
    description="Envía email con link de recuperación."
)
async def recuperar_password(
    request: RecuperarPasswordRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia proceso de recuperación de contraseña.
    
    Siempre retorna éxito para no revelar si el email existe.
    """
    # Generar token
    token = _generar_token_verificacion()
    
    # TODO: Guardar token en BD con expiración (1 hora)
    
    # Enviar email en background
    background_tasks.add_task(_enviar_email_recuperacion, request.email, token)
    
    return ResponseWrapper(
        success=True,
        data={"email_enviado": True},
        message="Si el email existe, recibirás instrucciones de recuperación"
    )


@router.post(
    "/reset-password",
    response_model=ResponseWrapper[dict],
    summary="Resetear contraseña",
    description="Cambia la contraseña usando token de recuperación."
)
async def reset_password(request: ResetPasswordRequest):
    """
    Completa el proceso de recuperación de contraseña.
    
    - Valida token de recuperación
    - Actualiza contraseña
    - Invalida token
    - Cierra todas las sesiones activas
    """
    # TODO: Validar token en BD
    
    if len(request.token) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    # Hash nueva contraseña
    password_hash = _hash_password(request.nueva_password)
    
    # TODO: Actualizar en BD
    
    return ResponseWrapper(
        success=True,
        data={"password_actualizado": True},
        message="Contraseña actualizada. Por favor inicia sesión."
    )


# =============================================================================
# ENDPOINTS DE VERIFICACIÓN DE EMAIL
# =============================================================================

@router.get(
    "/verificar-email/{token}",
    response_model=ResponseWrapper[dict],
    summary="Verificar email",
    description="Confirma el email del usuario mediante token."
)
async def verificar_email(token: str):
    """
    Verifica email del usuario.
    
    - Valida token de verificación
    - Marca email como verificado
    - Invalida token
    """
    # TODO: Validar token en BD
    
    if len(token) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado"
        )
    
    return ResponseWrapper(
        success=True,
        data={"email_verificado": True},
        message="Email verificado correctamente"
    )


@router.post(
    "/reenviar-verificacion",
    response_model=ResponseWrapper[dict],
    summary="Reenviar email de verificación",
    description="Envía nuevo email de verificación."
)
async def reenviar_verificacion(
    current_user: UsuarioAutenticado = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Reenvía email de verificación.
    
    Requiere estar autenticado pero con email no verificado.
    """
    if current_user.email_verificado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está verificado"
        )
    
    token = _generar_token_verificacion()
    
    if background_tasks:
        background_tasks.add_task(_enviar_email_verificacion, current_user.email, token)
    
    return ResponseWrapper(
        success=True,
        data={"email_enviado": True},
        message="Email de verificación reenviado"
    )


# =============================================================================
# ENDPOINTS OAUTH2
# =============================================================================

@router.post(
    "/oauth/{provider}",
    response_model=ResponseWrapper[TokensResponse],
    summary="Autenticación OAuth2",
    description="Login/registro mediante proveedor OAuth2 (Google, Microsoft, GitHub)."
)
async def oauth_login(
    provider: ProveedorOAuth,
    request: Request,
    oauth_data: OAuthRequest
):
    """
    Autenticación mediante OAuth2.
    
    - Intercambia código por tokens del proveedor
    - Obtiene información del usuario
    - Crea cuenta si no existe
    - Genera tokens JWT propios
    """
    # TODO: Implementar flujo OAuth2 real
    
    # Mock response
    tokens = await _generar_tokens(
        user_id="usr_oauth_001",
        email=f"oauth_user@{provider.value}.com",
        rol="usuario",
        permisos=["read", "write"]
    )
    
    return ResponseWrapper(
        success=True,
        data=tokens,
        message=f"Autenticado con {provider.value}"
    )


@router.get(
    "/oauth/{provider}/url",
    response_model=ResponseWrapper[dict],
    summary="Obtener URL de OAuth",
    description="Retorna URL para iniciar flujo OAuth2."
)
async def get_oauth_url(
    provider: ProveedorOAuth,
    redirect_uri: str
):
    """
    Genera URL de autorización OAuth2.
    
    El frontend debe redirigir al usuario a esta URL.
    """
    state = secrets.token_urlsafe(16)
    
    # URLs mock - TODO: usar configuración real
    oauth_urls = {
        ProveedorOAuth.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
        ProveedorOAuth.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        ProveedorOAuth.GITHUB: "https://github.com/login/oauth/authorize"
    }
    
    base_url = oauth_urls.get(provider, "")
    
    return ResponseWrapper(
        success=True,
        data={
            "url": f"{base_url}?redirect_uri={redirect_uri}&state={state}",
            "state": state,
            "provider": provider.value
        },
        message="URL de autorización generada"
    )


# =============================================================================
# ENDPOINTS DE SESIONES
# =============================================================================

@router.get(
    "/sesiones",
    response_model=ResponseWrapper[List[SesionResponse]],
    summary="Listar sesiones activas",
    description="Retorna todas las sesiones activas del usuario."
)
async def listar_sesiones(
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Lista todas las sesiones activas del usuario.
    
    Incluye información de dispositivo, ubicación y último acceso.
    """
    # Mock de sesiones
    sesiones = [
        SesionResponse(
            id="ses_001",
            dispositivo="Desktop",
            navegador="Chrome 120",
            ip="192.168.1.100",
            ubicacion="Santiago, Chile",
            ultimo_acceso=datetime.utcnow() - timedelta(minutes=5),
            es_actual=True
        ),
        SesionResponse(
            id="ses_002",
            dispositivo="Mobile",
            navegador="Safari iOS 17",
            ip="192.168.1.101",
            ubicacion="Santiago, Chile",
            ultimo_acceso=datetime.utcnow() - timedelta(hours=2),
            es_actual=False
        )
    ]
    
    return ResponseWrapper(
        success=True,
        data=sesiones,
        message=f"{len(sesiones)} sesiones activas"
    )


@router.delete(
    "/sesiones/{session_id}",
    response_model=ResponseWrapper[dict],
    summary="Cerrar sesión específica",
    description="Cierra una sesión activa por su ID."
)
async def cerrar_sesion(
    session_id: str,
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Cierra una sesión específica.
    
    No permite cerrar la sesión actual (usar /logout).
    """
    # TODO: Verificar que la sesión pertenece al usuario
    
    if session_id == "ses_001":  # Mock: sesión actual
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes cerrar la sesión actual. Usa /logout."
        )
    
    return ResponseWrapper(
        success=True,
        data={"sesion_cerrada": session_id},
        message="Sesión cerrada correctamente"
    )


@router.delete(
    "/sesiones",
    response_model=ResponseWrapper[dict],
    summary="Cerrar todas las sesiones",
    description="Cierra todas las sesiones excepto la actual."
)
async def cerrar_todas_sesiones(
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Cierra todas las sesiones excepto la actual.
    
    Útil si se sospecha acceso no autorizado.
    """
    # TODO: Invalidar todas las sesiones excepto actual
    
    return ResponseWrapper(
        success=True,
        data={"sesiones_cerradas": 3},
        message="Todas las otras sesiones han sido cerradas"
    )


# =============================================================================
# ENDPOINTS DE 2FA
# =============================================================================

@router.post(
    "/2fa/activar",
    response_model=ResponseWrapper[Setup2FAResponse],
    summary="Activar 2FA",
    description="Inicia proceso de activación de autenticación de dos factores."
)
async def activar_2fa(
    request: Activar2FARequest,
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Activa autenticación de dos factores.
    
    Retorna:
    - Secret para TOTP
    - QR code para apps como Google Authenticator
    - Códigos de respaldo
    - Token temporal para verificación
    """
    if current_user.tiene_2fa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA ya está activado"
        )
    
    # Generar secret TOTP
    secret = secrets.token_hex(20)
    
    # Generar códigos de respaldo
    backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    
    # Token temporal para completar setup
    token_temporal = secrets.token_urlsafe(32)
    
    # URL para QR (formato otpauth)
    qr_url = f"otpauth://totp/DATAPOLIS:{current_user.email}?secret={secret}&issuer=DATAPOLIS"
    
    return ResponseWrapper(
        success=True,
        data=Setup2FAResponse(
            secret=secret,
            qr_code_url=qr_url,
            token_temporal=token_temporal,
            backup_codes=backup_codes
        ),
        message="Escanea el QR con tu app de autenticación y verifica el código"
    )


@router.post(
    "/2fa/verificar",
    response_model=ResponseWrapper[dict],
    summary="Verificar y completar activación 2FA",
    description="Verifica el código TOTP para completar activación de 2FA."
)
async def verificar_2fa(
    request: Verificar2FARequest,
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Completa la activación de 2FA verificando un código.
    
    - Valida el código TOTP
    - Activa 2FA en la cuenta
    - Guarda códigos de respaldo cifrados
    """
    # TODO: Validar código TOTP real
    
    if len(request.codigo) != 6 or not request.codigo.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido. Debe ser de 6 dígitos."
        )
    
    return ResponseWrapper(
        success=True,
        data={
            "2fa_activado": True,
            "metodo": "totp"
        },
        message="Autenticación de dos factores activada correctamente"
    )


@router.post(
    "/2fa/desactivar",
    response_model=ResponseWrapper[dict],
    summary="Desactivar 2FA",
    description="Desactiva autenticación de dos factores."
)
async def desactivar_2fa(
    codigo: str,
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Desactiva 2FA.
    
    Requiere código válido o código de respaldo.
    """
    if not current_user.tiene_2fa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA no está activado"
        )
    
    # TODO: Validar código
    
    return ResponseWrapper(
        success=True,
        data={"2fa_desactivado": True},
        message="Autenticación de dos factores desactivada"
    )


@router.get(
    "/2fa/backup-codes",
    response_model=ResponseWrapper[List[str]],
    summary="Obtener códigos de respaldo",
    description="Genera nuevos códigos de respaldo (invalida los anteriores)."
)
async def regenerar_backup_codes(
    codigo_2fa: str,
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Regenera códigos de respaldo.
    
    - Invalida códigos anteriores
    - Genera 10 nuevos códigos
    - Requiere código 2FA válido
    """
    if not current_user.tiene_2fa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA no está activado"
        )
    
    # TODO: Validar código 2FA
    
    nuevos_codigos = [secrets.token_hex(4).upper() for _ in range(10)]
    
    return ResponseWrapper(
        success=True,
        data=nuevos_codigos,
        message="Nuevos códigos de respaldo generados. Guárdalos en un lugar seguro."
    )


# =============================================================================
# ENDPOINT DE USUARIO ACTUAL
# =============================================================================

@router.get(
    "/me",
    response_model=ResponseWrapper[UsuarioAutenticado],
    summary="Obtener usuario actual",
    description="Retorna información del usuario autenticado."
)
async def get_me(
    current_user: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Obtiene información del usuario autenticado actual.
    
    Incluye: perfil, rol, permisos, estado de verificación.
    """
    return ResponseWrapper(
        success=True,
        data=current_user,
        message="Usuario autenticado"
    )


# =============================================================================
# ENDPOINT DE SALUD
# =============================================================================

@router.get(
    "/health",
    response_model=dict,
    summary="Health check del módulo de autenticación",
    include_in_schema=False
)
async def health_check():
    """Health check del servicio de autenticación."""
    return {
        "status": "healthy",
        "service": "auth",
        "timestamp": datetime.utcnow().isoformat()
    }
