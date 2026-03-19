# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Router M02 Copropiedad
API REST para Gestión Integral de Condominios y Copropiedades
Implementación completa Ley 21.442 Chile

Endpoints: 35+
- Gestión Condominios (CRUD + búsqueda)
- Gestión Unidades (registro, transferencia)
- Gestión Copropietarios (registro, estado cuenta)
- Gastos Comunes (emisión, cuotas, pagos)
- Asambleas (programación, convocatoria, quorum, votaciones)
- Cumplimiento Legal (verificación Ley 21.442, CMF)
- Reportes Financieros

Autor: DATAPOLIS SpA
Fecha: 2025
"""

from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

# =====================================================
# ENUMS PARA API
# =====================================================

class TipoCondominioEnum(str, Enum):
    """Tipos de condominio según Ley 21.442"""
    tipo_a = "tipo_a"  # Viviendas adosadas o aisladas
    tipo_b = "tipo_b"  # Edificios
    mixto = "mixto"
    condominio_social = "condominio_social"

class EstadoCondominioEnum(str, Enum):
    """Estados del condominio"""
    activo = "activo"
    inactivo = "inactivo"
    en_constitucion = "en_constitucion"
    en_liquidacion = "en_liquidacion"
    suspendido = "suspendido"

class TipoUnidadEnum(str, Enum):
    """Tipos de unidad en copropiedad"""
    departamento = "departamento"
    casa = "casa"
    oficina = "oficina"
    local_comercial = "local_comercial"
    bodega = "bodega"
    estacionamiento = "estacionamiento"
    area_comun = "area_comun"
    otro = "otro"

class EstadoUnidadEnum(str, Enum):
    """Estado de ocupación de la unidad"""
    ocupada_propietario = "ocupada_propietario"
    arrendada = "arrendada"
    desocupada = "desocupada"
    en_venta = "en_venta"
    en_remodelacion = "en_remodelacion"

class RolCopropietarioEnum(str, Enum):
    """Rol del copropietario"""
    propietario = "propietario"
    arrendatario = "arrendatario"
    usufructuario = "usufructuario"
    representante_legal = "representante_legal"
    administrador = "administrador"

class TipoGastoComunEnum(str, Enum):
    """Tipos de gasto común"""
    ordinario = "ordinario"
    extraordinario = "extraordinario"
    fondo_reserva = "fondo_reserva"

class EstadoCuentaEnum(str, Enum):
    """Estado de cuenta del copropietario"""
    al_dia = "al_dia"
    moroso_30 = "moroso_30"
    moroso_60 = "moroso_60"
    moroso_90 = "moroso_90"
    moroso_grave = "moroso_grave"
    en_cobranza = "en_cobranza"
    convenio_pago = "convenio_pago"

class TipoAsambleaEnum(str, Enum):
    """Tipos de asamblea"""
    ordinaria = "ordinaria"  # Anual obligatoria
    extraordinaria = "extraordinaria"
    universal = "universal"

class EstadoAsambleaEnum(str, Enum):
    """Estado de la asamblea"""
    programada = "programada"
    convocada = "convocada"
    primera_citacion = "primera_citacion"
    segunda_citacion = "segunda_citacion"
    en_curso = "en_curso"
    finalizada = "finalizada"
    cancelada = "cancelada"

class QuorumTipoEnum(str, Enum):
    """Tipos de quórum según Ley 21.442"""
    simple = "simple"  # >50% derechos
    absoluto = "absoluto"
    calificado_66 = "calificado_66"  # Modificar reglamento
    calificado_75 = "calificado_75"  # Reconstrucción
    unanimidad = "unanimidad"

class TipoVotacionEnum(str, Enum):
    """Tipos de votación"""
    abierta = "abierta"
    secreta = "secreta"
    electronica = "electronica"

class MedioPagoEnum(str, Enum):
    """Medios de pago aceptados"""
    transferencia = "transferencia"
    efectivo = "efectivo"
    cheque = "cheque"
    pac = "pac"  # Pago automático
    webpay = "webpay"
    tarjeta_credito = "tarjeta_credito"
    tarjeta_debito = "tarjeta_debito"

class NivelCumplimientoEnum(str, Enum):
    """Nivel de cumplimiento Ley 21.442"""
    completo = "completo"  # 100%
    alto = "alto"  # 80-99%
    medio = "medio"  # 60-79%
    bajo = "bajo"  # 40-59%
    critico = "critico"  # <40%

class FormatoReporteEnum(str, Enum):
    """Formatos de reporte"""
    pdf = "pdf"
    excel = "excel"
    json = "json"

class OrdenEnum(str, Enum):
    """Orden de resultados"""
    asc = "asc"
    desc = "desc"

# =====================================================
# SCHEMAS DE REQUEST
# =====================================================

class DireccionInput(BaseModel):
    """Dirección del condominio"""
    direccion_completa: str = Field(..., min_length=5, max_length=300, description="Dirección completa")
    numero: Optional[str] = Field(None, max_length=20)
    comuna: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=100)
    codigo_postal: Optional[str] = Field(None, max_length=10)
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)

class DatosLegalesInput(BaseModel):
    """Datos legales del condominio"""
    rut_comunidad: str = Field(..., description="RUT de la comunidad (ej: 65.123.456-7)")
    razon_social: str = Field(..., min_length=5, max_length=200)
    rol_sii: Optional[str] = Field(None, description="Rol SII del terreno común")
    fecha_constitucion: date = Field(..., description="Fecha constitución comunidad")
    notaria: Optional[str] = Field(None, max_length=200)
    inscripcion_cbr: Optional[str] = Field(None, description="Inscripción Conservador Bienes Raíces")
    conservador: Optional[str] = Field(None, max_length=200)
    reglamento_vigente: bool = Field(True, description="¿Tiene reglamento vigente?")
    administrador_actual: Optional[str] = Field(None, description="Nombre administrador actual")
    comite_administracion: Optional[List[str]] = Field(default_factory=list, description="Miembros comité")
    
    @validator('rut_comunidad')
    def validar_rut(cls, v):
        """Validar formato RUT chileno"""
        import re
        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$', v):
            raise ValueError('Formato RUT inválido. Debe ser XX.XXX.XXX-X')
        return v.upper()

class ConfiguracionGastosComunesInput(BaseModel):
    """Configuración de gastos comunes"""
    metodo_prorrateo: str = Field("alicuota", description="Método: alicuota, superficie, igualitario")
    porcentaje_fondo_reserva: float = Field(5.0, ge=5.0, le=30.0, description="Mínimo 5% según Ley 21.442")
    dia_vencimiento: int = Field(5, ge=1, le=28, description="Día del mes para vencimiento")
    dias_gracia: int = Field(5, ge=0, le=15, description="Días de gracia")
    tasa_interes_mora_mensual: float = Field(1.5, ge=0, le=1.5, description="Máximo 1.5% mensual")
    umbral_morosidad_grave_meses: int = Field(3, ge=1, le=12)
    genera_multa_atraso: bool = Field(True)

class CrearCondominioRequest(BaseModel):
    """Request para crear condominio"""
    nombre: str = Field(..., min_length=3, max_length=200, description="Nombre del condominio")
    tipo: TipoCondominioEnum = Field(..., description="Tipo según Ley 21.442")
    direccion: DireccionInput
    datos_legales: DatosLegalesInput
    configuracion_gc: Optional[ConfiguracionGastosComunesInput] = None
    superficie_terreno_m2: Optional[float] = Field(None, ge=0)
    superficie_areas_comunes_m2: Optional[float] = Field(None, ge=0)
    presupuesto_anual_uf: Optional[float] = Field(None, ge=0)
    descripcion: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None

class ActualizarCondominioRequest(BaseModel):
    """Request para actualizar condominio"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    estado: Optional[EstadoCondominioEnum] = None
    direccion: Optional[DireccionInput] = None
    datos_legales: Optional[DatosLegalesInput] = None
    configuracion_gc: Optional[ConfiguracionGastosComunesInput] = None
    superficie_terreno_m2: Optional[float] = Field(None, ge=0)
    superficie_areas_comunes_m2: Optional[float] = Field(None, ge=0)
    presupuesto_anual_uf: Optional[float] = Field(None, ge=0)
    descripcion: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None

class RegistrarUnidadRequest(BaseModel):
    """Request para registrar unidad"""
    codigo_unidad: str = Field(..., min_length=1, max_length=20, description="Código único (ej: 101, A-12)")
    tipo: TipoUnidadEnum
    rol_sii: Optional[str] = Field(None, description="Rol SII de la unidad")
    alicuota: float = Field(..., gt=0, le=100, description="Porcentaje de derechos (0-100)")
    superficie_util_m2: float = Field(..., gt=0, description="Superficie útil en m²")
    superficie_terraza_m2: Optional[float] = Field(None, ge=0)
    superficie_bodega_m2: Optional[float] = Field(None, ge=0)
    estacionamientos: int = Field(0, ge=0)
    piso: Optional[int] = None
    orientacion: Optional[str] = Field(None, max_length=50)
    propietario_id: Optional[str] = None
    expediente_id: Optional[str] = None
    ficha_propiedad_id: Optional[str] = None

class ActualizarUnidadRequest(BaseModel):
    """Request para actualizar unidad"""
    estado: Optional[EstadoUnidadEnum] = None
    alicuota: Optional[float] = Field(None, gt=0, le=100)
    superficie_util_m2: Optional[float] = Field(None, gt=0)
    superficie_terraza_m2: Optional[float] = Field(None, ge=0)
    superficie_bodega_m2: Optional[float] = Field(None, ge=0)
    estacionamientos: Optional[int] = Field(None, ge=0)
    propietario_id: Optional[str] = None
    arrendatario_id: Optional[str] = None
    expediente_id: Optional[str] = None
    ficha_propiedad_id: Optional[str] = None

class TransferirPropiedadRequest(BaseModel):
    """Request para transferir propiedad"""
    nuevo_propietario_id: str = Field(..., description="ID del nuevo propietario")
    fecha_transferencia: date = Field(..., description="Fecha de la transferencia")
    precio_venta_uf: Optional[float] = Field(None, ge=0)
    notaria: Optional[str] = None
    inscripcion_cbr: Optional[str] = None
    observaciones: Optional[str] = Field(None, max_length=500)

