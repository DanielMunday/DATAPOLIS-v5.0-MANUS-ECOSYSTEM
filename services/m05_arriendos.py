"""
DATAPOLIS v3.0 - Módulo M05: Gestión de Arriendos
=================================================
Sistema integral de administración de arriendos inmobiliarios.

Características principales:
- Gestión de contratos de arriendo (Ley 18.101 y Ley 21.461)
- Cálculo de rentabilidad y proyecciones
- Administración de garantías y depósitos
- Cobranza y seguimiento de pagos
- Reajustabilidad automática (IPC, UF)
- Integración con SII para boletas/facturas
- Cumplimiento Ley 21.461 "Devuélveme Mi Casa"
- Análisis de mercado de arriendos

Marcos Legales:
- Ley 18.101: Arrendamiento de predios urbanos
- Ley 21.461: "Devuélveme Mi Casa" (procedimiento monitorio)
- DL 825: IVA en arriendos amoblados
- Ley 21.210: Reforma tributaria arriendos

Autor: DATAPOLIS SpA
Versión: 3.0.0
Última actualización: 2025
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoContrato(str, Enum):
    """Tipos de contrato de arriendo según legislación chilena"""
    PLAZO_FIJO = "plazo_fijo"                    # Duración determinada
    PLAZO_INDEFINIDO = "plazo_indefinido"        # Sin término definido
    TEMPORAL = "temporal"                         # Menos de 3 meses
    AMOBLADO = "amoblado"                        # Incluye mobiliario (afecto IVA)
    COMERCIAL = "comercial"                       # Uso comercial/oficinas
    ESTACIONAMIENTO = "estacionamiento"          # Solo estacionamiento
    BODEGA = "bodega"                            # Solo bodega
    HABITACION = "habitacion"                    # Pieza dentro de propiedad


class EstadoContrato(str, Enum):
    """Estados del ciclo de vida del contrato"""
    BORRADOR = "borrador"                        # En elaboración
    PENDIENTE_FIRMA = "pendiente_firma"          # Esperando firmas
    VIGENTE = "vigente"                          # Activo
    RENOVADO = "renovado"                        # Renovación automática
    TERMINADO_NORMAL = "terminado_normal"        # Fin plazo acordado
    TERMINADO_ANTICIPADO = "terminado_anticipado" # Término antes de plazo
    DESAHUCIO = "desahucio"                      # En proceso de término
    EN_MORA = "en_mora"                          # Arrendatario moroso
    DEMANDA_LEY21461 = "demanda_ley21461"       # Procedimiento monitorio
    LANZAMIENTO = "lanzamiento"                  # Orden de desalojo


class TipoReajuste(str, Enum):
    """Mecanismos de reajuste de renta"""
    SIN_REAJUSTE = "sin_reajuste"                # Monto fijo
    IPC = "ipc"                                   # Índice Precios Consumidor
    UF = "uf"                                     # Unidad de Fomento
    DOLAR = "dolar"                              # Dólar observado
    PORCENTAJE_FIJO = "porcentaje_fijo"          # % anual fijo
    MIXTO = "mixto"                              # Combinación


class TipoGarantia(str, Enum):
    """Tipos de garantía aceptados"""
    DEPOSITO_EFECTIVO = "deposito_efectivo"      # Dinero en custodia
    BOLETA_GARANTIA = "boleta_garantia"          # Boleta bancaria
    SEGURO_ARRIENDO = "seguro_arriendo"          # Póliza de seguro
    AVAL_PERSONAL = "aval_personal"              # Persona natural garante
    AVAL_BANCARIO = "aval_bancario"              # Garantía bancaria
    PAGARE = "pagare"                            # Documento de pago
    HIPOTECA = "hipoteca"                        # Garantía real (comercial)


class EstadoGarantia(str, Enum):
    """Estado de la garantía"""
    VIGENTE = "vigente"
    EJECUTADA_PARCIAL = "ejecutada_parcial"
    EJECUTADA_TOTAL = "ejecutada_total"
    DEVUELTA = "devuelta"
    VENCIDA = "vencida"


class EstadoPago(str, Enum):
    """Estado de cobro de arriendo mensual"""
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    PAGADO_PARCIAL = "pagado_parcial"
    VENCIDO = "vencido"
    EN_COBRANZA = "en_cobranza"
    CASTIGADO = "castigado"


class MotivoTermino(str, Enum):
    """Causales de término de contrato"""
    # Término normal
    FIN_PLAZO = "fin_plazo"
    MUTUO_ACUERDO = "mutuo_acuerdo"
    
    # Término por arrendador (Ley 18.101 Art. 5)
    DESAHUCIO_ARRENDADOR = "desahucio_arrendador"
    NECESIDAD_ARRENDADOR = "necesidad_arrendador"      # Uso personal
    NO_PAGO_RENTA = "no_pago_renta"
    INCUMPLIMIENTO_ARRENDATARIO = "incumplimiento_arrendatario"
    SUBARRIENDO_NO_AUTORIZADO = "subarriendo_no_autorizado"
    
    # Término por arrendatario
    DESAHUCIO_ARRENDATARIO = "desahucio_arrendatario"
    VICIOS_PROPIEDAD = "vicios_propiedad"
    
    # Especiales
    ABANDONO = "abandono"
    FALLECIMIENTO = "fallecimiento"
    EXPROPIACION = "expropiacion"
    FUERZA_MAYOR = "fuerza_mayor"


class TipoNotificacion(str, Enum):
    """Tipos de notificación legal"""
    CARTA_CERTIFICADA = "carta_certificada"
    NOTIFICACION_JUDICIAL = "notificacion_judicial"
    NOTIFICACION_NOTARIAL = "notificacion_notarial"
    CORREO_ELECTRONICO = "correo_electronico"          # Si está pactado
    RECEPTOR_JUDICIAL = "receptor_judicial"


class EtapaLey21461(str, Enum):
    """Etapas del procedimiento monitorio Ley 21.461"""
    NO_APLICA = "no_aplica"
    PREPARACION = "preparacion"                        # Reuniendo antecedentes
    REQUERIMIENTO = "requerimiento"                    # 10 días para pagar/oponerse
    OPOSICION = "oposicion"                           # Arrendatario se opuso
    SENTENCIA = "sentencia"                           # Resolución judicial
    LANZAMIENTO = "lanzamiento"                       # Ejecución desalojo
    EJECUTADA = "ejecutada"                           # Proceso completado


class CategoriaPropiedad(str, Enum):
    """Categoría según rango de renta (para análisis)"""
    ECONOMICA = "economica"                           # < 10 UF
    MEDIA_BAJA = "media_baja"                         # 10-20 UF
    MEDIA = "media"                                   # 20-35 UF
    MEDIA_ALTA = "media_alta"                         # 35-50 UF
    PREMIUM = "premium"                               # 50-80 UF
    LUJO = "lujo"                                     # > 80 UF


# =============================================================================
# DATACLASSES - ESTRUCTURA DE DATOS
# =============================================================================

@dataclass
class PersonaArriendo:
    """Datos de persona (arrendador/arrendatario/aval)"""
    id: str = field(default_factory=lambda: str(uuid4()))
    rut: str = ""
    nombre_completo: str = ""
    email: str = ""
    telefono: str = ""
    direccion: str = ""
    comuna: str = ""
    
    # Datos adicionales
    nacionalidad: str = "Chilena"
    estado_civil: str = ""
    profesion: str = ""
    empleador: str = ""
    renta_mensual: Optional[Decimal] = None
    
    # Verificaciones
    dicom_verificado: bool = False
    dicom_score: Optional[int] = None
    dicom_fecha: Optional[datetime] = None
    referencias_verificadas: bool = False
    
    # Documentos
    cedula_identidad_url: str = ""
    liquidaciones_url: List[str] = field(default_factory=list)
    contrato_trabajo_url: str = ""


@dataclass
class PropiedadArriendo:
    """Datos de la propiedad en arriendo"""
    id: str = field(default_factory=lambda: str(uuid4()))
    expediente_id: Optional[str] = None              # Vínculo M00
    ficha_propiedad_id: Optional[str] = None         # Vínculo M01
    
    # Identificación
    rol_sii: str = ""
    direccion_completa: str = ""
    numero: str = ""
    departamento: Optional[str] = None
    comuna: str = ""
    region: str = "Metropolitana"
    
    # Características
    tipo: str = ""                                    # departamento, casa, etc.
    superficie_util_m2: Decimal = Decimal("0")
    dormitorios: int = 0
    banos: int = 0
    estacionamientos: int = 0
    bodega: bool = False
    bodega_m2: Decimal = Decimal("0")
    piso: Optional[int] = None
    orientacion: str = ""
    
    # Estado
    amoblado: bool = False
    inventario_amoblado: List[Dict[str, Any]] = field(default_factory=list)
    estado_conservacion: str = "bueno"
    ultima_remodelacion: Optional[date] = None
    
    # Gastos asociados
    gasto_comun_uf: Decimal = Decimal("0")
    contribuciones_semestral_uf: Decimal = Decimal("0")
    
    # Valorización
    valor_comercial_uf: Decimal = Decimal("0")
    avaluo_fiscal_uf: Decimal = Decimal("0")
    fecha_ultima_tasacion: Optional[date] = None


@dataclass
class Garantia:
    """Garantía del contrato de arriendo"""
    id: str = field(default_factory=lambda: str(uuid4()))
    contrato_id: str = ""
    
    tipo: TipoGarantia = TipoGarantia.DEPOSITO_EFECTIVO
    monto_uf: Decimal = Decimal("0")
    monto_pesos: Decimal = Decimal("0")
    fecha_constitucion: date = field(default_factory=date.today)
    fecha_vencimiento: Optional[date] = None
    estado: EstadoGarantia = EstadoGarantia.VIGENTE
    
    # Detalles según tipo
    banco: str = ""                                   # Para boleta/aval bancario
    numero_documento: str = ""                        # Boleta/pagaré
    aval_rut: str = ""                               # Para aval personal
    aval_nombre: str = ""
    poliza_numero: str = ""                          # Para seguro
    aseguradora: str = ""
    
    # Devolución
    fecha_devolucion: Optional[date] = None
    monto_devuelto: Decimal = Decimal("0")
    descuentos_aplicados: List[Dict[str, Any]] = field(default_factory=list)
    
    # Documentos
    documento_url: str = ""
    acta_devolucion_url: str = ""


@dataclass
class ConfiguracionReajuste:
    """Configuración de reajuste de renta"""
    tipo: TipoReajuste = TipoReajuste.IPC
    periodicidad_meses: int = 12                      # Cada cuánto se reajusta
    porcentaje_fijo_anual: Decimal = Decimal("0")    # Si es porcentaje fijo
    tope_reajuste_anual: Optional[Decimal] = None    # Límite máximo
    piso_reajuste_anual: Optional[Decimal] = None    # Mínimo garantizado
    fecha_ultimo_reajuste: Optional[date] = None
    indice_base: Decimal = Decimal("0")              # IPC o UF base


@dataclass
class CobroArriendo:
    """Cobro mensual de arriendo"""
    id: str = field(default_factory=lambda: str(uuid4()))
    contrato_id: str = ""
    
    # Período
    periodo: str = ""                                 # YYYY-MM
    fecha_emision: date = field(default_factory=date.today)
    fecha_vencimiento: date = field(default_factory=date.today)
    
    # Montos
    renta_base_uf: Decimal = Decimal("0")
    renta_base_pesos: Decimal = Decimal("0")
    gasto_comun_uf: Decimal = Decimal("0")
    gasto_comun_pesos: Decimal = Decimal("0")
    servicios_basicos: Decimal = Decimal("0")        # Si están incluidos
    otros_cobros: Decimal = Decimal("0")
    descuentos: Decimal = Decimal("0")
    
    # IVA (arriendos amoblados)
    afecto_iva: bool = False
    iva_monto: Decimal = Decimal("0")
    
    # Total
    total_cobro: Decimal = Decimal("0")
    
    # Estado y pago
    estado: EstadoPago = EstadoPago.PENDIENTE
    fecha_pago: Optional[date] = None
    monto_pagado: Decimal = Decimal("0")
    medio_pago: str = ""
    comprobante_pago: str = ""
    
    # Mora
    dias_mora: int = 0
    interes_mora: Decimal = Decimal("0")
    multa_atraso: Decimal = Decimal("0")
    
    # Documentos tributarios
    boleta_numero: str = ""
    boleta_url: str = ""
    factura_numero: str = ""
    factura_url: str = ""


@dataclass
class ProcesoLey21461:
    """Seguimiento procedimiento monitorio Ley 21.461"""
    id: str = field(default_factory=lambda: str(uuid4()))
    contrato_id: str = ""
    
    etapa: EtapaLey21461 = EtapaLey21461.NO_APLICA
    fecha_inicio: Optional[date] = None
    
    # Antecedentes
    meses_mora: int = 0
    monto_adeudado_uf: Decimal = Decimal("0")
    monto_adeudado_pesos: Decimal = Decimal("0")
    
    # Requerimiento judicial
    tribunal: str = ""
    rol_causa: str = ""
    fecha_presentacion: Optional[date] = None
    fecha_notificacion: Optional[date] = None
    plazo_vence: Optional[date] = None               # 10 días hábiles
    
    # Resolución
    hubo_oposicion: bool = False
    fecha_oposicion: Optional[date] = None
    motivo_oposicion: str = ""
    fecha_sentencia: Optional[date] = None
    sentencia_favorable: Optional[bool] = None
    
    # Lanzamiento
    fecha_lanzamiento_programada: Optional[date] = None
    fecha_lanzamiento_ejecutada: Optional[date] = None
    receptor_judicial: str = ""
    carabineros_asistieron: bool = False
    
    # Costas
    costas_judiciales: Decimal = Decimal("0")
    honorarios_abogado: Decimal = Decimal("0")
    
    # Documentos
    documentos: List[Dict[str, Any]] = field(default_factory=list)
    observaciones: str = ""


@dataclass
class HistorialContrato:
    """Registro de eventos del contrato"""
    id: str = field(default_factory=lambda: str(uuid4()))
    contrato_id: str = ""
    fecha: datetime = field(default_factory=datetime.now)
    tipo_evento: str = ""
    descripcion: str = ""
    usuario: str = ""
    datos_adicionales: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalisisRentabilidad:
    """Análisis de rentabilidad del arriendo"""
    propiedad_id: str = ""
    fecha_calculo: date = field(default_factory=date.today)
    
    # Valores base
    valor_propiedad_uf: Decimal = Decimal("0")
    renta_mensual_uf: Decimal = Decimal("0")
    
    # Ingresos anuales
    ingreso_bruto_anual_uf: Decimal = Decimal("0")   # Renta × 12
    vacancia_estimada_pct: Decimal = Decimal("5")    # % desocupación
    ingreso_efectivo_anual_uf: Decimal = Decimal("0")
    
    # Gastos anuales
    contribuciones_uf: Decimal = Decimal("0")
    seguros_uf: Decimal = Decimal("0")
    mantenciones_uf: Decimal = Decimal("0")          # 1% valor propiedad
    administracion_uf: Decimal = Decimal("0")        # 8-10% renta
    gastos_comunes_uf: Decimal = Decimal("0")        # Si los paga propietario
    otros_gastos_uf: Decimal = Decimal("0")
    total_gastos_uf: Decimal = Decimal("0")
    
    # Rentabilidades
    ingreso_neto_anual_uf: Decimal = Decimal("0")
    cap_rate_bruto: Decimal = Decimal("0")           # Rent bruta / Valor
    cap_rate_neto: Decimal = Decimal("0")            # Rent neta / Valor
    
    # Proyección
    proyeccion_5_anos: List[Dict[str, Any]] = field(default_factory=list)
    tir_estimada: Decimal = Decimal("0")
    van_estimado_uf: Decimal = Decimal("0")
    payback_anos: Decimal = Decimal("0")
    
    # Comparación mercado
    cap_rate_mercado_zona: Decimal = Decimal("0")
    diferencial_mercado: Decimal = Decimal("0")
    recomendacion: str = ""


@dataclass
class ContratoArriendo:
    """Contrato de arriendo completo"""
    id: str = field(default_factory=lambda: str(uuid4()))
    codigo: str = ""                                  # ARR-YYYY-NNNNNN
    
    # Tipo y estado
    tipo: TipoContrato = TipoContrato.PLAZO_FIJO
    estado: EstadoContrato = EstadoContrato.BORRADOR
    
    # Partes
    arrendador: PersonaArriendo = field(default_factory=PersonaArriendo)
    arrendatario: PersonaArriendo = field(default_factory=PersonaArriendo)
    codeudor: Optional[PersonaArriendo] = None
    
    # Propiedad
    propiedad: PropiedadArriendo = field(default_factory=PropiedadArriendo)
    
    # Fechas
    fecha_firma: Optional[date] = None
    fecha_inicio: date = field(default_factory=date.today)
    fecha_termino: Optional[date] = None              # None si indefinido
    duracion_meses: Optional[int] = None
    renovacion_automatica: bool = True
    preaviso_dias: int = 60                           # Ley 18.101: 2 meses
    
    # Renta
    renta_mensual_uf: Decimal = Decimal("0")
    renta_mensual_pesos: Decimal = Decimal("0")
    dia_pago: int = 5                                 # Día del mes
    
    # Reajuste
    reajuste: ConfiguracionReajuste = field(default_factory=ConfiguracionReajuste)
    
    # Garantía
    garantia: Optional[Garantia] = None
    meses_garantia: int = 1                           # Típico: 1 mes
    
    # IVA (arriendos amoblados > 100 UF anuales o comerciales)
    afecto_iva: bool = False
    
    # Gastos comunes
    gastos_comunes_incluidos: bool = False
    gasto_comun_mensual_uf: Decimal = Decimal("0")
    
    # Servicios
    servicios_incluidos: List[str] = field(default_factory=list)
    # ej: ["agua", "gas", "electricidad", "internet"]
    
    # Cláusulas especiales
    permite_mascotas: bool = False
    permite_subarriendo: bool = False
    uso_exclusivo: str = "habitacional"               # habitacional, comercial, mixto
    restricciones: List[str] = field(default_factory=list)
    clausulas_adicionales: str = ""
    
    # Documentos
    contrato_pdf_url: str = ""
    anexos_urls: List[str] = field(default_factory=list)
    inventario_url: str = ""
    acta_entrega_url: str = ""
    
    # Estado de cuenta
    cobros: List[CobroArriendo] = field(default_factory=list)
    saldo_favor: Decimal = Decimal("0")
    saldo_deuda: Decimal = Decimal("0")
    meses_mora: int = 0
    
    # Proceso legal
    proceso_ley21461: Optional[ProcesoLey21461] = None
    
    # Término
    motivo_termino: Optional[MotivoTermino] = None
    fecha_termino_real: Optional[date] = None
    acta_devolucion_url: str = ""
    
    # Auditoría
    historial: List[HistorialContrato] = field(default_factory=list)
    creado_en: datetime = field(default_factory=datetime.now)
    actualizado_en: datetime = field(default_factory=datetime.now)
    creado_por: str = ""
    version: int = 1


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class ArriendosService:
    """
    Servicio de Gestión de Arriendos M05.
    
    Funcionalidades:
    - CRUD de contratos de arriendo
    - Gestión de cobros y pagos
    - Cálculo de reajustes automáticos
    - Seguimiento de morosidad
    - Procedimiento Ley 21.461
    - Análisis de rentabilidad
    - Reportes y estadísticas
    """
    
    def __init__(self):
        self._contratos: Dict[str, ContratoArriendo] = {}
        self._propiedades: Dict[str, PropiedadArriendo] = {}
        self._contador_contratos = 0
        self._uf_actual = Decimal("38500.00")  # Mock UF
        self._ipc_actual = Decimal("4.5")      # Mock IPC anual %
        
        logger.info("ArriendosService M05 inicializado")
    
    # =========================================================================
    # GESTIÓN DE CONTRATOS
    # =========================================================================
    
    async def crear_contrato(
        self,
        tipo: TipoContrato,
        arrendador: PersonaArriendo,
        arrendatario: PersonaArriendo,
        propiedad: PropiedadArriendo,
        renta_mensual_uf: Decimal,
        fecha_inicio: date,
        duracion_meses: Optional[int] = 12,
        reajuste: Optional[ConfiguracionReajuste] = None,
        garantia_meses: int = 1,
        tipo_garantia: TipoGarantia = TipoGarantia.DEPOSITO_EFECTIVO,
        dia_pago: int = 5,
        usuario: str = "system"
    ) -> ContratoArriendo:
        """
        Crear nuevo contrato de arriendo.
        
        Args:
            tipo: Tipo de contrato (plazo_fijo, indefinido, etc.)
            arrendador: Datos del arrendador
            arrendatario: Datos del arrendatario
            propiedad: Datos de la propiedad
            renta_mensual_uf: Renta en UF
            fecha_inicio: Fecha inicio arriendo
            duracion_meses: Duración (None si indefinido)
            reajuste: Configuración de reajuste
            garantia_meses: Meses de garantía
            tipo_garantia: Tipo de garantía
            dia_pago: Día del mes para pago
            usuario: Usuario que crea
            
        Returns:
            ContratoArriendo creado
        """
        # Generar código único
        self._contador_contratos += 1
        year = datetime.now().year
        codigo = f"ARR-{year}-{self._contador_contratos:06d}"
        
        # Calcular fecha término si es plazo fijo
        fecha_termino = None
        if tipo == TipoContrato.PLAZO_FIJO and duracion_meses:
            fecha_termino = fecha_inicio + timedelta(days=duracion_meses * 30)
        
        # Configurar reajuste por defecto
        if reajuste is None:
            reajuste = ConfiguracionReajuste(
                tipo=TipoReajuste.IPC,
                periodicidad_meses=12,
                fecha_ultimo_reajuste=fecha_inicio,
                indice_base=self._ipc_actual
            )
        
        # Determinar si afecto a IVA
        # Arriendos amoblados > 100 UF anuales o comerciales
        afecto_iva = (
            tipo == TipoContrato.AMOBLADO and renta_mensual_uf * 12 > 100
        ) or tipo == TipoContrato.COMERCIAL
        
        # Crear contrato
        contrato = ContratoArriendo(
            codigo=codigo,
            tipo=tipo,
            estado=EstadoContrato.BORRADOR,
            arrendador=arrendador,
            arrendatario=arrendatario,
            propiedad=propiedad,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            duracion_meses=duracion_meses,
            renta_mensual_uf=renta_mensual_uf,
            renta_mensual_pesos=renta_mensual_uf * self._uf_actual,
            dia_pago=dia_pago,
            reajuste=reajuste,
            meses_garantia=garantia_meses,
            afecto_iva=afecto_iva,
            creado_por=usuario
        )
        
        # Crear garantía
        if garantia_meses > 0:
            monto_garantia_uf = renta_mensual_uf * garantia_meses
            contrato.garantia = Garantia(
                contrato_id=contrato.id,
                tipo=tipo_garantia,
                monto_uf=monto_garantia_uf,
                monto_pesos=monto_garantia_uf * self._uf_actual,
                fecha_constitucion=fecha_inicio
            )
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="creacion",
            descripcion=f"Contrato {codigo} creado",
            usuario=usuario,
            datos_adicionales={
                "tipo": tipo.value,
                "renta_uf": str(renta_mensual_uf),
                "duracion_meses": duracion_meses
            }
        ))
        
        # Guardar
        self._contratos[contrato.id] = contrato
        
        logger.info(f"Contrato {codigo} creado - Renta: {renta_mensual_uf} UF")
        
        return contrato
    
    async def obtener_contrato(self, contrato_id: str) -> Optional[ContratoArriendo]:
        """Obtener contrato por ID o código"""
        # Buscar por ID
        if contrato_id in self._contratos:
            return self._contratos[contrato_id]
        
        # Buscar por código
        for contrato in self._contratos.values():
            if contrato.codigo == contrato_id:
                return contrato
        
        return None
    
    async def listar_contratos(
        self,
        arrendador_rut: Optional[str] = None,
        arrendatario_rut: Optional[str] = None,
        estado: Optional[EstadoContrato] = None,
        comuna: Optional[str] = None,
        tipo: Optional[TipoContrato] = None,
        solo_morosos: bool = False,
        pagina: int = 1,
        por_pagina: int = 20
    ) -> Tuple[List[ContratoArriendo], int]:
        """
        Listar contratos con filtros.
        
        Returns:
            Tupla (lista_contratos, total)
        """
        resultados = list(self._contratos.values())
        
        # Aplicar filtros
        if arrendador_rut:
            resultados = [c for c in resultados 
                         if c.arrendador.rut == arrendador_rut]
        
        if arrendatario_rut:
            resultados = [c for c in resultados 
                         if c.arrendatario.rut == arrendatario_rut]
        
        if estado:
            resultados = [c for c in resultados if c.estado == estado]
        
        if comuna:
            resultados = [c for c in resultados 
                         if c.propiedad.comuna.lower() == comuna.lower()]
        
        if tipo:
            resultados = [c for c in resultados if c.tipo == tipo]
        
        if solo_morosos:
            resultados = [c for c in resultados if c.meses_mora > 0]
        
        total = len(resultados)
        
        # Paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        resultados = resultados[inicio:fin]
        
        return resultados, total
    
    async def actualizar_estado_contrato(
        self,
        contrato_id: str,
        nuevo_estado: EstadoContrato,
        motivo: Optional[str] = None,
        usuario: str = "system"
    ) -> ContratoArriendo:
        """Cambiar estado del contrato"""
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato:
            raise ValueError(f"Contrato {contrato_id} no encontrado")
        
        estado_anterior = contrato.estado
        contrato.estado = nuevo_estado
        contrato.actualizado_en = datetime.now()
        contrato.version += 1
        
        # Acciones según nuevo estado
        if nuevo_estado == EstadoContrato.VIGENTE and not contrato.fecha_firma:
            contrato.fecha_firma = date.today()
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="cambio_estado",
            descripcion=f"Estado cambió de {estado_anterior.value} a {nuevo_estado.value}",
            usuario=usuario,
            datos_adicionales={
                "estado_anterior": estado_anterior.value,
                "estado_nuevo": nuevo_estado.value,
                "motivo": motivo
            }
        ))
        
        logger.info(f"Contrato {contrato.codigo}: {estado_anterior.value} -> {nuevo_estado.value}")
        
        return contrato
    
    async def terminar_contrato(
        self,
        contrato_id: str,
        motivo: MotivoTermino,
        fecha_termino: date,
        observaciones: str = "",
        usuario: str = "system"
    ) -> ContratoArriendo:
        """
        Terminar contrato de arriendo.
        
        Gestiona:
        - Cambio de estado
        - Devolución de garantía
        - Liquidación final
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato:
            raise ValueError(f"Contrato {contrato_id} no encontrado")
        
        # Determinar tipo de término
        if motivo in [MotivoTermino.FIN_PLAZO, MotivoTermino.MUTUO_ACUERDO]:
            nuevo_estado = EstadoContrato.TERMINADO_NORMAL
        else:
            nuevo_estado = EstadoContrato.TERMINADO_ANTICIPADO
        
        contrato.estado = nuevo_estado
        contrato.motivo_termino = motivo
        contrato.fecha_termino_real = fecha_termino
        contrato.actualizado_en = datetime.now()
        contrato.version += 1
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="termino",
            descripcion=f"Contrato terminado por {motivo.value}",
            usuario=usuario,
            datos_adicionales={
                "motivo": motivo.value,
                "fecha_termino": fecha_termino.isoformat(),
                "observaciones": observaciones
            }
        ))
        
        logger.info(f"Contrato {contrato.codigo} terminado: {motivo.value}")
        
        return contrato
    
    # =========================================================================
    # GESTIÓN DE COBROS Y PAGOS
    # =========================================================================
    
    async def emitir_cobro_mensual(
        self,
        contrato_id: str,
        periodo: str,  # YYYY-MM
        cobros_adicionales: Optional[Dict[str, Decimal]] = None
    ) -> CobroArriendo:
        """
        Emitir cobro mensual de arriendo.
        
        Args:
            contrato_id: ID del contrato
            periodo: Período en formato YYYY-MM
            cobros_adicionales: Cobros extra (reparaciones, servicios, etc.)
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato:
            raise ValueError(f"Contrato {contrato_id} no encontrado")
        
        # Verificar si ya existe cobro para el período
        for cobro in contrato.cobros:
            if cobro.periodo == periodo:
                raise ValueError(f"Ya existe cobro para período {periodo}")
        
        # Calcular fechas
        year, month = map(int, periodo.split("-"))
        fecha_emision = date(year, month, 1)
        fecha_vencimiento = date(year, month, contrato.dia_pago)
        
        # Calcular renta (verificar si hay reajuste pendiente)
        renta_uf = await self._calcular_renta_con_reajuste(contrato, fecha_emision)
        renta_pesos = renta_uf * self._uf_actual
        
        # Gastos comunes
        gasto_comun_uf = Decimal("0")
        gasto_comun_pesos = Decimal("0")
        if not contrato.gastos_comunes_incluidos:
            gasto_comun_uf = contrato.gasto_comun_mensual_uf
            gasto_comun_pesos = gasto_comun_uf * self._uf_actual
        
        # Otros cobros
        otros = Decimal("0")
        if cobros_adicionales:
            otros = sum(cobros_adicionales.values())
        
        # Calcular IVA si corresponde
        iva = Decimal("0")
        if contrato.afecto_iva:
            base_iva = renta_pesos + otros
            iva = (base_iva * Decimal("0.19")).quantize(Decimal("1"), ROUND_HALF_UP)
        
        # Total
        total = renta_pesos + gasto_comun_pesos + otros + iva
        
        # Crear cobro
        cobro = CobroArriendo(
            contrato_id=contrato.id,
            periodo=periodo,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            renta_base_uf=renta_uf,
            renta_base_pesos=renta_pesos,
            gasto_comun_uf=gasto_comun_uf,
            gasto_comun_pesos=gasto_comun_pesos,
            otros_cobros=otros,
            afecto_iva=contrato.afecto_iva,
            iva_monto=iva,
            total_cobro=total
        )
        
        contrato.cobros.append(cobro)
        contrato.actualizado_en = datetime.now()
        
        logger.info(f"Cobro emitido: {contrato.codigo} período {periodo} - ${total:,.0f}")
        
        return cobro
    
    async def registrar_pago(
        self,
        contrato_id: str,
        cobro_id: str,
        monto: Decimal,
        fecha_pago: date,
        medio_pago: str,
        comprobante: str = ""
    ) -> CobroArriendo:
        """
        Registrar pago de arriendo.
        
        Actualiza estado del cobro y calcula mora si aplica.
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato:
            raise ValueError(f"Contrato {contrato_id} no encontrado")
        
        # Buscar cobro
        cobro = None
        for c in contrato.cobros:
            if c.id == cobro_id:
                cobro = c
                break
        
        if not cobro:
            raise ValueError(f"Cobro {cobro_id} no encontrado")
        
        # Calcular mora si pago atrasado
        if fecha_pago > cobro.fecha_vencimiento:
            dias_mora = (fecha_pago - cobro.fecha_vencimiento).days
            # Interés mora: máximo legal 1.5% mensual
            tasa_diaria = Decimal("0.015") / 30
            interes = cobro.total_cobro * tasa_diaria * dias_mora
            cobro.dias_mora = dias_mora
            cobro.interes_mora = interes.quantize(Decimal("1"), ROUND_HALF_UP)
        
        # Registrar pago
        cobro.fecha_pago = fecha_pago
        cobro.monto_pagado = monto
        cobro.medio_pago = medio_pago
        cobro.comprobante_pago = comprobante
        
        # Determinar estado
        total_con_mora = cobro.total_cobro + cobro.interes_mora
        if monto >= total_con_mora:
            cobro.estado = EstadoPago.PAGADO
        elif monto > 0:
            cobro.estado = EstadoPago.PAGADO_PARCIAL
        
        # Actualizar morosidad del contrato
        await self._actualizar_morosidad_contrato(contrato)
        
        contrato.actualizado_en = datetime.now()
        
        logger.info(f"Pago registrado: {contrato.codigo} período {cobro.periodo} - ${monto:,.0f}")
        
        return cobro
    
    async def _calcular_renta_con_reajuste(
        self,
        contrato: ContratoArriendo,
        fecha: date
    ) -> Decimal:
        """
        Calcular renta aplicando reajuste si corresponde.
        """
        if contrato.reajuste.tipo == TipoReajuste.SIN_REAJUSTE:
            return contrato.renta_mensual_uf
        
        # Verificar si toca reajuste
        ultimo_reajuste = contrato.reajuste.fecha_ultimo_reajuste or contrato.fecha_inicio
        meses_desde_reajuste = (
            (fecha.year - ultimo_reajuste.year) * 12 + 
            (fecha.month - ultimo_reajuste.month)
        )
        
        if meses_desde_reajuste < contrato.reajuste.periodicidad_meses:
            return contrato.renta_mensual_uf
        
        # Calcular reajuste
        renta_actual = contrato.renta_mensual_uf
        
        if contrato.reajuste.tipo == TipoReajuste.IPC:
            # Aplicar variación IPC
            factor = 1 + (self._ipc_actual / 100)
            renta_nueva = renta_actual * Decimal(str(factor))
            
        elif contrato.reajuste.tipo == TipoReajuste.UF:
            # En UF no hay reajuste, ya está en UF
            renta_nueva = renta_actual
            
        elif contrato.reajuste.tipo == TipoReajuste.PORCENTAJE_FIJO:
            factor = 1 + (contrato.reajuste.porcentaje_fijo_anual / 100)
            renta_nueva = renta_actual * factor
            
        else:
            renta_nueva = renta_actual
        
        # Aplicar topes
        if contrato.reajuste.tope_reajuste_anual:
            max_renta = renta_actual * (1 + contrato.reajuste.tope_reajuste_anual / 100)
            renta_nueva = min(renta_nueva, max_renta)
        
        if contrato.reajuste.piso_reajuste_anual:
            min_renta = renta_actual * (1 + contrato.reajuste.piso_reajuste_anual / 100)
            renta_nueva = max(renta_nueva, min_renta)
        
        # Actualizar fecha reajuste
        contrato.reajuste.fecha_ultimo_reajuste = fecha
        contrato.renta_mensual_uf = renta_nueva.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        logger.info(f"Reajuste aplicado {contrato.codigo}: {renta_actual} -> {renta_nueva} UF")
        
        return contrato.renta_mensual_uf
    
    async def _actualizar_morosidad_contrato(self, contrato: ContratoArriendo):
        """Actualizar estado de morosidad del contrato"""
        hoy = date.today()
        meses_mora = 0
        saldo_deuda = Decimal("0")
        
        for cobro in contrato.cobros:
            if cobro.estado in [EstadoPago.PENDIENTE, EstadoPago.PAGADO_PARCIAL, EstadoPago.VENCIDO]:
                if cobro.fecha_vencimiento < hoy:
                    cobro.estado = EstadoPago.VENCIDO
                    cobro.dias_mora = (hoy - cobro.fecha_vencimiento).days
                    meses_mora += 1
                    deuda = cobro.total_cobro - cobro.monto_pagado
                    saldo_deuda += deuda
        
        contrato.meses_mora = meses_mora
        contrato.saldo_deuda = saldo_deuda
        
        # Cambiar estado si hay mora grave
        if meses_mora >= 2 and contrato.estado == EstadoContrato.VIGENTE:
            contrato.estado = EstadoContrato.EN_MORA
    
    # =========================================================================
    # PROCEDIMIENTO LEY 21.461 "DEVUÉLVEME MI CASA"
    # =========================================================================
    
    async def iniciar_proceso_ley21461(
        self,
        contrato_id: str,
        usuario: str = "system"
    ) -> ProcesoLey21461:
        """
        Iniciar procedimiento monitorio Ley 21.461.
        
        Requisitos:
        - Mora de al menos 1 período completo
        - Contrato escrito
        - Propiedad destinada a habitación
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato:
            raise ValueError(f"Contrato {contrato_id} no encontrado")
        
        # Verificar requisitos
        if contrato.meses_mora < 1:
            raise ValueError("Se requiere al menos 1 mes de mora")
        
        if contrato.tipo == TipoContrato.COMERCIAL:
            raise ValueError("Ley 21.461 solo aplica a arriendos habitacionales")
        
        # Calcular deuda total
        deuda_total = Decimal("0")
        for cobro in contrato.cobros:
            if cobro.estado in [EstadoPago.VENCIDO, EstadoPago.PAGADO_PARCIAL]:
                deuda_total += cobro.total_cobro - cobro.monto_pagado + cobro.interes_mora
        
        # Crear proceso
        proceso = ProcesoLey21461(
            contrato_id=contrato.id,
            etapa=EtapaLey21461.PREPARACION,
            fecha_inicio=date.today(),
            meses_mora=contrato.meses_mora,
            monto_adeudado_pesos=deuda_total,
            monto_adeudado_uf=(deuda_total / self._uf_actual).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
        )
        
        contrato.proceso_ley21461 = proceso
        contrato.estado = EstadoContrato.DEMANDA_LEY21461
        contrato.actualizado_en = datetime.now()
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="proceso_legal",
            descripcion="Inicio procedimiento monitorio Ley 21.461",
            usuario=usuario,
            datos_adicionales={
                "meses_mora": contrato.meses_mora,
                "monto_adeudado_pesos": str(deuda_total)
            }
        ))
        
        logger.info(f"Proceso Ley 21.461 iniciado: {contrato.codigo}")
        
        return proceso
    
    async def actualizar_proceso_ley21461(
        self,
        contrato_id: str,
        nueva_etapa: EtapaLey21461,
        datos: Dict[str, Any],
        usuario: str = "system"
    ) -> ProcesoLey21461:
        """
        Actualizar etapa del procedimiento.
        
        Args:
            contrato_id: ID del contrato
            nueva_etapa: Nueva etapa del proceso
            datos: Datos específicos de la etapa
                - REQUERIMIENTO: tribunal, rol_causa, fecha_notificacion
                - OPOSICION: hubo_oposicion, motivo_oposicion
                - SENTENCIA: sentencia_favorable, fecha_sentencia
                - LANZAMIENTO: fecha_programada, receptor_judicial
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato or not contrato.proceso_ley21461:
            raise ValueError("Contrato o proceso no encontrado")
        
        proceso = contrato.proceso_ley21461
        proceso.etapa = nueva_etapa
        
        # Actualizar según etapa
        if nueva_etapa == EtapaLey21461.REQUERIMIENTO:
            proceso.tribunal = datos.get("tribunal", "")
            proceso.rol_causa = datos.get("rol_causa", "")
            proceso.fecha_presentacion = datos.get("fecha_presentacion")
            proceso.fecha_notificacion = datos.get("fecha_notificacion")
            if proceso.fecha_notificacion:
                # Plazo: 10 días hábiles para pagar u oponerse
                proceso.plazo_vence = proceso.fecha_notificacion + timedelta(days=14)
        
        elif nueva_etapa == EtapaLey21461.OPOSICION:
            proceso.hubo_oposicion = datos.get("hubo_oposicion", False)
            proceso.fecha_oposicion = datos.get("fecha_oposicion")
            proceso.motivo_oposicion = datos.get("motivo_oposicion", "")
        
        elif nueva_etapa == EtapaLey21461.SENTENCIA:
            proceso.fecha_sentencia = datos.get("fecha_sentencia")
            proceso.sentencia_favorable = datos.get("sentencia_favorable")
        
        elif nueva_etapa == EtapaLey21461.LANZAMIENTO:
            proceso.fecha_lanzamiento_programada = datos.get("fecha_programada")
            proceso.receptor_judicial = datos.get("receptor_judicial", "")
            contrato.estado = EstadoContrato.LANZAMIENTO
        
        elif nueva_etapa == EtapaLey21461.EJECUTADA:
            proceso.fecha_lanzamiento_ejecutada = datos.get("fecha_ejecutada")
            proceso.carabineros_asistieron = datos.get("carabineros", False)
            proceso.costas_judiciales = datos.get("costas", Decimal("0"))
            proceso.honorarios_abogado = datos.get("honorarios", Decimal("0"))
        
        contrato.actualizado_en = datetime.now()
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="proceso_legal",
            descripcion=f"Proceso Ley 21.461: avance a etapa {nueva_etapa.value}",
            usuario=usuario,
            datos_adicionales=datos
        ))
        
        logger.info(f"Proceso {contrato.codigo} actualizado: {nueva_etapa.value}")
        
        return proceso
    
    # =========================================================================
    # GESTIÓN DE GARANTÍAS
    # =========================================================================
    
    async def devolver_garantia(
        self,
        contrato_id: str,
        descuentos: Optional[List[Dict[str, Any]]] = None,
        observaciones: str = "",
        usuario: str = "system"
    ) -> Garantia:
        """
        Procesar devolución de garantía.
        
        Args:
            contrato_id: ID del contrato
            descuentos: Lista de descuentos [{concepto, monto}]
            observaciones: Observaciones de la devolución
        """
        contrato = await self.obtener_contrato(contrato_id)
        if not contrato or not contrato.garantia:
            raise ValueError("Contrato o garantía no encontrada")
        
        garantia = contrato.garantia
        
        # Verificar que el contrato esté terminado
        if contrato.estado not in [
            EstadoContrato.TERMINADO_NORMAL,
            EstadoContrato.TERMINADO_ANTICIPADO
        ]:
            raise ValueError("El contrato debe estar terminado para devolver garantía")
        
        # Calcular descuentos
        total_descuentos = Decimal("0")
        if descuentos:
            for d in descuentos:
                total_descuentos += Decimal(str(d.get("monto", 0)))
            garantia.descuentos_aplicados = descuentos
        
        # Agregar deuda pendiente a descuentos
        if contrato.saldo_deuda > 0:
            garantia.descuentos_aplicados.append({
                "concepto": "Deuda pendiente arriendos",
                "monto": str(contrato.saldo_deuda)
            })
            total_descuentos += contrato.saldo_deuda
        
        # Calcular monto a devolver
        monto_devolver = garantia.monto_pesos - total_descuentos
        monto_devolver = max(monto_devolver, Decimal("0"))  # No puede ser negativo
        
        garantia.monto_devuelto = monto_devolver
        garantia.fecha_devolucion = date.today()
        
        # Determinar estado
        if total_descuentos >= garantia.monto_pesos:
            garantia.estado = EstadoGarantia.EJECUTADA_TOTAL
        elif total_descuentos > 0:
            garantia.estado = EstadoGarantia.EJECUTADA_PARCIAL
        else:
            garantia.estado = EstadoGarantia.DEVUELTA
        
        # Registrar evento
        contrato.historial.append(HistorialContrato(
            contrato_id=contrato.id,
            tipo_evento="garantia",
            descripcion=f"Garantía procesada: devuelto ${monto_devolver:,.0f}",
            usuario=usuario,
            datos_adicionales={
                "monto_original": str(garantia.monto_pesos),
                "descuentos": str(total_descuentos),
                "monto_devuelto": str(monto_devolver),
                "observaciones": observaciones
            }
        ))
        
        contrato.actualizado_en = datetime.now()
        
        logger.info(f"Garantía devuelta {contrato.codigo}: ${monto_devolver:,.0f}")
        
        return garantia
    
    # =========================================================================
    # ANÁLISIS DE RENTABILIDAD
    # =========================================================================
    
    async def calcular_rentabilidad(
        self,
        propiedad_id: str,
        renta_mensual_uf: Decimal,
        valor_propiedad_uf: Decimal,
        gastos_anuales: Optional[Dict[str, Decimal]] = None,
        vacancia_pct: Decimal = Decimal("5"),
        plusvalia_anual_pct: Decimal = Decimal("3")
    ) -> AnalisisRentabilidad:
        """
        Calcular análisis completo de rentabilidad.
        
        Args:
            propiedad_id: ID de la propiedad
            renta_mensual_uf: Renta mensual en UF
            valor_propiedad_uf: Valor de la propiedad en UF
            gastos_anuales: Gastos desglosados
            vacancia_pct: Porcentaje estimado de vacancia
            plusvalia_anual_pct: Plusvalía esperada
        """
        analisis = AnalisisRentabilidad(
            propiedad_id=propiedad_id,
            valor_propiedad_uf=valor_propiedad_uf,
            renta_mensual_uf=renta_mensual_uf
        )
        
        # Ingresos
        ingreso_bruto = renta_mensual_uf * 12
        analisis.ingreso_bruto_anual_uf = ingreso_bruto
        analisis.vacancia_estimada_pct = vacancia_pct
        analisis.ingreso_efectivo_anual_uf = ingreso_bruto * (1 - vacancia_pct / 100)
        
        # Gastos
        if gastos_anuales:
            analisis.contribuciones_uf = gastos_anuales.get("contribuciones", Decimal("0"))
            analisis.seguros_uf = gastos_anuales.get("seguros", Decimal("0"))
            analisis.mantenciones_uf = gastos_anuales.get("mantenciones", 
                valor_propiedad_uf * Decimal("0.01"))  # 1% default
            analisis.administracion_uf = gastos_anuales.get("administracion",
                ingreso_bruto * Decimal("0.08"))  # 8% default
            analisis.gastos_comunes_uf = gastos_anuales.get("gastos_comunes", Decimal("0"))
            analisis.otros_gastos_uf = gastos_anuales.get("otros", Decimal("0"))
        else:
            # Estimaciones por defecto
            analisis.contribuciones_uf = valor_propiedad_uf * Decimal("0.012")  # 1.2%
            analisis.seguros_uf = valor_propiedad_uf * Decimal("0.002")        # 0.2%
            analisis.mantenciones_uf = valor_propiedad_uf * Decimal("0.01")    # 1%
            analisis.administracion_uf = ingreso_bruto * Decimal("0.08")       # 8%
        
        analisis.total_gastos_uf = (
            analisis.contribuciones_uf +
            analisis.seguros_uf +
            analisis.mantenciones_uf +
            analisis.administracion_uf +
            analisis.gastos_comunes_uf +
            analisis.otros_gastos_uf
        )
        
        # Rentabilidades
        analisis.ingreso_neto_anual_uf = analisis.ingreso_efectivo_anual_uf - analisis.total_gastos_uf
        
        analisis.cap_rate_bruto = (
            (ingreso_bruto / valor_propiedad_uf) * 100
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        analisis.cap_rate_neto = (
            (analisis.ingreso_neto_anual_uf / valor_propiedad_uf) * 100
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        # Proyección 5 años
        valor_actual = valor_propiedad_uf
        renta_actual = renta_mensual_uf
        flujos = []
        
        for ano in range(1, 6):
            # Reajustar renta por IPC
            renta_actual = renta_actual * Decimal("1.045")  # 4.5% IPC
            ingreso_ano = renta_actual * 12 * (1 - vacancia_pct / 100)
            
            # Reajustar gastos
            gastos_ano = analisis.total_gastos_uf * (Decimal("1.045") ** ano)
            
            # Plusvalía
            valor_actual = valor_actual * (1 + plusvalia_anual_pct / 100)
            
            flujo = {
                "ano": ano,
                "renta_mensual_uf": float(renta_actual.quantize(Decimal("0.01"))),
                "ingreso_anual_uf": float(ingreso_ano.quantize(Decimal("0.01"))),
                "gastos_anuales_uf": float(gastos_ano.quantize(Decimal("0.01"))),
                "flujo_neto_uf": float((ingreso_ano - gastos_ano).quantize(Decimal("0.01"))),
                "valor_propiedad_uf": float(valor_actual.quantize(Decimal("0.01")))
            }
            flujos.append(flujo)
        
        analisis.proyeccion_5_anos = flujos
        
        # TIR y Payback simplificados
        flujo_neto_anual = float(analisis.ingreso_neto_anual_uf)
        inversion = float(valor_propiedad_uf)
        
        # Payback simple
        if flujo_neto_anual > 0:
            analisis.payback_anos = Decimal(str(inversion / flujo_neto_anual)).quantize(
                Decimal("0.1"), ROUND_HALF_UP
            )
        
        # TIR aproximada (considerando plusvalía)
        valor_final = float(flujos[-1]["valor_propiedad_uf"])
        flujo_total_5_anos = sum(f["flujo_neto_uf"] for f in flujos) + valor_final
        tir_aprox = ((flujo_total_5_anos / inversion) ** (1/5) - 1) * 100
        analisis.tir_estimada = Decimal(str(tir_aprox)).quantize(Decimal("0.01"))
        
        # Comparación mercado (mock)
        analisis.cap_rate_mercado_zona = Decimal("5.5")
        analisis.diferencial_mercado = analisis.cap_rate_neto - analisis.cap_rate_mercado_zona
        
        # Recomendación
        if analisis.cap_rate_neto > Decimal("6"):
            analisis.recomendacion = "Excelente rentabilidad, supera significativamente el mercado"
        elif analisis.cap_rate_neto > Decimal("5"):
            analisis.recomendacion = "Buena rentabilidad, en línea con el mercado"
        elif analisis.cap_rate_neto > Decimal("4"):
            analisis.recomendacion = "Rentabilidad moderada, evaluar opciones de optimización"
        else:
            analisis.recomendacion = "Rentabilidad baja, considerar ajuste de renta o venta"
        
        logger.info(f"Rentabilidad calculada: Cap Rate Neto {analisis.cap_rate_neto}%")
        
        return analisis
    
    # =========================================================================
    # REPORTES Y ESTADÍSTICAS
    # =========================================================================
    
    async def generar_reporte_cartera(
        self,
        arrendador_rut: Optional[str] = None,
        fecha_corte: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Generar reporte de cartera de arriendos.
        """
        if fecha_corte is None:
            fecha_corte = date.today()
        
        # Filtrar contratos
        contratos = list(self._contratos.values())
        if arrendador_rut:
            contratos = [c for c in contratos if c.arrendador.rut == arrendador_rut]
        
        # Estadísticas
        total_contratos = len(contratos)
        vigentes = [c for c in contratos if c.estado == EstadoContrato.VIGENTE]
        morosos = [c for c in contratos if c.meses_mora > 0]
        
        # Ingresos
        ingreso_mensual_total = sum(c.renta_mensual_uf for c in vigentes)
        ingreso_mensual_pesos = ingreso_mensual_total * self._uf_actual
        
        # Morosidad
        deuda_total = sum(c.saldo_deuda for c in morosos)
        
        # Distribución por tipo
        por_tipo = {}
        for c in contratos:
            tipo = c.tipo.value
            if tipo not in por_tipo:
                por_tipo[tipo] = {"cantidad": 0, "renta_uf": Decimal("0")}
            por_tipo[tipo]["cantidad"] += 1
            por_tipo[tipo]["renta_uf"] += c.renta_mensual_uf
        
        # Distribución por comuna
        por_comuna = {}
        for c in vigentes:
            comuna = c.propiedad.comuna
            if comuna not in por_comuna:
                por_comuna[comuna] = {"cantidad": 0, "renta_promedio_uf": Decimal("0")}
            por_comuna[comuna]["cantidad"] += 1
        
        for comuna in por_comuna:
            contratos_comuna = [c for c in vigentes if c.propiedad.comuna == comuna]
            if contratos_comuna:
                promedio = sum(c.renta_mensual_uf for c in contratos_comuna) / len(contratos_comuna)
                por_comuna[comuna]["renta_promedio_uf"] = promedio.quantize(Decimal("0.01"))
        
        return {
            "fecha_corte": fecha_corte.isoformat(),
            "resumen": {
                "total_contratos": total_contratos,
                "contratos_vigentes": len(vigentes),
                "contratos_morosos": len(morosos),
                "porcentaje_morosidad": (len(morosos) / len(vigentes) * 100) if vigentes else 0
            },
            "financiero": {
                "ingreso_mensual_uf": str(ingreso_mensual_total),
                "ingreso_mensual_pesos": str(ingreso_mensual_pesos),
                "ingreso_anual_proyectado_uf": str(ingreso_mensual_total * 12),
                "deuda_total_pesos": str(deuda_total),
                "deuda_total_uf": str((deuda_total / self._uf_actual).quantize(Decimal("0.01")))
            },
            "distribucion_tipo": {
                k: {"cantidad": v["cantidad"], "renta_uf": str(v["renta_uf"])}
                for k, v in por_tipo.items()
            },
            "distribucion_comuna": {
                k: {"cantidad": v["cantidad"], "renta_promedio_uf": str(v["renta_promedio_uf"])}
                for k, v in por_comuna.items()
            },
            "alertas": {
                "contratos_por_vencer_30_dias": len([
                    c for c in vigentes 
                    if c.fecha_termino and (c.fecha_termino - fecha_corte).days <= 30
                ]),
                "garantias_por_vencer": len([
                    c for c in vigentes 
                    if c.garantia and c.garantia.fecha_vencimiento 
                    and (c.garantia.fecha_vencimiento - fecha_corte).days <= 30
                ]),
                "procesos_legales_activos": len([
                    c for c in contratos 
                    if c.proceso_ley21461 
                    and c.proceso_ley21461.etapa not in [
                        EtapaLey21461.NO_APLICA, 
                        EtapaLey21461.EJECUTADA
                    ]
                ])
            }
        }
    
    async def obtener_estadisticas_mercado(
        self,
        comuna: str,
        tipo_propiedad: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas de mercado de arriendos.
        """
        # Mock de estadísticas de mercado
        return {
            "comuna": comuna,
            "tipo_propiedad": tipo_propiedad or "todos",
            "fecha_actualizacion": datetime.now().isoformat(),
            "indicadores": {
                "renta_promedio_uf": "25.5",
                "renta_mediana_uf": "23.0",
                "renta_m2_promedio_uf": "0.38",
                "variacion_anual_pct": "4.2",
                "oferta_activa": 1250,
                "dias_promedio_arriendo": 28,
                "tasa_vacancia_pct": "4.8"
            },
            "rangos_renta": {
                "economica": {"min_uf": "8", "max_uf": "15", "porcentaje": "15"},
                "media_baja": {"min_uf": "15", "max_uf": "25", "porcentaje": "35"},
                "media": {"min_uf": "25", "max_uf": "40", "porcentaje": "30"},
                "media_alta": {"min_uf": "40", "max_uf": "60", "porcentaje": "15"},
                "premium": {"min_uf": "60", "max_uf": "100", "porcentaje": "5"}
            },
            "cap_rate_zona": {
                "promedio": "5.2",
                "minimo": "3.8",
                "maximo": "7.5"
            }
        }


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_arriendos_service: Optional[ArriendosService] = None


def get_arriendos_service() -> ArriendosService:
    """Obtener instancia singleton del servicio"""
    global _arriendos_service
    if _arriendos_service is None:
        _arriendos_service = ArriendosService()
    return _arriendos_service


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def calcular_dias_habiles(fecha_inicio: date, dias: int) -> date:
    """Calcular fecha sumando días hábiles"""
    fecha = fecha_inicio
    dias_contados = 0
    
    while dias_contados < dias:
        fecha += timedelta(days=1)
        # Excluir sábados (5) y domingos (6)
        if fecha.weekday() < 5:
            dias_contados += 1
    
    return fecha


def validar_rut_chileno(rut: str) -> bool:
    """Validar RUT chileno"""
    rut = rut.replace(".", "").replace("-", "").upper()
    
    if len(rut) < 2:
        return False
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    try:
        cuerpo_num = int(cuerpo)
    except ValueError:
        return False
    
    # Calcular dígito verificador
    suma = 0
    multiplo = 2
    
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_esperado = "0"
    elif dv_calculado == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(dv_calculado)
    
    return dv == dv_esperado


def formatear_rut(rut: str) -> str:
    """Formatear RUT con puntos y guión"""
    rut = rut.replace(".", "").replace("-", "").upper()
    
    if len(rut) < 2:
        return rut
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    # Agregar puntos
    cuerpo_formateado = ""
    for i, digito in enumerate(reversed(cuerpo)):
        if i > 0 and i % 3 == 0:
            cuerpo_formateado = "." + cuerpo_formateado
        cuerpo_formateado = digito + cuerpo_formateado
    
    return f"{cuerpo_formateado}-{dv}"
