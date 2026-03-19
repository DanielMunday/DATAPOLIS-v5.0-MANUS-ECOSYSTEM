# -*- coding: utf-8 -*-
"""
DATAPOLIS v3.0 - Schemas Indicadores Económicos
================================================
Modelos Pydantic para IE (Indicadores Económicos)
Fuente: Banco Central de Chile (BCCh)
Versión: 3.0.0
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from .base import BaseSchema, ResponseBase


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoIndicador(str, Enum):
    """Tipos de indicadores económicos BCCh"""
    UF = "uf"
    DOLAR = "dolar"
    EURO = "euro"
    IPC = "ipc"
    UTM = "utm"
    IVP = "ivp"
    IMACEC = "imacec"
    TPM = "tpm"
    TAB = "tab"
    LIBOR = "libor"


class FrecuenciaIndicador(str, Enum):
    """Frecuencia de actualización"""
    DIARIA = "diaria"
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"


class TendenciaIndicador(str, Enum):
    """Tendencia del indicador"""
    ALZA = "alza"
    BAJA = "baja"
    ESTABLE = "estable"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class IndicadorRequest(BaseSchema):
    """Request para obtener indicador específico"""
    tipo: TipoIndicador
    fecha: Optional[date] = Field(None, description="Fecha específica (default: hoy)")


class IndicadoresRangoRequest(BaseSchema):
    """Request para obtener indicadores en rango de fechas"""
    tipos: List[TipoIndicador] = Field(
        default=[TipoIndicador.UF, TipoIndicador.DOLAR],
        description="Indicadores a consultar"
    )
    fecha_inicio: date
    fecha_fin: date
    
    @field_validator("fecha_fin")
    @classmethod
    def validate_rango(cls, v, info):
        if info.data.get("fecha_inicio") and v < info.data["fecha_inicio"]:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return v


class ConversionMonedaRequest(BaseSchema):
    """Request para conversión de moneda"""
    monto: Decimal = Field(..., gt=0, description="Monto a convertir")
    moneda_origen: TipoIndicador = Field(..., description="Moneda de origen")
    moneda_destino: TipoIndicador = Field(..., description="Moneda destino")
    fecha: Optional[date] = Field(None, description="Fecha para tipo de cambio")


class ProyeccionRequest(BaseSchema):
    """Request para proyección de indicador"""
    tipo: TipoIndicador
    horizonte_meses: int = Field(default=12, ge=1, le=60)
    incluir_intervalos_confianza: bool = True
    nivel_confianza: float = Field(default=0.95, ge=0.8, le=0.99)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ValorIndicador(BaseSchema):
    """Valor de un indicador en fecha específica"""
    tipo: TipoIndicador
    nombre: str
    valor: Decimal
    unidad: str
    fecha: date
    
    # Variaciones
    variacion_diaria: Optional[Decimal] = None
    variacion_diaria_pct: Optional[Decimal] = None
    variacion_mensual: Optional[Decimal] = None
    variacion_mensual_pct: Optional[Decimal] = None
    variacion_anual: Optional[Decimal] = None
    variacion_anual_pct: Optional[Decimal] = None
    
    # Metadata
    fuente: str = "BCCh"
    ultima_actualizacion: datetime


class SerieIndicador(BaseSchema):
    """Serie temporal de indicador"""
    tipo: TipoIndicador
    nombre: str
    unidad: str
    frecuencia: FrecuenciaIndicador
    
    # Datos
    valores: List[Dict[str, any]] = Field(
        ...,
        description="Lista de {fecha, valor}"
    )
    
    # Estadísticas
    minimo: Decimal
    maximo: Decimal
    promedio: Decimal
    desviacion_std: Decimal
    tendencia: TendenciaIndicador
    
    # Período
    fecha_inicio: date
    fecha_fin: date
    total_registros: int


class ResultadoConversion(BaseSchema):
    """Resultado de conversión de moneda"""
    monto_origen: Decimal
    moneda_origen: str
    monto_destino: Decimal
    moneda_destino: str
    
    tipo_cambio: Decimal
    fecha_tipo_cambio: date
    
    # Detalle
    tasa_conversion: Decimal
    comision_estimada: Optional[Decimal] = None


class ProyeccionIndicador(BaseSchema):
    """Proyección de indicador económico"""
    tipo: TipoIndicador
    nombre: str
    
    # Proyecciones
    proyecciones: List[Dict[str, any]] = Field(
        ...,
        description="Lista de {fecha, valor_proyectado, limite_inferior, limite_superior}"
    )
    
    # Modelo
    modelo: str = Field(default="ARIMA", description="Modelo utilizado")
    parametros_modelo: Dict[str, any] = {}
    
    # Métricas
    mape: float = Field(..., description="Mean Absolute Percentage Error")
    rmse: float = Field(..., description="Root Mean Square Error")
    r2: float = Field(..., description="R-squared")
    
    # Confianza
    nivel_confianza: float
    
    # Riesgos
    escenario_optimista: Optional[Decimal] = None
    escenario_pesimista: Optional[Decimal] = None
    factores_riesgo: List[str] = []


class ResumenIndicadores(BaseSchema):
    """Resumen de indicadores principales"""
    fecha: date
    
    # Indicadores principales
    uf: ValorIndicador
    dolar: ValorIndicador
    euro: ValorIndicador
    utm: ValorIndicador
    
    # Tasas
    tpm: Optional[ValorIndicador] = None
    tab_30: Optional[ValorIndicador] = None
    
    # Inflación
    ipc_mensual: Optional[ValorIndicador] = None
    ipc_acumulado: Optional[ValorIndicador] = None
    
    # Actividad
    imacec: Optional[ValorIndicador] = None
    
    # Alertas
    alertas: List[str] = []


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

class IndicadorResponse(ResponseBase[ValorIndicador]):
    """Respuesta con indicador único"""
    pass


class IndicadoresListResponse(ResponseBase[List[ValorIndicador]]):
    """Respuesta con lista de indicadores"""
    pass


class SerieResponse(ResponseBase[SerieIndicador]):
    """Respuesta con serie temporal"""
    pass


class ConversionResponse(ResponseBase[ResultadoConversion]):
    """Respuesta de conversión"""
    pass


class ProyeccionResponse(ResponseBase[ProyeccionIndicador]):
    """Respuesta de proyección"""
    pass


class ResumenResponse(ResponseBase[ResumenIndicadores]):
    """Respuesta con resumen"""
    pass


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "TipoIndicador",
    "FrecuenciaIndicador",
    "TendenciaIndicador",
    
    # Requests
    "IndicadorRequest",
    "IndicadoresRangoRequest",
    "ConversionMonedaRequest",
    "ProyeccionRequest",
    
    # Data schemas
    "ValorIndicador",
    "SerieIndicador",
    "ResultadoConversion",
    "ProyeccionIndicador",
    "ResumenIndicadores",
    
    # Responses
    "IndicadorResponse",
    "IndicadoresListResponse",
    "SerieResponse",
    "ConversionResponse",
    "ProyeccionResponse",
    "ResumenResponse",
]
