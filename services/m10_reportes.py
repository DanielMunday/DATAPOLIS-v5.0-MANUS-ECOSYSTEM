"""
DATAPOLIS v3.0 - Módulo M10: Reportes y Business Intelligence
==============================================================
Sistema de reportes avanzados y análisis de datos:
- Dashboards interactivos
- KPIs en tiempo real
- Reportes CMF/SII automatizados
- Análisis predictivo
- Exportación multi-formato

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import json


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoReporte(str, Enum):
    """Tipos de reportes disponibles"""
    # Reportes Financieros
    BALANCE_GENERAL = "balance_general"
    ESTADO_RESULTADOS = "estado_resultados"
    FLUJO_CAJA = "flujo_caja"
    PRESUPUESTO_VS_REAL = "presupuesto_vs_real"
    
    # Reportes Operacionales
    MOROSIDAD = "morosidad"
    OCUPACION = "ocupacion"
    MANTENCIONES = "mantenciones"
    ARRIENDOS = "arriendos"
    
    # Reportes Regulatorios
    CMF_MENSUAL = "cmf_mensual"
    CMF_ANUAL = "cmf_anual"
    SII_F29 = "sii_f29"
    SII_DJAT = "sii_djat"
    
    # Reportes Analíticos
    TENDENCIAS = "tendencias"
    PROYECCIONES = "proyecciones"
    BENCHMARKING = "benchmarking"
    RENTABILIDAD = "rentabilidad"
    
    # Reportes Ejecutivos
    RESUMEN_EJECUTIVO = "resumen_ejecutivo"
    DASHBOARD_KPI = "dashboard_kpi"
    ALERTA_TEMPRANA = "alerta_temprana"


class FormatoExportacion(str, Enum):
    """Formatos de exportación"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    POWERPOINT = "powerpoint"


class Periodicidad(str, Enum):
    """Periodicidad de reportes"""
    DIARIO = "diario"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"
    AD_HOC = "ad_hoc"


class TipoGrafico(str, Enum):
    """Tipos de gráficos"""
    LINEA = "linea"
    BARRA = "barra"
    TORTA = "torta"
    AREA = "area"
    SCATTER = "scatter"
    MAPA_CALOR = "mapa_calor"
    GAUGE = "gauge"
    TREEMAP = "treemap"
    SANKEY = "sankey"
    FUNNEL = "funnel"


class NivelAlerta(str, Enum):
    """Niveles de alerta para KPIs"""
    CRITICO = "critico"
    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"
    NORMAL = "normal"


class CategoriaKPI(str, Enum):
    """Categorías de KPIs"""
    FINANCIERO = "financiero"
    OPERACIONAL = "operacional"
    COMERCIAL = "comercial"
    SATISFACCION = "satisfaccion"
    CUMPLIMIENTO = "cumplimiento"
    RIESGO = "riesgo"


# =============================================================================
# MODELOS DE DATOS
# =============================================================================

class KPI:
    """Modelo de indicador clave de rendimiento"""
    def __init__(
        self,
        id: UUID = None,
        codigo: str = "",
        nombre: str = "",
        descripcion: str = "",
        categoria: CategoriaKPI = CategoriaKPI.FINANCIERO,
        unidad: str = "",
        formula: str = "",
        valor_actual: Decimal = Decimal("0"),
        valor_anterior: Decimal = Decimal("0"),
        meta: Decimal = Decimal("0"),
        umbral_critico: Decimal = Decimal("0"),
        umbral_alto: Decimal = Decimal("0"),
        umbral_medio: Decimal = Decimal("0"),
        tendencia: str = "estable",
        variacion_pct: Decimal = Decimal("0"),
        nivel_alerta: NivelAlerta = NivelAlerta.NORMAL,
        ultima_actualizacion: datetime = None
    ):
        self.id = id or uuid4()
        self.codigo = codigo
        self.nombre = nombre
        self.descripcion = descripcion
        self.categoria = categoria
        self.unidad = unidad
        self.formula = formula
        self.valor_actual = valor_actual
        self.valor_anterior = valor_anterior
        self.meta = meta
        self.umbral_critico = umbral_critico
        self.umbral_alto = umbral_alto
        self.umbral_medio = umbral_medio
        self.tendencia = tendencia
        self.variacion_pct = variacion_pct
        self.nivel_alerta = nivel_alerta
        self.ultima_actualizacion = ultima_actualizacion or datetime.now()


