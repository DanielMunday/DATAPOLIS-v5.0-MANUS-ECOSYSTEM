# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Base
=============================
Modelos Pydantic base para validación y serialización
Versión: 3.0.0
Autor: Daniel (DATAPOLIS SpA)
Fecha: 2026-02-01

Compliance:
- Ley 21.719 (Protección Datos Personales)
- ISO 8601 (Fechas)
- RFC 7946 (GeoJSON)
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    EmailStr,
    HttpUrl,
)


# =============================================================================
# CONFIGURACIÓN BASE
# =============================================================================

class BaseSchema(BaseModel):
    """Schema base con configuración común"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v),
        }
    )


class TimestampMixin(BaseModel):
    """Mixin para timestamps automáticos"""
    created_at: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")


class AuditMixin(BaseModel):
    """Mixin para auditoría completa"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = Field(None, description="Usuario que creó el registro")
    updated_by: Optional[str] = Field(None, description="Usuario que actualizó")
    version: int = Field(default=1, description="Versión del registro")


# =============================================================================
# ENUMERACIONES COMUNES
# =============================================================================

class TipoDocumento(str, Enum):
    """Tipos de documento de identidad Chile"""
    RUT = "rut"
    PASAPORTE = "pasaporte"
    DNI_EXTRANJERO = "dni_extranjero"


class TipoPersona(str, Enum):
    """Tipo de persona legal"""
    NATURAL = "natural"
    JURIDICA = "juridica"


class Region(str, Enum):
    """Regiones de Chile con códigos oficiales"""
    ARICA = "XV"
    TARAPACA = "I"
    ANTOFAGASTA = "II"
    ATACAMA = "III"
    COQUIMBO = "IV"
    VALPARAISO = "V"
    METROPOLITANA = "RM"
    OHIGGINS = "VI"
    MAULE = "VII"
    NUBLE = "XVI"
    BIOBIO = "VIII"
    ARAUCANIA = "IX"
    LOS_RIOS = "XIV"
    LOS_LAGOS = "X"
    AYSEN = "XI"
    MAGALLANES = "XII"


class TipoPropiedad(str, Enum):
    """Tipos de propiedad inmobiliaria"""
    CASA = "casa"
    DEPARTAMENTO = "departamento"
    OFICINA = "oficina"
    LOCAL_COMERCIAL = "local_comercial"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"
    TERRENO = "terreno"
    PARCELA = "parcela"
    INDUSTRIAL = "industrial"
    AGRICOLA = "agricola"
    MIXTO = "mixto"


class EstadoPropiedad(str, Enum):
    """Estado de conservación de propiedad"""
    EXCELENTE = "excelente"
    BUENO = "bueno"
    REGULAR = "regular"
    MALO = "malo"
    EN_CONSTRUCCION = "en_construccion"
    DEMOLICION = "demolicion"


class Moneda(str, Enum):
    """Monedas soportadas"""
    CLP = "CLP"
    UF = "UF"
    USD = "USD"
    EUR = "EUR"
    UTM = "UTM"


class NivelRiesgo(str, Enum):
    """Niveles de riesgo estandarizados"""
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"
    
    
class EstadoProceso(str, Enum):
    """Estados de proceso/workflow"""
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    ERROR = "error"
    CANCELADO = "cancelado"
    REQUIERE_VALIDACION = "requiere_validacion"


# =============================================================================
# SCHEMAS DE RESPUESTA ESTÁNDAR
# =============================================================================

DataT = TypeVar("DataT")


class ResponseBase(BaseSchema, Generic[DataT]):
    """Respuesta API estándar"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[DataT] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    processing_time_ms: Optional[float] = None


class PaginatedResponse(BaseSchema, Generic[DataT]):
    """Respuesta paginada"""
    success: bool = True
    data: List[DataT] = []
    
    # Paginación
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, le=100, default=20)
    total_items: int = Field(ge=0, default=0)
    total_pages: int = Field(ge=0, default=0)
    has_next: bool = False
    has_prev: bool = False
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseSchema):
    """Respuesta de error estándar"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    # Para debugging (solo en desarrollo)
    traceback: Optional[str] = None


# =============================================================================
# SCHEMAS GEOESPACIALES (RFC 7946 GeoJSON)
# =============================================================================

class GeoPoint(BaseSchema):
    """Punto geográfico WGS84"""
    type: str = "Point"
    coordinates: tuple[float, float] = Field(
        ...,
        description="[longitud, latitud] en WGS84"
    )
    
    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        lon, lat = v
        if not -180 <= lon <= 180:
            raise ValueError(f"Longitud fuera de rango: {lon}")
        if not -90 <= lat <= 90:
            raise ValueError(f"Latitud fuera de rango: {lat}")
        return v


class GeoPolygon(BaseSchema):
    """Polígono geográfico"""
    type: str = "Polygon"
    coordinates: List[List[tuple[float, float]]] = Field(
        ...,
        description="Lista de anillos [exterior, ...huecos]"
    )


