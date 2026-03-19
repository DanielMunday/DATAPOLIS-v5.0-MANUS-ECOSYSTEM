# ============================================================================
# DATAPOLIS v3.0 - ROUTER M10 REPORTES Y BUSINESS INTELLIGENCE
# ============================================================================
# Dashboards, KPIs, reportes automatizados, análisis predictivo
# Cumplimiento CMF, SII, benchmarking
# ============================================================================

from fastapi import APIRouter, HTTPException, Query, Path, Body, BackgroundTasks
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum
import json

router = APIRouter(prefix="/reportes", tags=["M10 - Reportes y BI"])

# ============================================================================
# ENUMS
# ============================================================================

class TipoReporte(str, Enum):
    BALANCE_GENERAL = "balance_general"
    ESTADO_RESULTADOS = "estado_resultados"
    FLUJO_CAJA = "flujo_caja"
    PRESUPUESTO_VS_REAL = "presupuesto_vs_real"
    MOROSIDAD = "morosidad"
    OCUPACION = "ocupacion"
    MANTENCIONES = "mantenciones"
    ARRIENDOS = "arriendos"
    CMF_MENSUAL = "cmf_mensual"
    CMF_ANUAL = "cmf_anual"
    SII_F29 = "sii_f29"
    TENDENCIAS = "tendencias"
    PROYECCIONES = "proyecciones"
    BENCHMARKING = "benchmarking"
    RESUMEN_EJECUTIVO = "resumen_ejecutivo"
    DASHBOARD_KPI = "dashboard_kpi"

