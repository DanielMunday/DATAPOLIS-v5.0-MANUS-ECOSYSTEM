# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Auth
=============================
Modelos Pydantic para autenticación y autorización
Compliance: Ley 21.719 (Protección Datos)
Versión: 3.0.0
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from .base import BaseSchema, ResponseBase, RUTChileno, TipoPersona


# =============================================================================
# ENUMERACIONES
# =============================================================================

class RolUsuario(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "admin"
    TASADOR = "tasador"
    ANALISTA = "analista"
    ABOGADO = "abogado"
    CONTADOR = "contador"
    ADMINISTRADOR_EDIFICIO = "administrador_edificio"
    PROPIETARIO = "propietario"
    COPROPIETARIO = "copropietario"
    ARRENDATARIO = "arrendatario"
    INVERSIONISTA = "inversionista"
    VIEWER = "viewer"


class TipoToken(str, Enum):
    """Tipos de token"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class EstadoUsuario(str, Enum):
    """Estado de la cuenta"""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    PENDIENTE_VERIFICACION = "pendiente_verificacion"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class LoginRequest(BaseSchema):
    """Request de login"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    remember_me: bool = False
    device_info: Optional[str] = None


class RegisterRequest(BaseSchema):
    """Request de registro"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str
    
    # Datos personales
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    rut: Optional[RUTChileno] = None
    tipo_persona: TipoPersona = TipoPersona.NATURAL
    
    # Contacto
    telefono: Optional[str] = Field(None, pattern=r"^\+?56?\d{9}$")
    
    # Aceptación
    acepta_terminos: bool
    acepta_privacidad: bool
    
    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("password") and v != info.data["password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v
    
    @field_validator("acepta_terminos", "acepta_privacidad")
    @classmethod
    def must_accept(cls, v):
        if not v:
            raise ValueError("Debe aceptar los términos y condiciones")
        return v


class RefreshTokenRequest(BaseSchema):
    """Request para refresh token"""
    refresh_token: str


class ChangePasswordRequest(BaseSchema):
    """Request para cambio de contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str
    
    @field_validator("new_password_confirm")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v


class ForgotPasswordRequest(BaseSchema):
    """Request para recuperar contraseña"""
    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    """Request para resetear contraseña"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str


class APIKeyRequest(BaseSchema):
    """Request para crear API Key"""
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    permisos: List[str] = Field(default=["read"])
    expira_dias: Optional[int] = Field(None, ge=1, le=365)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class TokenData(BaseSchema):
    """Datos de token"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Segundos hasta expiración")
    expires_at: datetime


class UsuarioAuth(BaseSchema):
    """Usuario autenticado"""
    id: UUID
    email: EmailStr
    nombre: str
    apellido: str
    nombre_completo: str
    
    rut: Optional[str] = None
    tipo_persona: TipoPersona
    
    roles: List[RolUsuario]
    permisos: List[str]
    
    estado: EstadoUsuario
    email_verificado: bool
    
    ultimo_login: Optional[datetime] = None
    created_at: datetime


class LoginResponse(BaseSchema):
    """Respuesta de login exitoso"""
    token: TokenData
    usuario: UsuarioAuth
    requiere_2fa: bool = False


class APIKeyData(BaseSchema):
    """Datos de API Key"""
    id: UUID
    nombre: str
    key_prefix: str = Field(..., description="Primeros caracteres de la key")
    permisos: List[str]
    
    creada_at: datetime
    expira_at: Optional[datetime] = None
    ultimo_uso: Optional[datetime] = None
    
    activa: bool = True


class APIKeyCreatedResponse(BaseSchema):
    """Respuesta al crear API Key (única vez que se muestra completa)"""
    api_key: str = Field(..., description="API Key completa - guardar de forma segura")
    data: APIKeyData


class SessionInfo(BaseSchema):
    """Información de sesión activa"""
    id: UUID
    device_info: Optional[str] = None
    ip_address: str
    created_at: datetime
    last_activity: datetime
    is_current: bool = False


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

class AuthResponse(ResponseBase[LoginResponse]):
    """Respuesta de autenticación"""
    pass


class UsuarioResponse(ResponseBase[UsuarioAuth]):
    """Respuesta con datos de usuario"""
    pass


class TokenResponse(ResponseBase[TokenData]):
    """Respuesta de token"""
    pass


class APIKeyResponse(ResponseBase[APIKeyCreatedResponse]):
    """Respuesta de API Key creada"""
    pass


class APIKeysListResponse(ResponseBase[List[APIKeyData]]):
    """Respuesta lista de API Keys"""
    pass


class SessionsListResponse(ResponseBase[List[SessionInfo]]):
    """Respuesta lista de sesiones"""
    pass


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "RolUsuario",
    "TipoToken",
    "EstadoUsuario",
    
    # Requests
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "APIKeyRequest",
    
    # Data schemas
    "TokenData",
    "UsuarioAuth",
    "LoginResponse",
    "APIKeyData",
    "APIKeyCreatedResponse",
    "SessionInfo",
    
    # Responses
    "AuthResponse",
    "UsuarioResponse",
    "TokenResponse",
    "APIKeyResponse",
    "APIKeysListResponse",
    "SessionsListResponse",
]
