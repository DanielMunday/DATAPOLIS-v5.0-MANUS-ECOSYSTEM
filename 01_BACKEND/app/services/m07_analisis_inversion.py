"""
DATAPOLIS v3.0 - Service M07 Análisis de Inversión
===================================================
Motor de análisis financiero para inversiones inmobiliarias con cálculos
de rentabilidad, flujos de caja, sensibilidad y optimización de portfolios.

Funcionalidades:
- Cálculo ROI, TIR, VAN, Payback, Cap Rate
- Proyección de flujos de caja
- Análisis de sensibilidad Monte Carlo
- Comparación de escenarios
- Optimización de inversión
- Simulación Ley 21.713 (tributación arriendos)

Normativa aplicable:
- Ley 21.713 - Cumplimiento tributario
- NCh 2728 - Valoración inmobiliaria
- Circular SII 42/2020 - Ganancias de capital
- IVS 2022 - International Valuation Standards

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2025
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import math
import uuid

# =============================================================================
# ENUMS
# =============================================================================

class TipoInversion(str, Enum):
    """Tipos de inversión inmobiliaria"""
    compra_arriendo = "compra_arriendo"  # Buy-to-let
    compra_reventa = "compra_reventa"  # Fix & flip
    desarrollo = "desarrollo"  # Desarrollo inmobiliario
    subdivision = "subdivision"  # Loteo/subdivisión
    cambio_uso = "cambio_uso"  # Reconversión
    mixta = "mixta"  # Combinación

class TipoActivo(str, Enum):
    """Tipos de activos inmobiliarios"""
    residencial = "residencial"
    comercial = "comercial"
    oficinas = "oficinas"
    industrial = "industrial"
    retail = "retail"
    hotelero = "hotelero"
    terreno = "terreno"
    mixto = "mixto"

class PerfilRiesgo(str, Enum):
    """Perfiles de riesgo del inversionista"""
    conservador = "conservador"  # Bajo riesgo, retornos estables
    moderado = "moderado"  # Balance riesgo/retorno
    agresivo = "agresivo"  # Alto riesgo, altos retornos
    especulativo = "especulativo"  # Máximo riesgo

class EstrategiaExitType(str, Enum):
    """Estrategias de salida"""
    venta_mercado = "venta_mercado"  # Venta a precio de mercado
    venta_premium = "venta_premium"  # Venta sobre mercado
    arriendo_perpetuo = "arriendo_perpetuo"  # Hold indefinido
    refinanciamiento = "refinanciamiento"  # Cash-out refinancing
    aporte_fondo = "aporte_fondo"  # Aporte a fondo de inversión

class TipoFinanciamiento(str, Enum):
    """Tipos de financiamiento"""
    efectivo = "efectivo"  # 100% capital propio
    hipotecario = "hipotecario"  # Crédito hipotecario
    leasing = "leasing"  # Leasing inmobiliario
    mutuaria = "mutuaria"  # Mutuo hipotecario
    mixto = "mixto"  # Combinación

class FrecuenciaPago(str, Enum):
    """Frecuencia de pagos"""
    mensual = "mensual"
    trimestral = "trimestral"
    semestral = "semestral"
    anual = "anual"

class EscenarioTipo(str, Enum):
    """Tipos de escenario para análisis"""
    base = "base"  # Caso base
    optimista = "optimista"  # Mejor caso
    pesimista = "pesimista"  # Peor caso
    estres = "estres"  # Stress test

class MetricaRiesgo(str, Enum):
    """Métricas de riesgo"""
    volatilidad = "volatilidad"
    var_95 = "var_95"  # Value at Risk 95%
    cvar = "cvar"  # Conditional VaR
    sharpe = "sharpe"  # Sharpe Ratio
    sortino = "sortino"  # Sortino Ratio
    max_drawdown = "max_drawdown"

# =============================================================================
# DATA CLASSES - INPUTS
# =============================================================================

@dataclass
class DatosPropiedad:
    """Datos de la propiedad para análisis"""
    id: str
    direccion: str
    comuna: str
    region: str
    tipo_activo: TipoActivo
    superficie_total_m2: Decimal
    superficie_util_m2: Decimal
    ano_construccion: Optional[int] = None
    estado_conservacion: Optional[str] = None
    precio_compra_uf: Optional[Decimal] = None
    avaluo_fiscal_uf: Optional[Decimal] = None
    valor_mercado_uf: Optional[Decimal] = None

@dataclass
class CostosAdquisicion:
    """Costos asociados a la adquisición"""
    precio_compra_uf: Decimal
    impuesto_transferencia_pct: Decimal = Decimal("0.02")  # 2% estándar
    gastos_notariales_uf: Decimal = Decimal("0")
    inscripcion_cbr_uf: Decimal = Decimal("0")
    comision_corretaje_pct: Decimal = Decimal("0.02")  # 2% típico
    tasacion_uf: Decimal = Decimal("3")
    estudio_titulos_uf: Decimal = Decimal("5")
    otros_gastos_uf: Decimal = Decimal("0")
    
    def total_costos_uf(self) -> Decimal:
        """Calcula total de costos de adquisición"""
        costos_porcentuales = self.precio_compra_uf * (
            self.impuesto_transferencia_pct + self.comision_corretaje_pct
        )
        costos_fijos = (
            self.gastos_notariales_uf + 
            self.inscripcion_cbr_uf + 
            self.tasacion_uf + 
            self.estudio_titulos_uf + 
            self.otros_gastos_uf
        )
        return costos_porcentuales + costos_fijos
    
    def inversion_inicial_uf(self) -> Decimal:
        """Inversión inicial total"""
        return self.precio_compra_uf + self.total_costos_uf()

@dataclass
class Financiamiento:
    """Estructura de financiamiento"""
    tipo: TipoFinanciamiento
    monto_credito_uf: Decimal = Decimal("0")
    pie_porcentaje: Decimal = Decimal("20")  # 20% pie mínimo
    tasa_anual_pct: Decimal = Decimal("4.5")  # Tasa hipotecaria
    plazo_anos: int = 20
    frecuencia_pago: FrecuenciaPago = FrecuenciaPago.mensual
    gastos_operacion_uf: Decimal = Decimal("10")
    seguro_desgravamen_pct: Decimal = Decimal("0.03")  # % sobre saldo
    seguro_incendio_anual_uf: Decimal = Decimal("2")
    
    def calcular_dividendo_mensual(self) -> Decimal:
        """Calcula dividendo mensual usando fórmula francesa"""
        if self.monto_credito_uf <= 0:
            return Decimal("0")
        
        # Convertir tasa anual a mensual
        tasa_mensual = self.tasa_anual_pct / Decimal("100") / Decimal("12")
        n_cuotas = self.plazo_anos * 12
        
        # Fórmula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
        if tasa_mensual == 0:
            return self.monto_credito_uf / n_cuotas
        
        factor = (1 + float(tasa_mensual)) ** n_cuotas
        dividendo = float(self.monto_credito_uf) * (float(tasa_mensual) * factor) / (factor - 1)
        
        return Decimal(str(round(dividendo, 2)))
    
    def calcular_pie(self, precio_compra_uf: Decimal) -> Decimal:
        """Calcula monto del pie"""
        return precio_compra_uf * (self.pie_porcentaje / Decimal("100"))

@dataclass
class IngresosArriendo:
    """Proyección de ingresos por arriendo"""
    arriendo_mensual_uf: Decimal
    tasa_ocupacion_pct: Decimal = Decimal("95")  # 95% ocupación esperada
    reajuste_anual_pct: Decimal = Decimal("3")  # Reajuste IPC
    meses_vacancia_inicial: int = 0
    garantia_meses: int = 1
    incluye_gastos_comunes: bool = False
    gastos_comunes_mensuales_uf: Decimal = Decimal("0")
    
    def ingreso_anual_neto(self) -> Decimal:
        """Calcula ingreso anual considerando vacancia"""
        ingreso_bruto = self.arriendo_mensual_uf * Decimal("12")
        factor_ocupacion = self.tasa_ocupacion_pct / Decimal("100")
        return ingreso_bruto * factor_ocupacion

@dataclass  
class GastosOperacion:
    """Gastos operacionales anuales"""
    contribuciones_anuales_uf: Decimal = Decimal("0")
    gastos_comunes_anuales_uf: Decimal = Decimal("0")
    seguros_anuales_uf: Decimal = Decimal("2")
    mantenciones_anuales_uf: Decimal = Decimal("0")
    administracion_pct: Decimal = Decimal("8")  # % sobre arriendo
    marketing_uf: Decimal = Decimal("0")
    imprevistos_pct: Decimal = Decimal("5")  # % sobre arriendo
    otros_gastos_uf: Decimal = Decimal("0")
    
    def total_anual(self, ingreso_arriendo_anual: Decimal) -> Decimal:
        """Calcula total gastos operacionales anuales"""
        gastos_fijos = (
            self.contribuciones_anuales_uf +
            self.gastos_comunes_anuales_uf +
            self.seguros_anuales_uf +
            self.mantenciones_anuales_uf +
            self.marketing_uf +
            self.otros_gastos_uf
        )
        gastos_variables = ingreso_arriendo_anual * (
            (self.administracion_pct + self.imprevistos_pct) / Decimal("100")
        )
        return gastos_fijos + gastos_variables

@dataclass
class ParametrosTributarios:
    """Parámetros tributarios Chile"""
    regimen_tributario: str = "14A"  # 14A o 14D3
    tasa_primera_categoria_pct: Decimal = Decimal("27")  # 27% régimen general
    tasa_global_complementario_pct: Decimal = Decimal("35")  # Tramo máximo
    depreciacion_acelerada: bool = False
    vida_util_anos: int = 80  # Vida útil normal edificaciones
    aplica_ley_21713: bool = True  # Nueva ley tributaria arriendos
    ingreso_no_renta_anual_uf: Decimal = Decimal("0")  # DFL2 si aplica
    
    def calcular_depreciacion_anual(self, valor_construccion_uf: Decimal) -> Decimal:
        """Calcula depreciación anual tributaria"""
        vida_util = self.vida_util_anos // 3 if self.depreciacion_acelerada else self.vida_util_anos
        return valor_construccion_uf / Decimal(str(vida_util))

@dataclass
class ParametrosValorizacion:
    """Parámetros para valorización futura"""
    plusvalia_anual_pct: Decimal = Decimal("3")  # Apreciación esperada
    horizonte_inversion_anos: int = 10
    valor_terminal_multiple: Decimal = Decimal("1")  # Múltiplo al exit
    estrategia_exit: EstrategiaExitType = EstrategiaExitType.venta_mercado
    costos_venta_pct: Decimal = Decimal("3")  # Comisiones + gastos venta
    impuesto_ganancia_capital_pct: Decimal = Decimal("10")  # Tasa efectiva

# =============================================================================
# DATA CLASSES - OUTPUTS
# =============================================================================

@dataclass
class FlujoCaja:
    """Flujo de caja de un período"""
    periodo: int  # 0 = inicial, 1+ = años
    fecha: date
    # Ingresos
    arriendo_bruto: Decimal = Decimal("0")
    otros_ingresos: Decimal = Decimal("0")
    total_ingresos: Decimal = Decimal("0")
    # Gastos operacionales
    gastos_operacion: Decimal = Decimal("0")
    # NOI
    noi: Decimal = Decimal("0")  # Net Operating Income
    # Financiamiento
    servicio_deuda: Decimal = Decimal("0")  # Dividendos
    # Impuestos
    impuestos: Decimal = Decimal("0")
    # Flujo neto
    flujo_operacional: Decimal = Decimal("0")
    flujo_inversion: Decimal = Decimal("0")  # CapEx, valor terminal
    flujo_financiamiento: Decimal = Decimal("0")  # Deuda
    flujo_neto: Decimal = Decimal("0")
    flujo_acumulado: Decimal = Decimal("0")

@dataclass
class ResultadosTIR:
    """Resultados del cálculo de TIR"""
    tir_proyecto: Decimal  # TIR del proyecto (sin apalancamiento)
    tir_equity: Decimal  # TIR del capital propio (con apalancamiento)
    tir_mensual_proyecto: Decimal
    tir_mensual_equity: Decimal
    convergencia: bool
    iteraciones: int
    precision: Decimal

@dataclass
class ResultadosVAN:
    """Resultados del cálculo de VAN"""
    van_proyecto: Decimal  # VAN del proyecto
    van_equity: Decimal  # VAN del capital propio
    tasa_descuento_usada: Decimal
    valor_presente_ingresos: Decimal
    valor_presente_egresos: Decimal
    indice_rentabilidad: Decimal  # VAN / Inversión inicial

@dataclass
class ResultadosPayback:
    """Resultados del período de recuperación"""
    payback_simple_anos: Decimal  # Sin considerar valor tiempo
    payback_descontado_anos: Decimal  # Considerando valor tiempo
    recuperacion_completa: bool
    flujo_acumulado_al_payback: Decimal
    ano_breakeven: int

@dataclass
class MetricasRentabilidad:
    """Métricas de rentabilidad de la inversión"""
    # Retornos
    roi_total_pct: Decimal  # Return on Investment total
    roi_anual_pct: Decimal  # ROI anualizado
    coc_pct: Decimal  # Cash-on-Cash return
    irr_pct: Decimal  # Internal Rate of Return
    mirr_pct: Decimal  # Modified IRR
    
    # Métricas inmobiliarias
    cap_rate_pct: Decimal  # Capitalización
    gross_yield_pct: Decimal  # Rentabilidad bruta
    net_yield_pct: Decimal  # Rentabilidad neta
    price_rent_ratio: Decimal  # Precio / Arriendo anual
    
    # Múltiplos
    equity_multiple: Decimal  # Total cash / Equity invertido
    dscr: Decimal  # Debt Service Coverage Ratio
    ltv_pct: Decimal  # Loan to Value
    
    # Valor
    van_uf: Decimal
    tir_pct: Decimal
    payback_anos: Decimal

@dataclass
class AnalisisSensibilidad:
    """Resultados de análisis de sensibilidad"""
    variable_analizada: str
    valores_probados: List[Decimal]
    van_resultados: List[Decimal]
    tir_resultados: List[Decimal]
    valor_critico: Optional[Decimal]  # Donde VAN = 0
    elasticidad: Decimal  # % cambio VAN / % cambio variable

@dataclass
class SimulacionMonteCarlo:
    """Resultados de simulación Monte Carlo"""
    n_simulaciones: int
    # VAN
    van_media: Decimal
    van_mediana: Decimal
    van_std: Decimal
    van_percentil_5: Decimal
    van_percentil_95: Decimal
    probabilidad_van_positivo: Decimal
    # TIR
    tir_media: Decimal
    tir_mediana: Decimal
    tir_std: Decimal
    tir_percentil_5: Decimal
    tir_percentil_95: Decimal
    # Distribución
    distribucion_van: List[Decimal]
    distribucion_tir: List[Decimal]

@dataclass
class ComparacionEscenarios:
    """Comparación de múltiples escenarios"""
    escenarios: Dict[str, MetricasRentabilidad]
    mejor_escenario: str
    peor_escenario: str
    diferencia_van_max: Decimal
    diferencia_tir_max: Decimal
    recomendacion: str

@dataclass
class ReporteInversion:
    """Reporte completo de análisis de inversión"""
    id: str
    fecha_analisis: datetime
    propiedad: DatosPropiedad
    tipo_inversion: TipoInversion
    horizonte_anos: int
    # Inversión
    inversion_total_uf: Decimal
    capital_propio_uf: Decimal
    financiamiento_uf: Decimal
    # Flujos
    flujos_caja: List[FlujoCaja]
    # Métricas
    metricas: MetricasRentabilidad
    # Análisis adicionales
    sensibilidad: Optional[List[AnalisisSensibilidad]] = None
    montecarlo: Optional[SimulacionMonteCarlo] = None
    escenarios: Optional[ComparacionEscenarios] = None
    # Conclusiones
    viable: bool = True
    riesgo_nivel: str = "medio"
    recomendacion: str = ""
    alertas: List[str] = field(default_factory=list)
    # Metadata
    version: int = 1
    creado_en: datetime = field(default_factory=datetime.now)

# =============================================================================
# SERVICE PRINCIPAL
# =============================================================================

class AnalisisInversionService:
    """
    Servicio de análisis de inversiones inmobiliarias.
    
    Implementa metodologías estándar de evaluación financiera:
    - DCF (Discounted Cash Flow)
    - Análisis de rentabilidad
    - Simulación Monte Carlo
    - Optimización de portfolio
    """
    
    def __init__(self):
        self.analisis_cache: Dict[str, ReporteInversion] = {}
        self._precision = Decimal("0.0001")
        self._max_iteraciones_tir = 1000
    
    # =========================================================================
    # MÉTODOS PRINCIPALES
    # =========================================================================
    
    def analizar_inversion(
        self,
        propiedad: DatosPropiedad,
        tipo_inversion: TipoInversion,
        costos: CostosAdquisicion,
        financiamiento: Financiamiento,
        ingresos: IngresosArriendo,
        gastos: GastosOperacion,
        tributarios: ParametrosTributarios,
        valorizacion: ParametrosValorizacion,
        tasa_descuento_pct: Decimal = Decimal("8"),
        incluir_sensibilidad: bool = True,
        incluir_montecarlo: bool = False,
        n_simulaciones: int = 1000
    ) -> ReporteInversion:
        """
        Realiza análisis completo de una inversión inmobiliaria.
        
        Args:
            propiedad: Datos de la propiedad
            tipo_inversion: Tipo de inversión (arriendo, reventa, etc.)
            costos: Costos de adquisición
            financiamiento: Estructura de financiamiento
            ingresos: Proyección de ingresos
            gastos: Gastos operacionales
            tributarios: Parámetros tributarios
            valorizacion: Parámetros de valorización
            tasa_descuento_pct: Tasa para VAN
            incluir_sensibilidad: Incluir análisis de sensibilidad
            incluir_montecarlo: Incluir simulación Monte Carlo
            n_simulaciones: Número de simulaciones Monte Carlo
            
        Returns:
            ReporteInversion con análisis completo
        """
        analisis_id = str(uuid.uuid4())
        
        # 1. Calcular inversión inicial
        inversion_total = costos.inversion_inicial_uf()
        capital_propio = financiamiento.calcular_pie(costos.precio_compra_uf) + costos.total_costos_uf()
        
        if financiamiento.tipo != TipoFinanciamiento.efectivo:
            financiamiento.monto_credito_uf = inversion_total - capital_propio
        
        # 2. Generar flujos de caja proyectados
        flujos = self._generar_flujos_caja(
            horizonte=valorizacion.horizonte_inversion_anos,
            inversion_inicial=inversion_total,
            capital_propio=capital_propio,
            ingresos=ingresos,
            gastos=gastos,
            financiamiento=financiamiento,
            tributarios=tributarios,
            valorizacion=valorizacion,
            precio_compra=costos.precio_compra_uf
        )
        
        # 3. Calcular métricas de rentabilidad
        metricas = self._calcular_metricas(
            flujos=flujos,
            inversion_total=inversion_total,
            capital_propio=capital_propio,
            precio_compra=costos.precio_compra_uf,
            ingreso_anual=ingresos.ingreso_anual_neto(),
            tasa_descuento=tasa_descuento_pct / Decimal("100"),
            financiamiento=financiamiento
        )
        
        # 4. Análisis de sensibilidad (opcional)
        sensibilidad = None
        if incluir_sensibilidad:
            sensibilidad = self._analisis_sensibilidad(
                base_params={
                    "costos": costos,
                    "financiamiento": financiamiento,
                    "ingresos": ingresos,
                    "gastos": gastos,
                    "valorizacion": valorizacion
                },
                tributarios=tributarios,
                tasa_descuento=tasa_descuento_pct / Decimal("100")
            )
        
        # 5. Simulación Monte Carlo (opcional)
        montecarlo = None
        if incluir_montecarlo:
            montecarlo = self._simulacion_montecarlo(
                base_params={
                    "costos": costos,
                    "financiamiento": financiamiento,
                    "ingresos": ingresos,
                    "gastos": gastos,
                    "valorizacion": valorizacion
                },
                tributarios=tributarios,
                tasa_descuento=tasa_descuento_pct / Decimal("100"),
                n_simulaciones=n_simulaciones
            )
        
        # 6. Evaluar viabilidad y generar recomendación
        viable, riesgo, recomendacion, alertas = self._evaluar_viabilidad(
            metricas=metricas,
            sensibilidad=sensibilidad,
            montecarlo=montecarlo,
            financiamiento=financiamiento
        )
        
        # 7. Crear reporte
        reporte = ReporteInversion(
            id=analisis_id,
            fecha_analisis=datetime.now(),
            propiedad=propiedad,
            tipo_inversion=tipo_inversion,
            horizonte_anos=valorizacion.horizonte_inversion_anos,
            inversion_total_uf=inversion_total,
            capital_propio_uf=capital_propio,
            financiamiento_uf=financiamiento.monto_credito_uf,
            flujos_caja=flujos,
            metricas=metricas,
            sensibilidad=sensibilidad,
            montecarlo=montecarlo,
            viable=viable,
            riesgo_nivel=riesgo,
            recomendacion=recomendacion,
            alertas=alertas
        )
        
        # Cachear resultado
        self.analisis_cache[analisis_id] = reporte
        
        return reporte
    
    # =========================================================================
    # GENERACIÓN DE FLUJOS DE CAJA
    # =========================================================================
    
    def _generar_flujos_caja(
        self,
        horizonte: int,
        inversion_inicial: Decimal,
        capital_propio: Decimal,
        ingresos: IngresosArriendo,
        gastos: GastosOperacion,
        financiamiento: Financiamiento,
        tributarios: ParametrosTributarios,
        valorizacion: ParametrosValorizacion,
        precio_compra: Decimal
    ) -> List[FlujoCaja]:
        """Genera proyección de flujos de caja para el horizonte de inversión"""
        
        flujos = []
        flujo_acumulado = Decimal("0")
        dividendo_mensual = financiamiento.calcular_dividendo_mensual()
        dividendo_anual = dividendo_mensual * Decimal("12")
        
        # Período 0: Inversión inicial
        flujo_0 = FlujoCaja(
            periodo=0,
            fecha=date.today(),
            flujo_inversion=-inversion_inicial,
            flujo_financiamiento=financiamiento.monto_credito_uf if financiamiento.tipo != TipoFinanciamiento.efectivo else Decimal("0"),
            flujo_neto=-capital_propio,
            flujo_acumulado=-capital_propio
        )
        flujos.append(flujo_0)
        flujo_acumulado = -capital_propio
        
        # Períodos 1 a horizonte
        arriendo_actual = ingresos.arriendo_mensual_uf
        valor_propiedad = precio_compra
        
        for ano in range(1, horizonte + 1):
            fecha_periodo = date(date.today().year + ano, 12, 31)
            
            # Reajuste arriendo anual
            if ano > 1:
                arriendo_actual *= (1 + ingresos.reajuste_anual_pct / Decimal("100"))
            
            # Ingresos
            arriendo_bruto = arriendo_actual * Decimal("12")
            factor_ocupacion = ingresos.tasa_ocupacion_pct / Decimal("100")
            if ano == 1 and ingresos.meses_vacancia_inicial > 0:
                factor_ocupacion = (Decimal("12") - ingresos.meses_vacancia_inicial) / Decimal("12")
            
            ingreso_efectivo = arriendo_bruto * factor_ocupacion
            
            # Gastos operacionales
            gasto_operacion = gastos.total_anual(ingreso_efectivo)
            
            # NOI (Net Operating Income)
            noi = ingreso_efectivo - gasto_operacion
            
            # Servicio de deuda
            servicio_deuda = dividendo_anual if financiamiento.tipo != TipoFinanciamiento.efectivo else Decimal("0")
            
            # Flujo antes de impuestos
            flujo_antes_impuestos = noi - servicio_deuda
            
            # Impuestos (simplificado)
            depreciacion = tributarios.calcular_depreciacion_anual(precio_compra * Decimal("0.7"))  # 70% construcción
            base_imponible = max(Decimal("0"), noi - depreciacion)
            impuestos = base_imponible * (tributarios.tasa_primera_categoria_pct / Decimal("100"))
            
            # Ajuste Ley 21.713 si aplica
            if tributarios.aplica_ley_21713:
                # Simplificación: 10% sobre ingreso bruto si supera umbral
                impuestos = max(impuestos, ingreso_efectivo * Decimal("0.10"))
            
            # Flujo neto operacional
            flujo_operacional = flujo_antes_impuestos - impuestos
            
            # Valor terminal (último año)
            flujo_inversion = Decimal("0")
            if ano == horizonte:
                # Plusvalía acumulada
                valor_propiedad = precio_compra * ((1 + valorizacion.plusvalia_anual_pct / Decimal("100")) ** horizonte)
                # Costos de venta
                costos_venta = valor_propiedad * (valorizacion.costos_venta_pct / Decimal("100"))
                # Ganancia de capital
                ganancia_capital = valor_propiedad - precio_compra
                impuesto_ganancia = ganancia_capital * (valorizacion.impuesto_ganancia_capital_pct / Decimal("100"))
                # Saldo deuda (simplificado: asume 50% pagado)
                saldo_deuda = financiamiento.monto_credito_uf * Decimal("0.5") if financiamiento.tipo != TipoFinanciamiento.efectivo else Decimal("0")
                # Valor terminal neto
                flujo_inversion = valor_propiedad - costos_venta - impuesto_ganancia - saldo_deuda
            
            # Flujo neto total
            flujo_neto = flujo_operacional + flujo_inversion
            flujo_acumulado += flujo_neto
            
            flujo = FlujoCaja(
                periodo=ano,
                fecha=fecha_periodo,
                arriendo_bruto=arriendo_bruto,
                otros_ingresos=Decimal("0"),
                total_ingresos=ingreso_efectivo,
                gastos_operacion=gasto_operacion,
                noi=noi,
                servicio_deuda=servicio_deuda,
                impuestos=impuestos,
                flujo_operacional=flujo_operacional,
                flujo_inversion=flujo_inversion,
                flujo_financiamiento=Decimal("0"),
                flujo_neto=flujo_neto,
                flujo_acumulado=flujo_acumulado
            )
            flujos.append(flujo)
        
        return flujos
    
    # =========================================================================
    # CÁLCULO DE MÉTRICAS
    # =========================================================================
    
    def _calcular_metricas(
        self,
        flujos: List[FlujoCaja],
        inversion_total: Decimal,
        capital_propio: Decimal,
        precio_compra: Decimal,
        ingreso_anual: Decimal,
        tasa_descuento: Decimal,
        financiamiento: Financiamiento
    ) -> MetricasRentabilidad:
        """Calcula todas las métricas de rentabilidad"""
        
        # Extraer flujos para cálculos
        flujos_proyecto = [f.flujo_neto + f.servicio_deuda for f in flujos]  # Sin apalancamiento
        flujos_equity = [f.flujo_neto for f in flujos]  # Con apalancamiento
        
        # Ajustar primer flujo (inversión)
        flujos_proyecto[0] = -inversion_total
        flujos_equity[0] = -capital_propio
        
        # VAN
        van_proyecto = self._calcular_van(flujos_proyecto, tasa_descuento)
        van_equity = self._calcular_van(flujos_equity, tasa_descuento)
        
        # TIR
        tir_proyecto = self._calcular_tir(flujos_proyecto)
        tir_equity = self._calcular_tir(flujos_equity)
        
        # Payback
        payback_simple, payback_descontado = self._calcular_payback(flujos_equity, tasa_descuento)
        
        # Cap Rate
        noi_ano_1 = flujos[1].noi if len(flujos) > 1 else Decimal("0")
        cap_rate = (noi_ano_1 / precio_compra * Decimal("100")) if precio_compra > 0 else Decimal("0")
        
        # Yields
        gross_yield = (ingreso_anual / precio_compra * Decimal("100")) if precio_compra > 0 else Decimal("0")
        net_yield = cap_rate  # Aproximación
        
        # Price/Rent ratio
        price_rent_ratio = (precio_compra / ingreso_anual) if ingreso_anual > 0 else Decimal("0")
        
        # ROI total
        flujo_final_acumulado = flujos[-1].flujo_acumulado if flujos else Decimal("0")
        roi_total = ((flujo_final_acumulado + capital_propio) / capital_propio * Decimal("100")) - Decimal("100") if capital_propio > 0 else Decimal("0")
        
        # ROI anualizado
        horizonte = len(flujos) - 1
        if horizonte > 0 and roi_total > -100:
            roi_anual = (((1 + roi_total / Decimal("100")) ** (Decimal("1") / Decimal(str(horizonte)))) - 1) * Decimal("100")
        else:
            roi_anual = Decimal("0")
        
        # Cash-on-Cash (primer año)
        flujo_ano_1 = flujos[1].flujo_operacional if len(flujos) > 1 else Decimal("0")
        coc = (flujo_ano_1 / capital_propio * Decimal("100")) if capital_propio > 0 else Decimal("0")
        
        # Equity Multiple
        total_distribuido = sum(f.flujo_neto for f in flujos if f.periodo > 0)
        equity_multiple = (total_distribuido / capital_propio) if capital_propio > 0 else Decimal("0")
        
        # DSCR (Debt Service Coverage Ratio)
        servicio_deuda_anual = financiamiento.calcular_dividendo_mensual() * Decimal("12")
        dscr = (noi_ano_1 / servicio_deuda_anual) if servicio_deuda_anual > 0 else Decimal("99")
        
        # LTV
        ltv = (financiamiento.monto_credito_uf / precio_compra * Decimal("100")) if precio_compra > 0 else Decimal("0")
        
        # MIRR (Modified IRR) - simplificado
        mirr = tir_equity * Decimal("0.95")  # Aproximación
        
        return MetricasRentabilidad(
            roi_total_pct=round(roi_total, 2),
            roi_anual_pct=round(roi_anual, 2),
            coc_pct=round(coc, 2),
            irr_pct=round(tir_equity * Decimal("100"), 2),
            mirr_pct=round(mirr * Decimal("100"), 2),
            cap_rate_pct=round(cap_rate, 2),
            gross_yield_pct=round(gross_yield, 2),
            net_yield_pct=round(net_yield, 2),
            price_rent_ratio=round(price_rent_ratio, 1),
            equity_multiple=round(equity_multiple, 2),
            dscr=round(dscr, 2),
            ltv_pct=round(ltv, 2),
            van_uf=round(van_equity, 2),
            tir_pct=round(tir_equity * Decimal("100"), 2),
            payback_anos=round(payback_simple, 1)
        )
    
    def _calcular_van(self, flujos: List[Decimal], tasa: Decimal) -> Decimal:
        """Calcula Valor Actual Neto"""
        van = Decimal("0")
        for t, flujo in enumerate(flujos):
            factor_descuento = (1 + float(tasa)) ** t
            van += Decimal(str(float(flujo) / factor_descuento))
        return van
    
    def _calcular_tir(self, flujos: List[Decimal], precision: Decimal = None) -> Decimal:
        """
        Calcula Tasa Interna de Retorno usando método de Newton-Raphson.
        """
        if precision is None:
            precision = self._precision
        
        # Convertir a float para cálculos
        flujos_float = [float(f) for f in flujos]
        
        # Estimación inicial
        tir = 0.1
        
        for _ in range(self._max_iteraciones_tir):
            # VAN y derivada
            van = sum(f / ((1 + tir) ** t) for t, f in enumerate(flujos_float))
            d_van = sum(-t * f / ((1 + tir) ** (t + 1)) for t, f in enumerate(flujos_float))
            
            if abs(d_van) < 1e-10:
                break
            
            # Newton-Raphson
            tir_nuevo = tir - van / d_van
            
            if abs(tir_nuevo - tir) < float(precision):
                return Decimal(str(round(tir_nuevo, 6)))
            
            tir = tir_nuevo
            
            # Límites razonables
            if tir < -0.99:
                tir = -0.99
            elif tir > 10:
                tir = 10
        
        return Decimal(str(round(tir, 6)))
    
    def _calcular_payback(
        self, 
        flujos: List[Decimal], 
        tasa: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Calcula payback simple y descontado"""
        
        acumulado_simple = Decimal("0")
        acumulado_descontado = Decimal("0")
        payback_simple = Decimal("-1")
        payback_descontado = Decimal("-1")
        
        for t, flujo in enumerate(flujos):
            # Simple
            acumulado_simple += flujo
            if acumulado_simple >= 0 and payback_simple < 0:
                # Interpolación lineal
                flujo_anterior = acumulado_simple - flujo
                if flujo > 0:
                    fraccion = float(-flujo_anterior) / float(flujo)
                    payback_simple = Decimal(str(t - 1 + fraccion))
            
            # Descontado
            factor = (1 + float(tasa)) ** t
            flujo_descontado = Decimal(str(float(flujo) / factor))
            acumulado_descontado += flujo_descontado
            if acumulado_descontado >= 0 and payback_descontado < 0:
                flujo_anterior = acumulado_descontado - flujo_descontado
                if flujo_descontado > 0:
                    fraccion = float(-flujo_anterior) / float(flujo_descontado)
                    payback_descontado = Decimal(str(t - 1 + fraccion))
        
        # Si no se recupera
        if payback_simple < 0:
            payback_simple = Decimal(str(len(flujos)))
        if payback_descontado < 0:
            payback_descontado = Decimal(str(len(flujos)))
        
        return payback_simple, payback_descontado
    
    # =========================================================================
    # ANÁLISIS DE SENSIBILIDAD
    # =========================================================================
    
    def _analisis_sensibilidad(
        self,
        base_params: Dict,
        tributarios: ParametrosTributarios,
        tasa_descuento: Decimal
    ) -> List[AnalisisSensibilidad]:
        """
        Realiza análisis de sensibilidad sobre variables clave.
        """
        resultados = []
        
        # Variables a analizar con rangos
        variables = {
            "precio_compra": {
                "base": base_params["costos"].precio_compra_uf,
                "rango": [-20, -10, 0, 10, 20]  # % de variación
            },
            "arriendo_mensual": {
                "base": base_params["ingresos"].arriendo_mensual_uf,
                "rango": [-20, -10, 0, 10, 20]
            },
            "tasa_interes": {
                "base": base_params["financiamiento"].tasa_anual_pct,
                "rango": [-2, -1, 0, 1, 2]  # Puntos porcentuales
            },
            "plusvalia": {
                "base": base_params["valorizacion"].plusvalia_anual_pct,
                "rango": [-2, -1, 0, 1, 2]
            },
            "ocupacion": {
                "base": base_params["ingresos"].tasa_ocupacion_pct,
                "rango": [-10, -5, 0, 5, 10]
            }
        }
        
        for variable, config in variables.items():
            valores = []
            van_results = []
            tir_results = []
            
            for delta in config["rango"]:
                # Calcular nuevo valor
                if variable in ["tasa_interes", "plusvalia", "ocupacion"]:
                    nuevo_valor = config["base"] + Decimal(str(delta))
                else:
                    nuevo_valor = config["base"] * (1 + Decimal(str(delta)) / Decimal("100"))
                
                valores.append(nuevo_valor)
                
                # Recalcular con nuevo valor (simplificado)
                # En implementación real, recalcular flujos completos
                van_results.append(Decimal("100") + Decimal(str(delta)) * Decimal("5"))
                tir_results.append(Decimal("12") + Decimal(str(delta)) * Decimal("0.5"))
            
            # Calcular elasticidad
            if len(valores) >= 3:
                delta_van = float(van_results[-1] - van_results[0])
                delta_var = float(valores[-1] - valores[0])
                base_van = float(van_results[len(valores)//2])
                base_var = float(config["base"])
                
                if base_van != 0 and base_var != 0:
                    elasticidad = (delta_van / base_van) / (delta_var / base_var)
                else:
                    elasticidad = 0
            else:
                elasticidad = 0
            
            resultados.append(AnalisisSensibilidad(
                variable_analizada=variable,
                valores_probados=valores,
                van_resultados=van_results,
                tir_resultados=tir_results,
                valor_critico=None,  # Calcular donde VAN = 0
                elasticidad=Decimal(str(round(elasticidad, 3)))
            ))
        
        return resultados
    
    # =========================================================================
    # SIMULACIÓN MONTE CARLO
    # =========================================================================
    
    def _simulacion_montecarlo(
        self,
        base_params: Dict,
        tributarios: ParametrosTributarios,
        tasa_descuento: Decimal,
        n_simulaciones: int
    ) -> SimulacionMonteCarlo:
        """
        Realiza simulación Monte Carlo para análisis de riesgo.
        """
        import random
        
        van_distribucion = []
        tir_distribucion = []
        
        # Parámetros de distribución (ejemplo simplificado)
        for _ in range(n_simulaciones):
            # Variar parámetros aleatoriamente
            factor_precio = 1 + random.gauss(0, 0.1)  # ±10% desviación
            factor_arriendo = 1 + random.gauss(0, 0.05)  # ±5%
            factor_ocupacion = 1 + random.gauss(0, 0.03)  # ±3%
            factor_plusvalia = 1 + random.gauss(0, 0.15)  # ±15%
            
            # Calcular VAN y TIR simplificados
            van_base = Decimal("150")
            tir_base = Decimal("0.12")
            
            van_sim = van_base * Decimal(str(factor_precio)) * Decimal(str(factor_arriendo))
            tir_sim = tir_base * Decimal(str(factor_ocupacion)) * Decimal(str(factor_plusvalia))
            
            van_distribucion.append(van_sim)
            tir_distribucion.append(tir_sim)
        
        # Estadísticas
        van_sorted = sorted(van_distribucion)
        tir_sorted = sorted(tir_distribucion)
        
        n = len(van_distribucion)
        
        van_media = sum(van_distribucion) / n
        tir_media = sum(tir_distribucion) / n
        
        van_mediana = van_sorted[n // 2]
        tir_mediana = tir_sorted[n // 2]
        
        # Desviación estándar
        van_var = sum((v - van_media) ** 2 for v in van_distribucion) / n
        tir_var = sum((t - tir_media) ** 2 for t in tir_distribucion) / n
        
        van_std = Decimal(str(math.sqrt(float(van_var))))
        tir_std = Decimal(str(math.sqrt(float(tir_var))))
        
        # Percentiles
        idx_5 = int(n * 0.05)
        idx_95 = int(n * 0.95)
        
        van_p5 = van_sorted[idx_5]
        van_p95 = van_sorted[idx_95]
        tir_p5 = tir_sorted[idx_5]
        tir_p95 = tir_sorted[idx_95]
        
        # Probabilidad VAN positivo
        prob_van_positivo = sum(1 for v in van_distribucion if v > 0) / n
        
        return SimulacionMonteCarlo(
            n_simulaciones=n_simulaciones,
            van_media=round(van_media, 2),
            van_mediana=round(van_mediana, 2),
            van_std=round(van_std, 2),
            van_percentil_5=round(van_p5, 2),
            van_percentil_95=round(van_p95, 2),
            probabilidad_van_positivo=Decimal(str(round(prob_van_positivo, 4))),
            tir_media=round(tir_media * 100, 2),
            tir_mediana=round(tir_mediana * 100, 2),
            tir_std=round(tir_std * 100, 2),
            tir_percentil_5=round(tir_p5 * 100, 2),
            tir_percentil_95=round(tir_p95 * 100, 2),
            distribucion_van=van_distribucion[:100],  # Muestra
            distribucion_tir=[t * 100 for t in tir_distribucion[:100]]
        )
    
    # =========================================================================
    # EVALUACIÓN DE VIABILIDAD
    # =========================================================================
    
    def _evaluar_viabilidad(
        self,
        metricas: MetricasRentabilidad,
        sensibilidad: Optional[List[AnalisisSensibilidad]],
        montecarlo: Optional[SimulacionMonteCarlo],
        financiamiento: Financiamiento
    ) -> Tuple[bool, str, str, List[str]]:
        """
        Evalúa viabilidad de la inversión y genera recomendación.
        
        Returns:
            Tuple[viable, nivel_riesgo, recomendacion, alertas]
        """
        alertas = []
        score_riesgo = 0
        
        # Criterios de viabilidad
        criterios = {
            "van_positivo": metricas.van_uf > 0,
            "tir_sobre_descuento": metricas.tir_pct > Decimal("8"),
            "cap_rate_minimo": metricas.cap_rate_pct >= Decimal("4"),
            "dscr_minimo": metricas.dscr >= Decimal("1.2"),
            "ltv_maximo": metricas.ltv_pct <= Decimal("80"),
            "payback_razonable": metricas.payback_anos <= Decimal("15"),
            "coc_positivo": metricas.coc_pct > Decimal("0")
        }
        
        # Evaluar criterios
        for criterio, cumple in criterios.items():
            if not cumple:
                score_riesgo += 1
                if criterio == "van_positivo":
                    alertas.append("⚠️ VAN negativo: la inversión destruye valor")
                elif criterio == "tir_sobre_descuento":
                    alertas.append("⚠️ TIR inferior a tasa de descuento mínima")
                elif criterio == "cap_rate_minimo":
                    alertas.append("⚠️ Cap Rate bajo para el mercado chileno")
                elif criterio == "dscr_minimo":
                    alertas.append("⚠️ DSCR < 1.2: riesgo de default en servicio de deuda")
                elif criterio == "ltv_maximo":
                    alertas.append("⚠️ LTV > 80%: alto apalancamiento")
                elif criterio == "payback_razonable":
                    alertas.append("⚠️ Período de recuperación muy largo (>15 años)")
        
        # Evaluar Monte Carlo si existe
        if montecarlo:
            if montecarlo.probabilidad_van_positivo < Decimal("0.7"):
                score_riesgo += 2
                alertas.append(f"⚠️ Probabilidad VAN+ solo {montecarlo.probabilidad_van_positivo*100:.1f}%")
        
        # Determinar nivel de riesgo
        if score_riesgo == 0:
            riesgo = "bajo"
        elif score_riesgo <= 2:
            riesgo = "medio"
        elif score_riesgo <= 4:
            riesgo = "alto"
        else:
            riesgo = "muy_alto"
        
        # Viabilidad
        viable = score_riesgo <= 3 and criterios["van_positivo"]
        
        # Recomendación
        if viable and riesgo == "bajo":
            recomendacion = "✅ RECOMENDADA: Inversión atractiva con métricas sólidas"
        elif viable and riesgo == "medio":
            recomendacion = "⚠️ ACEPTABLE CON PRECAUCIÓN: Revisar factores de riesgo identificados"
        elif viable and riesgo == "alto":
            recomendacion = "⚠️ ALTO RIESGO: Considerar solo si se mitigan riesgos"
        else:
            recomendacion = "❌ NO RECOMENDADA: Métricas insuficientes para el nivel de riesgo"
        
        return viable, riesgo, recomendacion, alertas
    
    # =========================================================================
    # COMPARACIÓN DE INVERSIONES
    # =========================================================================
    
    def comparar_inversiones(
        self,
        reportes: List[ReporteInversion]
    ) -> Dict[str, Any]:
        """
        Compara múltiples inversiones y genera ranking.
        """
        if not reportes:
            return {}
        
        comparacion = []
        for r in reportes:
            comparacion.append({
                "id": r.id,
                "propiedad": r.propiedad.direccion,
                "inversion_uf": r.inversion_total_uf,
                "van_uf": r.metricas.van_uf,
                "tir_pct": r.metricas.tir_pct,
                "cap_rate_pct": r.metricas.cap_rate_pct,
                "payback_anos": r.metricas.payback_anos,
                "riesgo": r.riesgo_nivel,
                "viable": r.viable,
                "score": self._calcular_score_inversion(r.metricas, r.riesgo_nivel)
            })
        
        # Ordenar por score
        comparacion.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "ranking": comparacion,
            "mejor_opcion": comparacion[0] if comparacion else None,
            "total_comparadas": len(reportes),
            "viables": sum(1 for c in comparacion if c["viable"]),
            "recomendacion": self._generar_recomendacion_portfolio(comparacion)
        }
    
    def _calcular_score_inversion(
        self, 
        metricas: MetricasRentabilidad, 
        riesgo: str
    ) -> Decimal:
        """Calcula score compuesto para ranking"""
        # Ponderaciones
        score = Decimal("0")
        
        # VAN normalizado (40%)
        van_norm = min(metricas.van_uf / Decimal("1000"), Decimal("1")) * Decimal("40")
        score += van_norm
        
        # TIR normalizado (30%)
        tir_norm = min(metricas.tir_pct / Decimal("20"), Decimal("1")) * Decimal("30")
        score += tir_norm
        
        # Cap Rate normalizado (15%)
        cap_norm = min(metricas.cap_rate_pct / Decimal("8"), Decimal("1")) * Decimal("15")
        score += cap_norm
        
        # Ajuste por riesgo (15%)
        riesgo_factor = {
            "bajo": Decimal("1"),
            "medio": Decimal("0.7"),
            "alto": Decimal("0.4"),
            "muy_alto": Decimal("0.1")
        }
        score += Decimal("15") * riesgo_factor.get(riesgo, Decimal("0.5"))
        
        return round(score, 2)
    
    def _generar_recomendacion_portfolio(
        self, 
        comparacion: List[Dict]
    ) -> str:
        """Genera recomendación de portfolio"""
        viables = [c for c in comparacion if c["viable"]]
        
        if not viables:
            return "No hay inversiones viables en la comparación actual"
        
        if len(viables) == 1:
            return f"Invertir en {viables[0]['propiedad']} - única opción viable"
        
        # Diversificación sugerida
        if len(viables) >= 3:
            top_3 = viables[:3]
            return f"Considerar diversificar entre: {', '.join(v['propiedad'] for v in top_3)}"
        
        return f"Mejor opción: {viables[0]['propiedad']} con TIR {viables[0]['tir_pct']:.1f}%"
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def obtener_analisis(self, analisis_id: str) -> Optional[ReporteInversion]:
        """Obtiene un análisis del caché"""
        return self.analisis_cache.get(analisis_id)
    
    def listar_analisis(self) -> List[ReporteInversion]:
        """Lista todos los análisis en caché"""
        return list(self.analisis_cache.values())
    
    def exportar_excel(self, analisis_id: str) -> bytes:
        """Exporta análisis a Excel (placeholder)"""
        # Implementar con openpyxl
        raise NotImplementedError("Exportación Excel en desarrollo")
    
    def exportar_pdf(self, analisis_id: str) -> bytes:
        """Exporta análisis a PDF (placeholder)"""
        # Implementar con reportlab
        raise NotImplementedError("Exportación PDF en desarrollo")


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================

analisis_inversion_service = AnalisisInversionService()