class GeoBoundingBox(BaseSchema):
    """Bounding box geográfico"""
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    
    @model_validator(mode="after")
    def validate_bbox(self):
        if self.min_lon > self.max_lon:
            raise ValueError("min_lon debe ser menor que max_lon")
        if self.min_lat > self.max_lat:
            raise ValueError("min_lat debe ser menor que max_lat")
        return self


class Direccion(BaseSchema):
    """Dirección postal chilena estandarizada"""
    calle: str = Field(..., min_length=1, max_length=200)
    numero: Optional[str] = Field(None, max_length=20)
    departamento: Optional[str] = Field(None, max_length=20)
    piso: Optional[int] = Field(None, ge=0, le=200)
    
    comuna: str = Field(..., min_length=1, max_length=100)
    region: Region
    codigo_postal: Optional[str] = Field(None, pattern=r"^\d{7}$")
    
    # Geocodificación
    ubicacion: Optional[GeoPoint] = None
    
    # Metadata
    direccion_completa: Optional[str] = None
    
    @model_validator(mode="after")
    def build_direccion_completa(self):
        partes = [self.calle]
        if self.numero:
            partes.append(self.numero)
        if self.departamento:
            partes.append(f"Depto. {self.departamento}")
        partes.extend([self.comuna, self.region.value])
        self.direccion_completa = ", ".join(partes)
        return self


# =============================================================================
# SCHEMAS DE IDENTIFICACIÓN
# =============================================================================

class RUTChileno(BaseSchema):
    """RUT chileno con validación"""
    numero: str = Field(..., pattern=r"^\d{1,8}$")
    dv: str = Field(..., pattern=r"^[0-9Kk]$")
    
    @property
    def formatted(self) -> str:
        """RUT formateado: XX.XXX.XXX-X"""
        num = self.numero.zfill(8)
        return f"{num[:-6]}.{num[-6:-3]}.{num[-3:]}-{self.dv.upper()}"
    
    @property
    def raw(self) -> str:
        """RUT sin formato: XXXXXXXX-X"""
        return f"{self.numero}-{self.dv.upper()}"
    
    @model_validator(mode="after")
    def validate_dv(self):
        """Validar dígito verificador"""
        suma = 0
        multiplo = 2
        for d in reversed(self.numero):
            suma += int(d) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2
        resto = suma % 11
        dv_calculado = "0" if resto == 0 else "K" if resto == 1 else str(11 - resto)
        if self.dv.upper() != dv_calculado:
            raise ValueError(f"DV inválido: esperado {dv_calculado}, recibido {self.dv}")
        return self


class ROLPropiedad(BaseSchema):
    """ROL de propiedad SII"""
    comuna_code: str = Field(..., pattern=r"^\d{5}$", description="Código comuna SII")
    manzana: str = Field(..., pattern=r"^\d{1,5}$")
    predio: str = Field(..., pattern=r"^\d{1,4}$")
    
    @property
    def formatted(self) -> str:
        """ROL formateado: XXXXX-XXXXX-XXXX"""
        return f"{self.comuna_code}-{self.manzana.zfill(5)}-{self.predio.zfill(4)}"


class InscripcionCBR(BaseSchema):
    """Inscripción en Conservador de Bienes Raíces"""
    conservador: str = Field(..., description="Nombre del CBR")
    foja: int = Field(..., ge=1)
    numero: int = Field(..., ge=1)
    año: int = Field(..., ge=1900, le=2100)
    registro: str = Field(default="propiedad", description="Tipo de registro")
    
    @property
    def formatted(self) -> str:
        return f"Foja {self.foja} N° {self.numero} del año {self.año}"


# =============================================================================
# SCHEMAS FINANCIEROS
# =============================================================================

class MontoMoneda(BaseSchema):
    """Monto con moneda"""
    valor: Decimal = Field(..., description="Valor numérico")
    moneda: Moneda = Field(default=Moneda.CLP)
    
    # Conversiones (se llenan automáticamente)
    valor_clp: Optional[Decimal] = Field(None, description="Equivalente en CLP")
    valor_uf: Optional[Decimal] = Field(None, description="Equivalente en UF")
    fecha_conversion: Optional[date] = Field(None, description="Fecha tipo de cambio")


class RangoValor(BaseSchema):
    """Rango de valores"""
    minimo: Decimal
    maximo: Decimal
    moneda: Moneda = Moneda.CLP
    
    @model_validator(mode="after")
    def validate_rango(self):
        if self.minimo > self.maximo:
            raise ValueError("mínimo debe ser menor o igual a máximo")
        return self


class IndicadorEconomico(BaseSchema):
    """Valor de indicador económico"""
    codigo: str = Field(..., description="Código indicador (uf, dolar, euro, ipc, etc.)")
    nombre: str
    valor: Decimal
    unidad: str
    fecha: date
    variacion_diaria: Optional[Decimal] = None
    variacion_mensual: Optional[Decimal] = None
    variacion_anual: Optional[Decimal] = None
    fuente: str = Field(default="BCCh")