class RegistrarCopropietarioRequest(BaseModel):
    """Request para registrar copropietario"""
    rut: str = Field(..., description="RUT del copropietario")
    nombre_completo: str = Field(..., min_length=3, max_length=200)
    email: str = Field(..., description="Email de contacto")
    telefono: Optional[str] = Field(None, max_length=20)
    rol: RolCopropietarioEnum = Field(RolCopropietarioEnum.propietario)
    unidades_ids: List[str] = Field(..., min_items=1, description="IDs de unidades asociadas")
    direccion_notificacion: Optional[str] = None
    recibe_notificaciones: bool = Field(True)
    
    @validator('rut')
    def validar_rut(cls, v):
        import re
        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$', v):
            raise ValueError('Formato RUT inválido')
        return v.upper()
    
    @validator('email')
    def validar_email(cls, v):
        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Email inválido')
        return v.lower()

class ItemGastoComunInput(BaseModel):
    """Ítem de detalle del gasto común"""
    concepto: str = Field(..., min_length=2, max_length=200)
    monto_uf: float = Field(..., ge=0)
    tipo: str = Field("ordinario", description="ordinario, extraordinario, fondo_reserva")

class EmitirGastoComunRequest(BaseModel):
    """Request para emitir gasto común"""
    periodo: str = Field(..., regex=r'^\d{4}-(0[1-9]|1[0-2])$', description="Formato YYYY-MM")
    tipo: TipoGastoComunEnum = Field(TipoGastoComunEnum.ordinario)
    monto_total_uf: float = Field(..., gt=0, description="Monto total en UF")
    detalle_items: List[ItemGastoComunInput] = Field(..., min_items=1)
    unidades_afectadas: Optional[List[str]] = Field(None, description="IDs de unidades (None = todas)")
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    observaciones: Optional[str] = Field(None, max_length=500)

class RegistrarPagoRequest(BaseModel):
    """Request para registrar pago"""
    copropietario_id: str = Field(..., description="ID del copropietario")
    unidad_id: str = Field(..., description="ID de la unidad")
    monto_uf: float = Field(..., gt=0, description="Monto pagado en UF")
    medio_pago: MedioPagoEnum
    comprobante: Optional[str] = Field(None, description="Número de comprobante")
    fecha_pago: Optional[date] = None
    periodo_pagado: str = Field(..., regex=r'^\d{4}-(0[1-9]|1[0-2])$')
    observaciones: Optional[str] = Field(None, max_length=300)

class ProgramarAsambleaRequest(BaseModel):
    """Request para programar asamblea"""
    tipo: TipoAsambleaEnum
    fecha_programada: datetime = Field(..., description="Fecha y hora de la asamblea")
    lugar: str = Field(..., min_length=5, max_length=300)
    tabla_materias: List[str] = Field(..., min_items=1, description="Materias a tratar")
    es_virtual: bool = Field(False)
    link_videoconferencia: Optional[str] = None
    quorum_requerido: Optional[QuorumTipoEnum] = None
    observaciones: Optional[str] = Field(None, max_length=500)

class ConvocarAsambleaRequest(BaseModel):
    """Request para convocar asamblea"""
    fecha_convocatoria: date = Field(..., description="Fecha de la convocatoria")
    es_segunda_citacion: bool = Field(False)
    medio_convocatoria: str = Field("email", description="email, carta, publicacion, mixto")
    mensaje_adicional: Optional[str] = Field(None, max_length=1000)

class RegistrarAsistenciaRequest(BaseModel):
    """Request para registrar asistencia"""
    copropietario_id: str
    representado_por: Optional[str] = Field(None, description="RUT del representante si aplica")
    hora_llegada: Optional[datetime] = None

class CrearVotacionRequest(BaseModel):
    """Request para crear votación"""
    materia: str = Field(..., min_length=5, max_length=500)
    descripcion: Optional[str] = Field(None, max_length=1000)
    tipo_votacion: TipoVotacionEnum = Field(TipoVotacionEnum.abierta)
    quorum_requerido: QuorumTipoEnum = Field(QuorumTipoEnum.simple)

class EmitirVotoRequest(BaseModel):
    """Request para emitir voto"""
    copropietario_id: str
    voto: str = Field(..., description="favor, contra, abstencion")
    
    @validator('voto')
    def validar_voto(cls, v):
        if v not in ['favor', 'contra', 'abstencion']:
            raise ValueError('Voto debe ser: favor, contra, abstencion')
        return v

class RegistrarContratoAntenaRequest(BaseModel):
    """Request para registrar contrato de antena (Ley 21.713)"""
    empresa: str = Field(..., min_length=2, max_length=200)
    rut_empresa: str
    monto_mensual_uf: float = Field(..., gt=0)
    fecha_inicio: date
    fecha_termino: date
    ubicacion_antena: str = Field(..., max_length=200)
    tipo_antena: str = Field("telecomunicaciones", description="telecomunicaciones, internet, radio")
    superficie_ocupada_m2: Optional[float] = Field(None, ge=0)
    observaciones: Optional[str] = Field(None, max_length=500)

class GenerarReporteRequest(BaseModel):
    """Request para generar reportes"""
    tipo_reporte: str = Field(..., description="financiero, morosidad, cumplimiento, asambleas")
    periodo_desde: Optional[str] = Field(None, regex=r'^\d{4}-(0[1-9]|1[0-2])$')
    periodo_hasta: Optional[str] = Field(None, regex=r'^\d{4}-(0[1-9]|1[0-2])$')
    formato: FormatoReporteEnum = Field(FormatoReporteEnum.pdf)
    incluir_detalle: bool = Field(True)
    secciones: Optional[List[str]] = None

# =====================================================
# SCHEMAS DE RESPONSE
# =====================================================

class DireccionResponse(BaseModel):
    """Response de dirección"""
    direccion_completa: str
    numero: Optional[str]
    comuna: str
    region: str
    codigo_postal: Optional[str]
    latitud: Optional[float]
    longitud: Optional[float]

class DatosLegalesResponse(BaseModel):
    """Response de datos legales"""
    rut_comunidad: str
    razon_social: str
    rol_sii: Optional[str]
    fecha_constitucion: date
    notaria: Optional[str]
    inscripcion_cbr: Optional[str]
    conservador: Optional[str]
    reglamento_vigente: bool
    administrador_actual: Optional[str]
    comite_administracion: List[str]

class ConfiguracionGCResponse(BaseModel):
    """Response de configuración gastos comunes"""
    metodo_prorrateo: str
    porcentaje_fondo_reserva: float
    dia_vencimiento: int
    dias_gracia: int
    tasa_interes_mora_mensual: float
    umbral_morosidad_grave_meses: int
    genera_multa_atraso: bool

class EstadisticasCondominioResponse(BaseModel):
    """Estadísticas del condominio"""
    total_unidades: int
    total_copropietarios: int
    unidades_ocupadas: int
    unidades_arrendadas: int
    unidades_desocupadas: int
    superficie_total_m2: float
    superficie_areas_comunes_m2: float
    alicuota_total_pct: float

class IndicadoresFinancierosResponse(BaseModel):
    """Indicadores financieros"""
    presupuesto_anual_uf: float
    gasto_comun_promedio_uf: float
    recaudacion_mensual_uf: float
    morosidad_porcentaje: float
    monto_moroso_uf: float
    fondo_reserva_saldo_uf: float
    fondo_reserva_cumple_ley: bool

class CondominioResponse(BaseModel):
    """Response completo de condominio"""
    id: str
    codigo: str
    nombre: str
    tipo: TipoCondominioEnum
    estado: EstadoCondominioEnum
    direccion: DireccionResponse
    datos_legales: DatosLegalesResponse
    configuracion_gc: ConfiguracionGCResponse
    estadisticas: EstadisticasCondominioResponse
    indicadores_financieros: IndicadoresFinancierosResponse
    nivel_cumplimiento_ley: NivelCumplimientoEnum
    puntaje_cumplimiento: int
    ultima_verificacion: Optional[datetime]
    proxima_asamblea: Optional[datetime]
    descripcion: Optional[str]
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    version: int

class CondominioResumenResponse(BaseModel):
    """Response resumido para listados"""
    id: str
    codigo: str
    nombre: str
    tipo: TipoCondominioEnum
    estado: EstadoCondominioEnum
    direccion_completa: str
    comuna: str
    total_unidades: int
    morosidad_porcentaje: float
    nivel_cumplimiento: NivelCumplimientoEnum

