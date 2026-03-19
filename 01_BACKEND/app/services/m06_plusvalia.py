# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Módulo M06: Plusvalía y Ganancias de Capital
=============================================================
Sistema integral para cálculo y gestión de plusvalía inmobiliaria
y ganancias de capital según normativa tributaria chilena.

Características principales:
- Cálculo de plusvalía real vs nominal
- Corrección monetaria según IPC/UF
- Determinación de ganancias de capital gravadas
- Beneficios tributarios DFL-2 y habitacionales
- Simulación de escenarios de venta
- Integración con SII y F22
- Proyección de plusvalía futura
- Análisis de rentabilidad histórica

Marco Legal:
- Ley de Impuesto a la Renta (Art. 17 N°8 letra b)
- Ley 21.210 Reforma Tributaria 2020
- Ley 21.420 Beneficios tributarios vivienda
- DFL-2 Beneficios tributarios inmobiliarios
- Circular SII N°44/2016 - Ganancias de capital
- Circular SII N°39/2020 - Nueva tributación

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

class TipoContribuyente(str, Enum):
    """Tipo de contribuyente para efectos tributarios"""
    PERSONA_NATURAL = "persona_natural"
    PERSONA_JURIDICA = "persona_juridica"
    SOCIEDAD_INVERSIONES = "sociedad_inversiones"
    FONDO_INVERSION = "fondo_inversion"


class RegimenTributario(str, Enum):
    """Régimen tributario del contribuyente"""
    PRIMERA_CATEGORIA = "primera_categoria"          # 27% empresas
    REGIMEN_GENERAL = "regimen_general"              # Personas naturales
    REGIMEN_PROPYME = "regimen_propyme"              # 25% PyMEs
    REGIMEN_RENTA_PRESUNTA = "regimen_renta_presunta"
    EXENTO = "exento"


class TipoBienRaiz(str, Enum):
    """Tipo de bien raíz para efectos tributarios"""
    HABITACIONAL = "habitacional"
    COMERCIAL = "comercial"
    AGRICOLA = "agricola"
    INDUSTRIAL = "industrial"
    MIXTO = "mixto"
    DFL2 = "dfl2"                                    # Acogido a DFL-2
    SITIO_ERIAZO = "sitio_eriazo"


class MetodoAdquisicion(str, Enum):
    """Método de adquisición del bien raíz"""
    COMPRAVENTA = "compraventa"
    HERENCIA = "herencia"
    DONACION = "donacion"
    PERMUTA = "permuta"
    ADJUDICACION = "adjudicacion"                    # División comunidad
    APORTE_CAPITAL = "aporte_capital"
    FUSION_DIVISION = "fusion_division"
    REMATE = "remate"
    EXPROPIACION = "expropiacion"


class TipoEnajenacion(str, Enum):
    """Tipo de enajenación o transferencia"""
    VENTA_DIRECTA = "venta_directa"
    VENTA_CON_HIPOTECA = "venta_con_hipoteca"
    VENTA_LEASING = "venta_leasing"
    PERMUTA = "permuta"
    APORTE_SOCIEDAD = "aporte_sociedad"
    DONACION = "donacion"
    EXPROPIACION = "expropiacion"
    REMATE_FORZADO = "remate_forzado"


class BeneficioTributario(str, Enum):
    """Beneficios tributarios aplicables"""
    SIN_BENEFICIO = "sin_beneficio"
    DFL2_TRADICIONAL = "dfl2_tradicional"            # Hasta 2 propiedades
    UNICA_VIVIENDA = "unica_vivienda"               # Exención total
    INGRESO_NO_RENTA_8000UF = "ingreso_no_renta"    # Art. 17 N°8 letra b
    PROPYME = "propyme"
    ZONA_EXTREMA = "zona_extrema"


class EstadoCalculo(str, Enum):
    """Estado del cálculo de plusvalía"""
    BORRADOR = "borrador"
    CALCULADO = "calculado"
    VERIFICADO = "verificado"
    APROBADO = "aprobado"
    DECLARADO = "declarado"                          # En F22


class MetodoCostoAdquisicion(str, Enum):
    """Método para determinar costo de adquisición"""
    VALOR_ESCRITURA = "valor_escritura"              # Valor en escritura
    AVALUO_FISCAL = "avaluo_fiscal"                  # Avalúo SII fecha adquisición
    VALOR_COMERCIAL = "valor_comercial"              # Tasación comercial
    COSTO_CONSTRUCCION = "costo_construccion"        # Costo real construcción
    VALOR_HERENCIA = "valor_herencia"                # Valor en posesión efectiva


# =============================================================================
# DATACLASSES - ESTRUCTURA DE DATOS
# =============================================================================

@dataclass
class DatosContribuyente:
    """Datos del contribuyente para cálculo tributario"""
    id: str = field(default_factory=lambda: str(uuid4()))
    rut: str = ""
    nombre: str = ""
    tipo: TipoContribuyente = TipoContribuyente.PERSONA_NATURAL
    regimen: RegimenTributario = RegimenTributario.REGIMEN_GENERAL
    
    # Tramo impuesto personas naturales
    renta_imponible_anual_utm: Decimal = Decimal("0")
    tramo_impuesto: int = 0                          # 0-7 según tabla
    tasa_marginal_pct: Decimal = Decimal("0")
    
    # Propiedades
    cantidad_propiedades: int = 0
    propiedades_dfl2: int = 0
    es_contribuyente_habitual: bool = False          # >1 venta/año


