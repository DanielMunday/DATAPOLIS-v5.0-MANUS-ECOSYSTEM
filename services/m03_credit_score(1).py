"""
DATAPOLIS v3.0 - M03 Credit Score Service
==========================================
Servicio de evaluación crediticia inmobiliaria con scoring multidimensional.

Características:
- Score 0-1000 con categorías AAA a D
- 5 dimensiones: Ubicación, Legal, Financiero, Técnico, Mercado
- XGBoost para predicción de riesgo
- SHAP para explicabilidad
- Integración con SII, CMF, Conservador de Bienes Raíces

Autor: DATAPOLIS SpA
Versión: 3.0.0
Licencia: Propietaria
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

# ML imports
try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    import shap
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES Y CONSTANTES
# =============================================================================

class CategoriaScore(str, Enum):
    """Categorías de credit score inmobiliario."""
    AAA = "AAA"  # 900-1000: Excelente - Riesgo mínimo
    AA = "AA"    # 800-899: Muy bueno - Riesgo muy bajo
    A = "A"      # 700-799: Bueno - Riesgo bajo
    BBB = "BBB"  # 600-699: Adecuado - Riesgo moderado
    BB = "BB"    # 500-599: Aceptable - Riesgo medio
    B = "B"      # 400-499: Regular - Riesgo medio-alto
    CCC = "CCC"  # 300-399: Débil - Riesgo alto
    CC = "CC"    # 200-299: Muy débil - Riesgo muy alto
    C = "C"      # 100-199: Crítico - Riesgo extremo
    D = "D"      # 0-99: Default/Impago


class DimensionScore(str, Enum):
    """Dimensiones de evaluación."""
    UBICACION = "ubicacion"
    LEGAL = "legal"
    FINANCIERO = "financiero"
    TECNICO = "tecnico"
    MERCADO = "mercado"


class TipoRiesgo(str, Enum):
    """Tipos de riesgo identificados."""
    TITULO = "titulo"
    GRAVAMEN = "gravamen"
    LITIGIO = "litigio"
    URBANISTICO = "urbanistico"
    AMBIENTAL = "ambiental"
    ESTRUCTURAL = "estructural"
    MERCADO = "mercado"
    LIQUIDEZ = "liquidez"
    REGULATORIO = "regulatorio"
    SISMICO = "sismico"


# Ponderaciones por dimensión (suman 100%)
PONDERACIONES_DIMENSION = {
    DimensionScore.UBICACION: 0.20,
    DimensionScore.LEGAL: 0.25,
    DimensionScore.FINANCIERO: 0.25,
    DimensionScore.TECNICO: 0.15,
    DimensionScore.MERCADO: 0.15,
}

# Rangos de score por categoría
RANGOS_CATEGORIA = {
    CategoriaScore.AAA: (900, 1000),
    CategoriaScore.AA: (800, 899),
    CategoriaScore.A: (700, 799),
    CategoriaScore.BBB: (600, 699),
    CategoriaScore.BB: (500, 599),
    CategoriaScore.B: (400, 499),
    CategoriaScore.CCC: (300, 399),
    CategoriaScore.CC: (200, 299),
    CategoriaScore.C: (100, 199),
    CategoriaScore.D: (0, 99),
}

# Factores de ajuste por zona (Santiago)
FACTORES_ZONA_SANTIAGO = {
    "vitacura": 1.15,
    "las_condes": 1.12,
    "lo_barnechea": 1.10,
    "providencia": 1.08,
    "nunoa": 1.05,
    "la_reina": 1.05,
    "santiago_centro": 1.00,
    "macul": 0.98,
    "penalolen": 0.95,
    "la_florida": 0.95,
    "maipu": 0.92,
    "puente_alto": 0.88,
    "san_bernardo": 0.85,
    "default": 0.90,
}

# Factores por tipo de propiedad
FACTORES_TIPO_PROPIEDAD = {
    "departamento": 1.00,
    "casa": 1.02,
    "oficina": 0.95,
    "local_comercial": 0.90,
    "bodega": 0.85,
    "estacionamiento": 0.80,
    "terreno": 0.75,
    "industrial": 0.70,
    "agricola": 0.65,
}

# Penalizaciones por riesgo
PENALIZACIONES_RIESGO = {
    TipoRiesgo.TITULO: -150,        # Problemas de título
    TipoRiesgo.GRAVAMEN: -100,      # Hipotecas/gravámenes
    TipoRiesgo.LITIGIO: -200,       # Litigios activos
    TipoRiesgo.URBANISTICO: -80,    # Incumplimientos urbanísticos
    TipoRiesgo.AMBIENTAL: -120,     # Riesgos ambientales
    TipoRiesgo.ESTRUCTURAL: -100,   # Problemas estructurales
    TipoRiesgo.MERCADO: -60,        # Riesgo de mercado
    TipoRiesgo.LIQUIDEZ: -70,       # Baja liquidez
    TipoRiesgo.REGULATORIO: -50,    # Riesgo regulatorio
    TipoRiesgo.SISMICO: -40,        # Zona sísmica alta
}


# =============================================================================
# DATACLASSES PARA RESULTADOS
# =============================================================================

@dataclass
class ComponenteScore:
    """Componente individual del score."""
    dimension: DimensionScore
    score: float  # 0-1000
    ponderacion: float
    score_ponderado: float
    factores_positivos: List[str] = field(default_factory=list)
    factores_negativos: List[str] = field(default_factory=list)
    riesgos_identificados: List[Dict[str, Any]] = field(default_factory=list)
    confianza: float = 0.0  # 0-100%


@dataclass
class RiesgoIdentificado:
    """Riesgo identificado en la evaluación."""
    tipo: TipoRiesgo
    descripcion: str
    severidad: str  # bajo, medio, alto, critico
    impacto_score: int
    mitigacion_sugerida: Optional[str] = None
    fuente: Optional[str] = None
    fecha_deteccion: datetime = field(default_factory=datetime.now)


@dataclass
class ExplicacionSHAP:
    """Explicación SHAP del score."""
    feature: str
    valor: float
    impacto_shap: float
    direccion: str  # positivo, negativo
    descripcion: str


@dataclass
class ResultadoCreditScore:
    """Resultado completo del credit score."""
    # Identificación
    propiedad_id: str
    rol_sii: Optional[str]
    fecha_evaluacion: datetime
    
    # Score principal
    score_total: int  # 0-1000
    categoria: CategoriaScore
    
    # Componentes
    componentes: Dict[DimensionScore, ComponenteScore]
    
    # Riesgos
    riesgos: List[RiesgoIdentificado]
    nivel_riesgo_global: str  # bajo, medio, alto, critico
    
    # Explicabilidad
    explicaciones_shap: List[ExplicacionSHAP]
    factores_principales: List[str]
    
    # Métricas
    confianza_evaluacion: float  # 0-100%
    completitud_datos: float  # 0-100%
    
    # Recomendaciones
    recomendaciones: List[str]
    
    # Metadata
    version_modelo: str = "3.0.0"
    tiempo_procesamiento_ms: float = 0.0


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class CreditScoreService:
    """
    Servicio de Credit Score Inmobiliario.
    
    Evalúa propiedades en 5 dimensiones:
    1. Ubicación: Zona, accesibilidad, servicios, plusvalía
    2. Legal: Títulos, gravámenes, litigios, permisos
    3. Financiero: Valor, rentabilidad, liquidez, deuda
    4. Técnico: Estado, antigüedad, materiales, mantención
    5. Mercado: Demanda, oferta, tendencias, competencia
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.modelo_xgb = None
        self.scaler = None
        self.shap_explainer = None
        self._cargar_modelo()
    
    def _cargar_modelo(self) -> None:
        """Carga modelo XGBoost pre-entrenado si existe."""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available")
            return
            
        try:
            modelo_path = settings.ML_MODEL_PATH / "credit_score_xgb.joblib"
            scaler_path = settings.ML_MODEL_PATH / "credit_score_scaler.joblib"
            
            if modelo_path.exists():
                self.modelo_xgb = joblib.load(modelo_path)
                logger.info("Modelo XGBoost cargado")
            
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                logger.info("Scaler cargado")
                
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
    
    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================
    
    async def evaluar(
        self,
        propiedad_id: str,
        datos_propiedad: Dict[str, Any],
        datos_legales: Optional[Dict[str, Any]] = None,
        datos_financieros: Optional[Dict[str, Any]] = None,
        datos_tecnicos: Optional[Dict[str, Any]] = None,
        datos_mercado: Optional[Dict[str, Any]] = None,
        incluir_shap: bool = True,
    ) -> ResultadoCreditScore:
        """
        Evalúa credit score completo de una propiedad.
        
        Args:
            propiedad_id: ID único de la propiedad
            datos_propiedad: Datos básicos (ubicación, tipo, superficie)
            datos_legales: Información legal (títulos, gravámenes)
            datos_financieros: Datos financieros (valor, rentabilidad)
            datos_tecnicos: Estado técnico (antigüedad, materiales)
            datos_mercado: Contexto de mercado (oferta, demanda)
            incluir_shap: Si incluir explicaciones SHAP
            
        Returns:
            ResultadoCreditScore con evaluación completa
        """
        inicio = datetime.now()
        
        # Inicializar contenedores
        componentes: Dict[DimensionScore, ComponenteScore] = {}
        riesgos: List[RiesgoIdentificado] = []
        
        # 1. Evaluar cada dimensión
        componentes[DimensionScore.UBICACION] = await self._evaluar_ubicacion(
            datos_propiedad, riesgos
        )
        
        componentes[DimensionScore.LEGAL] = await self._evaluar_legal(
            datos_propiedad, datos_legales or {}, riesgos
        )
        
        componentes[DimensionScore.FINANCIERO] = await self._evaluar_financiero(
            datos_propiedad, datos_financieros or {}, riesgos
        )
        
        componentes[DimensionScore.TECNICO] = await self._evaluar_tecnico(
            datos_propiedad, datos_tecnicos or {}, riesgos
        )
        
        componentes[DimensionScore.MERCADO] = await self._evaluar_mercado(
            datos_propiedad, datos_mercado or {}, riesgos
        )
        
        # 2. Calcular score total ponderado
        score_total = self._calcular_score_total(componentes)
        
        # 3. Aplicar penalizaciones por riesgos
        score_ajustado = self._aplicar_penalizaciones(score_total, riesgos)
        
        # 4. Determinar categoría
        categoria = self._determinar_categoria(score_ajustado)
        
        # 5. Calcular métricas de confianza
        confianza = self._calcular_confianza(componentes)
        completitud = self._calcular_completitud(
            datos_propiedad, datos_legales, datos_financieros,
            datos_tecnicos, datos_mercado
        )
        
        # 6. Generar explicaciones SHAP si disponible
        explicaciones_shap = []
        if incluir_shap and ML_AVAILABLE and self.modelo_xgb:
            explicaciones_shap = await self._generar_explicaciones_shap(
                datos_propiedad, datos_legales or {},
                datos_financieros or {}, datos_tecnicos or {},
                datos_mercado or {}
            )
        
        # 7. Identificar factores principales
        factores_principales = self._identificar_factores_principales(
            componentes, explicaciones_shap
        )
        
        # 8. Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(
            categoria, riesgos, componentes
        )
        
        # 9. Determinar nivel de riesgo global
        nivel_riesgo = self._determinar_nivel_riesgo(riesgos, score_ajustado)
        
        tiempo_ms = (datetime.now() - inicio).total_seconds() * 1000
        
        return ResultadoCreditScore(
            propiedad_id=propiedad_id,
            rol_sii=datos_propiedad.get("rol_sii"),
            fecha_evaluacion=datetime.now(),
            score_total=score_ajustado,
            categoria=categoria,
            componentes=componentes,
            riesgos=riesgos,
            nivel_riesgo_global=nivel_riesgo,
            explicaciones_shap=explicaciones_shap,
            factores_principales=factores_principales,
            confianza_evaluacion=confianza,
            completitud_datos=completitud,
            recomendaciones=recomendaciones,
            tiempo_procesamiento_ms=tiempo_ms,
        )
    
    # =========================================================================
    # EVALUACIÓN POR DIMENSIÓN
    # =========================================================================
    
    async def _evaluar_ubicacion(
        self,
        datos: Dict[str, Any],
        riesgos: List[RiesgoIdentificado],
    ) -> ComponenteScore:
        """
        Evalúa dimensión de ubicación.
        
        Factores:
        - Zona/comuna
        - Accesibilidad (metro, buses, autopistas)
        - Servicios cercanos
        - Plusvalía histórica
        - Seguridad
        """
        score = 500  # Base
        factores_pos = []
        factores_neg = []
        
        # 1. Factor zona
        comuna = datos.get("comuna", "").lower().replace(" ", "_")
        factor_zona = FACTORES_ZONA_SANTIAGO.get(comuna, FACTORES_ZONA_SANTIAGO["default"])
        
        if factor_zona >= 1.10:
            score += 150
            factores_pos.append(f"Ubicación premium ({comuna})")
        elif factor_zona >= 1.05:
            score += 100
            factores_pos.append(f"Buena ubicación ({comuna})")
        elif factor_zona >= 1.00:
            score += 50
            factores_pos.append(f"Ubicación consolidada ({comuna})")
        elif factor_zona >= 0.90:
            factores_neg.append(f"Ubicación en desarrollo ({comuna})")
        else:
            score -= 50
            factores_neg.append(f"Ubicación periférica ({comuna})")
        
        # 2. Accesibilidad transporte
        dist_metro = datos.get("distancia_metro_m", 9999)
        if dist_metro <= 500:
            score += 80
            factores_pos.append("Cercano a metro (<500m)")
        elif dist_metro <= 1000:
            score += 40
            factores_pos.append("Acceso a metro (<1km)")
        elif dist_metro > 2000:
            score -= 30
            factores_neg.append("Lejos de transporte público")
        
        # 3. Servicios cercanos
        servicios = datos.get("servicios_cercanos", [])
        servicios_premium = ["hospital", "colegio_premium", "universidad", "mall"]
        servicios_encontrados = [s for s in servicios if s in servicios_premium]
        score += len(servicios_encontrados) * 20
        if servicios_encontrados:
            factores_pos.append(f"Servicios cercanos: {', '.join(servicios_encontrados)}")
        
        # 4. Plusvalía histórica
        plusvalia_anual = datos.get("plusvalia_anual_pct", 0)
        if plusvalia_anual >= 8:
            score += 100
            factores_pos.append(f"Alta plusvalía ({plusvalia_anual}% anual)")
        elif plusvalia_anual >= 5:
            score += 50
            factores_pos.append(f"Buena plusvalía ({plusvalia_anual}% anual)")
        elif plusvalia_anual < 2:
            score -= 30
            factores_neg.append(f"Baja plusvalía ({plusvalia_anual}% anual)")
        
        # 5. Seguridad
        indice_seguridad = datos.get("indice_seguridad", 50)  # 0-100
        if indice_seguridad >= 80:
            score += 60
            factores_pos.append("Zona muy segura")
        elif indice_seguridad >= 60:
            score += 30
        elif indice_seguridad < 40:
            score -= 50
            factores_neg.append("Zona con problemas de seguridad")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.MERCADO,
                descripcion="Índice de seguridad bajo en la zona",
                severidad="medio",
                impacto_score=-50,
                mitigacion_sugerida="Verificar tendencias de seguridad",
            ))
        
        # 6. Zona sísmica
        zona_sismica = datos.get("zona_sismica", "2")
        if zona_sismica == "3":
            score -= 40
            factores_neg.append("Zona sísmica alta")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.SISMICO,
                descripcion="Propiedad en zona sísmica de alto riesgo",
                severidad="medio",
                impacto_score=-40,
                mitigacion_sugerida="Verificar cumplimiento NCh 433",
            ))
        
        # Normalizar score
        score = max(0, min(1000, score))
        
        return ComponenteScore(
            dimension=DimensionScore.UBICACION,
            score=score,
            ponderacion=PONDERACIONES_DIMENSION[DimensionScore.UBICACION],
            score_ponderado=score * PONDERACIONES_DIMENSION[DimensionScore.UBICACION],
            factores_positivos=factores_pos,
            factores_negativos=factores_neg,
            confianza=min(100, 50 + len(factores_pos) * 10 + len(factores_neg) * 5),
        )
    
    async def _evaluar_legal(
        self,
        datos_propiedad: Dict[str, Any],
        datos_legales: Dict[str, Any],
        riesgos: List[RiesgoIdentificado],
    ) -> ComponenteScore:
        """
        Evalúa dimensión legal.
        
        Factores:
        - Estado de títulos
        - Gravámenes e hipotecas
        - Litigios pendientes
        - Permisos y recepciones
        - Cumplimiento urbanístico
        """
        score = 700  # Base alta (presunción de legalidad)
        factores_pos = []
        factores_neg = []
        
        # 1. Estado de títulos
        titulo_status = datos_legales.get("titulo_status", "desconocido")
        if titulo_status == "limpio":
            score += 150
            factores_pos.append("Título de dominio limpio")
        elif titulo_status == "regular":
            score += 50
            factores_pos.append("Título regularizado")
        elif titulo_status == "irregular":
            score -= 200
            factores_neg.append("Título irregular")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.TITULO,
                descripcion="Propiedad con título de dominio irregular",
                severidad="critico",
                impacto_score=-150,
                mitigacion_sugerida="Regularización mediante D.L. 2695 o juicio de saneamiento",
                fuente="Conservador de Bienes Raíces",
            ))
        
        # 2. Gravámenes
        gravamenes = datos_legales.get("gravamenes", [])
        hipotecas = [g for g in gravamenes if g.get("tipo") == "hipoteca"]
        prohibiciones = [g for g in gravamenes if g.get("tipo") == "prohibicion"]
        
        if not gravamenes:
            score += 100
            factores_pos.append("Sin gravámenes registrados")
        else:
            # Evaluar hipotecas
            if hipotecas:
                monto_total_hip = sum(h.get("monto_uf", 0) for h in hipotecas)
                valor_propiedad = datos_propiedad.get("valor_uf", 0)
                if valor_propiedad > 0:
                    ltv = monto_total_hip / valor_propiedad
                    if ltv > 0.8:
                        score -= 100
                        factores_neg.append(f"Alto endeudamiento hipotecario (LTV: {ltv:.0%})")
                        riesgos.append(RiesgoIdentificado(
                            tipo=TipoRiesgo.GRAVAMEN,
                            descripcion=f"LTV elevado: {ltv:.0%}",
                            severidad="alto",
                            impacto_score=-100,
                            mitigacion_sugerida="Negociar alzamiento parcial",
                        ))
                    elif ltv > 0.5:
                        score -= 30
                        factores_neg.append(f"Hipoteca vigente (LTV: {ltv:.0%})")
            
            # Prohibiciones
            if prohibiciones:
                score -= 150
                factores_neg.append(f"{len(prohibiciones)} prohibición(es) registrada(s)")
                riesgos.append(RiesgoIdentificado(
                    tipo=TipoRiesgo.GRAVAMEN,
                    descripcion="Prohibición de enajenar vigente",
                    severidad="critico",
                    impacto_score=-150,
                    mitigacion_sugerida="Gestionar alzamiento de prohibición",
                ))
        
        # 3. Litigios
        litigios = datos_legales.get("litigios", [])
        litigios_activos = [l for l in litigios if l.get("estado") == "activo"]
        
        if litigios_activos:
            score -= 200
            factores_neg.append(f"{len(litigios_activos)} litigio(s) activo(s)")
            for litigio in litigios_activos:
                riesgos.append(RiesgoIdentificado(
                    tipo=TipoRiesgo.LITIGIO,
                    descripcion=f"Litigio: {litigio.get('tipo', 'desconocido')}",
                    severidad="critico",
                    impacto_score=-200,
                    mitigacion_sugerida="Consultar estado judicial y evaluar riesgos",
                    fuente=litigio.get("tribunal"),
                ))
        elif not litigios:
            score += 50
            factores_pos.append("Sin litigios registrados")
        
        # 4. Permisos
        permisos = datos_legales.get("permisos", {})
        tiene_recepcion = permisos.get("recepcion_final", False)
        tiene_permiso_edificacion = permisos.get("permiso_edificacion", False)
        
        if tiene_recepcion:
            score += 100
            factores_pos.append("Recepción final vigente")
        elif tiene_permiso_edificacion:
            score += 30
            factores_pos.append("Permiso de edificación (sin recepción)")
        else:
            score -= 100
            factores_neg.append("Sin recepción municipal")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.URBANISTICO,
                descripcion="Propiedad sin recepción final municipal",
                severidad="alto",
                impacto_score=-80,
                mitigacion_sugerida="Gestionar regularización ante DOM",
            ))
        
        # 5. Cumplimiento urbanístico
        cumple_uso_suelo = datos_legales.get("cumple_uso_suelo", True)
        cumple_constructibilidad = datos_legales.get("cumple_constructibilidad", True)
        
        if not cumple_uso_suelo:
            score -= 80
            factores_neg.append("Uso de suelo no compatible")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.URBANISTICO,
                descripcion="Uso actual no permitido por normativa",
                severidad="alto",
                impacto_score=-80,
            ))
        
        if not cumple_constructibilidad:
            score -= 60
            factores_neg.append("Excede coeficiente de constructibilidad")
        
        # 6. Años inscripción
        años_inscripcion = datos_legales.get("años_inscripcion", 0)
        if años_inscripcion >= 10:
            score += 30
            factores_pos.append(f"Inscripción consolidada ({años_inscripcion} años)")
        elif años_inscripcion < 2:
            score -= 20
            factores_neg.append("Inscripción reciente (<2 años)")
        
        score = max(0, min(1000, score))
        
        return ComponenteScore(
            dimension=DimensionScore.LEGAL,
            score=score,
            ponderacion=PONDERACIONES_DIMENSION[DimensionScore.LEGAL],
            score_ponderado=score * PONDERACIONES_DIMENSION[DimensionScore.LEGAL],
            factores_positivos=factores_pos,
            factores_negativos=factores_neg,
            riesgos_identificados=[r.__dict__ for r in riesgos if r.tipo in [TipoRiesgo.TITULO, TipoRiesgo.GRAVAMEN, TipoRiesgo.LITIGIO, TipoRiesgo.URBANISTICO]],
            confianza=min(100, 40 + (20 if datos_legales else 0) + len(factores_pos) * 5),
        )
    
    async def _evaluar_financiero(
        self,
        datos_propiedad: Dict[str, Any],
        datos_financieros: Dict[str, Any],
        riesgos: List[RiesgoIdentificado],
    ) -> ComponenteScore:
        """
        Evalúa dimensión financiera.
        
        Factores:
        - Valor vs mercado
        - Rentabilidad (yield)
        - Liquidez
        - Historial de pagos
        - Potencial de apreciación
        """
        score = 500  # Base
        factores_pos = []
        factores_neg = []
        
        valor_uf = datos_propiedad.get("valor_uf", 0)
        
        # 1. Relación valor/mercado
        valor_mercado_uf = datos_financieros.get("valor_mercado_estimado_uf", valor_uf)
        if valor_mercado_uf > 0 and valor_uf > 0:
            ratio = valor_uf / valor_mercado_uf
            if ratio <= 0.9:
                score += 100
                factores_pos.append(f"Precio bajo mercado ({(1-ratio)*100:.0f}% descuento)")
            elif ratio <= 1.0:
                score += 50
                factores_pos.append("Precio alineado con mercado")
            elif ratio <= 1.1:
                score += 20
            else:
                score -= 50
                factores_neg.append(f"Precio sobre mercado ({(ratio-1)*100:.0f}%)")
        
        # 2. Rentabilidad (cap rate / yield)
        renta_mensual_uf = datos_financieros.get("renta_mensual_uf", 0)
        if renta_mensual_uf > 0 and valor_uf > 0:
            cap_rate = (renta_mensual_uf * 12) / valor_uf * 100
            
            if cap_rate >= 7:
                score += 120
                factores_pos.append(f"Excelente rentabilidad ({cap_rate:.1f}% cap rate)")
            elif cap_rate >= 5:
                score += 80
                factores_pos.append(f"Buena rentabilidad ({cap_rate:.1f}% cap rate)")
            elif cap_rate >= 4:
                score += 40
                factores_pos.append(f"Rentabilidad aceptable ({cap_rate:.1f}% cap rate)")
            else:
                score -= 20
                factores_neg.append(f"Baja rentabilidad ({cap_rate:.1f}% cap rate)")
        
        # 3. Liquidez (días en mercado típicos)
        dias_mercado = datos_financieros.get("dias_mercado_promedio", 90)
        if dias_mercado <= 30:
            score += 80
            factores_pos.append("Alta liquidez (<30 días en mercado)")
        elif dias_mercado <= 60:
            score += 40
            factores_pos.append("Buena liquidez")
        elif dias_mercado <= 90:
            score += 10
        else:
            score -= 40
            factores_neg.append(f"Baja liquidez ({dias_mercado} días promedio)")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.LIQUIDEZ,
                descripcion=f"Tiempo de venta estimado: {dias_mercado} días",
                severidad="medio",
                impacto_score=-70,
            ))
        
        # 4. Historial de pagos (si es arriendo)
        if datos_financieros.get("es_arriendo", False):
            morosidad = datos_financieros.get("morosidad_pct", 0)
            if morosidad == 0:
                score += 60
                factores_pos.append("Sin morosidad histórica")
            elif morosidad <= 5:
                score += 30
                factores_pos.append("Morosidad controlada (<5%)")
            elif morosidad <= 15:
                score -= 20
                factores_neg.append(f"Morosidad moderada ({morosidad}%)")
            else:
                score -= 80
                factores_neg.append(f"Alta morosidad ({morosidad}%)")
        
        # 5. Costo mantención
        costo_mant_mensual_uf = datos_financieros.get("costo_mantencion_mensual_uf", 0)
        if costo_mant_mensual_uf > 0 and renta_mensual_uf > 0:
            ratio_costo = costo_mant_mensual_uf / renta_mensual_uf
            if ratio_costo > 0.3:
                score -= 40
                factores_neg.append(f"Altos costos de mantención ({ratio_costo*100:.0f}% de renta)")
            elif ratio_costo < 0.15:
                score += 30
                factores_pos.append("Bajos costos de mantención")
        
        # 6. Contribuciones (impuesto territorial)
        contribuciones_anuales_uf = datos_financieros.get("contribuciones_anuales_uf", 0)
        if contribuciones_anuales_uf > 0 and valor_uf > 0:
            tasa_efectiva = contribuciones_anuales_uf / valor_uf * 100
            if tasa_efectiva > 1.5:
                score -= 30
                factores_neg.append(f"Alta carga tributaria ({tasa_efectiva:.2f}%)")
            elif tasa_efectiva < 0.8:
                score += 20
                factores_pos.append("Carga tributaria favorable")
        
        # 7. Deuda asociada
        deuda_total_uf = datos_financieros.get("deuda_total_uf", 0)
        if deuda_total_uf > 0 and valor_uf > 0:
            debt_ratio = deuda_total_uf / valor_uf
            if debt_ratio > 0.8:
                score -= 100
                factores_neg.append(f"Alto nivel de deuda ({debt_ratio*100:.0f}%)")
                riesgos.append(RiesgoIdentificado(
                    tipo=TipoRiesgo.GRAVAMEN,
                    descripcion=f"Ratio deuda/valor: {debt_ratio*100:.0f}%",
                    severidad="alto",
                    impacto_score=-100,
                ))
            elif debt_ratio > 0.5:
                score -= 30
                factores_neg.append(f"Deuda moderada ({debt_ratio*100:.0f}%)")
        else:
            score += 40
            factores_pos.append("Sin deuda asociada")
        
        score = max(0, min(1000, score))
        
        return ComponenteScore(
            dimension=DimensionScore.FINANCIERO,
            score=score,
            ponderacion=PONDERACIONES_DIMENSION[DimensionScore.FINANCIERO],
            score_ponderado=score * PONDERACIONES_DIMENSION[DimensionScore.FINANCIERO],
            factores_positivos=factores_pos,
            factores_negativos=factores_neg,
            confianza=min(100, 30 + (30 if datos_financieros else 0) + len(factores_pos) * 8),
        )
    
    async def _evaluar_tecnico(
        self,
        datos_propiedad: Dict[str, Any],
        datos_tecnicos: Dict[str, Any],
        riesgos: List[RiesgoIdentificado],
    ) -> ComponenteScore:
        """
        Evalúa dimensión técnica.
        
        Factores:
        - Estado de conservación
        - Antigüedad vs vida útil
        - Calidad construcción
        - Eficiencia energética
        - Mantención histórica
        """
        score = 600  # Base
        factores_pos = []
        factores_neg = []
        
        # 1. Estado de conservación
        estado = datos_tecnicos.get("estado_conservacion", "regular")
        estados_score = {
            "excelente": 150,
            "muy_bueno": 100,
            "bueno": 50,
            "regular": 0,
            "malo": -100,
            "muy_malo": -200,
        }
        score += estados_score.get(estado, 0)
        
        if estado in ["excelente", "muy_bueno"]:
            factores_pos.append(f"Estado de conservación: {estado}")
        elif estado in ["malo", "muy_malo"]:
            factores_neg.append(f"Estado de conservación: {estado}")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.ESTRUCTURAL,
                descripcion=f"Propiedad en estado {estado}",
                severidad="alto" if estado == "muy_malo" else "medio",
                impacto_score=-100,
                mitigacion_sugerida="Evaluación estructural profesional",
            ))
        
        # 2. Antigüedad
        año_construccion = datos_propiedad.get("año_construccion", 2000)
        antiguedad = datetime.now().year - año_construccion
        
        tipo_construccion = datos_tecnicos.get("tipo_construccion", "hormigon")
        vida_util = {"hormigon": 80, "albanileria": 60, "madera": 40, "metalica": 50}.get(
            tipo_construccion, 60
        )
        
        vida_restante_pct = max(0, (vida_util - antiguedad) / vida_util * 100)
        
        if vida_restante_pct >= 80:
            score += 80
            factores_pos.append(f"Construcción reciente ({antiguedad} años)")
        elif vida_restante_pct >= 50:
            score += 30
            factores_pos.append(f"Vida útil restante: {vida_restante_pct:.0f}%")
        elif vida_restante_pct >= 25:
            score -= 30
            factores_neg.append(f"Construcción antigua ({antiguedad} años)")
        else:
            score -= 100
            factores_neg.append(f"Vida útil agotándose ({vida_restante_pct:.0f}% restante)")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.ESTRUCTURAL,
                descripcion=f"Propiedad con {vida_restante_pct:.0f}% de vida útil restante",
                severidad="alto",
                impacto_score=-100,
            ))
        
        # 3. Calidad construcción
        calidad = datos_tecnicos.get("calidad_construccion", "media")
        calidades_score = {
            "premium": 100,
            "alta": 60,
            "media_alta": 30,
            "media": 0,
            "economica": -40,
        }
        score += calidades_score.get(calidad, 0)
        if calidad in ["premium", "alta"]:
            factores_pos.append(f"Calidad de construcción: {calidad}")
        elif calidad == "economica":
            factores_neg.append("Construcción económica")
        
        # 4. Eficiencia energética
        cert_energetica = datos_tecnicos.get("certificacion_energetica", "")
        if cert_energetica:
            if cert_energetica in ["A", "A+"]:
                score += 60
                factores_pos.append(f"Certificación energética {cert_energetica}")
            elif cert_energetica in ["B", "C"]:
                score += 30
                factores_pos.append(f"Certificación energética {cert_energetica}")
            elif cert_energetica in ["E", "F", "G"]:
                score -= 20
                factores_neg.append(f"Baja eficiencia energética ({cert_energetica})")
        
        # 5. Instalaciones
        instalaciones = datos_tecnicos.get("instalaciones", {})
        
        # Eléctricas
        electrica_estado = instalaciones.get("electrica", "regular")
        if electrica_estado == "renovada":
            score += 30
            factores_pos.append("Instalación eléctrica renovada")
        elif electrica_estado == "deficiente":
            score -= 50
            factores_neg.append("Instalación eléctrica deficiente")
        
        # Sanitarias
        sanitaria_estado = instalaciones.get("sanitaria", "regular")
        if sanitaria_estado == "renovada":
            score += 30
            factores_pos.append("Instalaciones sanitarias renovadas")
        elif sanitaria_estado == "deficiente":
            score -= 50
            factores_neg.append("Instalaciones sanitarias deficientes")
        
        # Gas
        gas_estado = instalaciones.get("gas", "regular")
        if gas_estado == "deficiente":
            score -= 40
            factores_neg.append("Instalación de gas deficiente")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.ESTRUCTURAL,
                descripcion="Instalación de gas requiere revisión",
                severidad="medio",
                impacto_score=-40,
                mitigacion_sugerida="Certificación SEC",
            ))
        
        # 6. Mantención histórica
        tiene_historial = datos_tecnicos.get("historial_mantencion", False)
        if tiene_historial:
            score += 40
            factores_pos.append("Historial de mantención documentado")
        
        # 7. Problemas estructurales conocidos
        problemas = datos_tecnicos.get("problemas_estructurales", [])
        if problemas:
            for problema in problemas:
                score -= 80
                factores_neg.append(f"Problema estructural: {problema}")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.ESTRUCTURAL,
                descripcion=f"Problemas estructurales: {', '.join(problemas)}",
                severidad="critico",
                impacto_score=-100,
            ))
        
        score = max(0, min(1000, score))
        
        return ComponenteScore(
            dimension=DimensionScore.TECNICO,
            score=score,
            ponderacion=PONDERACIONES_DIMENSION[DimensionScore.TECNICO],
            score_ponderado=score * PONDERACIONES_DIMENSION[DimensionScore.TECNICO],
            factores_positivos=factores_pos,
            factores_negativos=factores_neg,
            confianza=min(100, 35 + (25 if datos_tecnicos else 0) + len(factores_pos) * 6),
        )
    
    async def _evaluar_mercado(
        self,
        datos_propiedad: Dict[str, Any],
        datos_mercado: Dict[str, Any],
        riesgos: List[RiesgoIdentificado],
    ) -> ComponenteScore:
        """
        Evalúa dimensión de mercado.
        
        Factores:
        - Oferta/demanda en zona
        - Tendencias de precios
        - Absorción del mercado
        - Competencia directa
        - Contexto macroeconómico
        """
        score = 500  # Base
        factores_pos = []
        factores_neg = []
        
        # 1. Balance oferta/demanda
        indice_demanda = datos_mercado.get("indice_demanda", 50)  # 0-100
        if indice_demanda >= 80:
            score += 120
            factores_pos.append("Alta demanda en la zona")
        elif indice_demanda >= 60:
            score += 60
            factores_pos.append("Demanda saludable")
        elif indice_demanda >= 40:
            score += 20
        else:
            score -= 60
            factores_neg.append("Baja demanda en la zona")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.MERCADO,
                descripcion=f"Índice de demanda bajo: {indice_demanda}",
                severidad="medio",
                impacto_score=-60,
            ))
        
        # 2. Tendencia de precios
        tendencia_precios = datos_mercado.get("tendencia_precios_12m_pct", 0)
        if tendencia_precios >= 10:
            score += 100
            factores_pos.append(f"Fuerte apreciación (+{tendencia_precios:.1f}% 12m)")
        elif tendencia_precios >= 5:
            score += 50
            factores_pos.append(f"Tendencia alcista (+{tendencia_precios:.1f}% 12m)")
        elif tendencia_precios >= 0:
            score += 20
            factores_pos.append("Precios estables")
        elif tendencia_precios >= -5:
            score -= 30
            factores_neg.append(f"Leve corrección ({tendencia_precios:.1f}% 12m)")
        else:
            score -= 80
            factores_neg.append(f"Precios en caída ({tendencia_precios:.1f}% 12m)")
            riesgos.append(RiesgoIdentificado(
                tipo=TipoRiesgo.MERCADO,
                descripcion=f"Caída de precios: {tendencia_precios:.1f}% en 12 meses",
                severidad="alto",
                impacto_score=-60,
            ))
        
        # 3. Tasa de absorción
        meses_inventario = datos_mercado.get("meses_inventario", 12)
        if meses_inventario <= 3:
            score += 80
            factores_pos.append("Mercado muy activo (<3 meses inventario)")
        elif meses_inventario <= 6:
            score += 40
            factores_pos.append("Mercado equilibrado")
        elif meses_inventario <= 12:
            score -= 20
            factores_neg.append("Mercado lento")
        else:
            score -= 60
            factores_neg.append(f"Sobreoferta ({meses_inventario} meses inventario)")
        
        # 4. Competencia directa
        propiedades_similares = datos_mercado.get("propiedades_similares_venta", 0)
        if propiedades_similares <= 5:
            score += 40
            factores_pos.append("Poca competencia directa")
        elif propiedades_similares <= 15:
            score += 10
        else:
            score -= 30
            factores_neg.append(f"Alta competencia ({propiedades_similares} similares)")
        
        # 5. Contexto macroeconómico
        tasa_interes = datos_mercado.get("tasa_hipotecaria_pct", 5.0)
        if tasa_interes <= 4.0:
            score += 50
            factores_pos.append("Tasas hipotecarias favorables")
        elif tasa_interes <= 5.5:
            score += 20
        elif tasa_interes >= 7.0:
            score -= 40
            factores_neg.append("Tasas hipotecarias elevadas")
        
        # 6. Proyectos en desarrollo
        proyectos_zona = datos_mercado.get("proyectos_nuevos_zona", 0)
        if proyectos_zona > 10:
            score -= 30
            factores_neg.append(f"Muchos proyectos nuevos ({proyectos_zona})")
        elif proyectos_zona > 0 and proyectos_zona <= 3:
            score += 20
            factores_pos.append("Desarrollo moderado en la zona")
        
        # 7. Tipo de propiedad en demanda
        tipo = datos_propiedad.get("tipo_propiedad", "departamento")
        tipo_demanda = datos_mercado.get("tipos_alta_demanda", ["departamento", "casa"])
        if tipo in tipo_demanda:
            score += 40
            factores_pos.append(f"Tipo '{tipo}' con alta demanda")
        
        score = max(0, min(1000, score))
        
        return ComponenteScore(
            dimension=DimensionScore.MERCADO,
            score=score,
            ponderacion=PONDERACIONES_DIMENSION[DimensionScore.MERCADO],
            score_ponderado=score * PONDERACIONES_DIMENSION[DimensionScore.MERCADO],
            factores_positivos=factores_pos,
            factores_negativos=factores_neg,
            confianza=min(100, 40 + (20 if datos_mercado else 0) + len(factores_pos) * 7),
        )
    
    # =========================================================================
    # CÁLCULOS Y UTILIDADES
    # =========================================================================
    
    def _calcular_score_total(
        self,
        componentes: Dict[DimensionScore, ComponenteScore],
    ) -> int:
        """Calcula score total ponderado."""
        total = sum(c.score_ponderado for c in componentes.values())
        return int(round(total))
    
    def _aplicar_penalizaciones(
        self,
        score: int,
        riesgos: List[RiesgoIdentificado],
    ) -> int:
        """Aplica penalizaciones por riesgos identificados."""
        # Limitar penalización total al 40% del score
        penalizacion_total = sum(
            PENALIZACIONES_RIESGO.get(r.tipo, 0) for r in riesgos
        )
        penalizacion_max = int(score * 0.4)
        penalizacion_aplicada = max(penalizacion_total, -penalizacion_max)
        
        return max(0, min(1000, score + penalizacion_aplicada))
    
    def _determinar_categoria(self, score: int) -> CategoriaScore:
        """Determina categoría según score."""
        for categoria, (min_score, max_score) in RANGOS_CATEGORIA.items():
            if min_score <= score <= max_score:
                return categoria
        return CategoriaScore.D
    
    def _calcular_confianza(
        self,
        componentes: Dict[DimensionScore, ComponenteScore],
    ) -> float:
        """Calcula confianza promedio ponderada."""
        total_conf = sum(
            c.confianza * c.ponderacion for c in componentes.values()
        )
        return round(total_conf, 1)
    
    def _calcular_completitud(
        self,
        datos_propiedad: Dict,
        datos_legales: Optional[Dict],
        datos_financieros: Optional[Dict],
        datos_tecnicos: Optional[Dict],
        datos_mercado: Optional[Dict],
    ) -> float:
        """Calcula porcentaje de completitud de datos."""
        campos_requeridos = {
            "propiedad": ["comuna", "tipo_propiedad", "superficie_m2", "valor_uf"],
            "legales": ["titulo_status", "gravamenes", "permisos"],
            "financieros": ["valor_mercado_estimado_uf", "renta_mensual_uf"],
            "tecnicos": ["estado_conservacion", "año_construccion"],
            "mercado": ["indice_demanda", "tendencia_precios_12m_pct"],
        }
        
        total_campos = 0
        campos_presentes = 0
        
        for campo in campos_requeridos["propiedad"]:
            total_campos += 1
            if campo in datos_propiedad and datos_propiedad[campo]:
                campos_presentes += 1
        
        if datos_legales:
            for campo in campos_requeridos["legales"]:
                total_campos += 1
                if campo in datos_legales:
                    campos_presentes += 1
        
        if datos_financieros:
            for campo in campos_requeridos["financieros"]:
                total_campos += 1
                if campo in datos_financieros:
                    campos_presentes += 1
        
        if datos_tecnicos:
            for campo in campos_requeridos["tecnicos"]:
                total_campos += 1
                if campo in datos_tecnicos:
                    campos_presentes += 1
        
        if datos_mercado:
            for campo in campos_requeridos["mercado"]:
                total_campos += 1
                if campo in datos_mercado:
                    campos_presentes += 1
        
        return round((campos_presentes / total_campos) * 100, 1) if total_campos > 0 else 0.0
    
    def _determinar_nivel_riesgo(
        self,
        riesgos: List[RiesgoIdentificado],
        score: int,
    ) -> str:
        """Determina nivel de riesgo global."""
        if not riesgos and score >= 700:
            return "bajo"
        
        criticos = sum(1 for r in riesgos if r.severidad == "critico")
        altos = sum(1 for r in riesgos if r.severidad == "alto")
        
        if criticos >= 2 or score < 300:
            return "critico"
        elif criticos == 1 or altos >= 2 or score < 500:
            return "alto"
        elif altos == 1 or score < 600:
            return "medio"
        else:
            return "bajo"
    
    def _identificar_factores_principales(
        self,
        componentes: Dict[DimensionScore, ComponenteScore],
        explicaciones_shap: List[ExplicacionSHAP],
    ) -> List[str]:
        """Identifica los factores más importantes del score."""
        factores = []
        
        # Top 3 positivos
        positivos = []
        for comp in componentes.values():
            positivos.extend(comp.factores_positivos)
        factores.extend(positivos[:3])
        
        # Top 3 negativos
        negativos = []
        for comp in componentes.values():
            negativos.extend(comp.factores_negativos)
        factores.extend(negativos[:3])
        
        # Agregar top SHAP si disponible
        if explicaciones_shap:
            top_shap = sorted(
                explicaciones_shap,
                key=lambda x: abs(x.impacto_shap),
                reverse=True
            )[:2]
            factores.extend([s.descripcion for s in top_shap])
        
        return factores[:8]  # Máximo 8 factores
    
    def _generar_recomendaciones(
        self,
        categoria: CategoriaScore,
        riesgos: List[RiesgoIdentificado],
        componentes: Dict[DimensionScore, ComponenteScore],
    ) -> List[str]:
        """Genera recomendaciones basadas en la evaluación."""
        recomendaciones = []
        
        # Recomendaciones por categoría
        if categoria in [CategoriaScore.D, CategoriaScore.C, CategoriaScore.CC]:
            recomendaciones.append(
                "⚠️ Score crítico: Se recomienda revisión exhaustiva antes de cualquier inversión"
            )
        elif categoria in [CategoriaScore.CCC, CategoriaScore.B]:
            recomendaciones.append(
                "⚡ Score bajo: Evaluar factores de riesgo y negociar precio acorde"
            )
        
        # Recomendaciones por riesgos críticos
        for riesgo in riesgos:
            if riesgo.severidad == "critico" and riesgo.mitigacion_sugerida:
                recomendaciones.append(f"🔴 {riesgo.mitigacion_sugerida}")
            elif riesgo.severidad == "alto" and riesgo.mitigacion_sugerida:
                recomendaciones.append(f"🟠 {riesgo.mitigacion_sugerida}")
        
        # Recomendaciones por dimensión débil
        for dimension, componente in componentes.items():
            if componente.score < 400:
                if dimension == DimensionScore.LEGAL:
                    recomendaciones.append(
                        "📋 Realizar due diligence legal completo (títulos, gravámenes, litigios)"
                    )
                elif dimension == DimensionScore.TECNICO:
                    recomendaciones.append(
                        "🔧 Solicitar inspección técnica profesional"
                    )
                elif dimension == DimensionScore.FINANCIERO:
                    recomendaciones.append(
                        "💰 Verificar valorización independiente y análisis de rentabilidad"
                    )
                elif dimension == DimensionScore.MERCADO:
                    recomendaciones.append(
                        "📊 Analizar tendencias de mercado y liquidez de la zona"
                    )
        
        # Recomendaciones positivas para scores altos
        if categoria in [CategoriaScore.AAA, CategoriaScore.AA]:
            recomendaciones.append(
                "✅ Propiedad con excelente perfil crediticio - apta para financiamiento preferencial"
            )
        
        return recomendaciones[:6]  # Máximo 6 recomendaciones
    
    # =========================================================================
    # EXPLICABILIDAD SHAP
    # =========================================================================
    
    async def _generar_explicaciones_shap(
        self,
        datos_propiedad: Dict[str, Any],
        datos_legales: Dict[str, Any],
        datos_financieros: Dict[str, Any],
        datos_tecnicos: Dict[str, Any],
        datos_mercado: Dict[str, Any],
    ) -> List[ExplicacionSHAP]:
        """Genera explicaciones SHAP para el score."""
        if not ML_AVAILABLE or not self.modelo_xgb:
            return []
        
        try:
            # Preparar features
            features = self._preparar_features(
                datos_propiedad, datos_legales, datos_financieros,
                datos_tecnicos, datos_mercado
            )
            
            if features is None:
                return []
            
            # Crear explainer si no existe
            if self.shap_explainer is None:
                self.shap_explainer = shap.TreeExplainer(self.modelo_xgb)
            
            # Calcular SHAP values
            shap_values = self.shap_explainer.shap_values(features)
            
            # Crear explicaciones
            explicaciones = []
            feature_names = self._get_feature_names()
            
            for i, (name, value, shap_val) in enumerate(
                zip(feature_names, features.values[0], shap_values[0])
            ):
                if abs(shap_val) > 0.01:  # Solo significativos
                    explicaciones.append(ExplicacionSHAP(
                        feature=name,
                        valor=float(value),
                        impacto_shap=float(shap_val),
                        direccion="positivo" if shap_val > 0 else "negativo",
                        descripcion=self._describir_feature(name, value, shap_val),
                    ))
            
            # Ordenar por impacto absoluto
            explicaciones.sort(key=lambda x: abs(x.impacto_shap), reverse=True)
            
            return explicaciones[:10]  # Top 10
            
        except Exception as e:
            logger.error(f"Error generando SHAP: {e}")
            return []
    
    def _preparar_features(
        self,
        datos_propiedad: Dict,
        datos_legales: Dict,
        datos_financieros: Dict,
        datos_tecnicos: Dict,
        datos_mercado: Dict,
    ) -> Optional[pd.DataFrame]:
        """Prepara DataFrame de features para ML."""
        try:
            features = {
                # Ubicación
                "factor_zona": FACTORES_ZONA_SANTIAGO.get(
                    datos_propiedad.get("comuna", "").lower().replace(" ", "_"),
                    0.9
                ),
                "distancia_metro_km": datos_propiedad.get("distancia_metro_m", 2000) / 1000,
                "plusvalia_anual": datos_propiedad.get("plusvalia_anual_pct", 3),
                "indice_seguridad": datos_propiedad.get("indice_seguridad", 50),
                
                # Legal
                "titulo_limpio": 1 if datos_legales.get("titulo_status") == "limpio" else 0,
                "tiene_gravamenes": 1 if datos_legales.get("gravamenes") else 0,
                "tiene_litigios": 1 if datos_legales.get("litigios") else 0,
                "tiene_recepcion": 1 if datos_legales.get("permisos", {}).get("recepcion_final") else 0,
                
                # Financiero
                "valor_uf": datos_propiedad.get("valor_uf", 5000),
                "ratio_precio_mercado": (
                    datos_propiedad.get("valor_uf", 5000) /
                    datos_financieros.get("valor_mercado_estimado_uf", 5000)
                ) if datos_financieros.get("valor_mercado_estimado_uf") else 1.0,
                "cap_rate": (
                    (datos_financieros.get("renta_mensual_uf", 0) * 12) /
                    datos_propiedad.get("valor_uf", 5000) * 100
                ) if datos_propiedad.get("valor_uf") else 0,
                "dias_mercado": datos_financieros.get("dias_mercado_promedio", 90),
                
                # Técnico
                "antiguedad_años": datetime.now().year - datos_propiedad.get("año_construccion", 2000),
                "estado_score": {
                    "excelente": 5, "muy_bueno": 4, "bueno": 3,
                    "regular": 2, "malo": 1, "muy_malo": 0
                }.get(datos_tecnicos.get("estado_conservacion", "regular"), 2),
                "calidad_score": {
                    "premium": 5, "alta": 4, "media_alta": 3,
                    "media": 2, "economica": 1
                }.get(datos_tecnicos.get("calidad_construccion", "media"), 2),
                
                # Mercado
                "indice_demanda": datos_mercado.get("indice_demanda", 50),
                "tendencia_precios": datos_mercado.get("tendencia_precios_12m_pct", 0),
                "meses_inventario": datos_mercado.get("meses_inventario", 12),
                "tasa_hipotecaria": datos_mercado.get("tasa_hipotecaria_pct", 5.5),
            }
            
            df = pd.DataFrame([features])
            
            # Escalar si hay scaler
            if self.scaler:
                df = pd.DataFrame(
                    self.scaler.transform(df),
                    columns=df.columns
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Error preparando features: {e}")
            return None
    
    def _get_feature_names(self) -> List[str]:
        """Retorna nombres de features."""
        return [
            "factor_zona", "distancia_metro_km", "plusvalia_anual", "indice_seguridad",
            "titulo_limpio", "tiene_gravamenes", "tiene_litigios", "tiene_recepcion",
            "valor_uf", "ratio_precio_mercado", "cap_rate", "dias_mercado",
            "antiguedad_años", "estado_score", "calidad_score",
            "indice_demanda", "tendencia_precios", "meses_inventario", "tasa_hipotecaria",
        ]
    
    def _describir_feature(self, name: str, value: float, shap_val: float) -> str:
        """Genera descripción legible de un feature."""
        direccion = "aumenta" if shap_val > 0 else "disminuye"
        
        descripciones = {
            "factor_zona": f"Factor de zona {value:.2f} {direccion} el score",
            "distancia_metro_km": f"Distancia a metro ({value:.1f}km) {direccion} el score",
            "plusvalia_anual": f"Plusvalía anual ({value:.1f}%) {direccion} el score",
            "indice_seguridad": f"Índice de seguridad ({value:.0f}) {direccion} el score",
            "titulo_limpio": f"{'Título limpio' if value else 'Título con problemas'} {direccion} el score",
            "tiene_gravamenes": f"{'Con' if value else 'Sin'} gravámenes {direccion} el score",
            "tiene_litigios": f"{'Con' if value else 'Sin'} litigios {direccion} el score",
            "cap_rate": f"Cap rate ({value:.1f}%) {direccion} el score",
            "antiguedad_años": f"Antigüedad ({value:.0f} años) {direccion} el score",
            "indice_demanda": f"Demanda ({value:.0f}/100) {direccion} el score",
            "tendencia_precios": f"Tendencia precios ({value:+.1f}%) {direccion} el score",
        }
        
        return descripciones.get(name, f"{name} = {value:.2f} {direccion} el score")
    
    # =========================================================================
    # ENTRENAMIENTO DE MODELO
    # =========================================================================
    
    async def entrenar_modelo(
        self,
        datos_historicos: pd.DataFrame,
        target_col: str = "score_real",
    ) -> Dict[str, Any]:
        """
        Entrena modelo XGBoost con datos históricos.
        
        Args:
            datos_historicos: DataFrame con features y score real
            target_col: Nombre de columna objetivo
            
        Returns:
            Métricas de entrenamiento
        """
        if not ML_AVAILABLE:
            raise RuntimeError("ML libraries not available")
        
        # Preparar datos
        feature_cols = self._get_feature_names()
        X = datos_historicos[feature_cols]
        y = datos_historicos[target_col]
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Escalar
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entrenar XGBoost
        self.modelo_xgb = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='reg:squarederror',
            random_state=42,
        )
        self.modelo_xgb.fit(X_train_scaled, y_train)
        
        # Evaluar
        y_pred = self.modelo_xgb.predict(X_test_scaled)
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        
        # Guardar modelos
        modelo_path = settings.ML_MODEL_PATH / "credit_score_xgb.joblib"
        scaler_path = settings.ML_MODEL_PATH / "credit_score_scaler.joblib"
        
        modelo_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.modelo_xgb, modelo_path)
        joblib.dump(self.scaler, scaler_path)
        
        # Crear SHAP explainer
        self.shap_explainer = shap.TreeExplainer(self.modelo_xgb)
        
        logger.info(f"Modelo entrenado - MAPE: {mape:.2f}%, RMSE: {rmse:.2f}")
        
        return {
            "mape": mape,
            "rmse": rmse,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "feature_importance": dict(
                zip(feature_cols, self.modelo_xgb.feature_importances_)
            ),
        }