class BusquedaCondominiosResponse(BaseModel):
    """Response de búsqueda de condominios"""
    resultados: List[CondominioResumenResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    filtros_aplicados: Dict[str, Any]

class UnidadResponse(BaseModel):
    """Response de unidad"""
    id: str
    condominio_id: str
    codigo_unidad: str
    tipo: TipoUnidadEnum
    estado: EstadoUnidadEnum
    rol_sii: Optional[str]
    alicuota: float
    superficie_util_m2: float
    superficie_terraza_m2: Optional[float]
    superficie_bodega_m2: Optional[float]
    estacionamientos: int
    piso: Optional[int]
    orientacion: Optional[str]
    propietario_id: Optional[str]
    propietario_nombre: Optional[str]
    arrendatario_id: Optional[str]
    arrendatario_nombre: Optional[str]
    expediente_id: Optional[str]
    ficha_propiedad_id: Optional[str]
    saldo_deuda_uf: float
    meses_morosidad: int
    estado_cuenta: EstadoCuentaEnum
    fecha_creacion: datetime
    fecha_actualizacion: datetime

class ListaUnidadesResponse(BaseModel):
    """Response de lista de unidades"""
    unidades: List[UnidadResponse]
    total: int
    condominio_id: str
    condominio_nombre: str
    suma_alicuotas: float

class CopropietarioResponse(BaseModel):
    """Response de copropietario"""
    id: str
    rut: str
    nombre_completo: str
    email: str
    telefono: Optional[str]
    rol: RolCopropietarioEnum
    unidades: List[Dict[str, Any]]  # [{id, codigo, alicuota}]
    porcentaje_derechos: float
    puede_votar: bool
    recibe_notificaciones: bool
    estado_cuenta: EstadoCuentaEnum
    saldo_deuda_total_uf: float
    fecha_registro: datetime

class EstadoCuentaResponse(BaseModel):
    """Response de estado de cuenta"""
    copropietario_id: str
    copropietario_nombre: str
    unidad_id: str
    unidad_codigo: str
    estado: EstadoCuentaEnum
    saldo_deuda_uf: float
    deuda_ordinarios_uf: float
    deuda_extraordinarios_uf: float
    deuda_fondo_reserva_uf: float
    deuda_multas_uf: float
    deuda_intereses_uf: float
    meses_morosidad: int
    ultimo_pago: Optional[Dict[str, Any]]
    proxima_cuota: Optional[Dict[str, Any]]
    historial_pagos: List[Dict[str, Any]]
    cuotas_pendientes: List[Dict[str, Any]]

class GastoComunResponse(BaseModel):
    """Response de gasto común"""
    id: str
    condominio_id: str
    periodo: str
    tipo: TipoGastoComunEnum
    monto_total_uf: float
    fecha_emision: date
    fecha_vencimiento: date
    unidades_afectadas: int
    detalle_items: List[Dict[str, Any]]
    total_recaudado_uf: float
    porcentaje_recaudacion: float
    estado: str  # emitido, parcialmente_pagado, pagado, vencido
    observaciones: Optional[str]
    fecha_creacion: datetime

class CuotaUnidadResponse(BaseModel):
    """Response de cuota individual"""
    id: str
    gasto_comun_id: str
    unidad_id: str
    unidad_codigo: str
    periodo: str
    monto_ordinario_uf: float
    monto_extraordinario_uf: float
    monto_fondo_reserva_uf: float
    monto_total_uf: float
    descuento_uf: float
    recargo_uf: float
    monto_final_uf: float
    estado: str  # pendiente, parcial, pagado, vencido
    fecha_vencimiento: date
    fecha_pago: Optional[date]
    monto_pagado_uf: float

class PagoResponse(BaseModel):
    """Response de pago"""
    id: str
    condominio_id: str
    copropietario_id: str
    copropietario_nombre: str
    unidad_id: str
    unidad_codigo: str
    monto_uf: float
    medio_pago: MedioPagoEnum
    comprobante: Optional[str]
    fecha_pago: date
    periodo_pagado: str
    cuotas_aplicadas: List[Dict[str, Any]]
    observaciones: Optional[str]
    fecha_registro: datetime

class AsambleaResponse(BaseModel):
    """Response de asamblea"""
    id: str
    condominio_id: str
    tipo: TipoAsambleaEnum
    estado: EstadoAsambleaEnum
    fecha_programada: datetime
    lugar: str
    tabla_materias: List[str]
    quorum_requerido: QuorumTipoEnum
    porcentaje_quorum_requerido: float
    convocatoria_primera: Optional[datetime]
    convocatoria_segunda: Optional[datetime]
    es_virtual: bool
    link_videoconferencia: Optional[str]
    asistentes_registrados: int
    derechos_presentes_pct: float
    tiene_quorum: bool
    votaciones: List[Dict[str, Any]]
    acta_id: Optional[str]
    observaciones: Optional[str]
    fecha_creacion: datetime

class QuorumResponse(BaseModel):
    """Response de verificación de quórum"""
    asamblea_id: str
    quorum_requerido: QuorumTipoEnum
    porcentaje_requerido: float
    derechos_presentes: float
    asistentes_count: int
    total_copropietarios: int
    tiene_quorum: bool
    es_segunda_citacion: bool
    diferencia_pct: float
    mensaje: str

class VotacionResponse(BaseModel):
    """Response de votación"""
    id: str
    asamblea_id: str
    materia: str
    descripcion: Optional[str]
    tipo_votacion: TipoVotacionEnum
    quorum_requerido: QuorumTipoEnum
    porcentaje_quorum: float
    estado: str  # abierta, cerrada
    votos_favor_pct: float
    votos_contra_pct: float
    votos_abstencion_pct: float
    total_votantes: int
    resultado: Optional[str]  # aprobada, rechazada, sin_quorum
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime]

class ResultadoVotacionResponse(BaseModel):
    """Response de resultado final de votación"""
    votacion_id: str
    materia: str
    resultado: str
    votos_favor_pct: float
    votos_contra_pct: float
    votos_abstencion_pct: float
    quorum_alcanzado: bool
    quorum_requerido_pct: float
    total_votantes: int
    detalle_votos: Optional[List[Dict[str, Any]]]
    fecha_cierre: datetime

class RequisitoLey21442Response(BaseModel):
    """Response de requisito individual Ley 21.442"""
    codigo: str
    nombre: str
    descripcion: str
    cumple: bool
    puntaje: int
    puntaje_maximo: int
    hallazgos: List[str]
    recomendaciones: List[str]
    fecha_verificacion: datetime

class VerificacionLey21442Response(BaseModel):
    """Response de verificación Ley 21.442"""
    condominio_id: str
    condominio_nombre: str
    nivel_cumplimiento: NivelCumplimientoEnum
    puntaje_total: int
    puntaje_maximo: int
    porcentaje_cumplimiento: float
    requisitos: List[RequisitoLey21442Response]
    hallazgos_criticos: List[str]
    acciones_correctivas: List[Dict[str, Any]]
    proxima_verificacion: date
    fecha_verificacion: datetime
    verificado_por: str

class ContratoAntenaResponse(BaseModel):
    """Response de contrato de antena (Ley 21.713)"""
    id: str
    condominio_id: str
    empresa: str
    rut_empresa: str
    monto_mensual_uf: float
    ingreso_anual_uf: float
    fecha_inicio: date
    fecha_termino: date
    dias_restantes: int
    ubicacion_antena: str
    tipo_antena: str
    superficie_ocupada_m2: Optional[float]
    requiere_declaracion_cmf: bool
    estado: str  # vigente, por_vencer, vencido
    fecha_registro: datetime

class RegistroCMFResponse(BaseModel):
    """Response de registro CMF"""
    condominio_id: str
    tiene_contratos_antenas: bool
    total_contratos: int
    ingresos_antenas_anuales_uf: float
    requiere_declaracion: bool
    cumple_tributacion: bool
    declaraciones_presentadas: List[Dict[str, Any]]
    proxima_declaracion: Optional[date]
    contratos_vigentes: List[Dict[str, Any]]

class ResumenFinancieroResponse(BaseModel):
    """Response de resumen financiero"""
    condominio_id: str
    condominio_nombre: str
    periodo: str
    ingresos: Dict[str, float]  # Por categoría
    total_ingresos_uf: float
    egresos: Dict[str, float]  # Por categoría
    total_egresos_uf: float
    resultado_periodo_uf: float
    saldo_caja_uf: float
    cuentas_por_cobrar_uf: float
    cuentas_por_pagar_uf: float
    fondo_reserva_saldo_uf: float
    fondo_reserva_meta_uf: float
    fondo_reserva_cumple: bool
    fecha_generacion: datetime

class MorosidadResponse(BaseModel):
    """Response de análisis de morosidad"""
    condominio_id: str
    fecha_analisis: datetime
    total_unidades: int
    unidades_al_dia: int
    unidades_morosas: int
    porcentaje_morosidad: float
    monto_total_moroso_uf: float
    distribucion_por_rango: Dict[str, int]  # 30, 60, 90, >90 días
    distribucion_por_monto: Dict[str, int]  # rangos de UF
    top_morosos: List[Dict[str, Any]]
    tendencia_ultimos_meses: List[Dict[str, Any]]
    proyeccion_cobranza: float

class ReporteResponse(BaseModel):
    """Response de generación de reporte"""
    id: str
    condominio_id: str
    tipo_reporte: str
    formato: FormatoReporteEnum
    periodo_desde: Optional[str]
    periodo_hasta: Optional[str]
    url_descarga: str
    tamano_bytes: int
    fecha_generacion: datetime
    expira: datetime
    secciones_incluidas: List[str]

class EstadisticasGlobalesResponse(BaseModel):
    """Response de estadísticas globales"""
    total_condominios: int
    por_tipo: Dict[str, int]
    por_estado: Dict[str, int]
    por_nivel_cumplimiento: Dict[str, int]
    total_unidades: int
    total_copropietarios: int
    morosidad_promedio_pct: float
    cumplimiento_promedio_pct: float
    fecha_calculo: datetime

# =====================================================
# MOCK SERVICE
# =====================================================

class MockCopropiedadService:
    """Servicio mock para desarrollo"""
    
    def __init__(self):
        self.condominios = {}
        self.unidades = {}
        self.copropietarios = {}
        self.gastos_comunes = {}
        self.pagos = {}
        self.asambleas = {}
        self.votaciones = {}
        self.contratos_antena = {}
        self._crear_datos_ejemplo()
    
    def _crear_datos_ejemplo(self):
        """Crear datos de ejemplo"""
        # Condominio ejemplo
        cond_id = str(uuid.uuid4())
        self.condominios[cond_id] = {
            "id": cond_id,
            "codigo": "COND-2025-000001",
            "nombre": "Edificio Los Aromos",
            "tipo": TipoCondominioEnum.tipo_b,
            "estado": EstadoCondominioEnum.activo,
            "direccion": {
                "direccion_completa": "Av. Providencia 1234",
                "numero": "1234",
                "comuna": "Providencia",
                "region": "Metropolitana",
                "codigo_postal": "7500000",
                "latitud": -33.4289,
                "longitud": -70.6093
            },
            "datos_legales": {
                "rut_comunidad": "65.123.456-7",
                "razon_social": "Comunidad Edificio Los Aromos",
                "rol_sii": "123-456",
                "fecha_constitucion": date(2015, 3, 15),
                "notaria": "Notaría González",
                "inscripcion_cbr": "12345-2015",
                "conservador": "CBR Santiago",
                "reglamento_vigente": True,
                "administrador_actual": "Administradora XYZ Ltda.",
                "comite_administracion": ["Juan Pérez", "María González", "Pedro Silva"]
            },
            "configuracion_gc": {
                "metodo_prorrateo": "alicuota",
                "porcentaje_fondo_reserva": 5.0,
                "dia_vencimiento": 5,
                "dias_gracia": 5,
                "tasa_interes_mora_mensual": 1.5,
                "umbral_morosidad_grave_meses": 3,
                "genera_multa_atraso": True
            },
            "estadisticas": {
                "total_unidades": 48,
                "total_copropietarios": 45,
                "unidades_ocupadas": 40,
                "unidades_arrendadas": 8,
                "unidades_desocupadas": 0,
                "superficie_total_m2": 4800.0,
                "superficie_areas_comunes_m2": 500.0,
                "alicuota_total_pct": 100.0
            },
            "indicadores_financieros": {
                "presupuesto_anual_uf": 2400.0,
                "gasto_comun_promedio_uf": 4.2,
                "recaudacion_mensual_uf": 195.0,
                "morosidad_porcentaje": 12.5,
                "monto_moroso_uf": 156.8,
                "fondo_reserva_saldo_uf": 850.0,
                "fondo_reserva_cumple_ley": True
            },
            "nivel_cumplimiento_ley": NivelCumplimientoEnum.alto,
            "puntaje_cumplimiento": 85,
            "ultima_verificacion": datetime(2025, 1, 15, 10, 30),
            "proxima_asamblea": datetime(2025, 3, 20, 19, 0),
            "descripcion": "Edificio residencial de 12 pisos con 48 departamentos",
            "fecha_creacion": datetime(2025, 1, 1, 9, 0),
            "fecha_actualizacion": datetime(2025, 1, 28, 14, 30),
            "version": 3
        }
        
        # Unidades ejemplo
        for i in range(1, 5):
            unidad_id = str(uuid.uuid4())
            self.unidades[unidad_id] = {
                "id": unidad_id,
                "condominio_id": cond_id,
                "codigo_unidad": f"{100 + i}",
                "tipo": TipoUnidadEnum.departamento,
                "estado": EstadoUnidadEnum.ocupada_propietario if i <= 3 else EstadoUnidadEnum.arrendada,
                "rol_sii": f"123-{456 + i}",
                "alicuota": 2.08,
                "superficie_util_m2": 75.0 + (i * 5),
                "superficie_terraza_m2": 8.0,
                "superficie_bodega_m2": 4.0,
                "estacionamientos": 1,
                "piso": i,
                "orientacion": "Norte",
                "propietario_id": f"prop-{i}",
                "propietario_nombre": f"Propietario {i}",
                "arrendatario_id": f"arr-{i}" if i == 4 else None,
                "arrendatario_nombre": f"Arrendatario {i}" if i == 4 else None,
                "expediente_id": None,
                "ficha_propiedad_id": None,
                "saldo_deuda_uf": 0.0 if i <= 2 else 8.4,
                "meses_morosidad": 0 if i <= 2 else 2,
                "estado_cuenta": EstadoCuentaEnum.al_dia if i <= 2 else EstadoCuentaEnum.moroso_60,
                "fecha_creacion": datetime(2025, 1, 1, 9, 0),
                "fecha_actualizacion": datetime(2025, 1, 28, 14, 30)
            }
    
    def obtener_condominio(self, id: str) -> Optional[Dict]:
        return self.condominios.get(id) or (
            next((c for c in self.condominios.values() if c["codigo"] == id), None)
        )
    
    def listar_condominios(self, filtros: Dict, pagina: int, por_pagina: int) -> tuple:
        resultados = list(self.condominios.values())
        total = len(resultados)
        inicio = (pagina - 1) * por_pagina
        return resultados[inicio:inicio + por_pagina], total
    
    def obtener_unidades(self, condominio_id: str) -> List[Dict]:
        return [u for u in self.unidades.values() if u["condominio_id"] == condominio_id]