@dataclass
class DatosAdquisicion:
    """Datos de la adquisición del bien raíz"""
    fecha_adquisicion: date = field(default_factory=date.today)
    metodo: MetodoAdquisicion = MetodoAdquisicion.COMPRAVENTA
    metodo_costo: MetodoCostoAdquisicion = MetodoCostoAdquisicion.VALOR_ESCRITURA
    
    # Valores originales
    valor_escritura_pesos: Decimal = Decimal("0")
    valor_escritura_uf: Decimal = Decimal("0")
    avaluo_fiscal_pesos: Decimal = Decimal("0")
    avaluo_fiscal_uf: Decimal = Decimal("0")
    
    # UF fecha adquisición
    uf_fecha_adquisicion: Decimal = Decimal("0")
    
    # Costos adicionales capitalizables
    comision_corretaje: Decimal = Decimal("0")
    gastos_notariales: Decimal = Decimal("0")
    impuesto_transferencia: Decimal = Decimal("0")   # 0% actualmente
    inscripcion_cbr: Decimal = Decimal("0")
    otros_gastos_adquisicion: Decimal = Decimal("0")
    
    # Mejoras capitalizables (deben cumplir requisitos SII)
    mejoras_capitalizadas: List[Dict[str, Any]] = field(default_factory=list)
    total_mejoras_uf: Decimal = Decimal("0")
    
    # Documentación
    escritura_url: str = ""
    inscripcion_cbr: str = ""
    boletas_mejoras: List[str] = field(default_factory=list)


@dataclass
class DatosEnajenacion:
    """Datos de la enajenación (venta) del bien raíz"""
    fecha_enajenacion: date = field(default_factory=date.today)
    tipo: TipoEnajenacion = TipoEnajenacion.VENTA_DIRECTA
    
    # Valores venta
    precio_venta_pesos: Decimal = Decimal("0")
    precio_venta_uf: Decimal = Decimal("0")
    
    # UF fecha venta
    uf_fecha_enajenacion: Decimal = Decimal("0")
    
    # Costos de venta (no deducibles de ganancia de capital)
    comision_corretaje_venta: Decimal = Decimal("0")
    gastos_notariales_venta: Decimal = Decimal("0")
    otros_gastos_venta: Decimal = Decimal("0")
    
    # Precio neto recibido
    precio_neto_uf: Decimal = Decimal("0")
    
    # Documentación
    escritura_venta_url: str = ""
    comprobante_pago_url: str = ""


@dataclass
class CorreccionMonetaria:
    """Detalle de corrección monetaria aplicada"""
    # IPC
    ipc_fecha_adquisicion: Decimal = Decimal("0")
    ipc_fecha_enajenacion: Decimal = Decimal("0")
    factor_correccion_ipc: Decimal = Decimal("0")
    
    # UF (método alternativo)
    variacion_uf_pct: Decimal = Decimal("0")
    
    # Valores corregidos
    costo_adquisicion_nominal: Decimal = Decimal("0")
    costo_adquisicion_corregido: Decimal = Decimal("0")
    mejoras_corregidas: Decimal = Decimal("0")
    costo_total_corregido_uf: Decimal = Decimal("0")


@dataclass  
class AnalisisBeneficiosTributarios:
    """Análisis de beneficios tributarios aplicables"""
    # Beneficio principal aplicado
    beneficio_aplicado: BeneficioTributario = BeneficioTributario.SIN_BENEFICIO
    
    # Art. 17 N°8 letra b) - Ingreso no renta hasta 8.000 UF
    aplica_inr_8000uf: bool = False
    monto_exento_uf: Decimal = Decimal("0")
    monto_gravado_uf: Decimal = Decimal("0")
    
    # DFL-2
    es_dfl2: bool = False
    fecha_acogimiento_dfl2: Optional[date] = None
    cumple_requisitos_dfl2: bool = False
    razon_no_cumple_dfl2: str = ""
    
    # Única vivienda habitual
    es_unica_vivienda: bool = False
    tiempo_habitacion_meses: int = 0
    cumple_requisitos_unica_vivienda: bool = False
    
    # Detalle cálculo beneficio
    ganancia_antes_beneficio_uf: Decimal = Decimal("0")
    reduccion_por_beneficio_uf: Decimal = Decimal("0")
    ganancia_despues_beneficio_uf: Decimal = Decimal("0")


@dataclass
class ImpuestoCalculado:
    """Detalle del impuesto calculado"""
    # Base imponible
    base_imponible_uf: Decimal = Decimal("0")
    base_imponible_utm: Decimal = Decimal("0")
    
    # Impuesto único (si aplica Art. 17 N°8 b)
    aplica_impuesto_unico: bool = False
    tasa_impuesto_unico_pct: Decimal = Decimal("10")   # 10% tasa única
    impuesto_unico_uf: Decimal = Decimal("0")
    
    # Impuesto Global Complementario (alternativa)
    aplica_global_complementario: bool = False
    tramo_gc: int = 0
    tasa_marginal_gc_pct: Decimal = Decimal("0")
    impuesto_gc_uf: Decimal = Decimal("0")
    
    # Primera Categoría (personas jurídicas)
    aplica_primera_categoria: bool = False
    tasa_primera_categoria_pct: Decimal = Decimal("27")
    impuesto_primera_categoria_uf: Decimal = Decimal("0")
    
    # Impuesto final
    impuesto_total_uf: Decimal = Decimal("0")
    impuesto_total_pesos: Decimal = Decimal("0")
    
    # Mejor opción
    mejor_opcion: str = ""
    ahorro_vs_alternativa_uf: Decimal = Decimal("0")


