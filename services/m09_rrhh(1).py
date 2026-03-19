"""
DATAPOLIS v3.0 - Módulo M09: RRHH y Nóminas
===========================================
Gestión integral de recursos humanos según normativa chilena:
- Código del Trabajo (DFL 1)
- Ley 16.744 (Accidentes del Trabajo)
- AFC (Seguro de Cesantía)
- AFP, FONASA/Isapre
- Gratificación legal Art. 47-50

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoContrato(str, Enum):
    """Tipos de contrato según Código del Trabajo"""
    INDEFINIDO = "indefinido"
    PLAZO_FIJO = "plazo_fijo"
    POR_OBRA = "por_obra"
    PART_TIME = "part_time"
    HONORARIOS = "honorarios"
    APRENDIZAJE = "aprendizaje"


class EstadoTrabajador(str, Enum):
    """Estados del trabajador"""
    ACTIVO = "activo"
    LICENCIA_MEDICA = "licencia_medica"
    VACACIONES = "vacaciones"
    PERMISO = "permiso"
    SUSPENDIDO = "suspendido"
    DESPEDIDO = "despedido"
    RENUNCIA = "renuncia"
    JUBILADO = "jubilado"


class TipoJornada(str, Enum):
    """Tipos de jornada laboral"""
    COMPLETA = "completa"  # 45 hrs semanales
    PARCIAL = "parcial"    # < 30 hrs semanales
    EXCEPCIONAL = "excepcional"
    TURNOS = "turnos"
    TELETRABAJO = "teletrabajo"


class CausalDespido(str, Enum):
    """Causales de despido según Código del Trabajo"""
    MUTUO_ACUERDO = "mutuo_acuerdo"  # Art 159 N°1
    RENUNCIA = "renuncia"  # Art 159 N°2
    MUERTE = "muerte"  # Art 159 N°3
    VENCIMIENTO_PLAZO = "vencimiento_plazo"  # Art 159 N°4
    FIN_OBRA = "fin_obra"  # Art 159 N°5
    CASO_FORTUITO = "caso_fortuito"  # Art 159 N°6
    FALTA_PROBIDAD = "falta_probidad"  # Art 160 N°1
    ACOSO = "acoso"  # Art 160 N°1 letra b
    INJURIAS = "injurias"  # Art 160 N°1 letra c
    CONDUCTA_INMORAL = "conducta_inmoral"  # Art 160 N°1 letra d
    NEGOCIACIONES_PROHIBIDAS = "negociaciones_prohibidas"  # Art 160 N°2
    AUSENCIAS_INJUSTIFICADAS = "ausencias_injustificadas"  # Art 160 N°3
    ABANDONO = "abandono"  # Art 160 N°4
    SEGURIDAD = "seguridad"  # Art 160 N°5
    PERJUICIO_MATERIAL = "perjuicio_material"  # Art 160 N°6
    INCUMPLIMIENTO_GRAVE = "incumplimiento_grave"  # Art 160 N°7
    NECESIDADES_EMPRESA = "necesidades_empresa"  # Art 161
    DESAHUCIO = "desahucio"  # Art 161 inciso 2


class TipoHaber(str, Enum):
    """Tipos de haberes en liquidación"""
    SUELDO_BASE = "sueldo_base"
    GRATIFICACION = "gratificacion"
    BONO_PRODUCCION = "bono_produccion"
    BONO_RESPONSABILIDAD = "bono_responsabilidad"
    COLACION = "colacion"
    MOVILIZACION = "movilizacion"
    HORAS_EXTRA = "horas_extra"
    COMISIONES = "comisiones"
    AGUINALDO = "aguinaldo"
    VACACIONES = "vacaciones"
    OTRO_IMPONIBLE = "otro_imponible"
    OTRO_NO_IMPONIBLE = "otro_no_imponible"


class TipoDescuento(str, Enum):
    """Tipos de descuentos en liquidación"""
    AFP = "afp"
    SALUD = "salud"
    AFC = "afc"
    IMPUESTO_UNICO = "impuesto_unico"
    ANTICIPO = "anticipo"
    PRESTAMO = "prestamo"
    CUOTA_SINDICAL = "cuota_sindical"
    PENSION_ALIMENTICIA = "pension_alimenticia"
    OTRO_DESCUENTO = "otro_descuento"


class TipoAFP(str, Enum):
    """AFPs en Chile"""
    CAPITAL = "capital"
    CUPRUM = "cuprum"
    HABITAT = "habitat"
    MODELO = "modelo"
    PLANVITAL = "planvital"
    PROVIDA = "provida"
    UNO = "uno"


class TipoSalud(str, Enum):
    """Sistemas de salud"""
    FONASA = "fonasa"
    ISAPRE = "isapre"


# =============================================================================
# CONSTANTES PREVISIONALES 2026
# =============================================================================

# Topes imponibles (en UF)
TOPE_IMPONIBLE_AFP_UF = Decimal("81.6")
TOPE_IMPONIBLE_SALUD_UF = Decimal("81.6")
TOPE_IMPONIBLE_AFC_UF = Decimal("126.6")

# Tasas AFP (comisión + SIS) 2026
TASAS_AFP = {
    TipoAFP.CAPITAL: Decimal("11.44"),
    TipoAFP.CUPRUM: Decimal("11.44"),
    TipoAFP.HABITAT: Decimal("11.27"),
    TipoAFP.MODELO: Decimal("10.58"),
    TipoAFP.PLANVITAL: Decimal("11.16"),
    TipoAFP.PROVIDA: Decimal("11.45"),
    TipoAFP.UNO: Decimal("10.69"),
}

# Cotización obligatoria AFP
COTIZACION_AFP_BASE = Decimal("10")

# Tasa FONASA
TASA_FONASA = Decimal("7")

# AFC (Seguro Cesantía)
TASA_AFC_TRABAJADOR_INDEFINIDO = Decimal("0.6")
TASA_AFC_TRABAJADOR_PLAZO = Decimal("0")
TASA_AFC_EMPLEADOR_INDEFINIDO = Decimal("2.4")
TASA_AFC_EMPLEADOR_PLAZO = Decimal("3.0")

# Gratificación Legal
GRATIFICACION_TOPE_IMM = Decimal("4.75")  # 4.75 IMM

# Sueldo Mínimo
SUELDO_MINIMO_2026 = 500000  # CLP (estimado)
IMM_2026 = 500000  # Ingreso Mínimo Mensual


# =============================================================================
# MODELOS DE DATOS
# =============================================================================

class Trabajador:
    """Modelo de trabajador/empleado"""
    def __init__(
        self,
        id: UUID = None,
        rut: str = "",
        nombres: str = "",
        apellido_paterno: str = "",
        apellido_materno: str = "",
        fecha_nacimiento: date = None,
        sexo: str = "M",
        nacionalidad: str = "Chilena",
        estado_civil: str = "soltero",
        direccion: str = "",
        comuna: str = "",
        telefono: str = "",
        email: str = "",
        tipo_contrato: TipoContrato = TipoContrato.INDEFINIDO,
        fecha_ingreso: date = None,
        fecha_termino: Optional[date] = None,
        cargo: str = "",
        departamento: str = "",
        jefe_directo_id: Optional[UUID] = None,
        tipo_jornada: TipoJornada = TipoJornada.COMPLETA,
        horas_semanales: int = 45,
        sueldo_base: int = 0,
        afp: TipoAFP = TipoAFP.HABITAT,
        salud: TipoSalud = TipoSalud.FONASA,
        isapre_nombre: Optional[str] = None,
        isapre_uf: Optional[Decimal] = None,
        cuenta_banco: Optional[str] = None,
        banco: Optional[str] = None,
        estado: EstadoTrabajador = EstadoTrabajador.ACTIVO,
        cargas_familiares: int = 0,
        copropiedad_id: Optional[UUID] = None
    ):
        self.id = id or uuid4()
        self.rut = rut
        self.nombres = nombres
        self.apellido_paterno = apellido_paterno
        self.apellido_materno = apellido_materno
        self.fecha_nacimiento = fecha_nacimiento
        self.sexo = sexo
        self.nacionalidad = nacionalidad
        self.estado_civil = estado_civil
        self.direccion = direccion
        self.comuna = comuna
        self.telefono = telefono
        self.email = email
        self.tipo_contrato = tipo_contrato
        self.fecha_ingreso = fecha_ingreso or date.today()
        self.fecha_termino = fecha_termino
        self.cargo = cargo
        self.departamento = departamento
        self.jefe_directo_id = jefe_directo_id
        self.tipo_jornada = tipo_jornada
        self.horas_semanales = horas_semanales
        self.sueldo_base = sueldo_base
        self.afp = afp
        self.salud = salud
        self.isapre_nombre = isapre_nombre
        self.isapre_uf = isapre_uf
        self.cuenta_banco = cuenta_banco
        self.banco = banco
        self.estado = estado
        self.cargas_familiares = cargas_familiares
        self.copropiedad_id = copropiedad_id
    
    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno}"
    
    @property
    def antiguedad_anos(self) -> int:
        if not self.fecha_ingreso:
            return 0
        return (date.today() - self.fecha_ingreso).days // 365


class Contrato:
    """Modelo de contrato de trabajo"""
    def __init__(
        self,
        id: UUID = None,
        trabajador_id: UUID = None,
        tipo: TipoContrato = TipoContrato.INDEFINIDO,
        fecha_inicio: date = None,
        fecha_termino: Optional[date] = None,
        sueldo_base: int = 0,
        tipo_jornada: TipoJornada = TipoJornada.COMPLETA,
        horas_semanales: int = 45,
        cargo: str = "",
        funciones: str = "",
        lugar_trabajo: str = "",
        clausulas_especiales: Optional[str] = None,
        firmado: bool = False,
        fecha_firma: Optional[date] = None,
        documento_url: Optional[str] = None,
        anexos: List[Dict] = None
    ):
        self.id = id or uuid4()
        self.trabajador_id = trabajador_id
        self.tipo = tipo
        self.fecha_inicio = fecha_inicio or date.today()
        self.fecha_termino = fecha_termino
        self.sueldo_base = sueldo_base
        self.tipo_jornada = tipo_jornada
        self.horas_semanales = horas_semanales
        self.cargo = cargo
        self.funciones = funciones
        self.lugar_trabajo = lugar_trabajo
        self.clausulas_especiales = clausulas_especiales
        self.firmado = firmado
        self.fecha_firma = fecha_firma
        self.documento_url = documento_url
        self.anexos = anexos or []


class LiquidacionSueldo:
    """Modelo de liquidación de sueldo"""
    def __init__(
        self,
        id: UUID = None,
        trabajador_id: UUID = None,
        periodo: str = "",
        dias_trabajados: int = 30,
        haberes: List[Dict] = None,
        descuentos: List[Dict] = None,
        total_haberes_imponibles: int = 0,
        total_haberes_no_imponibles: int = 0,
        total_haberes: int = 0,
        total_descuentos_legales: int = 0,
        total_descuentos_voluntarios: int = 0,
        total_descuentos: int = 0,
        sueldo_liquido: int = 0,
        valor_uf: Decimal = Decimal("38000"),
        estado: str = "borrador",
        fecha_pago: Optional[date] = None,
        comprobante_pago: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.trabajador_id = trabajador_id
        self.periodo = periodo
        self.dias_trabajados = dias_trabajados
        self.haberes = haberes or []
        self.descuentos = descuentos or []
        self.total_haberes_imponibles = total_haberes_imponibles
        self.total_haberes_no_imponibles = total_haberes_no_imponibles
        self.total_haberes = total_haberes
        self.total_descuentos_legales = total_descuentos_legales
        self.total_descuentos_voluntarios = total_descuentos_voluntarios
        self.total_descuentos = total_descuentos
        self.sueldo_liquido = sueldo_liquido
        self.valor_uf = valor_uf
        self.estado = estado
        self.fecha_pago = fecha_pago
        self.comprobante_pago = comprobante_pago


class Vacaciones:
    """Modelo de vacaciones"""
    def __init__(
        self,
        id: UUID = None,
        trabajador_id: UUID = None,
        fecha_inicio: date = None,
        fecha_termino: date = None,
        dias_habiles: int = 0,
        dias_progresivos: int = 0,
        total_dias: int = 0,
        estado: str = "solicitada",
        aprobado_por: Optional[UUID] = None,
        fecha_aprobacion: Optional[date] = None,
        observaciones: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.trabajador_id = trabajador_id
        self.fecha_inicio = fecha_inicio
        self.fecha_termino = fecha_termino
        self.dias_habiles = dias_habiles
        self.dias_progresivos = dias_progresivos
        self.total_dias = total_dias
        self.estado = estado
        self.aprobado_por = aprobado_por
        self.fecha_aprobacion = fecha_aprobacion
        self.observaciones = observaciones


class LicenciaMedica:
    """Modelo de licencia médica"""
    def __init__(
        self,
        id: UUID = None,
        trabajador_id: UUID = None,
        tipo: str = "enfermedad_comun",
        fecha_inicio: date = None,
        fecha_termino: date = None,
        dias: int = 0,
        diagnostico: str = "",
        medico: str = "",
        institucion: str = "",
        folio_compin: Optional[str] = None,
        estado: str = "presentada",
        subsidio_estimado: int = 0,
        documento_url: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.trabajador_id = trabajador_id
        self.tipo = tipo
        self.fecha_inicio = fecha_inicio
        self.fecha_termino = fecha_termino
        self.dias = dias
        self.diagnostico = diagnostico
        self.medico = medico
        self.institucion = institucion
        self.folio_compin = folio_compin
        self.estado = estado
        self.subsidio_estimado = subsidio_estimado
        self.documento_url = documento_url


class Finiquito:
    """Modelo de finiquito"""
    def __init__(
        self,
        id: UUID = None,
        trabajador_id: UUID = None,
        fecha_termino: date = None,
        causal: CausalDespido = CausalDespido.RENUNCIA,
        fecha_aviso: Optional[date] = None,
        sueldo_base: int = 0,
        anos_servicio: int = 0,
        # Conceptos
        sueldo_proporcional: int = 0,
        vacaciones_proporcionales: int = 0,
        vacaciones_pendientes: int = 0,
        gratificacion_proporcional: int = 0,
        indemnizacion_anos_servicio: int = 0,
        indemnizacion_aviso_previo: int = 0,
        indemnizacion_feriado_anual: int = 0,
        otros_haberes: int = 0,
        # Descuentos
        descuento_afp: int = 0,
        descuento_salud: int = 0,
        descuento_afc: int = 0,
        descuento_impuesto: int = 0,
        otros_descuentos: int = 0,
        # Totales
        total_haberes: int = 0,
        total_descuentos: int = 0,
        total_liquido: int = 0,
        # Estado
        estado: str = "borrador",
        fecha_firma: Optional[date] = None,
        ratificado_inspeccion: bool = False,
        documento_url: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.trabajador_id = trabajador_id
        self.fecha_termino = fecha_termino
        self.causal = causal
        self.fecha_aviso = fecha_aviso
        self.sueldo_base = sueldo_base
        self.anos_servicio = anos_servicio
        self.sueldo_proporcional = sueldo_proporcional
        self.vacaciones_proporcionales = vacaciones_proporcionales
        self.vacaciones_pendientes = vacaciones_pendientes
        self.gratificacion_proporcional = gratificacion_proporcional
        self.indemnizacion_anos_servicio = indemnizacion_anos_servicio
        self.indemnizacion_aviso_previo = indemnizacion_aviso_previo
        self.indemnizacion_feriado_anual = indemnizacion_feriado_anual
        self.otros_haberes = otros_haberes
        self.descuento_afp = descuento_afp
        self.descuento_salud = descuento_salud
        self.descuento_afc = descuento_afc
        self.descuento_impuesto = descuento_impuesto
        self.otros_descuentos = otros_descuentos
        self.total_haberes = total_haberes
        self.total_descuentos = total_descuentos
        self.total_liquido = total_liquido
        self.estado = estado
        self.fecha_firma = fecha_firma
        self.ratificado_inspeccion = ratificado_inspeccion
        self.documento_url = documento_url


# =============================================================================
# TABLAS DE IMPUESTO ÚNICO
# =============================================================================

# Tabla Impuesto Único 2da Categoría 2026 (en UTM)
TABLA_IMPUESTO_UNICO = [
    {"desde": Decimal("0"), "hasta": Decimal("13.5"), "tasa": Decimal("0"), "rebaja": Decimal("0")},
    {"desde": Decimal("13.5"), "hasta": Decimal("30"), "tasa": Decimal("4"), "rebaja": Decimal("0.54")},
    {"desde": Decimal("30"), "hasta": Decimal("50"), "tasa": Decimal("8"), "rebaja": Decimal("1.74")},
    {"desde": Decimal("50"), "hasta": Decimal("70"), "tasa": Decimal("13.5"), "rebaja": Decimal("4.49")},
    {"desde": Decimal("70"), "hasta": Decimal("90"), "tasa": Decimal("23"), "rebaja": Decimal("11.14")},
    {"desde": Decimal("90"), "hasta": Decimal("120"), "tasa": Decimal("30.4"), "rebaja": Decimal("17.8")},
    {"desde": Decimal("120"), "hasta": Decimal("310"), "tasa": Decimal("35"), "rebaja": Decimal("23.32")},
    {"desde": Decimal("310"), "hasta": Decimal("999999"), "tasa": Decimal("40"), "rebaja": Decimal("38.82")},
]


# =============================================================================
# SERVICIO DE RRHH
# =============================================================================

class RRHHService:
    """
    Servicio de gestión de RRHH y Nóminas
    
    Funcionalidades:
    - Gestión de trabajadores y contratos
    - Cálculo de liquidaciones de sueldo
    - Gestión de vacaciones y licencias
    - Cálculo de finiquitos
    - Reportes Previred
    - Cumplimiento Código del Trabajo
    """
    
    def __init__(self):
        self.trabajadores: Dict[UUID, Trabajador] = {}
        self.contratos: Dict[UUID, Contrato] = {}
        self.liquidaciones: Dict[UUID, LiquidacionSueldo] = {}
        self.vacaciones: Dict[UUID, Vacaciones] = {}
        self.licencias: Dict[UUID, LicenciaMedica] = {}
        self.finiquitos: Dict[UUID, Finiquito] = {}
        self.valor_uf = Decimal("38000")
        self.valor_utm = Decimal("65000")
    
    # =========================================================================
    # GESTIÓN DE TRABAJADORES
    # =========================================================================
    
    async def crear_trabajador(
        self,
        rut: str,
        nombres: str,
        apellido_paterno: str,
        apellido_materno: str,
        fecha_nacimiento: date,
        tipo_contrato: TipoContrato,
        cargo: str,
        sueldo_base: int,
        afp: TipoAFP,
        salud: TipoSalud,
        copropiedad_id: Optional[UUID] = None,
        **kwargs
    ) -> Trabajador:
        """Crea un nuevo trabajador"""
        
        # Validar RUT único
        for t in self.trabajadores.values():
            if t.rut == rut:
                raise ValueError(f"Ya existe trabajador con RUT {rut}")
        
        # Validar sueldo mínimo
        if tipo_contrato != TipoContrato.HONORARIOS:
            if sueldo_base < SUELDO_MINIMO_2026:
                raise ValueError(f"Sueldo base debe ser al menos ${SUELDO_MINIMO_2026:,}")
        
        trabajador = Trabajador(
            rut=rut,
            nombres=nombres,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            fecha_nacimiento=fecha_nacimiento,
            tipo_contrato=tipo_contrato,
            cargo=cargo,
            sueldo_base=sueldo_base,
            afp=afp,
            salud=salud,
            copropiedad_id=copropiedad_id,
            **kwargs
        )
        
        self.trabajadores[trabajador.id] = trabajador
        
        # Crear contrato automáticamente
        await self.crear_contrato(
            trabajador_id=trabajador.id,
            tipo=tipo_contrato,
            sueldo_base=sueldo_base,
            cargo=cargo,
            horas_semanales=kwargs.get("horas_semanales", 45)
        )
        
        return trabajador
    
    async def obtener_trabajador(self, trabajador_id: UUID) -> Optional[Trabajador]:
        """Obtiene un trabajador por ID"""
        return self.trabajadores.get(trabajador_id)
    
    async def listar_trabajadores(
        self,
        copropiedad_id: Optional[UUID] = None,
        estado: Optional[EstadoTrabajador] = None,
        departamento: Optional[str] = None
    ) -> List[Trabajador]:
        """Lista trabajadores con filtros"""
        trabajadores = list(self.trabajadores.values())
        
        if copropiedad_id:
            trabajadores = [t for t in trabajadores if t.copropiedad_id == copropiedad_id]
        if estado:
            trabajadores = [t for t in trabajadores if t.estado == estado]
        if departamento:
            trabajadores = [t for t in trabajadores if t.departamento == departamento]
        
        return trabajadores
    
    # =========================================================================
    # CONTRATOS
    # =========================================================================
    
    async def crear_contrato(
        self,
        trabajador_id: UUID,
        tipo: TipoContrato,
        sueldo_base: int,
        cargo: str,
        horas_semanales: int = 45,
        fecha_inicio: date = None,
        fecha_termino: date = None,
        funciones: str = "",
        lugar_trabajo: str = ""
    ) -> Contrato:
        """Crea un nuevo contrato"""
        
        trabajador = self.trabajadores.get(trabajador_id)
        if not trabajador:
            raise ValueError("Trabajador no encontrado")
        
        tipo_jornada = TipoJornada.COMPLETA
        if horas_semanales < 30:
            tipo_jornada = TipoJornada.PARCIAL
        
        contrato = Contrato(
            trabajador_id=trabajador_id,
            tipo=tipo,
            fecha_inicio=fecha_inicio or date.today(),
            fecha_termino=fecha_termino,
            sueldo_base=sueldo_base,
            tipo_jornada=tipo_jornada,
            horas_semanales=horas_semanales,
            cargo=cargo,
            funciones=funciones,
            lugar_trabajo=lugar_trabajo
        )
        
        self.contratos[contrato.id] = contrato
        return contrato
    
    # =========================================================================
    # CÁLCULO DE LIQUIDACIÓN
    # =========================================================================
    
    async def calcular_liquidacion(
        self,
        trabajador_id: UUID,
        periodo: str,
        dias_trabajados: int = 30,
        horas_extra: int = 0,
        bonos_adicionales: List[Dict] = None,
        descuentos_adicionales: List[Dict] = None
    ) -> LiquidacionSueldo:
        """Calcula liquidación de sueldo completa"""
        
        trabajador = self.trabajadores.get(trabajador_id)
        if not trabajador:
            raise ValueError("Trabajador no encontrado")
        
        haberes = []
        descuentos = []
        
        # =================================================================
        # HABERES
        # =================================================================
        
        # Sueldo base proporcional
        sueldo_proporcional = int(trabajador.sueldo_base * dias_trabajados / 30)
        haberes.append({
            "tipo": TipoHaber.SUELDO_BASE.value,
            "descripcion": "Sueldo Base",
            "monto": sueldo_proporcional,
            "imponible": True
        })
        
        # Gratificación Legal (Art. 50 - garantizada mensual)
        # Tope: 4.75 IMM / 12 mensual
        tope_gratificacion = int(GRATIFICACION_TOPE_IMM * IMM_2026 / 12)
        gratificacion = min(int(sueldo_proporcional * 0.25), tope_gratificacion)
        haberes.append({
            "tipo": TipoHaber.GRATIFICACION.value,
            "descripcion": "Gratificación Legal Art. 50",
            "monto": gratificacion,
            "imponible": True
        })
        
        # Horas extra (50% recargo)
        if horas_extra > 0:
            valor_hora = trabajador.sueldo_base / 180  # 45 hrs * 4 semanas
            monto_horas_extra = int(valor_hora * 1.5 * horas_extra)
            haberes.append({
                "tipo": TipoHaber.HORAS_EXTRA.value,
                "descripcion": f"Horas Extra ({horas_extra} hrs)",
                "monto": monto_horas_extra,
                "imponible": True
            })
        
        # Colación (no imponible hasta 1.5 UF diarias)
        colacion = 80000  # Monto fijo ejemplo
        haberes.append({
            "tipo": TipoHaber.COLACION.value,
            "descripcion": "Asignación Colación",
            "monto": colacion,
            "imponible": False
        })
        
        # Movilización (no imponible hasta 1.5 UF diarias)
        movilizacion = 50000  # Monto fijo ejemplo
        haberes.append({
            "tipo": TipoHaber.MOVILIZACION.value,
            "descripcion": "Asignación Movilización",
            "monto": movilizacion,
            "imponible": False
        })
        
        # Bonos adicionales
        if bonos_adicionales:
            for bono in bonos_adicionales:
                haberes.append({
                    "tipo": bono.get("tipo", TipoHaber.OTRO_IMPONIBLE.value),
                    "descripcion": bono.get("descripcion", "Bono"),
                    "monto": bono.get("monto", 0),
                    "imponible": bono.get("imponible", True)
                })
        
        # Calcular totales haberes
        total_imponibles = sum(h["monto"] for h in haberes if h["imponible"])
        total_no_imponibles = sum(h["monto"] for h in haberes if not h["imponible"])
        total_haberes = total_imponibles + total_no_imponibles
        
        # =================================================================
        # DESCUENTOS LEGALES
        # =================================================================
        
        # Tope imponible
        tope_imponible = int(TOPE_IMPONIBLE_AFP_UF * float(self.valor_uf))
        base_imponible = min(total_imponibles, tope_imponible)
        
        # AFP
        tasa_afp = TASAS_AFP.get(trabajador.afp, Decimal("11.5"))
        descuento_afp = int(base_imponible * float(tasa_afp) / 100)
        descuentos.append({
            "tipo": TipoDescuento.AFP.value,
            "descripcion": f"AFP {trabajador.afp.value.capitalize()} ({tasa_afp}%)",
            "monto": descuento_afp,
            "legal": True
        })
        
        # Salud
        if trabajador.salud == TipoSalud.FONASA:
            descuento_salud = int(base_imponible * float(TASA_FONASA) / 100)
            desc_salud = f"FONASA ({TASA_FONASA}%)"
        else:
            # Isapre: mínimo 7% o pactado en UF
            if trabajador.isapre_uf:
                descuento_salud = int(float(trabajador.isapre_uf) * float(self.valor_uf))
                minimo_7pct = int(base_imponible * 0.07)
                descuento_salud = max(descuento_salud, minimo_7pct)
            else:
                descuento_salud = int(base_imponible * 0.07)
            desc_salud = f"Isapre {trabajador.isapre_nombre or ''}"
        
        descuentos.append({
            "tipo": TipoDescuento.SALUD.value,
            "descripcion": desc_salud,
            "monto": descuento_salud,
            "legal": True
        })
        
        # AFC (Seguro de Cesantía)
        if trabajador.tipo_contrato == TipoContrato.INDEFINIDO:
            tasa_afc = TASA_AFC_TRABAJADOR_INDEFINIDO
        else:
            tasa_afc = TASA_AFC_TRABAJADOR_PLAZO
        
        tope_afc = int(TOPE_IMPONIBLE_AFC_UF * float(self.valor_uf))
        base_afc = min(total_imponibles, tope_afc)
        descuento_afc = int(base_afc * float(tasa_afc) / 100)
        
        descuentos.append({
            "tipo": TipoDescuento.AFC.value,
            "descripcion": f"AFC ({tasa_afc}%)",
            "monto": descuento_afc,
            "legal": True
        })
        
        # Impuesto Único 2da Categoría
        base_tributable = total_imponibles - descuento_afp - descuento_salud - descuento_afc
        impuesto = await self._calcular_impuesto_unico(base_tributable)
        
        descuentos.append({
            "tipo": TipoDescuento.IMPUESTO_UNICO.value,
            "descripcion": "Impuesto Único 2da Categoría",
            "monto": impuesto,
            "legal": True
        })
        
        # Descuentos adicionales (voluntarios)
        if descuentos_adicionales:
            for desc in descuentos_adicionales:
                descuentos.append({
                    "tipo": desc.get("tipo", TipoDescuento.OTRO_DESCUENTO.value),
                    "descripcion": desc.get("descripcion", "Otro"),
                    "monto": desc.get("monto", 0),
                    "legal": False
                })
        
        # Calcular totales descuentos
        total_legales = sum(d["monto"] for d in descuentos if d["legal"])
        total_voluntarios = sum(d["monto"] for d in descuentos if not d["legal"])
        total_descuentos = total_legales + total_voluntarios
        
        # Sueldo líquido
        sueldo_liquido = total_haberes - total_descuentos
        
        # Crear liquidación
        liquidacion = LiquidacionSueldo(
            trabajador_id=trabajador_id,
            periodo=periodo,
            dias_trabajados=dias_trabajados,
            haberes=haberes,
            descuentos=descuentos,
            total_haberes_imponibles=total_imponibles,
            total_haberes_no_imponibles=total_no_imponibles,
            total_haberes=total_haberes,
            total_descuentos_legales=total_legales,
            total_descuentos_voluntarios=total_voluntarios,
            total_descuentos=total_descuentos,
            sueldo_liquido=sueldo_liquido,
            valor_uf=self.valor_uf
        )
        
        self.liquidaciones[liquidacion.id] = liquidacion
        return liquidacion
    
    async def _calcular_impuesto_unico(self, base_tributable: int) -> int:
        """Calcula impuesto único según tabla"""
        
        # Convertir a UTM
        base_utm = Decimal(str(base_tributable)) / self.valor_utm
        
        impuesto_utm = Decimal("0")
        for tramo in TABLA_IMPUESTO_UNICO:
            if tramo["desde"] <= base_utm < tramo["hasta"]:
                impuesto_utm = (base_utm * tramo["tasa"] / 100) - tramo["rebaja"]
                break
        
        # Convertir a pesos
        impuesto = int(float(impuesto_utm * self.valor_utm))
        return max(0, impuesto)
    
    # =========================================================================
    # VACACIONES
    # =========================================================================
    
    async def calcular_dias_vacaciones(
        self,
        trabajador_id: UUID
    ) -> Dict[str, Any]:
        """Calcula días de vacaciones disponibles"""
        
        trabajador = self.trabajadores.get(trabajador_id)
        if not trabajador:
            raise ValueError("Trabajador no encontrado")
        
        # Días base: 15 hábiles por año
        dias_base = 15
        
        # Días progresivos: 1 día adicional por cada 3 años después de 10
        anos = trabajador.antiguedad_anos
        dias_progresivos = 0
        if anos > 10:
            dias_progresivos = (anos - 10) // 3
        
        total_dias_anuales = dias_base + dias_progresivos
        
        # Calcular días pendientes (mock: proporcional)
        meses_trabajados = ((date.today() - trabajador.fecha_ingreso).days % 365) // 30
        dias_acumulados = int(total_dias_anuales * meses_trabajados / 12)
        
        # Descontar vacaciones tomadas (mock)
        dias_tomados = sum(
            v.total_dias for v in self.vacaciones.values()
            if v.trabajador_id == trabajador_id and v.estado == "aprobada"
        )
        
        dias_disponibles = dias_acumulados - dias_tomados
        
        return {
            "trabajador_id": trabajador_id,
            "antiguedad_anos": anos,
            "dias_base": dias_base,
            "dias_progresivos": dias_progresivos,
            "total_dias_anuales": total_dias_anuales,
            "dias_acumulados": dias_acumulados,
            "dias_tomados": dias_tomados,
            "dias_disponibles": max(0, dias_disponibles)
        }
    
    async def solicitar_vacaciones(
        self,
        trabajador_id: UUID,
        fecha_inicio: date,
        fecha_termino: date,
        observaciones: str = ""
    ) -> Vacaciones:
        """Registra solicitud de vacaciones"""
        
        # Calcular días hábiles
        dias_habiles = self._calcular_dias_habiles(fecha_inicio, fecha_termino)
        
        disponibles = await self.calcular_dias_vacaciones(trabajador_id)
        if dias_habiles > disponibles["dias_disponibles"]:
            raise ValueError(f"Solo tiene {disponibles['dias_disponibles']} días disponibles")
        
        vacaciones = Vacaciones(
            trabajador_id=trabajador_id,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            dias_habiles=dias_habiles,
            dias_progresivos=0,
            total_dias=dias_habiles,
            observaciones=observaciones
        )
        
        self.vacaciones[vacaciones.id] = vacaciones
        return vacaciones
    
    def _calcular_dias_habiles(self, inicio: date, termino: date) -> int:
        """Calcula días hábiles entre dos fechas"""
        dias = 0
        actual = inicio
        while actual <= termino:
            if actual.weekday() < 5:  # Lunes a Viernes
                dias += 1
            actual = date(actual.year, actual.month, actual.day + 1) if actual.day < 28 else date(actual.year, actual.month + 1, 1)
        return dias
    
    # =========================================================================
    # FINIQUITOS
    # =========================================================================
    
    async def calcular_finiquito(
        self,
        trabajador_id: UUID,
        fecha_termino: date,
        causal: CausalDespido,
        fecha_aviso: date = None
    ) -> Finiquito:
        """Calcula finiquito según causal"""
        
        trabajador = self.trabajadores.get(trabajador_id)
        if not trabajador:
            raise ValueError("Trabajador no encontrado")
        
        sueldo = trabajador.sueldo_base
        anos = trabajador.antiguedad_anos
        
        # Calcular proporcionales
        dia_mes = fecha_termino.day
        sueldo_proporcional = int(sueldo * dia_mes / 30)
        
        # Vacaciones proporcionales
        vacaciones_info = await self.calcular_dias_vacaciones(trabajador_id)
        valor_dia = sueldo / 30
        vacaciones_proporcionales = int(valor_dia * vacaciones_info["dias_disponibles"])
        
        # Gratificación proporcional
        tope_grat = int(GRATIFICACION_TOPE_IMM * IMM_2026 / 12)
        gratificacion = min(int(sueldo * 0.25), tope_grat)
        gratificacion_proporcional = int(gratificacion * dia_mes / 30)
        
        # Indemnizaciones según causal
        indemnizacion_anos = 0
        indemnizacion_aviso = 0
        
        # Art. 161 - Necesidades de la empresa
        if causal == CausalDespido.NECESIDADES_EMPRESA:
            # 30 días por año, tope 11 años (330 días)
            indemnizacion_anos = min(anos, 11) * sueldo
            # Aviso previo: 30 días si no hubo aviso con 30 días anticipación
            if not fecha_aviso or (fecha_termino - fecha_aviso).days < 30:
                indemnizacion_aviso = sueldo
        
        # Art. 161 inciso 2 - Desahucio (cargos confianza)
        elif causal == CausalDespido.DESAHUCIO:
            indemnizacion_anos = min(anos, 11) * sueldo
            if not fecha_aviso or (fecha_termino - fecha_aviso).days < 30:
                indemnizacion_aviso = sueldo
        
        # Art. 159 N°4,5 - Vencimiento plazo / Fin obra
        elif causal in [CausalDespido.VENCIMIENTO_PLAZO, CausalDespido.FIN_OBRA]:
            # Sin indemnización por años
            pass
        
        # Art. 160 - Causales imputables al trabajador
        elif causal in [CausalDespido.FALTA_PROBIDAD, CausalDespido.ACOSO,
                       CausalDespido.AUSENCIAS_INJUSTIFICADAS, CausalDespido.ABANDONO,
                       CausalDespido.INCUMPLIMIENTO_GRAVE]:
            # Sin indemnización
            pass
        
        # Calcular totales
        total_haberes = (
            sueldo_proporcional +
            vacaciones_proporcionales +
            gratificacion_proporcional +
            indemnizacion_anos +
            indemnizacion_aviso
        )
        
        # Descuentos sobre haberes imponibles (no sobre indemnizaciones)
        base_imponible = sueldo_proporcional + gratificacion_proporcional
        
        tasa_afp = float(TASAS_AFP.get(trabajador.afp, Decimal("11.5")))
        descuento_afp = int(base_imponible * tasa_afp / 100)
        descuento_salud = int(base_imponible * 0.07)
        descuento_afc = int(base_imponible * float(TASA_AFC_TRABAJADOR_INDEFINIDO) / 100)
        
        impuesto = await self._calcular_impuesto_unico(
            base_imponible - descuento_afp - descuento_salud - descuento_afc
        )
        
        total_descuentos = descuento_afp + descuento_salud + descuento_afc + impuesto
        total_liquido = total_haberes - total_descuentos
        
        finiquito = Finiquito(
            trabajador_id=trabajador_id,
            fecha_termino=fecha_termino,
            causal=causal,
            fecha_aviso=fecha_aviso,
            sueldo_base=sueldo,
            anos_servicio=anos,
            sueldo_proporcional=sueldo_proporcional,
            vacaciones_proporcionales=vacaciones_proporcionales,
            gratificacion_proporcional=gratificacion_proporcional,
            indemnizacion_anos_servicio=indemnizacion_anos,
            indemnizacion_aviso_previo=indemnizacion_aviso,
            descuento_afp=descuento_afp,
            descuento_salud=descuento_salud,
            descuento_afc=descuento_afc,
            descuento_impuesto=impuesto,
            total_haberes=total_haberes,
            total_descuentos=total_descuentos,
            total_liquido=total_liquido
        )
        
        self.finiquitos[finiquito.id] = finiquito
        return finiquito
    
    # =========================================================================
    # REPORTES PREVIRED
    # =========================================================================
    
    async def generar_archivo_previred(
        self,
        periodo: str,
        copropiedad_id: UUID = None
    ) -> Dict[str, Any]:
        """Genera archivo para carga en Previred"""
        
        trabajadores = await self.listar_trabajadores(
            copropiedad_id=copropiedad_id,
            estado=EstadoTrabajador.ACTIVO
        )
        
        registros = []
        total_afp = 0
        total_salud = 0
        total_afc = 0
        
        for trab in trabajadores:
            # Buscar liquidación del período
            liquidacion = None
            for liq in self.liquidaciones.values():
                if liq.trabajador_id == trab.id and liq.periodo == periodo:
                    liquidacion = liq
                    break
            
            if not liquidacion:
                continue
            
            # Extraer descuentos
            desc_afp = next((d["monto"] for d in liquidacion.descuentos if d["tipo"] == TipoDescuento.AFP.value), 0)
            desc_salud = next((d["monto"] for d in liquidacion.descuentos if d["tipo"] == TipoDescuento.SALUD.value), 0)
            desc_afc = next((d["monto"] for d in liquidacion.descuentos if d["tipo"] == TipoDescuento.AFC.value), 0)
            
            registros.append({
                "rut": trab.rut,
                "nombre": trab.nombre_completo,
                "afp": trab.afp.value,
                "salud": "FONASA" if trab.salud == TipoSalud.FONASA else trab.isapre_nombre,
                "remuneracion_imponible": liquidacion.total_haberes_imponibles,
                "cotizacion_afp": desc_afp,
                "cotizacion_salud": desc_salud,
                "cotizacion_afc": desc_afc,
                "dias_trabajados": liquidacion.dias_trabajados
            })
            
            total_afp += desc_afp
            total_salud += desc_salud
            total_afc += desc_afc
        
        return {
            "periodo": periodo,
            "generado_en": datetime.now(),
            "total_trabajadores": len(registros),
            "registros": registros,
            "totales": {
                "afp": total_afp,
                "salud": total_salud,
                "afc": total_afc,
                "total": total_afp + total_salud + total_afc
            },
            "formato": "PREVIRED_v2"
        }
    
    # =========================================================================
    # ESTADÍSTICAS
    # =========================================================================
    
    async def obtener_estadisticas(
        self,
        copropiedad_id: UUID = None
    ) -> Dict[str, Any]:
        """Obtiene estadísticas de RRHH"""
        
        trabajadores = await self.listar_trabajadores(copropiedad_id=copropiedad_id)
        activos = [t for t in trabajadores if t.estado == EstadoTrabajador.ACTIVO]
        
        total_nomina = sum(t.sueldo_base for t in activos)
        
        return {
            "total_trabajadores": len(trabajadores),
            "trabajadores_activos": len(activos),
            "por_tipo_contrato": {
                tipo.value: len([t for t in activos if t.tipo_contrato == tipo])
                for tipo in TipoContrato
            },
            "por_departamento": {},  # Agrupar por departamento
            "total_nomina_mensual": total_nomina,
            "costo_empleador_estimado": int(total_nomina * 1.05),  # +5% aprox
            "antiguedad_promedio_anos": (
                sum(t.antiguedad_anos for t in activos) / len(activos)
                if activos else 0
            )
        }


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================

rrhh_service = RRHHService()