class Dashboard:
    """Modelo de dashboard"""
    def __init__(
        self,
        id: UUID = None,
        nombre: str = "",
        descripcion: str = "",
        tipo: str = "operacional",
        widgets: List[Dict] = None,
        filtros: Dict = None,
        layout: Dict = None,
        publico: bool = False,
        propietario_id: UUID = None,
        creado_en: datetime = None,
        actualizado_en: datetime = None
    ):
        self.id = id or uuid4()
        self.nombre = nombre
        self.descripcion = descripcion
        self.tipo = tipo
        self.widgets = widgets or []
        self.filtros = filtros or {}
        self.layout = layout or {"columns": 12, "rows": []}
        self.publico = publico
        self.propietario_id = propietario_id
        self.creado_en = creado_en or datetime.now()
        self.actualizado_en = actualizado_en or datetime.now()


class ReporteProgramado:
    """Modelo de reporte programado"""
    def __init__(
        self,
        id: UUID = None,
        nombre: str = "",
        tipo_reporte: TipoReporte = TipoReporte.RESUMEN_EJECUTIVO,
        periodicidad: Periodicidad = Periodicidad.MENSUAL,
        formato: FormatoExportacion = FormatoExportacion.PDF,
        destinatarios: List[str] = None,
        parametros: Dict = None,
        activo: bool = True,
        ultima_ejecucion: datetime = None,
        proxima_ejecucion: datetime = None,
        copropiedad_id: UUID = None
    ):
        self.id = id or uuid4()
        self.nombre = nombre
        self.tipo_reporte = tipo_reporte
        self.periodicidad = periodicidad
        self.formato = formato
        self.destinatarios = destinatarios or []
        self.parametros = parametros or {}
        self.activo = activo
        self.ultima_ejecucion = ultima_ejecucion
        self.proxima_ejecucion = proxima_ejecucion
        self.copropiedad_id = copropiedad_id


class ReporteGenerado:
    """Modelo de reporte generado"""
    def __init__(
        self,
        id: UUID = None,
        tipo: TipoReporte = TipoReporte.RESUMEN_EJECUTIVO,
        nombre: str = "",
        formato: FormatoExportacion = FormatoExportacion.PDF,
        periodo: str = "",
        parametros: Dict = None,
        datos: Dict = None,
        archivo_url: Optional[str] = None,
        tamano_bytes: int = 0,
        generado_en: datetime = None,
        generado_por: UUID = None,
        expira_en: datetime = None
    ):
        self.id = id or uuid4()
        self.tipo = tipo
        self.nombre = nombre
        self.formato = formato
        self.periodo = periodo
        self.parametros = parametros or {}
        self.datos = datos or {}
        self.archivo_url = archivo_url
        self.tamano_bytes = tamano_bytes
        self.generado_en = generado_en or datetime.now()
        self.generado_por = generado_por
        self.expira_en = expira_en or (datetime.now() + timedelta(days=30))


# =============================================================================
# DEFINICIÓN DE KPIS ESTÁNDAR DATAPOLIS
# =============================================================================