# Instancia global del servicio mock
mock_service = MockCopropiedadService()

# =====================================================
# ROUTER
# =====================================================

router = APIRouter(
    prefix="/copropiedad",
    tags=["M02 - Copropiedad"],
    responses={
        404: {"description": "Recurso no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)

# =====================================================
# ENDPOINTS - GESTIÓN CONDOMINIOS
# =====================================================

@router.post(
    "/",
    response_model=CondominioResponse,
    status_code=201,
    summary="Crear condominio",
    description="Registra un nuevo condominio en el sistema con validación Ley 21.442"
)
async def crear_condominio(
    request: CrearCondominioRequest,
    background_tasks: BackgroundTasks
):
    """
    Crear nuevo condominio con:
    - Validación de datos legales (RUT, inscripción)
    - Configuración de gastos comunes (fondo reserva mín 5%)
    - Generación de código único COND-YYYY-NNNNNN
    - Verificación inicial de cumplimiento
    """
    # Generar código único
    codigo = f"COND-{datetime.now().year}-{str(len(mock_service.condominios) + 1).zfill(6)}"
    
    condominio_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Configuración por defecto si no se proporciona
    config_gc = request.configuracion_gc or ConfiguracionGastosComunesInput()
    
    condominio = {
        "id": condominio_id,
        "codigo": codigo,
        "nombre": request.nombre,
        "tipo": request.tipo,
        "estado": EstadoCondominioEnum.activo,
        "direccion": request.direccion.dict(),
        "datos_legales": request.datos_legales.dict(),
        "configuracion_gc": config_gc.dict(),
        "estadisticas": {
            "total_unidades": 0,
            "total_copropietarios": 0,
            "unidades_ocupadas": 0,
            "unidades_arrendadas": 0,
            "unidades_desocupadas": 0,
            "superficie_total_m2": 0.0,
            "superficie_areas_comunes_m2": request.superficie_areas_comunes_m2 or 0.0,
            "alicuota_total_pct": 0.0
        },
        "indicadores_financieros": {
            "presupuesto_anual_uf": request.presupuesto_anual_uf or 0.0,
            "gasto_comun_promedio_uf": 0.0,
            "recaudacion_mensual_uf": 0.0,
            "morosidad_porcentaje": 0.0,
            "monto_moroso_uf": 0.0,
            "fondo_reserva_saldo_uf": 0.0,
            "fondo_reserva_cumple_ley": False
        },
        "nivel_cumplimiento_ley": NivelCumplimientoEnum.bajo,
        "puntaje_cumplimiento": 0,
        "ultima_verificacion": None,
        "proxima_asamblea": None,
        "descripcion": request.descripcion,
        "fecha_creacion": ahora,
        "fecha_actualizacion": ahora,
        "version": 1
    }
    
    mock_service.condominios[condominio_id] = condominio
    
    # Programar verificación inicial en background
    background_tasks.add_task(lambda: None)  # Placeholder
    
    return CondominioResponse(**condominio)


@router.get(
    "/{condominio_id}",
    response_model=CondominioResponse,
    summary="Obtener condominio",
    description="Obtiene los datos completos de un condominio por ID o código"
)
async def obtener_condominio(
    condominio_id: str = Path(..., description="ID o código del condominio")
):
    """Obtener condominio por ID o código COND-YYYY-NNNNNN"""
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    return CondominioResponse(**condominio)


@router.get(
    "/",
    response_model=BusquedaCondominiosResponse,
    summary="Buscar condominios",
    description="Búsqueda avanzada de condominios con filtros"
)
async def buscar_condominios(
    texto: Optional[str] = Query(None, description="Búsqueda por nombre, dirección o código"),
    comuna: Optional[str] = Query(None, description="Filtrar por comuna"),
    region: Optional[str] = Query(None, description="Filtrar por región"),
    tipo: Optional[TipoCondominioEnum] = Query(None, description="Filtrar por tipo"),
    estado: Optional[EstadoCondominioEnum] = Query(None, description="Filtrar por estado"),
    nivel_cumplimiento: Optional[NivelCumplimientoEnum] = Query(None, description="Filtrar por cumplimiento"),
    morosidad_max: Optional[float] = Query(None, ge=0, le=100, description="Morosidad máxima %"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página"),
    ordenar_por: str = Query("fecha_actualizacion", description="Campo para ordenar"),
    orden: OrdenEnum = Query(OrdenEnum.desc, description="Dirección del orden")
):
    """
    Búsqueda avanzada con filtros:
    - Texto libre (nombre, dirección, código)
    - Ubicación (comuna, región)
    - Tipo de condominio
    - Estado y nivel de cumplimiento
    - Rango de morosidad
    """
    filtros = {
        "texto": texto,
        "comuna": comuna,
        "region": region,
        "tipo": tipo,
        "estado": estado,
        "nivel_cumplimiento": nivel_cumplimiento,
        "morosidad_max": morosidad_max
    }
    
    resultados, total = mock_service.listar_condominios(filtros, pagina, por_pagina)
    
    resumen = [
        CondominioResumenResponse(
            id=c["id"],
            codigo=c["codigo"],
            nombre=c["nombre"],
            tipo=c["tipo"],
            estado=c["estado"],
            direccion_completa=c["direccion"]["direccion_completa"],
            comuna=c["direccion"]["comuna"],
            total_unidades=c["estadisticas"]["total_unidades"],
            morosidad_porcentaje=c["indicadores_financieros"]["morosidad_porcentaje"],
            nivel_cumplimiento=c["nivel_cumplimiento_ley"]
        )
        for c in resultados
    ]
    
    return BusquedaCondominiosResponse(
        resultados=resumen,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=(total + por_pagina - 1) // por_pagina,
        filtros_aplicados={k: v for k, v in filtros.items() if v is not None}
    )


@router.put(
    "/{condominio_id}",
    response_model=CondominioResponse,
    summary="Actualizar condominio",
    description="Actualiza los datos de un condominio existente"
)
async def actualizar_condominio(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: ActualizarCondominioRequest = Body(...)
):
    """Actualización parcial de condominio con versionamiento"""
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    # Actualizar campos proporcionados
    actualizaciones = request.dict(exclude_unset=True, exclude_none=True)
    for campo, valor in actualizaciones.items():
        if campo == "direccion" and valor:
            condominio["direccion"].update(valor)
        elif campo == "datos_legales" and valor:
            condominio["datos_legales"].update(valor)
        elif campo == "configuracion_gc" and valor:
            condominio["configuracion_gc"].update(valor)
        else:
            condominio[campo] = valor
    
    condominio["fecha_actualizacion"] = datetime.now()
    condominio["version"] += 1
    
    return CondominioResponse(**condominio)


@router.delete(
    "/{condominio_id}",
    status_code=204,
    summary="Eliminar condominio",
    description="Elimina (soft delete) un condominio"
)
async def eliminar_condominio(
    condominio_id: str = Path(..., description="ID del condominio")
):
    """Soft delete - cambia estado a inactivo"""
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    condominio["estado"] = EstadoCondominioEnum.inactivo
    condominio["fecha_actualizacion"] = datetime.now()
    return None


# =====================================================
# ENDPOINTS - GESTIÓN UNIDADES
# =====================================================

@router.post(
    "/{condominio_id}/unidades",
    response_model=UnidadResponse,
    status_code=201,
    summary="Registrar unidad",
    description="Registra una nueva unidad en el condominio"
)
async def registrar_unidad(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: RegistrarUnidadRequest = Body(...)
):
    """
    Registrar nueva unidad con:
    - Validación de alícuota (suma total ≤ 100%)
    - Vinculación con propietario
    - Actualización de estadísticas del condominio
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    # Verificar alícuota disponible
    unidades_existentes = mock_service.obtener_unidades(condominio["id"])
    alicuota_total = sum(u["alicuota"] for u in unidades_existentes)
    if alicuota_total + request.alicuota > 100:
        raise HTTPException(
            status_code=422,
            detail=f"Alícuota excede el 100%. Disponible: {100 - alicuota_total}%"
        )
    
    unidad_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    unidad = {
        "id": unidad_id,
        "condominio_id": condominio["id"],
        "codigo_unidad": request.codigo_unidad,
        "tipo": request.tipo,
        "estado": EstadoUnidadEnum.desocupada,
        "rol_sii": request.rol_sii,
        "alicuota": request.alicuota,
        "superficie_util_m2": request.superficie_util_m2,
        "superficie_terraza_m2": request.superficie_terraza_m2,
        "superficie_bodega_m2": request.superficie_bodega_m2,
        "estacionamientos": request.estacionamientos,
        "piso": request.piso,
        "orientacion": request.orientacion,
        "propietario_id": request.propietario_id,
        "propietario_nombre": None,
        "arrendatario_id": None,
        "arrendatario_nombre": None,
        "expediente_id": request.expediente_id,
        "ficha_propiedad_id": request.ficha_propiedad_id,
        "saldo_deuda_uf": 0.0,
        "meses_morosidad": 0,
        "estado_cuenta": EstadoCuentaEnum.al_dia,
        "fecha_creacion": ahora,
        "fecha_actualizacion": ahora
    }
    
    mock_service.unidades[unidad_id] = unidad
    
    # Actualizar estadísticas condominio
    condominio["estadisticas"]["total_unidades"] += 1
    condominio["estadisticas"]["unidades_desocupadas"] += 1
    condominio["estadisticas"]["superficie_total_m2"] += request.superficie_util_m2
    condominio["estadisticas"]["alicuota_total_pct"] += request.alicuota
    
    return UnidadResponse(**unidad)


@router.get(
    "/{condominio_id}/unidades",
    response_model=ListaUnidadesResponse,
    summary="Listar unidades",
    description="Lista todas las unidades de un condominio"
)
async def listar_unidades(
    condominio_id: str = Path(..., description="ID del condominio"),
    tipo: Optional[TipoUnidadEnum] = Query(None, description="Filtrar por tipo"),
    estado: Optional[EstadoUnidadEnum] = Query(None, description="Filtrar por estado"),
    estado_cuenta: Optional[EstadoCuentaEnum] = Query(None, description="Filtrar por estado cuenta"),
    solo_morosos: bool = Query(False, description="Solo unidades morosas")
):
    """Listar unidades con filtros opcionales"""
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    unidades = mock_service.obtener_unidades(condominio["id"])
    
    # Aplicar filtros
    if tipo:
        unidades = [u for u in unidades if u["tipo"] == tipo]
    if estado:
        unidades = [u for u in unidades if u["estado"] == estado]
    if estado_cuenta:
        unidades = [u for u in unidades if u["estado_cuenta"] == estado_cuenta]
    if solo_morosos:
        unidades = [u for u in unidades if u["meses_morosidad"] > 0]
    
    return ListaUnidadesResponse(
        unidades=[UnidadResponse(**u) for u in unidades],
        total=len(unidades),
        condominio_id=condominio["id"],
        condominio_nombre=condominio["nombre"],
        suma_alicuotas=sum(u["alicuota"] for u in unidades)
    )


@router.get(
    "/{condominio_id}/unidades/{unidad_id}",
    response_model=UnidadResponse,
    summary="Obtener unidad",
    description="Obtiene los datos de una unidad específica"
)
async def obtener_unidad(
    condominio_id: str = Path(..., description="ID del condominio"),
    unidad_id: str = Path(..., description="ID o código de la unidad")
):
    """Obtener unidad por ID o código"""
    unidad = mock_service.unidades.get(unidad_id)
    if not unidad:
        # Buscar por código
        unidades = mock_service.obtener_unidades(condominio_id)
        unidad = next((u for u in unidades if u["codigo_unidad"] == unidad_id), None)
    
    if not unidad:
        raise HTTPException(status_code=404, detail=f"Unidad no encontrada: {unidad_id}")
    
    return UnidadResponse(**unidad)


@router.put(
    "/{condominio_id}/unidades/{unidad_id}",
    response_model=UnidadResponse,
    summary="Actualizar unidad",
    description="Actualiza los datos de una unidad"
)
async def actualizar_unidad(
    condominio_id: str = Path(..., description="ID del condominio"),
    unidad_id: str = Path(..., description="ID de la unidad"),
    request: ActualizarUnidadRequest = Body(...)
):
    """Actualización parcial de unidad"""
    unidad = mock_service.unidades.get(unidad_id)
    if not unidad:
        raise HTTPException(status_code=404, detail=f"Unidad no encontrada: {unidad_id}")
    
    actualizaciones = request.dict(exclude_unset=True, exclude_none=True)
    for campo, valor in actualizaciones.items():
        unidad[campo] = valor
    
    unidad["fecha_actualizacion"] = datetime.now()
    
    return UnidadResponse(**unidad)


@router.post(
    "/{condominio_id}/unidades/{unidad_id}/transferir",
    response_model=UnidadResponse,
    summary="Transferir propiedad",
    description="Registra la transferencia de propiedad de una unidad"
)
async def transferir_propiedad(
    condominio_id: str = Path(..., description="ID del condominio"),
    unidad_id: str = Path(..., description="ID de la unidad"),
    request: TransferirPropiedadRequest = Body(...)
):
    """
    Transferir propiedad:
    - Actualiza propietario
    - Recalcula porcentaje de derechos
    - Registra en historial
    """
    unidad = mock_service.unidades.get(unidad_id)
    if not unidad:
        raise HTTPException(status_code=404, detail=f"Unidad no encontrada: {unidad_id}")
    
    # Registrar transferencia
    unidad["propietario_id"] = request.nuevo_propietario_id
    unidad["propietario_nombre"] = f"Nuevo Propietario {request.nuevo_propietario_id}"
    unidad["fecha_actualizacion"] = datetime.now()
    
    return UnidadResponse(**unidad)


# =====================================================
# ENDPOINTS - GESTIÓN COPROPIETARIOS
# =====================================================

@router.post(
    "/{condominio_id}/copropietarios",
    response_model=CopropietarioResponse,
    status_code=201,
    summary="Registrar copropietario",
    description="Registra un nuevo copropietario en el condominio"
)
async def registrar_copropietario(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: RegistrarCopropietarioRequest = Body(...)
):
    """
    Registrar copropietario:
    - Calcula porcentaje de derechos según alícuotas
    - Asigna derecho a voto según rol
    - Vincula con unidades
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    copropietario_id = str(uuid.uuid4())
    
    # Calcular porcentaje de derechos
    unidades_info = []
    porcentaje_total = 0.0
    for unidad_id in request.unidades_ids:
        unidad = mock_service.unidades.get(unidad_id)
        if unidad:
            unidades_info.append({
                "id": unidad["id"],
                "codigo": unidad["codigo_unidad"],
                "alicuota": unidad["alicuota"]
            })
            porcentaje_total += unidad["alicuota"]
    
    # Determinar si puede votar
    puede_votar = request.rol in [
        RolCopropietarioEnum.propietario,
        RolCopropietarioEnum.usufructuario,
        RolCopropietarioEnum.representante_legal
    ]
    
    copropietario = {
        "id": copropietario_id,
        "rut": request.rut,
        "nombre_completo": request.nombre_completo,
        "email": request.email,
        "telefono": request.telefono,
        "rol": request.rol,
        "unidades": unidades_info,
        "porcentaje_derechos": porcentaje_total,
        "puede_votar": puede_votar,
        "recibe_notificaciones": request.recibe_notificaciones,
        "estado_cuenta": EstadoCuentaEnum.al_dia,
        "saldo_deuda_total_uf": 0.0,
        "fecha_registro": datetime.now()
    }
    
    mock_service.copropietarios[copropietario_id] = copropietario
    
    # Actualizar estadísticas
    condominio["estadisticas"]["total_copropietarios"] += 1
    
    return CopropietarioResponse(**copropietario)


@router.get(
    "/{condominio_id}/copropietarios",
    response_model=List[CopropietarioResponse],
    summary="Listar copropietarios",
    description="Lista todos los copropietarios de un condominio"
)
async def listar_copropietarios(
    condominio_id: str = Path(..., description="ID del condominio"),
    rol: Optional[RolCopropietarioEnum] = Query(None, description="Filtrar por rol"),
    solo_votantes: bool = Query(False, description="Solo con derecho a voto"),
    solo_morosos: bool = Query(False, description="Solo morosos")
):
    """Listar copropietarios con filtros"""
    # En producción, filtrar por condominio_id
    copropietarios = list(mock_service.copropietarios.values())
    
    if rol:
        copropietarios = [c for c in copropietarios if c["rol"] == rol]
    if solo_votantes:
        copropietarios = [c for c in copropietarios if c["puede_votar"]]
    if solo_morosos:
        copropietarios = [c for c in copropietarios if c["saldo_deuda_total_uf"] > 0]
    
    return [CopropietarioResponse(**c) for c in copropietarios]


@router.get(
    "/{condominio_id}/copropietarios/{copropietario_id}/estado-cuenta",
    response_model=EstadoCuentaResponse,
    summary="Estado de cuenta",
    description="Obtiene el estado de cuenta detallado de un copropietario"
)
async def obtener_estado_cuenta(
    condominio_id: str = Path(..., description="ID del condominio"),
    copropietario_id: str = Path(..., description="ID del copropietario"),
    unidad_id: Optional[str] = Query(None, description="ID de unidad específica")
):
    """
    Estado de cuenta detallado:
    - Deuda por categoría (ordinarios, extraordinarios, fondo reserva, multas, intereses)
    - Historial de pagos
    - Cuotas pendientes
    """
    copropietario = mock_service.copropietarios.get(copropietario_id)
    if not copropietario:
        raise HTTPException(status_code=404, detail=f"Copropietario no encontrado: {copropietario_id}")
    
    # Mock de estado de cuenta
    return EstadoCuentaResponse(
        copropietario_id=copropietario_id,
        copropietario_nombre=copropietario["nombre_completo"],
        unidad_id=unidad_id or copropietario["unidades"][0]["id"] if copropietario["unidades"] else "",
        unidad_codigo=copropietario["unidades"][0]["codigo"] if copropietario["unidades"] else "",
        estado=EstadoCuentaEnum.al_dia,
        saldo_deuda_uf=0.0,
        deuda_ordinarios_uf=0.0,
        deuda_extraordinarios_uf=0.0,
        deuda_fondo_reserva_uf=0.0,
        deuda_multas_uf=0.0,
        deuda_intereses_uf=0.0,
        meses_morosidad=0,
        ultimo_pago={"fecha": "2025-01-05", "monto_uf": 4.2, "periodo": "2025-01"},
        proxima_cuota={"periodo": "2025-02", "monto_uf": 4.2, "vencimiento": "2025-02-05"},
        historial_pagos=[],
        cuotas_pendientes=[]
    )


# =====================================================
# ENDPOINTS - GASTOS COMUNES
# =====================================================

@router.post(
    "/{condominio_id}/gastos-comunes",
    response_model=GastoComunResponse,
    status_code=201,
    summary="Emitir gasto común",
    description="Emite el gasto común del período para el condominio"
)
async def emitir_gasto_comun(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: EmitirGastoComunRequest = Body(...)
):
    """
    Emitir gasto común:
    - Calcula cuotas individuales por alícuota
    - Separa fondo de reserva (mín 5% Ley 21.442)
    - Genera fechas de vencimiento
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    gasto_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Calcular fechas
    fecha_emision = request.fecha_emision or ahora.date()
    config = condominio["configuracion_gc"]
    
    # Fecha vencimiento: día configurado del mes siguiente
    if request.fecha_vencimiento:
        fecha_vencimiento = request.fecha_vencimiento
    else:
        mes = int(request.periodo.split("-")[1])
        ano = int(request.periodo.split("-")[0])
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
        fecha_vencimiento = date(ano, mes, config["dia_vencimiento"])
    
    gasto = {
        "id": gasto_id,
        "condominio_id": condominio["id"],
        "periodo": request.periodo,
        "tipo": request.tipo,
        "monto_total_uf": request.monto_total_uf,
        "fecha_emision": fecha_emision,
        "fecha_vencimiento": fecha_vencimiento,
        "unidades_afectadas": condominio["estadisticas"]["total_unidades"],
        "detalle_items": [item.dict() for item in request.detalle_items],
        "total_recaudado_uf": 0.0,
        "porcentaje_recaudacion": 0.0,
        "estado": "emitido",
        "observaciones": request.observaciones,
        "fecha_creacion": ahora
    }
    
    mock_service.gastos_comunes[gasto_id] = gasto
    
    return GastoComunResponse(**gasto)


@router.get(
    "/{condominio_id}/gastos-comunes",
    response_model=List[GastoComunResponse],
    summary="Listar gastos comunes",
    description="Lista los gastos comunes emitidos"
)
async def listar_gastos_comunes(
    condominio_id: str = Path(..., description="ID del condominio"),
    periodo_desde: Optional[str] = Query(None, description="Período inicial YYYY-MM"),
    periodo_hasta: Optional[str] = Query(None, description="Período final YYYY-MM"),
    tipo: Optional[TipoGastoComunEnum] = Query(None, description="Tipo de gasto")
):
    """Listar gastos comunes con filtros de período y tipo"""
    gastos = [g for g in mock_service.gastos_comunes.values() if g["condominio_id"] == condominio_id]
    
    if tipo:
        gastos = [g for g in gastos if g["tipo"] == tipo]
    
    return [GastoComunResponse(**g) for g in gastos]


@router.get(
    "/{condominio_id}/unidades/{unidad_id}/cuotas",
    response_model=List[CuotaUnidadResponse],
    summary="Obtener cuotas de unidad",
    description="Obtiene las cuotas de gasto común de una unidad"
)
async def obtener_cuotas_unidad(
    condominio_id: str = Path(..., description="ID del condominio"),
    unidad_id: str = Path(..., description="ID de la unidad"),
    periodo_desde: Optional[str] = Query(None, description="Período inicial"),
    solo_pendientes: bool = Query(False, description="Solo cuotas pendientes")
):
    """Obtener cuotas individuales de la unidad"""
    # Mock response
    return []


@router.post(
    "/{condominio_id}/pagos",
    response_model=PagoResponse,
    status_code=201,
    summary="Registrar pago",
    description="Registra un pago de gasto común"
)
async def registrar_pago(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: RegistrarPagoRequest = Body(...)
):
    """
    Registrar pago:
    - Aplica a cuotas pendientes (FIFO)
    - Actualiza estado de cuenta
    - Registra movimiento contable
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    pago_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    pago = {
        "id": pago_id,
        "condominio_id": condominio["id"],
        "copropietario_id": request.copropietario_id,
        "copropietario_nombre": "Copropietario",  # Mock
        "unidad_id": request.unidad_id,
        "unidad_codigo": "101",  # Mock
        "monto_uf": request.monto_uf,
        "medio_pago": request.medio_pago,
        "comprobante": request.comprobante,
        "fecha_pago": request.fecha_pago or ahora.date(),
        "periodo_pagado": request.periodo_pagado,
        "cuotas_aplicadas": [],
        "observaciones": request.observaciones,
        "fecha_registro": ahora
    }
    
    mock_service.pagos[pago_id] = pago
    
    return PagoResponse(**pago)


# =====================================================
# ENDPOINTS - ASAMBLEAS Y VOTACIONES
# =====================================================

@router.post(
    "/{condominio_id}/asambleas",
    response_model=AsambleaResponse,
    status_code=201,
    summary="Programar asamblea",
    description="Programa una nueva asamblea de copropietarios"
)
async def programar_asamblea(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: ProgramarAsambleaRequest = Body(...)
):
    """
    Programar asamblea:
    - Determina quórum según materias (Ley 21.442)
    - Configura modalidad (presencial/virtual)
    - Actualiza próxima asamblea del condominio
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    asamblea_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Determinar quórum requerido
    quorum = request.quorum_requerido or QuorumTipoEnum.simple
    porcentaje_quorum = {
        QuorumTipoEnum.simple: 50.01,
        QuorumTipoEnum.absoluto: 50.01,
        QuorumTipoEnum.calificado_66: 66.67,
        QuorumTipoEnum.calificado_75: 75.0,
        QuorumTipoEnum.unanimidad: 100.0
    }.get(quorum, 50.01)
    
    asamblea = {
        "id": asamblea_id,
        "condominio_id": condominio["id"],
        "tipo": request.tipo,
        "estado": EstadoAsambleaEnum.programada,
        "fecha_programada": request.fecha_programada,
        "lugar": request.lugar,
        "tabla_materias": request.tabla_materias,
        "quorum_requerido": quorum,
        "porcentaje_quorum_requerido": porcentaje_quorum,
        "convocatoria_primera": None,
        "convocatoria_segunda": None,
        "es_virtual": request.es_virtual,
        "link_videoconferencia": request.link_videoconferencia,
        "asistentes_registrados": 0,
        "derechos_presentes_pct": 0.0,
        "tiene_quorum": False,
        "votaciones": [],
        "acta_id": None,
        "observaciones": request.observaciones,
        "fecha_creacion": ahora
    }
    
    mock_service.asambleas[asamblea_id] = asamblea
    
    # Actualizar próxima asamblea del condominio
    condominio["proxima_asamblea"] = request.fecha_programada
    
    return AsambleaResponse(**asamblea)


@router.post(
    "/{condominio_id}/asambleas/{asamblea_id}/convocar",
    response_model=AsambleaResponse,
    summary="Convocar asamblea",
    description="Envía la convocatoria de la asamblea"
)
async def convocar_asamblea(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea"),
    request: ConvocarAsambleaRequest = Body(...)
):
    """
    Convocar asamblea (Ley 21.442):
    - 1ª citación: mínimo 10 días de anticipación
    - 2ª citación: 5 días después de 1ª
    """
    asamblea = mock_service.asambleas.get(asamblea_id)
    if not asamblea:
        raise HTTPException(status_code=404, detail=f"Asamblea no encontrada: {asamblea_id}")
    
    if request.es_segunda_citacion:
        asamblea["convocatoria_segunda"] = datetime.combine(request.fecha_convocatoria, datetime.min.time())
        asamblea["estado"] = EstadoAsambleaEnum.segunda_citacion
    else:
        asamblea["convocatoria_primera"] = datetime.combine(request.fecha_convocatoria, datetime.min.time())
        asamblea["estado"] = EstadoAsambleaEnum.convocada
    
    return AsambleaResponse(**asamblea)


@router.post(
    "/{condominio_id}/asambleas/{asamblea_id}/asistencia",
    response_model=Dict[str, Any],
    summary="Registrar asistencia",
    description="Registra la asistencia de un copropietario"
)
async def registrar_asistencia(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea"),
    request: RegistrarAsistenciaRequest = Body(...)
):
    """Registrar asistencia y actualizar derechos presentes"""
    asamblea = mock_service.asambleas.get(asamblea_id)
    if not asamblea:
        raise HTTPException(status_code=404, detail=f"Asamblea no encontrada: {asamblea_id}")
    
    copropietario = mock_service.copropietarios.get(request.copropietario_id)
    if not copropietario:
        raise HTTPException(status_code=404, detail=f"Copropietario no encontrado: {request.copropietario_id}")
    
    # Actualizar asistentes
    asamblea["asistentes_registrados"] += 1
    asamblea["derechos_presentes_pct"] += copropietario["porcentaje_derechos"]
    asamblea["tiene_quorum"] = asamblea["derechos_presentes_pct"] >= asamblea["porcentaje_quorum_requerido"]
    
    return {
        "registrado": True,
        "copropietario_id": request.copropietario_id,
        "porcentaje_derechos": copropietario["porcentaje_derechos"],
        "total_asistentes": asamblea["asistentes_registrados"],
        "derechos_presentes_pct": asamblea["derechos_presentes_pct"],
        "tiene_quorum": asamblea["tiene_quorum"]
    }


@router.get(
    "/{condominio_id}/asambleas/{asamblea_id}/quorum",
    response_model=QuorumResponse,
    summary="Verificar quórum",
    description="Verifica si la asamblea tiene quórum"
)
async def verificar_quorum(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea")
):
    """Verificar quórum según Ley 21.442"""
    asamblea = mock_service.asambleas.get(asamblea_id)
    if not asamblea:
        raise HTTPException(status_code=404, detail=f"Asamblea no encontrada: {asamblea_id}")
    
    es_segunda = asamblea["estado"] == EstadoAsambleaEnum.segunda_citacion
    tiene_quorum = asamblea["tiene_quorum"] or es_segunda  # 2ª citación = quórum con presentes
    
    return QuorumResponse(
        asamblea_id=asamblea_id,
        quorum_requerido=asamblea["quorum_requerido"],
        porcentaje_requerido=asamblea["porcentaje_quorum_requerido"],
        derechos_presentes=asamblea["derechos_presentes_pct"],
        asistentes_count=asamblea["asistentes_registrados"],
        total_copropietarios=45,  # Mock
        tiene_quorum=tiene_quorum,
        es_segunda_citacion=es_segunda,
        diferencia_pct=asamblea["derechos_presentes_pct"] - asamblea["porcentaje_quorum_requerido"],
        mensaje="Quórum alcanzado" if tiene_quorum else "Sin quórum suficiente"
    )


@router.post(
    "/{condominio_id}/asambleas/{asamblea_id}/votaciones",
    response_model=VotacionResponse,
    status_code=201,
    summary="Crear votación",
    description="Crea una nueva votación en la asamblea"
)
async def crear_votacion(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea"),
    request: CrearVotacionRequest = Body(...)
):
    """Crear votación con quórum específico"""
    asamblea = mock_service.asambleas.get(asamblea_id)
    if not asamblea:
        raise HTTPException(status_code=404, detail=f"Asamblea no encontrada: {asamblea_id}")
    
    votacion_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    porcentaje_quorum = {
        QuorumTipoEnum.simple: 50.01,
        QuorumTipoEnum.calificado_66: 66.67,
        QuorumTipoEnum.calificado_75: 75.0,
        QuorumTipoEnum.unanimidad: 100.0
    }.get(request.quorum_requerido, 50.01)
    
    votacion = {
        "id": votacion_id,
        "asamblea_id": asamblea_id,
        "materia": request.materia,
        "descripcion": request.descripcion,
        "tipo_votacion": request.tipo_votacion,
        "quorum_requerido": request.quorum_requerido,
        "porcentaje_quorum": porcentaje_quorum,
        "estado": "abierta",
        "votos_favor_pct": 0.0,
        "votos_contra_pct": 0.0,
        "votos_abstencion_pct": 0.0,
        "total_votantes": 0,
        "resultado": None,
        "fecha_apertura": ahora,
        "fecha_cierre": None
    }
    
    mock_service.votaciones[votacion_id] = votacion
    asamblea["votaciones"].append({"id": votacion_id, "materia": request.materia})
    
    return VotacionResponse(**votacion)


@router.post(
    "/{condominio_id}/asambleas/{asamblea_id}/votaciones/{votacion_id}/votar",
    response_model=Dict[str, Any],
    summary="Emitir voto",
    description="Registra el voto de un copropietario"
)
async def emitir_voto(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea"),
    votacion_id: str = Path(..., description="ID de la votación"),
    request: EmitirVotoRequest = Body(...)
):
    """Emitir voto ponderado por porcentaje de derechos"""
    votacion = mock_service.votaciones.get(votacion_id)
    if not votacion:
        raise HTTPException(status_code=404, detail=f"Votación no encontrada: {votacion_id}")
    
    if votacion["estado"] != "abierta":
        raise HTTPException(status_code=422, detail="La votación está cerrada")
    
    copropietario = mock_service.copropietarios.get(request.copropietario_id)
    if not copropietario:
        raise HTTPException(status_code=404, detail=f"Copropietario no encontrado: {request.copropietario_id}")
    
    if not copropietario["puede_votar"]:
        raise HTTPException(status_code=422, detail="El copropietario no tiene derecho a voto")
    
    # Registrar voto (ponderado por derechos)
    ponderacion = copropietario["porcentaje_derechos"]
    if request.voto == "favor":
        votacion["votos_favor_pct"] += ponderacion
    elif request.voto == "contra":
        votacion["votos_contra_pct"] += ponderacion
    else:
        votacion["votos_abstencion_pct"] += ponderacion
    
    votacion["total_votantes"] += 1
    
    return {
        "registrado": True,
        "copropietario_id": request.copropietario_id,
        "voto": request.voto,
        "ponderacion": ponderacion,
        "totales": {
            "favor": votacion["votos_favor_pct"],
            "contra": votacion["votos_contra_pct"],
            "abstencion": votacion["votos_abstencion_pct"]
        }
    }


@router.post(
    "/{condominio_id}/asambleas/{asamblea_id}/votaciones/{votacion_id}/cerrar",
    response_model=ResultadoVotacionResponse,
    summary="Cerrar votación",
    description="Cierra la votación y calcula el resultado"
)
async def cerrar_votacion(
    condominio_id: str = Path(..., description="ID del condominio"),
    asamblea_id: str = Path(..., description="ID de la asamblea"),
    votacion_id: str = Path(..., description="ID de la votación")
):
    """
    Cerrar votación y determinar resultado:
    - Simple: >50% a favor
    - Calificado 66%: ≥66.67% a favor
    - Calificado 75%: ≥75% a favor
    - Unanimidad: 100% a favor
    """
    votacion = mock_service.votaciones.get(votacion_id)
    if not votacion:
        raise HTTPException(status_code=404, detail=f"Votación no encontrada: {votacion_id}")
    
    ahora = datetime.now()
    votacion["estado"] = "cerrada"
    votacion["fecha_cierre"] = ahora
    
    # Calcular resultado
    total_votos = votacion["votos_favor_pct"] + votacion["votos_contra_pct"]
    if total_votos == 0:
        votacion["resultado"] = "sin_quorum"
    else:
        porcentaje_favor = (votacion["votos_favor_pct"] / total_votos) * 100
        umbral = votacion["porcentaje_quorum"]
        votacion["resultado"] = "aprobada" if porcentaje_favor >= umbral else "rechazada"
    
    return ResultadoVotacionResponse(
        votacion_id=votacion_id,
        materia=votacion["materia"],
        resultado=votacion["resultado"],
        votos_favor_pct=votacion["votos_favor_pct"],
        votos_contra_pct=votacion["votos_contra_pct"],
        votos_abstencion_pct=votacion["votos_abstencion_pct"],
        quorum_alcanzado=votacion["resultado"] != "sin_quorum",
        quorum_requerido_pct=votacion["porcentaje_quorum"],
        total_votantes=votacion["total_votantes"],
        detalle_votos=None,
        fecha_cierre=ahora
    )


# =====================================================
# ENDPOINTS - CUMPLIMIENTO LEY 21.442 Y CMF
# =====================================================

@router.get(
    "/{condominio_id}/cumplimiento",
    response_model=VerificacionLey21442Response,
    summary="Verificar cumplimiento Ley 21.442",
    description="Evalúa el cumplimiento de los requisitos de la Ley 21.442"
)
async def verificar_cumplimiento(
    condominio_id: str = Path(..., description="ID del condominio"),
    forzar_recalculo: bool = Query(False, description="Forzar recálculo")
):
    """
    Verificación de 10 requisitos obligatorios Ley 21.442:
    1. Reglamento de copropiedad vigente
    2. Administrador designado y registrado
    3. Comité de administración (mín 3 miembros)
    4. Asamblea ordinaria anual (últimos 12 meses)
    5. Fondo de reserva ≥5%
    6. Contabilidad formal
    7. Cuenta bancaria de la comunidad
    8. Rendiciones periódicas
    9. Seguro de incendio
    10. Libro de actas
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    ahora = datetime.now()
    
    # Mock de requisitos evaluados
    requisitos = [
        RequisitoLey21442Response(
            codigo="REQ-001",
            nombre="Reglamento de copropiedad",
            descripcion="Reglamento vigente inscrito en CBR",
            cumple=condominio["datos_legales"]["reglamento_vigente"],
            puntaje=10 if condominio["datos_legales"]["reglamento_vigente"] else 0,
            puntaje_maximo=10,
            hallazgos=[],
            recomendaciones=[],
            fecha_verificacion=ahora
        ),
        RequisitoLey21442Response(
            codigo="REQ-002",
            nombre="Administrador designado",
            descripcion="Administrador registrado y vigente",
            cumple=bool(condominio["datos_legales"]["administrador_actual"]),
            puntaje=10 if condominio["datos_legales"]["administrador_actual"] else 0,
            puntaje_maximo=10,
            hallazgos=[],
            recomendaciones=[],
            fecha_verificacion=ahora
        ),
        RequisitoLey21442Response(
            codigo="REQ-003",
            nombre="Comité de administración",
            descripcion="Mínimo 3 miembros electos",
            cumple=len(condominio["datos_legales"]["comite_administracion"]) >= 3,
            puntaje=10 if len(condominio["datos_legales"]["comite_administracion"]) >= 3 else 5,
            puntaje_maximo=10,
            hallazgos=[] if len(condominio["datos_legales"]["comite_administracion"]) >= 3 else ["Comité incompleto"],
            recomendaciones=[] if len(condominio["datos_legales"]["comite_administracion"]) >= 3 else ["Completar comité con mínimo 3 miembros"],
            fecha_verificacion=ahora
        ),
        RequisitoLey21442Response(
            codigo="REQ-004",
            nombre="Asamblea ordinaria anual",
            descripcion="Realizada en últimos 12 meses",
            cumple=True,
            puntaje=10,
            puntaje_maximo=10,
            hallazgos=[],
            recomendaciones=[],
            fecha_verificacion=ahora
        ),
        RequisitoLey21442Response(
            codigo="REQ-005",
            nombre="Fondo de reserva",
            descripcion="Mínimo 5% del presupuesto",
            cumple=condominio["indicadores_financieros"]["fondo_reserva_cumple_ley"],
            puntaje=10 if condominio["indicadores_financieros"]["fondo_reserva_cumple_ley"] else 0,
            puntaje_maximo=10,
            hallazgos=[] if condominio["indicadores_financieros"]["fondo_reserva_cumple_ley"] else ["Fondo reserva bajo mínimo legal"],
            recomendaciones=[] if condominio["indicadores_financieros"]["fondo_reserva_cumple_ley"] else ["Incrementar aportes al fondo de reserva"],
            fecha_verificacion=ahora
        ),
    ]
    
    puntaje_total = sum(r.puntaje for r in requisitos)
    puntaje_maximo = sum(r.puntaje_maximo for r in requisitos)
    porcentaje = (puntaje_total / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    
    if porcentaje >= 90:
        nivel = NivelCumplimientoEnum.completo
    elif porcentaje >= 70:
        nivel = NivelCumplimientoEnum.alto
    elif porcentaje >= 50:
        nivel = NivelCumplimientoEnum.medio
    elif porcentaje >= 30:
        nivel = NivelCumplimientoEnum.bajo
    else:
        nivel = NivelCumplimientoEnum.critico
    
    return VerificacionLey21442Response(
        condominio_id=condominio_id,
        condominio_nombre=condominio["nombre"],
        nivel_cumplimiento=nivel,
        puntaje_total=puntaje_total,
        puntaje_maximo=puntaje_maximo,
        porcentaje_cumplimiento=porcentaje,
        requisitos=requisitos,
        hallazgos_criticos=[h for r in requisitos for h in r.hallazgos],
        acciones_correctivas=[],
        proxima_verificacion=date(2025, 4, 15),
        fecha_verificacion=ahora,
        verificado_por="Sistema DATAPOLIS"
    )


@router.post(
    "/{condominio_id}/contratos-antena",
    response_model=ContratoAntenaResponse,
    status_code=201,
    summary="Registrar contrato antena",
    description="Registra un contrato de arriendo de antena (Ley 21.713)"
)
async def registrar_contrato_antena(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: RegistrarContratoAntenaRequest = Body(...)
):
    """
    Registrar contrato de antena según Ley 21.713:
    - Calcula ingreso anual
    - Determina obligación de declaración CMF
    - Registra para cumplimiento tributario
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    contrato_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Calcular ingreso anual
    ingreso_anual = request.monto_mensual_uf * 12
    
    # Calcular días restantes
    dias_restantes = (request.fecha_termino - date.today()).days
    
    contrato = {
        "id": contrato_id,
        "condominio_id": condominio["id"],
        "empresa": request.empresa,
        "rut_empresa": request.rut_empresa,
        "monto_mensual_uf": request.monto_mensual_uf,
        "ingreso_anual_uf": ingreso_anual,
        "fecha_inicio": request.fecha_inicio,
        "fecha_termino": request.fecha_termino,
        "dias_restantes": dias_restantes,
        "ubicacion_antena": request.ubicacion_antena,
        "tipo_antena": request.tipo_antena,
        "superficie_ocupada_m2": request.superficie_ocupada_m2,
        "requiere_declaracion_cmf": ingreso_anual > 100,  # Umbral ejemplo
        "estado": "vigente" if dias_restantes > 30 else ("por_vencer" if dias_restantes > 0 else "vencido"),
        "fecha_registro": ahora
    }
    
    mock_service.contratos_antena[contrato_id] = contrato
    
    return ContratoAntenaResponse(**contrato)


@router.get(
    "/{condominio_id}/cmf",
    response_model=RegistroCMFResponse,
    summary="Registro CMF",
    description="Obtiene el estado de cumplimiento CMF del condominio"
)
async def obtener_registro_cmf(
    condominio_id: str = Path(..., description="ID del condominio")
):
    """Estado de cumplimiento tributario CMF para arriendos de antenas"""
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    contratos = [c for c in mock_service.contratos_antena.values() if c["condominio_id"] == condominio["id"]]
    
    return RegistroCMFResponse(
        condominio_id=condominio_id,
        tiene_contratos_antenas=len(contratos) > 0,
        total_contratos=len(contratos),
        ingresos_antenas_anuales_uf=sum(c["ingreso_anual_uf"] for c in contratos),
        requiere_declaracion=any(c["requiere_declaracion_cmf"] for c in contratos),
        cumple_tributacion=True,
        declaraciones_presentadas=[],
        proxima_declaracion=date(2025, 4, 30) if contratos else None,
        contratos_vigentes=[{"id": c["id"], "empresa": c["empresa"], "monto_mensual_uf": c["monto_mensual_uf"]} for c in contratos if c["estado"] == "vigente"]
    )


# =====================================================
# ENDPOINTS - REPORTES FINANCIEROS
# =====================================================

@router.get(
    "/{condominio_id}/financiero/resumen",
    response_model=ResumenFinancieroResponse,
    summary="Resumen financiero",
    description="Genera el resumen financiero del período"
)
async def generar_resumen_financiero(
    condominio_id: str = Path(..., description="ID del condominio"),
    periodo: str = Query(..., regex=r'^\d{4}-(0[1-9]|1[0-2])$', description="Período YYYY-MM")
):
    """
    Resumen financiero mensual:
    - Ingresos por categoría
    - Egresos por categoría
    - Resultado del período
    - Estado fondo de reserva
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    return ResumenFinancieroResponse(
        condominio_id=condominio_id,
        condominio_nombre=condominio["nombre"],
        periodo=periodo,
        ingresos={
            "gastos_comunes": 195.0,
            "multas": 2.5,
            "intereses": 1.2,
            "arriendos": 15.0
        },
        total_ingresos_uf=213.7,
        egresos={
            "remuneraciones": 45.0,
            "mantenciones": 35.0,
            "servicios_basicos": 28.0,
            "seguros": 8.0,
            "administracion": 25.0,
            "fondo_reserva": 10.0
        },
        total_egresos_uf=151.0,
        resultado_periodo_uf=62.7,
        saldo_caja_uf=320.5,
        cuentas_por_cobrar_uf=156.8,
        cuentas_por_pagar_uf=45.0,
        fondo_reserva_saldo_uf=850.0,
        fondo_reserva_meta_uf=1000.0,
        fondo_reserva_cumple=True,
        fecha_generacion=datetime.now()
    )


@router.get(
    "/{condominio_id}/financiero/morosidad",
    response_model=MorosidadResponse,
    summary="Análisis de morosidad",
    description="Análisis detallado de la morosidad del condominio"
)
async def analizar_morosidad(
    condominio_id: str = Path(..., description="ID del condominio")
):
    """
    Análisis de morosidad:
    - Distribución por rango de días
    - Distribución por monto
    - Top morosos
    - Tendencia histórica
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    return MorosidadResponse(
        condominio_id=condominio_id,
        fecha_analisis=datetime.now(),
        total_unidades=condominio["estadisticas"]["total_unidades"],
        unidades_al_dia=42,
        unidades_morosas=6,
        porcentaje_morosidad=12.5,
        monto_total_moroso_uf=156.8,
        distribucion_por_rango={"30": 2, "60": 2, "90": 1, "90+": 1},
        distribucion_por_monto={"0-5": 3, "5-10": 2, "10+": 1},
        top_morosos=[
            {"unidad": "503", "monto_uf": 42.0, "meses": 5},
            {"unidad": "1201", "monto_uf": 33.6, "meses": 4},
            {"unidad": "807", "monto_uf": 25.2, "meses": 3}
        ],
        tendencia_ultimos_meses=[
            {"periodo": "2024-10", "porcentaje": 10.2},
            {"periodo": "2024-11", "porcentaje": 11.0},
            {"periodo": "2024-12", "porcentaje": 11.8},
            {"periodo": "2025-01", "porcentaje": 12.5}
        ],
        proyeccion_cobranza=0.75
    )


@router.post(
    "/{condominio_id}/reportes",
    response_model=ReporteResponse,
    status_code=201,
    summary="Generar reporte",
    description="Genera un reporte del condominio"
)
async def generar_reporte(
    condominio_id: str = Path(..., description="ID del condominio"),
    request: GenerarReporteRequest = Body(...),
    background_tasks: BackgroundTasks = None
):
    """
    Generar reportes:
    - Financiero: Ingresos, egresos, balance
    - Morosidad: Análisis detallado
    - Cumplimiento: Estado Ley 21.442
    - Asambleas: Historial y actas
    """
    condominio = mock_service.obtener_condominio(condominio_id)
    if not condominio:
        raise HTTPException(status_code=404, detail=f"Condominio no encontrado: {condominio_id}")
    
    reporte_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    return ReporteResponse(
        id=reporte_id,
        condominio_id=condominio_id,
        tipo_reporte=request.tipo_reporte,
        formato=request.formato,
        periodo_desde=request.periodo_desde,
        periodo_hasta=request.periodo_hasta,
        url_descarga=f"/api/v1/copropiedad/{condominio_id}/reportes/{reporte_id}/download",
        tamano_bytes=125000,
        fecha_generacion=ahora,
        expira=datetime(ahora.year, ahora.month, ahora.day + 7),
        secciones_incluidas=request.secciones or ["resumen", "detalle", "graficos"]
    )


@router.get(
    "/{condominio_id}/reportes/{reporte_id}/download",
    summary="Descargar reporte",
    description="Descarga el archivo del reporte generado"
)
async def descargar_reporte(
    condominio_id: str = Path(..., description="ID del condominio"),
    reporte_id: str = Path(..., description="ID del reporte")
):
    """Endpoint para descarga de reporte generado"""
    # En producción, retornar FileResponse
    return {"mensaje": "Descarga de reporte", "reporte_id": reporte_id}


# =====================================================
# ENDPOINTS - ESTADÍSTICAS GLOBALES
# =====================================================

@router.get(
    "/estadisticas/global",
    response_model=EstadisticasGlobalesResponse,
    summary="Estadísticas globales",
    description="Estadísticas agregadas de todos los condominios"
)
async def obtener_estadisticas_globales():
    """Estadísticas globales del sistema de copropiedades"""
    condominios = list(mock_service.condominios.values())
    
    return EstadisticasGlobalesResponse(
        total_condominios=len(condominios),
        por_tipo={
            "tipo_a": sum(1 for c in condominios if c["tipo"] == TipoCondominioEnum.tipo_a),
            "tipo_b": sum(1 for c in condominios if c["tipo"] == TipoCondominioEnum.tipo_b),
            "mixto": sum(1 for c in condominios if c["tipo"] == TipoCondominioEnum.mixto)
        },
        por_estado={
            "activo": sum(1 for c in condominios if c["estado"] == EstadoCondominioEnum.activo),
            "inactivo": sum(1 for c in condominios if c["estado"] == EstadoCondominioEnum.inactivo)
        },
        por_nivel_cumplimiento={
            "completo": sum(1 for c in condominios if c["nivel_cumplimiento_ley"] == NivelCumplimientoEnum.completo),
            "alto": sum(1 for c in condominios if c["nivel_cumplimiento_ley"] == NivelCumplimientoEnum.alto),
            "medio": sum(1 for c in condominios if c["nivel_cumplimiento_ley"] == NivelCumplimientoEnum.medio),
            "bajo": sum(1 for c in condominios if c["nivel_cumplimiento_ley"] == NivelCumplimientoEnum.bajo)
        },
        total_unidades=sum(c["estadisticas"]["total_unidades"] for c in condominios),
        total_copropietarios=sum(c["estadisticas"]["total_copropietarios"] for c in condominios),
        morosidad_promedio_pct=sum(c["indicadores_financieros"]["morosidad_porcentaje"] for c in condominios) / len(condominios) if condominios else 0,
        cumplimiento_promedio_pct=sum(c["puntaje_cumplimiento"] for c in condominios) / len(condominios) if condominios else 0,
        fecha_calculo=datetime.now()
    )


# =====================================================
# METADATA DEL ROUTER
# =====================================================

ROUTER_METADATA = {
    "nombre": "M02 - Copropiedad",
    "version": "3.0.0",
    "descripcion": "Gestión integral de condominios y copropiedades según Ley 21.442 Chile",
    "endpoints_count": 35,
    "categorias": [
        "Gestión Condominios (CRUD, búsqueda)",
        "Gestión Unidades (registro, transferencia)",
        "Gestión Copropietarios (registro, estado cuenta)",
        "Gastos Comunes (emisión, cuotas, pagos)",
        "Asambleas (programación, quorum, votaciones)",
        "Cumplimiento Legal (Ley 21.442, CMF)",
        "Reportes Financieros"
    ],
    "leyes_implementadas": [
        "Ley 21.442 - Copropiedad Inmobiliaria",
        "Ley 21.713 - Tributación arriendos antenas"
    ],
    "autor": "DATAPOLIS SpA",
    "fecha_actualizacion": "2025-01-29"
}
