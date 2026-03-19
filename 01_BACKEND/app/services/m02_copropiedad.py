# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Servicio M02 Copropiedad
=========================================
Gestión integral de condominios y copropiedades según Ley 21.442

Funcionalidades:
- Registro y administración de condominios
- Gestión de unidades y propietarios
- Gastos comunes y fondos de reserva
- Asambleas y votaciones
- Reglamento de copropiedad
- Cumplimiento normativo Ley 21.442
- Integración CMF para antenas/arrendamientos

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2026-02
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import hashlib
import uuid
import statistics


# =============================================================================
# ENUMS - TIPOS Y ESTADOS
# =============================================================================

class TipoCondominio(Enum):
    """Tipos de condominio según Ley 21.442"""
    TIPO_A = "tipo_a"  # Inmuebles adosados o aislados con terreno común
    TIPO_B = "tipo_b"  # Inmuebles superpuestos (edificios)
    MIXTO = "mixto"    # Combinación de tipo A y B
    CONDOMINIO_SOCIAL = "condominio_social"  # Vivienda social


class EstadoCondominio(Enum):
    """Estado del condominio"""
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    EN_CONSTITUCION = "en_constitucion"
    EN_LIQUIDACION = "en_liquidacion"
    SUSPENDIDO = "suspendido"


class TipoUnidad(Enum):
    """Tipos de unidad en copropiedad"""
    DEPARTAMENTO = "departamento"
    CASA = "casa"
    OFICINA = "oficina"
    LOCAL_COMERCIAL = "local_comercial"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"
    AREA_COMUN = "area_comun"
    OTRO = "otro"


class EstadoUnidad(Enum):
    """Estado de la unidad"""
    OCUPADA_PROPIETARIO = "ocupada_propietario"
    ARRENDADA = "arrendada"
    DESOCUPADA = "desocupada"
    EN_VENTA = "en_venta"
    EN_REMODELACION = "en_remodelacion"


class RolCopropietario(Enum):
    """Rol del copropietario"""
    PROPIETARIO = "propietario"
    ARRENDATARIO = "arrendatario"
    USUFRUCTUARIO = "usufructuario"
    REPRESENTANTE_LEGAL = "representante_legal"
    ADMINISTRADOR = "administrador"


class TipoGastoComun(Enum):
    """Tipos de gastos comunes"""
    ORDINARIO = "ordinario"           # Administración, mantención, servicios
    EXTRAORDINARIO = "extraordinario"  # Reparaciones, mejoras
    FONDO_RESERVA = "fondo_reserva"   # Obligatorio Ley 21.442


class EstadoCuenta(Enum):
    """Estado de cuenta del copropietario"""
    AL_DIA = "al_dia"
    MOROSO_30 = "moroso_30"    # 1-30 días
    MOROSO_60 = "moroso_60"    # 31-60 días
    MOROSO_90 = "moroso_90"    # 61-90 días
    MOROSO_GRAVE = "moroso_grave"  # >90 días
    EN_COBRANZA = "en_cobranza"
    CONVENIO_PAGO = "convenio_pago"


class TipoAsamblea(Enum):
    """Tipos de asamblea"""
    ORDINARIA = "ordinaria"          # Anual obligatoria
    EXTRAORDINARIA = "extraordinaria"  # Temas específicos
    UNIVERSAL = "universal"           # Todos los copropietarios presentes


class EstadoAsamblea(Enum):
    """Estado de la asamblea"""
    PROGRAMADA = "programada"
    CONVOCADA = "convocada"
    PRIMERA_CITACION = "primera_citacion"
    SEGUNDA_CITACION = "segunda_citacion"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


class QuorumTipo(Enum):
    """Tipos de quórum según materia"""
    SIMPLE = "simple"                    # >50% derechos presentes
    ABSOLUTO = "absoluto"                # >50% derechos totales
    CALIFICADO_66 = "calificado_66"     # 66.67% para modificar reglamento
    CALIFICADO_75 = "calificado_75"     # 75% para reconstrucción
    UNANIMIDAD = "unanimidad"            # 100% para cambios estructurales


class TipoVotacion(Enum):
    """Tipos de votación"""
    ABIERTA = "abierta"           # A mano alzada
    SECRETA = "secreta"           # Votación secreta
    ELECTRONICA = "electronica"   # Plataforma digital


class TipoIngreso(Enum):
    """Tipos de ingreso del condominio"""
    GASTO_COMUN = "gasto_comun"
    MULTA = "multa"
    INTERES_MORA = "interes_mora"
    ARRIENDO_AREA_COMUN = "arriendo_area_comun"
    ARRIENDO_ANTENA = "arriendo_antena"  # Ley 21.713
    PUBLICIDAD = "publicidad"
    OTRO = "otro"


class TipoEgreso(Enum):
    """Tipos de egreso"""
    REMUNERACIONES = "remuneraciones"
    MANTENCIONES = "mantenciones"
    REPARACIONES = "reparaciones"
    SERVICIOS_BASICOS = "servicios_basicos"
    SEGUROS = "seguros"
    ADMINISTRACION = "administracion"
    ASESORIAS = "asesorias"
    GASTOS_BANCARIOS = "gastos_bancarios"
    IMPUESTOS = "impuestos"
    FONDO_RESERVA = "fondo_reserva"
    OTRO = "otro"


class NivelCumplimiento(Enum):
    """Nivel de cumplimiento Ley 21.442"""
    COMPLETO = "completo"           # 100% cumplimiento
    ALTO = "alto"                   # 80-99%
    MEDIO = "medio"                 # 60-79%
    BAJO = "bajo"                   # 40-59%
    CRITICO = "critico"             # <40%


# =============================================================================
# DATA CLASSES - ESTRUCTURA CONDOMINIO
# =============================================================================

@dataclass
class DireccionCondominio:
    """Dirección del condominio"""
    direccion_completa: str
    numero: str
    comuna: str
    region: str
    codigo_postal: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


@dataclass
class DatosLegales:
    """Datos legales del condominio"""
    rut_comunidad: str
    razon_social: str
    rol_sii: str
    fecha_constitucion: date
    notaria_constitucion: str
    inscripcion_cbr: str  # Foja-Número-Año
    conservador: str
    reglamento_copropiedad_vigente: str  # ID documento
    fecha_reglamento: date
    administrador_actual: Optional[str] = None
    comite_administracion: List[str] = field(default_factory=list)


@dataclass 
class ConfiguracionGastosComunes:
    """Configuración de gastos comunes"""
    metodo_prorrateo: str = "alicuota"  # alicuota, superficie, igualitario
    porcentaje_fondo_reserva: float = 5.0  # Mínimo 5% Ley 21.442
    dia_vencimiento: int = 10  # Día del mes
    dias_gracia: int = 5
    tasa_interes_mora_mensual: float = 1.5  # Máximo legal
    aplicar_interes_compuesto: bool = False
    umbral_morosidad_grave_meses: int = 3
    genera_multa_atraso: bool = True
    monto_multa_atraso_uf: float = 0.5


@dataclass
class UnidadCopropiedad:
    """Unidad individual de copropiedad"""
    id: str
    condominio_id: str
    codigo_unidad: str  # Ej: "A-101", "Torre1-Piso5-Depto501"
    tipo: TipoUnidad
    rol_sii: str
    alicuota: float  # Porcentaje de derechos
    superficie_util_m2: float
    superficie_terraza_m2: float = 0.0
    superficie_bodega_m2: float = 0.0
    estacionamientos: int = 0
    piso: Optional[int] = None
    orientacion: Optional[str] = None
    estado: EstadoUnidad = EstadoUnidad.OCUPADA_PROPIETARIO
    propietario_id: Optional[str] = None
    arrendatario_id: Optional[str] = None
    fecha_adquisicion: Optional[date] = None
    expediente_id: Optional[str] = None  # Vínculo M00
    ficha_propiedad_id: Optional[str] = None  # Vínculo M01


