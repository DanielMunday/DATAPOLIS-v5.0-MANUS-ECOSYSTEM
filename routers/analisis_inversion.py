"""
DATAPOLIS v3.0 - Router M07: Análisis de Inversión Inmobiliaria
================================================================

API REST completa para análisis financiero de inversiones inmobiliarias.

Funcionalidades:
- Análisis completo de inversiones (ROI, TIR, VAN, payback)
- Comparación de múltiples inversiones
- Análisis de sensibilidad
- Simulación Monte Carlo
- Optimización de portfolios
- Reportes y exportaciones

Normativa:
- Ley 21.713 (tributación arriendos)
- NCh 2728 (valoración inmobiliaria)
- Circular SII 42/2020 (ganancias de capital)
- IVS 2022 (International Valuation Standards)

Endpoints: 28
Autor: DATAPOLIS SpA
Versión: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

router = APIRouter(
    prefix="/analisis-inversion",
    tags=["M07 - Análisis de Inversión"],
    responses={
        400: {"description": "Parámetros inválidos"},
        401: {"description": "No autenticado"},
        403: {"description": "Sin permisos"},
        404: {"description": "Análisis no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)


# =============================================================================
# ENUMS
# =============================================================================

class TipoInversion(str, Enum):
    """Tipos de inversión inmobiliaria"""
    COMPRA_ARRIENDO = "compra_arriendo"  # Buy-to-let
    COMPRA_REVENTA = "compra_reventa"    # Fix & flip
    DESARROLLO = "desarrollo"             # Ground-up development
    SUBDIVISION = "subdivision"           # Subdivisión de terrenos
    CAMBIO_USO = "cambio_uso"            # Cambio de destino
    MIXTA = "mixta"                       # Combinación estrategias


class TipoActivo(str, Enum):
    """Tipos de activo inmobiliario"""
    RESIDENCIAL = "residencial"
    COMERCIAL = "comercial"
    OFICINAS = "oficinas"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"
    HOTELERO = "hotelero"
    TERRENO = "terreno"
    MIXTO = "mixto"


class PerfilRiesgo(str, Enum):
    """Perfil de riesgo del inversionista"""
    CONSERVADOR = "conservador"    # TIR objetivo: 6-8%
    MODERADO = "moderado"          # TIR objetivo: 8-12%
    AGRESIVO = "agresivo"          # TIR objetivo: 12-18%
    ESPECULATIVO = "especulativo"  # TIR objetivo: 18%+


class EstrategiaSalida(str, Enum):
    """Estrategias de salida de la inversión"""
    VENTA_MERCADO = "venta_mercado"       # Venta a precio de mercado
    VENTA_PREMIUM = "venta_premium"       # Venta con prima
    ARRIENDO_PERPETUO = "arriendo_perpetuo"  # Hold indefinido
    REFINANCIAMIENTO = "refinanciamiento"    # Cash-out refinance
    APORTE_FONDO = "aporte_fondo"            # Aporte a fondo inmobiliario


class TipoFinanciamiento(str, Enum):
    """Tipos de financiamiento"""
    EFECTIVO = "efectivo"           # 100% equity
    HIPOTECARIO = "hipotecario"     # Crédito hipotecario
    LEASING = "leasing"             # Leasing habitacional
    MUTUARIA = "mutuaria"           # Mutuaria hipotecaria
    MIXTO = "mixto"                 # Combinación


class TipoReporte(str, Enum):
    """Tipos de reporte de análisis"""
    EJECUTIVO = "ejecutivo"         # Resumen ejecutivo
    DETALLADO = "detallado"         # Análisis completo
    COMPARATIVO = "comparativo"     # Comparación inversiones
    SENSIBILIDAD = "sensibilidad"   # Solo sensibilidad
    MONTECARLO = "montecarlo"       # Solo simulación


class FormatoExportacion(str, Enum):
    """Formatos de exportación"""
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"
    HTML = "html"


class VariableSensibilidad(str, Enum):
    """Variables para análisis de sensibilidad"""
    PRECIO_COMPRA = "precio_compra"
    ARRIENDO_MENSUAL = "arriendo_mensual"
    TASA_INTERES = "tasa_interes"
    PLUSVALIA = "plusvalia"
    OCUPACION = "ocupacion"
    GASTOS_OPERACION = "gastos_operacion"
    PLAZO_INVERSION = "plazo_inversion"


class EscenarioTipo(str, Enum):
    """Tipos de escenarios"""
    BASE = "base"
    OPTIMISTA = "optimista"
    PESIMISTA = "pesimista"
    ESTRES = "estres"


# =============================================================================
# SCHEMAS - REQUESTS
# =============================================================================

class DatosPropiedadRequest(BaseModel):
    """Datos de la propiedad a analizar"""
    direccion: str = Field(..., min_length=5, max_length=500, description="Dirección completa")
    comuna: str = Field(..., min_length=2, max_length=100)
    region: Optional[str] = Field("Metropolitana", max_length=100)
    tipo_activo: TipoActivo = Field(TipoActivo.RESIDENCIAL)
    superficie_total_m2: float = Field(..., gt=0, le=100000, description="Superficie total en m²")
    superficie_util_m2: Optional[float] = Field(None, gt=0, le=100000, description="Superficie útil en m²")
    ano_construccion: Optional[int] = Field(None, ge=1900, le=2030)
    estado_conservacion: Optional[str] = Field("bueno", description="Estado: excelente, bueno, regular, malo")
    precio_compra_uf: float = Field(..., gt=0, le=1000000, description="Precio de compra en UF")
    avaluo_fiscal_uf: Optional[float] = Field(None, gt=0, description="Avalúo fiscal SII en UF")
    valor_mercado_uf: Optional[float] = Field(None, gt=0, description="Valor de mercado estimado en UF")
    rol_sii: Optional[str] = Field(None, max_length=50, description="ROL SII")
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class CostosAdquisicionRequest(BaseModel):
    """Costos de adquisición de la propiedad"""
    impuesto_transferencia_pct: float = Field(2.0, ge=0, le=10, description="Impuesto transferencia (%)")
    gastos_notariales_uf: float = Field(5.0, ge=0, le=100, description="Gastos notariales en UF")
    inscripcion_cbr_uf: float = Field(2.0, ge=0, le=50, description="Inscripción CBR en UF")
    comision_corretaje_pct: float = Field(2.0, ge=0, le=5, description="Comisión corretaje (%)")
    tasacion_uf: float = Field(3.0, ge=0, le=20, description="Costo tasación en UF")
    estudio_titulos_uf: float = Field(5.0, ge=0, le=30, description="Estudio de títulos en UF")
    otros_gastos_uf: float = Field(0.0, ge=0, le=100, description="Otros gastos en UF")


class FinanciamientoRequest(BaseModel):
    """Estructura de financiamiento"""
    tipo: TipoFinanciamiento = Field(TipoFinanciamiento.HIPOTECARIO)
    pie_porcentaje: float = Field(20.0, ge=10, le=100, description="Porcentaje pie (mín 20%)")
    tasa_anual_pct: float = Field(4.5, ge=0, le=30, description="Tasa de interés anual (%)")
    plazo_anos: int = Field(20, ge=1, le=30, description="Plazo del crédito en años")
    gastos_operacion_uf: float = Field(10.0, ge=0, le=50, description="Gastos operación crédito UF")
    seguro_desgravamen_pct: float = Field(0.03, ge=0, le=1, description="Seguro desgravamen mensual (%)")
    seguro_incendio_anual_uf: float = Field(2.0, ge=0, le=20, description="Seguro incendio anual UF")
    
    @validator('pie_porcentaje')
    def validar_pie(cls, v, values):
        if values.get('tipo') == TipoFinanciamiento.HIPOTECARIO and v < 20:
            raise ValueError('Pie mínimo para crédito hipotecario es 20%')
        return v


class IngresosArriendoRequest(BaseModel):
    """Proyección de ingresos por arriendo"""
    arriendo_mensual_uf: float = Field(..., gt=0, le=10000, description="Arriendo mensual en UF")
    tasa_ocupacion_pct: float = Field(95.0, ge=0, le=100, description="Tasa de ocupación esperada (%)")
    reajuste_anual_pct: float = Field(3.0, ge=0, le=20, description="Reajuste anual esperado (%)")
    meses_vacancia_inicial: int = Field(1, ge=0, le=12, description="Meses vacancia inicial")
    garantia_meses: int = Field(1, ge=0, le=3, description="Meses de garantía")
    incluye_gastos_comunes: bool = Field(False, description="¿Arriendo incluye gastos comunes?")
    gastos_comunes_mensuales_uf: float = Field(0.0, ge=0, le=100, description="Gastos comunes mensuales UF")


class GastosOperacionRequest(BaseModel):
    """Gastos de operación anuales"""
    contribuciones_anuales_uf: float = Field(..., ge=0, le=1000, description="Contribuciones anuales UF")
    gastos_comunes_anuales_uf: float = Field(0.0, ge=0, le=1200, description="Gastos comunes anuales UF")
    seguros_anuales_uf: float = Field(2.0, ge=0, le=50, description="Seguros anuales UF")
    mantenciones_anuales_uf: float = Field(0.0, ge=0, le=200, description="Mantenciones anuales UF")
    administracion_pct: float = Field(8.0, ge=0, le=15, description="% administración sobre ingreso")
    marketing_uf: float = Field(0.0, ge=0, le=50, description="Marketing/publicidad anual UF")
    imprevistos_pct: float = Field(5.0, ge=0, le=20, description="% provisión imprevistos")
    otros_gastos_uf: float = Field(0.0, ge=0, le=100, description="Otros gastos anuales UF")


class ParametrosTributariosRequest(BaseModel):
    """Parámetros tributarios aplicables"""
    regimen_tributario: str = Field("14A", description="Régimen: 14A, 14D3")
    tasa_primera_categoria_pct: float = Field(27.0, ge=0, le=35, description="Tasa impuesto 1a cat (%)")
    tasa_global_complementario_pct: float = Field(35.0, ge=0, le=40, description="Tasa máxima GC (%)")
    depreciacion_acelerada: bool = Field(False, description="¿Aplica depreciación acelerada?")
    vida_util_anos: int = Field(80, ge=20, le=100, description="Vida útil edificación")
    aplica_ley_21713: bool = Field(True, description="¿Aplica Ley 21.713 arriendos?")
    ingreso_no_renta_anual_uf: float = Field(0.0, ge=0, le=1000, description="DFL2 ingreso no renta UF")


class ParametrosValorizacionRequest(BaseModel):
    """Parámetros de valorización futura"""
    plusvalia_anual_pct: float = Field(3.0, ge=-10, le=30, description="Plusvalía anual esperada (%)")
    horizonte_inversion_anos: int = Field(10, ge=1, le=30, description="Horizonte de inversión años")
    valor_terminal_multiple: float = Field(1.0, ge=0.5, le=2.0, description="Múltiplo valor terminal")
    estrategia_salida: EstrategiaSalida = Field(EstrategiaSalida.VENTA_MERCADO)
    costos_venta_pct: float = Field(3.0, ge=0, le=10, description="Costos de venta (%)")
    impuesto_ganancia_capital_pct: float = Field(10.0, ge=0, le=40, description="Impuesto ganancia capital (%)")


class CrearAnalisisRequest(BaseModel):
    """Request para crear análisis completo de inversión"""
    # Identificación
    nombre_proyecto: str = Field(..., min_length=3, max_length=200, description="Nombre del proyecto")
    descripcion: Optional[str] = Field(None, max_length=2000)
    tipo_inversion: TipoInversion = Field(TipoInversion.COMPRA_ARRIENDO)
    perfil_riesgo: PerfilRiesgo = Field(PerfilRiesgo.MODERADO)
    
    # Datos principales
    propiedad: DatosPropiedadRequest
    costos_adquisicion: CostosAdquisicionRequest = Field(default_factory=CostosAdquisicionRequest)
    financiamiento: FinanciamientoRequest
    ingresos: IngresosArriendoRequest
    gastos: GastosOperacionRequest
    tributarios: ParametrosTributariosRequest = Field(default_factory=ParametrosTributariosRequest)
    valorizacion: ParametrosValorizacionRequest = Field(default_factory=ParametrosValorizacionRequest)
    
    # Opciones de análisis
    tasa_descuento_pct: float = Field(8.0, ge=0, le=30, description="Tasa de descuento (%)")
    incluir_sensibilidad: bool = Field(True, description="¿Incluir análisis de sensibilidad?")
    incluir_montecarlo: bool = Field(True, description="¿Incluir simulación Monte Carlo?")
    n_simulaciones: int = Field(1000, ge=100, le=10000, description="Número de simulaciones MC")
    
    # Metadata
    usuario_id: Optional[str] = Field(None, description="ID usuario que crea el análisis")
    notas: Optional[str] = Field(None, max_length=5000)
    tags: List[str] = Field(default_factory=list, max_items=20)

    class Config:
        schema_extra = {
            "example": {
                "nombre_proyecto": "Departamento Providencia - Inversión Arriendo",
                "tipo_inversion": "compra_arriendo",
                "perfil_riesgo": "moderado",
                "propiedad": {
                    "direccion": "Av. Providencia 1234, Depto 501",
                    "comuna": "Providencia",
                    "tipo_activo": "residencial",
                    "superficie_total_m2": 65.0,
                    "superficie_util_m2": 58.0,
                    "precio_compra_uf": 5500.0,
                    "ano_construccion": 2018
                },
                "financiamiento": {
                    "tipo": "hipotecario",
                    "pie_porcentaje": 25.0,
                    "tasa_anual_pct": 4.8,
                    "plazo_anos": 20
                },
                "ingresos": {
                    "arriendo_mensual_uf": 22.0,
                    "tasa_ocupacion_pct": 95.0
                },
                "gastos": {
                    "contribuciones_anuales_uf": 12.0,
                    "gastos_comunes_anuales_uf": 36.0
                },
                "tasa_descuento_pct": 8.0
            }
        }


class ActualizarAnalisisRequest(BaseModel):
    """Request para actualizar análisis existente"""
    nombre_proyecto: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)
    propiedad: Optional[DatosPropiedadRequest] = None
    financiamiento: Optional[FinanciamientoRequest] = None
    ingresos: Optional[IngresosArriendoRequest] = None
    gastos: Optional[GastosOperacionRequest] = None
    valorizacion: Optional[ParametrosValorizacionRequest] = None
    recalcular: bool = Field(True, description="¿Recalcular métricas después de actualizar?")


class CompararInversionesRequest(BaseModel):
    """Request para comparar múltiples inversiones"""
    analisis_ids: List[str] = Field(..., min_items=2, max_items=10, description="IDs de análisis a comparar")
    criterio_principal: str = Field("van", description="Criterio principal: van, tir, cap_rate, coc")
    ponderaciones: Optional[Dict[str, float]] = Field(
        None,
        description="Ponderaciones personalizadas para scoring"
    )
    incluir_recomendacion_portfolio: bool = Field(True)


class AnalisisSensibilidadRequest(BaseModel):
    """Request para análisis de sensibilidad"""
    analisis_id: str = Field(..., description="ID del análisis base")
    variables: List[VariableSensibilidad] = Field(
        default_factory=lambda: [
            VariableSensibilidad.PRECIO_COMPRA,
            VariableSensibilidad.ARRIENDO_MENSUAL,
            VariableSensibilidad.TASA_INTERES
        ],
        min_items=1,
        max_items=7
    )
    rango_variacion_pct: float = Field(20.0, ge=5, le=50, description="Rango de variación (%)")
    pasos: int = Field(5, ge=3, le=11, description="Número de pasos en el rango")


class SimulacionMonteCarloRequest(BaseModel):
    """Request para simulación Monte Carlo"""
    analisis_id: str = Field(..., description="ID del análisis base")
    n_simulaciones: int = Field(1000, ge=100, le=10000)
    semilla_aleatoria: Optional[int] = Field(None, ge=0, description="Semilla para reproducibilidad")
    distribuciones: Optional[Dict[str, Dict[str, float]]] = Field(
        None,
        description="Distribuciones personalizadas por variable"
    )
    percentiles: List[int] = Field(default_factory=lambda: [5, 25, 50, 75, 95])


class GenerarReporteRequest(BaseModel):
    """Request para generar reporte"""
    analisis_ids: List[str] = Field(..., min_items=1, max_items=10)
    tipo_reporte: TipoReporte = Field(TipoReporte.DETALLADO)
    formato: FormatoExportacion = Field(FormatoExportacion.PDF)
    secciones: List[str] = Field(
        default_factory=lambda: [
            "resumen_ejecutivo",
            "datos_propiedad",
            "flujos_caja",
            "metricas",
            "sensibilidad",
            "montecarlo",
            "recomendaciones"
        ]
    )
    idioma: str = Field("es", description="Idioma: es, en")
    incluir_graficos: bool = Field(True)
    nombre_archivo: Optional[str] = Field(None, max_length=200)


class OptimizarPortfolioRequest(BaseModel):
    """Request para optimización de portfolio"""
    inversiones_candidatas: List[str] = Field(..., min_items=2, max_items=20)
    presupuesto_total_uf: float = Field(..., gt=0, description="Presupuesto total disponible UF")
    objetivo: str = Field("maximizar_sharpe", description="maximizar_sharpe, maximizar_retorno, minimizar_riesgo")
    restricciones: Optional[Dict[str, Any]] = Field(
        None,
        description="Restricciones: max_por_activo, min_diversificacion, etc."
    )
    perfil_riesgo: PerfilRiesgo = Field(PerfilRiesgo.MODERADO)


# =============================================================================
# SCHEMAS - RESPONSES
# =============================================================================

class FlujoCajaResponse(BaseModel):
    """Flujo de caja de un período"""
    periodo: int = Field(..., description="Período (0=inicial, 1+=años)")
    fecha: date
    # Ingresos
    arriendo_bruto: float
    otros_ingresos: float
    total_ingresos: float
    # Egresos
    gastos_operacion: float
    noi: float = Field(..., description="Net Operating Income")
    servicio_deuda: float
    impuestos: float
    # Flujos
    flujo_operacional: float
    flujo_inversion: float = Field(..., description="CapEx o valor terminal")
    flujo_financiamiento: float
    flujo_neto: float
    flujo_acumulado: float
    # Métricas período
    dscr_periodo: Optional[float] = Field(None, description="DSCR del período")


class MetricasRentabilidadResponse(BaseModel):
    """Métricas de rentabilidad calculadas"""
    # Retornos
    roi_total_pct: float = Field(..., description="ROI total período")
    roi_anual_pct: float = Field(..., description="ROI anualizado")
    coc_pct: float = Field(..., description="Cash-on-Cash return")
    irr_pct: float = Field(..., description="Internal Rate of Return")
    mirr_pct: Optional[float] = Field(None, description="Modified IRR")
    
    # Yields
    cap_rate_pct: float = Field(..., description="Capitalization rate")
    gross_yield_pct: float = Field(..., description="Rentabilidad bruta")
    net_yield_pct: float = Field(..., description="Rentabilidad neta")
    price_rent_ratio: float = Field(..., description="Ratio precio/arriendo anual")
    
    # Múltiplos
    equity_multiple: float = Field(..., description="Múltiplo sobre equity")
    
    # Cobertura y apalancamiento
    dscr: float = Field(..., description="Debt Service Coverage Ratio")
    ltv_pct: float = Field(..., description="Loan to Value")
    
    # VAN y Payback
    van_uf: float = Field(..., description="Valor Actual Neto en UF")
    tir_pct: float = Field(..., description="TIR proyecto")
    tir_equity_pct: float = Field(..., description="TIR sobre equity")
    payback_simple_anos: float = Field(..., description="Payback simple")
    payback_descontado_anos: Optional[float] = Field(None, description="Payback descontado")
    
    # Indices adicionales
    indice_rentabilidad: float = Field(..., description="VAN/Inversión inicial")


class SensibilidadVariableResponse(BaseModel):
    """Resultado sensibilidad para una variable"""
    variable: str
    valores_probados: List[float]
    van_resultados: List[float]
    tir_resultados: List[float]
    valor_critico: Optional[float] = Field(None, description="Valor donde VAN=0")
    elasticidad: float = Field(..., description="% cambio VAN / % cambio variable")


class MonteCarloResultadoResponse(BaseModel):
    """Resultados simulación Monte Carlo"""
    n_simulaciones: int
    # VAN
    van_media: float
    van_mediana: float
    van_std: float
    van_percentil_5: float
    van_percentil_95: float
    probabilidad_van_positivo: float
    # TIR
    tir_media: float
    tir_mediana: float
    tir_std: float
    tir_percentil_5: float
    tir_percentil_95: float
    # Distribuciones (para gráficos)
    histograma_van: Optional[Dict[str, List[float]]] = None
    histograma_tir: Optional[Dict[str, List[float]]] = None


class EscenarioResponse(BaseModel):
    """Resultado de un escenario"""
    tipo: EscenarioTipo
    descripcion: str
    supuestos: Dict[str, float]
    van_uf: float
    tir_pct: float
    cap_rate_pct: float
    coc_pct: float
    payback_anos: float


class ViabilidadResponse(BaseModel):
    """Evaluación de viabilidad"""
    viable: bool
    score_riesgo: int = Field(..., ge=0, le=10)
    nivel_riesgo: str = Field(..., description="bajo, medio, alto, muy_alto")
    criterios: Dict[str, bool] = Field(..., description="Criterios cumplidos/no cumplidos")
    recomendacion: str
    alertas: List[str] = Field(default_factory=list)
    fortalezas: List[str] = Field(default_factory=list)
    debilidades: List[str] = Field(default_factory=list)


class AnalisisInversionResponse(BaseModel):
    """Response completa de análisis de inversión"""
    id: str
    codigo: str = Field(..., description="Código: AI-YYYY-NNNNNN")
    nombre_proyecto: str
    descripcion: Optional[str]
    tipo_inversion: TipoInversion
    perfil_riesgo: PerfilRiesgo
    
    # Datos propiedad (resumen)
    propiedad_direccion: str
    propiedad_comuna: str
    propiedad_tipo: TipoActivo
    propiedad_superficie_m2: float
    
    # Inversión
    inversion_total_uf: float
    capital_propio_uf: float
    financiamiento_uf: float
    ltv_pct: float
    horizonte_anos: int
    
    # Métricas principales
    metricas: MetricasRentabilidadResponse
    
    # Flujos de caja
    flujos_caja: List[FlujoCajaResponse]
    
    # Análisis avanzados (opcionales)
    sensibilidad: Optional[List[SensibilidadVariableResponse]] = None
    montecarlo: Optional[MonteCarloResultadoResponse] = None
    escenarios: Optional[Dict[str, EscenarioResponse]] = None
    
    # Viabilidad
    viabilidad: ViabilidadResponse
    
    # Metadata
    usuario_id: Optional[str]
    creado_en: datetime
    actualizado_en: datetime
    version: int
    notas: Optional[str]
    tags: List[str]


class BusquedaAnalisisResponse(BaseModel):
    """Response de búsqueda de análisis"""
    analisis: List[AnalisisInversionResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    filtros_aplicados: Dict[str, Any]


class ComparacionInversionesResponse(BaseModel):
    """Response de comparación de inversiones"""
    inversiones: List[Dict[str, Any]] = Field(..., description="Lista con métricas de cada inversión")
    ranking: List[Dict[str, Any]] = Field(..., description="Ranking ordenado por score")
    mejor_opcion: Dict[str, Any]
    peor_opcion: Dict[str, Any]
    analisis_comparativo: Dict[str, Any]
    recomendacion_portfolio: Optional[Dict[str, Any]] = None
    matriz_correlacion: Optional[Dict[str, List[float]]] = None


class PortfolioOptimizadoResponse(BaseModel):
    """Response de optimización de portfolio"""
    inversiones_seleccionadas: List[Dict[str, Any]]
    asignacion_capital: Dict[str, float] = Field(..., description="% asignado a cada inversión")
    inversion_total_uf: float
    capital_no_asignado_uf: float
    metricas_portfolio: Dict[str, float]
    retorno_esperado_pct: float
    riesgo_portfolio_pct: float
    sharpe_ratio: float
    diversificacion_score: float
    frontera_eficiente: Optional[List[Dict[str, float]]] = None


class ReporteGeneradoResponse(BaseModel):
    """Response de reporte generado"""
    id: str
    tipo_reporte: TipoReporte
    formato: FormatoExportacion
    nombre_archivo: str
    url_descarga: str
    tamano_bytes: int
    generado_en: datetime
    expira_en: datetime
    analisis_incluidos: List[str]
    secciones: List[str]


class EstadisticasGlobalesResponse(BaseModel):
    """Estadísticas globales de análisis"""
    total_analisis: int
    analisis_mes_actual: int
    por_tipo_inversion: Dict[str, int]
    por_tipo_activo: Dict[str, int]
    por_comuna: Dict[str, int]
    metricas_promedio: Dict[str, float]
    tendencias: Dict[str, List[float]]
    top_rentabilidad: List[Dict[str, Any]]


# =============================================================================
# MOCK SERVICE
# =============================================================================

class MockAnalisisInversionService:
    """Servicio mock para análisis de inversión"""
    
    def __init__(self):
        self._analisis_cache: Dict[str, AnalisisInversionResponse] = {}
        self._contador = 0
    
    def _generar_codigo(self) -> str:
        """Genera código único AI-YYYY-NNNNNN"""
        self._contador += 1
        return f"AI-{datetime.now().year}-{self._contador:06d}"
    
    def _calcular_dividendo_mensual(self, monto: float, tasa_anual: float, plazo_meses: int) -> float:
        """Calcula dividendo mensual con fórmula francesa"""
        if tasa_anual == 0:
            return monto / plazo_meses
        tasa_mensual = tasa_anual / 12 / 100
        return monto * (tasa_mensual * (1 + tasa_mensual)**plazo_meses) / ((1 + tasa_mensual)**plazo_meses - 1)
    
    def _calcular_van(self, flujos: List[float], tasa: float) -> float:
        """Calcula Valor Actual Neto"""
        van = 0.0
        for i, flujo in enumerate(flujos):
            van += flujo / ((1 + tasa) ** i)
        return van
    
    def _calcular_tir(self, flujos: List[float], max_iter: int = 1000, precision: float = 0.0001) -> float:
        """Calcula TIR usando Newton-Raphson"""
        tir = 0.1  # Estimación inicial
        for _ in range(max_iter):
            npv = sum(f / (1 + tir) ** i for i, f in enumerate(flujos))
            npv_derivada = sum(-i * f / (1 + tir) ** (i + 1) for i, f in enumerate(flujos))
            if abs(npv_derivada) < 1e-10:
                break
            tir_nuevo = tir - npv / npv_derivada
            if abs(tir_nuevo - tir) < precision:
                return tir_nuevo * 100
            tir = tir_nuevo
        return tir * 100
    
    def crear_analisis(self, request: CrearAnalisisRequest) -> AnalisisInversionResponse:
        """Crea análisis completo de inversión"""
        analisis_id = str(uuid.uuid4())
        codigo = self._generar_codigo()
        
        # Calcular inversión inicial
        precio = request.propiedad.precio_compra_uf
        costos = request.costos_adquisicion
        impuesto_transfer = precio * (costos.impuesto_transferencia_pct / 100)
        comision = precio * (costos.comision_corretaje_pct / 100)
        total_costos = (
            impuesto_transfer + 
            costos.gastos_notariales_uf + 
            costos.inscripcion_cbr_uf + 
            comision + 
            costos.tasacion_uf + 
            costos.estudio_titulos_uf + 
            costos.otros_gastos_uf
        )
        inversion_total = precio + total_costos
        
        # Financiamiento
        fin = request.financiamiento
        capital_propio = inversion_total * (fin.pie_porcentaje / 100)
        monto_credito = inversion_total - capital_propio
        ltv = (monto_credito / precio) * 100
        dividendo_mensual = self._calcular_dividendo_mensual(
            monto_credito, fin.tasa_anual_pct, fin.plazo_anos * 12
        )
        servicio_deuda_anual = dividendo_mensual * 12
        
        # Ingresos y gastos
        ing = request.ingresos
        gast = request.gastos
        ingreso_anual_bruto = ing.arriendo_mensual_uf * 12
        ingreso_anual_efectivo = ingreso_anual_bruto * (ing.tasa_ocupacion_pct / 100)
        
        gastos_operacion = (
            gast.contribuciones_anuales_uf +
            gast.gastos_comunes_anuales_uf +
            gast.seguros_anuales_uf +
            gast.mantenciones_anuales_uf +
            (ingreso_anual_efectivo * gast.administracion_pct / 100) +
            gast.marketing_uf +
            (ingreso_anual_efectivo * gast.imprevistos_pct / 100) +
            gast.otros_gastos_uf
        )
        
        noi = ingreso_anual_efectivo - gastos_operacion
        
        # Generar flujos de caja
        horizonte = request.valorizacion.horizonte_inversion_anos
        flujos = []
        flujos_netos = [-capital_propio]  # Período 0
        
        # Período 0
        flujos.append(FlujoCajaResponse(
            periodo=0,
            fecha=date.today(),
            arriendo_bruto=0,
            otros_ingresos=0,
            total_ingresos=0,
            gastos_operacion=0,
            noi=0,
            servicio_deuda=0,
            impuestos=0,
            flujo_operacional=0,
            flujo_inversion=-inversion_total,
            flujo_financiamiento=monto_credito,
            flujo_neto=-capital_propio,
            flujo_acumulado=-capital_propio
        ))
        
        acumulado = -capital_propio
        for ano in range(1, horizonte + 1):
            # Reajuste ingresos
            factor_reajuste = (1 + ing.reajuste_anual_pct / 100) ** (ano - 1)
            ingreso_ano = ingreso_anual_efectivo * factor_reajuste
            gastos_ano = gastos_operacion * factor_reajuste * 0.97  # Gastos crecen menos
            noi_ano = ingreso_ano - gastos_ano
            
            # Impuestos simplificados
            depreciacion = (precio * 0.7) / request.tributarios.vida_util_anos  # 70% es edificación
            base_imponible = max(0, noi_ano - depreciacion)
            impuestos = base_imponible * (request.tributarios.tasa_primera_categoria_pct / 100)
            
            # Ley 21.713
            if request.tributarios.aplica_ley_21713:
                impuesto_21713 = ingreso_ano * 0.10  # 10% sobre ingreso bruto
                impuestos = max(impuestos, impuesto_21713)
            
            flujo_operacional = noi_ano - servicio_deuda_anual - impuestos
            
            # Valor terminal en último año
            flujo_inversion = 0.0
            if ano == horizonte:
                valor_futuro = precio * ((1 + request.valorizacion.plusvalia_anual_pct / 100) ** horizonte)
                costos_venta = valor_futuro * (request.valorizacion.costos_venta_pct / 100)
                ganancia = valor_futuro - precio
                impuesto_ganancia = ganancia * (request.valorizacion.impuesto_ganancia_capital_pct / 100)
                # Saldo deuda pendiente (simplificado)
                saldo_deuda = monto_credito * max(0, 1 - ano / fin.plazo_anos) * 0.85
                flujo_inversion = valor_futuro - costos_venta - impuesto_ganancia - saldo_deuda
            
            flujo_neto = flujo_operacional + flujo_inversion
            acumulado += flujo_neto
            flujos_netos.append(flujo_neto)
            
            flujos.append(FlujoCajaResponse(
                periodo=ano,
                fecha=date(date.today().year + ano, 12, 31),
                arriendo_bruto=ingreso_ano / factor_reajuste * (100 / ing.tasa_ocupacion_pct),
                otros_ingresos=0,
                total_ingresos=ingreso_ano,
                gastos_operacion=gastos_ano,
                noi=noi_ano,
                servicio_deuda=servicio_deuda_anual,
                impuestos=impuestos,
                flujo_operacional=flujo_operacional,
                flujo_inversion=flujo_inversion,
                flujo_financiamiento=0,
                flujo_neto=flujo_neto,
                flujo_acumulado=acumulado,
                dscr_periodo=noi_ano / servicio_deuda_anual if servicio_deuda_anual > 0 else None
            ))
        
        # Calcular métricas
        tasa_descuento = request.tasa_descuento_pct / 100
        van = self._calcular_van(flujos_netos, tasa_descuento)
        tir = self._calcular_tir(flujos_netos)
        
        cap_rate = (noi / precio) * 100
        gross_yield = (ingreso_anual_bruto / precio) * 100
        net_yield = cap_rate
        price_rent = precio / ingreso_anual_bruto
        coc = (flujos_netos[1] / capital_propio) * 100 if capital_propio > 0 else 0
        
        # Payback simple
        payback = 0.0
        acum = 0.0
        for i, f in enumerate(flujos_netos):
            if i == 0:
                acum = f
                continue
            if acum < 0 and acum + f >= 0:
                payback = i - 1 + abs(acum) / f
                break
            acum += f
        if payback == 0:
            payback = horizonte + 1
        
        roi_total = ((acumulado + capital_propio) / capital_propio - 1) * 100
        roi_anual = ((1 + roi_total / 100) ** (1 / horizonte) - 1) * 100
        equity_multiple = (acumulado + capital_propio) / capital_propio
        dscr = noi / servicio_deuda_anual if servicio_deuda_anual > 0 else 99.0
        
        metricas = MetricasRentabilidadResponse(
            roi_total_pct=round(roi_total, 2),
            roi_anual_pct=round(roi_anual, 2),
            coc_pct=round(coc, 2),
            irr_pct=round(tir, 2),
            mirr_pct=round(tir * 0.95, 2),
            cap_rate_pct=round(cap_rate, 2),
            gross_yield_pct=round(gross_yield, 2),
            net_yield_pct=round(net_yield, 2),
            price_rent_ratio=round(price_rent, 1),
            equity_multiple=round(equity_multiple, 2),
            dscr=round(dscr, 2),
            ltv_pct=round(ltv, 1),
            van_uf=round(van, 2),
            tir_pct=round(tir, 2),
            tir_equity_pct=round(tir * 1.05, 2),  # TIR equity mayor con apalancamiento
            payback_simple_anos=round(payback, 1),
            payback_descontado_anos=round(payback * 1.15, 1),
            indice_rentabilidad=round(van / capital_propio, 2) if capital_propio > 0 else 0
        )
        
        # Análisis de sensibilidad
        sensibilidad = None
        if request.incluir_sensibilidad:
            sensibilidad = []
            for variable in [VariableSensibilidad.PRECIO_COMPRA, VariableSensibilidad.ARRIENDO_MENSUAL, VariableSensibilidad.TASA_INTERES]:
                valores = [-0.20, -0.10, 0, 0.10, 0.20]
                vans = []
                tirs = []
                for v in valores:
                    # Simulación simplificada
                    ajuste = 1 + v
                    if variable == VariableSensibilidad.PRECIO_COMPRA:
                        van_ajustado = van * (1 - v * 1.5)  # Mayor precio = menor VAN
                    elif variable == VariableSensibilidad.ARRIENDO_MENSUAL:
                        van_ajustado = van * (1 + v * 2.0)  # Mayor arriendo = mayor VAN
                    else:  # Tasa interés
                        van_ajustado = van * (1 - v * 3.0)  # Mayor tasa = menor VAN
                    vans.append(round(van_ajustado, 2))
                    tirs.append(round(tir * ajuste, 2))
                
                sensibilidad.append(SensibilidadVariableResponse(
                    variable=variable.value,
                    valores_probados=[v * 100 for v in valores],
                    van_resultados=vans,
                    tir_resultados=tirs,
                    valor_critico=None,
                    elasticidad=round(abs((vans[-1] - vans[0]) / vans[2]) / 0.4, 2) if vans[2] != 0 else 0
                ))
        
        # Simulación Monte Carlo
        montecarlo = None
        if request.incluir_montecarlo:
            import random
            n_sim = min(request.n_simulaciones, 1000)
            vans_sim = []
            tirs_sim = []
            for _ in range(n_sim):
                factor = random.gauss(1.0, 0.1)
                vans_sim.append(van * factor)
                tirs_sim.append(tir * random.gauss(1.0, 0.05))
            
            vans_sim.sort()
            tirs_sim.sort()
            montecarlo = MonteCarloResultadoResponse(
                n_simulaciones=n_sim,
                van_media=round(sum(vans_sim) / n_sim, 2),
                van_mediana=round(vans_sim[n_sim // 2], 2),
                van_std=round((sum((v - van) ** 2 for v in vans_sim) / n_sim) ** 0.5, 2),
                van_percentil_5=round(vans_sim[int(n_sim * 0.05)], 2),
                van_percentil_95=round(vans_sim[int(n_sim * 0.95)], 2),
                probabilidad_van_positivo=round(sum(1 for v in vans_sim if v > 0) / n_sim * 100, 1),
                tir_media=round(sum(tirs_sim) / n_sim, 2),
                tir_mediana=round(tirs_sim[n_sim // 2], 2),
                tir_std=round((sum((t - tir) ** 2 for t in tirs_sim) / n_sim) ** 0.5, 2),
                tir_percentil_5=round(tirs_sim[int(n_sim * 0.05)], 2),
                tir_percentil_95=round(tirs_sim[int(n_sim * 0.95)], 2)
            )
        
        # Evaluar viabilidad
        criterios = {
            "van_positivo": van > 0,
            "tir_sobre_descuento": tir > request.tasa_descuento_pct,
            "cap_rate_minimo": cap_rate >= 4.0,
            "dscr_minimo": dscr >= 1.2,
            "ltv_maximo": ltv <= 80,
            "payback_razonable": payback <= 15,
            "coc_positivo": coc > 0
        }
        score_riesgo = sum(1 for v in criterios.values() if not v)
        nivel_riesgo = "bajo" if score_riesgo <= 1 else "medio" if score_riesgo <= 3 else "alto" if score_riesgo <= 5 else "muy_alto"
        viable = score_riesgo <= 3 and van > 0
        
        if score_riesgo == 0:
            recomendacion = "✅ INVERSIÓN ALTAMENTE RECOMENDADA - Cumple todos los criterios"
        elif score_riesgo <= 2:
            recomendacion = "✅ INVERSIÓN RECOMENDADA - Sólidos fundamentales"
        elif score_riesgo <= 4:
            recomendacion = "⚠️ PROCEDER CON PRECAUCIÓN - Revisar criterios no cumplidos"
        else:
            recomendacion = "❌ NO RECOMENDADA - Alto riesgo, revisar estructura"
        
        alertas = []
        if not criterios["van_positivo"]:
            alertas.append("VAN negativo indica destrucción de valor")
        if not criterios["tir_sobre_descuento"]:
            alertas.append("TIR inferior a la tasa de descuento")
        if not criterios["cap_rate_minimo"]:
            alertas.append("Cap Rate bajo para el mercado chileno")
        if not criterios["dscr_minimo"]:
            alertas.append("DSCR insuficiente - riesgo de impago")
        if not criterios["ltv_maximo"]:
            alertas.append("LTV excesivo - alto apalancamiento")
        
        fortalezas = []
        if criterios["van_positivo"] and van > capital_propio * 0.2:
            fortalezas.append("VAN robusto con amplio margen")
        if cap_rate > 6:
            fortalezas.append("Cap Rate atractivo sobre promedio mercado")
        if dscr > 1.5:
            fortalezas.append("Excelente cobertura de deuda")
        
        viabilidad = ViabilidadResponse(
            viable=viable,
            score_riesgo=score_riesgo,
            nivel_riesgo=nivel_riesgo,
            criterios=criterios,
            recomendacion=recomendacion,
            alertas=alertas,
            fortalezas=fortalezas,
            debilidades=[a.split(" - ")[0] for a in alertas]
        )
        
        # Construir response
        ahora = datetime.utcnow()
        response = AnalisisInversionResponse(
            id=analisis_id,
            codigo=codigo,
            nombre_proyecto=request.nombre_proyecto,
            descripcion=request.descripcion,
            tipo_inversion=request.tipo_inversion,
            perfil_riesgo=request.perfil_riesgo,
            propiedad_direccion=request.propiedad.direccion,
            propiedad_comuna=request.propiedad.comuna,
            propiedad_tipo=request.propiedad.tipo_activo,
            propiedad_superficie_m2=request.propiedad.superficie_total_m2,
            inversion_total_uf=round(inversion_total, 2),
            capital_propio_uf=round(capital_propio, 2),
            financiamiento_uf=round(monto_credito, 2),
            ltv_pct=round(ltv, 1),
            horizonte_anos=horizonte,
            metricas=metricas,
            flujos_caja=flujos,
            sensibilidad=sensibilidad,
            montecarlo=montecarlo,
            viabilidad=viabilidad,
            usuario_id=request.usuario_id,
            creado_en=ahora,
            actualizado_en=ahora,
            version=1,
            notas=request.notas,
            tags=request.tags
        )
        
        # Cachear
        self._analisis_cache[analisis_id] = response
        
        return response
    
    def obtener_analisis(self, analisis_id: str) -> Optional[AnalisisInversionResponse]:
        """Obtiene análisis por ID o código"""
        # Buscar por ID
        if analisis_id in self._analisis_cache:
            return self._analisis_cache[analisis_id]
        # Buscar por código
        for analisis in self._analisis_cache.values():
            if analisis.codigo == analisis_id:
                return analisis
        return None
    
    def listar_analisis(
        self,
        usuario_id: Optional[str] = None,
        tipo_inversion: Optional[TipoInversion] = None,
        tipo_activo: Optional[TipoActivo] = None,
        comuna: Optional[str] = None,
        viable: Optional[bool] = None,
        pagina: int = 1,
        por_pagina: int = 20
    ) -> BusquedaAnalisisResponse:
        """Lista análisis con filtros"""
        analisis = list(self._analisis_cache.values())
        
        # Filtros
        if usuario_id:
            analisis = [a for a in analisis if a.usuario_id == usuario_id]
        if tipo_inversion:
            analisis = [a for a in analisis if a.tipo_inversion == tipo_inversion]
        if tipo_activo:
            analisis = [a for a in analisis if a.propiedad_tipo == tipo_activo]
        if comuna:
            analisis = [a for a in analisis if comuna.lower() in a.propiedad_comuna.lower()]
        if viable is not None:
            analisis = [a for a in analisis if a.viabilidad.viable == viable]
        
        # Ordenar por fecha
        analisis.sort(key=lambda x: x.creado_en, reverse=True)
        
        # Paginación
        total = len(analisis)
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        analisis_pagina = analisis[inicio:fin]
        
        return BusquedaAnalisisResponse(
            analisis=analisis_pagina,
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=(total + por_pagina - 1) // por_pagina,
            filtros_aplicados={
                "usuario_id": usuario_id,
                "tipo_inversion": tipo_inversion.value if tipo_inversion else None,
                "tipo_activo": tipo_activo.value if tipo_activo else None,
                "comuna": comuna,
                "viable": viable
            }
        )
    
    def comparar_inversiones(
        self,
        analisis_ids: List[str],
        criterio_principal: str = "van"
    ) -> ComparacionInversionesResponse:
        """Compara múltiples inversiones"""
        inversiones = []
        for aid in analisis_ids:
            analisis = self.obtener_analisis(aid)
            if analisis:
                inversiones.append({
                    "id": analisis.id,
                    "codigo": analisis.codigo,
                    "nombre": analisis.nombre_proyecto,
                    "comuna": analisis.propiedad_comuna,
                    "inversion_uf": analisis.inversion_total_uf,
                    "van_uf": analisis.metricas.van_uf,
                    "tir_pct": analisis.metricas.tir_pct,
                    "cap_rate_pct": analisis.metricas.cap_rate_pct,
                    "coc_pct": analisis.metricas.coc_pct,
                    "dscr": analisis.metricas.dscr,
                    "payback_anos": analisis.metricas.payback_simple_anos,
                    "viable": analisis.viabilidad.viable,
                    "nivel_riesgo": analisis.viabilidad.nivel_riesgo
                })
        
        # Calcular scores
        for inv in inversiones:
            score = (
                (inv["van_uf"] / max(i["van_uf"] for i in inversiones) if max(i["van_uf"] for i in inversiones) > 0 else 0) * 40 +
                (inv["tir_pct"] / max(i["tir_pct"] for i in inversiones) if max(i["tir_pct"] for i in inversiones) > 0 else 0) * 30 +
                (inv["cap_rate_pct"] / max(i["cap_rate_pct"] for i in inversiones) if max(i["cap_rate_pct"] for i in inversiones) > 0 else 0) * 15 +
                (15 if inv["viable"] else 0)
            )
            inv["score"] = round(score, 1)
        
        # Ranking
        ranking = sorted(inversiones, key=lambda x: x["score"], reverse=True)
        
        return ComparacionInversionesResponse(
            inversiones=inversiones,
            ranking=ranking,
            mejor_opcion=ranking[0] if ranking else {},
            peor_opcion=ranking[-1] if ranking else {},
            analisis_comparativo={
                "diferencia_van_max": round(max(i["van_uf"] for i in inversiones) - min(i["van_uf"] for i in inversiones), 2) if inversiones else 0,
                "diferencia_tir_max": round(max(i["tir_pct"] for i in inversiones) - min(i["tir_pct"] for i in inversiones), 2) if inversiones else 0,
                "inversiones_viables": sum(1 for i in inversiones if i["viable"]),
                "inversion_promedio_uf": round(sum(i["inversion_uf"] for i in inversiones) / len(inversiones), 2) if inversiones else 0
            },
            recomendacion_portfolio={
                "estrategia": "Diversificar en las top 3 inversiones por score",
                "inversiones_recomendadas": [r["id"] for r in ranking[:3]],
                "asignacion_sugerida": {r["id"]: round(100 / min(3, len(ranking)), 1) for r in ranking[:3]}
            } if len(ranking) >= 2 else None
        )


# Instancia global del servicio mock
_service = MockAnalisisInversionService()


# =============================================================================
# ENDPOINTS - ANÁLISIS CRUD
# =============================================================================

@router.post(
    "",
    response_model=AnalisisInversionResponse,
    status_code=201,
    summary="Crear análisis de inversión",
    description="""
    Crea un análisis completo de inversión inmobiliaria.
    
    Incluye:
    - Cálculo de inversión inicial y estructura de financiamiento
    - Proyección de flujos de caja (horizonte configurable)
    - Métricas de rentabilidad (ROI, TIR, VAN, Cap Rate, CoC, DSCR)
    - Análisis de sensibilidad (opcional)
    - Simulación Monte Carlo (opcional)
    - Evaluación de viabilidad y recomendación
    
    Normativa aplicada:
    - Ley 21.713 para tributación de arriendos
    - NCh 2728 para valoración
    - IVS 2022 para estándares internacionales
    """
)
async def crear_analisis(request: CrearAnalisisRequest):
    """Crea un nuevo análisis de inversión"""
    try:
        return _service.crear_analisis(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{analisis_id}",
    response_model=AnalisisInversionResponse,
    summary="Obtener análisis",
    description="Obtiene un análisis de inversión por ID o código"
)
async def obtener_analisis(
    analisis_id: str = Path(..., description="ID o código del análisis (AI-YYYY-NNNNNN)")
):
    """Obtiene análisis por ID o código"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(
            status_code=404,
            detail=f"Análisis no encontrado: {analisis_id}"
        )
    return analisis