# =============================================================================
# SCHEMAS DE ARCHIVOS Y DOCUMENTOS
# =============================================================================

class ArchivoBase(BaseSchema):
    """Metadata de archivo"""
    nombre: str = Field(..., max_length=255)
    extension: str = Field(..., max_length=10)
    mime_type: str
    tamaño_bytes: int = Field(..., ge=0)
    hash_sha256: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")


class DocumentoAdjunto(ArchivoBase):
    """Documento adjunto con metadata"""
    id: UUID
    tipo_documento: str = Field(..., description="Tipo: escritura, plano, certificado, etc.")
    descripcion: Optional[str] = None
    fecha_documento: Optional[date] = None
    url_descarga: Optional[HttpUrl] = None
    
    # Verificación
    verificado: bool = False
    fecha_verificacion: Optional[datetime] = None
    verificado_por: Optional[str] = None


# =============================================================================
# SCHEMAS DE USUARIO Y PERMISOS
# =============================================================================

class UsuarioBase(BaseSchema):
    """Usuario básico"""
    id: UUID
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    rut: Optional[RUTChileno] = None
    tipo_persona: TipoPersona = TipoPersona.NATURAL
    activo: bool = True


class PermisoRecurso(BaseSchema):
    """Permiso sobre recurso"""
    recurso: str = Field(..., description="Tipo de recurso")
    recurso_id: Optional[UUID] = None
    accion: str = Field(..., description="create, read, update, delete, admin")
    otorgado_por: UUID
    fecha_otorgamiento: datetime
    fecha_expiracion: Optional[datetime] = None


# =============================================================================
# SCHEMAS DE FILTROS Y BÚSQUEDA
# =============================================================================

class FiltroBase(BaseSchema):
    """Filtro base para consultas"""
    # Paginación
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    # Ordenamiento
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern=r"^(asc|desc)$")
    
    # Fechas
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class FiltroPropiedades(FiltroBase):
    """Filtro para búsqueda de propiedades"""
    # Ubicación
    region: Optional[Region] = None
    comunas: Optional[List[str]] = None
    bbox: Optional[GeoBoundingBox] = None
    radio_km: Optional[float] = Field(None, ge=0.1, le=50)
    punto_central: Optional[GeoPoint] = None
    
    # Tipo
    tipos: Optional[List[TipoPropiedad]] = None
    estados: Optional[List[EstadoPropiedad]] = None
    
    # Características
    superficie_min: Optional[float] = Field(None, ge=0)
    superficie_max: Optional[float] = Field(None, ge=0)
    dormitorios_min: Optional[int] = Field(None, ge=0)
    dormitorios_max: Optional[int] = Field(None, ge=0)
    baños_min: Optional[int] = Field(None, ge=0)
    estacionamientos_min: Optional[int] = Field(None, ge=0)
    
    # Precio
    precio_min: Optional[Decimal] = Field(None, ge=0)
    precio_max: Optional[Decimal] = Field(None, ge=0)
    moneda_precio: Moneda = Moneda.UF
    
    # Texto
    texto_busqueda: Optional[str] = Field(None, max_length=200)


# =============================================================================
# SCHEMAS DE VALIDACIÓN HUMANA (HITL)
# =============================================================================

class ValidacionHumana(BaseSchema):
    """Registro de validación humana"""
    id: UUID
    tipo_validacion: str = Field(..., description="Tipo de check validado")
    recurso_tipo: str = Field(..., description="Tipo de recurso validado")
    recurso_id: UUID
    
    # Resultado
    estado_anterior: str
    estado_validado: str
    aprobado: bool
    observaciones: Optional[str] = None
    
    # Auditoría
    validador_id: UUID
    validador_nombre: str
    validador_rol: str = Field(..., description="Rol: abogado, ingeniero, tasador, etc.")
    fecha_validacion: datetime
    
    # Documentación
    documentos_soporte: Optional[List[UUID]] = None


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Base
    "BaseSchema",
    "TimestampMixin",
    "AuditMixin",
    
    # Enums
    "TipoDocumento",
    "TipoPersona",
    "Region",
    "TipoPropiedad",
    "EstadoPropiedad",
    "Moneda",
    "NivelRiesgo",
    "EstadoProceso",
    
    # Responses
    "ResponseBase",
    "PaginatedResponse",
    "ErrorResponse",
    
    # Geo
    "GeoPoint",
    "GeoPolygon",
    "GeoBoundingBox",
    "Direccion",
    
    # Identificación
    "RUTChileno",
    "ROLPropiedad",
    "InscripcionCBR",
    
    # Financiero
    "MontoMoneda",
    "RangoValor",
    "IndicadorEconomico",
    
    # Archivos
    "ArchivoBase",
    "DocumentoAdjunto",
    
    # Usuario
    "UsuarioBase",
    "PermisoRecurso",
    
    # Filtros
    "FiltroBase",
    "FiltroPropiedades",
    
    # HITL
    "ValidacionHumana",
]
