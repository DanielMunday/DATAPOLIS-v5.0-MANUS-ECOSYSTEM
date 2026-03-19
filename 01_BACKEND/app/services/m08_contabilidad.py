"""
DATAPOLIS v3.0 - Módulo M08: Contabilidad y Finanzas
====================================================
Gestión contable integral según normativa chilena:
- PCGA Chile / IFRS (NIC 40, NIIF 16)
- SII: Libro Compras/Ventas, F29, DJAT
- Ley 21.713: Tributación rentas inmobiliarias
- CMF: Reportes regulatorios condominios

Autor: DATAPOLIS SpA
Versión: 3.0.0
Última actualización: 2026-02-01
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import asyncio


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoCuenta(str, Enum):
    """Tipos de cuentas contables según PCGA Chile"""
    ACTIVO_CIRCULANTE = "activo_circulante"
    ACTIVO_FIJO = "activo_fijo"
    ACTIVO_INTANGIBLE = "activo_intangible"
    PASIVO_CIRCULANTE = "pasivo_circulante"
    PASIVO_LARGO_PLAZO = "pasivo_largo_plazo"
    PATRIMONIO = "patrimonio"
    INGRESO = "ingreso"
    GASTO = "gasto"
    COSTO = "costo"
    RESULTADO = "resultado"
    ORDEN = "cuenta_orden"


class TipoMovimiento(str, Enum):
    """Tipos de movimientos contables"""
    DEBE = "debe"
    HABER = "haber"


class TipoComprobante(str, Enum):
    """Tipos de comprobantes contables"""
    INGRESO = "ingreso"
    EGRESO = "egreso"
    TRASPASO = "traspaso"
    PROVISION = "provision"
    AJUSTE = "ajuste"
    APERTURA = "apertura"
    CIERRE = "cierre"
    DEPRECIACION = "depreciacion"


class EstadoComprobante(str, Enum):
    """Estados de comprobantes"""
    BORRADOR = "borrador"
    CONTABILIZADO = "contabilizado"
    ANULADO = "anulado"
    REVERSADO = "reversado"


class TipoDocumentoTributario(str, Enum):
    """Tipos de DTE según SII"""
    FACTURA = "33"
    FACTURA_EXENTA = "34"
    BOLETA = "39"
    BOLETA_EXENTA = "41"
    NOTA_CREDITO = "61"
    NOTA_DEBITO = "56"
    GUIA_DESPACHO = "52"
    FACTURA_COMPRA = "46"
    LIQUIDACION = "43"


class PeriodoTributario(str, Enum):
    """Períodos tributarios"""
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"


class TipoReporte(str, Enum):
    """Tipos de reportes contables"""
    BALANCE_GENERAL = "balance_general"
    ESTADO_RESULTADOS = "estado_resultados"
    FLUJO_EFECTIVO = "flujo_efectivo"
    LIBRO_MAYOR = "libro_mayor"
    LIBRO_DIARIO = "libro_diario"
    BALANCE_TRIBUTARIO = "balance_tributario"
    BALANCE_8_COLUMNAS = "balance_8_columnas"
    RAZON_CORRIENTE = "razon_corriente"


class MetodoDepreciacion(str, Enum):
    """Métodos de depreciación"""
    LINEAL = "lineal"
    ACELERADA = "acelerada"
    UNIDADES_PRODUCCION = "unidades_produccion"
    SALDO_DECRECIENTE = "saldo_decreciente"


class TipoImpuesto(str, Enum):
    """Tipos de impuestos"""
    IVA = "iva"
    PPM = "ppm"
    RETENCION = "retencion"
    PRIMERA_CATEGORIA = "primera_categoria"
    GLOBAL_COMPLEMENTARIO = "global_complementario"
    UNICO_TRABAJADORES = "impuesto_unico"


# =============================================================================
# MODELOS DE DATOS
# =============================================================================

class CuentaContable:
    """Modelo de cuenta contable según plan de cuentas PCGA Chile"""
    def __init__(
        self,
        id: UUID = None,
        codigo: str = "",
        nombre: str = "",
        tipo: TipoCuenta = TipoCuenta.ACTIVO_CIRCULANTE,
        nivel: int = 1,
        cuenta_padre_id: Optional[UUID] = None,
        acepta_movimientos: bool = True,
        cuenta_sii: Optional[str] = None,
        activa: bool = True,
        naturaleza: TipoMovimiento = TipoMovimiento.DEBE,
        saldo_actual_uf: Decimal = Decimal("0"),
        descripcion: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.codigo = codigo
        self.nombre = nombre
        self.tipo = tipo
        self.nivel = nivel
        self.cuenta_padre_id = cuenta_padre_id
        self.acepta_movimientos = acepta_movimientos
        self.cuenta_sii = cuenta_sii
        self.activa = activa
        self.naturaleza = naturaleza
        self.saldo_actual_uf = saldo_actual_uf
        self.descripcion = descripcion


class MovimientoContable:
    """Modelo de movimiento contable"""
    def __init__(
        self,
        id: UUID = None,
        comprobante_id: UUID = None,
        cuenta_id: UUID = None,
        tipo: TipoMovimiento = TipoMovimiento.DEBE,
        monto_uf: Decimal = Decimal("0"),
        monto_pesos: int = 0,
        valor_uf_fecha: Decimal = Decimal("0"),
        glosa: str = "",
        centro_costo: Optional[str] = None,
        referencia: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.comprobante_id = comprobante_id
        self.cuenta_id = cuenta_id
        self.tipo = tipo
        self.monto_uf = monto_uf
        self.monto_pesos = monto_pesos
        self.valor_uf_fecha = valor_uf_fecha
        self.glosa = glosa
        self.centro_costo = centro_costo
        self.referencia = referencia


class ComprobanteContable:
    """Modelo de comprobante contable"""
    def __init__(
        self,
        id: UUID = None,
        numero: int = 0,
        tipo: TipoComprobante = TipoComprobante.INGRESO,
        fecha: date = None,
        periodo: str = "",
        glosa: str = "",
        estado: EstadoComprobante = EstadoComprobante.BORRADOR,
        movimientos: List[MovimientoContable] = None,
        total_debe_uf: Decimal = Decimal("0"),
        total_haber_uf: Decimal = Decimal("0"),
        cuadrado: bool = False,
        usuario_id: UUID = None,
        documento_respaldo: Optional[str] = None,
        creado_en: datetime = None,
        contabilizado_en: Optional[datetime] = None
    ):
        self.id = id or uuid4()
        self.numero = numero
        self.tipo = tipo
        self.fecha = fecha or date.today()
        self.periodo = periodo or self.fecha.strftime("%Y%m")
        self.glosa = glosa
        self.estado = estado
        self.movimientos = movimientos or []
        self.total_debe_uf = total_debe_uf
        self.total_haber_uf = total_haber_uf
        self.cuadrado = cuadrado
        self.usuario_id = usuario_id
        self.documento_respaldo = documento_respaldo
        self.creado_en = creado_en or datetime.now()
        self.contabilizado_en = contabilizado_en


class DocumentoTributario:
    """Modelo de documento tributario electrónico (DTE)"""
    def __init__(
        self,
        id: UUID = None,
        tipo_dte: TipoDocumentoTributario = TipoDocumentoTributario.FACTURA,
        folio: int = 0,
        fecha_emision: date = None,
        rut_emisor: str = "",
        razon_social_emisor: str = "",
        rut_receptor: str = "",
        razon_social_receptor: str = "",
        monto_neto: int = 0,
        monto_iva: int = 0,
        monto_total: int = 0,
        tasa_iva_pct: Decimal = Decimal("19"),
        exento: bool = False,
        estado_sii: str = "pendiente",
        track_id: Optional[str] = None,
        xml_dte: Optional[str] = None,
        pdf_dte: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.tipo_dte = tipo_dte
        self.folio = folio
        self.fecha_emision = fecha_emision or date.today()
        self.rut_emisor = rut_emisor
        self.razon_social_emisor = razon_social_emisor
        self.rut_receptor = rut_receptor
        self.razon_social_receptor = razon_social_receptor
        self.monto_neto = monto_neto
        self.monto_iva = monto_iva
        self.monto_total = monto_total
        self.tasa_iva_pct = tasa_iva_pct
        self.exento = exento
        self.estado_sii = estado_sii
        self.track_id = track_id
        self.xml_dte = xml_dte
        self.pdf_dte = pdf_dte


class ActivoFijo:
    """Modelo de activo fijo para depreciación"""
    def __init__(
        self,
        id: UUID = None,
        codigo: str = "",
        descripcion: str = "",
        fecha_adquisicion: date = None,
        valor_adquisicion_uf: Decimal = Decimal("0"),
        vida_util_anos: int = 0,
        vida_util_tributaria_anos: int = 0,
        metodo_depreciacion: MetodoDepreciacion = MetodoDepreciacion.LINEAL,
        valor_residual_uf: Decimal = Decimal("0"),
        depreciacion_acumulada_uf: Decimal = Decimal("0"),
        valor_libro_uf: Decimal = Decimal("0"),
        cuenta_activo_id: UUID = None,
        cuenta_depreciacion_id: UUID = None,
        cuenta_gasto_id: UUID = None,
        ubicacion: Optional[str] = None,
        responsable: Optional[str] = None,
        dado_baja: bool = False,
        fecha_baja: Optional[date] = None
    ):
        self.id = id or uuid4()
        self.codigo = codigo
        self.descripcion = descripcion
        self.fecha_adquisicion = fecha_adquisicion or date.today()
        self.valor_adquisicion_uf = valor_adquisicion_uf
        self.vida_util_anos = vida_util_anos
        self.vida_util_tributaria_anos = vida_util_tributaria_anos
        self.metodo_depreciacion = metodo_depreciacion
        self.valor_residual_uf = valor_residual_uf
        self.depreciacion_acumulada_uf = depreciacion_acumulada_uf
        self.valor_libro_uf = valor_libro_uf
        self.cuenta_activo_id = cuenta_activo_id
        self.cuenta_depreciacion_id = cuenta_depreciacion_id
        self.cuenta_gasto_id = cuenta_gasto_id
        self.ubicacion = ubicacion
        self.responsable = responsable
        self.dado_baja = dado_baja
        self.fecha_baja = fecha_baja


class DeclaracionImpuesto:
    """Modelo de declaración de impuestos"""
    def __init__(
        self,
        id: UUID = None,
        tipo: TipoImpuesto = TipoImpuesto.IVA,
        periodo: str = "",
        formulario: str = "29",
        fecha_vencimiento: date = None,
        base_imponible: int = 0,
        debito_fiscal: int = 0,
        credito_fiscal: int = 0,
        impuesto_determinado: int = 0,
        remanente_anterior: int = 0,
        remanente_periodo: int = 0,
        ppm_pagado: int = 0,
        total_a_pagar: int = 0,
        estado: str = "pendiente",
        fecha_presentacion: Optional[date] = None,
        folio_sii: Optional[str] = None
    ):
        self.id = id or uuid4()
        self.tipo = tipo
        self.periodo = periodo
        self.formulario = formulario
        self.fecha_vencimiento = fecha_vencimiento
        self.base_imponible = base_imponible
        self.debito_fiscal = debito_fiscal
        self.credito_fiscal = credito_fiscal
        self.impuesto_determinado = impuesto_determinado
        self.remanente_anterior = remanente_anterior
        self.remanente_periodo = remanente_periodo
        self.ppm_pagado = ppm_pagado
        self.total_a_pagar = total_a_pagar
        self.estado = estado
        self.fecha_presentacion = fecha_presentacion
        self.folio_sii = folio_sii


# =============================================================================
# PLAN DE CUENTAS ESTÁNDAR DATAPOLIS
# =============================================================================

PLAN_CUENTAS_DATAPOLIS = {
    # ACTIVOS
    "1": {"nombre": "ACTIVOS", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 1},
    "1.1": {"nombre": "Activo Circulante", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 2},
    "1.1.01": {"nombre": "Caja", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11100"},
    "1.1.02": {"nombre": "Banco Estado CTA CTE", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11110"},
    "1.1.03": {"nombre": "Banco Chile CTA CTE", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11110"},
    "1.1.04": {"nombre": "Fondo Reserva", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11120"},
    "1.1.05": {"nombre": "Cuentas por Cobrar Copropietarios", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11210"},
    "1.1.06": {"nombre": "Cuentas por Cobrar Arriendos", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11210"},
    "1.1.07": {"nombre": "Deudores Morosos", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11220"},
    "1.1.08": {"nombre": "Anticipos Proveedores", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11310"},
    "1.1.09": {"nombre": "IVA Crédito Fiscal", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11410"},
    "1.1.10": {"nombre": "PPM por Recuperar", "tipo": TipoCuenta.ACTIVO_CIRCULANTE, "nivel": 3, "sii": "11420"},
    
    "1.2": {"nombre": "Activo Fijo", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 2},
    "1.2.01": {"nombre": "Terrenos", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12110"},
    "1.2.02": {"nombre": "Edificios y Construcciones", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12120"},
    "1.2.03": {"nombre": "Depreciación Acum. Edificios", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12121"},
    "1.2.04": {"nombre": "Instalaciones", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12130"},
    "1.2.05": {"nombre": "Depreciación Acum. Instalaciones", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12131"},
    "1.2.06": {"nombre": "Maquinarias y Equipos", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12140"},
    "1.2.07": {"nombre": "Depreciación Acum. Maquinarias", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12141"},
    "1.2.08": {"nombre": "Muebles y Útiles", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12150"},
    "1.2.09": {"nombre": "Depreciación Acum. Muebles", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12151"},
    "1.2.10": {"nombre": "Vehículos", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12160"},
    "1.2.11": {"nombre": "Depreciación Acum. Vehículos", "tipo": TipoCuenta.ACTIVO_FIJO, "nivel": 3, "sii": "12161"},
    
    # PASIVOS
    "2": {"nombre": "PASIVOS", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 1},
    "2.1": {"nombre": "Pasivo Circulante", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 2},
    "2.1.01": {"nombre": "Proveedores", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21110"},
    "2.1.02": {"nombre": "Acreedores Varios", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21120"},
    "2.1.03": {"nombre": "Anticipos Copropietarios", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21130"},
    "2.1.04": {"nombre": "Remuneraciones por Pagar", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21210"},
    "2.1.05": {"nombre": "Honorarios por Pagar", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21220"},
    "2.1.06": {"nombre": "Retenciones por Pagar", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21310"},
    "2.1.07": {"nombre": "IVA Débito Fiscal", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21410"},
    "2.1.08": {"nombre": "PPM por Pagar", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21420"},
    "2.1.09": {"nombre": "Impuesto Renta por Pagar", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21430"},
    "2.1.10": {"nombre": "Provisiones Gastos", "tipo": TipoCuenta.PASIVO_CIRCULANTE, "nivel": 3, "sii": "21510"},
    
    "2.2": {"nombre": "Pasivo Largo Plazo", "tipo": TipoCuenta.PASIVO_LARGO_PLAZO, "nivel": 2},
    "2.2.01": {"nombre": "Préstamos Bancarios LP", "tipo": TipoCuenta.PASIVO_LARGO_PLAZO, "nivel": 3, "sii": "22110"},
    "2.2.02": {"nombre": "Fondo de Reserva Obligatorio", "tipo": TipoCuenta.PASIVO_LARGO_PLAZO, "nivel": 3, "sii": "22210"},
    
    # PATRIMONIO
    "3": {"nombre": "PATRIMONIO", "tipo": TipoCuenta.PATRIMONIO, "nivel": 1},
    "3.1": {"nombre": "Capital", "tipo": TipoCuenta.PATRIMONIO, "nivel": 2},
    "3.1.01": {"nombre": "Capital Pagado", "tipo": TipoCuenta.PATRIMONIO, "nivel": 3, "sii": "31110"},
    "3.1.02": {"nombre": "Reservas", "tipo": TipoCuenta.PATRIMONIO, "nivel": 3, "sii": "31210"},
    "3.1.03": {"nombre": "Resultados Acumulados", "tipo": TipoCuenta.PATRIMONIO, "nivel": 3, "sii": "31310"},
    "3.1.04": {"nombre": "Resultado del Ejercicio", "tipo": TipoCuenta.PATRIMONIO, "nivel": 3, "sii": "31320"},
    
    # INGRESOS
    "4": {"nombre": "INGRESOS", "tipo": TipoCuenta.INGRESO, "nivel": 1},
    "4.1": {"nombre": "Ingresos Operacionales", "tipo": TipoCuenta.INGRESO, "nivel": 2},
    "4.1.01": {"nombre": "Gastos Comunes Ordinarios", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41110"},
    "4.1.02": {"nombre": "Gastos Comunes Extraordinarios", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41120"},
    "4.1.03": {"nombre": "Fondo de Reserva", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41130"},
    "4.1.04": {"nombre": "Arriendos Percibidos", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41210"},
    "4.1.05": {"nombre": "Servicios Administración", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41310"},
    "4.1.06": {"nombre": "Ingresos por Antenas (Ley 21.713)", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "41410"},
    
    "4.2": {"nombre": "Otros Ingresos", "tipo": TipoCuenta.INGRESO, "nivel": 2},
    "4.2.01": {"nombre": "Intereses Ganados", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "42110"},
    "4.2.02": {"nombre": "Multas e Intereses Morosos", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "42120"},
    "4.2.03": {"nombre": "Otros Ingresos Varios", "tipo": TipoCuenta.INGRESO, "nivel": 3, "sii": "42130"},
    
    # GASTOS
    "5": {"nombre": "GASTOS", "tipo": TipoCuenta.GASTO, "nivel": 1},
    "5.1": {"nombre": "Gastos Operacionales", "tipo": TipoCuenta.GASTO, "nivel": 2},
    "5.1.01": {"nombre": "Remuneraciones", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51110"},
    "5.1.02": {"nombre": "Leyes Sociales", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51120"},
    "5.1.03": {"nombre": "Honorarios", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51210"},
    "5.1.04": {"nombre": "Servicios Básicos (Agua, Luz, Gas)", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51310"},
    "5.1.05": {"nombre": "Aseo y Mantención", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51320"},
    "5.1.06": {"nombre": "Seguridad y Vigilancia", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51330"},
    "5.1.07": {"nombre": "Jardinería", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51340"},
    "5.1.08": {"nombre": "Reparaciones y Mantenciones", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51350"},
    "5.1.09": {"nombre": "Seguros", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51410"},
    "5.1.10": {"nombre": "Contribuciones", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51420"},
    "5.1.11": {"nombre": "Gastos Legales", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51510"},
    "5.1.12": {"nombre": "Gastos de Cobranza", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51520"},
    "5.1.13": {"nombre": "Gastos Bancarios", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51610"},
    "5.1.14": {"nombre": "Depreciación del Ejercicio", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51710"},
    "5.1.15": {"nombre": "Gastos Varios", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "51810"},
    
    "5.2": {"nombre": "Gastos Financieros", "tipo": TipoCuenta.GASTO, "nivel": 2},
    "5.2.01": {"nombre": "Intereses Préstamos", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "52110"},
    "5.2.02": {"nombre": "Comisiones Bancarias", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "52120"},
    "5.2.03": {"nombre": "Diferencias de Cambio", "tipo": TipoCuenta.GASTO, "nivel": 3, "sii": "52130"},
}


# =============================================================================
# SERVICIO DE CONTABILIDAD
# =============================================================================

class ContabilidadService:
    """
    Servicio de contabilidad y finanzas DATAPOLIS v3.0
    
    Funcionalidades:
    - Plan de cuentas según PCGA Chile
    - Comprobantes contables (ingreso, egreso, traspaso)
    - Libro diario y mayor
    - Balance general y estado de resultados
    - Depreciación de activos fijos
    - Libro compras/ventas SII
    - Declaraciones F29 y DJAT
    - Reportes CMF para condominios
    """
    
    def __init__(self):
        self.cuentas: Dict[UUID, CuentaContable] = {}
        self.comprobantes: Dict[UUID, ComprobanteContable] = {}
        self.documentos_tributarios: Dict[UUID, DocumentoTributario] = {}
        self.activos_fijos: Dict[UUID, ActivoFijo] = {}
        self.declaraciones: Dict[UUID, DeclaracionImpuesto] = {}
        self._inicializar_plan_cuentas()
    
    def _inicializar_plan_cuentas(self):
        """Inicializa el plan de cuentas estándar"""
        for codigo, datos in PLAN_CUENTAS_DATAPOLIS.items():
            cuenta = CuentaContable(
                codigo=codigo,
                nombre=datos["nombre"],
                tipo=datos["tipo"],
                nivel=datos["nivel"],
                cuenta_sii=datos.get("sii"),
                acepta_movimientos=datos["nivel"] >= 3
            )
            self.cuentas[cuenta.id] = cuenta
    
    # =========================================================================
    # GESTIÓN DE CUENTAS
    # =========================================================================
    
    async def crear_cuenta(
        self,
        codigo: str,
        nombre: str,
        tipo: TipoCuenta,
        nivel: int = 3,
        cuenta_padre_codigo: Optional[str] = None,
        cuenta_sii: Optional[str] = None,
        descripcion: Optional[str] = None
    ) -> CuentaContable:
        """Crea una nueva cuenta contable"""
        
        # Validar código único
        for cuenta in self.cuentas.values():
            if cuenta.codigo == codigo:
                raise ValueError(f"Ya existe cuenta con código {codigo}")
        
        # Buscar cuenta padre
        cuenta_padre_id = None
        if cuenta_padre_codigo:
            for cuenta in self.cuentas.values():
                if cuenta.codigo == cuenta_padre_codigo:
                    cuenta_padre_id = cuenta.id
                    break
        
        # Determinar naturaleza
        naturaleza = TipoMovimiento.DEBE
        if tipo in [TipoCuenta.PASIVO_CIRCULANTE, TipoCuenta.PASIVO_LARGO_PLAZO, 
                    TipoCuenta.PATRIMONIO, TipoCuenta.INGRESO]:
            naturaleza = TipoMovimiento.HABER
        
        cuenta = CuentaContable(
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            nivel=nivel,
            cuenta_padre_id=cuenta_padre_id,
            cuenta_sii=cuenta_sii,
            naturaleza=naturaleza,
            descripcion=descripcion
        )
        
        self.cuentas[cuenta.id] = cuenta
        return cuenta
    
    async def obtener_plan_cuentas(
        self,
        tipo: Optional[TipoCuenta] = None,
        nivel: Optional[int] = None,
        activas_solo: bool = True
    ) -> List[CuentaContable]:
        """Obtiene el plan de cuentas con filtros"""
        cuentas = list(self.cuentas.values())
        
        if tipo:
            cuentas = [c for c in cuentas if c.tipo == tipo]
        if nivel:
            cuentas = [c for c in cuentas if c.nivel == nivel]
        if activas_solo:
            cuentas = [c for c in cuentas if c.activa]
        
        return sorted(cuentas, key=lambda c: c.codigo)
    
    async def obtener_saldo_cuenta(
        self,
        cuenta_id: UUID,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None
    ) -> Dict[str, Any]:
        """Obtiene saldo de una cuenta con movimientos"""
        
        cuenta = self.cuentas.get(cuenta_id)
        if not cuenta:
            raise ValueError("Cuenta no encontrada")
        
        # Filtrar movimientos por fecha
        movimientos = []
        total_debe = Decimal("0")
        total_haber = Decimal("0")
        
        for comprobante in self.comprobantes.values():
            if comprobante.estado != EstadoComprobante.CONTABILIZADO:
                continue
            
            if fecha_desde and comprobante.fecha < fecha_desde:
                continue
            if fecha_hasta and comprobante.fecha > fecha_hasta:
                continue
            
            for mov in comprobante.movimientos:
                if mov.cuenta_id == cuenta_id:
                    movimientos.append({
                        "fecha": comprobante.fecha,
                        "comprobante": comprobante.numero,
                        "glosa": mov.glosa,
                        "debe": mov.monto_uf if mov.tipo == TipoMovimiento.DEBE else Decimal("0"),
                        "haber": mov.monto_uf if mov.tipo == TipoMovimiento.HABER else Decimal("0")
                    })
                    if mov.tipo == TipoMovimiento.DEBE:
                        total_debe += mov.monto_uf
                    else:
                        total_haber += mov.monto_uf
        
        # Calcular saldo según naturaleza
        if cuenta.naturaleza == TipoMovimiento.DEBE:
            saldo = total_debe - total_haber
        else:
            saldo = total_haber - total_debe
        
        return {
            "cuenta": cuenta,
            "movimientos": movimientos,
            "total_debe_uf": total_debe,
            "total_haber_uf": total_haber,
            "saldo_uf": saldo
        }
    
    # =========================================================================
    # COMPROBANTES CONTABLES
    # =========================================================================
    
    async def crear_comprobante(
        self,
        tipo: TipoComprobante,
        fecha: date,
        glosa: str,
        movimientos: List[Dict[str, Any]],
        usuario_id: UUID,
        documento_respaldo: Optional[str] = None,
        contabilizar_automatico: bool = False
    ) -> ComprobanteContable:
        """Crea un nuevo comprobante contable"""
        
        # Generar número correlativo
        periodo = fecha.strftime("%Y%m")
        comprobantes_periodo = [
            c for c in self.comprobantes.values()
            if c.periodo == periodo and c.tipo == tipo
        ]
        numero = len(comprobantes_periodo) + 1
        
        # Crear movimientos
        movs = []
        total_debe = Decimal("0")
        total_haber = Decimal("0")
        
        for mov_data in movimientos:
            # Buscar cuenta
            cuenta = None
            for c in self.cuentas.values():
                if c.codigo == mov_data.get("cuenta_codigo") or c.id == mov_data.get("cuenta_id"):
                    cuenta = c
                    break
            
            if not cuenta:
                raise ValueError(f"Cuenta no encontrada: {mov_data.get('cuenta_codigo')}")
            
            if not cuenta.acepta_movimientos:
                raise ValueError(f"Cuenta {cuenta.codigo} no acepta movimientos")
            
            mov = MovimientoContable(
                cuenta_id=cuenta.id,
                tipo=TipoMovimiento(mov_data["tipo"]),
                monto_uf=Decimal(str(mov_data["monto_uf"])),
                monto_pesos=mov_data.get("monto_pesos", 0),
                valor_uf_fecha=Decimal(str(mov_data.get("valor_uf", "38000"))),
                glosa=mov_data.get("glosa", glosa),
                centro_costo=mov_data.get("centro_costo"),
                referencia=mov_data.get("referencia")
            )
            movs.append(mov)
            
            if mov.tipo == TipoMovimiento.DEBE:
                total_debe += mov.monto_uf
            else:
                total_haber += mov.monto_uf
        
        # Validar cuadratura
        cuadrado = abs(total_debe - total_haber) < Decimal("0.01")
        
        comprobante = ComprobanteContable(
            numero=numero,
            tipo=tipo,
            fecha=fecha,
            periodo=periodo,
            glosa=glosa,
            movimientos=movs,
            total_debe_uf=total_debe,
            total_haber_uf=total_haber,
            cuadrado=cuadrado,
            usuario_id=usuario_id,
            documento_respaldo=documento_respaldo
        )
        
        self.comprobantes[comprobante.id] = comprobante
        
        # Contabilizar automáticamente si está cuadrado
        if contabilizar_automatico and cuadrado:
            await self.contabilizar_comprobante(comprobante.id)
        
        return comprobante
    
    async def contabilizar_comprobante(self, comprobante_id: UUID) -> ComprobanteContable:
        """Contabiliza un comprobante (pasa de borrador a contabilizado)"""
        
        comprobante = self.comprobantes.get(comprobante_id)
        if not comprobante:
            raise ValueError("Comprobante no encontrado")
        
        if comprobante.estado != EstadoComprobante.BORRADOR:
            raise ValueError(f"Comprobante en estado {comprobante.estado}, no se puede contabilizar")
        
        if not comprobante.cuadrado:
            raise ValueError("Comprobante no está cuadrado")
        
        comprobante.estado = EstadoComprobante.CONTABILIZADO
        comprobante.contabilizado_en = datetime.now()
        
        # Actualizar saldos de cuentas
        for mov in comprobante.movimientos:
            cuenta = self.cuentas.get(mov.cuenta_id)
            if cuenta:
                if mov.tipo == TipoMovimiento.DEBE:
                    if cuenta.naturaleza == TipoMovimiento.DEBE:
                        cuenta.saldo_actual_uf += mov.monto_uf
                    else:
                        cuenta.saldo_actual_uf -= mov.monto_uf
                else:
                    if cuenta.naturaleza == TipoMovimiento.HABER:
                        cuenta.saldo_actual_uf += mov.monto_uf
                    else:
                        cuenta.saldo_actual_uf -= mov.monto_uf
        
        return comprobante
    
    async def anular_comprobante(
        self,
        comprobante_id: UUID,
        motivo: str,
        usuario_id: UUID
    ) -> ComprobanteContable:
        """Anula un comprobante contabilizado"""
        
        comprobante = self.comprobantes.get(comprobante_id)
        if not comprobante:
            raise ValueError("Comprobante no encontrado")
        
        if comprobante.estado == EstadoComprobante.ANULADO:
            raise ValueError("Comprobante ya está anulado")
        
        # Si estaba contabilizado, revertir saldos
        if comprobante.estado == EstadoComprobante.CONTABILIZADO:
            for mov in comprobante.movimientos:
                cuenta = self.cuentas.get(mov.cuenta_id)
                if cuenta:
                    if mov.tipo == TipoMovimiento.DEBE:
                        if cuenta.naturaleza == TipoMovimiento.DEBE:
                            cuenta.saldo_actual_uf -= mov.monto_uf
                        else:
                            cuenta.saldo_actual_uf += mov.monto_uf
                    else:
                        if cuenta.naturaleza == TipoMovimiento.HABER:
                            cuenta.saldo_actual_uf -= mov.monto_uf
                        else:
                            cuenta.saldo_actual_uf += mov.monto_uf
        
        comprobante.estado = EstadoComprobante.ANULADO
        comprobante.glosa = f"{comprobante.glosa} [ANULADO: {motivo}]"
        
        return comprobante
    
    # =========================================================================
    # REPORTES CONTABLES
    # =========================================================================
    
    async def generar_balance_general(
        self,
        fecha_corte: date,
        incluir_comparativo: bool = False
    ) -> Dict[str, Any]:
        """Genera balance general a una fecha de corte"""
        
        activos = {"circulante": [], "fijo": [], "otros": []}
        pasivos = {"circulante": [], "largo_plazo": []}
        patrimonio = []
        
        total_activo = Decimal("0")
        total_pasivo = Decimal("0")
        total_patrimonio = Decimal("0")
        
        for cuenta in sorted(self.cuentas.values(), key=lambda c: c.codigo):
            if cuenta.nivel < 3 or not cuenta.acepta_movimientos:
                continue
            
            saldo_info = await self.obtener_saldo_cuenta(
                cuenta.id,
                fecha_hasta=fecha_corte
            )
            saldo = saldo_info["saldo_uf"]
            
            if abs(saldo) < Decimal("0.01"):
                continue
            
            item = {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "saldo_uf": saldo
            }
            
            if cuenta.tipo == TipoCuenta.ACTIVO_CIRCULANTE:
                activos["circulante"].append(item)
                total_activo += saldo
            elif cuenta.tipo == TipoCuenta.ACTIVO_FIJO:
                activos["fijo"].append(item)
                total_activo += saldo
            elif cuenta.tipo == TipoCuenta.PASIVO_CIRCULANTE:
                pasivos["circulante"].append(item)
                total_pasivo += saldo
            elif cuenta.tipo == TipoCuenta.PASIVO_LARGO_PLAZO:
                pasivos["largo_plazo"].append(item)
                total_pasivo += saldo
            elif cuenta.tipo == TipoCuenta.PATRIMONIO:
                patrimonio.append(item)
                total_patrimonio += saldo
        
        return {
            "tipo_reporte": TipoReporte.BALANCE_GENERAL,
            "fecha_corte": fecha_corte,
            "generado_en": datetime.now(),
            "activos": activos,
            "pasivos": pasivos,
            "patrimonio": patrimonio,
            "total_activo_uf": total_activo,
            "total_pasivo_uf": total_pasivo,
            "total_patrimonio_uf": total_patrimonio,
            "total_pasivo_patrimonio_uf": total_pasivo + total_patrimonio,
            "cuadrado": abs(total_activo - (total_pasivo + total_patrimonio)) < Decimal("0.01")
        }
    
    async def generar_estado_resultados(
        self,
        fecha_desde: date,
        fecha_hasta: date
    ) -> Dict[str, Any]:
        """Genera estado de resultados para un período"""
        
        ingresos = []
        gastos = []
        total_ingresos = Decimal("0")
        total_gastos = Decimal("0")
        
        for cuenta in sorted(self.cuentas.values(), key=lambda c: c.codigo):
            if cuenta.nivel < 3 or not cuenta.acepta_movimientos:
                continue
            
            saldo_info = await self.obtener_saldo_cuenta(
                cuenta.id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
            saldo = saldo_info["saldo_uf"]
            
            if abs(saldo) < Decimal("0.01"):
                continue
            
            item = {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "monto_uf": saldo
            }
            
            if cuenta.tipo == TipoCuenta.INGRESO:
                ingresos.append(item)
                total_ingresos += saldo
            elif cuenta.tipo == TipoCuenta.GASTO:
                gastos.append(item)
                total_gastos += saldo
        
        resultado_operacional = total_ingresos - total_gastos
        
        return {
            "tipo_reporte": TipoReporte.ESTADO_RESULTADOS,
            "periodo": f"{fecha_desde} a {fecha_hasta}",
            "generado_en": datetime.now(),
            "ingresos": ingresos,
            "gastos": gastos,
            "total_ingresos_uf": total_ingresos,
            "total_gastos_uf": total_gastos,
            "resultado_operacional_uf": resultado_operacional,
            "utilidad_neta_uf": resultado_operacional,
            "margen_operacional_pct": (
                (resultado_operacional / total_ingresos * 100)
                if total_ingresos > 0 else Decimal("0")
            )
        }
    
    async def generar_libro_mayor(
        self,
        cuenta_codigo: str,
        fecha_desde: date,
        fecha_hasta: date
    ) -> Dict[str, Any]:
        """Genera libro mayor para una cuenta"""
        
        cuenta = None
        for c in self.cuentas.values():
            if c.codigo == cuenta_codigo:
                cuenta = c
                break
        
        if not cuenta:
            raise ValueError(f"Cuenta {cuenta_codigo} no encontrada")
        
        saldo_info = await self.obtener_saldo_cuenta(
            cuenta.id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        return {
            "tipo_reporte": TipoReporte.LIBRO_MAYOR,
            "cuenta": {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "tipo": cuenta.tipo.value
            },
            "periodo": f"{fecha_desde} a {fecha_hasta}",
            "movimientos": saldo_info["movimientos"],
            "total_debe_uf": saldo_info["total_debe_uf"],
            "total_haber_uf": saldo_info["total_haber_uf"],
            "saldo_final_uf": saldo_info["saldo_uf"]
        }
    
    async def generar_libro_diario(
        self,
        fecha_desde: date,
        fecha_hasta: date
    ) -> Dict[str, Any]:
        """Genera libro diario para un período"""
        
        asientos = []
        
        for comprobante in sorted(
            self.comprobantes.values(),
            key=lambda c: (c.fecha, c.numero)
        ):
            if comprobante.estado != EstadoComprobante.CONTABILIZADO:
                continue
            if comprobante.fecha < fecha_desde or comprobante.fecha > fecha_hasta:
                continue
            
            lineas = []
            for mov in comprobante.movimientos:
                cuenta = self.cuentas.get(mov.cuenta_id)
                lineas.append({
                    "cuenta_codigo": cuenta.codigo if cuenta else "???",
                    "cuenta_nombre": cuenta.nombre if cuenta else "Desconocida",
                    "debe_uf": mov.monto_uf if mov.tipo == TipoMovimiento.DEBE else Decimal("0"),
                    "haber_uf": mov.monto_uf if mov.tipo == TipoMovimiento.HABER else Decimal("0"),
                    "glosa": mov.glosa
                })
            
            asientos.append({
                "numero": comprobante.numero,
                "fecha": comprobante.fecha,
                "tipo": comprobante.tipo.value,
                "glosa": comprobante.glosa,
                "lineas": lineas,
                "total_uf": comprobante.total_debe_uf
            })
        
        return {
            "tipo_reporte": TipoReporte.LIBRO_DIARIO,
            "periodo": f"{fecha_desde} a {fecha_hasta}",
            "generado_en": datetime.now(),
            "asientos": asientos,
            "total_asientos": len(asientos)
        }
    
    # =========================================================================
    # DEPRECIACIÓN DE ACTIVOS FIJOS
    # =========================================================================
    
    async def registrar_activo_fijo(
        self,
        codigo: str,
        descripcion: str,
        fecha_adquisicion: date,
        valor_adquisicion_uf: Decimal,
        vida_util_anos: int,
        vida_util_tributaria_anos: int,
        metodo: MetodoDepreciacion,
        valor_residual_uf: Decimal,
        cuenta_activo_codigo: str,
        cuenta_depreciacion_codigo: str,
        cuenta_gasto_codigo: str,
        ubicacion: Optional[str] = None
    ) -> ActivoFijo:
        """Registra un nuevo activo fijo"""
        
        # Buscar cuentas
        cuenta_activo = None
        cuenta_depreciacion = None
        cuenta_gasto = None
        
        for c in self.cuentas.values():
            if c.codigo == cuenta_activo_codigo:
                cuenta_activo = c
            elif c.codigo == cuenta_depreciacion_codigo:
                cuenta_depreciacion = c
            elif c.codigo == cuenta_gasto_codigo:
                cuenta_gasto = c
        
        activo = ActivoFijo(
            codigo=codigo,
            descripcion=descripcion,
            fecha_adquisicion=fecha_adquisicion,
            valor_adquisicion_uf=valor_adquisicion_uf,
            vida_util_anos=vida_util_anos,
            vida_util_tributaria_anos=vida_util_tributaria_anos,
            metodo_depreciacion=metodo,
            valor_residual_uf=valor_residual_uf,
            valor_libro_uf=valor_adquisicion_uf,
            cuenta_activo_id=cuenta_activo.id if cuenta_activo else None,
            cuenta_depreciacion_id=cuenta_depreciacion.id if cuenta_depreciacion else None,
            cuenta_gasto_id=cuenta_gasto.id if cuenta_gasto else None,
            ubicacion=ubicacion
        )
        
        self.activos_fijos[activo.id] = activo
        return activo
    
    async def calcular_depreciacion_mensual(
        self,
        activo_id: UUID
    ) -> Dict[str, Any]:
        """Calcula depreciación mensual de un activo"""
        
        activo = self.activos_fijos.get(activo_id)
        if not activo:
            raise ValueError("Activo fijo no encontrado")
        
        if activo.dado_baja:
            raise ValueError("Activo dado de baja")
        
        base_depreciable = activo.valor_adquisicion_uf - activo.valor_residual_uf
        
        if activo.metodo_depreciacion == MetodoDepreciacion.LINEAL:
            # Depreciación lineal: valor / vida útil / 12
            depreciacion_anual = base_depreciable / activo.vida_util_anos
            depreciacion_mensual = depreciacion_anual / 12
        
        elif activo.metodo_depreciacion == MetodoDepreciacion.ACELERADA:
            # Depreciación acelerada: vida útil tributaria (1/3)
            depreciacion_anual = base_depreciable / activo.vida_util_tributaria_anos
            depreciacion_mensual = depreciacion_anual / 12
        
        else:
            depreciacion_mensual = base_depreciable / (activo.vida_util_anos * 12)
        
        # No depreciar más allá del valor residual
        if activo.valor_libro_uf - depreciacion_mensual < activo.valor_residual_uf:
            depreciacion_mensual = activo.valor_libro_uf - activo.valor_residual_uf
        
        return {
            "activo": activo,
            "depreciacion_mensual_uf": depreciacion_mensual,
            "depreciacion_anual_uf": depreciacion_mensual * 12,
            "valor_libro_actual_uf": activo.valor_libro_uf,
            "valor_libro_proyectado_uf": activo.valor_libro_uf - depreciacion_mensual,
            "depreciacion_acumulada_uf": activo.depreciacion_acumulada_uf + depreciacion_mensual
        }
    
    async def procesar_depreciacion_periodo(
        self,
        fecha: date,
        usuario_id: UUID
    ) -> Dict[str, Any]:
        """Procesa depreciación de todos los activos para un período"""
        
        activos_procesados = []
        total_depreciacion = Decimal("0")
        
        for activo in self.activos_fijos.values():
            if activo.dado_baja:
                continue
            
            if activo.valor_libro_uf <= activo.valor_residual_uf:
                continue
            
            try:
                calc = await self.calcular_depreciacion_mensual(activo.id)
                dep = calc["depreciacion_mensual_uf"]
                
                if dep > 0:
                    # Actualizar activo
                    activo.depreciacion_acumulada_uf += dep
                    activo.valor_libro_uf -= dep
                    
                    activos_procesados.append({
                        "activo_codigo": activo.codigo,
                        "activo_descripcion": activo.descripcion,
                        "depreciacion_uf": dep
                    })
                    total_depreciacion += dep
                    
            except Exception as e:
                print(f"Error depreciando {activo.codigo}: {e}")
        
        # Crear comprobante de depreciación si hay monto
        comprobante = None
        if total_depreciacion > 0:
            movimientos = []
            
            # Por cada activo, crear movimientos
            for activo_info in activos_procesados:
                activo = None
                for a in self.activos_fijos.values():
                    if a.codigo == activo_info["activo_codigo"]:
                        activo = a
                        break
                
                if activo and activo.cuenta_depreciacion_id and activo.cuenta_gasto_id:
                    cuenta_dep = self.cuentas.get(activo.cuenta_depreciacion_id)
                    cuenta_gasto = self.cuentas.get(activo.cuenta_gasto_id)
                    
                    # Gasto depreciación (debe)
                    movimientos.append({
                        "cuenta_id": cuenta_gasto.id,
                        "tipo": "debe",
                        "monto_uf": activo_info["depreciacion_uf"],
                        "glosa": f"Depreciación {activo.descripcion}"
                    })
                    
                    # Depreciación acumulada (haber)
                    movimientos.append({
                        "cuenta_id": cuenta_dep.id,
                        "tipo": "haber",
                        "monto_uf": activo_info["depreciacion_uf"],
                        "glosa": f"Depreciación {activo.descripcion}"
                    })
            
            if movimientos:
                comprobante = await self.crear_comprobante(
                    tipo=TipoComprobante.DEPRECIACION,
                    fecha=fecha,
                    glosa=f"Depreciación activos fijos {fecha.strftime('%Y-%m')}",
                    movimientos=movimientos,
                    usuario_id=usuario_id,
                    contabilizar_automatico=True
                )
        
        return {
            "periodo": fecha.strftime("%Y-%m"),
            "activos_procesados": activos_procesados,
            "total_depreciacion_uf": total_depreciacion,
            "comprobante_id": comprobante.id if comprobante else None,
            "comprobante_numero": comprobante.numero if comprobante else None
        }
    
    # =========================================================================
    # DOCUMENTOS TRIBUTARIOS (DTE)
    # =========================================================================
    
    async def registrar_documento_compra(
        self,
        tipo_dte: TipoDocumentoTributario,
        folio: int,
        fecha_emision: date,
        rut_emisor: str,
        razon_social_emisor: str,
        monto_neto: int,
        monto_iva: int = None,
        exento: bool = False
    ) -> DocumentoTributario:
        """Registra un documento de compra (libro compras)"""
        
        if monto_iva is None and not exento:
            monto_iva = int(monto_neto * 0.19)
        elif exento:
            monto_iva = 0
        
        doc = DocumentoTributario(
            tipo_dte=tipo_dte,
            folio=folio,
            fecha_emision=fecha_emision,
            rut_emisor=rut_emisor,
            razon_social_emisor=razon_social_emisor,
            rut_receptor="76.xxx.xxx-x",  # RUT copropiedad
            razon_social_receptor="Comunidad Edificio XXX",
            monto_neto=monto_neto,
            monto_iva=monto_iva,
            monto_total=monto_neto + monto_iva,
            exento=exento
        )
        
        self.documentos_tributarios[doc.id] = doc
        return doc
    
    async def generar_libro_compras(
        self,
        periodo: str  # formato YYYYMM
    ) -> Dict[str, Any]:
        """Genera libro de compras para un período"""
        
        year = int(periodo[:4])
        month = int(periodo[4:])
        
        documentos = []
        total_neto = 0
        total_iva = 0
        total_exento = 0
        
        for doc in sorted(
            self.documentos_tributarios.values(),
            key=lambda d: (d.fecha_emision, d.folio)
        ):
            if doc.fecha_emision.year != year or doc.fecha_emision.month != month:
                continue
            
            documentos.append({
                "tipo_dte": doc.tipo_dte.value,
                "folio": doc.folio,
                "fecha": doc.fecha_emision,
                "rut_emisor": doc.rut_emisor,
                "razon_social": doc.razon_social_emisor,
                "neto": doc.monto_neto,
                "iva": doc.monto_iva,
                "total": doc.monto_total
            })
            
            if doc.exento:
                total_exento += doc.monto_neto
            else:
                total_neto += doc.monto_neto
                total_iva += doc.monto_iva
        
        return {
            "periodo": periodo,
            "generado_en": datetime.now(),
            "documentos": documentos,
            "total_documentos": len(documentos),
            "total_neto": total_neto,
            "total_iva_credito": total_iva,
            "total_exento": total_exento,
            "total_general": total_neto + total_iva + total_exento
        }
    
    async def preparar_f29(
        self,
        periodo: str
    ) -> Dict[str, Any]:
        """Prepara datos para formulario F29"""
        
        libro_compras = await self.generar_libro_compras(periodo)
        
        # Calcular débitos (ventas/ingresos afectos)
        # En condominios generalmente no hay débito
        debito_fiscal = 0
        base_imponible_ventas = 0
        
        credito_fiscal = libro_compras["total_iva_credito"]
        
        # IVA determinado
        if debito_fiscal > credito_fiscal:
            iva_determinado = debito_fiscal - credito_fiscal
            remanente = 0
        else:
            iva_determinado = 0
            remanente = credito_fiscal - debito_fiscal
        
        return {
            "formulario": "29",
            "periodo": periodo,
            "fecha_vencimiento": self._calcular_vencimiento_f29(periodo),
            "ventas_afectas": base_imponible_ventas,
            "debito_fiscal": debito_fiscal,
            "compras_afectas": libro_compras["total_neto"],
            "credito_fiscal": credito_fiscal,
            "iva_determinado": iva_determinado,
            "remanente_credito": remanente,
            "ppm": 0,
            "total_a_pagar": iva_determinado,
            "libro_compras": libro_compras
        }
    
    def _calcular_vencimiento_f29(self, periodo: str) -> date:
        """Calcula fecha vencimiento F29"""
        year = int(periodo[:4])
        month = int(periodo[4:])
        
        # F29 vence día 12 del mes siguiente
        if month == 12:
            return date(year + 1, 1, 12)
        else:
            return date(year, month + 1, 12)
    
    # =========================================================================
    # REPORTES CMF CONDOMINIOS
    # =========================================================================
    
    async def generar_reporte_cmf(
        self,
        copropiedad_id: UUID,
        periodo: str
    ) -> Dict[str, Any]:
        """Genera reporte para CMF según Ley 21.442"""
        
        year = int(periodo[:4])
        month = int(periodo[4:])
        
        # Obtener datos financieros
        balance = await self.generar_balance_general(
            fecha_corte=date(year, month, 28)
        )
        
        resultados = await self.generar_estado_resultados(
            fecha_desde=date(year, month, 1),
            fecha_hasta=date(year, month, 28)
        )
        
        return {
            "reporte": "CMF_21442",
            "copropiedad_id": copropiedad_id,
            "periodo": periodo,
            "generado_en": datetime.now(),
            "resumen_financiero": {
                "total_activos_uf": balance["total_activo_uf"],
                "total_pasivos_uf": balance["total_pasivo_uf"],
                "patrimonio_uf": balance["total_patrimonio_uf"],
                "ingresos_periodo_uf": resultados["total_ingresos_uf"],
                "gastos_periodo_uf": resultados["total_gastos_uf"],
                "resultado_periodo_uf": resultados["utilidad_neta_uf"]
            },
            "fondo_reserva": {
                "saldo_actual_uf": Decimal("150"),  # Mock
                "aporte_periodo_uf": Decimal("15"),
                "cumple_minimo": True,
                "porcentaje_gc": Decimal("5")
            },
            "morosidad": {
                "total_morosos": 5,
                "monto_moroso_uf": Decimal("45"),
                "porcentaje_morosidad": Decimal("3.5"),
                "antiguedad_promedio_dias": 45
            },
            "cumplimiento": {
                "contabilidad_al_dia": True,
                "fondo_reserva_constituido": True,
                "cuenta_bancaria_exclusiva": True,
                "reglamento_actualizado": True
            }
        }
    
    # =========================================================================
    # CIERRES CONTABLES
    # =========================================================================
    
    async def cierre_mensual(
        self,
        periodo: str,
        usuario_id: UUID
    ) -> Dict[str, Any]:
        """Ejecuta cierre contable mensual"""
        
        year = int(periodo[:4])
        month = int(periodo[4:])
        fecha_cierre = date(year, month, 28)
        
        # Verificar todos los comprobantes contabilizados
        pendientes = [
            c for c in self.comprobantes.values()
            if c.periodo == periodo and c.estado == EstadoComprobante.BORRADOR
        ]
        
        if pendientes:
            return {
                "exito": False,
                "error": f"Hay {len(pendientes)} comprobantes pendientes de contabilizar",
                "comprobantes_pendientes": [c.numero for c in pendientes]
            }
        
        # Generar reportes
        balance = await self.generar_balance_general(fecha_cierre)
        resultados = await self.generar_estado_resultados(
            date(year, month, 1),
            fecha_cierre
        )
        
        return {
            "exito": True,
            "periodo": periodo,
            "fecha_cierre": fecha_cierre,
            "ejecutado_en": datetime.now(),
            "ejecutado_por": usuario_id,
            "balance_cuadrado": balance["cuadrado"],
            "resultado_periodo_uf": resultados["utilidad_neta_uf"],
            "total_comprobantes": len([
                c for c in self.comprobantes.values()
                if c.periodo == periodo
            ])
        }
    
    async def cierre_anual(
        self,
        ano: int,
        usuario_id: UUID
    ) -> Dict[str, Any]:
        """Ejecuta cierre contable anual"""
        
        fecha_cierre = date(ano, 12, 31)
        
        # Verificar cierres mensuales
        for mes in range(1, 13):
            periodo = f"{ano}{mes:02d}"
            # Aquí verificaríamos que el mes está cerrado
        
        # Generar balance final
        balance = await self.generar_balance_general(fecha_cierre)
        resultados = await self.generar_estado_resultados(
            date(ano, 1, 1),
            fecha_cierre
        )
        
        # Crear asiento de cierre
        # Transferir resultado a resultados acumulados
        
        return {
            "exito": True,
            "ano": ano,
            "fecha_cierre": fecha_cierre,
            "ejecutado_en": datetime.now(),
            "resultado_ejercicio_uf": resultados["utilidad_neta_uf"],
            "total_activos_uf": balance["total_activo_uf"],
            "total_pasivos_uf": balance["total_pasivo_uf"],
            "patrimonio_uf": balance["total_patrimonio_uf"]
        }


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================

contabilidad_service = ContabilidadService()


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

async def obtener_plan_cuentas() -> List[CuentaContable]:
    """Obtiene el plan de cuentas completo"""
    return await contabilidad_service.obtener_plan_cuentas()


async def crear_comprobante_ingreso(
    fecha: date,
    glosa: str,
    movimientos: List[Dict],
    usuario_id: UUID
) -> ComprobanteContable:
    """Crea un comprobante de ingreso"""
    return await contabilidad_service.crear_comprobante(
        tipo=TipoComprobante.INGRESO,
        fecha=fecha,
        glosa=glosa,
        movimientos=movimientos,
        usuario_id=usuario_id,
        contabilizar_automatico=True
    )


async def generar_balance(fecha_corte: date) -> Dict[str, Any]:
    """Genera balance general"""
    return await contabilidad_service.generar_balance_general(fecha_corte)


async def generar_estado_resultados(
    fecha_desde: date,
    fecha_hasta: date
) -> Dict[str, Any]:
    """Genera estado de resultados"""
    return await contabilidad_service.generar_estado_resultados(
        fecha_desde,
        fecha_hasta
    )