KPIS_ESTANDAR = {
    # KPIs Financieros
    "FIN-001": {
        "nombre": "Tasa de Morosidad",
        "descripcion": "Porcentaje de unidades en mora sobre total",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(unidades_morosas / total_unidades) * 100",
        "meta": Decimal("5"),
        "umbral_critico": Decimal("15"),
        "umbral_alto": Decimal("10"),
        "umbral_medio": Decimal("7")
    },
    "FIN-002": {
        "nombre": "Recaudación Efectiva",
        "descripcion": "Porcentaje de cobros efectivos sobre emitidos",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(cobros_recibidos / cobros_emitidos) * 100",
        "meta": Decimal("95"),
        "umbral_critico": Decimal("80"),
        "umbral_alto": Decimal("85"),
        "umbral_medio": Decimal("90")
    },
    "FIN-003": {
        "nombre": "Ratio Fondo Reserva",
        "descripcion": "Fondo de reserva sobre gastos mensuales",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "meses",
        "formula": "fondo_reserva / gastos_mensuales_promedio",
        "meta": Decimal("6"),
        "umbral_critico": Decimal("1"),
        "umbral_alto": Decimal("2"),
        "umbral_medio": Decimal("3")
    },
    "FIN-004": {
        "nombre": "Ejecución Presupuestaria",
        "descripcion": "Gastos reales vs presupuestados",
        "categoria": CategoriaKPI.FINANCIERO,
        "unidad": "%",
        "formula": "(gastos_reales / gastos_presupuestados) * 100",
        "meta": Decimal("100"),
        "umbral_critico": Decimal("120"),
        "umbral_alto": Decimal("110"),
        "umbral_medio": Decimal("105")
    },
    
    # KPIs Operacionales
    "OPE-001": {
        "nombre": "Tiempo Resolución Mantenciones",
        "descripcion": "Días promedio para cerrar mantención",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "días",
        "formula": "promedio(fecha_cierre - fecha_apertura)",
        "meta": Decimal("3"),
        "umbral_critico": Decimal("10"),
        "umbral_alto": Decimal("7"),
        "umbral_medio": Decimal("5")
    },
    "OPE-002": {
        "nombre": "Tasa Ocupación",
        "descripcion": "Unidades ocupadas sobre total",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "%",
        "formula": "(unidades_ocupadas / total_unidades) * 100",
        "meta": Decimal("95"),
        "umbral_critico": Decimal("80"),
        "umbral_alto": Decimal("85"),
        "umbral_medio": Decimal("90")
    },
    "OPE-003": {
        "nombre": "Mantenciones Preventivas",
        "descripcion": "% mantenciones preventivas vs correctivas",
        "categoria": CategoriaKPI.OPERACIONAL,
        "unidad": "%",
        "formula": "(mant_preventivas / total_mantenciones) * 100",
        "meta": Decimal("70"),
        "umbral_critico": Decimal("30"),
        "umbral_alto": Decimal("40"),
        "umbral_medio": Decimal("50")
    },
    
    # KPIs Satisfacción
    "SAT-001": {
        "nombre": "NPS Residentes",
        "descripcion": "Net Promoter Score de residentes",
        "categoria": CategoriaKPI.SATISFACCION,
        "unidad": "puntos",
        "formula": "%promotores - %detractores",
        "meta": Decimal("50"),
        "umbral_critico": Decimal("0"),
        "umbral_alto": Decimal("20"),
        "umbral_medio": Decimal("30")
    },
    "SAT-002": {
        "nombre": "Tiempo Respuesta Consultas",
        "descripcion": "Horas promedio respuesta a residentes",
        "categoria": CategoriaKPI.SATISFACCION,
        "unidad": "horas",
        "formula": "promedio(tiempo_respuesta)",
        "meta": Decimal("24"),
        "umbral_critico": Decimal("72"),
        "umbral_alto": Decimal("48"),
        "umbral_medio": Decimal("36")
    },
    
    # KPIs Cumplimiento
    "CUM-001": {
        "nombre": "Cumplimiento CMF",
        "descripcion": "% requisitos CMF cumplidos",
        "categoria": CategoriaKPI.CUMPLIMIENTO,
        "unidad": "%",
        "formula": "(requisitos_cumplidos / total_requisitos) * 100",
        "meta": Decimal("100"),
        "umbral_critico": Decimal("70"),
        "umbral_alto": Decimal("80"),
        "umbral_medio": Decimal("90")
    },
    "CUM-002": {
        "nombre": "Declaraciones SII al día",
        "descripcion": "% declaraciones presentadas a tiempo",
        "categoria": CategoriaKPI.CUMPLIMIENTO,
        "unidad": "%",
        "formula": "(decl_a_tiempo / total_declaraciones) * 100",
        "meta": Decimal("100"),
        "umbral_critico": Decimal("80"),
        "umbral_alto": Decimal("90"),
        "umbral_medio": Decimal("95")
    },
    
    # KPIs Riesgo
    "RIE-001": {
        "nombre": "Score Riesgo General",
        "descripcion": "Índice compuesto de riesgo",
        "categoria": CategoriaKPI.RIESGO,
        "unidad": "puntos",
        "formula": "modelo_riesgo_compuesto",
        "meta": Decimal("80"),
        "umbral_critico": Decimal("40"),
        "umbral_alto": Decimal("50"),
        "umbral_medio": Decimal("60")
    }
}


# =============================================================================
# SERVICIO DE REPORTES Y BI
# =============================================================================

