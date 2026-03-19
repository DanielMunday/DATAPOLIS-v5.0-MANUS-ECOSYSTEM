"""
DATAPOLIS v3.0 - Router API Credit Score Inmobiliario
Endpoints REST para M03_CreditScore (5 dimensiones, SHAP, XGBoost)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.schemas.credit_score import (
    CreditScoreRequest, CreditScoreResponse, CreditScoreRapidoRequest,
    SimulacionRequest, SimulacionResponse, HistorialScoreResponse,
    BenchmarkResponse, RiesgoDetalladoResponse, FactorImpactoResponse
)
from app.schemas.base import ResponseWrapper, ErrorResponse
from app.services.m03_credit_score import ServicioCreditScore
from app.config import get_settings

router = APIRouter(
    prefix="/credit-score",
    tags=["Credit Score Inmobiliario"],
    responses={
        400: {"model": ErrorResponse, "description": "Request inválido"},
        404: {"model": ErrorResponse, "description": "Propiedad no encontrada"},
        500: {"model": ErrorResponse, "description": "Error interno"}
    }
)

settings = get_settings()
_servicio_credit_score: Optional[ServicioCreditScore] = None

async def get_servicio() -> ServicioCreditScore:
    """Dependency injection para servicio credit score"""
    global _servicio_credit_score
    if _servicio_credit_score is None:
        _servicio_credit_score = ServicioCreditScore()
    return _servicio_credit_score


class CategoriaScore(str, Enum):
    """Categorías de clasificación crediticia"""
    AAA = "AAA"  # 900-1000
    AA = "AA"    # 800-899
    A = "A"      # 700-799
    BBB = "BBB"  # 600-699
    BB = "BB"    # 500-599
    B = "B"      # 400-499
    CCC = "CCC"  # 300-399
    CC = "CC"    # 200-299
    C = "C"      # 100-199
    D = "D"      # 0-99


# ============================================================================
# EVALUACIÓN CREDIT SCORE
# ============================================================================

@router.post(
    "/evaluar",
    response_model=ResponseWrapper[CreditScoreResponse],
    summary="Evaluación completa Credit Score",
    description="Genera Credit Score inmobiliario con análisis de 5 dimensiones"
)
async def evaluar_credit_score(
    request: CreditScoreRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Evaluación Credit Score inmobiliario integral.
    
    **5 Dimensiones evaluadas**:
    1. **Ubicación** (20%): Zona, accesibilidad, servicios, plusvalía, seguridad
    2. **Legal** (25%): Títulos, gravámenes, litigios, permisos
    3. **Financiero** (25%): Valor, rentabilidad, liquidez, deuda
    4. **Técnico** (15%): Estado, antigüedad, calidad, eficiencia
    5. **Mercado** (15%): Demanda, tendencias, competencia
    
    **Score**: 0-1000 puntos con categoría AAA a D
    
    **Incluye**: Explicabilidad SHAP (Machine Learning interpretable)
    """
    try:
        resultado = await servicio.evaluar(
            datos_propiedad=request.datos_propiedad,
            datos_legales=request.datos_legales,
            datos_financieros=request.datos_financieros,
            datos_tecnicos=request.datos_tecnicos,
            datos_mercado=request.datos_mercado,
            incluir_shap=request.incluir_explicaciones
        )
        
        # Log para analytics
        background_tasks.add_task(
            _log_evaluacion,
            resultado.id_evaluacion,
            request.datos_propiedad.get("rol_sii")
        )
        
        return ResponseWrapper(
            success=True,
            data=resultado,
            message=f"Score: {resultado.score_total} ({resultado.categoria})"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evaluación: {str(e)}")


@router.post(
    "/rapido",
    response_model=ResponseWrapper[dict],
    summary="Credit Score rápido",
    description="Evaluación simplificada instantánea"
)
async def evaluar_rapido(
    request: CreditScoreRapidoRequest,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Credit Score rápido con datos mínimos.
    
    **Datos requeridos**:
    - Comuna y dirección
    - Tipo de propiedad
    - Valor estimado
    - Antigüedad
    
    **Precisión**: Aproximada (±50-100 puntos vs evaluación completa)
    """
    try:
        resultado = await servicio.evaluar_rapido(
            comuna=request.comuna,
            tipo_propiedad=request.tipo_propiedad,
            valor_uf=request.valor_uf,
            antiguedad_anos=request.antiguedad_anos,
            tiene_hipoteca=request.tiene_hipoteca,
            estado_conservacion=request.estado_conservacion
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "score_estimado": resultado["score"],
                "categoria": resultado["categoria"],
                "rango_score": {
                    "minimo": resultado["score_min"],
                    "maximo": resultado["score_max"]
                },
                "factores_principales": resultado["factores"],
                "confianza": resultado["confianza"],
                "nota": "Evaluación simplificada. Para score preciso, use evaluación completa."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/evaluar/{rol_sii}",
    response_model=ResponseWrapper[CreditScoreResponse],
    summary="Credit Score por ROL SII"
)
async def evaluar_por_rol(
    rol_sii: str,
    actualizar_datos: bool = Query(False, description="Forzar actualización desde fuentes"),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Evalúa Credit Score consultando datos automáticamente por ROL SII.
    
    **Fuentes consultadas**:
    - SII (avalúo, contribuciones)
    - CBR (títulos, gravámenes)
    - DOM Municipal (permisos)
    - Mercado (comparables)
    """
    try:
        resultado = await servicio.evaluar_por_rol(rol_sii, actualizar_datos)
        
        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró información para ROL {rol_sii}"
            )
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANÁLISIS DE DIMENSIONES
# ============================================================================

@router.get(
    "/dimensiones",
    response_model=ResponseWrapper[List[dict]],
    summary="Descripción de dimensiones"
)
async def listar_dimensiones():
    """
    Detalle de las 5 dimensiones evaluadas en el Credit Score.
    """
    dimensiones = [
        {
            "codigo": "UBICACION",
            "nombre": "Ubicación y Entorno",
            "peso": 0.20,
            "descripcion": "Evalúa la localización, accesibilidad, servicios cercanos y potencial de plusvalía",
            "factores": [
                "Factor zona (ranking comunal)",
                "Distancia a transporte público",
                "Servicios y equipamiento cercano",
                "Plusvalía histórica",
                "Índice de seguridad",
                "Zona sísmica"
            ],
            "fuentes": ["Google Maps", "SECTRA", "Carabineros", "SHOA"]
        },
        {
            "codigo": "LEGAL",
            "nombre": "Situación Legal",
            "peso": 0.25,
            "descripcion": "Verifica títulos de dominio, gravámenes, litigios y permisos",
            "factores": [
                "Estado títulos CBR",
                "Gravámenes e hipotecas",
                "Prohibiciones y embargos",
                "Litigios activos",
                "Permisos municipales",
                "Cumplimiento urbanístico"
            ],
            "fuentes": ["CBR", "Poder Judicial", "DOM Municipal"]
        },
        {
            "codigo": "FINANCIERO",
            "nombre": "Situación Financiera",
            "peso": 0.25,
            "descripcion": "Analiza valor, rentabilidad, liquidez y obligaciones",
            "factores": [
                "Relación valor vs mercado",
                "Cap Rate y rentabilidad",
                "Liquidez (días en mercado)",
                "Estado morosidad",
                "Costos mantención",
                "Deuda y LTV"
            ],
            "fuentes": ["SII", "Portales inmobiliarios", "TGR", "CMF"]
        },
        {
            "codigo": "TECNICO",
            "nombre": "Estado Técnico",
            "peso": 0.15,
            "descripcion": "Evalúa condición física, antigüedad y calidad constructiva",
            "factores": [
                "Estado de conservación",
                "Vida útil remanente",
                "Calidad construcción",
                "Certificación energética",
                "Instalaciones (eléctrica, gas, sanitaria)"
            ],
            "fuentes": ["Inspección", "SEC", "MINVU"]
        },
        {
            "codigo": "MERCADO",
            "nombre": "Condiciones de Mercado",
            "peso": 0.15,
            "descripcion": "Analiza dinámica de oferta/demanda y tendencias",
            "factores": [
                "Índice de demanda zona",
                "Tendencia precios 12 meses",
                "Meses de inventario",
                "Nivel competencia",
                "Tasas hipotecarias",
                "Proyectos en desarrollo"
            ],
            "fuentes": ["Portales", "BCCh", "INE", "TOCTOC"]
        }
    ]
    
    return ResponseWrapper(success=True, data=dimensiones)


@router.get(
    "/dimension/{codigo}",
    response_model=ResponseWrapper[dict],
    summary="Detalle de dimensión específica"
)
async def get_dimension_detalle(
    codigo: str,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Obtiene detalle completo de una dimensión con benchmarks.
    """
    codigo_upper = codigo.upper()
    if codigo_upper not in ["UBICACION", "LEGAL", "FINANCIERO", "TECNICO", "MERCADO"]:
        raise HTTPException(status_code=400, detail=f"Dimensión no válida: {codigo}")
    
    try:
        detalle = await servicio.detalle_dimension(codigo_upper)
        return ResponseWrapper(success=True, data=detalle)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANÁLISIS DE RIESGOS
# ============================================================================

@router.get(
    "/riesgos/{id_evaluacion}",
    response_model=ResponseWrapper[RiesgoDetalladoResponse],
    summary="Riesgos identificados en evaluación"
)
async def get_riesgos_evaluacion(
    id_evaluacion: str,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Obtiene detalle de riesgos identificados en una evaluación.
    
    **Tipos de riesgo**:
    - Título: Problemas dominio
    - Gravamen: Hipotecas, prohibiciones
    - Litigio: Juicios activos
    - Urbanístico: Incumplimientos normativos
    - Ambiental: Contaminación, riesgos naturales
    - Estructural: Problemas construcción
    - Mercado: Baja demanda, sobrevaloración
    - Liquidez: Dificultad de venta
    - Regulatorio: Cambios normativos
    - Sísmico: Zona de riesgo
    """
    try:
        resultado = await servicio.obtener_riesgos(id_evaluacion)
        
        if resultado is None:
            raise HTTPException(status_code=404, detail="Evaluación no encontrada")
        
        return ResponseWrapper(
            success=True,
            data=RiesgoDetalladoResponse(
                id_evaluacion=id_evaluacion,
                total_riesgos=resultado["total"],
                riesgos_criticos=resultado["criticos"],
                riesgos_altos=resultado["altos"],
                riesgos_medios=resultado["medios"],
                riesgos_bajos=resultado["bajos"],
                detalle_riesgos=resultado["detalle"],
                recomendaciones_mitigacion=resultado["mitigaciones"]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/riesgos/tipos",
    response_model=ResponseWrapper[List[dict]],
    summary="Catálogo de tipos de riesgo"
)
async def listar_tipos_riesgo():
    """Lista todos los tipos de riesgo evaluados con descripción"""
    tipos = [
        {
            "codigo": "TITULO",
            "nombre": "Riesgo de Título",
            "descripcion": "Problemas con dominio, inscripciones o cadena de títulos",
            "severidad_max": "critico",
            "impacto_tipico": -150
        },
        {
            "codigo": "GRAVAMEN",
            "nombre": "Gravámenes",
            "descripcion": "Hipotecas, prohibiciones, usufructos",
            "severidad_max": "alto",
            "impacto_tipico": -100
        },
        {
            "codigo": "LITIGIO",
            "nombre": "Litigios",
            "descripcion": "Juicios activos que afectan la propiedad",
            "severidad_max": "critico",
            "impacto_tipico": -200
        },
        {
            "codigo": "URBANISTICO",
            "nombre": "Urbanístico",
            "descripcion": "Incumplimientos de normativa urbana o permisos",
            "severidad_max": "alto",
            "impacto_tipico": -80
        },
        {
            "codigo": "AMBIENTAL",
            "nombre": "Ambiental",
            "descripcion": "Contaminación, pasivos ambientales",
            "severidad_max": "critico",
            "impacto_tipico": -120
        },
        {
            "codigo": "ESTRUCTURAL",
            "nombre": "Estructural",
            "descripcion": "Problemas de construcción o daños estructurales",
            "severidad_max": "critico",
            "impacto_tipico": -150
        },
        {
            "codigo": "MERCADO",
            "nombre": "Mercado",
            "descripcion": "Baja demanda, sobrevaloración, tendencia negativa",
            "severidad_max": "medio",
            "impacto_tipico": -50
        },
        {
            "codigo": "LIQUIDEZ",
            "nombre": "Liquidez",
            "descripcion": "Dificultad para vender en plazo razonable",
            "severidad_max": "medio",
            "impacto_tipico": -40
        },
        {
            "codigo": "REGULATORIO",
            "nombre": "Regulatorio",
            "descripcion": "Exposición a cambios normativos adversos",
            "severidad_max": "medio",
            "impacto_tipico": -30
        },
        {
            "codigo": "SISMICO",
            "nombre": "Sísmico",
            "descripcion": "Ubicación en zona de alto riesgo sísmico",
            "severidad_max": "alto",
            "impacto_tipico": -60
        }
    ]
    
    return ResponseWrapper(success=True, data=tipos)


# ============================================================================
# EXPLICABILIDAD (SHAP)
# ============================================================================

@router.get(
    "/explicar/{id_evaluacion}",
    response_model=ResponseWrapper[FactorImpactoResponse],
    summary="Explicación SHAP del score"
)
async def explicar_score(
    id_evaluacion: str,
    top_factores: int = Query(10, ge=1, le=20),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Genera explicación interpretable del Credit Score usando SHAP.
    
    **SHAP (SHapley Additive exPlanations)**:
    - Identifica factores con mayor impacto positivo/negativo
    - Cuantifica contribución de cada variable
    - Permite entender decisiones del modelo ML
    """
    try:
        resultado = await servicio.explicar_shap(id_evaluacion, top_factores)
        
        if resultado is None:
            raise HTTPException(status_code=404, detail="Evaluación no encontrada")
        
        return ResponseWrapper(
            success=True,
            data=FactorImpactoResponse(
                id_evaluacion=id_evaluacion,
                score_base=resultado["base_value"],
                score_final=resultado["score_final"],
                factores_positivos=resultado["positivos"],
                factores_negativos=resultado["negativos"],
                top_factores=resultado["top_features"],
                grafico_waterfall_url=resultado.get("waterfall_url")
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SIMULACIONES
# ============================================================================

@router.post(
    "/simular",
    response_model=ResponseWrapper[SimulacionResponse],
    summary="Simular cambios en score"
)
async def simular_cambios(
    request: SimulacionRequest,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Simula impacto de cambios hipotéticos en el Credit Score.
    
    **Casos de uso**:
    - ¿Qué pasa si pago la hipoteca?
    - ¿Cómo afecta regularizar un permiso?
    - ¿Cuánto mejora renovando instalaciones?
    """
    try:
        resultado = await servicio.simular_cambios(
            id_evaluacion_base=request.id_evaluacion_base,
            cambios=request.cambios_propuestos
        )
        
        return ResponseWrapper(
            success=True,
            data=SimulacionResponse(
                score_actual=resultado["score_actual"],
                score_simulado=resultado["score_simulado"],
                diferencia=resultado["diferencia"],
                categoria_actual=resultado["categoria_actual"],
                categoria_simulada=resultado["categoria_simulada"],
                cambio_categoria=resultado["cambio_categoria"],
                detalle_impactos=resultado["impactos"],
                recomendacion=resultado["recomendacion"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/simular/optimizar",
    response_model=ResponseWrapper[dict],
    summary="Optimizar score"
)
async def optimizar_score(
    id_evaluacion: str = Query(...),
    score_objetivo: int = Query(..., ge=0, le=1000),
    presupuesto_max_uf: Optional[float] = Query(None),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Sugiere acciones para alcanzar un score objetivo.
    
    **Algoritmo**: Optimización costo-beneficio de acciones posibles
    """
    try:
        resultado = await servicio.optimizar_score(
            id_evaluacion,
            score_objetivo,
            presupuesto_max_uf
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "score_actual": resultado["score_actual"],
                "score_objetivo": score_objetivo,
                "score_alcanzable": resultado["score_alcanzable"],
                "acciones_recomendadas": resultado["acciones"],
                "costo_total_estimado_uf": resultado["costo_total"],
                "roi_estimado": resultado["roi"],
                "tiempo_estimado_meses": resultado["tiempo"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BENCHMARKS Y COMPARATIVOS
# ============================================================================

@router.get(
    "/benchmark/{comuna}",
    response_model=ResponseWrapper[BenchmarkResponse],
    summary="Benchmark scores por comuna"
)
async def get_benchmark_comuna(
    comuna: str,
    tipo_propiedad: Optional[str] = Query(None),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Obtiene estadísticas de Credit Score para una comuna.
    
    **Métricas**:
    - Score promedio, mediana, desviación
    - Distribución por categoría
    - Percentiles (P10, P25, P50, P75, P90)
    """
    try:
        resultado = await servicio.benchmark_comuna(comuna, tipo_propiedad)
        
        return ResponseWrapper(
            success=True,
            data=BenchmarkResponse(
                comuna=comuna,
                tipo_propiedad=tipo_propiedad,
                total_evaluaciones=resultado["total"],
                score_promedio=resultado["promedio"],
                score_mediana=resultado["mediana"],
                desviacion_estandar=resultado["std_dev"],
                distribucion_categorias=resultado["distribucion"],
                percentiles=resultado["percentiles"],
                periodo_datos=resultado["periodo"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ranking/comunas",
    response_model=ResponseWrapper[List[dict]],
    summary="Ranking comunas por score promedio"
)
async def get_ranking_comunas(
    region: Optional[str] = Query(None),
    top: int = Query(20, ge=5, le=100),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Ranking de comunas ordenadas por Credit Score promedio.
    """
    try:
        ranking = await servicio.ranking_comunas(region, top)
        return ResponseWrapper(success=True, data=ranking)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HISTORIAL
# ============================================================================

@router.get(
    "/historial/{rol_sii}",
    response_model=ResponseWrapper[HistorialScoreResponse],
    summary="Historial de scores"
)
async def get_historial_score(
    rol_sii: str,
    limite: int = Query(10, ge=1, le=50),
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """
    Historial de evaluaciones Credit Score para una propiedad.
    """
    try:
        resultado = await servicio.historial_scores(rol_sii, limite)
        
        return ResponseWrapper(
            success=True,
            data=HistorialScoreResponse(
                rol_sii=rol_sii,
                total_evaluaciones=resultado["total"],
                evaluaciones=resultado["evaluaciones"],
                tendencia=resultado["tendencia"],
                variacion_promedio=resultado["variacion"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_evaluacion}",
    response_model=ResponseWrapper[CreditScoreResponse],
    summary="Obtener evaluación por ID"
)
async def get_evaluacion(
    id_evaluacion: str,
    servicio: ServicioCreditScore = Depends(get_servicio)
):
    """Recupera evaluación existente por ID"""
    try:
        resultado = await servicio.obtener_evaluacion(id_evaluacion)
        
        if resultado is None:
            raise HTTPException(status_code=404, detail="Evaluación no encontrada")
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILIDADES
# ============================================================================

@router.get(
    "/categorias",
    response_model=ResponseWrapper[List[dict]],
    summary="Categorías de clasificación"
)
async def listar_categorias():
    """Lista categorías de clasificación crediticia con rangos"""
    categorias = [
        {"categoria": "AAA", "rango": "900-1000", "descripcion": "Excelente - Riesgo mínimo", "color": "#22c55e"},
        {"categoria": "AA", "rango": "800-899", "descripcion": "Muy bueno - Riesgo muy bajo", "color": "#84cc16"},
        {"categoria": "A", "rango": "700-799", "descripcion": "Bueno - Riesgo bajo", "color": "#eab308"},
        {"categoria": "BBB", "rango": "600-699", "descripcion": "Aceptable - Riesgo moderado bajo", "color": "#f97316"},
        {"categoria": "BB", "rango": "500-599", "descripcion": "Regular - Riesgo moderado", "color": "#f97316"},
        {"categoria": "B", "rango": "400-499", "descripcion": "Especulativo - Riesgo moderado alto", "color": "#ef4444"},
        {"categoria": "CCC", "rango": "300-399", "descripcion": "Débil - Riesgo alto", "color": "#dc2626"},
        {"categoria": "CC", "rango": "200-299", "descripcion": "Muy débil - Riesgo muy alto", "color": "#b91c1c"},
        {"categoria": "C", "rango": "100-199", "descripcion": "Extremadamente débil", "color": "#991b1b"},
        {"categoria": "D", "rango": "0-99", "descripcion": "Default / Irrecuperable", "color": "#7f1d1d"}
    ]
    
    return ResponseWrapper(success=True, data=categorias)


async def _log_evaluacion(id_evaluacion: str, rol_sii: Optional[str]):
    """Log asíncrono para analytics"""
    pass


@router.get("/health", include_in_schema=False)
async def health_check():
    return {
        "status": "healthy",
        "service": "credit_score",
        "timestamp": datetime.now().isoformat()
    }