@dataclass
class Copropietario:
    """Copropietario o residente"""
    id: str
    rut: str
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    telefono_alternativo: Optional[str] = None
    direccion_notificacion: Optional[str] = None
    rol: RolCopropietario = RolCopropietario.PROPIETARIO
    unidades: List[str] = field(default_factory=list)  # IDs de unidades
    porcentaje_derechos: float = 0.0  # Suma de alícuotas
    fecha_registro: date = field(default_factory=date.today)
    activo: bool = True
    recibe_notificaciones: bool = True
    puede_votar: bool = True


@dataclass
class EstadoCuentaCopropietario:
    """Estado de cuenta de un copropietario"""
    copropietario_id: str
    unidad_id: str
    estado: EstadoCuenta
    saldo_favor: float = 0.0
    saldo_deuda: float = 0.0
    deuda_gastos_ordinarios: float = 0.0
    deuda_gastos_extraordinarios: float = 0.0
    deuda_fondo_reserva: float = 0.0
    deuda_multas: float = 0.0
    deuda_intereses: float = 0.0
    meses_morosidad: int = 0
    ultimo_pago_fecha: Optional[date] = None
    ultimo_pago_monto: float = 0.0
    fecha_calculo: datetime = field(default_factory=datetime.now)


# =============================================================================
# DATA CLASSES - GESTIÓN FINANCIERA
# =============================================================================

@dataclass
class GastoComun:
    """Gasto común del período"""
    id: str
    condominio_id: str
    periodo: str  # "2026-01"
    tipo: TipoGastoComun
    descripcion: str
    monto_total: float
    fecha_emision: date
    fecha_vencimiento: date
    unidades_afectadas: List[str] = field(default_factory=list)  # Vacío = todas
    estado: str = "emitido"  # emitido, pagado, parcial, vencido, anulado
    detalle_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CuotaUnidad:
    """Cuota de gasto común por unidad"""
    id: str
    gasto_comun_id: str
    unidad_id: str
    copropietario_id: str
    monto_gasto_ordinario: float
    monto_gasto_extraordinario: float = 0.0
    monto_fondo_reserva: float = 0.0
    monto_total: float = 0.0
    descuento: float = 0.0
    recargo: float = 0.0
    monto_final: float = 0.0
    estado: str = "pendiente"  # pendiente, pagado, parcial, vencido
    fecha_pago: Optional[date] = None
    comprobante_pago: Optional[str] = None


@dataclass
class Pago:
    """Registro de pago"""
    id: str
    condominio_id: str
    copropietario_id: str
    unidad_id: str
    fecha_pago: datetime
    monto: float
    medio_pago: str  # transferencia, efectivo, cheque, pac, webpay
    comprobante: str
    periodo_pagado: str
    cuotas_pagadas: List[str] = field(default_factory=list)
    observaciones: Optional[str] = None
    registrado_por: str = "sistema"


@dataclass
class FondoReserva:
    """Estado del fondo de reserva"""
    condominio_id: str
    saldo_actual: float
    porcentaje_meta: float = 5.0  # Mínimo legal
    saldo_meta_mensual: float = 0.0
    aporte_mensual_requerido: float = 0.0
    cumple_ley_21442: bool = True
    movimientos: List[Dict[str, Any]] = field(default_factory=list)
    fecha_actualizacion: datetime = field(default_factory=datetime.now)


@dataclass
class MovimientoContable:
    """Movimiento contable"""
    id: str
    condominio_id: str
    fecha: datetime
    tipo: str  # ingreso, egreso
    categoria: str
    descripcion: str
    monto: float
    documento_respaldo: Optional[str] = None
    cuenta_contable: Optional[str] = None
    periodo: str = ""
    registrado_por: str = "sistema"


# =============================================================================
# DATA CLASSES - ASAMBLEAS Y VOTACIONES
# =============================================================================

@dataclass
class Asamblea:
    """Asamblea de copropietarios"""
    id: str
    condominio_id: str
    tipo: TipoAsamblea
    fecha_programada: datetime
    lugar: str
    estado: EstadoAsamblea = EstadoAsamblea.PROGRAMADA
    tabla_materias: List[Dict[str, Any]] = field(default_factory=list)
    quorum_requerido: QuorumTipo = QuorumTipo.SIMPLE
    convocatoria_primera: Optional[datetime] = None
    convocatoria_segunda: Optional[datetime] = None
    fecha_realizacion: Optional[datetime] = None
    asistentes: List[str] = field(default_factory=list)  # IDs copropietarios
    derechos_presentes: float = 0.0  # Porcentaje
    acta_id: Optional[str] = None
    grabacion_url: Optional[str] = None
    es_virtual: bool = False
    link_videoconferencia: Optional[str] = None


@dataclass
class Votacion:
    """Votación en asamblea"""
    id: str
    asamblea_id: str
    materia: str
    descripcion: str
    tipo_votacion: TipoVotacion
    quorum_requerido: QuorumTipo
    estado: str = "pendiente"  # pendiente, en_curso, cerrada, anulada
    votos_favor: float = 0.0  # Por derechos
    votos_contra: float = 0.0
    votos_abstencion: float = 0.0
    votos_detalle: List[Dict[str, Any]] = field(default_factory=list)
    resultado: Optional[str] = None  # aprobada, rechazada, sin_quorum
    fecha_inicio: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None


@dataclass
class ActaAsamblea:
    """Acta de asamblea"""
    id: str
    asamblea_id: str
    numero_acta: str
    fecha_certificacion: date
    notario: Optional[str] = None
    contenido: str = ""
    asistentes_registrados: List[Dict[str, Any]] = field(default_factory=list)
    acuerdos: List[Dict[str, Any]] = field(default_factory=list)
    votaciones_realizadas: List[str] = field(default_factory=list)
    firmas_digitales: List[Dict[str, Any]] = field(default_factory=list)
    documento_pdf_url: Optional[str] = None
    hash_documento: Optional[str] = None


# =============================================================================
# DATA CLASSES - CUMPLIMIENTO LEY 21.442
# =============================================================================

@dataclass
class VerificacionLey21442:
    """Verificación de cumplimiento Ley 21.442"""
    condominio_id: str
    fecha_verificacion: datetime
    nivel_cumplimiento: NivelCumplimiento
    puntaje_total: float  # 0-100
    
    # Requisitos obligatorios
    tiene_reglamento_actualizado: bool = False
    tiene_administrador_registrado: bool = False
    tiene_comite_administracion: bool = False
    celebra_asambleas_anuales: bool = False
    tiene_fondo_reserva_minimo: bool = False
    lleva_contabilidad_formal: bool = False
    tiene_cuenta_bancaria_comunidad: bool = False
    presenta_rendiciones_periodicas: bool = False
    tiene_seguro_incendio: bool = False
    tiene_libro_actas: bool = False
    
    # Detalles
    hallazgos: List[Dict[str, Any]] = field(default_factory=list)
    recomendaciones: List[str] = field(default_factory=list)
    acciones_correctivas: List[Dict[str, Any]] = field(default_factory=list)
    proxima_verificacion: Optional[date] = None


@dataclass
class RegistroCMF:
    """Registro para cumplimiento CMF (antenas Ley 21.713)"""
    condominio_id: str
    tiene_contratos_antenas: bool = False
    ingresos_antenas_anuales_uf: float = 0.0
    declaraciones_cmf: List[Dict[str, Any]] = field(default_factory=list)
    contratos_vigentes: List[Dict[str, Any]] = field(default_factory=list)
    cumple_tributacion: bool = True
    ultima_declaracion: Optional[date] = None


# =============================================================================
# DATA CLASSES - ENTIDAD PRINCIPAL
# =============================================================================

