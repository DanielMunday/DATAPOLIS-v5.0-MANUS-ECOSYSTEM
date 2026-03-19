"""
DATAPOLIS v3.0 - Router M06B: Plusvalía y Ganancias de Capital
==============================================================

API REST completa para cálculo de plusvalías, ganancias de capital
y proyecciones de valorización de activos inmobiliarios.

Funcionalidades:
- Cálculo de plusvalía histórica y proyectada
- Ganancias de capital según Ley 21.210 y 21.713
- Análisis de factores de valorización
- Proyecciones con múltiples escenarios
- Comparación con benchmark de mercado

Normativa:
- Ley 21.210 (Modernización Tributaria - impuesto ganancias capital)
- Ley 21.713 (Tributación rentas inmobiliarias)
- Circular SII 42/2020 (Costo tributario y ajustes)
- NCh 2728:2015 (Valoración inmobiliaria)

Endpoints: 22
Autor: DATAPOLIS SpA
Versión: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid

router = APIRouter(
    prefix="/plusvalia",
    tags=["M06B - Plusvalía y Ganancias de Capital"],
    responses={
        400: {"description": "Parámetros inválidos"},
        401: {"description": "No autenticado"},
        403: {"description": "Sin permisos"},
        404: {"description": "Cálculo no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)


# =============================================================================
# ENUMS
# =============================================================================

class TipoActivo(str, Enum):
    """Tipos de activo inmobiliario"""
    RESIDENCIAL = "residencial"
    COMERCIAL = "comercial"
    INDUSTRIAL = "industrial"
    TERRENO = "terreno"
    AGRICOLA = "agricola"
    MIXTO = "mixto"


class MetodoValorizacion(str, Enum):
    """Métodos de valorización"""
    COMPARABLES = "comparables"           # Comparación de mercado
    COSTO_REPOSICION = "costo_reposicion"  # Costo de reposición
    CAPITALIZACION = "capitalizacion"      # Capitalización de rentas
    RESIDUAL = "residual"                  # Método residual
    MIXTO = "mixto"                        # Combinación


class RegimenTributario(str, Enum):
    """Regímenes tributarios aplicables"""
    PERSONA_NATURAL = "persona_natural"    # IGC
    PYME_14D3 = "pyme_14d3"               # Régimen ProPyme
    GENERAL_14A = "general_14a"           # Régimen general
    RENTA_PRESUNTA = "renta_presunta"     # Renta presunta


class TipoGanancia(str, Enum):
    """Tipos de ganancia de capital"""
    HABITUAL = "habitual"                 # Renta ordinaria
    NO_HABITUAL = "no_habitual"           # Ganancia capital especial
    INGRESO_NO_RENTA = "ingreso_no_renta" # DFL2 (exento)


class EscenarioProyeccion(str, Enum):
    """Escenarios para proyección"""
    CONSERVADOR = "conservador"
    BASE = "base"
    OPTIMISTA = "optimista"
    ESTRES = "estres"


class FactorValorizacion(str, Enum):
    """Factores que afectan valorización"""
    UBICACION = "ubicacion"
    INFRAESTRUCTURA = "infraestructura"
    NORMATIVA_URBANA = "normativa_urbana"
    DESARROLLO_INMOBILIARIO = "desarrollo_inmobiliario"
    ACCESIBILIDAD = "accesibilidad"
    SERVICIOS = "servicios"
    SEGURIDAD = "seguridad"
    AMBIENTALES = "ambientales"


# =============================================================================
# SCHEMAS - REQUESTS
# =============================================================================

class DatosAdquisicionRequest(BaseModel):
    """Datos de adquisición del inmueble"""
    fecha_adquisicion: date = Field(..., description="Fecha de compra/adquisición")
    precio_adquisicion_uf: float = Field(..., gt=0, description="Precio de compra en UF")
    precio_adquisicion_pesos: Optional[float] = Field(None, gt=0, description="Precio en pesos históricos")
    valor_uf_fecha: Optional[float] = Field(None, gt=0, description="Valor UF a la fecha de compra")
    forma_adquisicion: str = Field("compraventa", description="compraventa, herencia, donacion, adjudicacion")
    costo_mejoras_uf: float = Field(0, ge=0, description="Inversiones en mejoras capitalizables UF")
    fecha_mejoras: Optional[date] = Field(None, description="Fecha de principales mejoras")
    gastos_adquisicion_uf: float = Field(0, ge=0, description="Gastos compra (notario, CBR, impuestos)")


class DatosActualesRequest(BaseModel):
    """Datos actuales del inmueble"""
    direccion: str = Field(..., min_length=5, max_length=500)
    comuna: str = Field(..., min_length=2, max_length=100)
    region: str = Field("Metropolitana", max_length=100)
    tipo_activo: TipoActivo = Field(TipoActivo.RESIDENCIAL)
    superficie_terreno_m2: float = Field(..., gt=0, description="Superficie terreno en m²")
    superficie_construida_m2: Optional[float] = Field(None, gt=0, description="Superficie construida m²")
    ano_construccion: Optional[int] = Field(None, ge=1900, le=2030)
    rol_sii: Optional[str] = Field(None, max_length=50, description="ROL SII")
    avaluo_fiscal_uf: Optional[float] = Field(None, gt=0, description="Avalúo fiscal actual UF")
    valor_mercado_actual_uf: Optional[float] = Field(None, gt=0, description="Valor mercado estimado UF")
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class ParametrosTributariosRequest(BaseModel):
    """Parámetros tributarios para cálculo de impuestos"""
    regimen: RegimenTributario = Field(RegimenTributario.PERSONA_NATURAL)
    tipo_ganancia: TipoGanancia = Field(TipoGanancia.NO_HABITUAL)
    anos_posesion: Optional[int] = Field(None, ge=0, description="Años de posesión (calculado si no se indica)")
    aplica_dfl2: bool = Field(False, description="¿Aplica beneficio DFL2?")
    vivienda_unica: bool = Field(False, description="¿Es vivienda única del contribuyente?")
    tasa_marginal_igc_pct: float = Field(35.0, ge=0, le=40, description="Tasa marginal IGC (%)")
    credito_primera_vivienda_uf: float = Field(0, ge=0, description="Crédito por primera vivienda UF")


class CalcularPlusvaliaRequest(BaseModel):
    """Request completo para calcular plusvalía"""
    # Identificación
    nombre_calculo: str = Field(..., min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)
    
    # Datos principales
    adquisicion: DatosAdquisicionRequest
    datos_actuales: DatosActualesRequest
    tributarios: ParametrosTributariosRequest = Field(default_factory=ParametrosTributariosRequest)
    
    # Opciones
    fecha_calculo: Optional[date] = Field(None, description="Fecha del cálculo (default: hoy)")
    valor_venta_estimado_uf: Optional[float] = Field(None, gt=0, description="Precio venta esperado UF")
    incluir_proyeccion: bool = Field(True, description="¿Incluir proyección de plusvalía?")
    horizonte_proyeccion_anos: int = Field(5, ge=1, le=20, description="Horizonte de proyección")
    
    # Metadata
    usuario_id: Optional[str] = None
    notas: Optional[str] = Field(None, max_length=5000)

    class Config:
        schema_extra = {
            "example": {
                "nombre_calculo": "Plusvalía Departamento Providencia",
                "adquisicion": {
                    "fecha_adquisicion": "2018-06-15",
                    "precio_adquisicion_uf": 4200.0,
                    "costo_mejoras_uf": 150.0,
                    "gastos_adquisicion_uf": 120.0
                },
                "datos_actuales": {
                    "direccion": "Av. Providencia 1234, Depto 501",
                    "comuna": "Providencia",
                    "tipo_activo": "residencial",
                    "superficie_terreno_m2": 8.5,
                    "superficie_construida_m2": 65.0,
                    "valor_mercado_actual_uf": 5800.0
                },
                "valor_venta_estimado_uf": 6000.0
            }
        }


class ProyectarPlusvaliaRequest(BaseModel):
    """Request para proyección de plusvalía"""
    calculo_id: str = Field(..., description="ID del cálculo base")
    horizonte_anos: int = Field(10, ge=1, le=30, description="Horizonte de proyección")
    escenarios: List[EscenarioProyeccion] = Field(
        default_factory=lambda: [
            EscenarioProyeccion.CONSERVADOR,
            EscenarioProyeccion.BASE,
            EscenarioProyeccion.OPTIMISTA
        ]
    )
    tasa_plusvalia_anual_pct: Optional[float] = Field(None, ge=-10, le=30, description="Tasa manual (%)")


class SimularVentaRequest(BaseModel):
    """Request para simular venta"""
    calculo_id: str = Field(..., description="ID del cálculo base")
    precio_venta_uf: float = Field(..., gt=0, description="Precio de venta estimado UF")
    fecha_venta: Optional[date] = Field(None, description="Fecha estimada de venta")
    gastos_venta_pct: float = Field(3.0, ge=0, le=10, description="Gastos de venta (%)")
    comision_corretaje_pct: float = Field(2.0, ge=0, le=5, description="Comisión corretaje (%)")


class CompararComunasRequest(BaseModel):
    """Request para comparar plusvalía entre comunas"""
    comunas: List[str] = Field(..., min_items=2, max_items=20)
    tipo_activo: TipoActivo = Field(TipoActivo.RESIDENCIAL)
    periodo_anos: int = Field(5, ge=1, le=20)


# =============================================================================
# SCHEMAS - RESPONSES
# =============================================================================

class CostoTributarioResponse(BaseModel):
    """Cálculo del costo tributario según Ley 21.210"""
    precio_adquisicion_uf: float
    gastos_adquisicion_uf: float
    mejoras_capitalizables_uf: float
    costo_tributario_base_uf: float
    ajuste_ipc_uf: float = Field(..., description="Ajuste por IPC hasta 31/12/2014")
    ajuste_variacion_ipc_uf: float = Field(..., description="Ajuste variación IPC desde 2015")
    costo_tributario_final_uf: float
    factor_ajuste_aplicado: float


class GananciaCapitalResponse(BaseModel):
    """Cálculo de ganancia de capital"""
    valor_venta_uf: float
    gastos_venta_uf: float
    precio_venta_neto_uf: float
    costo_tributario_uf: float
    ganancia_capital_bruta_uf: float
    deducciones_uf: float
    ganancia_capital_neta_uf: float
    tipo_ganancia: TipoGanancia
    exenta: bool
    motivo_exencion: Optional[str]


class ImpuestoGananciaResponse(BaseModel):
    """Cálculo del impuesto sobre ganancia de capital"""
    ganancia_capital_uf: float
    base_imponible_uf: float
    # Opción IGC
    tasa_igc_aplicada_pct: float
    impuesto_igc_uf: float
    # Opción tasa única
    tasa_unica_pct: float = Field(10.0, description="Tasa única Ley 21.210")
    impuesto_tasa_unica_uf: float
    # Recomendación
    opcion_recomendada: str
    impuesto_menor_uf: float
    ahorro_opcion_uf: float
    # Créditos
    credito_primera_vivienda_uf: float
    impuesto_final_uf: float


class PlusvaliaHistoricaResponse(BaseModel):
    """Plusvalía histórica calculada"""
    fecha_adquisicion: date
    fecha_calculo: date
    anos_transcurridos: float
    valor_adquisicion_uf: float
    valor_actual_uf: float
    plusvalia_uf: float
    plusvalia_pct: float
    plusvalia_anual_promedio_pct: float
    plusvalia_real_uf: float = Field(..., description="Ajustada por inflación")
    plusvalia_real_pct: float


class ProyeccionAnualResponse(BaseModel):
    """Proyección de valor para un año"""
    ano: int
    fecha: date
    valor_estimado_uf: float
    plusvalia_acumulada_uf: float
    plusvalia_acumulada_pct: float
    plusvalia_ano_uf: float
    plusvalia_ano_pct: float


class EscenarioProyeccionResponse(BaseModel):
    """Proyección bajo un escenario"""
    escenario: EscenarioProyeccion
    descripcion: str
    tasa_anual_asumida_pct: float
    proyecciones: List[ProyeccionAnualResponse]
    valor_final_uf: float
    plusvalia_total_uf: float
    plusvalia_total_pct: float
    cagr_pct: float = Field(..., description="Compound Annual Growth Rate")


class FactorValorizacionResponse(BaseModel):
    """Análisis de factor de valorización"""
    factor: FactorValorizacion
    descripcion: str
    impacto_estimado_pct: float = Field(..., ge=-50, le=100)
    tendencia: str = Field(..., description="positiva, neutral, negativa")
    detalle: str
    fuente: Optional[str]


class BenchmarkComunaResponse(BaseModel):
    """Benchmark de plusvalía por comuna"""
    comuna: str
    region: str
    plusvalia_5_anos_pct: float
    plusvalia_anual_promedio_pct: float
    precio_m2_promedio_uf: float
    variacion_ultimo_ano_pct: float
    ranking_regional: int
    n_transacciones_ano: int


class CalculoPlusvaliaResponse(BaseModel):
    """Response completa de cálculo de plusvalía"""
    id: str
    codigo: str = Field(..., description="Código: PV-YYYY-NNNNNN")
    nombre_calculo: str
    descripcion: Optional[str]
    
    # Datos propiedad
    direccion: str
    comuna: str
    tipo_activo: TipoActivo
    superficie_m2: float
    rol_sii: Optional[str]
    
    # Plusvalía histórica
    plusvalia_historica: PlusvaliaHistoricaResponse
    
    # Costo tributario
    costo_tributario: CostoTributarioResponse
    
    # Ganancia de capital (si hay valor venta)
    ganancia_capital: Optional[GananciaCapitalResponse]
    impuesto: Optional[ImpuestoGananciaResponse]
    
    # Proyección (si se solicitó)
    proyecciones: Optional[List[EscenarioProyeccionResponse]]
    
    # Factores
    factores_valorizacion: List[FactorValorizacionResponse]
    
    # Benchmark
    benchmark_comuna: Optional[BenchmarkComunaResponse]
    
    # Metadata
    usuario_id: Optional[str]
    creado_en: datetime
    actualizado_en: datetime
    version: int
    notas: Optional[str]


class SimulacionVentaResponse(BaseModel):
    """Response de simulación de venta"""
    calculo_id: str
    precio_venta_uf: float
    fecha_venta: date
    gastos_venta_uf: float
    precio_neto_uf: float
    costo_tributario_uf: float
    ganancia_bruta_uf: float
    ganancia_neta_uf: float
    impuesto_estimado_uf: float
    neto_a_recibir_uf: float
    rentabilidad_total_pct: float
    rentabilidad_anual_pct: float
    recomendaciones: List[str]


class ComparacionComunasResponse(BaseModel):
    """Response de comparación entre comunas"""
    comunas: List[BenchmarkComunaResponse]
    ranking: List[Dict[str, Any]]
    mejor_plusvalia: str
    peor_plusvalia: str
    diferencia_max_pct: float
    recomendacion: str


class EstadisticasPlusvaliaResponse(BaseModel):
    """Estadísticas agregadas de plusvalías"""
    total_calculos: int
    por_tipo_activo: Dict[str, int]
    por_comuna: Dict[str, int]
    plusvalia_promedio_pct: float
    plusvalia_mediana_pct: float
    mayor_plusvalia: Dict[str, Any]
    menor_plusvalia: Dict[str, Any]
    tendencia_mensual: List[Dict[str, float]]


class BusquedaCalculosResponse(BaseModel):
    """Response de búsqueda de cálculos"""
    calculos: List[CalculoPlusvaliaResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


# =============================================================================
# MOCK SERVICE
# =============================================================================

class MockPlusvaliaService:
    """Servicio mock para cálculos de plusvalía"""
    
    def __init__(self):
        self._calculos_cache: Dict[str, CalculoPlusvaliaResponse] = {}
        self._contador = 0
        # Datos benchmark por comuna
        self._benchmarks = {
            "Providencia": {"plusvalia_5a": 32.5, "anual": 5.8, "precio_m2": 95.0, "var_1a": 4.2},
            "Las Condes": {"plusvalia_5a": 28.0, "anual": 5.1, "precio_m2": 110.0, "var_1a": 3.8},
            "Ñuñoa": {"plusvalia_5a": 38.0, "anual": 6.7, "precio_m2": 78.0, "var_1a": 5.5},
            "Santiago": {"plusvalia_5a": 22.0, "anual": 4.1, "precio_m2": 72.0, "var_1a": 2.8},
            "Vitacura": {"plusvalia_5a": 25.0, "anual": 4.6, "precio_m2": 135.0, "var_1a": 3.2},
            "La Florida": {"plusvalia_5a": 35.0, "anual": 6.2, "precio_m2": 52.0, "var_1a": 4.8},
            "Maipú": {"plusvalia_5a": 30.0, "anual": 5.4, "precio_m2": 42.0, "var_1a": 4.0},
        }
    
    def _generar_codigo(self) -> str:
        self._contador += 1
        return f"PV-{datetime.now().year}-{self._contador:06d}"
    
    def calcular_plusvalia(self, request: CalcularPlusvaliaRequest) -> CalculoPlusvaliaResponse:
        """Calcula plusvalía completa"""
        calculo_id = str(uuid.uuid4())
        codigo = self._generar_codigo()
        fecha_calculo = request.fecha_calculo or date.today()
        
        # Calcular años transcurridos
        dias = (fecha_calculo - request.adquisicion.fecha_adquisicion).days
        anos = dias / 365.25
        
        # Determinar valor actual
        valor_actual = request.valor_venta_estimado_uf or request.datos_actuales.valor_mercado_actual_uf or \
                       request.adquisicion.precio_adquisicion_uf * 1.3
        valor_adquisicion = request.adquisicion.precio_adquisicion_uf
        
        # Plusvalía histórica
        plusvalia_uf = valor_actual - valor_adquisicion
        plusvalia_pct = (plusvalia_uf / valor_adquisicion) * 100
        plusvalia_anual = ((valor_actual / valor_adquisicion) ** (1 / max(anos, 0.1)) - 1) * 100
        
        # Ajuste por inflación (estimado ~3% anual)
        factor_inflacion = (1.03) ** anos
        valor_adquisicion_real = valor_adquisicion * factor_inflacion
        plusvalia_real = valor_actual - valor_adquisicion_real
        plusvalia_real_pct = (plusvalia_real / valor_adquisicion_real) * 100
        
        plusvalia_historica = PlusvaliaHistoricaResponse(
            fecha_adquisicion=request.adquisicion.fecha_adquisicion,
            fecha_calculo=fecha_calculo,
            anos_transcurridos=round(anos, 1),
            valor_adquisicion_uf=valor_adquisicion,
            valor_actual_uf=valor_actual,
            plusvalia_uf=round(plusvalia_uf, 2),
            plusvalia_pct=round(plusvalia_pct, 2),
            plusvalia_anual_promedio_pct=round(plusvalia_anual, 2),
            plusvalia_real_uf=round(plusvalia_real, 2),
            plusvalia_real_pct=round(plusvalia_real_pct, 2)
        )
        
        # Costo tributario según Ley 21.210
        costo_base = (
            request.adquisicion.precio_adquisicion_uf +
            request.adquisicion.gastos_adquisicion_uf +
            request.adquisicion.costo_mejoras_uf
        )
        
        # Ajustes IPC (simplificado)
        if request.adquisicion.fecha_adquisicion.year <= 2014:
            ajuste_ipc = costo_base * 0.15  # 15% ajuste estimado
            ajuste_var_ipc = costo_base * 0.20  # 20% variación desde 2015
        else:
            ajuste_ipc = 0
            ajuste_var_ipc = costo_base * (anos * 0.03)  # ~3% anual
        
        costo_final = costo_base + ajuste_ipc + ajuste_var_ipc
        
        costo_tributario = CostoTributarioResponse(
            precio_adquisicion_uf=request.adquisicion.precio_adquisicion_uf,
            gastos_adquisicion_uf=request.adquisicion.gastos_adquisicion_uf,
            mejoras_capitalizables_uf=request.adquisicion.costo_mejoras_uf,
            costo_tributario_base_uf=round(costo_base, 2),
            ajuste_ipc_uf=round(ajuste_ipc, 2),
            ajuste_variacion_ipc_uf=round(ajuste_var_ipc, 2),
            costo_tributario_final_uf=round(costo_final, 2),
            factor_ajuste_aplicado=round((costo_final / costo_base), 4)
        )
        
        # Ganancia de capital (si hay valor venta)
        ganancia_capital = None
        impuesto = None
        
        if request.valor_venta_estimado_uf:
            precio_venta = request.valor_venta_estimado_uf
            gastos_venta = precio_venta * 0.03  # 3% gastos venta
            precio_neto = precio_venta - gastos_venta
            ganancia_bruta = precio_neto - costo_final
            
            # Determinar si está exenta
            exenta = False
            motivo_exencion = None
            
            if request.tributarios.aplica_dfl2 and anos >= 1:
                exenta = True
                motivo_exencion = "Beneficio DFL2 - Más de 1 año de posesión"
            elif request.tributarios.vivienda_unica and ganancia_bruta <= 8000:
                exenta = True
                motivo_exencion = "Vivienda única con ganancia bajo 8000 UF"
            
            ganancia_capital = GananciaCapitalResponse(
                valor_venta_uf=precio_venta,
                gastos_venta_uf=round(gastos_venta, 2),
                precio_venta_neto_uf=round(precio_neto, 2),
                costo_tributario_uf=round(costo_final, 2),
                ganancia_capital_bruta_uf=round(ganancia_bruta, 2),
                deducciones_uf=0,
                ganancia_capital_neta_uf=round(ganancia_bruta, 2),
                tipo_ganancia=request.tributarios.tipo_ganancia,
                exenta=exenta,
                motivo_exencion=motivo_exencion
            )
            
            # Calcular impuesto si no está exenta
            if not exenta:
                base_imponible = ganancia_bruta
                
                # Opción IGC
                impuesto_igc = base_imponible * (request.tributarios.tasa_marginal_igc_pct / 100)
                
                # Opción tasa única 10%
                impuesto_tasa_unica = base_imponible * 0.10
                
                # Recomendación
                if impuesto_igc < impuesto_tasa_unica:
                    opcion = "IGC"
                    menor = impuesto_igc
                    ahorro = impuesto_tasa_unica - impuesto_igc
                else:
                    opcion = "Tasa única 10%"
                    menor = impuesto_tasa_unica
                    ahorro = impuesto_igc - impuesto_tasa_unica
                
                credito = request.tributarios.credito_primera_vivienda_uf
                impuesto_final = max(0, menor - credito)
                
                impuesto = ImpuestoGananciaResponse(
                    ganancia_capital_uf=round(ganancia_bruta, 2),
                    base_imponible_uf=round(base_imponible, 2),
                    tasa_igc_aplicada_pct=request.tributarios.tasa_marginal_igc_pct,
                    impuesto_igc_uf=round(impuesto_igc, 2),
                    tasa_unica_pct=10.0,
                    impuesto_tasa_unica_uf=round(impuesto_tasa_unica, 2),
                    opcion_recomendada=opcion,
                    impuesto_menor_uf=round(menor, 2),
                    ahorro_opcion_uf=round(ahorro, 2),
                    credito_primera_vivienda_uf=credito,
                    impuesto_final_uf=round(impuesto_final, 2)
                )
        
        # Proyecciones
        proyecciones = None
        if request.incluir_proyeccion:
            proyecciones = []
            escenarios_config = {
                EscenarioProyeccion.CONSERVADOR: {"tasa": 2.5, "desc": "Crecimiento moderado bajo inflación"},
                EscenarioProyeccion.BASE: {"tasa": 4.5, "desc": "Crecimiento histórico promedio mercado"},
                EscenarioProyeccion.OPTIMISTA: {"tasa": 7.0, "desc": "Alto crecimiento con desarrollo urbano"},
                EscenarioProyeccion.ESTRES: {"tasa": 0.0, "desc": "Estancamiento del mercado"},
            }
            
            for escenario, config in escenarios_config.items():
                tasa = config["tasa"] / 100
                proy_anos = []
                valor_base = valor_actual
                
                for a in range(1, request.horizonte_proyeccion_anos + 1):
                    valor_ano = valor_actual * ((1 + tasa) ** a)
                    plusv_acum = valor_ano - valor_actual
                    plusv_ano = valor_ano - (valor_actual * ((1 + tasa) ** (a - 1)))
                    
                    proy_anos.append(ProyeccionAnualResponse(
                        ano=a,
                        fecha=date(fecha_calculo.year + a, fecha_calculo.month, 1),
                        valor_estimado_uf=round(valor_ano, 2),
                        plusvalia_acumulada_uf=round(plusv_acum, 2),
                        plusvalia_acumulada_pct=round((plusv_acum / valor_actual) * 100, 2),
                        plusvalia_ano_uf=round(plusv_ano, 2),
                        plusvalia_ano_pct=round(config["tasa"], 2)
                    ))
                
                valor_final = proy_anos[-1].valor_estimado_uf
                proyecciones.append(EscenarioProyeccionResponse(
                    escenario=escenario,
                    descripcion=config["desc"],
                    tasa_anual_asumida_pct=config["tasa"],
                    proyecciones=proy_anos,
                    valor_final_uf=valor_final,
                    plusvalia_total_uf=round(valor_final - valor_actual, 2),
                    plusvalia_total_pct=round((valor_final / valor_actual - 1) * 100, 2),
                    cagr_pct=config["tasa"]
                ))
        
        # Factores de valorización
        factores = [
            FactorValorizacionResponse(
                factor=FactorValorizacion.UBICACION,
                descripcion="Posicionamiento geográfico y entorno",
                impacto_estimado_pct=15.0,
                tendencia="positiva",
                detalle=f"Comuna {request.datos_actuales.comuna} con buena valorización",
                fuente="Análisis de mercado DATAPOLIS"
            ),
            FactorValorizacionResponse(
                factor=FactorValorizacion.INFRAESTRUCTURA,
                descripcion="Proyectos de infraestructura cercanos",
                impacto_estimado_pct=8.0,
                tendencia="positiva",
                detalle="Metro y conectividad en desarrollo",
                fuente="Estudios MOP/Metro"
            ),
            FactorValorizacionResponse(
                factor=FactorValorizacion.NORMATIVA_URBANA,
                descripcion="Cambios regulatorios y densificación",
                impacto_estimado_pct=5.0,
                tendencia="neutral",
                detalle="Estabilidad normativa sin cambios mayores previstos",
                fuente="Plan Regulador Comunal"
            ),
        ]
        
        # Benchmark comuna
        benchmark = None
        comuna = request.datos_actuales.comuna
        if comuna in self._benchmarks:
            bm = self._benchmarks[comuna]
            benchmark = BenchmarkComunaResponse(
                comuna=comuna,
                region=request.datos_actuales.region,
                plusvalia_5_anos_pct=bm["plusvalia_5a"],
                plusvalia_anual_promedio_pct=bm["anual"],
                precio_m2_promedio_uf=bm["precio_m2"],
                variacion_ultimo_ano_pct=bm["var_1a"],
                ranking_regional=3,
                n_transacciones_ano=1250
            )
        
        # Construir response
        ahora = datetime.utcnow()
        response = CalculoPlusvaliaResponse(
            id=calculo_id,
            codigo=codigo,
            nombre_calculo=request.nombre_calculo,
            descripcion=request.descripcion,
            direccion=request.datos_actuales.direccion,
            comuna=request.datos_actuales.comuna,
            tipo_activo=request.datos_actuales.tipo_activo,
            superficie_m2=request.datos_actuales.superficie_construida_m2 or request.datos_actuales.superficie_terreno_m2,
            rol_sii=request.datos_actuales.rol_sii,
            plusvalia_historica=plusvalia_historica,
            costo_tributario=costo_tributario,
            ganancia_capital=ganancia_capital,
            impuesto=impuesto,
            proyecciones=proyecciones,
            factores_valorizacion=factores,
            benchmark_comuna=benchmark,
            usuario_id=request.usuario_id,
            creado_en=ahora,
            actualizado_en=ahora,
            version=1,
            notas=request.notas
        )
        
        self._calculos_cache[calculo_id] = response
        return response
    
    def obtener_calculo(self, calculo_id: str) -> Optional[CalculoPlusvaliaResponse]:
        if calculo_id in self._calculos_cache:
            return self._calculos_cache[calculo_id]
        for calc in self._calculos_cache.values():
            if calc.codigo == calculo_id:
                return calc
        return None
    
    def obtener_benchmark(self, comuna: str) -> Optional[BenchmarkComunaResponse]:
        if comuna in self._benchmarks:
            bm = self._benchmarks[comuna]
            return BenchmarkComunaResponse(
                comuna=comuna,
                region="Metropolitana",
                plusvalia_5_anos_pct=bm["plusvalia_5a"],
                plusvalia_anual_promedio_pct=bm["anual"],
                precio_m2_promedio_uf=bm["precio_m2"],
                variacion_ultimo_ano_pct=bm["var_1a"],
                ranking_regional=3,
                n_transacciones_ano=1250
            )
        return None


# Instancia global
_service = MockPlusvaliaService()


# =============================================================================
# ENDPOINTS - CÁLCULOS CRUD
# =============================================================================

@router.post(
    "",
    response_model=CalculoPlusvaliaResponse,
    status_code=201,
    summary="Calcular plusvalía",
    description="""
    Calcula plusvalía histórica y proyectada de un inmueble.
    
    Incluye:
    - Plusvalía histórica nominal y real (ajustada por inflación)
    - Costo tributario según Ley 21.210 con ajustes IPC
    - Ganancia de capital e impuesto estimado
    - Proyecciones bajo múltiples escenarios
    - Factores de valorización
    - Benchmark de la comuna
    """
)
async def calcular_plusvalia(request: CalcularPlusvaliaRequest):
    """Calcula plusvalía completa de un inmueble"""
    try:
        return _service.calcular_plusvalia(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{calculo_id}",
    response_model=CalculoPlusvaliaResponse,
    summary="Obtener cálculo",
    description="Obtiene un cálculo de plusvalía por ID o código"
)
async def obtener_calculo(
    calculo_id: str = Path(..., description="ID o código del cálculo (PV-YYYY-NNNNNN)")
):
    """Obtiene cálculo por ID"""
    calculo = _service.obtener_calculo(calculo_id)
    if not calculo:
        raise HTTPException(status_code=404, detail=f"Cálculo no encontrado: {calculo_id}")
    return calculo


@router.get(
    "",
    response_model=BusquedaCalculosResponse,
    summary="Buscar cálculos",
    description="Búsqueda de cálculos con filtros"
)
async def buscar_calculos(
    usuario_id: Optional[str] = Query(None),
    tipo_activo: Optional[TipoActivo] = Query(None),
    comuna: Optional[str] = Query(None),
    plusvalia_min_pct: Optional[float] = Query(None, ge=-100),
    plusvalia_max_pct: Optional[float] = Query(None, le=500),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100)
):
    """Busca cálculos con filtros"""
    calculos = list(_service._calculos_cache.values())
    
    if usuario_id:
        calculos = [c for c in calculos if c.usuario_id == usuario_id]
    if tipo_activo:
        calculos = [c for c in calculos if c.tipo_activo == tipo_activo]
    if comuna:
        calculos = [c for c in calculos if comuna.lower() in c.comuna.lower()]
    if plusvalia_min_pct is not None:
        calculos = [c for c in calculos if c.plusvalia_historica.plusvalia_pct >= plusvalia_min_pct]
    if plusvalia_max_pct is not None:
        calculos = [c for c in calculos if c.plusvalia_historica.plusvalia_pct <= plusvalia_max_pct]
    
    total = len(calculos)
    inicio = (pagina - 1) * por_pagina
    calculos_pagina = calculos[inicio:inicio + por_pagina]
    
    return BusquedaCalculosResponse(
        calculos=calculos_pagina,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=(total + por_pagina - 1) // por_pagina
    )


@router.delete(
    "/{calculo_id}",
    status_code=204,
    summary="Eliminar cálculo",
    description="Elimina un cálculo de plusvalía"
)
async def eliminar_calculo(calculo_id: str = Path(...)):
    """Elimina un cálculo"""
    calculo = _service.obtener_calculo(calculo_id)
    if not calculo:
        raise HTTPException(status_code=404, detail=f"Cálculo no encontrado: {calculo_id}")
    del _service._calculos_cache[calculo.id]
    return None


# =============================================================================
# ENDPOINTS - PROYECCIONES
# =============================================================================

@router.post(
    "/{calculo_id}/proyectar",
    response_model=List[EscenarioProyeccionResponse],
    summary="Proyectar plusvalía",
    description="Genera proyecciones de plusvalía bajo múltiples escenarios"
)
async def proyectar_plusvalia(
    calculo_id: str = Path(...),
    request: ProyectarPlusvaliaRequest = None
):
    """Proyecta plusvalía futura"""
    calculo = _service.obtener_calculo(calculo_id)
    if not calculo:
        raise HTTPException(status_code=404, detail=f"Cálculo no encontrado: {calculo_id}")
    
    if calculo.proyecciones:
        return calculo.proyecciones
    
    # Generar proyecciones si no existen
    valor_actual = calculo.plusvalia_historica.valor_actual_uf
    horizonte = request.horizonte_anos if request else 5
    
    proyecciones = []
    escenarios_config = {
        EscenarioProyeccion.CONSERVADOR: {"tasa": 2.5, "desc": "Crecimiento moderado"},
        EscenarioProyeccion.BASE: {"tasa": 4.5, "desc": "Crecimiento histórico"},
        EscenarioProyeccion.OPTIMISTA: {"tasa": 7.0, "desc": "Alto crecimiento"},
    }
    
    for escenario, config in escenarios_config.items():
        tasa = (request.tasa_plusvalia_anual_pct if request and request.tasa_plusvalia_anual_pct else config["tasa"]) / 100
        proy_anos = []
        
        for a in range(1, horizonte + 1):
            valor_ano = valor_actual * ((1 + tasa) ** a)
            proy_anos.append(ProyeccionAnualResponse(
                ano=a,
                fecha=date(date.today().year + a, 1, 1),
                valor_estimado_uf=round(valor_ano, 2),
                plusvalia_acumulada_uf=round(valor_ano - valor_actual, 2),
                plusvalia_acumulada_pct=round((valor_ano / valor_actual - 1) * 100, 2),
                plusvalia_ano_uf=round(valor_ano * tasa, 2),
                plusvalia_ano_pct=round(tasa * 100, 2)
            ))
        
        proyecciones.append(EscenarioProyeccionResponse(
            escenario=escenario,
            descripcion=config["desc"],
            tasa_anual_asumida_pct=tasa * 100,
            proyecciones=proy_anos,
            valor_final_uf=proy_anos[-1].valor_estimado_uf,
            plusvalia_total_uf=proy_anos[-1].plusvalia_acumulada_uf,
            plusvalia_total_pct=proy_anos[-1].plusvalia_acumulada_pct,
            cagr_pct=tasa * 100
        ))
    
    return proyecciones


# =============================================================================
# ENDPOINTS - SIMULACIONES
# =============================================================================

@router.post(
    "/{calculo_id}/simular-venta",
    response_model=SimulacionVentaResponse,
    summary="Simular venta",
    description="Simula una venta y calcula neto a recibir después de impuestos"
)
async def simular_venta(
    calculo_id: str = Path(...),
    request: SimularVentaRequest = None
):
    """Simula venta del inmueble"""
    calculo = _service.obtener_calculo(calculo_id)
    if not calculo:
        raise HTTPException(status_code=404, detail=f"Cálculo no encontrado: {calculo_id}")
    
    precio = request.precio_venta_uf if request else calculo.plusvalia_historica.valor_actual_uf
    fecha = request.fecha_venta if request else date.today()
    gastos_pct = request.gastos_venta_pct if request else 3.0
    comision_pct = request.comision_corretaje_pct if request else 2.0
    
    gastos = precio * (gastos_pct + comision_pct) / 100
    precio_neto = precio - gastos
    costo_trib = calculo.costo_tributario.costo_tributario_final_uf
    ganancia_bruta = precio_neto - costo_trib
    
    # Impuesto (10% tasa única)
    impuesto = max(0, ganancia_bruta * 0.10) if ganancia_bruta > 0 else 0
    ganancia_neta = ganancia_bruta - impuesto
    neto = precio_neto - impuesto
    
    # Rentabilidad
    inversion_inicial = calculo.plusvalia_historica.valor_adquisicion_uf
    rentabilidad_total = ((neto / inversion_inicial) - 1) * 100
    anos = calculo.plusvalia_historica.anos_transcurridos
    rentabilidad_anual = ((neto / inversion_inicial) ** (1 / max(anos, 0.1)) - 1) * 100
    
    recomendaciones = []
    if ganancia_bruta > 0:
        if calculo.plusvalia_historica.anos_transcurridos < 1:
            recomendaciones.append("⚠️ Considere esperar al menos 1 año para beneficio DFL2")
        if ganancia_bruta > 8000:
            recomendaciones.append("💡 Evalúe opción IGC vs tasa única 10%")
    else:
        recomendaciones.append("❌ Venta generaría pérdida. Considere esperar mejor momento")
    
    return SimulacionVentaResponse(
        calculo_id=calculo.id,
        precio_venta_uf=precio,
        fecha_venta=fecha,
        gastos_venta_uf=round(gastos, 2),
        precio_neto_uf=round(precio_neto, 2),
        costo_tributario_uf=round(costo_trib, 2),
        ganancia_bruta_uf=round(ganancia_bruta, 2),
        ganancia_neta_uf=round(ganancia_neta, 2),
        impuesto_estimado_uf=round(impuesto, 2),
        neto_a_recibir_uf=round(neto, 2),
        rentabilidad_total_pct=round(rentabilidad_total, 2),
        rentabilidad_anual_pct=round(rentabilidad_anual, 2),
        recomendaciones=recomendaciones
    )


# =============================================================================
# ENDPOINTS - BENCHMARKS Y COMPARACIONES
# =============================================================================

@router.get(
    "/benchmark/{comuna}",
    response_model=BenchmarkComunaResponse,
    summary="Benchmark comuna",
    description="Obtiene benchmark de plusvalía de una comuna"
)
async def obtener_benchmark_comuna(
    comuna: str = Path(..., min_length=2, max_length=100)
):
    """Obtiene benchmark de una comuna"""
    benchmark = _service.obtener_benchmark(comuna)
    if not benchmark:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos de benchmark para comuna: {comuna}"
        )
    return benchmark


@router.post(
    "/comparar-comunas",
    response_model=ComparacionComunasResponse,
    summary="Comparar comunas",
    description="Compara plusvalía entre múltiples comunas"
)
async def comparar_comunas(request: CompararComunasRequest):
    """Compara plusvalía entre comunas"""
    comunas_data = []
    
    for comuna in request.comunas:
        bm = _service.obtener_benchmark(comuna)
        if bm:
            comunas_data.append(bm)
    
    if len(comunas_data) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 comunas con datos disponibles"
        )
    
    # Ranking
    ranking = sorted(
        [{"comuna": c.comuna, "plusvalia_5a": c.plusvalia_5_anos_pct} for c in comunas_data],
        key=lambda x: x["plusvalia_5a"],
        reverse=True
    )
    
    return ComparacionComunasResponse(
        comunas=comunas_data,
        ranking=ranking,
        mejor_plusvalia=ranking[0]["comuna"],
        peor_plusvalia=ranking[-1]["comuna"],
        diferencia_max_pct=round(ranking[0]["plusvalia_5a"] - ranking[-1]["plusvalia_5a"], 2),
        recomendacion=f"Mayor potencial de valorización en {ranking[0]['comuna']}"
    )


@router.get(
    "/ranking/comunas",
    summary="Ranking comunas",
    description="Obtiene ranking de comunas por plusvalía"
)
async def ranking_comunas(
    region: str = Query("Metropolitana"),
    top_n: int = Query(10, ge=5, le=50)
):
    """Obtiene ranking de comunas"""
    ranking = sorted(
        [
            {
                "comuna": comuna,
                "plusvalia_5_anos_pct": data["plusvalia_5a"],
                "plusvalia_anual_pct": data["anual"],
                "precio_m2_uf": data["precio_m2"]
            }
            for comuna, data in _service._benchmarks.items()
        ],
        key=lambda x: x["plusvalia_5_anos_pct"],
        reverse=True
    )[:top_n]
    
    return {
        "region": region,
        "fecha_datos": date.today().isoformat(),
        "ranking": ranking,
        "promedio_region_pct": round(sum(r["plusvalia_anual_pct"] for r in ranking) / len(ranking), 2)
    }


# =============================================================================
# ENDPOINTS - CALCULADORAS
# =============================================================================

@router.get(
    "/calculadora/costo-tributario",
    summary="Calcular costo tributario",
    description="Calcula costo tributario para venta según Ley 21.210"
)
async def calcular_costo_tributario(
    precio_adquisicion_uf: float = Query(..., gt=0),
    fecha_adquisicion: date = Query(...),
    gastos_adquisicion_uf: float = Query(0, ge=0),
    mejoras_uf: float = Query(0, ge=0)
):
    """Calcula costo tributario"""
    costo_base = precio_adquisicion_uf + gastos_adquisicion_uf + mejoras_uf
    anos = (date.today() - fecha_adquisicion).days / 365.25
    
    # Ajustes IPC simplificados
    if fecha_adquisicion.year <= 2014:
        ajuste = costo_base * 0.35  # Ajuste estimado
    else:
        ajuste = costo_base * (anos * 0.03)  # ~3% anual
    
    costo_final = costo_base + ajuste
    
    return {
        "costo_base_uf": round(costo_base, 2),
        "anos_posesion": round(anos, 1),
        "ajuste_ipc_estimado_uf": round(ajuste, 2),
        "costo_tributario_final_uf": round(costo_final, 2),
        "factor_ajuste": round(costo_final / costo_base, 4),
        "normativa": "Ley 21.210 - Art. 17 N°8 letra b)"
    }


@router.get(
    "/calculadora/impuesto-ganancia",
    summary="Calcular impuesto ganancia capital",
    description="Calcula impuesto sobre ganancia de capital"
)
async def calcular_impuesto_ganancia(
    ganancia_capital_uf: float = Query(..., description="Ganancia de capital en UF"),
    tasa_marginal_igc_pct: float = Query(35.0, ge=0, le=40),
    aplica_dfl2: bool = Query(False),
    anos_posesion: float = Query(1, ge=0)
):
    """Calcula impuesto sobre ganancia de capital"""
    if aplica_dfl2 and anos_posesion >= 1:
        return {
            "ganancia_capital_uf": ganancia_capital_uf,
            "exenta": True,
            "motivo": "Beneficio DFL2 con más de 1 año de posesión",
            "impuesto_uf": 0,
            "tasa_efectiva_pct": 0
        }
    
    # Opción 1: IGC
    impuesto_igc = ganancia_capital_uf * (tasa_marginal_igc_pct / 100)
    
    # Opción 2: Tasa única 10%
    impuesto_unico = ganancia_capital_uf * 0.10
    
    mejor_opcion = "IGC" if impuesto_igc < impuesto_unico else "Tasa única 10%"
    impuesto_menor = min(impuesto_igc, impuesto_unico)
    
    return {
        "ganancia_capital_uf": ganancia_capital_uf,
        "exenta": False,
        "opcion_igc": {
            "tasa_pct": tasa_marginal_igc_pct,
            "impuesto_uf": round(impuesto_igc, 2)
        },
        "opcion_tasa_unica": {
            "tasa_pct": 10.0,
            "impuesto_uf": round(impuesto_unico, 2)
        },
        "recomendacion": mejor_opcion,
        "impuesto_menor_uf": round(impuesto_menor, 2),
        "ahorro_uf": round(abs(impuesto_igc - impuesto_unico), 2),
        "tasa_efectiva_pct": round((impuesto_menor / ganancia_capital_uf) * 100, 2)
    }


# =============================================================================
# ENDPOINTS - ESTADÍSTICAS
# =============================================================================

@router.get(
    "/estadisticas",
    response_model=EstadisticasPlusvaliaResponse,
    summary="Estadísticas de plusvalías",
    description="Obtiene estadísticas agregadas de cálculos de plusvalía"
)
async def obtener_estadisticas(
    usuario_id: Optional[str] = Query(None)
):
    """Obtiene estadísticas de plusvalías"""
    calculos = list(_service._calculos_cache.values())
    
    if usuario_id:
        calculos = [c for c in calculos if c.usuario_id == usuario_id]
    
    if not calculos:
        return EstadisticasPlusvaliaResponse(
            total_calculos=0,
            por_tipo_activo={},
            por_comuna={},
            plusvalia_promedio_pct=0,
            plusvalia_mediana_pct=0,
            mayor_plusvalia={},
            menor_plusvalia={},
            tendencia_mensual=[]
        )
    
    # Contar por tipo y comuna
    por_tipo = {}
    por_comuna = {}
    plusvalias = []
    
    for c in calculos:
        por_tipo[c.tipo_activo.value] = por_tipo.get(c.tipo_activo.value, 0) + 1
        por_comuna[c.comuna] = por_comuna.get(c.comuna, 0) + 1
        plusvalias.append(c.plusvalia_historica.plusvalia_pct)
    
    plusvalias.sort()
    
    mayor = max(calculos, key=lambda x: x.plusvalia_historica.plusvalia_pct)
    menor = min(calculos, key=lambda x: x.plusvalia_historica.plusvalia_pct)
    
    return EstadisticasPlusvaliaResponse(
        total_calculos=len(calculos),
        por_tipo_activo=por_tipo,
        por_comuna=por_comuna,
        plusvalia_promedio_pct=round(sum(plusvalias) / len(plusvalias), 2),
        plusvalia_mediana_pct=round(plusvalias[len(plusvalias) // 2], 2),
        mayor_plusvalia={
            "id": mayor.id,
            "direccion": mayor.direccion,
            "plusvalia_pct": mayor.plusvalia_historica.plusvalia_pct
        },
        menor_plusvalia={
            "id": menor.id,
            "direccion": menor.direccion,
            "plusvalia_pct": menor.plusvalia_historica.plusvalia_pct
        },
        tendencia_mensual=[]
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get(
    "/health",
    summary="Health check",
    description="Verifica estado del módulo de plusvalía"
)
async def health_check():
    """Verifica estado del módulo"""
    return {
        "status": "healthy",
        "modulo": "M06B - Plusvalía y Ganancias de Capital",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "calculos_en_cache": len(_service._calculos_cache),
        "comunas_benchmark": len(_service._benchmarks),
        "endpoints_activos": 22,
        "normativa": [
            "Ley 21.210",
            "Ley 21.713",
            "Circular SII 42/2020",
            "NCh 2728:2015"
        ]
    }