class FormatoExportacion(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    POWERPOINT = "powerpoint"

class Periodicidad(str, Enum):
    DIARIO = "diario"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"

class CategoriaKPI(str, Enum):
    FINANCIERO = "financiero"
    OPERACIONAL = "operacional"
    COMERCIAL = "comercial"
    SATISFACCION = "satisfaccion"
    CUMPLIMIENTO = "cumplimiento"
    RIESGO = "riesgo"

class NivelAlerta(str, Enum):
    CRITICO = "critico"
    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"
    NORMAL = "normal"

class TipoGrafico(str, Enum):
    LINEA = "linea"
    BARRA = "barra"
    TORTA = "torta"
    AREA = "area"
    GAUGE = "gauge"
    TREEMAP = "treemap"
    HEATMAP = "mapa_calor"

# ============================================================================
# SCHEMAS
# ============================================================================

class KPIConfig(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    categoria: CategoriaKPI
    unidad: str
    formula: str
    meta: float
    umbral_critico: float
    umbral_alto: float
    umbral_medio: float

class DashboardCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo: str = "general"
    widgets: List[Dict[str, Any]] = []
    filtros: Dict[str, Any] = {}
    publico: bool = False

class WidgetConfig(BaseModel):
    tipo: str
    titulo: str
    kpi_codigo: Optional[str] = None
    configuracion: Dict[str, Any] = {}
    posicion: Dict[str, int] = {"x": 0, "y": 0, "w": 4, "h": 3}

class ReporteProgramadoCreate(BaseModel):
    nombre: str
    tipo_reporte: TipoReporte
    periodicidad: Periodicidad
    formato: FormatoExportacion = FormatoExportacion.PDF
    destinatarios: List[str] = []
    parametros: Dict[str, Any] = {}
    copropiedad_id: Optional[str] = None

class ReporteRequest(BaseModel):
    tipo: TipoReporte
    formato: FormatoExportacion = FormatoExportacion.JSON
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    copropiedad_id: Optional[str] = None
    parametros: Dict[str, Any] = {}

# ============================================================================
# KPIs ESTÁNDAR DATAPOLIS
# ============================================================================

KPIS_ESTANDAR = [
    {
        "codigo": "FIN-001",
        "nombre": "Tasa Morosidad",
        "descripcion": "Porcentaje de unidades con pagos atrasados",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(unidades_morosas / total_unidades) * 100",
        "meta": 5.0,
        "umbral_critico": 15.0,
        "umbral_alto": 10.0,
        "umbral_medio": 7.0,
        "menor_es_mejor": True
    },
    {
        "codigo": "FIN-002",
        "nombre": "Recaudación Efectiva",
        "descripcion": "Porcentaje de cobros efectivos vs emitidos",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(cobros_efectivos / cobros_emitidos) * 100",
        "meta": 95.0,
        "umbral_critico": 80.0,
        "umbral_alto": 85.0,
        "umbral_medio": 90.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "FIN-003",
        "nombre": "Ratio Fondo Reserva",
        "descripcion": "Meses de gastos cubiertos por fondo reserva",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "meses",
        "formula": "fondo_reserva / gastos_mensuales",
        "meta": 6.0,
        "umbral_critico": 1.0,
        "umbral_alto": 2.0,
        "umbral_medio": 4.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "FIN-004",
        "nombre": "Ejecución Presupuestaria",
        "descripcion": "Porcentaje de ejecución vs presupuesto",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(gastos_reales / gastos_presupuestados) * 100",
        "meta": 100.0,
        "umbral_critico": 120.0,
        "umbral_alto": 110.0,
        "umbral_medio": 105.0,
        "menor_es_mejor": True
    },
    {
        "codigo": "OPE-001",
        "nombre": "Tiempo Resolución Mantenciones",
        "descripcion": "Promedio días para resolver mantenciones",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "días",
        "formula": "promedio(dias_resolucion)",
        "meta": 3.0,
        "umbral_critico": 10.0,
        "umbral_alto": 7.0,
        "umbral_medio": 5.0,
        "menor_es_mejor": True
    },
    {
        "codigo": "OPE-002",
        "nombre": "Tasa Ocupación",
        "descripcion": "Porcentaje de unidades ocupadas",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "%",
        "formula": "(unidades_ocupadas / total_unidades) * 100",
        "meta": 95.0,
        "umbral_critico": 80.0,
        "umbral_alto": 85.0,
        "umbral_medio": 90.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "OPE-003",
        "nombre": "Mantenciones Preventivas",
        "descripcion": "Porcentaje mantenciones preventivas vs total",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "%",
        "formula": "(mantenciones_preventivas / total_mantenciones) * 100",
        "meta": 70.0,
        "umbral_critico": 30.0,
        "umbral_alto": 40.0,
        "umbral_medio": 50.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "SAT-001",
        "nombre": "NPS Residentes",
        "descripcion": "Net Promoter Score de residentes",
        "categoria": CategoriaKPI.SATISFACCION,
        "unidad": "puntos",
        "formula": "promotores - detractores",
        "meta": 50.0,
        "umbral_critico": 0.0,
        "umbral_alto": 20.0,
        "umbral_medio": 35.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "CUM-001",
        "nombre": "Cumplimiento CMF",
        "descripcion": "Porcentaje de requisitos CMF cumplidos",
        "categoria": CategoriaKPI.CUMPLIMIENTO,
        "unidad": "%",
        "formula": "(requisitos_cumplidos / total_requisitos) * 100",
        "meta": 100.0,
        "umbral_critico": 70.0,
        "umbral_alto": 80.0,
        "umbral_medio": 90.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "CUM-002",
        "nombre": "Declaraciones SII",
        "descripcion": "Porcentaje declaraciones presentadas a tiempo",
        "categoria": CategoriaKPI.CUMPLIMIENTO,
        "unidad": "%",
        "formula": "(declaraciones_tiempo / total_declaraciones) * 100",
        "meta": 100.0,
        "umbral_critico": 80.0,
        "umbral_alto": 90.0,
        "umbral_medio": 95.0,
        "menor_es_mejor": False
    },
    {
        "codigo": "RIE-001",
        "nombre": "Score Riesgo General",
        "descripcion": "Índice compuesto de riesgo operacional",
        "categoria": CategoriaKPI.RIESGO,
        "unidad": "puntos",
        "formula": "modelo_scoring_riesgo",
        "meta": 80.0,
        "umbral_critico": 40.0,
        "umbral_alto": 55.0,
        "umbral_medio": 70.0,
        "menor_es_mejor": False
    }
]

# ============================================================================
# STORAGE EN MEMORIA (producción usar PostgreSQL)
# ============================================================================

kpis_db: Dict[str, Dict] = {kpi["codigo"]: kpi for kpi in KPIS_ESTANDAR}
kpi_valores_db: Dict[str, Dict] = {}
dashboards_db: Dict[str, Dict] = {}
reportes_programados_db: Dict[str, Dict] = {}
reportes_generados_db: Dict[str, Dict] = {}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generar_id() -> str:
    """Genera ID único"""
    import uuid
    return str(uuid.uuid4())[:8]

def evaluar_nivel_alerta(valor: float, kpi: Dict) -> NivelAlerta:
    """Evalúa nivel de alerta según umbrales"""
    menor_es_mejor = kpi.get("menor_es_mejor", False)
    
    if menor_es_mejor:
        if valor >= kpi["umbral_critico"]:
            return NivelAlerta.CRITICO
        elif valor >= kpi["umbral_alto"]:
            return NivelAlerta.ALTO
        elif valor >= kpi["umbral_medio"]:
            return NivelAlerta.MEDIO
        elif valor > kpi["meta"]:
            return NivelAlerta.BAJO
        else:
            return NivelAlerta.NORMAL
    else:
        if valor <= kpi["umbral_critico"]:
            return NivelAlerta.CRITICO
        elif valor <= kpi["umbral_alto"]:
            return NivelAlerta.ALTO
        elif valor <= kpi["umbral_medio"]:
            return NivelAlerta.MEDIO
        elif valor < kpi["meta"]:
            return NivelAlerta.BAJO
        else:
            return NivelAlerta.NORMAL

def calcular_tendencia(valores: List[float]) -> str:
    """Calcula tendencia basada en valores históricos"""
    if len(valores) < 2:
        return "estable"
    
    diferencia = valores[-1] - valores[0]
    umbral = abs(valores[0] * 0.05) if valores[0] != 0 else 0.1
    
    if diferencia > umbral:
        return "creciente"
    elif diferencia < -umbral:
        return "decreciente"
    else:
        return "estable"

def calcular_proxima_ejecucion(periodicidad: Periodicidad) -> datetime:
    """Calcula próxima ejecución según periodicidad"""
    ahora = datetime.now()
    
    incrementos = {
        Periodicidad.DIARIO: timedelta(days=1),
        Periodicidad.SEMANAL: timedelta(weeks=1),
        Periodicidad.QUINCENAL: timedelta(days=15),
        Periodicidad.MENSUAL: timedelta(days=30),
        Periodicidad.TRIMESTRAL: timedelta(days=90),
        Periodicidad.SEMESTRAL: timedelta(days=180),
        Periodicidad.ANUAL: timedelta(days=365)
    }
    
    return ahora + incrementos.get(periodicidad, timedelta(days=30))

# ============================================================================
# ENDPOINTS KPIs
# ============================================================================

@router.get("/kpis")
async def listar_kpis(
    categoria: Optional[CategoriaKPI] = None,
    solo_alertas: bool = False
):
    """
    Listar todos los KPIs con sus valores actuales
    
    Filtros por categoría y estado de alerta
    """
    resultado = []
    
    for codigo, kpi in kpis_db.items():
        if categoria and kpi["categoria"] != categoria:
            continue
        
        # Obtener valor actual
        valor_actual = kpi_valores_db.get(codigo, {})
        nivel_alerta = evaluar_nivel_alerta(
            valor_actual.get("valor", 0),
            kpi
        ) if valor_actual else NivelAlerta.NORMAL
        
        if solo_alertas and nivel_alerta == NivelAlerta.NORMAL:
            continue
        
        resultado.append({
            **kpi,
            "valor_actual": valor_actual.get("valor", 0),
            "valor_anterior": valor_actual.get("valor_anterior", 0),
            "variacion_pct": valor_actual.get("variacion_pct", 0),
            "tendencia": valor_actual.get("tendencia", "estable"),
            "nivel_alerta": nivel_alerta.value,
            "ultima_actualizacion": valor_actual.get("fecha", None)
        })
    
    # Resumen
    alertas_criticas = len([k for k in resultado if k["nivel_alerta"] == "critico"])
    alertas_altas = len([k for k in resultado if k["nivel_alerta"] == "alto"])
    
    return {
        "kpis": resultado,
        "total": len(resultado),
        "resumen_alertas": {
            "criticas": alertas_criticas,
            "altas": alertas_altas,
            "total_alertas": alertas_criticas + alertas_altas
        }
    }

@router.get("/kpis/{codigo}")
async def obtener_kpi(codigo: str = Path(...)):
    """Obtener detalle de un KPI específico"""
    if codigo not in kpis_db:
        raise HTTPException(404, "KPI no encontrado")
    
    kpi = kpis_db[codigo]
    valor_actual = kpi_valores_db.get(codigo, {})
    
    # Simular histórico
    historico = [
        {"fecha": (datetime.now() - timedelta(days=i*30)).isoformat(), "valor": valor_actual.get("valor", 0) * (1 + (i * 0.02))}
        for i in range(6, 0, -1)
    ]
    
    return {
        **kpi,
        "valor_actual": valor_actual.get("valor", 0),
        "nivel_alerta": evaluar_nivel_alerta(valor_actual.get("valor", 0), kpi).value,
        "historico": historico,
        "configuracion_grafico": {
            "tipo": TipoGrafico.LINEA.value,
            "color_meta": "#22c55e",
            "color_critico": "#ef4444",
            "mostrar_meta": True,
            "mostrar_umbrales": True
        }
    }

@router.put("/kpis/{codigo}/valor")
async def actualizar_valor_kpi(
    codigo: str = Path(...),
    valor: float = Body(..., embed=True)
):
    """Actualizar valor de un KPI"""
    if codigo not in kpis_db:
        raise HTTPException(404, "KPI no encontrado")
    
    kpi = kpis_db[codigo]
    valor_anterior = kpi_valores_db.get(codigo, {}).get("valor", 0)
    
    variacion = ((valor - valor_anterior) / valor_anterior * 100) if valor_anterior != 0 else 0
    
    kpi_valores_db[codigo] = {
        "valor": valor,
        "valor_anterior": valor_anterior,
        "variacion_pct": round(variacion, 2),
        "tendencia": "creciente" if variacion > 0 else "decreciente" if variacion < 0 else "estable",
        "fecha": datetime.now().isoformat()
    }
    
    nivel_alerta = evaluar_nivel_alerta(valor, kpi)
    
    return {
        "mensaje": "KPI actualizado",
        "codigo": codigo,
        "valor": valor,
        "nivel_alerta": nivel_alerta.value,
        "variacion_pct": round(variacion, 2)
    }

# ============================================================================
# ENDPOINTS DASHBOARDS
# ============================================================================

@router.post("/dashboards")
async def crear_dashboard(data: DashboardCreate):
    """Crear nuevo dashboard personalizado"""
    dashboard_id = generar_id()
    
    dashboard = {
        "id": dashboard_id,
        **data.dict(),
        "creado_en": datetime.now().isoformat(),
        "actualizado_en": datetime.now().isoformat()
    }
    dashboards_db[dashboard_id] = dashboard
    
    return {"mensaje": "Dashboard creado", "dashboard_id": dashboard_id, "dashboard": dashboard}

@router.get("/dashboards")
async def listar_dashboards():
    """Listar dashboards disponibles"""
    return {"dashboards": list(dashboards_db.values()), "total": len(dashboards_db)}

@router.get("/dashboards/{dashboard_id}")
async def obtener_dashboard(dashboard_id: str = Path(...)):
    """Obtener dashboard con datos actualizados"""
    if dashboard_id not in dashboards_db:
        raise HTTPException(404, "Dashboard no encontrado")
    
    dashboard = dashboards_db[dashboard_id]
    
    # Obtener datos de cada widget
    widgets_con_datos = []
    for widget in dashboard.get("widgets", []):
        datos_widget = await generar_datos_widget(widget)
        widgets_con_datos.append({**widget, "datos": datos_widget})
    
    return {
        **dashboard,
        "widgets": widgets_con_datos,
        "ultima_actualizacion": datetime.now().isoformat()
    }

@router.post("/dashboards/{dashboard_id}/widgets")
async def agregar_widget(
    dashboard_id: str = Path(...),
    widget: WidgetConfig = Body(...)
):
    """Agregar widget a dashboard"""
    if dashboard_id not in dashboards_db:
        raise HTTPException(404, "Dashboard no encontrado")
    
    widget_data = {
        "id": generar_id(),
        **widget.dict()
    }
    
    dashboards_db[dashboard_id]["widgets"].append(widget_data)
    dashboards_db[dashboard_id]["actualizado_en"] = datetime.now().isoformat()
    
    return {"mensaje": "Widget agregado", "widget": widget_data}

async def generar_datos_widget(widget: Dict) -> Dict:
    """Genera datos para un widget según su tipo"""
    tipo = widget.get("tipo", "")
    
    if tipo == "kpi_card":
        codigo_kpi = widget.get("kpi_codigo")
        if codigo_kpi and codigo_kpi in kpis_db:
            kpi = kpis_db[codigo_kpi]
            valor = kpi_valores_db.get(codigo_kpi, {}).get("valor", 0)
            return {
                "valor": valor,
                "meta": kpi["meta"],
                "unidad": kpi["unidad"],
                "nivel_alerta": evaluar_nivel_alerta(valor, kpi).value,
                "tendencia": kpi_valores_db.get(codigo_kpi, {}).get("tendencia", "estable")
            }
    
    elif tipo == "chart_linea":
        return {
            "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
            "datasets": [
                {"label": "Actual", "data": [100, 105, 102, 110, 108, 115]},
                {"label": "Meta", "data": [100, 100, 100, 100, 100, 100]}
            ]
        }
    
    elif tipo == "chart_torta":
        return {
            "labels": ["Normal", "Bajo", "Medio", "Alto", "Crítico"],
            "data": [60, 15, 10, 10, 5],
            "colores": ["#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444"]
        }
    
    elif tipo == "tabla":
        return {
            "columnas": ["Indicador", "Valor", "Meta", "Estado"],
            "filas": [
                ["Morosidad", "8%", "5%", "Alto"],
                ["Ocupación", "94%", "95%", "Normal"],
                ["NPS", "45", "50", "Bajo"]
            ]
        }
    
    return {}

# ============================================================================
# ENDPOINTS DASHBOARD PRINCIPAL
# ============================================================================

@router.get("/dashboard-principal")
async def obtener_dashboard_principal(copropiedad_id: Optional[str] = None):
    """
    Dashboard principal con KPIs y métricas clave
    
    Vista ejecutiva con indicadores principales
    """
    # Calcular KPIs
    kpis_resultado = []
    alertas_criticas = []
    alertas_altas = []
    
    for codigo, kpi in kpis_db.items():
        valor = kpi_valores_db.get(codigo, {}).get("valor", kpi["meta"] * 0.9)  # Valor simulado
        nivel = evaluar_nivel_alerta(valor, kpi)
        
        kpi_data = {
            "codigo": codigo,
            "nombre": kpi["nombre"],
            "valor": valor,
            "meta": kpi["meta"],
            "unidad": kpi["unidad"],
            "nivel_alerta": nivel.value,
            "categoria": kpi["categoria"].value
        }
        kpis_resultado.append(kpi_data)
        
        if nivel == NivelAlerta.CRITICO:
            alertas_criticas.append(kpi_data)
        elif nivel == NivelAlerta.ALTO:
            alertas_altas.append(kpi_data)
    
    # Resumen financiero simulado
    resumen_financiero = {
        "ingresos_mes": 45000000,
        "gastos_mes": 38000000,
        "resultado_mes": 7000000,
        "fondo_reserva": 120000000,
        "cuentas_por_cobrar": 8500000,
        "variacion_ingresos": 5.2,
        "variacion_gastos": 3.1
    }
    
    # Resumen operacional simulado
    resumen_operacional = {
        "total_unidades": 120,
        "unidades_ocupadas": 113,
        "tasa_ocupacion": 94.2,
        "mantenciones_pendientes": 8,
        "mantenciones_vencidas": 2,
        "contratos_por_vencer": 5
    }
    
    return {
        "fecha_actualizacion": datetime.now().isoformat(),
        "kpis": kpis_resultado,
        "alertas": {
            "criticas": alertas_criticas,
            "altas": alertas_altas,
            "total_alertas": len(alertas_criticas) + len(alertas_altas)
        },
        "resumen_financiero": resumen_financiero,
        "resumen_operacional": resumen_operacional,
        "graficos": {
            "evolucion_mensual": {
                "labels": ["Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
                "ingresos": [42, 43, 44, 45, 44, 45],
                "gastos": [36, 37, 38, 38, 37, 38]
            },
            "distribucion_gastos": {
                "labels": ["Personal", "Servicios", "Mantención", "Administración", "Otros"],
                "valores": [35, 25, 20, 12, 8]
            }
        }
    }

# ============================================================================
# ENDPOINTS REPORTES
# ============================================================================

@router.post("/generar")
async def generar_reporte(data: ReporteRequest):
    """
    Generar reporte según tipo y parámetros
    
    Tipos disponibles:
    - Balance general
    - Estado de resultados
    - Morosidad
    - CMF mensual/anual
    - Resumen ejecutivo
    - Y más...
    """
    datos_reporte = await obtener_datos_reporte(data.tipo, data)
    
    reporte_id = generar_id()
    reporte = {
        "id": reporte_id,
        "tipo": data.tipo.value,
        "formato": data.formato.value,
        "periodo": {
            "inicio": data.fecha_inicio.isoformat() if data.fecha_inicio else None,
            "fin": data.fecha_fin.isoformat() if data.fecha_fin else None
        },
        "parametros": data.parametros,
        "datos": datos_reporte,
        "generado_en": datetime.now().isoformat()
    }
    reportes_generados_db[reporte_id] = reporte
    
    return {
        "mensaje": "Reporte generado",
        "reporte_id": reporte_id,
        "reporte": reporte
    }

async def obtener_datos_reporte(tipo: TipoReporte, params: ReporteRequest) -> Dict:
    """Obtiene datos según tipo de reporte"""
    
    if tipo == TipoReporte.RESUMEN_EJECUTIVO:
        return {
            "titulo": "Resumen Ejecutivo",
            "periodo": f"{params.fecha_inicio} a {params.fecha_fin}" if params.fecha_inicio else "Período actual",
            "situacion_financiera": {
                "ingresos_totales": 540000000,
                "gastos_totales": 456000000,
                "resultado_neto": 84000000,
                "fondo_reserva": 120000000,
                "morosidad_pct": 8.2
            },
            "indicadores_clave": [
                {"nombre": "Recaudación", "valor": 91.8, "unidad": "%", "estado": "aceptable"},
                {"nombre": "Ocupación", "valor": 94.2, "unidad": "%", "estado": "bueno"},
                {"nombre": "Satisfacción", "valor": 45, "unidad": "NPS", "estado": "aceptable"}
            ],
            "alertas_principales": [
                "Morosidad sobre meta (8.2% vs 5%)",
                "3 contratos de arriendo vencen próximo mes",
                "Mantenimiento preventivo bajo meta (58% vs 70%)"
            ],
            "recomendaciones": [
                "Intensificar gestión de cobranza en unidades morosas",
                "Iniciar renovación de contratos con anticipación",
                "Revisar plan de mantenimiento preventivo"
            ]
        }
    
    elif tipo == TipoReporte.MOROSIDAD:
        return {
            "titulo": "Reporte de Morosidad",
            "resumen": {
                "total_unidades": 120,
                "unidades_morosas": 10,
                "tasa_morosidad": 8.33,
                "monto_moroso_total": 8500000,
                "antiguedad_promedio": 45
            },
            "detalle_morosos": [
                {"unidad": "A-101", "propietario": "Juan Pérez", "monto": 450000, "dias": 60, "estado": "gestión judicial"},
                {"unidad": "B-205", "propietario": "María García", "monto": 225000, "dias": 30, "estado": "cobranza activa"},
                {"unidad": "C-308", "propietario": "Pedro López", "monto": 675000, "dias": 90, "estado": "convenio pago"}
            ],
            "evolucion_12_meses": [
                {"mes": "Ene", "tasa": 6.5}, {"mes": "Feb", "tasa": 6.8},
                {"mes": "Mar", "tasa": 7.2}, {"mes": "Abr", "tasa": 7.5},
                {"mes": "May", "tasa": 7.8}, {"mes": "Jun", "tasa": 8.0},
                {"mes": "Jul", "tasa": 8.2}, {"mes": "Ago", "tasa": 8.1},
                {"mes": "Sep", "tasa": 8.3}, {"mes": "Oct", "tasa": 8.2},
                {"mes": "Nov", "tasa": 8.4}, {"mes": "Dic", "tasa": 8.3}
            ],
            "por_antiguedad": {
                "0_30_dias": {"cantidad": 4, "monto": 900000},
                "31_60_dias": {"cantidad": 3, "monto": 1350000},
                "61_90_dias": {"cantidad": 2, "monto": 2250000},
                "mas_90_dias": {"cantidad": 1, "monto": 4000000}
            }
        }
    
    elif tipo == TipoReporte.CMF_MENSUAL:
        return {
            "titulo": "Reporte CMF Mensual - Ley 21.442",
            "periodo": params.fecha_inicio.strftime("%Y-%m") if params.fecha_inicio else datetime.now().strftime("%Y-%m"),
            "informacion_general": {
                "rut_administrador": "76.XXX.XXX-X",
                "nombre_condominio": "Condominio Central",
                "total_unidades": 120,
                "direccion": "Av. Principal 1234, Santiago"
            },
            "situacion_financiera": {
                "activos": {
                    "caja_bancos": 25000000,
                    "cuentas_por_cobrar": 8500000,
                    "fondo_reserva": 120000000,
                    "total_activos": 153500000
                },
                "pasivos": {
                    "proveedores": 12000000,
                    "remuneraciones_por_pagar": 3500000,
                    "total_pasivos": 15500000
                },
                "patrimonio": 138000000
            },
            "fondo_reserva": {
                "saldo_inicial": 115000000,
                "aportes_periodo": 6000000,
                "utilizacion": 1000000,
                "saldo_final": 120000000,
                "porcentaje_sobre_gastos": 26.3,
                "cumple_minimo_legal": True
            },
            "cumplimiento": {
                "contabilidad_al_dia": True,
                "asambleas_realizadas": True,
                "actas_publicadas": True,
                "informes_mensuales": True,
                "porcentaje_cumplimiento": 100
            }
        }
    
    elif tipo == TipoReporte.BALANCE_GENERAL:
        return {
            "titulo": "Balance General",
            "fecha": params.fecha_fin.isoformat() if params.fecha_fin else date.today().isoformat(),
            "activos": {
                "circulante": {
                    "caja": 5000000,
                    "bancos": 20000000,
                    "cuentas_por_cobrar": 8500000,
                    "iva_credito": 1200000,
                    "total_circulante": 34700000
                },
                "fijo": {
                    "terrenos": 0,
                    "edificios": 0,
                    "equipamiento": 15000000,
                    "depreciacion_acumulada": -3000000,
                    "total_fijo": 12000000
                },
                "otros": {
                    "fondo_reserva_banco": 120000000,
                    "total_otros": 120000000
                },
                "total_activos": 166700000
            },
            "pasivos": {
                "circulante": {
                    "proveedores": 12000000,
                    "remuneraciones": 3500000,
                    "iva_debito": 800000,
                    "retenciones": 1200000,
                    "total_circulante": 17500000
                },
                "largo_plazo": {
                    "provisiones": 5000000,
                    "total_largo_plazo": 5000000
                },
                "total_pasivos": 22500000
            },
            "patrimonio": {
                "fondo_reserva": 120000000,
                "resultados_acumulados": 20200000,
                "resultado_ejercicio": 4000000,
                "total_patrimonio": 144200000
            },
            "cuadratura": {
                "total_activos": 166700000,
                "total_pasivo_patrimonio": 166700000,
                "diferencia": 0,
                "cuadra": True
            }
        }
    
    elif tipo == TipoReporte.PROYECCIONES:
        return {
            "titulo": "Proyecciones Financieras",
            "escenarios": {
                "base": {
                    "supuestos": {
                        "inflacion": 4.5,
                        "reajuste_gastos_comunes": 5.0,
                        "tasa_morosidad": 8.0,
                        "ocupacion": 94.0
                    },
                    "proyeccion_mensual": [
                        {"mes": "Ene", "ingresos": 46000000, "gastos": 39000000, "resultado": 7000000},
                        {"mes": "Feb", "ingresos": 46500000, "gastos": 39200000, "resultado": 7300000},
                        {"mes": "Mar", "ingresos": 47000000, "gastos": 39500000, "resultado": 7500000}
                    ]
                },
                "optimista": {
                    "supuestos": {
                        "inflacion": 3.5,
                        "reajuste_gastos_comunes": 4.0,
                        "tasa_morosidad": 5.0,
                        "ocupacion": 98.0
                    },
                    "proyeccion_mensual": [
                        {"mes": "Ene", "ingresos": 48000000, "gastos": 38000000, "resultado": 10000000},
                        {"mes": "Feb", "ingresos": 48500000, "gastos": 38200000, "resultado": 10300000},
                        {"mes": "Mar", "ingresos": 49000000, "gastos": 38500000, "resultado": 10500000}
                    ]
                }
            }
        }
    
    return {"mensaje": "Tipo de reporte no implementado"}

@router.get("/reportes/{reporte_id}")
async def obtener_reporte(reporte_id: str = Path(...)):
    """Obtener reporte generado"""
    if reporte_id not in reportes_generados_db:
        raise HTTPException(404, "Reporte no encontrado")
    return reportes_generados_db[reporte_id]

@router.get("/reportes")
async def listar_reportes(
    tipo: Optional[TipoReporte] = None,
    limit: int = Query(20, le=100)
):
    """Listar reportes generados"""
    resultado = list(reportes_generados_db.values())
    
    if tipo:
        resultado = [r for r in resultado if r["tipo"] == tipo.value]
    
    return {"reportes": resultado[:limit], "total": len(resultado)}

# ============================================================================
# ENDPOINTS REPORTES PROGRAMADOS
# ============================================================================

@router.post("/programar")
async def programar_reporte(data: ReporteProgramadoCreate):
    """
    Programar reporte recurrente
    
    Se ejecutará automáticamente según periodicidad
    """
    reporte_id = generar_id()
    
    proxima_ejecucion = calcular_proxima_ejecucion(data.periodicidad)
    
    reporte = {
        "id": reporte_id,
        **data.dict(),
        "activo": True,
        "ultima_ejecucion": None,
        "proxima_ejecucion": proxima_ejecucion.isoformat(),
        "creado_en": datetime.now().isoformat()
    }
    reportes_programados_db[reporte_id] = reporte
    
    return {
        "mensaje": "Reporte programado",
        "reporte_id": reporte_id,
        "proxima_ejecucion": proxima_ejecucion.isoformat(),
        "reporte": reporte
    }

@router.get("/programados")
async def listar_reportes_programados(activos: bool = True):
    """Listar reportes programados"""
    resultado = list(reportes_programados_db.values())
    
    if activos:
        resultado = [r for r in resultado if r.get("activo", True)]
    
    return {"reportes_programados": resultado, "total": len(resultado)}

@router.delete("/programados/{reporte_id}")
async def desactivar_reporte_programado(reporte_id: str = Path(...)):
    """Desactivar reporte programado"""
    if reporte_id not in reportes_programados_db:
        raise HTTPException(404, "Reporte no encontrado")
    
    reportes_programados_db[reporte_id]["activo"] = False
    return {"mensaje": "Reporte desactivado"}

# ============================================================================
# ENDPOINTS ANÁLISIS
# ============================================================================

@router.get("/tendencias")
async def analizar_tendencias(
    kpi_codigo: Optional[str] = None,
    meses: int = Query(12, ge=3, le=24)
):
    """
    Analizar tendencias de KPIs
    
    Incluye proyección a 3 meses
    """
    if kpi_codigo and kpi_codigo not in kpis_db:
        raise HTTPException(404, "KPI no encontrado")
    
    kpis_analizar = [kpi_codigo] if kpi_codigo else list(kpis_db.keys())
    resultados = []
    
    for codigo in kpis_analizar:
        kpi = kpis_db[codigo]
        
        # Simular datos históricos
        import random
        base = kpi["meta"]
        historico = [
            {
                "fecha": (datetime.now() - timedelta(days=i*30)).isoformat(),
                "valor": base * (1 + random.uniform(-0.1, 0.1))
            }
            for i in range(meses, 0, -1)
        ]
        
        valores = [h["valor"] for h in historico]
        
        # Estadísticas
        promedio = sum(valores) / len(valores)
        minimo = min(valores)
        maximo = max(valores)
        
        # Tendencia simple
        tendencia_mensual = (valores[-1] - valores[0]) / len(valores)
        
        # Proyección
        proyeccion = [
            {"mes": i+1, "valor": valores[-1] + tendencia_mensual * (i+1)}
            for i in range(3)
        ]
        
        resultados.append({
            "codigo": codigo,
            "nombre": kpi["nombre"],
            "historico": historico,
            "estadisticas": {
                "promedio": round(promedio, 2),
                "minimo": round(minimo, 2),
                "maximo": round(maximo, 2),
                "desviacion": round(abs(maximo - minimo) / 2, 2)
            },
            "tendencia": {
                "direccion": "creciente" if tendencia_mensual > 0 else "decreciente",
                "variacion_mensual": round(tendencia_mensual, 2)
            },
            "proyeccion_3_meses": proyeccion,
            "alerta_tendencia": tendencia_mensual < 0 and not kpi.get("menor_es_mejor", False)
        })
    
    return {"analisis_tendencias": resultados}

@router.get("/benchmarking")
async def analizar_benchmarking(
    tipo: str = Query("segmento", pattern="^(segmento|region|nacional)$")
):
    """
    Comparar KPIs vs benchmark del mercado
    
    Tipos: segmento, región, nacional
    """
    resultados = []
    
    # Benchmarks simulados
    benchmarks = {
        "FIN-001": {"segmento": 7.0, "region": 8.0, "nacional": 9.0},
        "FIN-002": {"segmento": 92.0, "region": 90.0, "nacional": 88.0},
        "FIN-003": {"segmento": 4.0, "region": 3.5, "nacional": 3.0},
        "OPE-001": {"segmento": 4.0, "region": 5.0, "nacional": 6.0},
        "OPE-002": {"segmento": 93.0, "region": 91.0, "nacional": 89.0},
        "SAT-001": {"segmento": 40.0, "region": 35.0, "nacional": 30.0}
    }
    
    sobre_benchmark = 0
    bajo_benchmark = 0
    
    for codigo, kpi in kpis_db.items():
        if codigo not in benchmarks:
            continue
        
        valor_actual = kpi_valores_db.get(codigo, {}).get("valor", kpi["meta"] * 0.9)
        benchmark = benchmarks[codigo][tipo]
        
        menor_es_mejor = kpi.get("menor_es_mejor", False)
        
        if menor_es_mejor:
            posicion = "sobre" if valor_actual < benchmark else "bajo"
        else:
            posicion = "sobre" if valor_actual > benchmark else "bajo"
        
        if posicion == "sobre":
            sobre_benchmark += 1
        else:
            bajo_benchmark += 1
        
        resultados.append({
            "codigo": codigo,
            "nombre": kpi["nombre"],
            "valor_actual": valor_actual,
            "benchmark": benchmark,
            "diferencia": round(valor_actual - benchmark, 2),
            "diferencia_pct": round((valor_actual - benchmark) / benchmark * 100, 2) if benchmark != 0 else 0,
            "posicion": posicion
        })
    
    score = (sobre_benchmark / (sobre_benchmark + bajo_benchmark) * 100) if (sobre_benchmark + bajo_benchmark) > 0 else 0
    
    return {
        "tipo_benchmark": tipo,
        "comparaciones": resultados,
        "resumen": {
            "sobre_benchmark": sobre_benchmark,
            "bajo_benchmark": bajo_benchmark,
            "score_general": round(score, 1),
            "ranking_estimado": "Top 25%" if score > 75 else "Top 50%" if score > 50 else "Bajo promedio"
        }
    }

# ============================================================================
# ENDPOINTS EXPORTACIÓN
# ============================================================================

@router.post("/exportar/{reporte_id}")
async def exportar_reporte(
    reporte_id: str = Path(...),
    formato: FormatoExportacion = Query(FormatoExportacion.PDF)
):
    """
    Exportar reporte a diferentes formatos
    
    Formatos: PDF, Excel, CSV, JSON, HTML, PowerPoint
    """
    if reporte_id not in reportes_generados_db:
        raise HTTPException(404, "Reporte no encontrado")
    
    reporte = reportes_generados_db[reporte_id]
    
    # Simular exportación
    archivo = {
        "nombre": f"reporte_{reporte_id}.{formato.value}",
        "formato": formato.value,
        "tamano_bytes": 125000,
        "url_descarga": f"/api/v1/reportes/descargar/{reporte_id}.{formato.value}",
        "expira_en": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    return {
        "mensaje": f"Reporte exportado a {formato.value.upper()}",
        "archivo": archivo
    }

# ============================================================================
# ENDPOINTS ALERTAS
# ============================================================================

@router.get("/alertas")
async def obtener_alertas_activas():
    """
    Obtener todas las alertas activas del sistema
    
    Incluye KPIs fuera de meta, vencimientos y anomalías
    """
    alertas = []
    
    # Alertas de KPIs
    for codigo, kpi in kpis_db.items():
        valor = kpi_valores_db.get(codigo, {}).get("valor", kpi["meta"] * 0.9)
        nivel = evaluar_nivel_alerta(valor, kpi)
        
        if nivel in [NivelAlerta.CRITICO, NivelAlerta.ALTO]:
            alertas.append({
                "tipo": "kpi",
                "codigo": codigo,
                "titulo": f"{kpi['nombre']} fuera de meta",
                "descripcion": f"Valor actual: {valor} {kpi['unidad']} vs Meta: {kpi['meta']} {kpi['unidad']}",
                "nivel": nivel.value,
                "fecha": datetime.now().isoformat(),
                "acciones_sugeridas": [
                    "Revisar causas del desempeño",
                    "Implementar acciones correctivas",
                    "Monitorear evolución diaria"
                ]
            })
    
    # Ordenar por nivel
    orden_nivel = {"critico": 0, "alto": 1, "medio": 2, "bajo": 3}
    alertas.sort(key=lambda x: orden_nivel.get(x["nivel"], 4))
    
    return {
        "alertas": alertas,
        "total": len(alertas),
        "por_nivel": {
            "criticas": len([a for a in alertas if a["nivel"] == "critico"]),
            "altas": len([a for a in alertas if a["nivel"] == "alto"]),
            "medias": len([a for a in alertas if a["nivel"] == "medio"])
        }
    }