@dataclass
class ResultadoPlusvalia:
    """Resultado completo del cálculo de plusvalía"""
    id: str = field(default_factory=lambda: str(uuid4()))
    expediente_id: Optional[str] = None
    ficha_propiedad_id: Optional[str] = None
    
    # Identificación
    rol_sii: str = ""
    direccion: str = ""
    tipo_bien: TipoBienRaiz = TipoBienRaiz.HABITACIONAL
    
    # Contribuyente
    contribuyente: Optional[DatosContribuyente] = None
    
    # Datos transacción
    adquisicion: Optional[DatosAdquisicion] = None
    enajenacion: Optional[DatosEnajenacion] = None
    
    # Período tenencia
    dias_tenencia: int = 0
    anos_tenencia: Decimal = Decimal("0")
    
    # Plusvalía bruta
    precio_venta_uf: Decimal = Decimal("0")
    costo_adquisicion_uf: Decimal = Decimal("0")
    plusvalia_nominal_uf: Decimal = Decimal("0")
    plusvalia_nominal_pct: Decimal = Decimal("0")
    
    # Corrección monetaria
    correccion: Optional[CorreccionMonetaria] = None
    
    # Ganancia de capital (base imponible)
    costo_corregido_uf: Decimal = Decimal("0")
    ganancia_capital_uf: Decimal = Decimal("0")
    ganancia_capital_pct: Decimal = Decimal("0")
    
    # Beneficios tributarios
    beneficios: Optional[AnalisisBeneficiosTributarios] = None
    
    # Impuesto
    impuesto: Optional[ImpuestoCalculado] = None
    
    # Resultado neto
    ganancia_neta_despues_impuesto_uf: Decimal = Decimal("0")
    rentabilidad_efectiva_anual_pct: Decimal = Decimal("0")
    
    # Estado
    estado: EstadoCalculo = EstadoCalculo.BORRADOR
    fecha_calculo: datetime = field(default_factory=datetime.now)
    usuario_calculo: str = ""
    
    # Observaciones
    observaciones: List[str] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)


@dataclass
class SimulacionVenta:
    """Simulación de escenario de venta"""
    id: str = field(default_factory=lambda: str(uuid4()))
    nombre_escenario: str = ""
    
    # Parámetros simulación
    fecha_venta_simulada: date = field(default_factory=date.today)
    precio_venta_uf: Decimal = Decimal("0")
    
    # Resultado
    plusvalia_estimada_uf: Decimal = Decimal("0")
    impuesto_estimado_uf: Decimal = Decimal("0")
    ganancia_neta_uf: Decimal = Decimal("0")
    
    # Comparación con escenario base
    diferencia_vs_base_uf: Decimal = Decimal("0")
    recomendacion: str = ""


@dataclass
class ProyeccionPlusvalia:
    """Proyección de plusvalía futura"""
    fecha_proyeccion: date = field(default_factory=date.today)
    horizonte_anos: int = 5
    
    # Supuestos
    tasa_apreciacion_anual_pct: Decimal = Decimal("4")
    inflacion_proyectada_pct: Decimal = Decimal("3")
    
    # Proyección por año
    proyeccion_anual: List[Dict[str, Any]] = field(default_factory=list)
    
    # Punto de equilibrio
    ano_equilibrio_fiscal: Optional[int] = None      # Cuando INR > costo fiscal


@dataclass
class ReporteF22:
    """Datos para declaración F22"""
    ano_tributario: int = 0
    
    # Recuadro aplicable
    codigo_recuadro: str = ""                        # Ej: 155, 605, etc.
    
    # Valores a declarar
    ingreso_bruto_uf: Decimal = Decimal("0")
    costo_directo_uf: Decimal = Decimal("0")
    ganancia_capital_uf: Decimal = Decimal("0")
    
    # Beneficios
    monto_exento_uf: Decimal = Decimal("0")
    base_imponible_uf: Decimal = Decimal("0")
    
    # Impuesto
    impuesto_determinado_uf: Decimal = Decimal("0")
    creditos_aplicables_uf: Decimal = Decimal("0")
    impuesto_final_uf: Decimal = Decimal("0")
    
    # Instrucciones
    instrucciones: List[str] = field(default_factory=list)


# =============================================================================
# CONSTANTES TRIBUTARIAS
# =============================================================================

# Tabla Global Complementario 2024 (UTM)
TABLA_GLOBAL_COMPLEMENTARIO = [
    {"desde": Decimal("0"), "hasta": Decimal("13.5"), "tasa": Decimal("0"), "rebaja": Decimal("0")},
    {"desde": Decimal("13.5"), "hasta": Decimal("30"), "tasa": Decimal("4"), "rebaja": Decimal("0.54")},
    {"desde": Decimal("30"), "hasta": Decimal("50"), "tasa": Decimal("8"), "rebaja": Decimal("1.74")},
    {"desde": Decimal("50"), "hasta": Decimal("70"), "tasa": Decimal("13.5"), "rebaja": Decimal("4.49")},
    {"desde": Decimal("70"), "hasta": Decimal("90"), "tasa": Decimal("23"), "rebaja": Decimal("11.14")},
    {"desde": Decimal("90"), "hasta": Decimal("120"), "tasa": Decimal("30.4"), "rebaja": Decimal("17.8")},
    {"desde": Decimal("120"), "hasta": Decimal("310"), "tasa": Decimal("35"), "rebaja": Decimal("23.32")},
    {"desde": Decimal("310"), "hasta": Decimal("999999"), "tasa": Decimal("40"), "rebaja": Decimal("38.82")},
]

# Límite ingreso no renta Art. 17 N°8 b)
LIMITE_INR_UF = Decimal("8000")

# Tasa impuesto único ganancias de capital
TASA_IMPUESTO_UNICO_PCT = Decimal("10")

# Tasa primera categoría
TASA_PRIMERA_CATEGORIA_PCT = Decimal("27")