# =============================================================================
# FUNCIONES AUXILIARES PARA API
# =============================================================================

async def evaluar_propiedad(
    db: AsyncSession,
    propiedad_id: str,
    datos_propiedad: Dict[str, Any],
    **kwargs,
) -> ResultadoCreditScore:
    """
    Función wrapper para evaluar credit score de una propiedad.
    
    Uso:
        resultado = await evaluar_propiedad(
            db=session,
            propiedad_id="PROP-12345",
            datos_propiedad={
                "comuna": "Providencia",
                "tipo_propiedad": "departamento",
                "superficie_m2": 80,
                "valor_uf": 5500,
            },
            datos_legales={...},
            datos_financieros={...},
        )
    """
    service = CreditScoreService(db)
    return await service.evaluar(
        propiedad_id=propiedad_id,
        datos_propiedad=datos_propiedad,
        **kwargs,
    )


def score_to_dict(resultado: ResultadoCreditScore) -> Dict[str, Any]:
    """Convierte resultado a diccionario serializable."""
    return {
        "propiedad_id": resultado.propiedad_id,
        "rol_sii": resultado.rol_sii,
        "fecha_evaluacion": resultado.fecha_evaluacion.isoformat(),
        "score_total": resultado.score_total,
        "categoria": resultado.categoria.value,
        "componentes": {
            dim.value: {
                "score": comp.score,
                "ponderacion": comp.ponderacion,
                "score_ponderado": comp.score_ponderado,
                "factores_positivos": comp.factores_positivos,
                "factores_negativos": comp.factores_negativos,
                "confianza": comp.confianza,
            }
            for dim, comp in resultado.componentes.items()
        },
        "riesgos": [
            {
                "tipo": r.tipo.value,
                "descripcion": r.descripcion,
                "severidad": r.severidad,
                "impacto_score": r.impacto_score,
                "mitigacion_sugerida": r.mitigacion_sugerida,
            }
            for r in resultado.riesgos
        ],
        "nivel_riesgo_global": resultado.nivel_riesgo_global,
        "explicaciones_shap": [
            {
                "feature": e.feature,
                "valor": e.valor,
                "impacto_shap": e.impacto_shap,
                "direccion": e.direccion,
                "descripcion": e.descripcion,
            }
            for e in resultado.explicaciones_shap
        ],
        "factores_principales": resultado.factores_principales,
        "confianza_evaluacion": resultado.confianza_evaluacion,
        "completitud_datos": resultado.completitud_datos,
        "recomendaciones": resultado.recomendaciones,
        "version_modelo": resultado.version_modelo,
        "tiempo_procesamiento_ms": resultado.tiempo_procesamiento_ms,
    }