class ReportesService:
    """
    Servicio de Reportes y Business Intelligence
    
    Funcionalidades:
    - Dashboards personalizables
    - KPIs en tiempo real
    - Reportes automatizados
    - Análisis de tendencias
    - Alertas inteligentes
    - Exportación multi-formato
    """
    
    def __init__(self):
        self.kpis: Dict[str, KPI] = {}
        self.dashboards: Dict[UUID, Dashboard] = {}
        self.reportes_programados: Dict[UUID, ReporteProgramado] = {}
        self.reportes_generados: Dict[UUID, ReporteGenerado] = {}
        self._inicializar_kpis()
    
    def _inicializar_kpis(self):
        """Inicializa KPIs estándar"""
        for codigo, config in KPIS_ESTANDAR.items():
            kpi = KPI(
                codigo=codigo,
                nombre=config["nombre"],
                descripcion=config["descripcion"],
                categoria=config["categoria"],
                unidad=config["unidad"],
                formula=config["formula"],
                meta=config["meta"],
                umbral_critico=config["umbral_critico"],
                umbral_alto=config["umbral_alto"],
                umbral_medio=config["umbral_medio"]
            )
            self.kpis[codigo] = kpi
    
    # =========================================================================
    # GESTIÓN DE KPIS
    # =========================================================================
    
    async def obtener_kpis(
        self,
        categoria: Optional[CategoriaKPI] = None,
        solo_alertas: bool = False
    ) -> List[KPI]:
        """Obtiene KPIs con filtros opcionales"""
        kpis = list(self.kpis.values())
        
        if categoria:
            kpis = [k for k in kpis if k.categoria == categoria]
        
        if solo_alertas:
            kpis = [k for k in kpis if k.nivel_alerta != NivelAlerta.NORMAL]
        
        return kpis
    
    async def actualizar_kpi(
        self,
        codigo: str,
        valor: Decimal,
        copropiedad_id: UUID = None
    ) -> KPI:
        """Actualiza valor de un KPI"""
        
        kpi = self.kpis.get(codigo)
        if not kpi:
            raise ValueError(f"KPI {codigo} no encontrado")
        
        # Guardar valor anterior
        kpi.valor_anterior = kpi.valor_actual
        kpi.valor_actual = valor
        
        # Calcular variación
        if kpi.valor_anterior > 0:
            kpi.variacion_pct = ((valor - kpi.valor_anterior) / kpi.valor_anterior) * 100
        
        # Determinar tendencia
        if valor > kpi.valor_anterior:
            kpi.tendencia = "creciente"
        elif valor < kpi.valor_anterior:
            kpi.tendencia = "decreciente"
        else:
            kpi.tendencia = "estable"
        
        # Evaluar nivel de alerta
        kpi.nivel_alerta = self._evaluar_alerta(kpi)
        kpi.ultima_actualizacion = datetime.now()
        
        return kpi
    
    def _evaluar_alerta(self, kpi: KPI) -> NivelAlerta:
        """Evalúa nivel de alerta según umbrales"""
        valor = kpi.valor_actual
        
        # Para KPIs donde mayor es peor (ej: morosidad, tiempo respuesta)
        if kpi.codigo in ["FIN-001", "FIN-004", "OPE-001", "SAT-002"]:
            if valor >= kpi.umbral_critico:
                return NivelAlerta.CRITICO
            elif valor >= kpi.umbral_alto:
                return NivelAlerta.ALTO
            elif valor >= kpi.umbral_medio:
                return NivelAlerta.MEDIO
            elif valor > kpi.meta:
                return NivelAlerta.BAJO
            return NivelAlerta.NORMAL
        
        # Para KPIs donde menor es peor (ej: recaudación, ocupación)
        else:
            if valor <= kpi.umbral_critico:
                return NivelAlerta.CRITICO
            elif valor <= kpi.umbral_alto:
                return NivelAlerta.ALTO
            elif valor <= kpi.umbral_medio:
                return NivelAlerta.MEDIO
            elif valor < kpi.meta:
                return NivelAlerta.BAJO
            return NivelAlerta.NORMAL
    
    async def calcular_dashboard_kpis(
        self,
        copropiedad_id: UUID
    ) -> Dict[str, Any]:
        """Calcula todos los KPIs para un dashboard"""
        
        # Simular cálculo de KPIs (en producción se conectaría a servicios reales)
        kpis_calculados = []
        alertas = []
        
        for codigo, kpi in self.kpis.items():
            # Simular valores
            import random
            valor = Decimal(str(random.uniform(
                float(kpi.umbral_critico) * 0.8,
                float(kpi.meta) * 1.2
            )))
            
            kpi_actualizado = await self.actualizar_kpi(codigo, valor, copropiedad_id)
            
            kpis_calculados.append({
                "codigo": kpi_actualizado.codigo,
                "nombre": kpi_actualizado.nombre,
                "valor": float(kpi_actualizado.valor_actual),
                "meta": float(kpi_actualizado.meta),
                "unidad": kpi_actualizado.unidad,
                "variacion_pct": float(kpi_actualizado.variacion_pct),
                "tendencia": kpi_actualizado.tendencia,
                "nivel_alerta": kpi_actualizado.nivel_alerta.value,
                "categoria": kpi_actualizado.categoria.value
            })
            
            if kpi_actualizado.nivel_alerta in [NivelAlerta.CRITICO, NivelAlerta.ALTO]:
                alertas.append({
                    "codigo": kpi_actualizado.codigo,
                    "nombre": kpi_actualizado.nombre,
                    "nivel": kpi_actualizado.nivel_alerta.value,
                    "mensaje": f"{kpi_actualizado.nombre}: {kpi_actualizado.valor_actual}{kpi_actualizado.unidad} (meta: {kpi_actualizado.meta}{kpi_actualizado.unidad})"
                })
        
        return {
            "copropiedad_id": str(copropiedad_id),
            "fecha_calculo": datetime.now().isoformat(),
            "kpis": kpis_calculados,
            "alertas": alertas,
            "resumen": {
                "total_kpis": len(kpis_calculados),
                "en_meta": len([k for k in kpis_calculados if k["nivel_alerta"] == "normal"]),
                "alertas_criticas": len([a for a in alertas if a["nivel"] == "critico"]),
                "alertas_altas": len([a for a in alertas if a["nivel"] == "alto"])
            }
        }
    
    # =========================================================================
    # DASHBOARDS
    # =========================================================================
    
    async def crear_dashboard(
        self,
        nombre: str,
        tipo: str,
        propietario_id: UUID,
        descripcion: str = "",
        widgets: List[Dict] = None,
        publico: bool = False
    ) -> Dashboard:
        """Crea un nuevo dashboard"""
        
        dashboard = Dashboard(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            widgets=widgets or [],
            propietario_id=propietario_id,
            publico=publico
        )
        
        self.dashboards[dashboard.id] = dashboard
        return dashboard
    
    async def obtener_dashboard(self, dashboard_id: UUID) -> Optional[Dashboard]:
        """Obtiene un dashboard por ID"""
        return self.dashboards.get(dashboard_id)
    
    async def agregar_widget(
        self,
        dashboard_id: UUID,
        tipo_widget: str,
        titulo: str,
        configuracion: Dict,
        posicion: Dict = None
    ) -> Dashboard:
        """Agrega widget a un dashboard"""
        
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            raise ValueError("Dashboard no encontrado")
        
        widget = {
            "id": str(uuid4()),
            "tipo": tipo_widget,
            "titulo": titulo,
            "configuracion": configuracion,
            "posicion": posicion or {"x": 0, "y": 0, "w": 4, "h": 3}
        }
        
        dashboard.widgets.append(widget)
        dashboard.actualizado_en = datetime.now()
        
        return dashboard
    
    async def generar_datos_widget(
        self,
        tipo_widget: str,
        configuracion: Dict,
        copropiedad_id: UUID
    ) -> Dict[str, Any]:
        """Genera datos para un widget específico"""
        
        if tipo_widget == "kpi_card":
            kpi_codigo = configuracion.get("kpi_codigo")
            kpi = self.kpis.get(kpi_codigo)
            if kpi:
                return {
                    "valor": float(kpi.valor_actual),
                    "meta": float(kpi.meta),
                    "variacion": float(kpi.variacion_pct),
                    "tendencia": kpi.tendencia,
                    "alerta": kpi.nivel_alerta.value
                }
        
        elif tipo_widget == "chart_linea":
            # Generar datos de serie temporal
            datos = []
            for i in range(12):
                fecha = date.today() - timedelta(days=30*(11-i))
                import random
                datos.append({
                    "fecha": fecha.isoformat(),
                    "valor": random.uniform(80, 120)
                })
            return {"serie": datos}
        
        elif tipo_widget == "chart_torta":
            return {
                "segmentos": [
                    {"etiqueta": "Pagado", "valor": 75},
                    {"etiqueta": "Pendiente", "valor": 15},
                    {"etiqueta": "Moroso", "valor": 10}
                ]
            }
        
        elif tipo_widget == "tabla":
            return {
                "columnas": ["Unidad", "Propietario", "Estado", "Monto"],
                "filas": [
                    ["101", "Juan Pérez", "Pagado", "$150.000"],
                    ["102", "María García", "Pendiente", "$150.000"],
                    ["103", "Carlos López", "Moroso", "$450.000"]
                ]
            }
        
        return {}
    
    # =========================================================================
    # GENERACIÓN DE REPORTES
    # =========================================================================
    
    async def generar_reporte(
        self,
        tipo: TipoReporte,
        formato: FormatoExportacion,
        parametros: Dict,
        usuario_id: UUID
    ) -> ReporteGenerado:
        """Genera un reporte específico"""
        
        # Obtener datos según tipo de reporte
        datos = await self._obtener_datos_reporte(tipo, parametros)
        
        # Crear reporte
        reporte = ReporteGenerado(
            tipo=tipo,
            nombre=f"{tipo.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            formato=formato,
            periodo=parametros.get("periodo", datetime.now().strftime("%Y%m")),
            parametros=parametros,
            datos=datos,
            generado_por=usuario_id
        )
        
        # Generar archivo (simulado)
        reporte.archivo_url = f"/reportes/{reporte.id}.{formato.value}"
        reporte.tamano_bytes = len(json.dumps(datos)) * 2  # Estimación
        
        self.reportes_generados[reporte.id] = reporte
        return reporte
    
    async def _obtener_datos_reporte(
        self,
        tipo: TipoReporte,
        parametros: Dict
    ) -> Dict[str, Any]:
        """Obtiene datos para un tipo de reporte"""
        
        if tipo == TipoReporte.RESUMEN_EJECUTIVO:
            return {
                "titulo": "Resumen Ejecutivo",
                "periodo": parametros.get("periodo"),
                "secciones": [
                    {
                        "titulo": "Situación Financiera",
                        "indicadores": [
                            {"nombre": "Recaudación", "valor": "95%", "tendencia": "up"},
                            {"nombre": "Morosidad", "valor": "5%", "tendencia": "down"},
                            {"nombre": "Fondo Reserva", "valor": "UF 500", "tendencia": "stable"}
                        ]
                    },
                    {
                        "titulo": "Operaciones",
                        "indicadores": [
                            {"nombre": "Mantenciones Abiertas", "valor": "3", "tendencia": "down"},
                            {"nombre": "Tiempo Promedio Resolución", "valor": "2.5 días", "tendencia": "down"},
                            {"nombre": "Ocupación", "valor": "98%", "tendencia": "stable"}
                        ]
                    }
                ]
            }
        
        elif tipo == TipoReporte.MOROSIDAD:
            return {
                "titulo": "Reporte de Morosidad",
                "periodo": parametros.get("periodo"),
                "resumen": {
                    "total_unidades": 100,
                    "unidades_morosas": 5,
                    "tasa_morosidad": 5.0,
                    "monto_moroso_total_uf": Decimal("45.5")
                },
                "detalle_morosos": [
                    {"unidad": "101", "propietario": "Juan Pérez", "meses_mora": 2, "monto_uf": Decimal("10")},
                    {"unidad": "205", "propietario": "María García", "meses_mora": 3, "monto_uf": Decimal("15")},
                    {"unidad": "308", "propietario": "Carlos López", "meses_mora": 1, "monto_uf": Decimal("5")}
                ],
                "evolucion_12_meses": [
                    {"mes": "2025-01", "tasa": 4.5},
                    {"mes": "2025-02", "tasa": 4.8},
                    {"mes": "2025-03", "tasa": 5.0}
                ]
            }
        
        elif tipo == TipoReporte.CMF_MENSUAL:
            return {
                "titulo": "Reporte CMF Mensual - Ley 21.442",
                "periodo": parametros.get("periodo"),
                "copropiedad": {
                    "rut": "76.xxx.xxx-x",
                    "nombre": "Comunidad Edificio XXX",
                    "direccion": "Av. Principal 123"
                },
                "financiero": {
                    "activos_totales_uf": Decimal("1500"),
                    "pasivos_totales_uf": Decimal("200"),
                    "patrimonio_uf": Decimal("1300"),
                    "fondo_reserva_uf": Decimal("150")
                },
                "cumplimiento": {
                    "contabilidad_al_dia": True,
                    "fondo_reserva_constituido": True,
                    "cuenta_bancaria_exclusiva": True,
                    "asambleas_realizadas": 2,
                    "actas_firmadas": True
                },
                "observaciones": []
            }
        
        elif tipo == TipoReporte.BALANCE_GENERAL:
            return {
                "titulo": "Balance General",
                "fecha_corte": parametros.get("fecha_corte", date.today().isoformat()),
                "activos": {
                    "circulante": [
                        {"cuenta": "Caja", "monto_uf": Decimal("10")},
                        {"cuenta": "Bancos", "monto_uf": Decimal("250")},
                        {"cuenta": "Cuentas por Cobrar", "monto_uf": Decimal("45")}
                    ],
                    "fijo": [
                        {"cuenta": "Equipamiento", "monto_uf": Decimal("80")},
                        {"cuenta": "Depreciación Acum.", "monto_uf": Decimal("-20")}
                    ]
                },
                "pasivos": {
                    "circulante": [
                        {"cuenta": "Proveedores", "monto_uf": Decimal("30")},
                        {"cuenta": "Provisiones", "monto_uf": Decimal("15")}
                    ]
                },
                "patrimonio": [
                    {"cuenta": "Fondo Reserva", "monto_uf": Decimal("150")},
                    {"cuenta": "Resultado Acumulado", "monto_uf": Decimal("170")}
                ],
                "total_activos_uf": Decimal("365"),
                "total_pasivos_uf": Decimal("45"),
                "total_patrimonio_uf": Decimal("320"),
                "cuadrado": True
            }
        
        elif tipo == TipoReporte.PROYECCIONES:
            return {
                "titulo": "Proyecciones Financieras",
                "horizonte": parametros.get("horizonte_meses", 12),
                "escenarios": [
                    {
                        "nombre": "Base",
                        "supuestos": {"morosidad": 5, "inflacion": 3},
                        "proyeccion": [
                            {"mes": 1, "ingresos_uf": 100, "gastos_uf": 90},
                            {"mes": 2, "ingresos_uf": 102, "gastos_uf": 91},
                            {"mes": 3, "ingresos_uf": 104, "gastos_uf": 92}
                        ]
                    },
                    {
                        "nombre": "Optimista",
                        "supuestos": {"morosidad": 3, "inflacion": 2},
                        "proyeccion": [
                            {"mes": 1, "ingresos_uf": 105, "gastos_uf": 88},
                            {"mes": 2, "ingresos_uf": 108, "gastos_uf": 89},
                            {"mes": 3, "ingresos_uf": 111, "gastos_uf": 90}
                        ]
                    }
                ]
            }
        
        return {"error": "Tipo de reporte no implementado"}
    
    # =========================================================================
    # REPORTES PROGRAMADOS
    # =========================================================================
    
    async def programar_reporte(
        self,
        nombre: str,
        tipo_reporte: TipoReporte,
        periodicidad: Periodicidad,
        formato: FormatoExportacion,
        destinatarios: List[str],
        parametros: Dict,
        copropiedad_id: UUID
    ) -> ReporteProgramado:
        """Programa un reporte recurrente"""
        
        # Calcular próxima ejecución
        proxima = self._calcular_proxima_ejecucion(periodicidad)
        
        reporte = ReporteProgramado(
            nombre=nombre,
            tipo_reporte=tipo_reporte,
            periodicidad=periodicidad,
            formato=formato,
            destinatarios=destinatarios,
            parametros=parametros,
            proxima_ejecucion=proxima,
            copropiedad_id=copropiedad_id
        )
        
        self.reportes_programados[reporte.id] = reporte
        return reporte
    
    def _calcular_proxima_ejecucion(self, periodicidad: Periodicidad) -> datetime:
        """Calcula próxima fecha de ejecución"""
        ahora = datetime.now()
        
        if periodicidad == Periodicidad.DIARIO:
            return ahora + timedelta(days=1)
        elif periodicidad == Periodicidad.SEMANAL:
            return ahora + timedelta(weeks=1)
        elif periodicidad == Periodicidad.QUINCENAL:
            return ahora + timedelta(days=15)
        elif periodicidad == Periodicidad.MENSUAL:
            return ahora + timedelta(days=30)
        elif periodicidad == Periodicidad.TRIMESTRAL:
            return ahora + timedelta(days=90)
        elif periodicidad == Periodicidad.SEMESTRAL:
            return ahora + timedelta(days=180)
        elif periodicidad == Periodicidad.ANUAL:
            return ahora + timedelta(days=365)
        
        return ahora
    
    async def ejecutar_reportes_programados(self) -> List[ReporteGenerado]:
        """Ejecuta reportes programados pendientes"""
        
        reportes_ejecutados = []
        ahora = datetime.now()
        
        for prog in self.reportes_programados.values():
            if not prog.activo:
                continue
            
            if prog.proxima_ejecucion and prog.proxima_ejecucion <= ahora:
                # Generar reporte
                reporte = await self.generar_reporte(
                    tipo=prog.tipo_reporte,
                    formato=prog.formato,
                    parametros=prog.parametros,
                    usuario_id=prog.copropiedad_id  # Usar como sistema
                )
                
                reportes_ejecutados.append(reporte)
                
                # Actualizar programación
                prog.ultima_ejecucion = ahora
                prog.proxima_ejecucion = self._calcular_proxima_ejecucion(prog.periodicidad)
                
                # TODO: Enviar a destinatarios
        
        return reportes_ejecutados
    
    # =========================================================================
    # ANÁLISIS Y TENDENCIAS
    # =========================================================================
    
    async def analizar_tendencias(
        self,
        kpi_codigo: str,
        periodo_meses: int = 12,
        copropiedad_id: UUID = None
    ) -> Dict[str, Any]:
        """Analiza tendencias de un KPI"""
        
        kpi = self.kpis.get(kpi_codigo)
        if not kpi:
            raise ValueError(f"KPI {kpi_codigo} no encontrado")
        
        # Simular datos históricos
        import random
        datos_historicos = []
        base = float(kpi.meta)
        
        for i in range(periodo_meses):
            fecha = date.today() - timedelta(days=30*(periodo_meses-1-i))
            valor = base * (1 + random.uniform(-0.2, 0.2))
            datos_historicos.append({
                "periodo": fecha.strftime("%Y-%m"),
                "valor": round(valor, 2)
            })
        
        # Calcular estadísticas
        valores = [d["valor"] for d in datos_historicos]
        promedio = sum(valores) / len(valores)
        minimo = min(valores)
        maximo = max(valores)
        
        # Tendencia simple (pendiente)
        if len(valores) >= 2:
            tendencia = (valores[-1] - valores[0]) / len(valores)
        else:
            tendencia = 0
        
        return {
            "kpi_codigo": kpi_codigo,
            "kpi_nombre": kpi.nombre,
            "periodo_analizado": f"Últimos {periodo_meses} meses",
            "datos": datos_historicos,
            "estadisticas": {
                "promedio": round(promedio, 2),
                "minimo": round(minimo, 2),
                "maximo": round(maximo, 2),
                "desviacion": round((maximo - minimo) / 2, 2),
                "tendencia_mensual": round(tendencia, 3)
            },
            "proyeccion_3_meses": [
                round(valores[-1] + tendencia * (i+1), 2)
                for i in range(3)
            ],
            "alerta_tendencia": "negativa" if tendencia < 0 and kpi_codigo not in ["FIN-001", "OPE-001"] else "positiva" if tendencia > 0 else "estable"
        }
    
    async def generar_benchmarking(
        self,
        copropiedad_id: UUID,
        comparar_con: str = "segmento"  # segmento, region, nacional
    ) -> Dict[str, Any]:
        """Genera comparativa de benchmarking"""
        
        # Simular benchmarks
        import random
        
        benchmarks = []
        for codigo, kpi in self.kpis.items():
            valor_propio = float(kpi.valor_actual) if kpi.valor_actual else float(kpi.meta)
            valor_benchmark = float(kpi.meta) * (1 + random.uniform(-0.1, 0.1))
            
            posicion = "sobre" if valor_propio > valor_benchmark else "bajo" if valor_propio < valor_benchmark else "igual"
            
            benchmarks.append({
                "kpi_codigo": codigo,
                "kpi_nombre": kpi.nombre,
                "valor_propio": round(valor_propio, 2),
                "valor_benchmark": round(valor_benchmark, 2),
                "diferencia": round(valor_propio - valor_benchmark, 2),
                "diferencia_pct": round((valor_propio - valor_benchmark) / valor_benchmark * 100, 1) if valor_benchmark else 0,
                "posicion": posicion,
                "unidad": kpi.unidad
            })
        
        # Calcular score general
        sobre_benchmark = len([b for b in benchmarks if b["posicion"] == "sobre"])
        score = (sobre_benchmark / len(benchmarks)) * 100 if benchmarks else 0
        
        return {
            "copropiedad_id": str(copropiedad_id),
            "comparacion": comparar_con,
            "fecha_analisis": datetime.now().isoformat(),
            "benchmarks": benchmarks,
            "resumen": {
                "kpis_sobre_benchmark": sobre_benchmark,
                "kpis_bajo_benchmark": len([b for b in benchmarks if b["posicion"] == "bajo"]),
                "kpis_en_benchmark": len([b for b in benchmarks if b["posicion"] == "igual"]),
                "score_general": round(score, 1),
                "ranking_estimado": "Top 25%" if score > 75 else "Top 50%" if score > 50 else "Bajo promedio"
            }
        }
    
    # =========================================================================
    # EXPORTACIÓN
    # =========================================================================
    
    async def exportar_datos(
        self,
        tipo_datos: str,
        formato: FormatoExportacion,
        filtros: Dict,
        usuario_id: UUID
    ) -> Dict[str, Any]:
        """Exporta datos en formato especificado"""
        
        # Simular exportación
        return {
            "tipo_datos": tipo_datos,
            "formato": formato.value,
            "registros_exportados": 150,
            "archivo_url": f"/exports/{uuid4()}.{formato.value}",
            "tamano_bytes": 25600,
            "generado_en": datetime.now().isoformat(),
            "expira_en": (datetime.now() + timedelta(hours=24)).isoformat()
        }


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================

reportes_service = ReportesService()
