"""
DATAPOLIS v3.0 - Servicio MS: Mercado de Suelo
===============================================
Motor de análisis de mercado inmobiliario con:
- Clustering espacial de precios
- Modelo hedónico de precios
- Análisis de oferta/demanda
- Detección de oportunidades
- Proyecciones de mercado

Fuentes de datos:
- Portal Inmobiliario, Yapo, Toctoc
- SII (transacciones reales)
- MINVU (permisos edificación)
- INE (estadísticas construcción)
- BCCh (créditos hipotecarios)

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import math
import statistics
from collections import defaultdict
import hashlib
import json


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================

class TipoPropiedad(str, Enum):
    """Tipos de propiedad inmobiliaria"""
    DEPARTAMENTO = "departamento"
    CASA = "casa"
    OFICINA = "oficina"
    LOCAL_COMERCIAL = "local_comercial"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"
    TERRENO = "terreno"
    PARCELA = "parcela"


class TipoOperacion(str, Enum):
    """Tipos de operación"""
    VENTA = "venta"
    ARRIENDO = "arriendo"


class EstadoPropiedad(str, Enum):
    """Estado de la propiedad"""
    NUEVO = "nuevo"
    USADO = "usado"
    EN_CONSTRUCCION = "en_construccion"
    EN_VERDE = "en_verde"
    REMODELADO = "remodelado"


class SegmentoMercado(str, Enum):
    """Segmentos de mercado"""
    ECONOMICO = "economico"
    MEDIO_BAJO = "medio_bajo"
    MEDIO = "medio"
    MEDIO_ALTO = "medio_alto"
    ALTO = "alto"
    PREMIUM = "premium"
    LUJO = "lujo"


class TendenciaMercado(str, Enum):
    """Tendencias del mercado"""
    ALZA_FUERTE = "alza_fuerte"       # > 10% anual
    ALZA_MODERADA = "alza_moderada"   # 5-10% anual
    ESTABLE = "estable"               # -2% a 5% anual
    BAJA_MODERADA = "baja_moderada"   # -5% a -2% anual
    BAJA_FUERTE = "baja_fuerte"       # < -5% anual


class TipoCluster(str, Enum):
    """Tipos de cluster espacial"""
    HOT_SPOT = "hot_spot"           # Precios altos agrupados
    COLD_SPOT = "cold_spot"         # Precios bajos agrupados
    HIGH_OUTLIER = "high_outlier"   # Precio alto aislado
    LOW_OUTLIER = "low_outlier"     # Precio bajo aislado
    NOT_SIGNIFICANT = "not_significant"


# Rangos de segmentos por precio UF/m2 (departamentos RM)
SEGMENTOS_PRECIO_UF_M2 = {
    SegmentoMercado.ECONOMICO: (0, 35),
    SegmentoMercado.MEDIO_BAJO: (35, 50),
    SegmentoMercado.MEDIO: (50, 70),
    SegmentoMercado.MEDIO_ALTO: (70, 100),
    SegmentoMercado.ALTO: (100, 150),
    SegmentoMercado.PREMIUM: (150, 250),
    SegmentoMercado.LUJO: (250, float('inf'))
}

# Factores para modelo hedónico
FACTORES_HEDONICOS = {
    "superficie": 0.35,
    "dormitorios": 0.10,
    "baños": 0.08,
    "estacionamientos": 0.07,
    "antiguedad": -0.05,
    "piso": 0.03,
    "orientacion": 0.02,
    "vista": 0.05,
    "amenities": 0.08,
    "cercania_metro": 0.12,
    "area_verde": 0.05
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PropiedadMercado:
    """Propiedad en el mercado"""
    id: str
    tipo: TipoPropiedad
    operacion: TipoOperacion
    estado: EstadoPropiedad
    
    # Ubicación
    direccion: str
    comuna: str
    region: str
    latitud: float
    longitud: float
    
    # Características
    superficie_util: float
    superficie_total: Optional[float]
    dormitorios: int
    baños: int
    estacionamientos: int
    bodegas: int
    piso: Optional[int]
    orientacion: Optional[str]
    año_construccion: Optional[int]
    
    # Precio
    precio_publicado: float  # UF
    precio_m2: float  # UF/m2
    gastos_comunes: Optional[float]  # CLP
    
    # Metadata
    fuente: str
    url: Optional[str]
    fecha_publicacion: date
    dias_publicado: int
    
    # Análisis
    segmento: Optional[SegmentoMercado] = None
    score_oportunidad: Optional[float] = None


@dataclass
class ClusterEspacial:
    """Cluster espacial de precios"""
    id: str
    tipo: TipoCluster
    centroide_lat: float
    centroide_lon: float
    radio_km: float
    propiedades_count: int
    precio_m2_promedio: float
    precio_m2_mediana: float
    desviacion_estandar: float
    z_score: float
    p_value: float
    comunas: List[str]
    descripcion: str


@dataclass
class AnalisisZona:
    """Análisis de una zona geográfica"""
    zona_id: str
    nombre: str
    tipo: str  # comuna, sector, barrio
    geometria_wkt: Optional[str]
    
    # Oferta
    total_propiedades: int
    propiedades_venta: int
    propiedades_arriendo: int
    por_tipo: Dict[str, int]
    por_estado: Dict[str, int]
    
    # Precios venta
    precio_m2_promedio_venta: float
    precio_m2_mediana_venta: float
    precio_m2_min_venta: float
    precio_m2_max_venta: float
    
    # Precios arriendo
    precio_m2_promedio_arriendo: float
    cap_rate_promedio: float
    
    # Tendencias
    variacion_precio_mes: float
    variacion_precio_trimestre: float
    variacion_precio_año: float
    tendencia: TendenciaMercado
    
    # Demanda
    dias_promedio_venta: int
    tasa_absorcion_mensual: float
    indice_liquidez: float
    
    # Competitividad
    inventario_meses: float
    nuevas_publicaciones_mes: int
    propiedades_retiradas_mes: int


@dataclass
class ModeloHedonicoResultado:
    """Resultado de modelo hedónico de precios"""
    valor_estimado: float  # UF
    valor_m2_estimado: float  # UF/m2
    intervalo_confianza: Tuple[float, float]
    
    # Contribución de factores
    contribuciones: Dict[str, float]
    factor_ubicacion: float
    factor_caracteristicas: float
    factor_condicion: float
    
    # Métricas del modelo
    r_squared: float
    rmse: float
    mape: float
    
    # Comparación mercado
    diferencia_mercado_pct: float
    posicion_percentil: int
    es_oportunidad: bool
    tipo_oportunidad: Optional[str]


@dataclass
class ProyeccionMercado:
    """Proyección de mercado"""
    fecha_proyeccion: date
    horizonte_meses: int
    
    # Proyecciones de precio
    precio_m2_proyectado: float
    variacion_esperada_pct: float
    escenario_optimista: float
    escenario_pesimista: float
    
    # Intervalos de confianza
    intervalo_80: Tuple[float, float]
    intervalo_95: Tuple[float, float]
    
    # Factores considerados
    tendencia_historica: float
    factor_macroeconomico: float
    factor_oferta_demanda: float
    factor_estacionalidad: float
    
    # Riesgos
    volatilidad_historica: float
    nivel_incertidumbre: str
    factores_riesgo: List[str]


@dataclass
class OportunidadInversion:
    """Oportunidad de inversión detectada"""
    id: str
    propiedad: PropiedadMercado
    tipo_oportunidad: str
    
    # Métricas de oportunidad
    descuento_mercado_pct: float
    potencial_plusvalia_pct: float
    cap_rate_estimado: float
    roi_proyectado_anual: float
    
    # Análisis
    razones: List[str]
    riesgos: List[str]
    recomendacion: str
    urgencia: str  # alta, media, baja
    
    # Score
    score_total: float
    score_precio: float
    score_ubicacion: float
    score_potencial: float
    
    # Comparables
    comparables_similares: int
    precio_comparables_promedio: float


@dataclass
class ReporteMercado:
    """Reporte completo de mercado"""
    id: str
    fecha_generacion: datetime
    periodo_analisis: str
    
    # Cobertura
    zonas_analizadas: List[str]
    total_propiedades_analizadas: int
    fuentes_datos: List[str]
    
    # Resumen ejecutivo
    resumen: str
    tendencia_general: TendenciaMercado
    indice_actividad: float
    
    # Análisis por zona
    zonas: List[AnalisisZona]
    
    # Clusters espaciales
    clusters: List[ClusterEspacial]
    
    # Proyecciones
    proyecciones: List[ProyeccionMercado]
    
    # Oportunidades
    oportunidades: List[OportunidadInversion]
    
    # Indicadores macro
    indicadores_macro: Dict[str, Any]
    
    # Recomendaciones
    recomendaciones: List[str]


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class ServicioMercadoSuelo:
    """
    Motor de Análisis de Mercado de Suelo.
    
    Funcionalidades:
    - Scraping y consolidación de ofertas
    - Clustering espacial de precios (LISA, Getis-Ord)
    - Modelo hedónico de precios
    - Análisis de tendencias
    - Detección de oportunidades
    - Proyecciones de mercado
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._fuentes_activas: List[str] = [
            "portal_inmobiliario",
            "yapo",
            "toctoc",
            "sii_transacciones"
        ]
        self._modelo_hedonico_entrenado = False
    
    # =========================================================================
    # OBTENCIÓN DE DATOS DE MERCADO
    # =========================================================================
    
    async def obtener_oferta_mercado(
        self,
        comuna: Optional[str] = None,
        region: str = "Metropolitana",
        tipo_propiedad: Optional[TipoPropiedad] = None,
        operacion: TipoOperacion = TipoOperacion.VENTA,
        precio_min_uf: Optional[float] = None,
        precio_max_uf: Optional[float] = None,
        superficie_min: Optional[float] = None,
        superficie_max: Optional[float] = None,
        dormitorios_min: Optional[int] = None,
        limite: int = 100
    ) -> List[PropiedadMercado]:
        """
        Obtiene oferta actual del mercado desde múltiples fuentes.
        
        Args:
            comuna: Filtrar por comuna
            region: Región (default: Metropolitana)
            tipo_propiedad: Tipo de propiedad
            operacion: Venta o arriendo
            precio_min_uf: Precio mínimo en UF
            precio_max_uf: Precio máximo en UF
            superficie_min: Superficie mínima m2
            superficie_max: Superficie máxima m2
            dormitorios_min: Dormitorios mínimos
            limite: Máximo de resultados
            
        Returns:
            Lista de propiedades en el mercado
        """
        # Simular obtención de múltiples fuentes
        propiedades = []
        
        # Mock de propiedades para desarrollo
        comunas_rm = [
            ("Las Condes", -33.4167, -70.5833, 95.0),
            ("Providencia", -33.4289, -70.6167, 105.0),
            ("Ñuñoa", -33.4567, -70.5967, 72.0),
            ("Santiago Centro", -33.4489, -70.6693, 65.0),
            ("Vitacura", -33.3889, -70.5722, 140.0),
            ("La Reina", -33.4467, -70.5433, 78.0),
            ("Macul", -33.4889, -70.5989, 55.0),
            ("San Miguel", -33.4967, -70.6533, 52.0),
            ("La Florida", -33.5167, -70.5833, 48.0),
            ("Peñalolén", -33.4833, -70.5167, 45.0)
        ]
        
        import random
        
        for i in range(min(limite, 50)):
            comuna_data = random.choice(comunas_rm)
            comuna_nombre, lat_base, lon_base, precio_base = comuna_data
            
            if comuna and comuna.lower() != comuna_nombre.lower():
                continue
            
            # Variación aleatoria
            lat = lat_base + random.uniform(-0.02, 0.02)
            lon = lon_base + random.uniform(-0.02, 0.02)
            precio_var = precio_base * random.uniform(0.8, 1.3)
            superficie = random.randint(40, 150)
            dormitorios = random.randint(1, 4)
            
            prop_tipo = tipo_propiedad or random.choice([
                TipoPropiedad.DEPARTAMENTO,
                TipoPropiedad.CASA
            ])
            
            precio_total = precio_var * superficie
            
            # Aplicar filtros
            if precio_min_uf and precio_total < precio_min_uf:
                continue
            if precio_max_uf and precio_total > precio_max_uf:
                continue
            if superficie_min and superficie < superficie_min:
                continue
            if superficie_max and superficie > superficie_max:
                continue
            if dormitorios_min and dormitorios < dormitorios_min:
                continue
            
            propiedad = PropiedadMercado(
                id=f"prop_{i:05d}",
                tipo=prop_tipo,
                operacion=operacion,
                estado=random.choice(list(EstadoPropiedad)),
                direccion=f"Calle {random.randint(100, 999)} #{random.randint(1, 100)}",
                comuna=comuna_nombre,
                region=region,
                latitud=lat,
                longitud=lon,
                superficie_util=superficie,
                superficie_total=superficie * random.uniform(1.0, 1.2),
                dormitorios=dormitorios,
                baños=max(1, dormitorios - random.randint(0, 1)),
                estacionamientos=random.randint(0, 2),
                bodegas=random.randint(0, 1),
                piso=random.randint(1, 20) if prop_tipo == TipoPropiedad.DEPARTAMENTO else None,
                orientacion=random.choice(["Norte", "Sur", "Oriente", "Poniente"]),
                año_construccion=random.randint(1990, 2024),
                precio_publicado=round(precio_total, 1),
                precio_m2=round(precio_var, 2),
                gastos_comunes=random.randint(50000, 200000) if prop_tipo == TipoPropiedad.DEPARTAMENTO else None,
                fuente=random.choice(self._fuentes_activas),
                url=f"https://ejemplo.cl/propiedad/{i}",
                fecha_publicacion=date.today() - timedelta(days=random.randint(1, 90)),
                dias_publicado=random.randint(1, 90),
                segmento=self._determinar_segmento(precio_var),
                score_oportunidad=random.uniform(0.3, 0.9)
            )
            propiedades.append(propiedad)
        
        return propiedades
    
    def _determinar_segmento(self, precio_m2_uf: float) -> SegmentoMercado:
        """Determina el segmento de mercado según precio UF/m2."""
        for segmento, (min_precio, max_precio) in SEGMENTOS_PRECIO_UF_M2.items():
            if min_precio <= precio_m2_uf < max_precio:
                return segmento
        return SegmentoMercado.LUJO
    
    # =========================================================================
    # CLUSTERING ESPACIAL
    # =========================================================================
    
    async def analizar_clusters_espaciales(
        self,
        propiedades: List[PropiedadMercado],
        metodo: str = "getis_ord",
        distancia_km: float = 1.0,
        min_propiedades_cluster: int = 5
    ) -> List[ClusterEspacial]:
        """
        Identifica clusters espaciales de precios usando análisis de autocorrelación espacial.
        
        Args:
            propiedades: Lista de propiedades a analizar
            metodo: "getis_ord" (Gi*) o "lisa" (Local Moran's I)
            distancia_km: Radio de búsqueda para vecinos
            min_propiedades_cluster: Mínimo de propiedades para formar cluster
            
        Returns:
            Lista de clusters identificados
        """
        if len(propiedades) < min_propiedades_cluster:
            return []
        
        clusters = []
        
        # Calcular estadísticos globales
        precios_m2 = [p.precio_m2 for p in propiedades]
        media_global = statistics.mean(precios_m2)
        std_global = statistics.stdev(precios_m2)
        
        # Agrupar por ubicación aproximada (grid)
        grid_size = 0.01  # ~1km
        grids: Dict[Tuple[int, int], List[PropiedadMercado]] = defaultdict(list)
        
        for prop in propiedades:
            grid_x = int(prop.longitud / grid_size)
            grid_y = int(prop.latitud / grid_size)
            grids[(grid_x, grid_y)].append(prop)
        
        cluster_id = 0
        for (grid_x, grid_y), props_grid in grids.items():
            if len(props_grid) < min_propiedades_cluster:
                continue
            
            # Calcular estadísticos locales
            precios_locales = [p.precio_m2 for p in props_grid]
            media_local = statistics.mean(precios_locales)
            std_local = statistics.stdev(precios_locales) if len(precios_locales) > 1 else 0
            
            # Z-score (Getis-Ord Gi*)
            z_score = (media_local - media_global) / std_global if std_global > 0 else 0
            
            # P-value aproximado (distribución normal)
            p_value = 2 * (1 - self._norm_cdf(abs(z_score)))
            
            # Determinar tipo de cluster
            if p_value < 0.05:
                if z_score > 1.96:
                    tipo = TipoCluster.HOT_SPOT
                elif z_score < -1.96:
                    tipo = TipoCluster.COLD_SPOT
                else:
                    tipo = TipoCluster.NOT_SIGNIFICANT
            else:
                tipo = TipoCluster.NOT_SIGNIFICANT
            
            if tipo != TipoCluster.NOT_SIGNIFICANT:
                # Calcular centroide
                lat_centro = statistics.mean([p.latitud for p in props_grid])
                lon_centro = statistics.mean([p.longitud for p in props_grid])
                
                # Comunas únicas
                comunas = list(set(p.comuna for p in props_grid))
                
                # Descripción
                if tipo == TipoCluster.HOT_SPOT:
                    desc = f"Zona de precios altos ({media_local:.1f} UF/m²), {len(props_grid)} propiedades"
                else:
                    desc = f"Zona de precios bajos ({media_local:.1f} UF/m²), {len(props_grid)} propiedades"
                
                cluster = ClusterEspacial(
                    id=f"cluster_{cluster_id:03d}",
                    tipo=tipo,
                    centroide_lat=lat_centro,
                    centroide_lon=lon_centro,
                    radio_km=distancia_km,
                    propiedades_count=len(props_grid),
                    precio_m2_promedio=media_local,
                    precio_m2_mediana=statistics.median(precios_locales),
                    desviacion_estandar=std_local,
                    z_score=z_score,
                    p_value=p_value,
                    comunas=comunas,
                    descripcion=desc
                )
                clusters.append(cluster)
                cluster_id += 1
        
        # Ordenar por z_score absoluto (más significativos primero)
        clusters.sort(key=lambda c: abs(c.z_score), reverse=True)
        
        return clusters
    
    def _norm_cdf(self, x: float) -> float:
        """Función de distribución acumulada normal estándar (aproximación)."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    # =========================================================================
    # MODELO HEDÓNICO DE PRECIOS
    # =========================================================================
    
    async def calcular_valor_hedonico(
        self,
        propiedad: PropiedadMercado,
        comparables: List[PropiedadMercado]
    ) -> ModeloHedonicoResultado:
        """
        Calcula valor de una propiedad usando modelo hedónico.
        
        El modelo descompone el precio en contribuciones de:
        - Características físicas (superficie, dormitorios, etc.)
        - Ubicación (comuna, cercanía a servicios)
        - Condición y antigüedad
        
        Args:
            propiedad: Propiedad a valorar
            comparables: Propiedades comparables del mercado
            
        Returns:
            Resultado del modelo hedónico
        """
        if len(comparables) < 5:
            raise ValueError("Se requieren al menos 5 comparables para el modelo hedónico")
        
        # Calcular precio base de comparables
        precios_comparables = [c.precio_m2 for c in comparables]
        precio_base = statistics.median(precios_comparables)
        std_comparables = statistics.stdev(precios_comparables)
        
        # Contribuciones de factores
        contribuciones = {}
        
        # Factor superficie (comparación con promedio)
        sup_promedio = statistics.mean([c.superficie_util for c in comparables])
        factor_sup = (propiedad.superficie_util / sup_promedio - 1) * FACTORES_HEDONICOS["superficie"]
        contribuciones["superficie"] = factor_sup * precio_base
        
        # Factor dormitorios
        dorm_promedio = statistics.mean([c.dormitorios for c in comparables])
        factor_dorm = (propiedad.dormitorios / dorm_promedio - 1) * FACTORES_HEDONICOS["dormitorios"]
        contribuciones["dormitorios"] = factor_dorm * precio_base
        
        # Factor baños
        banos_promedio = statistics.mean([c.baños for c in comparables])
        factor_banos = (propiedad.baños / banos_promedio - 1) * FACTORES_HEDONICOS["baños"]
        contribuciones["baños"] = factor_banos * precio_base
        
        # Factor estacionamientos
        est_promedio = statistics.mean([c.estacionamientos for c in comparables])
        if est_promedio > 0:
            factor_est = (propiedad.estacionamientos / est_promedio - 1) * FACTORES_HEDONICOS["estacionamientos"]
        else:
            factor_est = propiedad.estacionamientos * 0.03
        contribuciones["estacionamientos"] = factor_est * precio_base
        
        # Factor antigüedad
        if propiedad.año_construccion:
            antiguedad = datetime.now().year - propiedad.año_construccion
            antig_promedio = statistics.mean([
                datetime.now().year - c.año_construccion 
                for c in comparables if c.año_construccion
            ]) if any(c.año_construccion for c in comparables) else 20
            
            factor_antig = -(antiguedad - antig_promedio) / antig_promedio * abs(FACTORES_HEDONICOS["antiguedad"])
            contribuciones["antiguedad"] = factor_antig * precio_base
        else:
            contribuciones["antiguedad"] = 0
        
        # Factor piso (para departamentos)
        if propiedad.piso and propiedad.tipo == TipoPropiedad.DEPARTAMENTO:
            pisos_comparables = [c.piso for c in comparables if c.piso]
            if pisos_comparables:
                piso_promedio = statistics.mean(pisos_comparables)
                factor_piso = (propiedad.piso - piso_promedio) / 20 * FACTORES_HEDONICOS["piso"]
                contribuciones["piso"] = factor_piso * precio_base
            else:
                contribuciones["piso"] = 0
        else:
            contribuciones["piso"] = 0
        
        # Calcular valor estimado
        ajuste_total = sum(contribuciones.values())
        valor_m2_estimado = precio_base + ajuste_total
        valor_estimado = valor_m2_estimado * propiedad.superficie_util
        
        # Intervalos de confianza (95%)
        margen_error = 1.96 * std_comparables
        intervalo = (
            max(0, valor_m2_estimado - margen_error) * propiedad.superficie_util,
            (valor_m2_estimado + margen_error) * propiedad.superficie_util
        )
        
        # Métricas del modelo (mock para desarrollo)
        r_squared = 0.85
        rmse = std_comparables * 0.5
        mape = 8.5
        
        # Comparación con precio publicado
        diferencia_mercado = ((propiedad.precio_m2 - valor_m2_estimado) / valor_m2_estimado) * 100
        
        # Determinar percentil
        posicion = sum(1 for c in comparables if c.precio_m2 < propiedad.precio_m2)
        percentil = int((posicion / len(comparables)) * 100)
        
        # Detectar oportunidad
        es_oportunidad = diferencia_mercado < -10
        tipo_oportunidad = None
        if diferencia_mercado < -20:
            tipo_oportunidad = "descuento_excepcional"
        elif diferencia_mercado < -10:
            tipo_oportunidad = "descuento_moderado"
        elif diferencia_mercado > 15:
            tipo_oportunidad = "sobreprecio"
        
        # Factores agregados
        factor_caracteristicas = sum([
            contribuciones.get("superficie", 0),
            contribuciones.get("dormitorios", 0),
            contribuciones.get("baños", 0),
            contribuciones.get("estacionamientos", 0)
        ])
        
        return ModeloHedonicoResultado(
            valor_estimado=round(valor_estimado, 1),
            valor_m2_estimado=round(valor_m2_estimado, 2),
            intervalo_confianza=intervalo,
            contribuciones={k: round(v, 2) for k, v in contribuciones.items()},
            factor_ubicacion=1.0,  # Simplificado
            factor_caracteristicas=factor_caracteristicas / precio_base,
            factor_condicion=contribuciones.get("antiguedad", 0) / precio_base,
            r_squared=r_squared,
            rmse=rmse,
            mape=mape,
            diferencia_mercado_pct=round(diferencia_mercado, 2),
            posicion_percentil=percentil,
            es_oportunidad=es_oportunidad,
            tipo_oportunidad=tipo_oportunidad
        )
    
    # =========================================================================
    # ANÁLISIS DE ZONAS
    # =========================================================================
    
    async def analizar_zona(
        self,
        propiedades: List[PropiedadMercado],
        nombre_zona: str,
        tipo_zona: str = "comuna"
    ) -> AnalisisZona:
        """
        Realiza análisis completo de una zona geográfica.
        
        Args:
            propiedades: Propiedades de la zona
            nombre_zona: Nombre de la zona
            tipo_zona: Tipo (comuna, sector, barrio)
            
        Returns:
            Análisis completo de la zona
        """
        if not propiedades:
            raise ValueError("No hay propiedades para analizar")
        
        # Separar por operación
        venta = [p for p in propiedades if p.operacion == TipoOperacion.VENTA]
        arriendo = [p for p in propiedades if p.operacion == TipoOperacion.ARRIENDO]
        
        # Conteo por tipo
        por_tipo = defaultdict(int)
        for p in propiedades:
            por_tipo[p.tipo.value] += 1
        
        # Conteo por estado
        por_estado = defaultdict(int)
        for p in propiedades:
            por_estado[p.estado.value] += 1
        
        # Estadísticos de precio venta
        precios_venta = [p.precio_m2 for p in venta] if venta else [0]
        precio_m2_promedio_venta = statistics.mean(precios_venta)
        precio_m2_mediana_venta = statistics.median(precios_venta)
        
        # Estadísticos de arriendo
        precios_arriendo = [p.precio_m2 for p in arriendo] if arriendo else [0]
        precio_m2_promedio_arriendo = statistics.mean(precios_arriendo)
        
        # Cap rate (arriendo anual / precio venta)
        cap_rate = (precio_m2_promedio_arriendo * 12 / precio_m2_promedio_venta * 100) if precio_m2_promedio_venta > 0 else 0
        
        # Días promedio venta (mock basado en días publicado)
        dias_venta = [p.dias_publicado for p in venta] if venta else [30]
        dias_promedio = int(statistics.mean(dias_venta))
        
        # Tasa de absorción (simplificada)
        tasa_absorcion = 0.15  # 15% mensual mock
        
        # Índice de liquidez
        indice_liquidez = min(1.0, 30 / dias_promedio) if dias_promedio > 0 else 0.5
        
        # Inventario en meses
        inventario_meses = len(venta) / (len(venta) * tasa_absorcion) if tasa_absorcion > 0 else 12
        
        # Tendencias (mock)
        variacion_mes = -1.5
        variacion_trimestre = 2.3
        variacion_año = 5.8
        
        # Determinar tendencia
        if variacion_año > 10:
            tendencia = TendenciaMercado.ALZA_FUERTE
        elif variacion_año > 5:
            tendencia = TendenciaMercado.ALZA_MODERADA
        elif variacion_año > -2:
            tendencia = TendenciaMercado.ESTABLE
        elif variacion_año > -5:
            tendencia = TendenciaMercado.BAJA_MODERADA
        else:
            tendencia = TendenciaMercado.BAJA_FUERTE
        
        return AnalisisZona(
            zona_id=f"zona_{hashlib.md5(nombre_zona.encode()).hexdigest()[:8]}",
            nombre=nombre_zona,
            tipo=tipo_zona,
            geometria_wkt=None,
            total_propiedades=len(propiedades),
            propiedades_venta=len(venta),
            propiedades_arriendo=len(arriendo),
            por_tipo=dict(por_tipo),
            por_estado=dict(por_estado),
            precio_m2_promedio_venta=round(precio_m2_promedio_venta, 2),
            precio_m2_mediana_venta=round(precio_m2_mediana_venta, 2),
            precio_m2_min_venta=round(min(precios_venta), 2),
            precio_m2_max_venta=round(max(precios_venta), 2),
            precio_m2_promedio_arriendo=round(precio_m2_promedio_arriendo, 2),
            cap_rate_promedio=round(cap_rate, 2),
            variacion_precio_mes=variacion_mes,
            variacion_precio_trimestre=variacion_trimestre,
            variacion_precio_año=variacion_año,
            tendencia=tendencia,
            dias_promedio_venta=dias_promedio,
            tasa_absorcion_mensual=tasa_absorcion,
            indice_liquidez=round(indice_liquidez, 2),
            inventario_meses=round(inventario_meses, 1),
            nuevas_publicaciones_mes=int(len(propiedades) * 0.2),
            propiedades_retiradas_mes=int(len(propiedades) * 0.15)
        )
    
    # =========================================================================
    # DETECCIÓN DE OPORTUNIDADES
    # =========================================================================
    
    async def detectar_oportunidades(
        self,
        propiedades: List[PropiedadMercado],
        umbral_descuento_pct: float = 10.0,
        cap_rate_minimo: float = 5.0,
        max_dias_publicado: int = 30
    ) -> List[OportunidadInversion]:
        """
        Detecta oportunidades de inversión en el mercado.
        
        Criterios:
        - Descuento vs. valor hedónico
        - Cap rate atractivo
        - Potencial de plusvalía
        - Tiempo en mercado
        
        Args:
            propiedades: Propiedades a analizar
            umbral_descuento_pct: Descuento mínimo para considerar oportunidad
            cap_rate_minimo: Cap rate mínimo para arriendo
            max_dias_publicado: Máximo días para considerar "fresca"
            
        Returns:
            Lista de oportunidades ordenadas por score
        """
        oportunidades = []
        
        # Obtener comparables por comuna
        por_comuna: Dict[str, List[PropiedadMercado]] = defaultdict(list)
        for p in propiedades:
            por_comuna[p.comuna].append(p)
        
        for prop in propiedades:
            # Solo propiedades en venta
            if prop.operacion != TipoOperacion.VENTA:
                continue
            
            comparables = por_comuna[prop.comuna]
            if len(comparables) < 5:
                continue
            
            # Calcular valor hedónico
            try:
                hedonico = await self.calcular_valor_hedonico(prop, comparables)
            except:
                continue
            
            # Verificar si es oportunidad
            if not hedonico.es_oportunidad:
                continue
            
            descuento = -hedonico.diferencia_mercado_pct
            if descuento < umbral_descuento_pct:
                continue
            
            # Calcular métricas
            razones = []
            riesgos = []
            
            if descuento > 20:
                razones.append(f"Descuento excepcional de {descuento:.1f}% vs mercado")
            else:
                razones.append(f"Descuento de {descuento:.1f}% vs mercado")
            
            if prop.dias_publicado <= max_dias_publicado:
                razones.append(f"Publicación reciente ({prop.dias_publicado} días)")
            else:
                riesgos.append(f"Tiempo en mercado prolongado ({prop.dias_publicado} días)")
            
            # Potencial plusvalía (basado en tendencia zona)
            potencial_plusvalia = 5.0  # Mock: 5% anual
            
            # Cap rate estimado
            precio_arriendo_estimado = prop.precio_m2 * 0.004  # 0.4% mensual
            cap_rate = (precio_arriendo_estimado * 12 / prop.precio_m2) * 100
            
            if cap_rate >= cap_rate_minimo:
                razones.append(f"Cap rate atractivo: {cap_rate:.1f}%")
            
            # ROI proyectado
            roi_anual = potencial_plusvalia + cap_rate
            
            # Scores
            score_precio = min(1.0, descuento / 25)
            score_ubicacion = 0.7  # Mock
            score_potencial = min(1.0, roi_anual / 15)
            score_total = (score_precio * 0.4 + score_ubicacion * 0.3 + score_potencial * 0.3)
            
            # Urgencia
            if descuento > 25 and prop.dias_publicado < 7:
                urgencia = "alta"
            elif descuento > 15:
                urgencia = "media"
            else:
                urgencia = "baja"
            
            # Recomendación
            if score_total > 0.8:
                recomendacion = "Fuerte oportunidad. Actuar rápidamente."
            elif score_total > 0.6:
                recomendacion = "Buena oportunidad. Verificar condiciones físicas."
            else:
                recomendacion = "Oportunidad moderada. Evaluar alternativas."
            
            oportunidad = OportunidadInversion(
                id=f"opp_{prop.id}",
                propiedad=prop,
                tipo_oportunidad=hedonico.tipo_oportunidad or "descuento",
                descuento_mercado_pct=round(descuento, 2),
                potencial_plusvalia_pct=round(potencial_plusvalia, 2),
                cap_rate_estimado=round(cap_rate, 2),
                roi_proyectado_anual=round(roi_anual, 2),
                razones=razones,
                riesgos=riesgos,
                recomendacion=recomendacion,
                urgencia=urgencia,
                score_total=round(score_total, 3),
                score_precio=round(score_precio, 3),
                score_ubicacion=round(score_ubicacion, 3),
                score_potencial=round(score_potencial, 3),
                comparables_similares=len(comparables),
                precio_comparables_promedio=round(statistics.mean([c.precio_m2 for c in comparables]), 2)
            )
            oportunidades.append(oportunidad)
        
        # Ordenar por score
        oportunidades.sort(key=lambda o: o.score_total, reverse=True)
        
        return oportunidades
    
    # =========================================================================
    # PROYECCIONES DE MERCADO
    # =========================================================================
    
    async def proyectar_mercado(
        self,
        zona: str,
        horizonte_meses: int = 12,
        tipo_propiedad: Optional[TipoPropiedad] = None
    ) -> ProyeccionMercado:
        """
        Genera proyección de precios para una zona.
        
        Metodología:
        - Tendencia histórica (60%)
        - Factores macroeconómicos (25%)
        - Oferta/demanda local (15%)
        
        Args:
            zona: Nombre de la zona
            horizonte_meses: Meses a proyectar
            tipo_propiedad: Tipo específico o todos
            
        Returns:
            Proyección de mercado
        """
        # Precio actual mock
        precio_actual = 75.0  # UF/m2
        
        # Componentes de la proyección
        tendencia_historica = 0.05  # 5% anual histórico
        factor_macro = 0.02  # Efecto positivo tasas bajas
        factor_oferta_demanda = -0.01  # Ligera sobreoferta
        factor_estacionalidad = 0.005  # Q1 típicamente positivo
        
        # Tasa de crecimiento compuesta
        tasa_anual = tendencia_historica + factor_macro + factor_oferta_demanda + factor_estacionalidad
        tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
        
        # Precio proyectado
        precio_proyectado = precio_actual * ((1 + tasa_mensual) ** horizonte_meses)
        variacion_esperada = ((precio_proyectado / precio_actual) - 1) * 100
        
        # Escenarios
        volatilidad = 0.08  # 8% anual
        escenario_optimista = precio_actual * ((1 + tasa_anual + volatilidad) ** (horizonte_meses/12))
        escenario_pesimista = precio_actual * ((1 + tasa_anual - volatilidad) ** (horizonte_meses/12))
        
        # Intervalos de confianza
        std_proyeccion = precio_actual * volatilidad * math.sqrt(horizonte_meses/12)
        intervalo_80 = (precio_proyectado - 1.28 * std_proyeccion, precio_proyectado + 1.28 * std_proyeccion)
        intervalo_95 = (precio_proyectado - 1.96 * std_proyeccion, precio_proyectado + 1.96 * std_proyeccion)
        
        # Nivel de incertidumbre
        if horizonte_meses <= 6:
            nivel_incertidumbre = "bajo"
        elif horizonte_meses <= 12:
            nivel_incertidumbre = "moderado"
        else:
            nivel_incertidumbre = "alto"
        
        # Factores de riesgo
        factores_riesgo = [
            "Cambios en política de tasas de interés",
            "Variaciones en tipo de cambio",
            "Ajustes regulatorios (Ley de Integración Social)",
            "Ciclo económico general"
        ]
        
        return ProyeccionMercado(
            fecha_proyeccion=date.today() + timedelta(days=horizonte_meses * 30),
            horizonte_meses=horizonte_meses,
            precio_m2_proyectado=round(precio_proyectado, 2),
            variacion_esperada_pct=round(variacion_esperada, 2),
            escenario_optimista=round(escenario_optimista, 2),
            escenario_pesimista=round(escenario_pesimista, 2),
            intervalo_80=(round(intervalo_80[0], 2), round(intervalo_80[1], 2)),
            intervalo_95=(round(intervalo_95[0], 2), round(intervalo_95[1], 2)),
            tendencia_historica=round(tendencia_historica * 100, 2),
            factor_macroeconomico=round(factor_macro * 100, 2),
            factor_oferta_demanda=round(factor_oferta_demanda * 100, 2),
            factor_estacionalidad=round(factor_estacionalidad * 100, 2),
            volatilidad_historica=round(volatilidad * 100, 2),
            nivel_incertidumbre=nivel_incertidumbre,
            factores_riesgo=factores_riesgo
        )
    
    # =========================================================================
    # GENERACIÓN DE REPORTES
    # =========================================================================
    
    async def generar_reporte_mercado(
        self,
        comunas: List[str],
        tipo_propiedad: Optional[TipoPropiedad] = None,
        incluir_proyecciones: bool = True,
        incluir_oportunidades: bool = True
    ) -> ReporteMercado:
        """
        Genera reporte completo de mercado.
        
        Args:
            comunas: Lista de comunas a incluir
            tipo_propiedad: Filtrar por tipo
            incluir_proyecciones: Incluir proyecciones
            incluir_oportunidades: Incluir oportunidades
            
        Returns:
            Reporte completo de mercado
        """
        # Obtener propiedades
        todas_propiedades = []
        for comuna in comunas:
            props = await self.obtener_oferta_mercado(
                comuna=comuna,
                tipo_propiedad=tipo_propiedad,
                limite=200
            )
            todas_propiedades.extend(props)
        
        # Analizar zonas
        zonas = []
        for comuna in comunas:
            props_comuna = [p for p in todas_propiedades if p.comuna == comuna]
            if props_comuna:
                zona = await self.analizar_zona(props_comuna, comuna)
                zonas.append(zona)
        
        # Clusters espaciales
        clusters = await self.analizar_clusters_espaciales(todas_propiedades)
        
        # Proyecciones
        proyecciones = []
        if incluir_proyecciones:
            for comuna in comunas[:3]:  # Top 3 comunas
                proy = await self.proyectar_mercado(comuna, horizonte_meses=12)
                proyecciones.append(proy)
        
        # Oportunidades
        oportunidades = []
        if incluir_oportunidades:
            oportunidades = await self.detectar_oportunidades(todas_propiedades)
            oportunidades = oportunidades[:10]  # Top 10
        
        # Determinar tendencia general
        variaciones = [z.variacion_precio_año for z in zonas]
        variacion_promedio = statistics.mean(variaciones) if variaciones else 0
        
        if variacion_promedio > 10:
            tendencia_general = TendenciaMercado.ALZA_FUERTE
        elif variacion_promedio > 5:
            tendencia_general = TendenciaMercado.ALZA_MODERADA
        elif variacion_promedio > -2:
            tendencia_general = TendenciaMercado.ESTABLE
        elif variacion_promedio > -5:
            tendencia_general = TendenciaMercado.BAJA_MODERADA
        else:
            tendencia_general = TendenciaMercado.BAJA_FUERTE
        
        # Índice de actividad (0-100)
        indice_actividad = min(100, len(todas_propiedades) / 10)
        
        # Resumen ejecutivo
        resumen = f"""