@dataclass
class Condominio:
    """Condominio - Entidad principal"""
    id: str
    codigo: str  # "COND-2026-XXXXXX"
    nombre: str
    tipo: TipoCondominio
    estado: EstadoCondominio
    direccion: DireccionCondominio
    datos_legales: DatosLegales
    configuracion_gc: ConfiguracionGastosComunes
    
    # Estadísticas
    total_unidades: int = 0
    total_copropietarios: int = 0
    superficie_total_m2: float = 0.0
    superficie_areas_comunes_m2: float = 0.0
    
    # Financiero
    presupuesto_anual: float = 0.0
    gasto_comun_promedio_uf: float = 0.0
    morosidad_porcentaje: float = 0.0
    fondo_reserva_saldo: float = 0.0
    
    # Cumplimiento
    nivel_cumplimiento_ley: NivelCumplimiento = NivelCumplimiento.MEDIO
    ultima_verificacion: Optional[datetime] = None
    proxima_asamblea: Optional[datetime] = None
    
    # Metadata
    fecha_creacion: datetime = field(default_factory=datetime.now)
    fecha_actualizacion: datetime = field(default_factory=datetime.now)
    creado_por: str = "sistema"
    version: int = 1


@dataclass
class ResumenFinanciero:
    """Resumen financiero del condominio"""
    condominio_id: str
    periodo: str
    
    # Ingresos
    ingresos_gastos_comunes: float = 0.0
    ingresos_multas: float = 0.0
    ingresos_intereses: float = 0.0
    ingresos_arriendos: float = 0.0
    ingresos_otros: float = 0.0
    total_ingresos: float = 0.0
    
    # Egresos
    egresos_remuneraciones: float = 0.0
    egresos_mantenciones: float = 0.0
    egresos_servicios: float = 0.0
    egresos_seguros: float = 0.0
    egresos_administracion: float = 0.0
    egresos_otros: float = 0.0
    total_egresos: float = 0.0
    
    # Balance
    resultado_periodo: float = 0.0
    saldo_caja: float = 0.0
    cuentas_por_cobrar: float = 0.0
    cuentas_por_pagar: float = 0.0
    
    # Fondo de reserva
    aporte_fondo_reserva: float = 0.0
    saldo_fondo_reserva: float = 0.0
    
    fecha_calculo: datetime = field(default_factory=datetime.now)


# =============================================================================
# SERVICIO PRINCIPAL - COPROPIEDAD
# =============================================================================

