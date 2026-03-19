"""
DATAPOLIS v3.0 - M01 Ficha Propiedad
=====================================
Módulo de información técnica detallada de propiedades inmobiliarias.
Centraliza datos físicos, legales, urbanísticos y de mercado.

Funcionalidades:
- Ficha técnica completa
- Información urbanística (PRC, usos de suelo)
- Características físicas y constructivas
- Historial de transacciones
- Comparables de mercado
- Integración SII, CBR, DOM
- Certificados y permisos

Fuentes de datos:
- SII (avalúos, roles, propietarios)
- Conservador de Bienes Raíces
- Direcciones de Obras Municipales
- Planes Reguladores Comunales
- Portal Inmobiliario, Yapo, Toctoc

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2026-02
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import uuid
import statistics
import hashlib

logger = logging.getLogger(__name__)


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
    SITIO_ERIAZO = "sitio_eriazo"
    INDUSTRIAL = "industrial"
    AGRICOLA = "agricola"
    MIXTO = "mixto"


class EstadoConservacion(str, Enum):
    """Estado de conservación del inmueble"""
    NUEVO = "nuevo"
    EXCELENTE = "excelente"
    BUENO = "bueno"
    REGULAR = "regular"
    DETERIORADO = "deteriorado"
    EN_RUINAS = "en_ruinas"
    EN_CONSTRUCCION = "en_construccion"
    EN_REMODELACION = "en_remodelacion"


class TipoEstructura(str, Enum):
    """Tipo de estructura constructiva"""
    HORMIGON_ARMADO = "hormigon_armado"
    ALBAÑILERIA_REFORZADA = "albanileria_reforzada"
    ALBAÑILERIA_CONFINADA = "albanileria_confinada"
    ESTRUCTURA_METALICA = "estructura_metalica"
    MADERA = "madera"
    ADOBE = "adobe"
    MIXTA = "mixta"
    PREFABRICADA = "prefabricada"


class CalidadTerminaciones(str, Enum):
    """Calidad de terminaciones"""
    LUJO = "lujo"
    ALTA = "alta"
    MEDIA_ALTA = "media_alta"
    MEDIA = "media"
    ECONOMICA = "economica"
    SOCIAL = "social"


class ZonaUrbana(str, Enum):
    """Zonas según Plan Regulador"""
    RESIDENCIAL_EXCLUSIVA = "ZR1"  # Solo vivienda
    RESIDENCIAL_MIXTA = "ZR2"  # Vivienda + comercio menor
    COMERCIAL = "ZC"  # Comercio
    EQUIPAMIENTO = "ZE"  # Equipamiento
    INDUSTRIAL_EXCLUSIVA = "ZI1"  # Industria inofensiva
    INDUSTRIAL_MIXTA = "ZI2"  # Industria molesta
    AREA_VERDE = "ZAV"  # Área verde
    PROTECCION = "ZP"  # Protección
    EXTENSION_URBANA = "ZEU"  # Extensión
    RURAL = "ZR"  # Rural


class TipoTransaccion(str, Enum):
    """Tipos de transacciones registradas"""
    COMPRAVENTA = "compraventa"
    ARRIENDO = "arriendo"
    HIPOTECA = "hipoteca"
    ALZAMIENTO_HIPOTECA = "alzamiento_hipoteca"
    PROHIBICION = "prohibicion"
    ALZAMIENTO_PROHIBICION = "alzamiento_prohibicion"
    USUFRUCTO = "usufructo"
    SERVIDUMBRE = "servidumbre"
    ADJUDICACION = "adjudicacion"
    DONACION = "donacion"
    HERENCIA = "herencia"


class EstadoLegal(str, Enum):
    """Estado legal de la propiedad"""
    LIMPIO = "limpio"  # Sin gravámenes ni litigios
    CON_HIPOTECA = "con_hipoteca"
    CON_PROHIBICION = "con_prohibicion"
    EN_LITIGIO = "en_litigio"
    EN_SUCESION = "en_sucesion"
    IRREGULAR = "irregular"
    EXPROPIACION = "expropiacion"


class FuenteDatos(str, Enum):
    """Fuentes de datos"""
    SII = "sii"
    CBR = "cbr"
    DOM = "dom"
    MINVU = "minvu"
    PORTAL_INMOBILIARIO = "portal_inmobiliario"
    YAPO = "yapo"
    TOCTOC = "toctoc"
    USUARIO = "usuario"
    TASACION = "tasacion"


# Coeficientes de depreciación por material
DEPRECIACION_ANUAL: Dict[TipoEstructura, float] = {
    TipoEstructura.HORMIGON_ARMADO: 0.008,  # 0.8% anual
    TipoEstructura.ALBAÑILERIA_REFORZADA: 0.010,
    TipoEstructura.ALBAÑILERIA_CONFINADA: 0.012,
    TipoEstructura.ESTRUCTURA_METALICA: 0.015,
    TipoEstructura.MADERA: 0.020,
    TipoEstructura.ADOBE: 0.025,
    TipoEstructura.MIXTA: 0.012,
    TipoEstructura.PREFABRICADA: 0.018,
}

# Vida útil estimada por tipo de estructura (años)
VIDA_UTIL: Dict[TipoEstructura, int] = {
    TipoEstructura.HORMIGON_ARMADO: 80,
    TipoEstructura.ALBAÑILERIA_REFORZADA: 60,
    TipoEstructura.ALBAÑILERIA_CONFINADA: 50,
    TipoEstructura.ESTRUCTURA_METALICA: 50,
    TipoEstructura.MADERA: 40,
    TipoEstructura.ADOBE: 40,
    TipoEstructura.MIXTA: 50,
    TipoEstructura.PREFABRICADA: 35,
}


# =============================================================================
# DATA CLASSES - INFORMACIÓN BÁSICA
# =============================================================================

@dataclass
class UbicacionPropiedad:
    """Ubicación detallada de la propiedad"""
    direccion_completa: str
    numero: str
    departamento: Optional[str]
    piso: Optional[int]
    comuna: str
    region: str
    codigo_postal: Optional[str]
    latitud: float
    longitud: float
    manzana: Optional[str]
    sitio: Optional[str]
    unidad_vecinal: Optional[str]
    distrito_censal: Optional[str]
    zona_censal: Optional[str]


@dataclass
class IdentificacionSII:
    """Identificación tributaria SII"""
    rol_sii: str
    rol_avaluo: Optional[str]
    rol_matriz: Optional[str]  # Para subdivisiones
    comuna_sii: int
    manzana_sii: int
    predio_sii: int
    serie: Optional[str]
    destino_sii: int  # Código destino catastral
    destino_descripcion: str
    propietario_rut: Optional[str]
    propietario_nombre: Optional[str]
    fecha_ultimo_avaluo: Optional[date]


@dataclass
class SuperficiesPropiedad:
    """Superficies de la propiedad"""
    # Terreno
    terreno_m2: Optional[float]
    terreno_escritura_m2: Optional[float]
    terreno_municipal_m2: Optional[float]
    terreno_sii_m2: Optional[float]
    
    # Construcción
    construida_total_m2: float
    construida_util_m2: float
    construida_comun_m2: Optional[float]
    construida_sii_m2: Optional[float]
    
    # Adicionales
    terraza_m2: Optional[float]
    jardin_m2: Optional[float]
    estacionamientos_m2: Optional[float]
    bodega_m2: Optional[float]
    piscina_m2: Optional[float]
    
    # Coeficientes (copropiedad)
    coeficiente_copropiedad: Optional[float]
    alicuota: Optional[float]


@dataclass
class CaracteristicasConstructivas:
    """Características constructivas del inmueble"""
    tipo_estructura: TipoEstructura
    calidad_terminaciones: CalidadTerminaciones
    estado_conservacion: EstadoConservacion
    ano_construccion: int
    ano_remodelacion: Optional[int]
    pisos_edificio: Optional[int]
    piso_unidad: Optional[int]
    orientacion: Optional[str]  # N, S, E, O, NE, NO, SE, SO
    vista: Optional[str]
    iluminacion_natural: Optional[str]  # Excelente, Buena, Regular, Deficiente
    ventilacion: Optional[str]
    aislacion_termica: Optional[str]
    aislacion_acustica: Optional[str]
    eficiencia_energetica: Optional[str]  # Letra CEV
    certificacion_energetica_id: Optional[str]


@dataclass
class Dependencias:
    """Distribución de dependencias"""
    dormitorios: int
    banos: int
    banos_visita: int
    living: int
    comedor: int
    living_comedor: bool
    cocina: int
    cocina_americana: bool
    logia: int
    escritorio: int
    sala_estar: int
    walk_in_closet: int
    despensa: int
    lavadero: int
    quincho: int
    sala_juegos: int
    gimnasio_privado: int
    sauna: int
    dependencias_servicio: int
    bano_servicio: int


@dataclass
class Estacionamientos:
    """Información de estacionamientos"""
    cantidad: int
    tipo: str  # cubierto, descubierto, subterraneo, automatizado
    ubicacion: Optional[str]
    numeros: List[str]
    superficie_total_m2: Optional[float]
    tiene_bodega: bool
    bodega_m2: Optional[float]
    bodega_numero: Optional[str]


@dataclass
class Amenities:
    """Amenidades y características adicionales"""
    # Interiores
    calefaccion: Optional[str]  # central, individual, split, radiadores
    aire_acondicionado: bool
    chimenea: bool
    piso_radiante: bool
    agua_caliente: str  # calefon, termo, central, solar
    gas: str  # natural, licuado, electrico
    
    # Seguridad
    alarma: bool
    circuito_cerrado: bool
    portero_electrico: bool
    citofono: bool
    control_acceso: bool
    conserje_24h: bool
    
    # Edificio/Condominio
    ascensor: bool
    cantidad_ascensores: int
    piscina_comun: bool
    gimnasio_comun: bool
    quincho_comun: bool
    sala_eventos: bool
    areas_verdes_comunes: bool
    juegos_infantiles: bool
    cancha_deportiva: bool
    sauna_comun: bool
    lavanderia_comun: bool
    bicicletero: bool
    salon_multiuso: bool


# =============================================================================
# DATA CLASSES - INFORMACIÓN LEGAL Y URBANÍSTICA
# =============================================================================

@dataclass
class InformacionUrbanistica:
    """Información urbanística según Plan Regulador"""
    zona: ZonaUrbana
    zona_secundaria: Optional[str]
    uso_suelo_permitido: List[str]
    uso_suelo_prohibido: List[str]
    coeficiente_constructibilidad: float
    coeficiente_ocupacion_suelo: float
    densidad_maxima: Optional[int]  # hab/ha
    altura_maxima_m: Optional[float]
    pisos_maximos: Optional[int]
    antejardín_minimo_m: Optional[float]
    rasante: Optional[float]  # Grados
    adosamiento_permitido: bool
    distancia_medianeros_m: Optional[float]
    zona_inundable: bool
    zona_proteccion: bool
    zona_patrimonial: bool
    zona_riesgo: Optional[str]
    restricciones_adicionales: List[str]
    plan_regulador_vigente: str
    fecha_aprobacion_prc: Optional[date]


@dataclass
class Gravamen:
    """Gravamen o carga sobre la propiedad"""
    tipo: str  # hipoteca, prohibicion, usufructo, servidumbre
    institucion: Optional[str]
    monto_uf: Optional[float]
    fecha_inscripcion: date
    fecha_vencimiento: Optional[date]
    numero_inscripcion: str
    foja: int
    numero: int
    ano: int
    vigente: bool
    observaciones: Optional[str]


@dataclass
class InformacionLegal:
    """Estado legal de la propiedad"""
    estado: EstadoLegal
    inscripcion_dominio: str  # Foja-Número-Año
    foja: int
    numero: int
    ano: int
    conservador: str
    fecha_inscripcion: date
    titulo_anterior: Optional[str]
    gravamenes: List[Gravamen]
    prohibiciones: List[Gravamen]
    litigios_pendientes: bool
    litigios_detalle: Optional[str]
    expropiacion_afecta: bool
    expropiacion_detalle: Optional[str]
    limitaciones_dominio: List[str]
    servidumbres: List[str]


@dataclass
class Transaccion:
    """Registro de transacción histórica"""
    tipo: TipoTransaccion
    fecha: date
    precio_uf: Optional[float]
    precio_clp: Optional[float]
    comprador: Optional[str]
    vendedor: Optional[str]
    notaria: Optional[str]
    repertorio: Optional[str]
    inscripcion_cbr: Optional[str]
    fuente: FuenteDatos
    observaciones: Optional[str]


# =============================================================================
# DATA CLASSES - VALORIZACIÓN Y MERCADO
# =============================================================================

@dataclass
class AvaluoFiscal:
    """Avalúo fiscal SII"""
    avaluo_total_clp: int
    avaluo_terreno_clp: int
    avaluo_construccion_clp: int
    avaluo_total_uf: float
    avaluo_terreno_uf: float
    avaluo_construccion_uf: float
    fecha_avaluo: date
    exento_contribuciones: bool
    monto_contribuciones_semestral: int
    destino_catastral: int
    material_predominante: Optional[str]
    calidad_construccion: Optional[str]


@dataclass
class ValorMercado:
    """Estimación de valor de mercado"""
    valor_uf: float
    valor_uf_m2: float
    valor_clp: int
    fecha_estimacion: date
    metodologia: str  # comparables, hedónico, flujos, costo
    fuente: str
    confianza: float  # 0-1
    rango_inferior_uf: float
    rango_superior_uf: float
    comparables_utilizados: int
    ajustes_aplicados: Dict[str, float]


@dataclass
class ComparableMercado:
    """Propiedad comparable de mercado"""
    id: str
    direccion: str
    comuna: str
    distancia_m: float
    tipo_propiedad: TipoPropiedad
    superficie_util_m2: float
    dormitorios: int
    banos: int
    estacionamientos: int
    ano_construccion: int
    precio_uf: float
    precio_uf_m2: float
    tipo_operacion: str  # venta, arriendo
    fecha_publicacion: date
    dias_publicado: int
    fuente: FuenteDatos
    url: Optional[str]
    similitud_score: float  # 0-1


@dataclass
class IndicadoresMercado:
    """Indicadores de mercado de la zona"""
    precio_m2_promedio_uf: float
    precio_m2_mediana_uf: float
    precio_m2_min_uf: float
    precio_m2_max_uf: float
    desviacion_estandar: float
    oferta_activa: int
    transacciones_ultimo_ano: int
    dias_promedio_venta: int
    tasa_absorcion: float
    tendencia_precios: str  # alza, estable, baja
    variacion_anual_pct: float
    segmento_mercado: str
    liquidez: str  # alta, media, baja
    fecha_actualizacion: date


# =============================================================================
# DATA CLASS PRINCIPAL - FICHA PROPIEDAD
# =============================================================================

@dataclass
class FichaPropiedad:
    """Ficha completa de propiedad inmobiliaria"""
    # Identificación
    id: str
    codigo: str  # FP-2026-000001
    rol_sii: str
    tipo_propiedad: TipoPropiedad
    nombre: str
    descripcion: Optional[str]
    
    # Componentes
    ubicacion: UbicacionPropiedad
    identificacion_sii: IdentificacionSII
    superficies: SuperficiesPropiedad
    caracteristicas: CaracteristicasConstructivas
    dependencias: Dependencias
    estacionamientos: Estacionamientos
    amenities: Amenities
    
    # Legal y urbanístico
    informacion_urbanistica: Optional[InformacionUrbanistica]
    informacion_legal: Optional[InformacionLegal]
    historial_transacciones: List[Transaccion]
    
    # Valorización
    avaluo_fiscal: Optional[AvaluoFiscal]
    valor_mercado: Optional[ValorMercado]
    comparables: List[ComparableMercado]
    indicadores_mercado: Optional[IndicadoresMercado]
    
    # Metadata
    expediente_id: Optional[str]
    fuentes_datos: List[FuenteDatos]
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    actualizado_por: str
    version: int
    completitud_pct: float
    
    # Campos calculados
    depreciacion_acumulada_pct: float = 0.0
    vida_util_remanente_anos: int = 0
    valor_reposicion_uf: float = 0.0


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class ServicioFichaPropiedad:
    """
    Servicio para gestión de fichas de propiedad.
    Integra información de múltiples fuentes.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ServicioFichaPropiedad")
        self._fichas_cache: Dict[str, FichaPropiedad] = {}
        self._contador_fichas = 0
    
    # =========================================================================
    # GESTIÓN DE FICHAS
    # =========================================================================
    
    async def crear_ficha(
        self,
        rol_sii: str,
        tipo_propiedad: TipoPropiedad,
        direccion: str,
        comuna: str,
        region: str,
        latitud: float,
        longitud: float,
        superficie_util_m2: float,
        ano_construccion: int,
        creado_por: str,
        descripcion: Optional[str] = None
    ) -> FichaPropiedad:
        """
        Crea una nueva ficha de propiedad.
        
        Args:
            rol_sii: Rol SII de la propiedad
            tipo_propiedad: Tipo de propiedad
            direccion: Dirección completa
            comuna: Comuna
            region: Región
            latitud: Latitud
            longitud: Longitud
            superficie_util_m2: Superficie útil
            ano_construccion: Año de construcción
            creado_por: Usuario creador
            descripcion: Descripción opcional
            
        Returns:
            FichaPropiedad creada
        """
        self.logger.info(f"Creando ficha para rol {rol_sii}")
        
        # Generar código
        self._contador_fichas += 1
        codigo = f"FP-{datetime.now().year}-{self._contador_fichas:06d}"
        
        ahora = datetime.now()
        
        # Crear componentes básicos
        ubicacion = UbicacionPropiedad(
            direccion_completa=direccion,
            numero=self._extraer_numero(direccion),
            departamento=None,
            piso=None,
            comuna=comuna,
            region=region,
            codigo_postal=None,
            latitud=latitud,
            longitud=longitud,
            manzana=None,
            sitio=None,
            unidad_vecinal=None,
            distrito_censal=None,
            zona_censal=None
        )
        
        identificacion = self._crear_identificacion_sii(rol_sii, comuna)
        superficies = self._crear_superficies_basicas(superficie_util_m2)
        caracteristicas = self._crear_caracteristicas_basicas(ano_construccion)
        dependencias = self._crear_dependencias_basicas(tipo_propiedad)
        estacionamientos = Estacionamientos(
            cantidad=0, tipo="ninguno", ubicacion=None, numeros=[],
            superficie_total_m2=None, tiene_bodega=False,
            bodega_m2=None, bodega_numero=None
        )
        amenities = self._crear_amenities_basicos()
        
        ficha = FichaPropiedad(
            id=str(uuid.uuid4()),
            codigo=codigo,
            rol_sii=rol_sii,
            tipo_propiedad=tipo_propiedad,
            nombre=f"{tipo_propiedad.value.replace('_', ' ').title()} {comuna}",
            descripcion=descripcion,
            ubicacion=ubicacion,
            identificacion_sii=identificacion,
            superficies=superficies,
            caracteristicas=caracteristicas,
            dependencias=dependencias,
            estacionamientos=estacionamientos,
            amenities=amenities,
            informacion_urbanistica=None,
            informacion_legal=None,
            historial_transacciones=[],
            avaluo_fiscal=None,
            valor_mercado=None,
            comparables=[],
            indicadores_mercado=None,
            expediente_id=None,
            fuentes_datos=[FuenteDatos.USUARIO],
            fecha_creacion=ahora,
            fecha_actualizacion=ahora,
            actualizado_por=creado_por,
            version=1,
            completitud_pct=25.0
        )
        
        # Calcular campos derivados
        self._calcular_depreciacion(ficha)
        
        # Guardar en caché
        self._fichas_cache[ficha.id] = ficha
        
        self.logger.info(f"Ficha {codigo} creada para {rol_sii}")
        return ficha
    
    async def obtener_ficha(
        self,
        ficha_id: Optional[str] = None,
        rol_sii: Optional[str] = None
    ) -> Optional[FichaPropiedad]:
        """
        Obtiene una ficha por ID o rol SII.
        
        Args:
            ficha_id: ID de la ficha
            rol_sii: Rol SII alternativo
            
        Returns:
            FichaPropiedad o None
        """
        if ficha_id and ficha_id in self._fichas_cache:
            return self._fichas_cache[ficha_id]
        
        if rol_sii:
            for ficha in self._fichas_cache.values():
                if ficha.rol_sii == rol_sii:
                    return ficha
        
        # Mock: generar ficha de ejemplo
        if ficha_id:
            return self._generar_ficha_ejemplo(ficha_id)
        
        return None
    
    async def actualizar_ficha(
        self,
        ficha_id: str,
        actualizaciones: Dict[str, Any],
        usuario_id: str
    ) -> FichaPropiedad:
        """
        Actualiza una ficha de propiedad.
        
        Args:
            ficha_id: ID de la ficha
            actualizaciones: Campos a actualizar
            usuario_id: Usuario que actualiza
            
        Returns:
            Ficha actualizada
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        for campo, valor in actualizaciones.items():
            if hasattr(ficha, campo):
                setattr(ficha, campo, valor)
        
        ficha.fecha_actualizacion = datetime.now()
        ficha.actualizado_por = usuario_id
        ficha.version += 1
        
        # Recalcular completitud
        ficha.completitud_pct = self._calcular_completitud(ficha)
        
        # Recalcular depreciación
        self._calcular_depreciacion(ficha)
        
        self._fichas_cache[ficha_id] = ficha
        
        return ficha
    
    async def eliminar_ficha(
        self,
        ficha_id: str,
        usuario_id: str
    ) -> bool:
        """
        Elimina una ficha de propiedad.
        """
        if ficha_id in self._fichas_cache:
            del self._fichas_cache[ficha_id]
            self.logger.info(f"Ficha {ficha_id} eliminada por {usuario_id}")
            return True
        return False
    
    # =========================================================================
    # INTEGRACIONES EXTERNAS
    # =========================================================================
    
    async def sincronizar_sii(
        self,
        ficha_id: str
    ) -> Dict[str, Any]:
        """
        Sincroniza datos con SII.
        
        Args:
            ficha_id: ID de la ficha
            
        Returns:
            Datos actualizados
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        self.logger.info(f"Sincronizando con SII para {ficha.rol_sii}")
        
        # Mock: datos SII
        datos_sii = {
            "rol_sii": ficha.rol_sii,
            "direccion": ficha.ubicacion.direccion_completa,
            "comuna": ficha.ubicacion.comuna,
            "destino": 1,  # Habitacional
            "destino_descripcion": "Habitacional",
            "superficie_terreno_m2": 150.0,
            "superficie_construida_m2": 95.0,
            "ano_construccion": ficha.caracteristicas.ano_construccion,
            "material": "H",  # Hormigón
            "calidad": "B",  # Buena
            "avaluo_total": 85000000,
            "avaluo_terreno": 45000000,
            "avaluo_construccion": 40000000,
            "exento": False,
            "contribuciones_semestral": 285000,
            "propietario_rut": "12.345.678-9",
            "propietario_nombre": "Juan Pérez González",
            "fecha_avaluo": date.today() - timedelta(days=180),
            "fuente": "SII",
            "timestamp": datetime.now().isoformat()
        }
        
        # Actualizar ficha con datos SII
        uf_valor = 38500  # Mock UF
        
        ficha.identificacion_sii.destino_sii = datos_sii["destino"]
        ficha.identificacion_sii.destino_descripcion = datos_sii["destino_descripcion"]
        ficha.identificacion_sii.propietario_rut = datos_sii["propietario_rut"]
        ficha.identificacion_sii.propietario_nombre = datos_sii["propietario_nombre"]
        ficha.identificacion_sii.fecha_ultimo_avaluo = datos_sii["fecha_avaluo"]
        
        ficha.superficies.terreno_sii_m2 = datos_sii["superficie_terreno_m2"]
        ficha.superficies.construida_sii_m2 = datos_sii["superficie_construida_m2"]
        
        ficha.avaluo_fiscal = AvaluoFiscal(
            avaluo_total_clp=datos_sii["avaluo_total"],
            avaluo_terreno_clp=datos_sii["avaluo_terreno"],
            avaluo_construccion_clp=datos_sii["avaluo_construccion"],
            avaluo_total_uf=round(datos_sii["avaluo_total"] / uf_valor, 2),
            avaluo_terreno_uf=round(datos_sii["avaluo_terreno"] / uf_valor, 2),
            avaluo_construccion_uf=round(datos_sii["avaluo_construccion"] / uf_valor, 2),
            fecha_avaluo=datos_sii["fecha_avaluo"],
            exento_contribuciones=datos_sii["exento"],
            monto_contribuciones_semestral=datos_sii["contribuciones_semestral"],
            destino_catastral=datos_sii["destino"],
            material_predominante=datos_sii["material"],
            calidad_construccion=datos_sii["calidad"]
        )
        
        if FuenteDatos.SII not in ficha.fuentes_datos:
            ficha.fuentes_datos.append(FuenteDatos.SII)
        
        ficha.fecha_actualizacion = datetime.now()
        ficha.completitud_pct = self._calcular_completitud(ficha)
        
        self._fichas_cache[ficha_id] = ficha
        
        return datos_sii
    
    async def sincronizar_cbr(
        self,
        ficha_id: str
    ) -> Dict[str, Any]:
        """
        Sincroniza datos con Conservador de Bienes Raíces.
        
        Args:
            ficha_id: ID de la ficha
            
        Returns:
            Datos actualizados
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        self.logger.info(f"Sincronizando con CBR para {ficha.rol_sii}")
        
        # Mock: datos CBR
        datos_cbr = {
            "inscripcion": "Foja 1234 N° 567 Año 2020",
            "foja": 1234,
            "numero": 567,
            "ano": 2020,
            "conservador": "CBR Santiago",
            "fecha_inscripcion": date(2020, 3, 15),
            "titulo_anterior": "Foja 890 N° 123 Año 2015",
            "estado": "limpio",
            "gravamenes": [
                {
                    "tipo": "hipoteca",
                    "institucion": "Banco Estado",
                    "monto_uf": 2500,
                    "fecha_inscripcion": date(2020, 3, 15),
                    "numero_inscripcion": "H-2020-12345",
                    "foja": 1234,
                    "numero": 568,
                    "ano": 2020,
                    "vigente": True
                }
            ],
            "prohibiciones": [],
            "litigios": False,
            "servidumbres": [],
            "fuente": "CBR",
            "timestamp": datetime.now().isoformat()
        }
        
        # Convertir gravámenes
        gravamenes = []
        for g in datos_cbr["gravamenes"]:
            gravamenes.append(Gravamen(
                tipo=g["tipo"],
                institucion=g["institucion"],
                monto_uf=g["monto_uf"],
                fecha_inscripcion=g["fecha_inscripcion"],
                fecha_vencimiento=None,
                numero_inscripcion=g["numero_inscripcion"],
                foja=g["foja"],
                numero=g["numero"],
                ano=g["ano"],
                vigente=g["vigente"],
                observaciones=None
            ))
        
        ficha.informacion_legal = InformacionLegal(
            estado=EstadoLegal(datos_cbr["estado"]) if datos_cbr["estado"] in [e.value for e in EstadoLegal] else EstadoLegal.CON_HIPOTECA,
            inscripcion_dominio=datos_cbr["inscripcion"],
            foja=datos_cbr["foja"],
            numero=datos_cbr["numero"],
            ano=datos_cbr["ano"],
            conservador=datos_cbr["conservador"],
            fecha_inscripcion=datos_cbr["fecha_inscripcion"],
            titulo_anterior=datos_cbr["titulo_anterior"],
            gravamenes=gravamenes,
            prohibiciones=[],
            litigios_pendientes=datos_cbr["litigios"],
            litigios_detalle=None,
            expropiacion_afecta=False,
            expropiacion_detalle=None,
            limitaciones_dominio=[],
            servidumbres=datos_cbr["servidumbres"]
        )
        
        if FuenteDatos.CBR not in ficha.fuentes_datos:
            ficha.fuentes_datos.append(FuenteDatos.CBR)
        
        ficha.fecha_actualizacion = datetime.now()
        ficha.completitud_pct = self._calcular_completitud(ficha)
        
        self._fichas_cache[ficha_id] = ficha
        
        return datos_cbr
    
    async def obtener_informacion_urbanistica(
        self,
        ficha_id: str
    ) -> InformacionUrbanistica:
        """
        Obtiene información urbanística del Plan Regulador.
        
        Args:
            ficha_id: ID de la ficha
            
        Returns:
            InformacionUrbanistica
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        # Mock: información urbanística
        info_urb = InformacionUrbanistica(
            zona=ZonaUrbana.RESIDENCIAL_MIXTA,
            zona_secundaria="ZR2-B",
            uso_suelo_permitido=["vivienda", "comercio_menor", "equipamiento_menor"],
            uso_suelo_prohibido=["industria", "bodegaje", "talleres_molestos"],
            coeficiente_constructibilidad=2.8,
            coeficiente_ocupacion_suelo=0.6,
            densidad_maxima=800,
            altura_maxima_m=35.0,
            pisos_maximos=10,
            antejardín_minimo_m=3.0,
            rasante=70.0,
            adosamiento_permitido=False,
            distancia_medianeros_m=4.0,
            zona_inundable=False,
            zona_proteccion=False,
            zona_patrimonial=False,
            zona_riesgo=None,
            restricciones_adicionales=[],
            plan_regulador_vigente=f"PRC {ficha.ubicacion.comuna}",
            fecha_aprobacion_prc=date(2020, 6, 15)
        )
        
        ficha.informacion_urbanistica = info_urb
        
        if FuenteDatos.DOM not in ficha.fuentes_datos:
            ficha.fuentes_datos.append(FuenteDatos.DOM)
        
        ficha.fecha_actualizacion = datetime.now()
        ficha.completitud_pct = self._calcular_completitud(ficha)
        
        self._fichas_cache[ficha_id] = ficha
        
        return info_urb
    
    # =========================================================================
    # COMPARABLES Y MERCADO
    # =========================================================================
    
    async def buscar_comparables(
        self,
        ficha_id: str,
        radio_km: float = 1.0,
        max_resultados: int = 10,
        solo_venta: bool = True,
        antiguedad_max_dias: int = 180
    ) -> List[ComparableMercado]:
        """
        Busca propiedades comparables en el mercado.
        
        Args:
            ficha_id: ID de la ficha
            radio_km: Radio de búsqueda en km
            max_resultados: Máximo de resultados
            solo_venta: Solo propiedades en venta
            antiguedad_max_dias: Máxima antigüedad de publicación
            
        Returns:
            Lista de comparables
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        self.logger.info(f"Buscando comparables para {ficha.codigo} en radio {radio_km}km")
        
        # Mock: comparables
        comparables = []
        base_precio = 4500  # UF/m2 base
        
        for i in range(max_resultados):
            distancia = (i + 1) * radio_km * 100  # metros
            variacion = 1 + (0.1 - i * 0.02)  # Variación de precio
            superficie = ficha.superficies.construida_util_m2 * (0.8 + i * 0.05)
            
            comp = ComparableMercado(
                id=str(uuid.uuid4()),
                direccion=f"Calle Ejemplo {1000 + i*10}, {ficha.ubicacion.comuna}",
                comuna=ficha.ubicacion.comuna,
                distancia_m=distancia,
                tipo_propiedad=ficha.tipo_propiedad,
                superficie_util_m2=round(superficie, 1),
                dormitorios=ficha.dependencias.dormitorios + (i % 2 - 1),
                banos=ficha.dependencias.banos,
                estacionamientos=ficha.estacionamientos.cantidad,
                ano_construccion=ficha.caracteristicas.ano_construccion + (i - 5),
                precio_uf=round(base_precio * variacion * superficie, 0),
                precio_uf_m2=round(base_precio * variacion, 1),
                tipo_operacion="venta" if solo_venta else ["venta", "arriendo"][i % 2],
                fecha_publicacion=date.today() - timedelta(days=i*15),
                dias_publicado=i*15,
                fuente=[FuenteDatos.PORTAL_INMOBILIARIO, FuenteDatos.YAPO, FuenteDatos.TOCTOC][i % 3],
                url=f"https://example.com/propiedad/{i}",
                similitud_score=round(0.95 - i * 0.03, 2)
            )
            comparables.append(comp)
        
        ficha.comparables = comparables
        ficha.fecha_actualizacion = datetime.now()
        
        self._fichas_cache[ficha_id] = ficha
        
        return comparables
    
    async def calcular_indicadores_mercado(
        self,
        ficha_id: str
    ) -> IndicadoresMercado:
        """
        Calcula indicadores de mercado de la zona.
        
        Args:
            ficha_id: ID de la ficha
            
        Returns:
            IndicadoresMercado
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        # Usar comparables si existen
        if not ficha.comparables:
            await self.buscar_comparables(ficha_id)
        
        precios_m2 = [c.precio_uf_m2 for c in ficha.comparables]
        
        if precios_m2:
            indicadores = IndicadoresMercado(
                precio_m2_promedio_uf=round(statistics.mean(precios_m2), 1),
                precio_m2_mediana_uf=round(statistics.median(precios_m2), 1),
                precio_m2_min_uf=round(min(precios_m2), 1),
                precio_m2_max_uf=round(max(precios_m2), 1),
                desviacion_estandar=round(statistics.stdev(precios_m2), 1) if len(precios_m2) > 1 else 0,
                oferta_activa=len(ficha.comparables) * 8,  # Extrapolación
                transacciones_ultimo_ano=len(ficha.comparables) * 3,
                dias_promedio_venta=45,
                tasa_absorcion=0.12,
                tendencia_precios="estable",
                variacion_anual_pct=3.5,
                segmento_mercado="medio_alto",
                liquidez="media",
                fecha_actualizacion=date.today()
            )
        else:
            # Indicadores por defecto
            indicadores = IndicadoresMercado(
                precio_m2_promedio_uf=4500,
                precio_m2_mediana_uf=4400,
                precio_m2_min_uf=3800,
                precio_m2_max_uf=5200,
                desviacion_estandar=350,
                oferta_activa=85,
                transacciones_ultimo_ano=120,
                dias_promedio_venta=45,
                tasa_absorcion=0.12,
                tendencia_precios="estable",
                variacion_anual_pct=3.5,
                segmento_mercado="medio_alto",
                liquidez="media",
                fecha_actualizacion=date.today()
            )
        
        ficha.indicadores_mercado = indicadores
        ficha.fecha_actualizacion = datetime.now()
        
        self._fichas_cache[ficha_id] = ficha
        
        return indicadores
    
    async def estimar_valor_mercado(
        self,
        ficha_id: str,
        metodologia: str = "comparables"
    ) -> ValorMercado:
        """
        Estima el valor de mercado de la propiedad.
        
        Args:
            ficha_id: ID de la ficha
            metodologia: Metodología de valoración
            
        Returns:
            ValorMercado
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        # Asegurar que tenemos indicadores de mercado
        if not ficha.indicadores_mercado:
            await self.calcular_indicadores_mercado(ficha_id)
        
        # Calcular valor base
        precio_m2_base = ficha.indicadores_mercado.precio_m2_mediana_uf
        superficie = ficha.superficies.construida_util_m2
        
        # Aplicar ajustes
        ajustes = {}
        
        # Ajuste por estado de conservación
        ajuste_conservacion = {
            EstadoConservacion.NUEVO: 1.10,
            EstadoConservacion.EXCELENTE: 1.05,
            EstadoConservacion.BUENO: 1.00,
            EstadoConservacion.REGULAR: 0.92,
            EstadoConservacion.DETERIORADO: 0.80,
            EstadoConservacion.EN_RUINAS: 0.50,
            EstadoConservacion.EN_CONSTRUCCION: 0.70,
            EstadoConservacion.EN_REMODELACION: 0.85,
        }
        factor_conservacion = ajuste_conservacion.get(ficha.caracteristicas.estado_conservacion, 1.0)
        ajustes["conservacion"] = factor_conservacion - 1.0
        
        # Ajuste por antigüedad
        antiguedad = datetime.now().year - ficha.caracteristicas.ano_construccion
        factor_antiguedad = max(0.7, 1 - antiguedad * 0.005)
        ajustes["antiguedad"] = factor_antiguedad - 1.0
        
        # Ajuste por calidad de terminaciones
        ajuste_calidad = {
            CalidadTerminaciones.LUJO: 1.25,
            CalidadTerminaciones.ALTA: 1.12,
            CalidadTerminaciones.MEDIA_ALTA: 1.05,
            CalidadTerminaciones.MEDIA: 1.00,
            CalidadTerminaciones.ECONOMICA: 0.90,
            CalidadTerminaciones.SOCIAL: 0.80,
        }
        factor_calidad = ajuste_calidad.get(ficha.caracteristicas.calidad_terminaciones, 1.0)
        ajustes["terminaciones"] = factor_calidad - 1.0
        
        # Ajuste por estacionamientos
        factor_estacionamientos = 1.0 + ficha.estacionamientos.cantidad * 0.02
        ajustes["estacionamientos"] = factor_estacionamientos - 1.0
        
        # Calcular valor final
        factor_total = factor_conservacion * factor_antiguedad * factor_calidad * factor_estacionamientos
        valor_m2_ajustado = precio_m2_base * factor_total
        valor_total_uf = valor_m2_ajustado * superficie
        
        # Rangos de confianza (±10%)
        rango_inferior = valor_total_uf * 0.90
        rango_superior = valor_total_uf * 1.10
        
        uf_valor = 38500  # Mock UF
        
        valor_mercado = ValorMercado(
            valor_uf=round(valor_total_uf, 0),
            valor_uf_m2=round(valor_m2_ajustado, 1),
            valor_clp=int(valor_total_uf * uf_valor),
            fecha_estimacion=date.today(),
            metodologia=metodologia,
            fuente="DATAPOLIS",
            confianza=0.85,
            rango_inferior_uf=round(rango_inferior, 0),
            rango_superior_uf=round(rango_superior, 0),
            comparables_utilizados=len(ficha.comparables),
            ajustes_aplicados=ajustes
        )
        
        ficha.valor_mercado = valor_mercado
        ficha.fecha_actualizacion = datetime.now()
        
        self._fichas_cache[ficha_id] = ficha
        
        return valor_mercado
    
    # =========================================================================
    # BÚSQUEDA Y LISTADOS
    # =========================================================================
    
    async def buscar_fichas(
        self,
        query: Optional[str] = None,
        tipo_propiedad: Optional[TipoPropiedad] = None,
        comuna: Optional[str] = None,
        region: Optional[str] = None,
        precio_min_uf: Optional[float] = None,
        precio_max_uf: Optional[float] = None,
        superficie_min_m2: Optional[float] = None,
        superficie_max_m2: Optional[float] = None,
        dormitorios_min: Optional[int] = None,
        ano_construccion_min: Optional[int] = None,
        estado_conservacion: Optional[EstadoConservacion] = None,
        ordenar_por: str = "fecha_actualizacion",
        orden: str = "desc",
        limite: int = 20,
        offset: int = 0
    ) -> Tuple[List[FichaPropiedad], int]:
        """
        Búsqueda avanzada de fichas de propiedad.
        
        Returns:
            Tuple (fichas, total)
        """
        # Mock: generar resultados de ejemplo
        fichas = []
        comunas = ["Providencia", "Las Condes", "Ñuñoa", "Santiago", "Vitacura"]
        
        for i in range(min(limite, 15)):
            comunas_item = comuna or comunas[i % len(comunas)]
            
            ficha = self._generar_ficha_ejemplo(
                str(uuid.uuid4()),
                comunas_item,
                tipo_propiedad or TipoPropiedad.DEPARTAMENTO
            )
            fichas.append(ficha)
        
        return fichas, 150  # Mock total
    
    async def listar_por_propietario(
        self,
        propietario_rut: str,
        limite: int = 50
    ) -> List[FichaPropiedad]:
        """
        Lista fichas por propietario.
        
        Args:
            propietario_rut: RUT del propietario
            limite: Máximo resultados
            
        Returns:
            Lista de fichas
        """
        fichas = []
        
        for ficha in self._fichas_cache.values():
            if ficha.identificacion_sii.propietario_rut == propietario_rut:
                fichas.append(ficha)
                if len(fichas) >= limite:
                    break
        
        # Mock: agregar algunas
        if len(fichas) < 3:
            for i in range(3 - len(fichas)):
                ficha = self._generar_ficha_ejemplo(str(uuid.uuid4()))
                ficha.identificacion_sii.propietario_rut = propietario_rut
                fichas.append(ficha)
        
        return fichas
    
    # =========================================================================
    # REPORTES
    # =========================================================================
    
    async def generar_reporte_ficha(
        self,
        ficha_id: str,
        formato: str = "json",
        secciones: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera reporte completo de la ficha.
        
        Args:
            ficha_id: ID de la ficha
            formato: Formato de salida
            secciones: Secciones a incluir
            
        Returns:
            Reporte estructurado
        """
        ficha = await self.obtener_ficha(ficha_id)
        if not ficha:
            raise ValueError(f"Ficha {ficha_id} no encontrada")
        
        secciones = secciones or ["general", "ubicacion", "superficies", "caracteristicas", "legal", "valoracion"]
        
        reporte = {
            "ficha_id": ficha.id,
            "codigo": ficha.codigo,
            "generado_en": datetime.now().isoformat(),
            "formato": formato,
            "secciones": {}
        }
        
        if "general" in secciones:
            reporte["secciones"]["general"] = {
                "rol_sii": ficha.rol_sii,
                "tipo_propiedad": ficha.tipo_propiedad.value,
                "nombre": ficha.nombre,
                "descripcion": ficha.descripcion,
                "completitud_pct": ficha.completitud_pct,
                "fuentes_datos": [f.value for f in ficha.fuentes_datos],
                "fecha_actualizacion": ficha.fecha_actualizacion.isoformat()
            }
        
        if "ubicacion" in secciones:
            reporte["secciones"]["ubicacion"] = {
                "direccion": ficha.ubicacion.direccion_completa,
                "comuna": ficha.ubicacion.comuna,
                "region": ficha.ubicacion.region,
                "coordenadas": {
                    "lat": ficha.ubicacion.latitud,
                    "lon": ficha.ubicacion.longitud
                }
            }
        
        if "superficies" in secciones:
            reporte["secciones"]["superficies"] = {
                "terreno_m2": ficha.superficies.terreno_m2,
                "construida_total_m2": ficha.superficies.construida_total_m2,
                "construida_util_m2": ficha.superficies.construida_util_m2,
                "terraza_m2": ficha.superficies.terraza_m2,
                "bodega_m2": ficha.superficies.bodega_m2
            }
        
        if "caracteristicas" in secciones:
            reporte["secciones"]["caracteristicas"] = {
                "tipo_estructura": ficha.caracteristicas.tipo_estructura.value,
                "calidad_terminaciones": ficha.caracteristicas.calidad_terminaciones.value,
                "estado_conservacion": ficha.caracteristicas.estado_conservacion.value,
                "ano_construccion": ficha.caracteristicas.ano_construccion,
                "depreciacion_acumulada_pct": ficha.depreciacion_acumulada_pct,
                "vida_util_remanente_anos": ficha.vida_util_remanente_anos,
                "dormitorios": ficha.dependencias.dormitorios,
                "banos": ficha.dependencias.banos,
                "estacionamientos": ficha.estacionamientos.cantidad
            }
        
        if "legal" in secciones and ficha.informacion_legal:
            reporte["secciones"]["legal"] = {
                "estado": ficha.informacion_legal.estado.value,
                "inscripcion_dominio": ficha.informacion_legal.inscripcion_dominio,
                "conservador": ficha.informacion_legal.conservador,
                "gravamenes": len(ficha.informacion_legal.gravamenes),
                "litigios": ficha.informacion_legal.litigios_pendientes
            }
        
        if "valoracion" in secciones:
            valoracion = {}
            
            if ficha.avaluo_fiscal:
                valoracion["avaluo_fiscal"] = {
                    "total_uf": ficha.avaluo_fiscal.avaluo_total_uf,
                    "terreno_uf": ficha.avaluo_fiscal.avaluo_terreno_uf,
                    "construccion_uf": ficha.avaluo_fiscal.avaluo_construccion_uf,
                    "contribuciones_semestral": ficha.avaluo_fiscal.monto_contribuciones_semestral
                }
            
            if ficha.valor_mercado:
                valoracion["valor_mercado"] = {
                    "valor_uf": ficha.valor_mercado.valor_uf,
                    "valor_uf_m2": ficha.valor_mercado.valor_uf_m2,
                    "metodologia": ficha.valor_mercado.metodologia,
                    "confianza": ficha.valor_mercado.confianza,
                    "rango": [ficha.valor_mercado.rango_inferior_uf, ficha.valor_mercado.rango_superior_uf]
                }
            
            if ficha.indicadores_mercado:
                valoracion["indicadores_mercado"] = {
                    "precio_m2_promedio": ficha.indicadores_mercado.precio_m2_promedio_uf,
                    "tendencia": ficha.indicadores_mercado.tendencia_precios,
                    "variacion_anual_pct": ficha.indicadores_mercado.variacion_anual_pct
                }
            
            reporte["secciones"]["valoracion"] = valoracion
        
        return reporte
    
    # =========================================================================
    # UTILIDADES INTERNAS
    # =========================================================================
    
    def _extraer_numero(self, direccion: str) -> str:
        """Extrae el número de una dirección."""
        import re
        match = re.search(r'\d+', direccion)
        return match.group() if match else "S/N"
    
    def _crear_identificacion_sii(self, rol_sii: str, comuna: str) -> IdentificacionSII:
        """Crea identificación SII básica."""
        partes = rol_sii.replace("-", " ").split()
        manzana = int(partes[0]) if partes else 0
        predio = int(partes[1]) if len(partes) > 1 else 0
        
        return IdentificacionSII(
            rol_sii=rol_sii,
            rol_avaluo=rol_sii,
            rol_matriz=None,
            comuna_sii=13101,  # Mock código comuna
            manzana_sii=manzana,
            predio_sii=predio,
            serie=None,
            destino_sii=1,
            destino_descripcion="Habitacional",
            propietario_rut=None,
            propietario_nombre=None,
            fecha_ultimo_avaluo=None
        )
    
    def _crear_superficies_basicas(self, superficie_util: float) -> SuperficiesPropiedad:
        """Crea superficies básicas."""
        return SuperficiesPropiedad(
            terreno_m2=None,
            terreno_escritura_m2=None,
            terreno_municipal_m2=None,
            terreno_sii_m2=None,
            construida_total_m2=superficie_util * 1.15,
            construida_util_m2=superficie_util,
            construida_comun_m2=superficie_util * 0.15,
            construida_sii_m2=None,
            terraza_m2=None,
            jardin_m2=None,
            estacionamientos_m2=None,
            bodega_m2=None,
            piscina_m2=None,
            coeficiente_copropiedad=None,
            alicuota=None
        )
    
    def _crear_caracteristicas_basicas(self, ano_construccion: int) -> CaracteristicasConstructivas:
        """Crea características constructivas básicas."""
        return CaracteristicasConstructivas(
            tipo_estructura=TipoEstructura.HORMIGON_ARMADO,
            calidad_terminaciones=CalidadTerminaciones.MEDIA,
            estado_conservacion=EstadoConservacion.BUENO,
            ano_construccion=ano_construccion,
            ano_remodelacion=None,
            pisos_edificio=None,
            piso_unidad=None,
            orientacion=None,
            vista=None,
            iluminacion_natural=None,
            ventilacion=None,
            aislacion_termica=None,
            aislacion_acustica=None,
            eficiencia_energetica=None,
            certificacion_energetica_id=None
        )
    
    def _crear_dependencias_basicas(self, tipo: TipoPropiedad) -> Dependencias:
        """Crea dependencias básicas según tipo."""
        if tipo == TipoPropiedad.DEPARTAMENTO:
            return Dependencias(
                dormitorios=2, banos=2, banos_visita=0, living=1, comedor=0,
                living_comedor=True, cocina=1, cocina_americana=True, logia=1,
                escritorio=0, sala_estar=0, walk_in_closet=0, despensa=0,
                lavadero=0, quincho=0, sala_juegos=0, gimnasio_privado=0,
                sauna=0, dependencias_servicio=0, bano_servicio=0
            )
        elif tipo == TipoPropiedad.CASA:
            return Dependencias(
                dormitorios=3, banos=2, banos_visita=1, living=1, comedor=1,
                living_comedor=False, cocina=1, cocina_americana=False, logia=1,
                escritorio=0, sala_estar=1, walk_in_closet=0, despensa=1,
                lavadero=1, quincho=0, sala_juegos=0, gimnasio_privado=0,
                sauna=0, dependencias_servicio=1, bano_servicio=1
            )
        else:
            return Dependencias(
                dormitorios=0, banos=1, banos_visita=0, living=0, comedor=0,
                living_comedor=False, cocina=0, cocina_americana=False, logia=0,
                escritorio=0, sala_estar=0, walk_in_closet=0, despensa=0,
                lavadero=0, quincho=0, sala_juegos=0, gimnasio_privado=0,
                sauna=0, dependencias_servicio=0, bano_servicio=0
            )
    
    def _crear_amenities_basicos(self) -> Amenities:
        """Crea amenities básicos."""
        return Amenities(
            calefaccion=None, aire_acondicionado=False, chimenea=False,
            piso_radiante=False, agua_caliente="calefon", gas="natural",
            alarma=False, circuito_cerrado=False, portero_electrico=True,
            citofono=True, control_acceso=False, conserje_24h=False,
            ascensor=False, cantidad_ascensores=0, piscina_comun=False,
            gimnasio_comun=False, quincho_comun=False, sala_eventos=False,
            areas_verdes_comunes=False, juegos_infantiles=False,
            cancha_deportiva=False, sauna_comun=False, lavanderia_comun=False,
            bicicletero=False, salon_multiuso=False
        )
    
    def _calcular_depreciacion(self, ficha: FichaPropiedad) -> None:
        """Calcula depreciación del inmueble."""
        tipo_estructura = ficha.caracteristicas.tipo_estructura
        ano_construccion = ficha.caracteristicas.ano_construccion
        
        tasa_anual = DEPRECIACION_ANUAL.get(tipo_estructura, 0.01)
        vida_util = VIDA_UTIL.get(tipo_estructura, 50)
        
        antiguedad = datetime.now().year - ano_construccion
        depreciacion = min(0.80, antiguedad * tasa_anual)  # Max 80%
        
        ficha.depreciacion_acumulada_pct = round(depreciacion * 100, 1)
        ficha.vida_util_remanente_anos = max(0, vida_util - antiguedad)
        
        # Valor de reposición (si tiene avalúo)
        if ficha.avaluo_fiscal:
            valor_construccion = ficha.avaluo_fiscal.avaluo_construccion_uf
            ficha.valor_reposicion_uf = round(valor_construccion / (1 - depreciacion), 0)
    
    def _calcular_completitud(self, ficha: FichaPropiedad) -> float:
        """Calcula porcentaje de completitud de la ficha."""
        total_campos = 10
        campos_completos = 0
        
        if ficha.ubicacion.direccion_completa:
            campos_completos += 1
        if ficha.identificacion_sii.propietario_rut:
            campos_completos += 1
        if ficha.superficies.construida_util_m2 > 0:
            campos_completos += 1
        if ficha.caracteristicas.ano_construccion > 0:
            campos_completos += 1
        if ficha.informacion_legal:
            campos_completos += 2
        if ficha.informacion_urbanistica:
            campos_completos += 1
        if ficha.avaluo_fiscal:
            campos_completos += 1
        if ficha.valor_mercado:
            campos_completos += 1
        if len(ficha.comparables) > 0:
            campos_completos += 1
        
        return round((campos_completos / total_campos) * 100, 1)
    
    def _generar_ficha_ejemplo(
        self,
        ficha_id: str,
        comuna: str = "Providencia",
        tipo: TipoPropiedad = TipoPropiedad.DEPARTAMENTO
    ) -> FichaPropiedad:
        """Genera ficha de ejemplo para desarrollo."""
        ahora = datetime.now()
        
        ubicacion = UbicacionPropiedad(
            direccion_completa=f"Av. Providencia 1234, Depto 501, {comuna}",
            numero="1234",
            departamento="501",
            piso=5,
            comuna=comuna,
            region="Metropolitana",
            codigo_postal="7500000",
            latitud=-33.4289,
            longitud=-70.6093,
            manzana=None,
            sitio=None,
            unidad_vecinal=None,
            distrito_censal=None,
            zona_censal=None
        )
        
        identificacion = IdentificacionSII(
            rol_sii="123-456",
            rol_avaluo="123-456",
            rol_matriz=None,
            comuna_sii=13123,
            manzana_sii=123,
            predio_sii=456,
            serie=None,
            destino_sii=1,
            destino_descripcion="Habitacional",
            propietario_rut="12.345.678-9",
            propietario_nombre="Juan Pérez González",
            fecha_ultimo_avaluo=date.today() - timedelta(days=180)
        )
        
        superficies = SuperficiesPropiedad(
            terreno_m2=None,
            terreno_escritura_m2=None,
            terreno_municipal_m2=None,
            terreno_sii_m2=None,
            construida_total_m2=95.0,
            construida_util_m2=82.0,
            construida_comun_m2=13.0,
            construida_sii_m2=95.0,
            terraza_m2=8.0,
            jardin_m2=None,
            estacionamientos_m2=12.5,
            bodega_m2=4.0,
            piscina_m2=None,
            coeficiente_copropiedad=0.0125,
            alicuota=1.25
        )
        
        caracteristicas = CaracteristicasConstructivas(
            tipo_estructura=TipoEstructura.HORMIGON_ARMADO,
            calidad_terminaciones=CalidadTerminaciones.MEDIA_ALTA,
            estado_conservacion=EstadoConservacion.BUENO,
            ano_construccion=2015,
            ano_remodelacion=None,
            pisos_edificio=15,
            piso_unidad=5,
            orientacion="NO",
            vista="Cordillera",
            iluminacion_natural="Buena",
            ventilacion="Buena",
            aislacion_termica="Media",
            aislacion_acustica="Media",
            eficiencia_energetica="D",
            certificacion_energetica_id=None
        )
        
        dependencias = Dependencias(
            dormitorios=3, banos=2, banos_visita=1, living=1, comedor=0,
            living_comedor=True, cocina=1, cocina_americana=True, logia=1,
            escritorio=1, sala_estar=0, walk_in_closet=1, despensa=0,
            lavadero=0, quincho=0, sala_juegos=0, gimnasio_privado=0,
            sauna=0, dependencias_servicio=0, bano_servicio=0
        )
        
        estacionamientos = Estacionamientos(
            cantidad=1,
            tipo="subterraneo",
            ubicacion="Subterráneo nivel -2",
            numeros=["E-123"],
            superficie_total_m2=12.5,
            tiene_bodega=True,
            bodega_m2=4.0,
            bodega_numero="B-45"
        )
        
        amenities = Amenities(
            calefaccion="individual",
            aire_acondicionado=True,
            chimenea=False,
            piso_radiante=False,
            agua_caliente="termo",
            gas="natural",
            alarma=True,
            circuito_cerrado=True,
            portero_electrico=True,
            citofono=True,
            control_acceso=True,
            conserje_24h=True,
            ascensor=True,
            cantidad_ascensores=3,
            piscina_comun=True,
            gimnasio_comun=True,
            quincho_comun=True,
            sala_eventos=True,
            areas_verdes_comunes=True,
            juegos_infantiles=True,
            cancha_deportiva=False,
            sauna_comun=True,
            lavanderia_comun=False,
            bicicletero=True,
            salon_multiuso=True
        )
        
        return FichaPropiedad(
            id=ficha_id,
            codigo=f"FP-2026-{str(uuid.uuid4())[:6].upper()}",
            rol_sii="123-456",
            tipo_propiedad=tipo,
            nombre=f"{tipo.value.replace('_', ' ').title()} {comuna}",
            descripcion="Departamento en excelente ubicación",
            ubicacion=ubicacion,
            identificacion_sii=identificacion,
            superficies=superficies,
            caracteristicas=caracteristicas,
            dependencias=dependencias,
            estacionamientos=estacionamientos,
            amenities=amenities,
            informacion_urbanistica=None,
            informacion_legal=None,
            historial_transacciones=[],
            avaluo_fiscal=None,
            valor_mercado=None,
            comparables=[],
            indicadores_mercado=None,
            expediente_id=None,
            fuentes_datos=[FuenteDatos.USUARIO],
            fecha_creacion=ahora - timedelta(days=30),
            fecha_actualizacion=ahora,
            actualizado_por="sistema",
            version=1,
            completitud_pct=35.0,
            depreciacion_acumulada_pct=7.2,
            vida_util_remanente_anos=71,
            valor_reposicion_uf=0
        )


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_servicio_ficha: Optional[ServicioFichaPropiedad] = None


def get_servicio_ficha() -> ServicioFichaPropiedad:
    """Obtiene instancia singleton del servicio."""
    global _servicio_ficha
    if _servicio_ficha is None:
        _servicio_ficha = ServicioFichaPropiedad()
    return _servicio_ficha


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "TipoPropiedad",
    "EstadoConservacion",
    "TipoEstructura",
    "CalidadTerminaciones",
    "ZonaUrbana",
    "TipoTransaccion",
    "EstadoLegal",
    "FuenteDatos",
    # Data classes
    "UbicacionPropiedad",
    "IdentificacionSII",
    "SuperficiesPropiedad",
    "CaracteristicasConstructivas",
    "Dependencias",
    "Estacionamientos",
    "Amenities",
    "InformacionUrbanistica",
    "Gravamen",
    "InformacionLegal",
    "Transaccion",
    "AvaluoFiscal",
    "ValorMercado",
    "ComparableMercado",
    "IndicadoresMercado",
    "FichaPropiedad",
    # Constantes
    "DEPRECIACION_ANUAL",
    "VIDA_UTIL",
    # Servicio
    "ServicioFichaPropiedad",
    "get_servicio_ficha",
]