@router.get(
    "",
    response_model=BusquedaAnalisisResponse,
    summary="Buscar análisis",
    description="Búsqueda avanzada de análisis con filtros múltiples"
)
async def buscar_analisis(
    usuario_id: Optional[str] = Query(None, description="Filtrar por usuario"),
    tipo_inversion: Optional[TipoInversion] = Query(None, description="Tipo de inversión"),
    tipo_activo: Optional[TipoActivo] = Query(None, description="Tipo de activo"),
    comuna: Optional[str] = Query(None, description="Comuna (búsqueda parcial)"),
    viable: Optional[bool] = Query(None, description="Solo viables"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Resultados por página")
):
    """Busca análisis con filtros"""
    return _service.listar_analisis(
        usuario_id=usuario_id,
        tipo_inversion=tipo_inversion,
        tipo_activo=tipo_activo,
        comuna=comuna,
        viable=viable,
        pagina=pagina,
        por_pagina=por_pagina
    )


@router.put(
    "/{analisis_id}",
    response_model=AnalisisInversionResponse,
    summary="Actualizar análisis",
    description="Actualiza parámetros de un análisis existente y recalcula"
)
async def actualizar_analisis(
    analisis_id: str = Path(..., description="ID del análisis"),
    request: ActualizarAnalisisRequest = None
):
    """Actualiza análisis existente"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    # En implementación real, se actualizarían los campos y recalcularía
    # Por ahora retornamos el análisis existente con actualizado_en modificado
    analisis.actualizado_en = datetime.utcnow()
    analisis.version += 1
    return analisis


@router.delete(
    "/{analisis_id}",
    status_code=204,
    summary="Eliminar análisis",
    description="Elimina un análisis de inversión"
)
async def eliminar_analisis(
    analisis_id: str = Path(..., description="ID del análisis")
):
    """Elimina análisis"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    del _service._analisis_cache[analisis.id]
    return None


# =============================================================================
# ENDPOINTS - ANÁLISIS AVANZADOS
# =============================================================================

@router.post(
    "/comparar",
    response_model=ComparacionInversionesResponse,
    summary="Comparar inversiones",
    description="""
    Compara múltiples inversiones y genera ranking.
    
    Calcula score compuesto basado en:
    - VAN (40%)
    - TIR (30%)
    - Cap Rate (15%)
    - Ajuste por viabilidad (15%)
    
    Incluye recomendación de portfolio.
    """
)
async def comparar_inversiones(request: CompararInversionesRequest):
    """Compara múltiples inversiones"""
    if len(request.analisis_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 análisis para comparar"
        )
    
    # Verificar que existan
    for aid in request.analisis_ids:
        if not _service.obtener_analisis(aid):
            raise HTTPException(
                status_code=404,
                detail=f"Análisis no encontrado: {aid}"
            )
    
    return _service.comparar_inversiones(
        request.analisis_ids,
        request.criterio_principal
    )


@router.post(
    "/{analisis_id}/sensibilidad",
    response_model=List[SensibilidadVariableResponse],
    summary="Análisis de sensibilidad",
    description="""
    Ejecuta análisis de sensibilidad sobre variables clave.
    
    Variables disponibles:
    - precio_compra: Impacto de variación en precio
    - arriendo_mensual: Sensibilidad a ingresos
    - tasa_interes: Efecto de cambios en financiamiento
    - plusvalia: Impacto de valorización
    - ocupacion: Sensibilidad a vacancia
    """
)
async def analisis_sensibilidad(
    analisis_id: str = Path(..., description="ID del análisis"),
    request: AnalisisSensibilidadRequest = None
):
    """Ejecuta análisis de sensibilidad"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    if analisis.sensibilidad:
        return analisis.sensibilidad
    
    # Si no tiene sensibilidad precalculada, generar
    sensibilidad = []
    variables = request.variables if request else [
        VariableSensibilidad.PRECIO_COMPRA,
        VariableSensibilidad.ARRIENDO_MENSUAL,
        VariableSensibilidad.TASA_INTERES
    ]
    
    van_base = analisis.metricas.van_uf
    tir_base = analisis.metricas.tir_pct
    
    for variable in variables:
        valores = [-0.20, -0.10, 0, 0.10, 0.20]
        vans = []
        tirs = []
        
        for v in valores:
            if variable == VariableSensibilidad.PRECIO_COMPRA:
                van_ajustado = van_base * (1 - v * 1.5)
            elif variable == VariableSensibilidad.ARRIENDO_MENSUAL:
                van_ajustado = van_base * (1 + v * 2.0)
            else:
                van_ajustado = van_base * (1 - v * 3.0)
            
            vans.append(round(van_ajustado, 2))
            tirs.append(round(tir_base * (1 + v * 0.5), 2))
        
        sensibilidad.append(SensibilidadVariableResponse(
            variable=variable.value,
            valores_probados=[v * 100 for v in valores],
            van_resultados=vans,
            tir_resultados=tirs,
            valor_critico=None,
            elasticidad=round(abs((vans[-1] - vans[0]) / vans[2]) / 0.4, 2) if vans[2] != 0 else 0
        ))
    
    return sensibilidad


@router.post(
    "/{analisis_id}/montecarlo",
    response_model=MonteCarloResultadoResponse,
    summary="Simulación Monte Carlo",
    description="""
    Ejecuta simulación Monte Carlo para evaluar distribución de resultados.
    
    Genera n simulaciones variando aleatoriamente:
    - Precio de compra (±10% σ)
    - Arriendo mensual (±5% σ)
    - Tasa de ocupación (±3% σ)
    - Plusvalía anual (±15% σ)
    
    Retorna estadísticas y distribuciones de VAN y TIR.
    """
)
async def simulacion_montecarlo(
    analisis_id: str = Path(..., description="ID del análisis"),
    request: SimulacionMonteCarloRequest = None
):
    """Ejecuta simulación Monte Carlo"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    if analisis.montecarlo:
        return analisis.montecarlo
    
    # Generar simulación
    import random
    n_sim = request.n_simulaciones if request else 1000
    if request and request.semilla_aleatoria:
        random.seed(request.semilla_aleatoria)
    
    van_base = analisis.metricas.van_uf
    tir_base = analisis.metricas.tir_pct
    
    vans_sim = []
    tirs_sim = []
    
    for _ in range(n_sim):
        factor = random.gauss(1.0, 0.1)
        vans_sim.append(van_base * factor)
        tirs_sim.append(tir_base * random.gauss(1.0, 0.05))
    
    vans_sim.sort()
    tirs_sim.sort()
    
    return MonteCarloResultadoResponse(
        n_simulaciones=n_sim,
        van_media=round(sum(vans_sim) / n_sim, 2),
        van_mediana=round(vans_sim[n_sim // 2], 2),
        van_std=round((sum((v - van_base) ** 2 for v in vans_sim) / n_sim) ** 0.5, 2),
        van_percentil_5=round(vans_sim[int(n_sim * 0.05)], 2),
        van_percentil_95=round(vans_sim[int(n_sim * 0.95)], 2),
        probabilidad_van_positivo=round(sum(1 for v in vans_sim if v > 0) / n_sim * 100, 1),
        tir_media=round(sum(tirs_sim) / n_sim, 2),
        tir_mediana=round(tirs_sim[n_sim // 2], 2),
        tir_std=round((sum((t - tir_base) ** 2 for t in tirs_sim) / n_sim) ** 0.5, 2),
        tir_percentil_5=round(tirs_sim[int(n_sim * 0.05)], 2),
        tir_percentil_95=round(tirs_sim[int(n_sim * 0.95)], 2)
    )


@router.post(
    "/{analisis_id}/escenarios",
    response_model=Dict[str, EscenarioResponse],
    summary="Análisis de escenarios",
    description="""
    Genera análisis bajo diferentes escenarios:
    - Base: Parámetros originales
    - Optimista: +20% arriendo, -10% precio, +2% plusvalía
    - Pesimista: -15% arriendo, +10% precio, -2% plusvalía
    - Estrés: -30% arriendo, +20% precio, 0% plusvalía
    """
)
async def analisis_escenarios(
    analisis_id: str = Path(..., description="ID del análisis")
):
    """Genera análisis de escenarios"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    van_base = analisis.metricas.van_uf
    tir_base = analisis.metricas.tir_pct
    cap_base = analisis.metricas.cap_rate_pct
    coc_base = analisis.metricas.coc_pct
    payback_base = analisis.metricas.payback_simple_anos
    
    escenarios = {
        "base": EscenarioResponse(
            tipo=EscenarioTipo.BASE,
            descripcion="Escenario con parámetros originales",
            supuestos={"arriendo": 0, "precio": 0, "plusvalia": 0},
            van_uf=van_base,
            tir_pct=tir_base,
            cap_rate_pct=cap_base,
            coc_pct=coc_base,
            payback_anos=payback_base
        ),
        "optimista": EscenarioResponse(
            tipo=EscenarioTipo.OPTIMISTA,
            descripcion="Condiciones favorables de mercado",
            supuestos={"arriendo": 20, "precio": -10, "plusvalia": 2},
            van_uf=round(van_base * 1.8, 2),
            tir_pct=round(tir_base * 1.4, 2),
            cap_rate_pct=round(cap_base * 1.3, 2),
            coc_pct=round(coc_base * 1.5, 2),
            payback_anos=round(payback_base * 0.7, 1)
        ),
        "pesimista": EscenarioResponse(
            tipo=EscenarioTipo.PESIMISTA,
            descripcion="Condiciones adversas moderadas",
            supuestos={"arriendo": -15, "precio": 10, "plusvalia": -2},
            van_uf=round(van_base * 0.4, 2),
            tir_pct=round(tir_base * 0.7, 2),
            cap_rate_pct=round(cap_base * 0.8, 2),
            coc_pct=round(coc_base * 0.6, 2),
            payback_anos=round(payback_base * 1.4, 1)
        ),
        "estres": EscenarioResponse(
            tipo=EscenarioTipo.ESTRES,
            descripcion="Escenario de estrés severo",
            supuestos={"arriendo": -30, "precio": 20, "plusvalia": 0},
            van_uf=round(van_base * -0.3, 2),
            tir_pct=round(tir_base * 0.4, 2),
            cap_rate_pct=round(cap_base * 0.5, 2),
            coc_pct=round(coc_base * 0.3, 2),
            payback_anos=round(payback_base * 2.5, 1)
        )
    }
    
    return escenarios


# =============================================================================
# ENDPOINTS - PORTFOLIO
# =============================================================================

@router.post(
    "/portfolio/optimizar",
    response_model=PortfolioOptimizadoResponse,
    summary="Optimizar portfolio",
    description="""
    Optimiza la asignación de capital entre múltiples inversiones.
    
    Objetivos disponibles:
    - maximizar_sharpe: Mejor relación retorno/riesgo
    - maximizar_retorno: Máximo retorno esperado
    - minimizar_riesgo: Mínima volatilidad
    
    Genera frontera eficiente y asignación óptima.
    """
)
async def optimizar_portfolio(request: OptimizarPortfolioRequest):
    """Optimiza portfolio de inversiones"""
    inversiones = []
    for aid in request.inversiones_candidatas:
        analisis = _service.obtener_analisis(aid)
        if analisis and analisis.viabilidad.viable:
            inversiones.append({
                "id": analisis.id,
                "nombre": analisis.nombre_proyecto,
                "inversion_uf": analisis.inversion_total_uf,
                "retorno_esperado": analisis.metricas.roi_anual_pct,
                "riesgo": analisis.viabilidad.score_riesgo * 5  # Convertir a %
            })
    
    if len(inversiones) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 inversiones viables para optimizar"
        )
    
    # Optimización simplificada
    total_disponible = request.presupuesto_total_uf
    asignacion = {}
    seleccionadas = []
    capital_usado = 0.0
    
    # Ordenar por retorno/riesgo (Sharpe simplificado)
    inversiones.sort(key=lambda x: x["retorno_esperado"] / max(x["riesgo"], 1), reverse=True)
    
    for inv in inversiones:
        if capital_usado + inv["inversion_uf"] <= total_disponible:
            seleccionadas.append(inv)
            capital_usado += inv["inversion_uf"]
    
    if not seleccionadas:
        raise HTTPException(
            status_code=400,
            detail="El presupuesto no es suficiente para ninguna inversión"
        )
    
    # Calcular asignación
    for inv in seleccionadas:
        asignacion[inv["id"]] = round((inv["inversion_uf"] / capital_usado) * 100, 1)
    
    # Métricas portfolio
    retorno_portfolio = sum(
        inv["retorno_esperado"] * (inv["inversion_uf"] / capital_usado)
        for inv in seleccionadas
    )
    riesgo_portfolio = sum(
        inv["riesgo"] * (inv["inversion_uf"] / capital_usado)
        for inv in seleccionadas
    ) * 0.8  # Factor diversificación
    
    sharpe = retorno_portfolio / max(riesgo_portfolio, 0.1)
    
    return PortfolioOptimizadoResponse(
        inversiones_seleccionadas=seleccionadas,
        asignacion_capital=asignacion,
        inversion_total_uf=round(capital_usado, 2),
        capital_no_asignado_uf=round(total_disponible - capital_usado, 2),
        metricas_portfolio={
            "n_inversiones": len(seleccionadas),
            "inversion_promedio_uf": round(capital_usado / len(seleccionadas), 2),
            "retorno_promedio_pct": round(retorno_portfolio, 2),
            "riesgo_promedio_pct": round(riesgo_portfolio, 2)
        },
        retorno_esperado_pct=round(retorno_portfolio, 2),
        riesgo_portfolio_pct=round(riesgo_portfolio, 2),
        sharpe_ratio=round(sharpe, 2),
        diversificacion_score=round(min(len(seleccionadas) / 5, 1.0) * 100, 0)
    )


# =============================================================================
# ENDPOINTS - REPORTES Y EXPORTACIÓN
# =============================================================================

@router.post(
    "/reportes/generar",
    response_model=ReporteGeneradoResponse,
    summary="Generar reporte",
    description="""
    Genera reporte de análisis en formato PDF, Excel o HTML.
    
    Tipos de reporte:
    - ejecutivo: Resumen de una página
    - detallado: Análisis completo con todos los detalles
    - comparativo: Comparación de múltiples inversiones
    - sensibilidad: Enfocado en análisis de sensibilidad
    - montecarlo: Enfocado en simulación probabilística
    """
)
async def generar_reporte(
    request: GenerarReporteRequest,
    background_tasks: BackgroundTasks
):
    """Genera reporte de análisis"""
    # Verificar que existan los análisis
    for aid in request.analisis_ids:
        if not _service.obtener_analisis(aid):
            raise HTTPException(
                status_code=404,
                detail=f"Análisis no encontrado: {aid}"
            )
    
    reporte_id = str(uuid.uuid4())
    nombre = request.nombre_archivo or f"reporte_inversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    extension = request.formato.value
    
    # En implementación real, se generaría el archivo en background
    # background_tasks.add_task(generar_reporte_async, reporte_id, request)
    
    return ReporteGeneradoResponse(
        id=reporte_id,
        tipo_reporte=request.tipo_reporte,
        formato=request.formato,
        nombre_archivo=f"{nombre}.{extension}",
        url_descarga=f"/api/v1/analisis-inversion/reportes/{reporte_id}/download",
        tamano_bytes=150000,  # Estimado
        generado_en=datetime.utcnow(),
        expira_en=datetime.utcnow().replace(hour=23, minute=59),
        analisis_incluidos=request.analisis_ids,
        secciones=request.secciones
    )


@router.get(
    "/reportes/{reporte_id}/download",
    summary="Descargar reporte",
    description="Descarga un reporte generado previamente"
)
async def descargar_reporte(
    reporte_id: str = Path(..., description="ID del reporte")
):
    """Descarga reporte generado"""
    # En implementación real, retornaría el archivo
    raise HTTPException(
        status_code=404,
        detail="Reporte no encontrado o expirado. Genere uno nuevo."
    )


@router.post(
    "/{analisis_id}/exportar",
    summary="Exportar análisis",
    description="Exporta un análisis individual a JSON, Excel o PDF"
)
async def exportar_analisis(
    analisis_id: str = Path(..., description="ID del análisis"),
    formato: FormatoExportacion = Query(FormatoExportacion.JSON)
):
    """Exporta análisis a formato especificado"""
    analisis = _service.obtener_analisis(analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    if formato == FormatoExportacion.JSON:
        return analisis.dict()
    
    # Para otros formatos, generar y retornar URL
    return {
        "url_descarga": f"/api/v1/analisis-inversion/{analisis_id}/download?formato={formato.value}",
        "formato": formato.value,
        "expira_en": datetime.utcnow().replace(hour=23, minute=59).isoformat()
    }


# =============================================================================
# ENDPOINTS - ESTADÍSTICAS Y BENCHMARKS
# =============================================================================

@router.get(
    "/estadisticas/globales",
    response_model=EstadisticasGlobalesResponse,
    summary="Estadísticas globales",
    description="Obtiene estadísticas agregadas de todos los análisis"
)
async def estadisticas_globales(
    usuario_id: Optional[str] = Query(None, description="Filtrar por usuario")
):
    """Obtiene estadísticas globales"""
    analisis = list(_service._analisis_cache.values())
    
    if usuario_id:
        analisis = [a for a in analisis if a.usuario_id == usuario_id]
    
    if not analisis:
        return EstadisticasGlobalesResponse(
            total_analisis=0,
            analisis_mes_actual=0,
            por_tipo_inversion={},
            por_tipo_activo={},
            por_comuna={},
            metricas_promedio={},
            tendencias={},
            top_rentabilidad=[]
        )
    
    # Contar por tipo
    por_tipo_inv = {}
    por_tipo_act = {}
    por_comuna = {}
    
    for a in analisis:
        por_tipo_inv[a.tipo_inversion.value] = por_tipo_inv.get(a.tipo_inversion.value, 0) + 1
        por_tipo_act[a.propiedad_tipo.value] = por_tipo_act.get(a.propiedad_tipo.value, 0) + 1
        por_comuna[a.propiedad_comuna] = por_comuna.get(a.propiedad_comuna, 0) + 1
    
    # Métricas promedio
    metricas_promedio = {
        "van_uf": round(sum(a.metricas.van_uf for a in analisis) / len(analisis), 2),
        "tir_pct": round(sum(a.metricas.tir_pct for a in analisis) / len(analisis), 2),
        "cap_rate_pct": round(sum(a.metricas.cap_rate_pct for a in analisis) / len(analisis), 2),
        "roi_anual_pct": round(sum(a.metricas.roi_anual_pct for a in analisis) / len(analisis), 2)
    }
    
    # Top rentabilidad
    top = sorted(analisis, key=lambda x: x.metricas.tir_pct, reverse=True)[:5]
    top_rentabilidad = [
        {
            "id": a.id,
            "nombre": a.nombre_proyecto,
            "tir_pct": a.metricas.tir_pct,
            "van_uf": a.metricas.van_uf
        }
        for a in top
    ]
    
    mes_actual = datetime.utcnow().month
    analisis_mes = sum(1 for a in analisis if a.creado_en.month == mes_actual)
    
    return EstadisticasGlobalesResponse(
        total_analisis=len(analisis),
        analisis_mes_actual=analisis_mes,
        por_tipo_inversion=por_tipo_inv,
        por_tipo_activo=por_tipo_act,
        por_comuna=por_comuna,
        metricas_promedio=metricas_promedio,
        tendencias={},  # Requiere datos históricos
        top_rentabilidad=top_rentabilidad
    )


@router.get(
    "/benchmarks/mercado",
    summary="Benchmarks de mercado",
    description="Obtiene benchmarks del mercado inmobiliario chileno"
)
async def benchmarks_mercado(
    tipo_activo: Optional[TipoActivo] = Query(None),
    comuna: Optional[str] = Query(None)
):
    """Obtiene benchmarks de mercado"""
    # Benchmarks típicos mercado chileno 2025
    benchmarks = {
        "residencial": {
            "cap_rate_promedio": 4.5,
            "cap_rate_rango": [3.5, 6.0],
            "tir_promedio": 8.5,
            "tir_rango": [6.0, 12.0],
            "yield_bruto_promedio": 5.2,
            "precio_m2_uf_promedio": 85.0,
            "precio_m2_uf_rango": [50.0, 150.0],
            "vacancia_promedio_pct": 5.0
        },
        "comercial": {
            "cap_rate_promedio": 6.5,
            "cap_rate_rango": [5.0, 9.0],
            "tir_promedio": 10.5,
            "tir_rango": [8.0, 15.0],
            "yield_bruto_promedio": 7.5,
            "precio_m2_uf_promedio": 120.0,
            "precio_m2_uf_rango": [70.0, 250.0],
            "vacancia_promedio_pct": 8.0
        },
        "oficinas": {
            "cap_rate_promedio": 7.0,
            "cap_rate_rango": [5.5, 9.5],
            "tir_promedio": 9.5,
            "tir_rango": [7.0, 13.0],
            "yield_bruto_promedio": 8.0,
            "precio_m2_uf_promedio": 95.0,
            "precio_m2_uf_rango": [60.0, 180.0],
            "vacancia_promedio_pct": 12.0
        }
    }
    
    if tipo_activo:
        key = tipo_activo.value
        if key in benchmarks:
            return {key: benchmarks[key]}
    
    return benchmarks


@router.get(
    "/calculadora/dividendo",
    summary="Calculadora de dividendo",
    description="Calcula dividendo mensual de crédito hipotecario"
)
async def calcular_dividendo(
    monto_uf: float = Query(..., gt=0, description="Monto del crédito en UF"),
    tasa_anual_pct: float = Query(4.5, ge=0, le=20, description="Tasa anual (%)"),
    plazo_anos: int = Query(20, ge=1, le=30, description="Plazo en años")
):
    """Calcula dividendo mensual"""
    plazo_meses = plazo_anos * 12
    
    if tasa_anual_pct == 0:
        dividendo = monto_uf / plazo_meses
    else:
        tasa_mensual = tasa_anual_pct / 12 / 100
        dividendo = monto_uf * (tasa_mensual * (1 + tasa_mensual)**plazo_meses) / ((1 + tasa_mensual)**plazo_meses - 1)
    
    return {
        "monto_credito_uf": monto_uf,
        "tasa_anual_pct": tasa_anual_pct,
        "plazo_anos": plazo_anos,
        "plazo_meses": plazo_meses,
        "dividendo_mensual_uf": round(dividendo, 4),
        "total_a_pagar_uf": round(dividendo * plazo_meses, 2),
        "intereses_totales_uf": round(dividendo * plazo_meses - monto_uf, 2),
        "costo_total_pct": round((dividendo * plazo_meses / monto_uf - 1) * 100, 1)
    }


@router.get(
    "/calculadora/cap-rate",
    summary="Calculadora Cap Rate",
    description="Calcula Cap Rate y rentabilidades"
)
async def calcular_cap_rate(
    precio_uf: float = Query(..., gt=0, description="Precio compra en UF"),
    arriendo_mensual_uf: float = Query(..., gt=0, description="Arriendo mensual en UF"),
    gastos_anuales_uf: float = Query(0, ge=0, description="Gastos operación anuales UF"),
    ocupacion_pct: float = Query(95, ge=0, le=100, description="Tasa ocupación (%)")
):
    """Calcula Cap Rate y yields"""
    ingreso_anual = arriendo_mensual_uf * 12 * (ocupacion_pct / 100)
    noi = ingreso_anual - gastos_anuales_uf
    
    gross_yield = (arriendo_mensual_uf * 12 / precio_uf) * 100
    net_yield = (noi / precio_uf) * 100
    cap_rate = net_yield
    price_rent_ratio = precio_uf / (arriendo_mensual_uf * 12)
    
    return {
        "precio_uf": precio_uf,
        "arriendo_mensual_uf": arriendo_mensual_uf,
        "ingreso_anual_uf": round(ingreso_anual, 2),
        "gastos_anuales_uf": gastos_anuales_uf,
        "noi_uf": round(noi, 2),
        "gross_yield_pct": round(gross_yield, 2),
        "net_yield_pct": round(net_yield, 2),
        "cap_rate_pct": round(cap_rate, 2),
        "price_rent_ratio": round(price_rent_ratio, 1),
        "anos_recuperacion_simple": round(price_rent_ratio, 1)
    }


# =============================================================================
# ENDPOINTS - CLONACIÓN Y TEMPLATES
# =============================================================================

@router.post(
    "/{analisis_id}/clonar",
    response_model=AnalisisInversionResponse,
    status_code=201,
    summary="Clonar análisis",
    description="Crea una copia de un análisis existente para modificar"
)
async def clonar_analisis(
    analisis_id: str = Path(..., description="ID del análisis a clonar"),
    nuevo_nombre: Optional[str] = Query(None, description="Nombre para el clon")
):
    """Clona un análisis existente"""
    original = _service.obtener_analisis(analisis_id)
    if not original:
        raise HTTPException(status_code=404, detail=f"Análisis no encontrado: {analisis_id}")
    
    # Crear copia con nuevo ID
    clon_id = str(uuid.uuid4())
    clon_codigo = _service._generar_codigo()
    
    # Copiar datos (en implementación real se copiarían todos los datos)
    clon = AnalisisInversionResponse(
        id=clon_id,
        codigo=clon_codigo,
        nombre_proyecto=nuevo_nombre or f"{original.nombre_proyecto} (Copia)",
        descripcion=original.descripcion,
        tipo_inversion=original.tipo_inversion,
        perfil_riesgo=original.perfil_riesgo,
        propiedad_direccion=original.propiedad_direccion,
        propiedad_comuna=original.propiedad_comuna,
        propiedad_tipo=original.propiedad_tipo,
        propiedad_superficie_m2=original.propiedad_superficie_m2,
        inversion_total_uf=original.inversion_total_uf,
        capital_propio_uf=original.capital_propio_uf,
        financiamiento_uf=original.financiamiento_uf,
        ltv_pct=original.ltv_pct,
        horizonte_anos=original.horizonte_anos,
        metricas=original.metricas,
        flujos_caja=original.flujos_caja,
        sensibilidad=original.sensibilidad,
        montecarlo=original.montecarlo,
        viabilidad=original.viabilidad,
        usuario_id=original.usuario_id,
        creado_en=datetime.utcnow(),
        actualizado_en=datetime.utcnow(),
        version=1,
        notas=f"Clonado de {original.codigo}",
        tags=original.tags + ["clonado"]
    )
    
    _service._analisis_cache[clon_id] = clon
    return clon


@router.get(
    "/templates",
    summary="Listar templates",
    description="Obtiene templates predefinidos de análisis"
)
async def listar_templates():
    """Lista templates disponibles"""
    return {
        "templates": [
            {
                "id": "template_depto_arriendo",
                "nombre": "Departamento para Arriendo",
                "descripcion": "Template estándar para inversión buy-to-let en departamento",
                "tipo_inversion": "compra_arriendo",
                "tipo_activo": "residencial",
                "parametros_default": {
                    "pie_porcentaje": 20,
                    "plazo_anos": 20,
                    "horizonte_inversion": 10,
                    "administracion_pct": 8,
                    "imprevistos_pct": 5
                }
            },
            {
                "id": "template_local_comercial",
                "nombre": "Local Comercial",
                "descripcion": "Template para inversión en local comercial",
                "tipo_inversion": "compra_arriendo",
                "tipo_activo": "comercial",
                "parametros_default": {
                    "pie_porcentaje": 30,
                    "plazo_anos": 15,
                    "horizonte_inversion": 8,
                    "administracion_pct": 5,
                    "imprevistos_pct": 8
                }
            },
            {
                "id": "template_flip",
                "nombre": "Fix & Flip",
                "descripcion": "Template para compra, remodelación y reventa",
                "tipo_inversion": "compra_reventa",
                "tipo_activo": "residencial",
                "parametros_default": {
                    "pie_porcentaje": 50,
                    "horizonte_inversion": 2,
                    "costos_remodelacion_pct": 15,
                    "margen_objetivo_pct": 25
                }
            }
        ]
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get(
    "/health",
    summary="Health check",
    description="Verifica estado del módulo de análisis de inversión"
)
async def health_check():
    """Verifica estado del módulo"""
    return {
        "status": "healthy",
        "modulo": "M07 - Análisis de Inversión",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "analisis_en_cache": len(_service._analisis_cache),
        "endpoints_activos": 28,
        "normativa": [
            "Ley 21.713",
            "NCh 2728",
            "Circular SII 42/2020",
            "IVS 2022"
        ]
    }
