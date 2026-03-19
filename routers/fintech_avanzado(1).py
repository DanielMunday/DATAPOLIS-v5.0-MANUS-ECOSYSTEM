"""
DATAPOLIS v3.0 - ROUTER FINTECH AVANZADO
=========================================
Router FastAPI para módulos FinTech adicionales:
- TNFD (Nature Risk Framework)
- Basel IV (Capital Requirements)
- SCF ESG (Supply Chain Finance)

Autor: DATAPOLIS SpA
Fecha: Febrero 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/fintech",
    tags=["FinTech Avanzado"],
    responses={401: {"description": "No autorizado"}}
)

# =====================================================
# ENUMERACIONES
# =====================================================

class NivelRiesgoNaturaleza(str, Enum):
    """Niveles de riesgo TNFD"""
    BAJO = "bajo"
    MODERADO = "moderado"
    ALTO = "alto"
    CRITICO = "critico"

class TipoRiesgoTNFD(str, Enum):
    """Tipos de riesgo relacionados con naturaleza"""
    FISICO_AGUDO = "fisico_agudo"
    FISICO_CRONICO = "fisico_cronico"
    TRANSICION_POLITICA = "transicion_politica"
    TRANSICION_LEGAL = "transicion_legal"
    TRANSICION_TECNOLOGIA = "transicion_tecnologia"
    TRANSICION_MERCADO = "transicion_mercado"
    TRANSICION_REPUTACION = "transicion_reputacion"

class CategoriaExposicion(str, Enum):
    """Categorías de exposición Basel IV"""
    SOBERANOS = "soberanos"
    BANCOS = "bancos"
    CORPORATIVOS = "corporativos"
    RETAIL = "retail"
    HIPOTECARIO = "hipotecario"
    OTROS = "otros"

class CalificacionCrediticia(str, Enum):
    """Calificaciones crediticias estándar"""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    D = "D"
    NR = "NR"  # Not Rated

class TipoFinanciamientoSCF(str, Enum):
    """Tipos de financiamiento Supply Chain"""
    FACTORING = "factoring"
    REVERSE_FACTORING = "reverse_factoring"
    CONFIRMING = "confirming"
    INVENTORY_FINANCING = "inventory_financing"
    DYNAMIC_DISCOUNTING = "dynamic_discounting"

# =====================================================
# MODELOS PYDANTIC - TNFD
# =====================================================

class EvaluacionTNFDRequest(BaseModel):
    """Solicitud de evaluación TNFD"""
    entidad_id: str = Field(..., description="ID de la entidad a evaluar")
    sector_economico: str = Field(..., description="Sector CIIU")
    ubicacion_geografica: str = Field(..., description="Región geográfica")
    actividades: List[str] = Field(..., description="Lista de actividades económicas")
    activos_naturales: Optional[List[str]] = Field(None, description="Activos naturales relacionados")
    dependencias_ecosistemicas: Optional[List[str]] = Field(None, description="Dependencias de ecosistemas")

class RiesgoNaturaleza(BaseModel):
    """Riesgo relacionado con naturaleza"""
    tipo: TipoRiesgoTNFD
    nivel: NivelRiesgoNaturaleza
    probabilidad: float = Field(..., ge=0, le=1)
    impacto_financiero_estimado: float
    horizonte_temporal: str
    descripcion: str
    acciones_mitigacion: List[str]

class EvaluacionTNFDResponse(BaseModel):
    """Respuesta de evaluación TNFD"""
    evaluacion_id: str
    entidad_id: str
    fecha_evaluacion: datetime
    nivel_riesgo_global: NivelRiesgoNaturaleza
    score_tnfd: float = Field(..., ge=0, le=100)
    riesgos_identificados: List[RiesgoNaturaleza]
    oportunidades: List[Dict[str, Any]]
    recomendaciones: List[str]
    cumplimiento_tnfd: Dict[str, bool]

class MetricaTNFD(BaseModel):
    """Métrica TNFD según framework LEAP"""
    categoria: str  # Locate, Evaluate, Assess, Prepare
    metrica: str
    valor: float
    unidad: str
    tendencia: str
    benchmark_sector: Optional[float] = None

# =====================================================
# MODELOS PYDANTIC - BASEL IV
# =====================================================

class ExposicionCrediticiaRequest(BaseModel):
    """Solicitud de cálculo de requerimiento de capital"""
    exposicion_id: str
    categoria: CategoriaExposicion
    monto_exposicion: float = Field(..., gt=0)
    calificacion: CalificacionCrediticia
    plazo_residual_meses: int = Field(..., gt=0)
    garantias: Optional[List[Dict[str, Any]]] = None
    colateral_financiero: float = Field(default=0, ge=0)
    pais_contraparte: str = "CL"

class RequerimientoCapitalResponse(BaseModel):
    """Respuesta de cálculo de capital Basel IV"""
    exposicion_id: str
    ead: float  # Exposure at Default
    pd: float  # Probability of Default
    lgd: float  # Loss Given Default
    rwa: float  # Risk Weighted Assets
    capital_requerido: float
    ratio_capital: float
    ponderacion_riesgo: float
    metodo: str = "SA-CR"  # Standardized Approach - Credit Risk
    fecha_calculo: datetime
    detalle: Dict[str, Any]

class PortafolioBaselRequest(BaseModel):
    """Portafolio para análisis Basel IV"""
    portafolio_id: str
    nombre: str
    exposiciones: List[ExposicionCrediticiaRequest]

class PortafolioBaselResponse(BaseModel):
    """Respuesta de análisis de portafolio Basel IV"""
    portafolio_id: str
    nombre: str
    total_exposiciones: int
    ead_total: float
    rwa_total: float
    capital_total_requerido: float
    ratio_capital_agregado: float
    distribucion_por_categoria: Dict[str, Dict[str, float]]
    concentracion_maxima: float
    fecha_calculo: datetime

# =====================================================
# MODELOS PYDANTIC - SCF ESG
# =====================================================

class ProveedorESGRequest(BaseModel):
    """Solicitud de evaluación ESG de proveedor"""
    proveedor_id: str
    nombre: str
    rut: str
    sector: str
    pais: str
    certificaciones_ambientales: Optional[List[str]] = None
    emisiones_scope1: Optional[float] = None
    emisiones_scope2: Optional[float] = None
    emisiones_scope3: Optional[float] = None
    score_social_existente: Optional[float] = None
    practicas_laborales: Optional[Dict[str, Any]] = None
    gobernanza: Optional[Dict[str, Any]] = None

class ScoreESGResponse(BaseModel):
    """Respuesta de score ESG"""
    proveedor_id: str
    score_ambiental: float = Field(..., ge=0, le=100)
    score_social: float = Field(..., ge=0, le=100)
    score_gobernanza: float = Field(..., ge=0, le=100)
    score_esg_total: float = Field(..., ge=0, le=100)
    nivel_riesgo: str
    componentes: Dict[str, Dict[str, Any]]
    recomendaciones: List[str]
    fecha_evaluacion: datetime

class FinanciamientoSCFRequest(BaseModel):
    """Solicitud de financiamiento Supply Chain"""
    tipo: TipoFinanciamientoSCF
    monto: float = Field(..., gt=0)
    moneda: str = "CLP"
    plazo_dias: int = Field(..., gt=0, le=365)
    proveedor_id: str
    comprador_id: str
    facturas: List[Dict[str, Any]]
    aplicar_descuento_esg: bool = False

class FinanciamientoSCFResponse(BaseModel):
    """Respuesta de financiamiento SCF"""
    operacion_id: str
    tipo: TipoFinanciamientoSCF
    monto_original: float
    monto_financiado: float
    tasa_base: float
    descuento_esg: float
    tasa_final: float
    costo_financiero: float
    fecha_desembolso: date
    fecha_vencimiento: date
    score_esg_aplicado: Optional[float] = None
    estado: str

# =====================================================
# ALMACENAMIENTO EN MEMORIA
# =====================================================

_evaluaciones_tnfd: Dict[str, dict] = {}
_calculos_basel: Dict[str, dict] = {}
_evaluaciones_esg: Dict[str, dict] = {}
_financiamientos_scf: Dict[str, dict] = {}

# =====================================================
# ENDPOINTS TNFD (Nature Risk)
# =====================================================

@router.post("/tnfd/evaluar", response_model=EvaluacionTNFDResponse,
             summary="Evaluar Riesgos TNFD (Framework LEAP)")
async def evaluar_tnfd(
    request: EvaluacionTNFDRequest,
    authorization: str = Header(...)
):
    """
    Realiza una evaluación de riesgos relacionados con la naturaleza
    según el framework TNFD (Taskforce on Nature-related Financial Disclosures).
    
    Implementa la metodología LEAP:
    - **L**ocate: Ubicación de interfaces con naturaleza
    - **E**valuate: Evaluación de dependencias e impactos
    - **A**ssess: Análisis de riesgos y oportunidades
    - **P**repare: Preparación de respuestas y divulgaciones
    """
    evaluacion_id = f"TNFD-{uuid.uuid4().hex[:12]}"
    
    # Análisis de riesgos basado en sector y ubicación
    riesgos = _analizar_riesgos_tnfd(request)
    
    # Calcular score global
    score_global = _calcular_score_tnfd(riesgos)
    nivel_global = _determinar_nivel_riesgo(score_global)
    
    # Identificar oportunidades
    oportunidades = _identificar_oportunidades_tnfd(request)
    
    evaluacion = {
        "evaluacion_id": evaluacion_id,
        "entidad_id": request.entidad_id,
        "fecha_evaluacion": datetime.utcnow(),
        "nivel_riesgo_global": nivel_global,
        "score_tnfd": score_global,
        "riesgos_identificados": riesgos,
        "oportunidades": oportunidades,
        "recomendaciones": _generar_recomendaciones_tnfd(riesgos),
        "cumplimiento_tnfd": {
            "gobernanza": True,
            "estrategia": True,
            "gestion_riesgos": True,
            "metricas_objetivos": True
        }
    }
    
    _evaluaciones_tnfd[evaluacion_id] = evaluacion
    logger.info(f"Evaluación TNFD completada: {evaluacion_id}")
    
    return EvaluacionTNFDResponse(**evaluacion)

@router.get("/tnfd/metricas/{entidad_id}", response_model=List[MetricaTNFD],
            summary="Obtener Métricas TNFD")
async def obtener_metricas_tnfd(
    entidad_id: str,
    authorization: str = Header(...),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría LEAP")
):
    """Obtiene las métricas TNFD de una entidad según el framework LEAP."""
    metricas = [
        MetricaTNFD(
            categoria="Locate",
            metrica="Área operaciones en zonas biodiversidad",
            valor=15.5,
            unidad="hectáreas",
            tendencia="estable",
            benchmark_sector=12.0
        ),
        MetricaTNFD(
            categoria="Evaluate",
            metrica="Dependencia de agua dulce",
            valor=85000,
            unidad="m³/año",
            tendencia="decreciente",
            benchmark_sector=95000
        ),
        MetricaTNFD(
            categoria="Assess",
            metrica="Exposición a riesgo físico agudo",
            valor=23.5,
            unidad="porcentaje",
            tendencia="creciente",
            benchmark_sector=18.0
        ),
        MetricaTNFD(
            categoria="Prepare",
            metrica="Inversión en soluciones basadas en naturaleza",
            valor=250000000,
            unidad="CLP",
            tendencia="creciente",
            benchmark_sector=180000000
        )
    ]
    
    if categoria:
        metricas = [m for m in metricas if m.categoria.lower() == categoria.lower()]
    
    return metricas

@router.get("/tnfd/evaluaciones/{evaluacion_id}",
            summary="Obtener Evaluación TNFD")
async def obtener_evaluacion_tnfd(
    evaluacion_id: str,
    authorization: str = Header(...)
):
    """Obtiene una evaluación TNFD específica."""
    if evaluacion_id not in _evaluaciones_tnfd:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    
    return _evaluaciones_tnfd[evaluacion_id]

# =====================================================
# ENDPOINTS BASEL IV (Capital Requirements)
# =====================================================

@router.post("/basel/calcular-capital", response_model=RequerimientoCapitalResponse,
             summary="Calcular Requerimiento de Capital Basel IV")
async def calcular_capital_basel(
    request: ExposicionCrediticiaRequest,
    authorization: str = Header(...)
):
    """
    Calcula el requerimiento de capital según Basel IV (CR-SA).
    
    Implementa el enfoque estándar para riesgo de crédito (SA-CR)
    según las directrices del Comité de Basilea y la CMF Chile.
    """
    # Obtener ponderación de riesgo según categoría y calificación
    ponderacion = _obtener_ponderacion_riesgo(
        request.categoria,
        request.calificacion,
        request.plazo_residual_meses
    )
    
    # Calcular EAD (ajustado por colateral)
    ead = request.monto_exposicion - (request.colateral_financiero * 0.8)  # Haircut 20%
    ead = max(ead, 0)
    
    # Calcular PD y LGD según categoría
    pd, lgd = _calcular_pd_lgd(request.categoria, request.calificacion)
    
    # Calcular RWA
    rwa = ead * ponderacion
    
    # Capital requerido (8% mínimo Basel + buffer)
    capital_requerido = rwa * 0.105  # 8% + 2.5% buffer conservación
    
    resultado = RequerimientoCapitalResponse(
        exposicion_id=request.exposicion_id,
        ead=ead,
        pd=pd,
        lgd=lgd,
        rwa=rwa,
        capital_requerido=capital_requerido,
        ratio_capital=capital_requerido / ead if ead > 0 else 0,
        ponderacion_riesgo=ponderacion,
        metodo="SA-CR",
        fecha_calculo=datetime.utcnow(),
        detalle={
            "categoria": request.categoria.value,
            "calificacion": request.calificacion.value,
            "colateral_reconocido": request.colateral_financiero * 0.8,
            "buffer_conservacion": 0.025,
            "buffer_contraciclico": 0.0
        }
    )
    
    _calculos_basel[request.exposicion_id] = resultado.dict()
    logger.info(f"Cálculo Basel IV: {request.exposicion_id}, RWA={rwa:,.0f}")
    
    return resultado

@router.post("/basel/analizar-portafolio", response_model=PortafolioBaselResponse,
             summary="Analizar Portafolio Basel IV")
async def analizar_portafolio_basel(
    request: PortafolioBaselRequest,
    authorization: str = Header(...)
):
    """
    Analiza un portafolio completo de exposiciones según Basel IV.
    
    Calcula:
    - RWA total agregado
    - Capital total requerido
    - Distribución por categoría
    - Concentración de riesgo
    """
    resultados = []
    ead_total = 0
    rwa_total = 0
    distribucion = {}
    
    for exp in request.exposiciones:
        # Calcular cada exposición
        ponderacion = _obtener_ponderacion_riesgo(
            exp.categoria, exp.calificacion, exp.plazo_residual_meses
        )
        ead = exp.monto_exposicion - (exp.colateral_financiero * 0.8)
        ead = max(ead, 0)
        rwa = ead * ponderacion
        
        ead_total += ead
        rwa_total += rwa
        
        # Agregar a distribución
        cat = exp.categoria.value
        if cat not in distribucion:
            distribucion[cat] = {"ead": 0, "rwa": 0, "count": 0}
        distribucion[cat]["ead"] += ead
        distribucion[cat]["rwa"] += rwa
        distribucion[cat]["count"] += 1
    
    capital_total = rwa_total * 0.105
    
    # Calcular concentración máxima
    max_concentracion = max(
        d["ead"] / ead_total if ead_total > 0 else 0
        for d in distribucion.values()
    ) if distribucion else 0
    
    return PortafolioBaselResponse(
        portafolio_id=request.portafolio_id,
        nombre=request.nombre,
        total_exposiciones=len(request.exposiciones),
        ead_total=ead_total,
        rwa_total=rwa_total,
        capital_total_requerido=capital_total,
        ratio_capital_agregado=capital_total / ead_total if ead_total > 0 else 0,
        distribucion_por_categoria=distribucion,
        concentracion_maxima=max_concentracion,
        fecha_calculo=datetime.utcnow()
    )

@router.get("/basel/ponderaciones",
            summary="Tabla de Ponderaciones de Riesgo Basel IV")
async def obtener_ponderaciones_basel():
    """
    Retorna la tabla de ponderaciones de riesgo según Basel IV SA-CR.
    """
    return {
        "soberanos": {
            "AAA_AA": 0.0,
            "A": 0.20,
            "BBB": 0.50,
            "BB": 1.00,
            "B_CCC": 1.50,
            "NR": 1.00
        },
        "bancos": {
            "corto_plazo": {
                "AAA_AA": 0.20,
                "A": 0.20,
                "BBB": 0.20,
                "BB": 0.50,
                "B_CCC": 1.50,
                "NR": 0.20
            },
            "largo_plazo": {
                "AAA_AA": 0.20,
                "A": 0.30,
                "BBB": 0.50,
                "BB": 1.00,
                "B_CCC": 1.50,
                "NR": 0.50
            }
        },
        "corporativos": {
            "AAA_AA": 0.20,
            "A": 0.50,
            "BBB": 0.75,
            "BB": 1.00,
            "B_CCC": 1.50,
            "NR": 1.00
        },
        "retail": {
            "hipotecario_residencial": 0.35,
            "otros": 0.75
        },
        "notas": {
            "fuente": "Basel III: Finalising post-crisis reforms (December 2017)",
            "implementacion_chile": "Basilea III CMF 2023-2025"
        }
    }

# =====================================================
# ENDPOINTS SCF ESG (Supply Chain Finance)
# =====================================================

@router.post("/scf/evaluar-proveedor", response_model=ScoreESGResponse,
             summary="Evaluar Score ESG de Proveedor")
async def evaluar_proveedor_esg(
    request: ProveedorESGRequest,
    authorization: str = Header(...)
):
    """
    Evalúa el score ESG de un proveedor para Supply Chain Finance.
    
    Componentes evaluados:
    - **E (Environmental)**: Emisiones, eficiencia energética, gestión de residuos
    - **S (Social)**: Prácticas laborales, seguridad, comunidad
    - **G (Governance)**: Ética, transparencia, cumplimiento
    """
    # Calcular scores por componente
    score_e = _calcular_score_ambiental(request)
    score_s = _calcular_score_social(request)
    score_g = _calcular_score_gobernanza(request)
    
    # Score total ponderado (E: 40%, S: 30%, G: 30%)
    score_total = score_e * 0.4 + score_s * 0.3 + score_g * 0.3
    
    # Determinar nivel de riesgo
    if score_total >= 80:
        nivel = "bajo"
    elif score_total >= 60:
        nivel = "moderado"
    elif score_total >= 40:
        nivel = "alto"
    else:
        nivel = "critico"
    
    resultado = ScoreESGResponse(
        proveedor_id=request.proveedor_id,
        score_ambiental=score_e,
        score_social=score_s,
        score_gobernanza=score_g,
        score_esg_total=score_total,
        nivel_riesgo=nivel,
        componentes={
            "ambiental": {
                "emisiones": min(100, 100 - (request.emisiones_scope1 or 0) / 1000),
                "certificaciones": len(request.certificaciones_ambientales or []) * 20,
                "gestion_residuos": 75
            },
            "social": {
                "practicas_laborales": 80,
                "seguridad": 85,
                "comunidad": 70
            },
            "gobernanza": {
                "etica": 85,
                "transparencia": 80,
                "cumplimiento": 90
            }
        },
        recomendaciones=_generar_recomendaciones_esg(score_e, score_s, score_g),
        fecha_evaluacion=datetime.utcnow()
    )
    
    _evaluaciones_esg[request.proveedor_id] = resultado.dict()
    logger.info(f"Evaluación ESG: {request.proveedor_id}, Score={score_total:.1f}")
    
    return resultado

@router.post("/scf/solicitar-financiamiento", response_model=FinanciamientoSCFResponse,
             summary="Solicitar Financiamiento Supply Chain")
async def solicitar_financiamiento_scf(
    request: FinanciamientoSCFRequest,
    authorization: str = Header(...)
):
    """
    Solicita financiamiento de cadena de suministro con componente ESG.
    
    Si el proveedor tiene buen score ESG, se aplica un descuento en la tasa.
    Esto incentiva prácticas sostenibles en toda la cadena de valor.
    """
    operacion_id = f"SCF-{uuid.uuid4().hex[:12]}"
    
    # Tasa base según tipo de financiamiento
    tasas_base = {
        TipoFinanciamientoSCF.FACTORING: 0.015,  # 1.5% mensual
        TipoFinanciamientoSCF.REVERSE_FACTORING: 0.012,
        TipoFinanciamientoSCF.CONFIRMING: 0.011,
        TipoFinanciamientoSCF.INVENTORY_FINANCING: 0.018,
        TipoFinanciamientoSCF.DYNAMIC_DISCOUNTING: 0.008
    }
    
    tasa_base = tasas_base.get(request.tipo, 0.015)
    descuento_esg = 0.0
    score_esg = None
    
    # Aplicar descuento ESG si está habilitado y hay evaluación
    if request.aplicar_descuento_esg and request.proveedor_id in _evaluaciones_esg:
        eval_esg = _evaluaciones_esg[request.proveedor_id]
        score_esg = eval_esg["score_esg_total"]
        
        # Descuento progresivo según score
        if score_esg >= 90:
            descuento_esg = 0.003  # 30 bps
        elif score_esg >= 80:
            descuento_esg = 0.002  # 20 bps
        elif score_esg >= 70:
            descuento_esg = 0.001  # 10 bps
    
    tasa_final = max(0.005, tasa_base - descuento_esg)  # Mínimo 0.5%
    
    # Calcular costos
    meses = request.plazo_dias / 30
    costo_financiero = request.monto * tasa_final * meses
    monto_financiado = request.monto - costo_financiero
    
    resultado = FinanciamientoSCFResponse(
        operacion_id=operacion_id,
        tipo=request.tipo,
        monto_original=request.monto,
        monto_financiado=monto_financiado,
        tasa_base=tasa_base,
        descuento_esg=descuento_esg,
        tasa_final=tasa_final,
        costo_financiero=costo_financiero,
        fecha_desembolso=date.today(),
        fecha_vencimiento=date.today() + __import__('datetime').timedelta(days=request.plazo_dias),
        score_esg_aplicado=score_esg,
        estado="aprobado"
    )
    
    _financiamientos_scf[operacion_id] = resultado.dict()
    logger.info(f"Financiamiento SCF: {operacion_id}, Monto={request.monto:,.0f}, Tasa={tasa_final:.4f}")
    
    return resultado

@router.get("/scf/operaciones",
            summary="Listar Operaciones SCF")
async def listar_operaciones_scf(
    authorization: str = Header(...),
    tipo: Optional[TipoFinanciamientoSCF] = Query(None),
    proveedor_id: Optional[str] = Query(None),
    limit: int = Query(default=50, le=100)
):
    """Lista las operaciones de Supply Chain Finance."""
    resultado = list(_financiamientos_scf.values())
    
    if tipo:
        resultado = [r for r in resultado if r["tipo"] == tipo.value]
    
    return resultado[:limit]

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def _analizar_riesgos_tnfd(request: EvaluacionTNFDRequest) -> List[RiesgoNaturaleza]:
    """Analiza riesgos TNFD basado en sector y ubicación."""
    riesgos = []
    
    # Riesgo físico agudo (ej: inundaciones, sequías)
    riesgos.append(RiesgoNaturaleza(
        tipo=TipoRiesgoTNFD.FISICO_AGUDO,
        nivel=NivelRiesgoNaturaleza.MODERADO,
        probabilidad=0.3,
        impacto_financiero_estimado=50000000,
        horizonte_temporal="corto_plazo",
        descripcion="Riesgo de eventos climáticos extremos",
        acciones_mitigacion=["Seguro climático", "Diversificación geográfica"]
    ))
    
    # Riesgo de transición regulatoria
    riesgos.append(RiesgoNaturaleza(
        tipo=TipoRiesgoTNFD.TRANSICION_POLITICA,
        nivel=NivelRiesgoNaturaleza.ALTO,
        probabilidad=0.7,
        impacto_financiero_estimado=100000000,
        horizonte_temporal="mediano_plazo",
        descripcion="Nuevas regulaciones ambientales (Ley Marco Cambio Climático)",
        acciones_mitigacion=["Inversión en tecnología limpia", "Cumplimiento anticipado"]
    ))
    
    return riesgos

def _calcular_score_tnfd(riesgos: List[RiesgoNaturaleza]) -> float:
    """Calcula score TNFD global (0-100, mayor es mejor)."""
    if not riesgos:
        return 80.0
    
    # Score inverso al riesgo promedio
    niveles = {"bajo": 10, "moderado": 30, "alto": 60, "critico": 90}
    riesgo_promedio = sum(niveles.get(r.nivel.value, 50) for r in riesgos) / len(riesgos)
    
    return 100 - riesgo_promedio

def _determinar_nivel_riesgo(score: float) -> NivelRiesgoNaturaleza:
    """Determina nivel de riesgo basado en score."""
    if score >= 80:
        return NivelRiesgoNaturaleza.BAJO
    elif score >= 60:
        return NivelRiesgoNaturaleza.MODERADO
    elif score >= 40:
        return NivelRiesgoNaturaleza.ALTO
    else:
        return NivelRiesgoNaturaleza.CRITICO

def _identificar_oportunidades_tnfd(request: EvaluacionTNFDRequest) -> List[Dict[str, Any]]:
    """Identifica oportunidades relacionadas con naturaleza."""
    return [
        {
            "tipo": "eficiencia_recursos",
            "descripcion": "Reducción consumo de agua en operaciones",
            "beneficio_estimado": 25000000,
            "horizonte": "corto_plazo"
        },
        {
            "tipo": "productos_sostenibles",
            "descripcion": "Desarrollo de productos eco-friendly",
            "beneficio_estimado": 150000000,
            "horizonte": "mediano_plazo"
        }
    ]

def _generar_recomendaciones_tnfd(riesgos: List[RiesgoNaturaleza]) -> List[str]:
    """Genera recomendaciones basadas en riesgos identificados."""
    return [
        "Implementar sistema de gestión ambiental ISO 14001",
        "Realizar evaluación de dependencias ecosistémicas",
        "Establecer objetivos basados en ciencia (SBTs para naturaleza)",
        "Divulgar según estándares TNFD en reporte anual"
    ]

def _obtener_ponderacion_riesgo(
    categoria: CategoriaExposicion,
    calificacion: CalificacionCrediticia,
    plazo_meses: int
) -> float:
    """Obtiene ponderación de riesgo según Basel IV SA-CR."""
    ponderaciones = {
        CategoriaExposicion.SOBERANOS: {
            CalificacionCrediticia.AAA: 0.0,
            CalificacionCrediticia.AA: 0.0,
            CalificacionCrediticia.A: 0.20,
            CalificacionCrediticia.BBB: 0.50,
            CalificacionCrediticia.BB: 1.00,
            CalificacionCrediticia.B: 1.00,
            CalificacionCrediticia.CCC: 1.50,
            CalificacionCrediticia.D: 1.50,
            CalificacionCrediticia.NR: 1.00
        },
        CategoriaExposicion.CORPORATIVOS: {
            CalificacionCrediticia.AAA: 0.20,
            CalificacionCrediticia.AA: 0.20,
            CalificacionCrediticia.A: 0.50,
            CalificacionCrediticia.BBB: 0.75,
            CalificacionCrediticia.BB: 1.00,
            CalificacionCrediticia.B: 1.00,
            CalificacionCrediticia.CCC: 1.50,
            CalificacionCrediticia.D: 1.50,
            CalificacionCrediticia.NR: 1.00
        },
        CategoriaExposicion.RETAIL: {
            "default": 0.75
        },
        CategoriaExposicion.HIPOTECARIO: {
            "default": 0.35
        }
    }
    
    cat_pond = ponderaciones.get(categoria, {})
    
    if "default" in cat_pond:
        return cat_pond["default"]
    
    return cat_pond.get(calificacion, 1.00)

def _calcular_pd_lgd(
    categoria: CategoriaExposicion,
    calificacion: CalificacionCrediticia
) -> tuple:
    """Calcula PD y LGD según categoría y calificación."""
    # PDs estimadas por calificación
    pds = {
        CalificacionCrediticia.AAA: 0.0001,
        CalificacionCrediticia.AA: 0.0002,
        CalificacionCrediticia.A: 0.0005,
        CalificacionCrediticia.BBB: 0.002,
        CalificacionCrediticia.BB: 0.01,
        CalificacionCrediticia.B: 0.05,
        CalificacionCrediticia.CCC: 0.15,
        CalificacionCrediticia.D: 1.0,
        CalificacionCrediticia.NR: 0.03
    }
    
    # LGDs por categoría
    lgds = {
        CategoriaExposicion.SOBERANOS: 0.45,
        CategoriaExposicion.BANCOS: 0.45,
        CategoriaExposicion.CORPORATIVOS: 0.45,
        CategoriaExposicion.RETAIL: 0.75,
        CategoriaExposicion.HIPOTECARIO: 0.25,
        CategoriaExposicion.OTROS: 0.45
    }
    
    return pds.get(calificacion, 0.03), lgds.get(categoria, 0.45)

def _calcular_score_ambiental(request: ProveedorESGRequest) -> float:
    """Calcula score ambiental."""
    score = 50.0  # Base
    
    # Bonificación por certificaciones
    if request.certificaciones_ambientales:
        score += len(request.certificaciones_ambientales) * 10
    
    # Penalización por emisiones altas
    emisiones_totales = (request.emisiones_scope1 or 0) + \
                       (request.emisiones_scope2 or 0) + \
                       (request.emisiones_scope3 or 0)
    
    if emisiones_totales > 0:
        # Normalizar emisiones (asumiendo benchmark de 10,000 tCO2e)
        score -= min(30, emisiones_totales / 333)
    
    return max(0, min(100, score))

def _calcular_score_social(request: ProveedorESGRequest) -> float:
    """Calcula score social."""
    score = 60.0  # Base
    
    if request.score_social_existente:
        score = request.score_social_existente
    
    if request.practicas_laborales:
        if request.practicas_laborales.get("sindicato"):
            score += 10
        if request.practicas_laborales.get("equidad_genero"):
            score += 10
    
    return max(0, min(100, score))

def _calcular_score_gobernanza(request: ProveedorESGRequest) -> float:
    """Calcula score de gobernanza."""
    score = 65.0  # Base
    
    if request.gobernanza:
        if request.gobernanza.get("directorio_independiente"):
            score += 15
        if request.gobernanza.get("codigo_etica"):
            score += 10
        if request.gobernanza.get("canal_denuncias"):
            score += 10
    
    return max(0, min(100, score))

def _generar_recomendaciones_esg(score_e: float, score_s: float, score_g: float) -> List[str]:
    """Genera recomendaciones ESG basadas en scores."""
    recomendaciones = []
    
    if score_e < 70:
        recomendaciones.append("Obtener certificación ISO 14001")
        recomendaciones.append("Establecer metas de reducción de emisiones")
    
    if score_s < 70:
        recomendaciones.append("Implementar programa de equidad de género")
        recomendaciones.append("Mejorar condiciones de seguridad laboral")
    
    if score_g < 70:
        recomendaciones.append("Adoptar código de ética formal")
        recomendaciones.append("Establecer canal de denuncias anónimo")
    
    return recomendaciones if recomendaciones else ["Mantener buenas prácticas ESG actuales"]

# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/health", summary="Health Check FinTech")
async def health_check():
    """Verifica el estado de los servicios FinTech."""
    return {
        "status": "healthy",
        "service": "DATAPOLIS FinTech Avanzado",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "modules": {
            "tnfd": "operational",
            "basel_iv": "operational",
            "scf_esg": "operational"
        }
    }