class CopropiedadService:
    """
    Servicio de gestión de condominios y copropiedades.
    Implementa Ley 21.442 y regulaciones CMF.
    """
    
    def __init__(self):
        self._condominios: Dict[str, Condominio] = {}
        self._unidades: Dict[str, UnidadCopropiedad] = {}
        self._copropietarios: Dict[str, Copropietario] = {}
        self._gastos_comunes: Dict[str, GastoComun] = {}
        self._cuotas: Dict[str, CuotaUnidad] = {}
        self._pagos: Dict[str, Pago] = {}
        self._asambleas: Dict[str, Asamblea] = {}
        self._votaciones: Dict[str, Votacion] = {}
        self._movimientos: Dict[str, MovimientoContable] = {}
        self._init_datos_ejemplo()
    
    def _init_datos_ejemplo(self):
        """Inicializa datos de ejemplo para desarrollo"""
        # Crear condominio de ejemplo
        condominio = self._generar_condominio_ejemplo()
        self._condominios[condominio.id] = condominio
    
    # =========================================================================
    # GESTIÓN DE CONDOMINIOS
    # =========================================================================
    
    def crear_condominio(
        self,
        nombre: str,
        tipo: TipoCondominio,
        direccion: Dict[str, Any],
        datos_legales: Dict[str, Any],
        configuracion_gc: Optional[Dict[str, Any]] = None,
        creado_por: str = "sistema"
    ) -> Condominio:
        """
        Crear nuevo condominio.
        
        Args:
            nombre: Nombre del condominio
            tipo: Tipo según Ley 21.442
            direccion: Datos de dirección
            datos_legales: Datos legales (RUT, inscripción, etc.)
            configuracion_gc: Configuración gastos comunes
            creado_por: Usuario que crea
            
        Returns:
            Condominio creado
        """
        condominio_id = f"cond-{uuid.uuid4().hex[:8]}"
        codigo = f"COND-{datetime.now().year}-{len(self._condominios):06d}"
        
        # Crear dirección
        dir_obj = DireccionCondominio(
            direccion_completa=direccion.get("direccion_completa", ""),
            numero=direccion.get("numero", ""),
            comuna=direccion.get("comuna", ""),
            region=direccion.get("region", ""),
            codigo_postal=direccion.get("codigo_postal"),
            latitud=direccion.get("latitud"),
            longitud=direccion.get("longitud")
        )
        
        # Crear datos legales
        legales_obj = DatosLegales(
            rut_comunidad=datos_legales.get("rut_comunidad", ""),
            razon_social=datos_legales.get("razon_social", nombre),
            rol_sii=datos_legales.get("rol_sii", ""),
            fecha_constitucion=date.fromisoformat(datos_legales.get("fecha_constitucion", "2020-01-01")),
            notaria_constitucion=datos_legales.get("notaria_constitucion", ""),
            inscripcion_cbr=datos_legales.get("inscripcion_cbr", ""),
            conservador=datos_legales.get("conservador", ""),
            reglamento_copropiedad_vigente=datos_legales.get("reglamento_id", ""),
            fecha_reglamento=date.fromisoformat(datos_legales.get("fecha_reglamento", "2020-01-01")),
            administrador_actual=datos_legales.get("administrador"),
            comite_administracion=datos_legales.get("comite", [])
        )
        
        # Configuración gastos comunes (defaults Ley 21.442)
        config_gc = ConfiguracionGastosComunes()
        if configuracion_gc:
            config_gc.metodo_prorrateo = configuracion_gc.get("metodo_prorrateo", "alicuota")
            config_gc.porcentaje_fondo_reserva = max(5.0, configuracion_gc.get("porcentaje_fondo_reserva", 5.0))
            config_gc.dia_vencimiento = configuracion_gc.get("dia_vencimiento", 10)
            config_gc.tasa_interes_mora_mensual = min(1.5, configuracion_gc.get("tasa_mora", 1.5))
        
        condominio = Condominio(
            id=condominio_id,
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            estado=EstadoCondominio.ACTIVO,
            direccion=dir_obj,
            datos_legales=legales_obj,
            configuracion_gc=config_gc,
            creado_por=creado_por
        )
        
        self._condominios[condominio_id] = condominio
        return condominio
    
    def obtener_condominio(self, condominio_id: str) -> Optional[Condominio]:
        """Obtener condominio por ID"""
        return self._condominios.get(condominio_id)
    
    def listar_condominios(
        self,
        comuna: Optional[str] = None,
        tipo: Optional[TipoCondominio] = None,
        estado: Optional[EstadoCondominio] = None,
        limite: int = 50,
        offset: int = 0
    ) -> Tuple[List[Condominio], int]:
        """Listar condominios con filtros"""
        resultados = list(self._condominios.values())
        
        if comuna:
            resultados = [c for c in resultados if c.direccion.comuna.lower() == comuna.lower()]
        if tipo:
            resultados = [c for c in resultados if c.tipo == tipo]
        if estado:
            resultados = [c for c in resultados if c.estado == estado]
        
        total = len(resultados)
        return resultados[offset:offset + limite], total
    
    def actualizar_condominio(
        self,
        condominio_id: str,
        actualizaciones: Dict[str, Any],
        usuario: str
    ) -> Optional[Condominio]:
        """Actualizar datos de condominio"""
        condominio = self._condominios.get(condominio_id)
        if not condominio:
            return None
        
        # Actualizar campos permitidos
        if "nombre" in actualizaciones:
            condominio.nombre = actualizaciones["nombre"]
        if "estado" in actualizaciones:
            condominio.estado = EstadoCondominio(actualizaciones["estado"])
        if "configuracion_gc" in actualizaciones:
            cfg = actualizaciones["configuracion_gc"]
            condominio.configuracion_gc.porcentaje_fondo_reserva = max(5.0, cfg.get("porcentaje_fondo_reserva", 5.0))
            condominio.configuracion_gc.dia_vencimiento = cfg.get("dia_vencimiento", 10)
        
        condominio.fecha_actualizacion = datetime.now()
        condominio.version += 1
        
        return condominio
    
    # =========================================================================
    # GESTIÓN DE UNIDADES
    # =========================================================================
    
    def registrar_unidad(
        self,
        condominio_id: str,
        codigo_unidad: str,
        tipo: TipoUnidad,
        rol_sii: str,
        alicuota: float,
        superficie_util_m2: float,
        propietario_id: Optional[str] = None,
        **kwargs
    ) -> UnidadCopropiedad:
        """
        Registrar nueva unidad en el condominio.
        
        Args:
            condominio_id: ID del condominio
            codigo_unidad: Código único de la unidad (ej: "A-101")
            tipo: Tipo de unidad
            rol_sii: Rol SII de la unidad
            alicuota: Porcentaje de derechos en copropiedad
            superficie_util_m2: Superficie útil
            propietario_id: ID del propietario (opcional)
            
        Returns:
            UnidadCopropiedad creada
        """
        unidad_id = f"unit-{uuid.uuid4().hex[:8]}"
        
        unidad = UnidadCopropiedad(
            id=unidad_id,
            condominio_id=condominio_id,
            codigo_unidad=codigo_unidad,
            tipo=tipo,
            rol_sii=rol_sii,
            alicuota=alicuota,
            superficie_util_m2=superficie_util_m2,
            superficie_terraza_m2=kwargs.get("superficie_terraza_m2", 0),
            superficie_bodega_m2=kwargs.get("superficie_bodega_m2", 0),
            estacionamientos=kwargs.get("estacionamientos", 0),
            piso=kwargs.get("piso"),
            orientacion=kwargs.get("orientacion"),
            estado=EstadoUnidad(kwargs.get("estado", "ocupada_propietario")),
            propietario_id=propietario_id,
            fecha_adquisicion=kwargs.get("fecha_adquisicion")
        )
        
        self._unidades[unidad_id] = unidad
        
        # Actualizar estadísticas del condominio
        condominio = self._condominios.get(condominio_id)
        if condominio:
            condominio.total_unidades += 1
            condominio.superficie_total_m2 += superficie_util_m2
        
        return unidad
    
    def obtener_unidad(self, unidad_id: str) -> Optional[UnidadCopropiedad]:
        """Obtener unidad por ID"""
        return self._unidades.get(unidad_id)
    
    def listar_unidades_condominio(
        self,
        condominio_id: str,
        tipo: Optional[TipoUnidad] = None,
        estado: Optional[EstadoUnidad] = None
    ) -> List[UnidadCopropiedad]:
        """Listar unidades de un condominio"""
        unidades = [u for u in self._unidades.values() if u.condominio_id == condominio_id]
        
        if tipo:
            unidades = [u for u in unidades if u.tipo == tipo]
        if estado:
            unidades = [u for u in unidades if u.estado == estado]
        
        return sorted(unidades, key=lambda u: u.codigo_unidad)
    
    def transferir_propiedad(
        self,
        unidad_id: str,
        nuevo_propietario_id: str,
        fecha_transferencia: date,
        usuario: str
    ) -> Optional[UnidadCopropiedad]:
        """Registrar transferencia de propiedad"""
        unidad = self._unidades.get(unidad_id)
        if not unidad:
            return None
        
        propietario_anterior = unidad.propietario_id
        unidad.propietario_id = nuevo_propietario_id
        unidad.fecha_adquisicion = fecha_transferencia
        
        # Actualizar copropietarios
        if propietario_anterior and propietario_anterior in self._copropietarios:
            cop_anterior = self._copropietarios[propietario_anterior]
            if unidad_id in cop_anterior.unidades:
                cop_anterior.unidades.remove(unidad_id)
                cop_anterior.porcentaje_derechos -= unidad.alicuota
        
        if nuevo_propietario_id in self._copropietarios:
            cop_nuevo = self._copropietarios[nuevo_propietario_id]
            cop_nuevo.unidades.append(unidad_id)
            cop_nuevo.porcentaje_derechos += unidad.alicuota
        
        return unidad
    
    # =========================================================================
    # GESTIÓN DE COPROPIETARIOS
    # =========================================================================
    
    def registrar_copropietario(
        self,
        rut: str,
        nombre_completo: str,
        email: str,
        unidades: List[str],
        rol: RolCopropietario = RolCopropietario.PROPIETARIO,
        **kwargs
    ) -> Copropietario:
        """
        Registrar nuevo copropietario.
        
        Args:
            rut: RUT del copropietario
            nombre_completo: Nombre completo
            email: Email de contacto
            unidades: Lista de IDs de unidades
            rol: Rol en la copropiedad
            
        Returns:
            Copropietario creado
        """
        copropietario_id = f"cop-{uuid.uuid4().hex[:8]}"
        
        # Calcular porcentaje de derechos
        porcentaje = 0.0
        for unidad_id in unidades:
            unidad = self._unidades.get(unidad_id)
            if unidad:
                porcentaje += unidad.alicuota
                unidad.propietario_id = copropietario_id
        
        copropietario = Copropietario(
            id=copropietario_id,
            rut=rut,
            nombre_completo=nombre_completo,
            email=email,
            telefono=kwargs.get("telefono"),
            telefono_alternativo=kwargs.get("telefono_alternativo"),
            direccion_notificacion=kwargs.get("direccion_notificacion"),
            rol=rol,
            unidades=unidades,
            porcentaje_derechos=porcentaje,
            recibe_notificaciones=kwargs.get("recibe_notificaciones", True),
            puede_votar=rol in [RolCopropietario.PROPIETARIO, RolCopropietario.REPRESENTANTE_LEGAL]
        )
        
        self._copropietarios[copropietario_id] = copropietario
        
        return copropietario
    
    def obtener_copropietario(self, copropietario_id: str) -> Optional[Copropietario]:
        """Obtener copropietario por ID"""
        return self._copropietarios.get(copropietario_id)
    
    def listar_copropietarios_condominio(
        self,
        condominio_id: str,
        solo_activos: bool = True
    ) -> List[Copropietario]:
        """Listar copropietarios de un condominio"""
        # Obtener unidades del condominio
        unidades_cond = {u.id for u in self._unidades.values() if u.condominio_id == condominio_id}
        
        copropietarios = []
        for cop in self._copropietarios.values():
            if any(u in unidades_cond for u in cop.unidades):
                if not solo_activos or cop.activo:
                    copropietarios.append(cop)
        
        return sorted(copropietarios, key=lambda c: c.nombre_completo)
    
    def obtener_estado_cuenta(
        self,
        copropietario_id: str,
        unidad_id: str
    ) -> EstadoCuentaCopropietario:
        """
        Obtener estado de cuenta de un copropietario para una unidad.
        
        Calcula deudas, mora e intereses.
        """
        # Calcular deudas desde cuotas pendientes
        cuotas_pendientes = [
            c for c in self._cuotas.values()
            if c.copropietario_id == copropietario_id 
            and c.unidad_id == unidad_id
            and c.estado in ["pendiente", "vencido", "parcial"]
        ]
        
        deuda_ordinarios = sum(c.monto_gasto_ordinario for c in cuotas_pendientes)
        deuda_extraordinarios = sum(c.monto_gasto_extraordinario for c in cuotas_pendientes)
        deuda_reserva = sum(c.monto_fondo_reserva for c in cuotas_pendientes)
        
        # Calcular meses de morosidad
        meses_mora = 0
        if cuotas_pendientes:
            cuota_mas_antigua = min(cuotas_pendientes, key=lambda c: c.id)
            # Simplificado: contar cuotas vencidas
            meses_mora = len([c for c in cuotas_pendientes if c.estado == "vencido"])
        
        # Determinar estado
        if meses_mora == 0:
            estado = EstadoCuenta.AL_DIA
        elif meses_mora <= 1:
            estado = EstadoCuenta.MOROSO_30
        elif meses_mora <= 2:
            estado = EstadoCuenta.MOROSO_60
        elif meses_mora <= 3:
            estado = EstadoCuenta.MOROSO_90
        else:
            estado = EstadoCuenta.MOROSO_GRAVE
        
        deuda_total = deuda_ordinarios + deuda_extraordinarios + deuda_reserva
        
        return EstadoCuentaCopropietario(
            copropietario_id=copropietario_id,
            unidad_id=unidad_id,
            estado=estado,
            saldo_deuda=deuda_total,
            deuda_gastos_ordinarios=deuda_ordinarios,
            deuda_gastos_extraordinarios=deuda_extraordinarios,
            deuda_fondo_reserva=deuda_reserva,
            meses_morosidad=meses_mora
        )
    
    # =========================================================================
    # GESTIÓN DE GASTOS COMUNES
    # =========================================================================
    
    def emitir_gasto_comun(
        self,
        condominio_id: str,
        periodo: str,
        monto_total: float,
        detalle_items: List[Dict[str, Any]],
        tipo: TipoGastoComun = TipoGastoComun.ORDINARIO,
        unidades_afectadas: Optional[List[str]] = None
    ) -> GastoComun:
        """
        Emitir gasto común del período.
        
        Args:
            condominio_id: ID del condominio
            periodo: Período en formato "YYYY-MM"
            monto_total: Monto total a prorratear
            detalle_items: Detalle de ítems del gasto
            tipo: Tipo de gasto común
            unidades_afectadas: Unidades específicas (vacío = todas)
            
        Returns:
            GastoComun emitido
        """
        condominio = self._condominios.get(condominio_id)
        if not condominio:
            raise ValueError(f"Condominio {condominio_id} no encontrado")
        
        gasto_id = f"gc-{uuid.uuid4().hex[:8]}"
        
        # Calcular fechas
        year, month = map(int, periodo.split("-"))
        fecha_emision = date(year, month, 1)
        fecha_vencimiento = date(year, month, condominio.configuracion_gc.dia_vencimiento)
        
        gasto = GastoComun(
            id=gasto_id,
            condominio_id=condominio_id,
            periodo=periodo,
            tipo=tipo,
            descripcion=f"Gasto común {tipo.value} {periodo}",
            monto_total=monto_total,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            unidades_afectadas=unidades_afectadas or [],
            detalle_items=detalle_items
        )
        
        self._gastos_comunes[gasto_id] = gasto
        
        # Generar cuotas individuales
        self._generar_cuotas(gasto, condominio)
        
        return gasto
    
    def _generar_cuotas(self, gasto: GastoComun, condominio: Condominio):
        """Genera cuotas individuales para cada unidad"""
        # Obtener unidades afectadas
        if gasto.unidades_afectadas:
            unidades = [self._unidades[uid] for uid in gasto.unidades_afectadas if uid in self._unidades]
        else:
            unidades = [u for u in self._unidades.values() if u.condominio_id == condominio.id]
        
        if not unidades:
            return
        
        # Calcular prorrateo
        total_alicuotas = sum(u.alicuota for u in unidades)
        
        # Separar fondo de reserva
        porcentaje_reserva = condominio.configuracion_gc.porcentaje_fondo_reserva / 100
        monto_reserva_total = gasto.monto_total * porcentaje_reserva
        monto_gasto_neto = gasto.monto_total - monto_reserva_total
        
        for unidad in unidades:
            factor = unidad.alicuota / total_alicuotas if total_alicuotas > 0 else 0
            
            if gasto.tipo == TipoGastoComun.ORDINARIO:
                monto_ordinario = round(monto_gasto_neto * factor, 0)
                monto_extraordinario = 0
            else:
                monto_ordinario = 0
                monto_extraordinario = round(monto_gasto_neto * factor, 0)
            
            monto_reserva = round(monto_reserva_total * factor, 0)
            monto_total = monto_ordinario + monto_extraordinario + monto_reserva
            
            cuota = CuotaUnidad(
                id=f"cuota-{uuid.uuid4().hex[:8]}",
                gasto_comun_id=gasto.id,
                unidad_id=unidad.id,
                copropietario_id=unidad.propietario_id or "",
                monto_gasto_ordinario=monto_ordinario,
                monto_gasto_extraordinario=monto_extraordinario,
                monto_fondo_reserva=monto_reserva,
                monto_total=monto_total,
                monto_final=monto_total
            )
            
            self._cuotas[cuota.id] = cuota
    
    def obtener_gasto_comun(self, gasto_id: str) -> Optional[GastoComun]:
        """Obtener gasto común por ID"""
        return self._gastos_comunes.get(gasto_id)
    
    def listar_gastos_comunes(
        self,
        condominio_id: str,
        periodo_desde: Optional[str] = None,
        periodo_hasta: Optional[str] = None,
        tipo: Optional[TipoGastoComun] = None
    ) -> List[GastoComun]:
        """Listar gastos comunes de un condominio"""
        gastos = [g for g in self._gastos_comunes.values() if g.condominio_id == condominio_id]
        
        if periodo_desde:
            gastos = [g for g in gastos if g.periodo >= periodo_desde]
        if periodo_hasta:
            gastos = [g for g in gastos if g.periodo <= periodo_hasta]
        if tipo:
            gastos = [g for g in gastos if g.tipo == tipo]
        
        return sorted(gastos, key=lambda g: g.periodo, reverse=True)
    
    def obtener_cuotas_unidad(
        self,
        unidad_id: str,
        periodo_desde: Optional[str] = None,
        solo_pendientes: bool = False
    ) -> List[CuotaUnidad]:
        """Obtener cuotas de una unidad"""
        cuotas = [c for c in self._cuotas.values() if c.unidad_id == unidad_id]
        
        if solo_pendientes:
            cuotas = [c for c in cuotas if c.estado in ["pendiente", "vencido", "parcial"]]
        
        return cuotas
    
    # =========================================================================
    # GESTIÓN DE PAGOS
    # =========================================================================
    
    def registrar_pago(
        self,
        condominio_id: str,
        copropietario_id: str,
        unidad_id: str,
        monto: float,
        medio_pago: str,
        comprobante: str,
        periodo: str,
        registrado_por: str = "sistema"
    ) -> Pago:
        """
        Registrar pago de gasto común.
        
        Aplica pago a cuotas pendientes (de más antigua a más reciente).
        """
        pago_id = f"pago-{uuid.uuid4().hex[:8]}"
        
        pago = Pago(
            id=pago_id,
            condominio_id=condominio_id,
            copropietario_id=copropietario_id,
            unidad_id=unidad_id,
            fecha_pago=datetime.now(),
            monto=monto,
            medio_pago=medio_pago,
            comprobante=comprobante,
            periodo_pagado=periodo,
            registrado_por=registrado_por
        )
        
        # Aplicar pago a cuotas pendientes
        cuotas_pendientes = sorted(
            [c for c in self._cuotas.values() 
             if c.unidad_id == unidad_id and c.estado in ["pendiente", "vencido", "parcial"]],
            key=lambda c: c.gasto_comun_id
        )
        
        monto_restante = monto
        for cuota in cuotas_pendientes:
            if monto_restante <= 0:
                break
            
            pendiente = cuota.monto_final - (cuota.monto_total - cuota.monto_final)
            if monto_restante >= pendiente:
                cuota.estado = "pagado"
                cuota.fecha_pago = date.today()
                monto_restante -= pendiente
                pago.cuotas_pagadas.append(cuota.id)
            else:
                cuota.estado = "parcial"
                monto_restante = 0
        
        self._pagos[pago_id] = pago
        
        # Registrar movimiento contable
        self._registrar_movimiento(
            condominio_id=condominio_id,
            tipo="ingreso",
            categoria=TipoIngreso.GASTO_COMUN.value,
            descripcion=f"Pago gasto común {periodo} - {unidad_id}",
            monto=monto,
            periodo=periodo
        )
        
        return pago
    
    def _registrar_movimiento(
        self,
        condominio_id: str,
        tipo: str,
        categoria: str,
        descripcion: str,
        monto: float,
        periodo: str = ""
    ) -> MovimientoContable:
        """Registrar movimiento contable"""
        mov_id = f"mov-{uuid.uuid4().hex[:8]}"
        
        movimiento = MovimientoContable(
            id=mov_id,
            condominio_id=condominio_id,
            fecha=datetime.now(),
            tipo=tipo,
            categoria=categoria,
            descripcion=descripcion,
            monto=monto,
            periodo=periodo or datetime.now().strftime("%Y-%m")
        )
        
        self._movimientos[mov_id] = movimiento
        return movimiento
    
    # =========================================================================
    # GESTIÓN DE ASAMBLEAS
    # =========================================================================
    
    def programar_asamblea(
        self,
        condominio_id: str,
        tipo: TipoAsamblea,
        fecha_programada: datetime,
        lugar: str,
        tabla_materias: List[Dict[str, Any]],
        es_virtual: bool = False,
        link_videoconferencia: Optional[str] = None
    ) -> Asamblea:
        """
        Programar nueva asamblea.
        
        Args:
            condominio_id: ID del condominio
            tipo: Tipo de asamblea
            fecha_programada: Fecha y hora
            lugar: Lugar de realización
            tabla_materias: Materias a tratar
            es_virtual: Si es asamblea virtual
            link_videoconferencia: Link para asamblea virtual
            
        Returns:
            Asamblea programada
        """
        asamblea_id = f"asam-{uuid.uuid4().hex[:8]}"
        
        # Determinar quórum según tipo
        quorum = QuorumTipo.SIMPLE
        for materia in tabla_materias:
            if materia.get("quorum") == "calificado_66":
                quorum = QuorumTipo.CALIFICADO_66
            elif materia.get("quorum") == "calificado_75":
                quorum = QuorumTipo.CALIFICADO_75
            elif materia.get("quorum") == "unanimidad":
                quorum = QuorumTipo.UNANIMIDAD
                break
        
        asamblea = Asamblea(
            id=asamblea_id,
            condominio_id=condominio_id,
            tipo=tipo,
            fecha_programada=fecha_programada,
            lugar=lugar,
            tabla_materias=tabla_materias,
            quorum_requerido=quorum,
            es_virtual=es_virtual,
            link_videoconferencia=link_videoconferencia
        )
        
        self._asambleas[asamblea_id] = asamblea
        
        # Actualizar próxima asamblea del condominio
        condominio = self._condominios.get(condominio_id)
        if condominio:
            condominio.proxima_asamblea = fecha_programada
        
        return asamblea
    
    def convocar_asamblea(
        self,
        asamblea_id: str,
        fecha_convocatoria: datetime,
        es_segunda_citacion: bool = False
    ) -> Asamblea:
        """
        Enviar convocatoria a asamblea.
        
        Ley 21.442 requiere:
        - Primera citación: 10 días de anticipación
        - Segunda citación: 5 días después si no hay quórum
        """
        asamblea = self._asambleas.get(asamblea_id)
        if not asamblea:
            raise ValueError(f"Asamblea {asamblea_id} no encontrada")
        
        if es_segunda_citacion:
            asamblea.convocatoria_segunda = fecha_convocatoria
            asamblea.estado = EstadoAsamblea.SEGUNDA_CITACION
        else:
            asamblea.convocatoria_primera = fecha_convocatoria
            asamblea.estado = EstadoAsamblea.CONVOCADA
        
        return asamblea
    
    def registrar_asistencia(
        self,
        asamblea_id: str,
        copropietario_id: str,
        representado_por: Optional[str] = None
    ) -> bool:
        """Registrar asistencia a asamblea"""
        asamblea = self._asambleas.get(asamblea_id)
        if not asamblea:
            return False
        
        if copropietario_id not in asamblea.asistentes:
            asamblea.asistentes.append(copropietario_id)
            
            # Actualizar derechos presentes
            cop = self._copropietarios.get(copropietario_id)
            if cop:
                asamblea.derechos_presentes += cop.porcentaje_derechos
        
        return True
    
    def verificar_quorum(self, asamblea_id: str) -> Dict[str, Any]:
        """
        Verificar quórum de asamblea.
        
        Returns:
            Dict con estado del quórum
        """
        asamblea = self._asambleas.get(asamblea_id)
        if not asamblea:
            return {"error": "Asamblea no encontrada"}
        
        # Determinar quórum requerido
        quorum_requerido = 50.0  # Por defecto simple
        if asamblea.quorum_requerido == QuorumTipo.CALIFICADO_66:
            quorum_requerido = 66.67
        elif asamblea.quorum_requerido == QuorumTipo.CALIFICADO_75:
            quorum_requerido = 75.0
        elif asamblea.quorum_requerido == QuorumTipo.UNANIMIDAD:
            quorum_requerido = 100.0
        
        # En segunda citación, quórum es con los presentes
        es_segunda = asamblea.estado == EstadoAsamblea.SEGUNDA_CITACION
        
        hay_quorum = asamblea.derechos_presentes >= quorum_requerido or es_segunda
        
        return {
            "asamblea_id": asamblea_id,
            "tipo_quorum": asamblea.quorum_requerido.value,
            "quorum_requerido_pct": quorum_requerido,
            "derechos_presentes_pct": asamblea.derechos_presentes,
            "asistentes_count": len(asamblea.asistentes),
            "hay_quorum": hay_quorum,
            "es_segunda_citacion": es_segunda,
            "mensaje": "Quórum alcanzado" if hay_quorum else f"Faltan {quorum_requerido - asamblea.derechos_presentes:.2f}% de derechos"
        }
    
    def crear_votacion(
        self,
        asamblea_id: str,
        materia: str,
        descripcion: str,
        tipo_votacion: TipoVotacion = TipoVotacion.ABIERTA,
        quorum_requerido: QuorumTipo = QuorumTipo.SIMPLE
    ) -> Votacion:
        """Crear votación en asamblea"""
        votacion_id = f"vot-{uuid.uuid4().hex[:8]}"
        
        votacion = Votacion(
            id=votacion_id,
            asamblea_id=asamblea_id,
            materia=materia,
            descripcion=descripcion,
            tipo_votacion=tipo_votacion,
            quorum_requerido=quorum_requerido
        )
        
        self._votaciones[votacion_id] = votacion
        return votacion
    
    def emitir_voto(
        self,
        votacion_id: str,
        copropietario_id: str,
        voto: str  # "favor", "contra", "abstencion"
    ) -> bool:
        """
        Emitir voto en votación.
        
        El voto se pondera por los derechos del copropietario.
        """
        votacion = self._votaciones.get(votacion_id)
        copropietario = self._copropietarios.get(copropietario_id)
        
        if not votacion or not copropietario:
            return False
        
        if not copropietario.puede_votar:
            return False
        
        # Verificar si ya votó
        for v in votacion.votos_detalle:
            if v.get("copropietario_id") == copropietario_id:
                return False  # Ya votó
        
        derechos = copropietario.porcentaje_derechos
        
        # Registrar voto
        votacion.votos_detalle.append({
            "copropietario_id": copropietario_id,
            "voto": voto,
            "derechos": derechos,
            "timestamp": datetime.now().isoformat()
        })
        
        # Actualizar totales
        if voto == "favor":
            votacion.votos_favor += derechos
        elif voto == "contra":
            votacion.votos_contra += derechos
        else:
            votacion.votos_abstencion += derechos
        
        return True
    
    def cerrar_votacion(self, votacion_id: str) -> Votacion:
        """
        Cerrar votación y determinar resultado.
        """
        votacion = self._votaciones.get(votacion_id)
        if not votacion:
            raise ValueError(f"Votación {votacion_id} no encontrada")
        
        votacion.estado = "cerrada"
        votacion.fecha_cierre = datetime.now()
        
        # Determinar resultado
        total_votos = votacion.votos_favor + votacion.votos_contra
        if total_votos == 0:
            votacion.resultado = "sin_votos"
        else:
            porcentaje_favor = (votacion.votos_favor / total_votos) * 100
            
            # Verificar quórum requerido
            quorum_requerido = 50.0
            if votacion.quorum_requerido == QuorumTipo.CALIFICADO_66:
                quorum_requerido = 66.67
            elif votacion.quorum_requerido == QuorumTipo.CALIFICADO_75:
                quorum_requerido = 75.0
            elif votacion.quorum_requerido == QuorumTipo.UNANIMIDAD:
                quorum_requerido = 100.0
            
            if porcentaje_favor >= quorum_requerido:
                votacion.resultado = "aprobada"
            else:
                votacion.resultado = "rechazada"
        
        return votacion
    
    # =========================================================================
    # CUMPLIMIENTO LEY 21.442
    # =========================================================================
    
    def verificar_cumplimiento_ley(
        self,
        condominio_id: str
    ) -> VerificacionLey21442:
        """
        Verificar cumplimiento de Ley 21.442.
        
        Evalúa todos los requisitos obligatorios y genera informe.
        """
        condominio = self._condominios.get(condominio_id)
        if not condominio:
            raise ValueError(f"Condominio {condominio_id} no encontrado")
        
        verificacion = VerificacionLey21442(
            condominio_id=condominio_id,
            fecha_verificacion=datetime.now(),
            nivel_cumplimiento=NivelCumplimiento.MEDIO,
            puntaje_total=0.0
        )
        
        puntaje = 0
        hallazgos = []
        recomendaciones = []
        
        # 1. Reglamento de copropiedad actualizado
        if condominio.datos_legales.reglamento_copropiedad_vigente:
            verificacion.tiene_reglamento_actualizado = True
            puntaje += 10
        else:
            hallazgos.append({
                "requisito": "Reglamento de copropiedad",
                "estado": "no_cumple",
                "detalle": "No se encontró reglamento vigente"
            })
            recomendaciones.append("Actualizar e inscribir reglamento de copropiedad")
        
        # 2. Administrador registrado
        if condominio.datos_legales.administrador_actual:
            verificacion.tiene_administrador_registrado = True
            puntaje += 10
        else:
            hallazgos.append({
                "requisito": "Administrador",
                "estado": "no_cumple",
                "detalle": "No hay administrador designado"
            })
            recomendaciones.append("Designar administrador en asamblea")
        
        # 3. Comité de administración
        if len(condominio.datos_legales.comite_administracion) >= 3:
            verificacion.tiene_comite_administracion = True
            puntaje += 10
        else:
            hallazgos.append({
                "requisito": "Comité de administración",
                "estado": "no_cumple",
                "detalle": f"Comité con {len(condominio.datos_legales.comite_administracion)} miembros (mínimo 3)"
            })
            recomendaciones.append("Constituir comité de administración con mínimo 3 miembros")
        
        # 4. Asambleas anuales
        # Verificar si hubo asamblea ordinaria en últimos 12 meses
        asambleas_recientes = [
            a for a in self._asambleas.values()
            if a.condominio_id == condominio_id
            and a.tipo == TipoAsamblea.ORDINARIA
            and a.estado == EstadoAsamblea.FINALIZADA
            and a.fecha_realizacion and a.fecha_realizacion > datetime.now() - timedelta(days=365)
        ]
        if asambleas_recientes:
            verificacion.celebra_asambleas_anuales = True
            puntaje += 15
        else:
            hallazgos.append({
                "requisito": "Asamblea ordinaria anual",
                "estado": "no_cumple",
                "detalle": "No se registra asamblea ordinaria en últimos 12 meses"
            })
            recomendaciones.append("Convocar asamblea ordinaria anual")
        
        # 5. Fondo de reserva mínimo 5%
        if condominio.configuracion_gc.porcentaje_fondo_reserva >= 5.0:
            verificacion.tiene_fondo_reserva_minimo = True
            puntaje += 15
        else:
            hallazgos.append({
                "requisito": "Fondo de reserva",
                "estado": "no_cumple",
                "detalle": f"Fondo de reserva al {condominio.configuracion_gc.porcentaje_fondo_reserva}% (mínimo 5%)"
            })
            recomendaciones.append("Ajustar fondo de reserva al mínimo legal del 5%")
        
        # 6. Contabilidad formal
        movimientos = [m for m in self._movimientos.values() if m.condominio_id == condominio_id]
        if len(movimientos) > 0:
            verificacion.lleva_contabilidad_formal = True
            puntaje += 10
        else:
            hallazgos.append({
                "requisito": "Contabilidad",
                "estado": "no_cumple",
                "detalle": "No se registran movimientos contables"
            })
            recomendaciones.append("Implementar sistema de contabilidad formal")
        
        # 7. Cuenta bancaria (asumimos cumple si hay pagos registrados)
        pagos = [p for p in self._pagos.values() if p.condominio_id == condominio_id]
        if pagos:
            verificacion.tiene_cuenta_bancaria_comunidad = True
            puntaje += 10
        else:
            recomendaciones.append("Abrir cuenta bancaria a nombre de la comunidad")
        
        # 8. Rendiciones periódicas (asumimos cumple si hay gastos emitidos)
        gastos = [g for g in self._gastos_comunes.values() if g.condominio_id == condominio_id]
        if gastos:
            verificacion.presenta_rendiciones_periodicas = True
            puntaje += 10
        
        # 9. Seguro de incendio (verificación manual)
        # Por defecto no cumple sin verificación
        hallazgos.append({
            "requisito": "Seguro de incendio",
            "estado": "verificar",
            "detalle": "Requiere verificación manual de póliza vigente"
        })
        recomendaciones.append("Verificar vigencia de póliza de seguro contra incendio")
        
        # 10. Libro de actas
        actas = [a for a in self._asambleas.values() if a.condominio_id == condominio_id and a.acta_id]
        if actas:
            verificacion.tiene_libro_actas = True
            puntaje += 10
        else:
            hallazgos.append({
                "requisito": "Libro de actas",
                "estado": "no_cumple",
                "detalle": "No se registran actas de asambleas"
            })
            recomendaciones.append("Mantener libro de actas actualizado")
        
        # Calcular nivel de cumplimiento
        verificacion.puntaje_total = puntaje
        if puntaje >= 90:
            verificacion.nivel_cumplimiento = NivelCumplimiento.COMPLETO
        elif puntaje >= 70:
            verificacion.nivel_cumplimiento = NivelCumplimiento.ALTO
        elif puntaje >= 50:
            verificacion.nivel_cumplimiento = NivelCumplimiento.MEDIO
        elif puntaje >= 30:
            verificacion.nivel_cumplimiento = NivelCumplimiento.BAJO
        else:
            verificacion.nivel_cumplimiento = NivelCumplimiento.CRITICO
        
        verificacion.hallazgos = hallazgos
        verificacion.recomendaciones = recomendaciones
        verificacion.proxima_verificacion = date.today() + timedelta(days=90)
        
        # Actualizar condominio
        condominio.nivel_cumplimiento_ley = verificacion.nivel_cumplimiento
        condominio.ultima_verificacion = datetime.now()
        
        return verificacion
    
    def registrar_contrato_antena(
        self,
        condominio_id: str,
        empresa: str,
        monto_mensual_uf: float,
        fecha_inicio: date,
        fecha_termino: date,
        ubicacion_antena: str
    ) -> Dict[str, Any]:
        """
        Registrar contrato de arriendo de antena (Ley 21.713).
        
        Registra para cumplimiento tributario CMF.
        """
        condominio = self._condominios.get(condominio_id)
        if not condominio:
            raise ValueError(f"Condominio {condominio_id} no encontrado")
        
        contrato = {
            "id": f"ant-{uuid.uuid4().hex[:8]}",
            "empresa": empresa,
            "monto_mensual_uf": monto_mensual_uf,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_termino": fecha_termino.isoformat(),
            "ubicacion": ubicacion_antena,
            "vigente": True,
            "registrado_en": datetime.now().isoformat()
        }
        
        # Calcular ingreso anual
        meses = (fecha_termino.year - fecha_inicio.year) * 12 + (fecha_termino.month - fecha_inicio.month)
        ingreso_anual = monto_mensual_uf * min(12, meses)
        
        return {
            "contrato": contrato,
            "ingreso_anual_estimado_uf": ingreso_anual,
            "requiere_declaracion_cmf": ingreso_anual > 0,
            "mensaje": "Contrato registrado. Recuerde declarar ingresos según Ley 21.713"
        }
    
    # =========================================================================
    # REPORTES Y ESTADÍSTICAS
    # =========================================================================
    
    def generar_resumen_financiero(
        self,
        condominio_id: str,
        periodo: str
    ) -> ResumenFinanciero:
        """
        Generar resumen financiero del período.
        """
        condominio = self._condominios.get(condominio_id)
        if not condominio:
            raise ValueError(f"Condominio {condominio_id} no encontrado")
        
        resumen = ResumenFinanciero(
            condominio_id=condominio_id,
            periodo=periodo
        )
        
        # Calcular ingresos del período
        movimientos_periodo = [
            m for m in self._movimientos.values()
            if m.condominio_id == condominio_id and m.periodo == periodo
        ]
        
        for mov in movimientos_periodo:
            if mov.tipo == "ingreso":
                if mov.categoria == TipoIngreso.GASTO_COMUN.value:
                    resumen.ingresos_gastos_comunes += mov.monto
                elif mov.categoria == TipoIngreso.MULTA.value:
                    resumen.ingresos_multas += mov.monto
                elif mov.categoria == TipoIngreso.INTERES_MORA.value:
                    resumen.ingresos_intereses += mov.monto
                elif mov.categoria in [TipoIngreso.ARRIENDO_AREA_COMUN.value, TipoIngreso.ARRIENDO_ANTENA.value]:
                    resumen.ingresos_arriendos += mov.monto
                else:
                    resumen.ingresos_otros += mov.monto
            else:  # egreso
                if mov.categoria == TipoEgreso.REMUNERACIONES.value:
                    resumen.egresos_remuneraciones += mov.monto
                elif mov.categoria == TipoEgreso.MANTENCIONES.value:
                    resumen.egresos_mantenciones += mov.monto
                elif mov.categoria == TipoEgreso.SERVICIOS_BASICOS.value:
                    resumen.egresos_servicios += mov.monto
                elif mov.categoria == TipoEgreso.SEGUROS.value:
                    resumen.egresos_seguros += mov.monto
                elif mov.categoria == TipoEgreso.ADMINISTRACION.value:
                    resumen.egresos_administracion += mov.monto
                else:
                    resumen.egresos_otros += mov.monto
        
        resumen.total_ingresos = (
            resumen.ingresos_gastos_comunes +
            resumen.ingresos_multas +
            resumen.ingresos_intereses +
            resumen.ingresos_arriendos +
            resumen.ingresos_otros
        )
        
        resumen.total_egresos = (
            resumen.egresos_remuneraciones +
            resumen.egresos_mantenciones +
            resumen.egresos_servicios +
            resumen.egresos_seguros +
            resumen.egresos_administracion +
            resumen.egresos_otros
        )
        
        resumen.resultado_periodo = resumen.total_ingresos - resumen.total_egresos
        
        # Calcular cuentas por cobrar (cuotas pendientes)
        cuotas_pendientes = [
            c for c in self._cuotas.values()
            if c.estado in ["pendiente", "vencido", "parcial"]
        ]
        # Filtrar por condominio
        for cuota in cuotas_pendientes:
            unidad = self._unidades.get(cuota.unidad_id)
            if unidad and unidad.condominio_id == condominio_id:
                resumen.cuentas_por_cobrar += cuota.monto_final
        
        resumen.saldo_fondo_reserva = condominio.fondo_reserva_saldo
        
        return resumen
    
    def calcular_morosidad(self, condominio_id: str) -> Dict[str, Any]:
        """
        Calcular indicadores de morosidad del condominio.
        """
        unidades = [u for u in self._unidades.values() if u.condominio_id == condominio_id]
        
        total_unidades = len(unidades)
        unidades_morosas = 0
        monto_total_moroso = 0.0
        morosos_por_rango = {
            "30_dias": 0,
            "60_dias": 0,
            "90_dias": 0,
            "mas_90_dias": 0
        }
        
        for unidad in unidades:
            if unidad.propietario_id:
                estado = self.obtener_estado_cuenta(unidad.propietario_id, unidad.id)
                if estado.estado != EstadoCuenta.AL_DIA:
                    unidades_morosas += 1
                    monto_total_moroso += estado.saldo_deuda
                    
                    if estado.estado == EstadoCuenta.MOROSO_30:
                        morosos_por_rango["30_dias"] += 1
                    elif estado.estado == EstadoCuenta.MOROSO_60:
                        morosos_por_rango["60_dias"] += 1
                    elif estado.estado == EstadoCuenta.MOROSO_90:
                        morosos_por_rango["90_dias"] += 1
                    else:
                        morosos_por_rango["mas_90_dias"] += 1
        
        porcentaje_morosidad = (unidades_morosas / total_unidades * 100) if total_unidades > 0 else 0
        
        # Actualizar condominio
        condominio = self._condominios.get(condominio_id)
        if condominio:
            condominio.morosidad_porcentaje = porcentaje_morosidad
        
        return {
            "condominio_id": condominio_id,
            "total_unidades": total_unidades,
            "unidades_morosas": unidades_morosas,
            "porcentaje_morosidad": round(porcentaje_morosidad, 2),
            "monto_total_moroso": monto_total_moroso,
            "distribucion_por_rango": morosos_por_rango,
            "fecha_calculo": datetime.now().isoformat()
        }
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _generar_condominio_ejemplo(self) -> Condominio:
        """Genera condominio de ejemplo para desarrollo"""
        condominio_id = "cond-ejemplo-001"
        
        direccion = DireccionCondominio(
            direccion_completa="Av. Providencia 1234",
            numero="1234",
            comuna="Providencia",
            region="Metropolitana",
            codigo_postal="7500000",
            latitud=-33.4280,
            longitud=-70.6100
        )
        
        datos_legales = DatosLegales(
            rut_comunidad="65.123.456-7",
            razon_social="Comunidad Edificio Providencia",
            rol_sii="1234-567",
            fecha_constitucion=date(2015, 3, 15),
            notaria_constitucion="Notaría Juan Pérez",
            inscripcion_cbr="Foja 1234 N° 567 Año 2015",
            conservador="Santiago",
            reglamento_copropiedad_vigente="reg-001",
            fecha_reglamento=date(2022, 6, 1),
            administrador_actual="Administradora ABC Ltda.",
            comite_administracion=["Juan Pérez", "María García", "Carlos López"]
        )
        
        config_gc = ConfiguracionGastosComunes(
            metodo_prorrateo="alicuota",
            porcentaje_fondo_reserva=5.0,
            dia_vencimiento=10,
            dias_gracia=5,
            tasa_interes_mora_mensual=1.5
        )
        
        condominio = Condominio(
            id=condominio_id,
            codigo="COND-2026-000001",
            nombre="Edificio Providencia",
            tipo=TipoCondominio.TIPO_B,
            estado=EstadoCondominio.ACTIVO,
            direccion=direccion,
            datos_legales=datos_legales,
            configuracion_gc=config_gc,
            total_unidades=120,
            total_copropietarios=115,
            superficie_total_m2=12500.0,
            superficie_areas_comunes_m2=2500.0,
            presupuesto_anual=180000000,
            gasto_comun_promedio_uf=8.5,
            morosidad_porcentaje=12.5,
            fondo_reserva_saldo=45000000,
            nivel_cumplimiento_ley=NivelCumplimiento.ALTO
        )
        
        return condominio