# Tasa PyME
TASA_PROPYME_PCT = Decimal("25")


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class PlusvaliaService:
    """
    Servicio para cálculo de plusvalía y ganancias de capital inmobiliarias.
    Implementa normativa tributaria chilena vigente.
    """
    
    def __init__(self):
        self.calculos: Dict[str, ResultadoPlusvalia] = {}
        self.simulaciones: Dict[str, List[SimulacionVenta]] = {}
        self.uf_historico: Dict[str, Decimal] = {}
        self.ipc_historico: Dict[str, Decimal] = {}
        self._cargar_indicadores_mock()
    
    def _cargar_indicadores_mock(self):
        """Carga indicadores mock para desarrollo"""
        # UF por fecha (simplificado)
        self.uf_historico = {
            "2015-01-01": Decimal("24627.10"),
            "2016-01-01": Decimal("25629.09"),
            "2017-01-01": Decimal("26347.98"),
            "2018-01-01": Decimal("26798.14"),
            "2019-01-01": Decimal("27565.79"),
            "2020-01-01": Decimal("28309.94"),
            "2021-01-01": Decimal("29070.33"),
            "2022-01-01": Decimal("31028.82"),
            "2023-01-01": Decimal("35122.26"),
            "2024-01-01": Decimal("36789.36"),
            "2025-01-01": Decimal("38500.00"),
        }
        
        # IPC base 100 = dic 2018
        self.ipc_historico = {
            "2015-01-01": Decimal("89.5"),
            "2016-01-01": Decimal("93.2"),
            "2017-01-01": Decimal("95.8"),
            "2018-01-01": Decimal("98.1"),
            "2019-01-01": Decimal("100.8"),
            "2020-01-01": Decimal("103.5"),
            "2021-01-01": Decimal("108.2"),
            "2022-01-01": Decimal("121.5"),
            "2023-01-01": Decimal("134.8"),
            "2024-01-01": Decimal("140.2"),
            "2025-01-01": Decimal("144.5"),
        }
    
    def _obtener_uf_fecha(self, fecha: date) -> Decimal:
        """Obtiene UF para una fecha específica"""
        # Simplificado: busca la más cercana anterior
        fecha_str = fecha.strftime("%Y-01-01")
        if fecha_str in self.uf_historico:
            return self.uf_historico[fecha_str]
        
        # Buscar año anterior
        ano = fecha.year
        while ano >= 2015:
            key = f"{ano}-01-01"
            if key in self.uf_historico:
                return self.uf_historico[key]
            ano -= 1
        
        return Decimal("38500")  # Default actual
    
    def _obtener_ipc_fecha(self, fecha: date) -> Decimal:
        """Obtiene IPC para una fecha específica"""
        fecha_str = fecha.strftime("%Y-01-01")
        if fecha_str in self.ipc_historico:
            return self.ipc_historico[fecha_str]
        
        ano = fecha.year
        while ano >= 2015:
            key = f"{ano}-01-01"
            if key in self.ipc_historico:
                return self.ipc_historico[key]
            ano -= 1
        
        return Decimal("144.5")
    
    async def calcular_plusvalia(
        self,
        contribuyente: DatosContribuyente,
        adquisicion: DatosAdquisicion,
        enajenacion: DatosEnajenacion,
        tipo_bien: TipoBienRaiz = TipoBienRaiz.HABITACIONAL,
        rol_sii: str = "",
        direccion: str = "",
        expediente_id: Optional[str] = None,
        ficha_propiedad_id: Optional[str] = None,
        usuario: str = ""
    ) -> ResultadoPlusvalia:
        """
        Calcula la plusvalía y ganancia de capital de una enajenación inmobiliaria.
        
        Args:
            contribuyente: Datos del contribuyente
            adquisicion: Datos de la adquisición original
            enajenacion: Datos de la enajenación/venta
            tipo_bien: Tipo de bien raíz
            rol_sii: Rol SII de la propiedad
            direccion: Dirección de la propiedad
            
        Returns:
            ResultadoPlusvalia con todos los cálculos
        """
        logger.info(f"Calculando plusvalía para {rol_sii}")
        
        resultado = ResultadoPlusvalia(
            expediente_id=expediente_id,
            ficha_propiedad_id=ficha_propiedad_id,
            rol_sii=rol_sii,
            direccion=direccion,
            tipo_bien=tipo_bien,
            contribuyente=contribuyente,
            adquisicion=adquisicion,
            enajenacion=enajenacion,
            usuario_calculo=usuario
        )
        
        # 1. Calcular período de tenencia
        resultado.dias_tenencia = (enajenacion.fecha_enajenacion - adquisicion.fecha_adquisicion).days
        resultado.anos_tenencia = Decimal(str(resultado.dias_tenencia)) / Decimal("365")
        
        # 2. Obtener UF de las fechas
        uf_adquisicion = self._obtener_uf_fecha(adquisicion.fecha_adquisicion)
        uf_enajenacion = self._obtener_uf_fecha(enajenacion.fecha_enajenacion)
        
        # 3. Calcular valores en UF si no están
        if adquisicion.valor_escritura_uf == 0 and adquisicion.valor_escritura_pesos > 0:
            adquisicion.valor_escritura_uf = adquisicion.valor_escritura_pesos / uf_adquisicion
        
        if enajenacion.precio_venta_uf == 0 and enajenacion.precio_venta_pesos > 0:
            enajenacion.precio_venta_uf = enajenacion.precio_venta_pesos / uf_enajenacion
        
        # 4. Calcular plusvalía nominal
        resultado.precio_venta_uf = enajenacion.precio_venta_uf
        resultado.costo_adquisicion_uf = adquisicion.valor_escritura_uf
        resultado.plusvalia_nominal_uf = resultado.precio_venta_uf - resultado.costo_adquisicion_uf
        
        if resultado.costo_adquisicion_uf > 0:
            resultado.plusvalia_nominal_pct = (
                resultado.plusvalia_nominal_uf / resultado.costo_adquisicion_uf * 100
            )
        
        # 5. Aplicar corrección monetaria
        correccion = await self._calcular_correccion_monetaria(
            adquisicion, enajenacion, uf_adquisicion, uf_enajenacion
        )
        resultado.correccion = correccion
        resultado.costo_corregido_uf = correccion.costo_total_corregido_uf
        
        # 6. Calcular ganancia de capital real
        resultado.ganancia_capital_uf = resultado.precio_venta_uf - resultado.costo_corregido_uf
        
        if resultado.costo_corregido_uf > 0:
            resultado.ganancia_capital_pct = (
                resultado.ganancia_capital_uf / resultado.costo_corregido_uf * 100
            )
        
        # 7. Analizar beneficios tributarios
        beneficios = await self._analizar_beneficios_tributarios(
            contribuyente, tipo_bien, adquisicion, resultado.ganancia_capital_uf
        )
        resultado.beneficios = beneficios
        
        # 8. Calcular impuesto
        impuesto = await self._calcular_impuesto(
            contribuyente, beneficios.ganancia_despues_beneficio_uf, uf_enajenacion
        )
        resultado.impuesto = impuesto
        
        # 9. Calcular ganancia neta después de impuesto
        resultado.ganancia_neta_despues_impuesto_uf = (
            resultado.ganancia_capital_uf - impuesto.impuesto_total_uf
        )
        
        # 10. Calcular rentabilidad efectiva anual
        if resultado.anos_tenencia > 0 and resultado.costo_adquisicion_uf > 0:
            # Rentabilidad compuesta anual
            factor = resultado.ganancia_neta_despues_impuesto_uf / resultado.costo_adquisicion_uf + 1
            resultado.rentabilidad_efectiva_anual_pct = (
                (Decimal(str(float(factor) ** (1 / float(resultado.anos_tenencia)))) - 1) * 100
            )
        
        # 11. Generar alertas
        resultado.alertas = await self._generar_alertas(resultado)
        
        resultado.estado = EstadoCalculo.CALCULADO
        resultado.fecha_calculo = datetime.now()
        
        # Guardar
        self.calculos[resultado.id] = resultado
        
        logger.info(f"Plusvalía calculada: {resultado.ganancia_capital_uf} UF")
        
        return resultado
    
    async def _calcular_correccion_monetaria(
        self,
        adquisicion: DatosAdquisicion,
        enajenacion: DatosEnajenacion,
        uf_adquisicion: Decimal,
        uf_enajenacion: Decimal
    ) -> CorreccionMonetaria:
        """Calcula la corrección monetaria según IPC"""
        correccion = CorreccionMonetaria()
        
        # Obtener IPC
        ipc_adq = self._obtener_ipc_fecha(adquisicion.fecha_adquisicion)
        ipc_ena = self._obtener_ipc_fecha(enajenacion.fecha_enajenacion)
        
        correccion.ipc_fecha_adquisicion = ipc_adq
        correccion.ipc_fecha_enajenacion = ipc_ena
        
        # Factor de corrección
        if ipc_adq > 0:
            correccion.factor_correccion_ipc = ipc_ena / ipc_adq
        else:
            correccion.factor_correccion_ipc = Decimal("1")
        
        # Variación UF
        if uf_adquisicion > 0:
            correccion.variacion_uf_pct = (
                (uf_enajenacion - uf_adquisicion) / uf_adquisicion * 100
            )
        
        # Costo nominal
        costo_nominal = adquisicion.valor_escritura_uf
        
        # Sumar costos capitalizables (en UF de su fecha)
        gastos_adq = (
            adquisicion.comision_corretaje +
            adquisicion.gastos_notariales +
            adquisicion.inscripcion_cbr +
            adquisicion.otros_gastos_adquisicion
        ) / uf_adquisicion
        
        costo_nominal += gastos_adq
        correccion.costo_adquisicion_nominal = costo_nominal
        
        # Aplicar corrección monetaria
        # El costo se expresa en UF, que ya está corregido por inflación
        # Para efectos tributarios, se usa el valor en UF sin ajuste adicional
        correccion.costo_adquisicion_corregido = costo_nominal
        
        # Mejoras (también en UF)
        mejoras_uf = adquisicion.total_mejoras_uf
        correccion.mejoras_corregidas = mejoras_uf
        
        # Costo total corregido
        correccion.costo_total_corregido_uf = (
            correccion.costo_adquisicion_corregido + 
            correccion.mejoras_corregidas
        )
        
        return correccion
    
    async def _analizar_beneficios_tributarios(
        self,
        contribuyente: DatosContribuyente,
        tipo_bien: TipoBienRaiz,
        adquisicion: DatosAdquisicion,
        ganancia_uf: Decimal
    ) -> AnalisisBeneficiosTributarios:
        """Analiza y aplica beneficios tributarios"""
        beneficios = AnalisisBeneficiosTributarios()
        beneficios.ganancia_antes_beneficio_uf = ganancia_uf
        
        # Verificar si es DFL-2
        if tipo_bien == TipoBienRaiz.DFL2:
            beneficios.es_dfl2 = True
            # DFL-2 tiene beneficios específicos pero limitados
            if contribuyente.propiedades_dfl2 <= 2:
                beneficios.cumple_requisitos_dfl2 = True
            else:
                beneficios.razon_no_cumple_dfl2 = "Excede límite de 2 propiedades DFL-2"
        
        # Verificar Art. 17 N°8 letra b) - Ingreso No Renta
        # Aplica a personas naturales no habituales
        if (contribuyente.tipo == TipoContribuyente.PERSONA_NATURAL and 
            not contribuyente.es_contribuyente_habitual):
            
            beneficios.aplica_inr_8000uf = True
            
            # El INR es hasta 8.000 UF de ganancia de capital
            if ganancia_uf <= LIMITE_INR_UF:
                beneficios.monto_exento_uf = ganancia_uf
                beneficios.monto_gravado_uf = Decimal("0")
            else:
                beneficios.monto_exento_uf = LIMITE_INR_UF
                beneficios.monto_gravado_uf = ganancia_uf - LIMITE_INR_UF
        else:
            # Personas jurídicas o habituales: todo gravado
            beneficios.monto_exento_uf = Decimal("0")
            beneficios.monto_gravado_uf = ganancia_uf
        
        # Determinar beneficio principal
        if beneficios.aplica_inr_8000uf and beneficios.monto_exento_uf > 0:
            beneficios.beneficio_aplicado = BeneficioTributario.INGRESO_NO_RENTA_8000UF
        elif beneficios.cumple_requisitos_dfl2:
            beneficios.beneficio_aplicado = BeneficioTributario.DFL2_TRADICIONAL
        else:
            beneficios.beneficio_aplicado = BeneficioTributario.SIN_BENEFICIO
        
        # Calcular reducción
        beneficios.reduccion_por_beneficio_uf = beneficios.monto_exento_uf
        beneficios.ganancia_despues_beneficio_uf = beneficios.monto_gravado_uf
        
        return beneficios
    
    async def _calcular_impuesto(
        self,
        contribuyente: DatosContribuyente,
        base_imponible_uf: Decimal,
        uf_actual: Decimal
    ) -> ImpuestoCalculado:
        """Calcula el impuesto según tipo de contribuyente"""
        impuesto = ImpuestoCalculado()
        impuesto.base_imponible_uf = base_imponible_uf
        
        # Si no hay base imponible, no hay impuesto
        if base_imponible_uf <= 0:
            impuesto.mejor_opcion = "Sin impuesto - Ganancia exenta o pérdida"
            return impuesto
        
        # Convertir a UTM (aprox 1 UTM = 0.0015 UF)
        utm_valor = uf_actual * Decimal("0.0015")
        impuesto.base_imponible_utm = base_imponible_uf / Decimal("0.0015") if utm_valor > 0 else Decimal("0")
        
        if contribuyente.tipo == TipoContribuyente.PERSONA_NATURAL:
            # Opción 1: Impuesto único 10%
            impuesto.aplica_impuesto_unico = True
            impuesto.tasa_impuesto_unico_pct = TASA_IMPUESTO_UNICO_PCT
            impuesto.impuesto_unico_uf = base_imponible_uf * TASA_IMPUESTO_UNICO_PCT / 100
            
            # Opción 2: Global Complementario
            impuesto.aplica_global_complementario = True
            impuesto_gc = self._calcular_global_complementario(
                impuesto.base_imponible_utm, contribuyente.renta_imponible_anual_utm
            )
            impuesto.tramo_gc = impuesto_gc["tramo"]
            impuesto.tasa_marginal_gc_pct = impuesto_gc["tasa"]
            impuesto.impuesto_gc_uf = impuesto_gc["impuesto_utm"] * Decimal("0.0015")
            
            # Elegir la mejor opción
            if impuesto.impuesto_unico_uf <= impuesto.impuesto_gc_uf:
                impuesto.impuesto_total_uf = impuesto.impuesto_unico_uf
                impuesto.mejor_opcion = "Impuesto Único 10% (Art. 17 N°8 b)"
                impuesto.ahorro_vs_alternativa_uf = impuesto.impuesto_gc_uf - impuesto.impuesto_unico_uf
            else:
                impuesto.impuesto_total_uf = impuesto.impuesto_gc_uf
                impuesto.mejor_opcion = "Global Complementario"
                impuesto.ahorro_vs_alternativa_uf = impuesto.impuesto_unico_uf - impuesto.impuesto_gc_uf
        
        elif contribuyente.tipo == TipoContribuyente.PERSONA_JURIDICA:
            # Primera categoría
            impuesto.aplica_primera_categoria = True
            
            if contribuyente.regimen == RegimenTributario.REGIMEN_PROPYME:
                impuesto.tasa_primera_categoria_pct = TASA_PROPYME_PCT
            else:
                impuesto.tasa_primera_categoria_pct = TASA_PRIMERA_CATEGORIA_PCT
            
            impuesto.impuesto_primera_categoria_uf = (
                base_imponible_uf * impuesto.tasa_primera_categoria_pct / 100
            )
            impuesto.impuesto_total_uf = impuesto.impuesto_primera_categoria_uf
            impuesto.mejor_opcion = f"Primera Categoría {impuesto.tasa_primera_categoria_pct}%"
        
        # Convertir a pesos
        impuesto.impuesto_total_pesos = impuesto.impuesto_total_uf * uf_actual
        
        return impuesto
    
    def _calcular_global_complementario(
        self, 
        ganancia_utm: Decimal,
        renta_base_utm: Decimal
    ) -> Dict[str, Any]:
        """Calcula impuesto Global Complementario"""
        renta_total_utm = renta_base_utm + ganancia_utm
        
        impuesto = Decimal("0")
        tramo = 0
        tasa = Decimal("0")
        
        for i, t in enumerate(TABLA_GLOBAL_COMPLEMENTARIO):
            if t["desde"] <= renta_total_utm < t["hasta"]:
                tramo = i
                tasa = t["tasa"]
                impuesto = renta_total_utm * t["tasa"] / 100 - t["rebaja"]
                break
        
        return {
            "tramo": tramo,
            "tasa": tasa,
            "impuesto_utm": max(impuesto, Decimal("0"))
        }
    
    async def _generar_alertas(self, resultado: ResultadoPlusvalia) -> List[str]:
        """Genera alertas y advertencias sobre el cálculo"""
        alertas = []
        
        # Alerta pérdida de capital
        if resultado.ganancia_capital_uf < 0:
            alertas.append("⚠️ PÉRDIDA DE CAPITAL: El costo corregido es mayor al precio de venta")
        
        # Alerta tenencia corta
        if resultado.anos_tenencia < 1:
            alertas.append("⚠️ TENENCIA MENOR A 1 AÑO: Podría considerarse operación especulativa")
        
        # Alerta contribuyente habitual
        if resultado.contribuyente and resultado.contribuyente.es_contribuyente_habitual:
            alertas.append("⚠️ CONTRIBUYENTE HABITUAL: No aplica beneficio INR 8.000 UF")
        
        # Alerta impuesto significativo
        if resultado.impuesto and resultado.impuesto.impuesto_total_uf > Decimal("500"):
            alertas.append(f"💰 IMPUESTO SIGNIFICATIVO: {resultado.impuesto.impuesto_total_uf:.2f} UF")
        
        # Alerta DFL-2 excedido
        if (resultado.beneficios and resultado.beneficios.es_dfl2 and 
            not resultado.beneficios.cumple_requisitos_dfl2):
            alertas.append(f"⚠️ DFL-2: {resultado.beneficios.razon_no_cumple_dfl2}")
        
        return alertas
    
    async def simular_venta(
        self,
        resultado_base_id: str,
        fecha_venta: date,
        precio_venta_uf: Decimal,
        nombre_escenario: str = ""
    ) -> SimulacionVenta:
        """
        Simula un escenario de venta alternativo.
        
        Args:
            resultado_base_id: ID del cálculo base
            fecha_venta: Fecha simulada de venta
            precio_venta_uf: Precio de venta simulado
            nombre_escenario: Nombre descriptivo
            
        Returns:
            SimulacionVenta con resultados
        """
        resultado_base = self.calculos.get(resultado_base_id)
        if not resultado_base:
            raise ValueError("Cálculo base no encontrado")
        
        simulacion = SimulacionVenta(
            nombre_escenario=nombre_escenario or f"Venta {fecha_venta}",
            fecha_venta_simulada=fecha_venta,
            precio_venta_uf=precio_venta_uf
        )
        
        # Recalcular con nuevos parámetros
        enajenacion_simulada = DatosEnajenacion(
            fecha_enajenacion=fecha_venta,
            precio_venta_uf=precio_venta_uf
        )
        
        # Crear copia de datos originales
        resultado_simulado = await self.calcular_plusvalia(
            contribuyente=resultado_base.contribuyente,
            adquisicion=resultado_base.adquisicion,
            enajenacion=enajenacion_simulada,
            tipo_bien=resultado_base.tipo_bien,
            rol_sii=resultado_base.rol_sii
        )
        
        # Llenar simulación
        simulacion.plusvalia_estimada_uf = resultado_simulado.ganancia_capital_uf
        simulacion.impuesto_estimado_uf = resultado_simulado.impuesto.impuesto_total_uf
        simulacion.ganancia_neta_uf = resultado_simulado.ganancia_neta_despues_impuesto_uf
        
        # Comparar con base
        simulacion.diferencia_vs_base_uf = (
            simulacion.ganancia_neta_uf - resultado_base.ganancia_neta_despues_impuesto_uf
        )
        
        # Generar recomendación
        if simulacion.diferencia_vs_base_uf > 0:
            simulacion.recomendacion = f"✅ Escenario favorable: +{simulacion.diferencia_vs_base_uf:.2f} UF vs base"
        elif simulacion.diferencia_vs_base_uf < 0:
            simulacion.recomendacion = f"❌ Escenario desfavorable: {simulacion.diferencia_vs_base_uf:.2f} UF vs base"
        else:
            simulacion.recomendacion = "= Resultado similar al escenario base"
        
        # Guardar simulación
        if resultado_base_id not in self.simulaciones:
            self.simulaciones[resultado_base_id] = []
        self.simulaciones[resultado_base_id].append(simulacion)
        
        return simulacion
    
    async def proyectar_plusvalia(
        self,
        resultado_id: str,
        horizonte_anos: int = 5,
        tasa_apreciacion_anual_pct: Decimal = Decimal("4"),
        inflacion_proyectada_pct: Decimal = Decimal("3")
    ) -> ProyeccionPlusvalia:
        """
        Proyecta la plusvalía futura.
        
        Args:
            resultado_id: ID del cálculo actual
            horizonte_anos: Años a proyectar
            tasa_apreciacion_anual_pct: Tasa de apreciación esperada
            inflacion_proyectada_pct: Inflación proyectada
            
        Returns:
            ProyeccionPlusvalia con análisis
        """
        resultado = self.calculos.get(resultado_id)
        if not resultado:
            raise ValueError("Cálculo no encontrado")
        
        proyeccion = ProyeccionPlusvalia(
            horizonte_anos=horizonte_anos,
            tasa_apreciacion_anual_pct=tasa_apreciacion_anual_pct,
            inflacion_proyectada_pct=inflacion_proyectada_pct
        )
        
        valor_actual = resultado.precio_venta_uf
        costo_base = resultado.costo_corregido_uf
        
        for ano in range(1, horizonte_anos + 1):
            # Proyectar valor
            factor = (1 + tasa_apreciacion_anual_pct / 100) ** ano
            valor_proyectado = valor_actual * Decimal(str(factor))
            
            # Calcular ganancia proyectada
            ganancia_proyectada = valor_proyectado - costo_base
            
            # Estimar impuesto (simplificado)
            if ganancia_proyectada > LIMITE_INR_UF:
                impuesto_estimado = (ganancia_proyectada - LIMITE_INR_UF) * TASA_IMPUESTO_UNICO_PCT / 100
            else:
                impuesto_estimado = Decimal("0")
            
            ganancia_neta = ganancia_proyectada - impuesto_estimado
            
            proyeccion.proyeccion_anual.append({
                "ano": ano,
                "fecha": date.today().replace(year=date.today().year + ano),
                "valor_proyectado_uf": valor_proyectado,
                "ganancia_capital_uf": ganancia_proyectada,
                "impuesto_estimado_uf": impuesto_estimado,
                "ganancia_neta_uf": ganancia_neta,
                "rentabilidad_acumulada_pct": (valor_proyectado / costo_base - 1) * 100 if costo_base > 0 else Decimal("0")
            })
            
            # Verificar punto de equilibrio fiscal
            if proyeccion.ano_equilibrio_fiscal is None and ganancia_proyectada >= LIMITE_INR_UF:
                proyeccion.ano_equilibrio_fiscal = ano
        
        return proyeccion
    
    async def generar_reporte_f22(
        self,
        resultado_id: str,
        ano_tributario: int
    ) -> ReporteF22:
        """
        Genera datos para declaración F22.
        
        Args:
            resultado_id: ID del cálculo
            ano_tributario: Año tributario para declarar
            
        Returns:
            ReporteF22 con instrucciones
        """
        resultado = self.calculos.get(resultado_id)
        if not resultado:
            raise ValueError("Cálculo no encontrado")
        
        reporte = ReporteF22(ano_tributario=ano_tributario)
        
        # Determinar recuadro según tipo contribuyente
        if resultado.contribuyente.tipo == TipoContribuyente.PERSONA_NATURAL:
            reporte.codigo_recuadro = "155"  # Ganancias de capital Art. 17 N°8
        else:
            reporte.codigo_recuadro = "605"  # Primera categoría
        
        # Valores
        reporte.ingreso_bruto_uf = resultado.precio_venta_uf
        reporte.costo_directo_uf = resultado.costo_corregido_uf
        reporte.ganancia_capital_uf = resultado.ganancia_capital_uf
        
        # Beneficios
        if resultado.beneficios:
            reporte.monto_exento_uf = resultado.beneficios.monto_exento_uf
            reporte.base_imponible_uf = resultado.beneficios.monto_gravado_uf
        
        # Impuesto
        if resultado.impuesto:
            reporte.impuesto_determinado_uf = resultado.impuesto.impuesto_total_uf
            reporte.impuesto_final_uf = resultado.impuesto.impuesto_total_uf
        
        # Instrucciones
        reporte.instrucciones = [
            f"1. Declarar en Formulario 22, recuadro {reporte.codigo_recuadro}",
            f"2. Ingreso bruto: {reporte.ingreso_bruto_uf:.2f} UF",
            f"3. Costo directo (corregido): {reporte.costo_directo_uf:.2f} UF",
            f"4. Ganancia de capital: {reporte.ganancia_capital_uf:.2f} UF",
        ]
        
        if resultado.beneficios and resultado.beneficios.aplica_inr_8000uf:
            reporte.instrucciones.append(
                f"5. Aplicar INR Art. 17 N°8 b): {reporte.monto_exento_uf:.2f} UF exentos"
            )
        
        if resultado.impuesto and resultado.impuesto.mejor_opcion:
            reporte.instrucciones.append(
                f"6. Opción tributaria recomendada: {resultado.impuesto.mejor_opcion}"
            )
        
        reporte.instrucciones.append(
            f"7. Impuesto a pagar: {reporte.impuesto_final_uf:.2f} UF"
        )
        
        return reporte
    
    async def obtener_calculo(self, calculo_id: str) -> Optional[ResultadoPlusvalia]:
        """Obtiene un cálculo por ID"""
        return self.calculos.get(calculo_id)
    
    async def listar_calculos(
        self,
        contribuyente_rut: Optional[str] = None,
        estado: Optional[EstadoCalculo] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None
    ) -> List[ResultadoPlusvalia]:
        """Lista cálculos con filtros opcionales"""
        calculos = list(self.calculos.values())
        
        if contribuyente_rut:
            calculos = [c for c in calculos if c.contribuyente and c.contribuyente.rut == contribuyente_rut]
        
        if estado:
            calculos = [c for c in calculos if c.estado == estado]
        
        if fecha_desde:
            calculos = [c for c in calculos if c.fecha_calculo.date() >= fecha_desde]
        
        if fecha_hasta:
            calculos = [c for c in calculos if c.fecha_calculo.date() <= fecha_hasta]
        
        return calculos


# =============================================================================
# FACTORY Y UTILIDADES
# =============================================================================

_plusvalia_service: Optional[PlusvaliaService] = None


def get_plusvalia_service() -> PlusvaliaService:
    """Obtiene instancia singleton del servicio"""
    global _plusvalia_service
    if _plusvalia_service is None:
        _plusvalia_service = PlusvaliaService()
    return _plusvalia_service


def calcular_tasa_efectiva(
    impuesto_uf: Decimal,
    ganancia_uf: Decimal
) -> Decimal:
    """Calcula la tasa efectiva de impuesto"""
    if ganancia_uf <= 0:
        return Decimal("0")
    return (impuesto_uf / ganancia_uf) * 100


def determinar_habitualidad(
    ventas_ultimos_12_meses: int,
    es_corredor: bool = False
) -> bool:
    """
    Determina si el contribuyente es habitual en operaciones inmobiliarias.
    
    Criterios SII:
    - Más de 1 operación en 12 meses
    - Actividad de corredor de propiedades
    """
    return ventas_ultimos_12_meses > 1 or es_corredor
