"""
DATAPOLIS v3.0 - Base de Datos
Configuración PostgreSQL/PostGIS/TimescaleDB con SQLAlchemy Async
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, Text, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Numeric,
    Enum as SQLEnum, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from geoalchemy2 import Geometry
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from enum import Enum
import uuid

from .config import settings


# =====================================================
# ENGINE Y SESSION
# =====================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Dependency injection para obtener sesión de BD"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =====================================================
# BASE DECLARATIVA
# =====================================================

class Base(DeclarativeBase):
    """Base para todos los modelos"""
    pass


class TimestampMixin:
    """Mixin para campos de auditoría temporal"""
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditMixin(TimestampMixin):
    """Mixin extendido con auditoría de usuario"""
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)


# =====================================================
# ENUMS
# =====================================================

class TipoPropiedad(str, Enum):
    DEPARTAMENTO = "departamento"
    CASA = "casa"
    OFICINA = "oficina"
    LOCAL_COMERCIAL = "local_comercial"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"
    TERRENO = "terreno"
    PARCELA = "parcela"
    INDUSTRIAL = "industrial"


class EstadoPropiedad(str, Enum):
    DISPONIBLE = "disponible"
    ARRENDADA = "arrendada"
    EN_VENTA = "en_venta"
    VENDIDA = "vendida"
    EN_PROCESO = "en_proceso"


class TipoDocumento(str, Enum):
    ESCRITURA = "escritura"
    PLANO = "plano"
    PERMISO_EDIFICACION = "permiso_edificacion"
    RECEPCION_FINAL = "recepcion_final"
    CERTIFICADO_DOMINIO = "certificado_dominio"
    HIPOTECA = "hipoteca"
    PROHIBICION = "prohibicion"
    CONTRIBUCIONES = "contribuciones"
    TASACION = "tasacion"
    CONTRATO_ARRIENDO = "contrato_arriendo"
    OTRO = "otro"


class NivelRiesgo(str, Enum):
    MUY_BAJO = "muy_bajo"
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    MUY_ALTO = "muy_alto"
    CRITICO = "critico"


class EstadoDueDiligence(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    OBSERVACIONES = "observaciones"


class MetodoValorizacion(str, Enum):
    COMPARACION = "comparacion"
    COSTO = "costo"
    INGRESO_DCF = "ingreso_dcf"
    RESIDUAL = "residual"
    HEDONIC = "hedonic"
    ML_ENSEMBLE = "ml_ensemble"


# =====================================================
# MODELOS - CORE
# =====================================================

class Usuario(Base, TimestampMixin):
    """Usuarios del sistema"""
    __tablename__ = "usuarios"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    rut: Mapped[Optional[str]] = mapped_column(String(12), unique=True, nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Rol y permisos
    rol: Mapped[str] = mapped_column(String(50), default="usuario")
    permisos: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # OAuth
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    microsoft_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    
    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # Relaciones
    propiedades = relationship("Propiedad", back_populates="propietario")
    expedientes = relationship("Expediente", back_populates="responsable")


class Organizacion(Base, TimestampMixin):
    """Organizaciones/Empresas"""
    __tablename__ = "organizaciones"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_fantasia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    giro: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    comuna: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Tipo de organización
    tipo: Mapped[str] = mapped_column(String(50), default="empresa")  # empresa, condominio, holding, etc.
    
    # Configuración
    config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)


# =====================================================
# IE - INDICADORES ECONÓMICOS (TimescaleDB)
# =====================================================

class IndicadorEconomico(Base):
    """Serie temporal de indicadores económicos - Hypertable TimescaleDB"""
    __tablename__ = "indicadores_economicos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    codigo_serie: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    
    # Metadatos
    fuente: Mapped[str] = mapped_column(String(50), default="BCCH")  # BCCH, SII, CMF
    unidad: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    variacion_diaria: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variacion_mensual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variacion_anual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_indicador_fecha_codigo', 'fecha', 'codigo_serie'),
    )


class PrediccionIndicador(Base, TimestampMixin):
    """Predicciones ARIMA/SARIMA de indicadores"""
    __tablename__ = "predicciones_indicadores"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_serie: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fecha_prediccion: Mapped[date] = mapped_column(Date, nullable=False)
    horizonte_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    
    valor_predicho: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    intervalo_confianza_inferior: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    intervalo_confianza_superior: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    
    # Métricas del modelo
    modelo: Mapped[str] = mapped_column(String(50), default="SARIMA")
    mape: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parametros_modelo: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# =====================================================
# MS - MERCADO SUELO
# =====================================================

class TransaccionSuelo(Base, TimestampMixin):
    """Transacciones de compraventa de terrenos"""
    __tablename__ = "transacciones_suelo"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Ubicación geográfica
    comuna: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    geometria: Mapped[Any] = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    
    # Datos de la transacción
    fecha_transaccion: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    precio_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    superficie_m2: Mapped[float] = mapped_column(Float, nullable=False)
    precio_uf_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Características del terreno
    uso_suelo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    coeficiente_constructibilidad: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coeficiente_ocupacion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altura_maxima: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    densidad_habitantes_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Fuente
    fuente: Mapped[str] = mapped_column(String(50), default="CBR")
    numero_inscripcion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class PrecioSueloPrediccion(Base, TimestampMixin):
    """Predicciones de precio de suelo por zona"""
    __tablename__ = "precios_suelo_prediccion"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comuna: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    zona: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geometria_zona: Mapped[Any] = mapped_column(Geometry('POLYGON', srid=4326), nullable=True)
    
    fecha_prediccion: Mapped[date] = mapped_column(Date, nullable=False)
    precio_uf_m2_actual: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    precio_uf_m2_6m: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    precio_uf_m2_12m: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    variacion_6m_pct: Mapped[float] = mapped_column(Float, nullable=False)
    variacion_12m_pct: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Confianza del modelo
    confianza: Mapped[float] = mapped_column(Float, nullable=False)
    modelo_usado: Mapped[str] = mapped_column(String(50), default="XGBoost")
    features_importantes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# =====================================================
# M00 - EXPEDIENTE UNIVERSAL
# =====================================================

class Expediente(Base, AuditMixin):
    """Expediente digital único por propiedad"""
    __tablename__ = "expedientes"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Relación con propiedad
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Estado
    estado: Mapped[str] = mapped_column(String(50), default="activo")
    completitud_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Metadatos
    fecha_apertura: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_cierre: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Hash blockchain para inmutabilidad
    blockchain_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    
    # Relaciones
    propiedad = relationship("Propiedad", back_populates="expediente")
    documentos = relationship("DocumentoExpediente", back_populates="expediente")
    responsable = relationship("Usuario", back_populates="expedientes")


class DocumentoExpediente(Base, TimestampMixin):
    """Documentos dentro de un expediente"""
    __tablename__ = "documentos_expediente"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expediente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("expedientes.id"), nullable=False)
    
    # Tipo y descripción
    tipo: Mapped[TipoDocumento] = mapped_column(SQLEnum(TipoDocumento), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Archivo
    archivo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    archivo_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Metadatos extraídos por IA
    contenido_extraido: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadatos_ia: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Validación
    is_validado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_validacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validado_por: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Relaciones
    expediente = relationship("Expediente", back_populates="documentos")


# =====================================================
# M01 - FICHA DE PROPIEDAD
# =====================================================

class Propiedad(Base, AuditMixin):
    """Ficha maestra de propiedad inmobiliaria"""
    __tablename__ = "propiedades"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identificación
    rol_sii: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    rol_cbr: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    comuna: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Geolocalización
    geometria: Mapped[Any] = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    latitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitud: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Tipo y estado
    tipo: Mapped[TipoPropiedad] = mapped_column(SQLEnum(TipoPropiedad), nullable=False)
    estado: Mapped[EstadoPropiedad] = mapped_column(SQLEnum(EstadoPropiedad), default=EstadoPropiedad.DISPONIBLE)
    
    # Superficies
    superficie_terreno_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    superficie_construida_m2: Mapped[float] = mapped_column(Float, nullable=False)
    superficie_util_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Características físicas
    ano_construccion: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dormitorios: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    banos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estacionamientos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bodegas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    piso: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    orientacion: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Condominio
    es_condominio: Mapped[bool] = mapped_column(Boolean, default=False)
    condominio_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=True)
    
    # Avalúo fiscal
    avaluo_fiscal_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    fecha_avaluo_fiscal: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    exento_contribuciones: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Propietario
    propietario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    
    # Metadatos
    caracteristicas: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    amenities: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    
    # Relaciones
    propietario = relationship("Usuario", back_populates="propiedades")
    expediente = relationship("Expediente", back_populates="propiedad", uselist=False)
    valorizaciones = relationship("Valorizacion", back_populates="propiedad")
    credit_scores = relationship("CreditScore", back_populates="propiedad")
    riesgos = relationship("AnalisisRiesgo", back_populates="propiedad")
    
    __table_args__ = (
        Index('idx_propiedad_ubicacion', 'comuna', 'region'),
        Index('idx_propiedad_geo', 'geometria', postgresql_using='gist'),
    )


# =====================================================
# M02 - RÉGIMEN DE COPROPIEDAD
# =====================================================

class Condominio(Base, AuditMixin):
    """Administración de condominios según Ley 21.442"""
    __tablename__ = "condominios"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identificación
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    comuna: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    rut_comunidad: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    
    # Tipo según Ley 21.442
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # Tipo A, B o C
    
    # Unidades
    total_unidades: Mapped[int] = mapped_column(Integer, nullable=False)
    total_estacionamientos: Mapped[int] = mapped_column(Integer, default=0)
    total_bodegas: Mapped[int] = mapped_column(Integer, default=0)
    
    # Administración
    administrador_nombre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    administrador_rut: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    fecha_inicio_administracion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Finanzas
    gasto_comun_mensual_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    fondo_reserva_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    morosidad_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Reglamento
    reglamento_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    fecha_ultimo_reglamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Compliance Ley 21.442
    cumple_ley_21442: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_verificacion_ley: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observaciones_compliance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class GastoComun(Base, TimestampMixin):
    """Registro de gastos comunes"""
    __tablename__ = "gastos_comunes"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    monto_ordinario_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    monto_extraordinario_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    fondo_reserva_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_pago: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente, pagado, moroso
    dias_mora: Mapped[int] = mapped_column(Integer, default=0)
    interes_mora_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)


# =====================================================
# M03 - CREDIT SCORE INMOBILIARIO
# =====================================================

class CreditScore(Base, TimestampMixin):
    """Score crediticio de propiedad"""
    __tablename__ = "credit_scores"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Score general
    score_total: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-1000
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)  # AAA, AA, A, BBB, BB, B, C, D
    
    # Componentes del score
    score_ubicacion: Mapped[int] = mapped_column(Integer, nullable=False)
    score_legal: Mapped[int] = mapped_column(Integer, nullable=False)
    score_financiero: Mapped[int] = mapped_column(Integer, nullable=False)
    score_tecnico: Mapped[int] = mapped_column(Integer, nullable=False)
    score_mercado: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Pesos utilizados
    pesos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Features para explicabilidad (SHAP)
    shap_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    features_positivos: Mapped[Optional[List[dict]]] = mapped_column(JSONB, nullable=True)
    features_negativos: Mapped[Optional[List[dict]]] = mapped_column(JSONB, nullable=True)
    
    # Recomendaciones
    recomendaciones: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Modelo
    modelo_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    propiedad = relationship("Propiedad", back_populates="credit_scores")


# =====================================================
# M04 - VALORIZACIÓN IVS 2022
# =====================================================

class Valorizacion(Base, AuditMixin):
    """Valorización de propiedad según estándares IVS 2022"""
    __tablename__ = "valorizaciones"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Tipo y propósito
    tipo_valor: Mapped[str] = mapped_column(String(50), nullable=False)  # mercado, liquidacion, inversion, asegurable
    proposito: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_valoracion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_inspeccion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Valores por método
    valor_comparacion_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_costo_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_ingreso_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_residual_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_hedonic_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Valor final reconciliado
    valor_final_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    metodo_principal: Mapped[MetodoValorizacion] = mapped_column(SQLEnum(MetodoValorizacion), nullable=False)
    
    # Ponderaciones de reconciliación
    ponderaciones: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Rango de valor
    valor_minimo_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    valor_maximo_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Comparables utilizados
    comparables_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Detalles DCF
    tasa_descuento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cap_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    flujos_proyectados: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Confianza y modelo ML
    confianza_pct: Mapped[float] = mapped_column(Float, nullable=False)
    modelo_ml_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Tasador
    tasador_nombre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tasador_registro: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Reporte
    reporte_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relaciones
    propiedad = relationship("Propiedad", back_populates="valorizaciones")


class Comparable(Base, TimestampMixin):
    """Propiedades comparables para valorización"""
    __tablename__ = "comparables"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Datos de la transacción
    direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    comuna: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    geometria: Mapped[Any] = mapped_column(Geometry('POINT', srid=4326), nullable=True)
    
    fecha_transaccion: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    precio_uf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    precio_uf_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Características
    tipo: Mapped[TipoPropiedad] = mapped_column(SQLEnum(TipoPropiedad), nullable=False)
    superficie_m2: Mapped[float] = mapped_column(Float, nullable=False)
    dormitorios: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    banos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ano_construccion: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Fuente
    fuente: Mapped[str] = mapped_column(String(50), nullable=False)  # CBR, portal, broker
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)


# =====================================================
# M05 - CARTERA DE ARRIENDOS
# =====================================================

class ContratoArriendo(Base, AuditMixin):
    """Contratos de arriendo"""
    __tablename__ = "contratos_arriendo"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Partes
    arrendador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    arrendatario_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    arrendatario_rut: Mapped[str] = mapped_column(String(12), nullable=False)
    
    # Fechas
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_termino: Mapped[date] = mapped_column(Date, nullable=False)
    renovacion_automatica: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Renta
    renta_mensual_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    dia_pago: Mapped[int] = mapped_column(Integer, default=5)
    garantia_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    meses_garantia: Mapped[int] = mapped_column(Integer, default=1)
    
    # Estado
    estado: Mapped[str] = mapped_column(String(20), default="vigente")  # vigente, terminado, renovado
    
    # Documento
    contrato_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class PagoArriendo(Base, TimestampMixin):
    """Pagos de arriendo"""
    __tablename__ = "pagos_arriendo"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contratos_arriendo.id"), nullable=False)
    
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    monto_uf: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_pago: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    dias_mora: Mapped[int] = mapped_column(Integer, default=0)


# =====================================================
# M12 - DUE DILIGENCE
# =====================================================

class DueDiligence(Base, AuditMixin):
    """Proceso de Due Diligence completo"""
    __tablename__ = "due_diligence"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Estado general
    estado: Mapped[EstadoDueDiligence] = mapped_column(SQLEnum(EstadoDueDiligence), default=EstadoDueDiligence.PENDIENTE)
    progreso_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Scores por área
    score_legal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    score_financiero: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_tecnico: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_ambiental: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Checks completados
    checks_total: Mapped[int] = mapped_column(Integer, default=150)
    checks_completados: Mapped[int] = mapped_column(Integer, default=0)
    checks_aprobados: Mapped[int] = mapped_column(Integer, default=0)
    checks_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    
    # Resultados detallados
    resultados_legal: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resultados_financiero: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resultados_tecnico: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resultados_ambiental: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Observaciones y recomendaciones
    observaciones_criticas: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    recomendaciones: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Fechas
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_finalizacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Reporte
    reporte_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class CheckDueDiligence(Base, TimestampMixin):
    """Checks individuales de Due Diligence"""
    __tablename__ = "checks_due_diligence"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    due_diligence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("due_diligence.id"), nullable=False)
    
    # Identificación del check
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)  # legal, financiero, tecnico, ambiental
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Resultado
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente, aprobado, fallido, no_aplica
    resultado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidencia_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Criticidad
    criticidad: Mapped[str] = mapped_column(String(20), default="medio")  # bajo, medio, alto, critico
    bloquea_operacion: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Ejecución
    ejecutado_por_ia: Mapped[bool] = mapped_column(Boolean, default=True)
    requiere_validacion_humana: Mapped[bool] = mapped_column(Boolean, default=False)
    validado_por: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    fecha_validacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# =====================================================
# M17 - GIRES (Gestión Integral de Riesgos)
# =====================================================

class AnalisisRiesgo(Base, TimestampMixin):
    """Análisis de riesgos multi-hazard"""
    __tablename__ = "analisis_riesgos"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propiedad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("propiedades.id"), nullable=False)
    
    # Scores de riesgo (0-100)
    riesgo_sismico: Mapped[int] = mapped_column(Integer, nullable=False)
    riesgo_tsunami: Mapped[int] = mapped_column(Integer, nullable=False)
    riesgo_inundacion: Mapped[int] = mapped_column(Integer, nullable=False)
    riesgo_remocion: Mapped[int] = mapped_column(Integer, nullable=False)  # remoción en masa
    riesgo_incendio: Mapped[int] = mapped_column(Integer, nullable=False)
    riesgo_volcanico: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Score compuesto
    riesgo_total: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel_riesgo: Mapped[NivelRiesgo] = mapped_column(SQLEnum(NivelRiesgo), nullable=False)
    
    # Pesos utilizados
    pesos_riesgos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Detalles por tipo de riesgo
    detalle_sismico: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    detalle_tsunami: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    detalle_inundacion: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Recomendaciones de mitigación
    recomendaciones_mitigacion: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    costo_mitigacion_uf: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Fuentes de datos
    fuentes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    fecha_datos: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Modelo
    modelo_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    
    # Relaciones
    propiedad = relationship("Propiedad", back_populates="riesgos")


class AlertaRiesgo(Base, TimestampMixin):
    """Alertas de riesgo en tiempo real"""
    __tablename__ = "alertas_riesgo"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tipo de alerta
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # sismo, tsunami, inundacion, etc.
    nivel: Mapped[str] = mapped_column(String(20), nullable=False)  # informativa, precaucion, alerta, alarma
    
    # Ubicación
    geometria_afectada: Mapped[Any] = mapped_column(Geometry('POLYGON', srid=4326), nullable=True)
    comunas_afectadas: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    
    # Detalles
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fuente: Mapped[str] = mapped_column(String(100), nullable=False)  # SENAPRED, SHOA, CSN
    
    # Tiempos
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fecha_vigencia_hasta: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


# =====================================================
# M22 - ÁGORA GEOVIEWER (Consultas espaciales)
# =====================================================

class ConsultaEspacial(Base, TimestampMixin):
    """Registro de consultas espaciales realizadas"""
    __tablename__ = "consultas_espaciales"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    
    # Query en lenguaje natural
    query_original: Mapped[str] = mapped_column(Text, nullable=False)
    query_procesada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Parámetros de la consulta
    capas_consultadas: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    filtros_aplicados: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    geometria_busqueda: Mapped[Any] = mapped_column(Geometry('POLYGON', srid=4326), nullable=True)
    
    # Resultados
    resultados_count: Mapped[int] = mapped_column(Integer, nullable=False)
    tiempo_ejecucion_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # IA
    modelo_llm_usado: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_usados: Mapped[int] = mapped_column(Integer, nullable=False)
    respuesta_ia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CapaGeoespacial(Base, TimestampMixin):
    """Metadatos de capas geoespaciales disponibles"""
    __tablename__ = "capas_geoespaciales"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)  # normativa, riesgos, infraestructura, etc.
    
    # Fuente
    fuente: Mapped[str] = mapped_column(String(100), nullable=False)
    url_servicio: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_servicio: Mapped[str] = mapped_column(String(20), nullable=False)  # WMS, WFS, ArcGIS
    
    # Geometría
    tipo_geometria: Mapped[str] = mapped_column(String(20), nullable=False)  # POINT, LINE, POLYGON
    srid: Mapped[int] = mapped_column(Integer, default=4326)
    
    # Atributos disponibles
    atributos: Mapped[List[dict]] = mapped_column(JSONB, nullable=False)
    
    # Estado
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_ultima_actualizacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# =====================================================
# INICIALIZACIÓN DE BD
# =====================================================

async def init_db():
    """Crear todas las tablas"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Habilitar extensiones PostGIS
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
        
        # Habilitar TimescaleDB si está disponible
        if settings.TIMESCALE_ENABLED:
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
                # Convertir tabla de indicadores a hypertable
                await conn.execute("""
                    SELECT create_hypertable('indicadores_economicos', 'fecha', 
                        if_not_exists => TRUE);
                """)
            except Exception as e:
                print(f"TimescaleDB no disponible: {e}")


async def drop_db():
    """Eliminar todas las tablas (solo desarrollo)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