Análisis de mercado para {len(comunas)} comunas de la Región Metropolitana.
Se analizaron {len(todas_propiedades)} propiedades de {len(self._fuentes_activas)} fuentes.

Precio promedio: {statistics.mean([p.precio_m2 for p in todas_propiedades]):.1f} UF/m²
Tendencia general: {tendencia_general.value}
Se identificaron {len(clusters)} clusters espaciales significativos.
Se detectaron {len(oportunidades)} oportunidades de inversión.
        """.strip()
        
        # Recomendaciones
        recomendaciones = [
            "Evaluar propiedades en clusters de precios bajos con potencial de valorización",
            "Considerar inversión en comunas con tendencia alcista moderada",
            "Monitorear tiempo de permanencia en mercado como indicador de demanda",
            "Diversificar inversiones entre diferentes segmentos de mercado"
        ]
        
        return ReporteMercado(
            id=f"rep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            fecha_generacion=datetime.now(),
            periodo_analisis="Último mes",
            zonas_analizadas=comunas,
            total_propiedades_analizadas=len(todas_propiedades),
            fuentes_datos=self._fuentes_activas,
            resumen=resumen,
            tendencia_general=tendencia_general,
            indice_actividad=round(indice_actividad, 1),
            zonas=zonas,
            clusters=clusters,
            proyecciones=proyecciones,
            oportunidades=oportunidades,
            indicadores_macro={
                "uf_actual": 37800.0,
                "tasa_hipotecaria_promedio": 4.5,
                "ipc_anual": 3.2,
                "pib_crecimiento": 2.1,
                "desempleo": 8.7
            },
            recomendaciones=recomendaciones
        )
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def calcular_distancia_km(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calcula distancia en km entre dos puntos (Haversine)."""
        R = 6371  # Radio de la Tierra en km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def obtener_estadisticas_globales(self) -> Dict[str, Any]:
        """Obtiene estadísticas globales del mercado."""
        return {
            "fecha_actualizacion": datetime.now().isoformat(),
            "total_propiedades_activas": 15420,
            "venta": {
                "total": 9850,
                "precio_m2_promedio_uf": 72.5,
                "variacion_mensual_pct": -1.2
            },
            "arriendo": {
                "total": 5570,
                "precio_m2_promedio_uf": 0.32,
                "variacion_mensual_pct": 0.5
            },
            "por_tipo": {
                "departamento": 8200,
                "casa": 4500,
                "oficina": 1200,
                "local_comercial": 850,
                "terreno": 670
            },
            "comunas_top_5": [
                {"comuna": "Santiago Centro", "propiedades": 2150},
                {"comuna": "Las Condes", "propiedades": 1890},
                {"comuna": "Providencia", "propiedades": 1650},
                {"comuna": "Ñuñoa", "propiedades": 1420},
                {"comuna": "La Florida", "propiedades": 1180}
            ]
        }


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================

_servicio_mercado: Optional[ServicioMercadoSuelo] = None


def get_servicio_mercado() -> ServicioMercadoSuelo:
    """Obtiene instancia singleton del servicio."""
    global _servicio_mercado
    if _servicio_mercado is None:
        _servicio_mercado = ServicioMercadoSuelo()
    return _servicio_mercado
