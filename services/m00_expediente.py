"""
DATAPOLIS v3.0 - M00 Expediente Universal
==========================================
Módulo base que centraliza toda la información de propiedades inmobiliarias.
El Expediente Universal es el núcleo documental de DATAPOLIS.

Funcionalidades:
- Gestión documental centralizada
- Versionamiento de documentos
- Workflows de aprobación
- Indexación y búsqueda full-text
- Integración con todos los módulos
- Trazabilidad completa de cambios
- Cumplimiento normativo (Ley 21.442)

Fuentes normativas:
- Ley 21.442 sobre Copropiedad Inmobiliaria
- Ley 21.713 sobre Tributación Digital
- NCh 2728 Gestión de Documentos
- ISO 15489 Records Management

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: 2026-02
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import hashlib
import uuid
import json
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================

class TipoExpediente(str, Enum):
    """Tipos de expediente según uso"""
    PROPIEDAD_INDIVIDUAL = "propiedad_individual"
    UNIDAD_COPROPIEDAD = "unidad_copropiedad"
    CONDOMINIO = "condominio"
    TERRENO = "terreno"
    PROYECTO_INMOBILIARIO = "proyecto_inmobiliario"
    PARCELA_AGRICOLA = "parcela_agricola"
    LOCAL_COMERCIAL = "local_comercial"
    OFICINA = "oficina"
    BODEGA = "bodega"
    ESTACIONAMIENTO = "estacionamiento"


class EstadoExpediente(str, Enum):
    """Estados del ciclo de vida del expediente"""
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    PENDIENTE_DOCUMENTOS = "pendiente_documentos"
    COMPLETO = "completo"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    ARCHIVADO = "archivado"
    CERRADO = "cerrado"


class TipoDocumento(str, Enum):
    """Categorías de documentos"""
    # Legales
    ESCRITURA_PROPIEDAD = "escritura_propiedad"
    CERTIFICADO_DOMINIO = "certificado_dominio"
    CERTIFICADO_GRAVAMENES = "certificado_gravamenes"
    CERTIFICADO_LITIGIOS = "certificado_litigios"
    PODER_NOTARIAL = "poder_notarial"
    CONTRATO_COMPRAVENTA = "contrato_compraventa"
    CONTRATO_ARRIENDO = "contrato_arriendo"
    PROMESA_COMPRAVENTA = "promesa_compraventa"
    
    # Técnicos
    PLANO_ARQUITECTURA = "plano_arquitectura"
    PLANO_ESTRUCTURA = "plano_estructura"
    PLANO_INSTALACIONES = "plano_instalaciones"
    CERTIFICADO_RECEPCION = "certificado_recepcion"
    PERMISO_EDIFICACION = "permiso_edificacion"
    INFORME_TASACION = "informe_tasacion"
    CERTIFICADO_EFICIENCIA = "certificado_eficiencia"
    
    # Tributarios
    AVALUO_FISCAL = "avaluo_fiscal"
    CERTIFICADO_DEUDA_CONTRIBUCIONES = "certificado_deuda_contribuciones"
    DECLARACION_RENTA = "declaracion_renta"
    BOLETA_CONTRIBUCIONES = "boleta_contribuciones"
    
    # Copropiedad
    REGLAMENTO_COPROPIEDAD = "reglamento_copropiedad"
    ACTA_ASAMBLEA = "acta_asamblea"
    PRESUPUESTO_GASTOS_COMUNES = "presupuesto_gastos_comunes"
    FONDO_RESERVA = "fondo_reserva"
    
    # Servicios
    CERTIFICADO_AGUA = "certificado_agua"
    CERTIFICADO_LUZ = "certificado_luz"
    CERTIFICADO_GAS = "certificado_gas"
    
    # Otros
    FOTOGRAFIA = "fotografia"
    VIDEO = "video"
    INFORME_INSPECCION = "informe_inspeccion"
    CORRESPONDENCIA = "correspondencia"
    OTRO = "otro"


class EstadoDocumento(str, Enum):
    """Estados de un documento"""
    PENDIENTE = "pendiente"
    CARGADO = "cargado"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    VENCIDO = "vencido"
    REEMPLAZADO = "reemplazado"


class NivelConfidencialidad(str, Enum):
    """Niveles de acceso a documentos"""
    PUBLICO = "publico"
    INTERNO = "interno"
    CONFIDENCIAL = "confidencial"
    RESTRINGIDO = "restringido"


class TipoEvento(str, Enum):
    """Tipos de eventos en el expediente"""
    CREACION = "creacion"
    MODIFICACION = "modificacion"
    DOCUMENTO_AGREGADO = "documento_agregado"
    DOCUMENTO_ELIMINADO = "documento_eliminado"
    CAMBIO_ESTADO = "cambio_estado"
    COMENTARIO = "comentario"
    ASIGNACION = "asignacion"
    ALERTA = "alerta"
    WORKFLOW = "workflow"
    INTEGRACION = "integracion"


class TipoWorkflow(str, Enum):
    """Tipos de workflow de aprobación"""
    REVISION_SIMPLE = "revision_simple"
    APROBACION_LEGAL = "aprobacion_legal"
    APROBACION_TECNICA = "aprobacion_tecnica"
    APROBACION_MULTIPLE = "aprobacion_multiple"
    VALIDACION_EXTERNA = "validacion_externa"


# Requisitos documentales por tipo de expediente
REQUISITOS_DOCUMENTALES: Dict[TipoExpediente, List[TipoDocumento]] = {
    TipoExpediente.PROPIEDAD_INDIVIDUAL: [
        TipoDocumento.ESCRITURA_PROPIEDAD,
        TipoDocumento.CERTIFICADO_DOMINIO,
        TipoDocumento.CERTIFICADO_GRAVAMENES,
        TipoDocumento.AVALUO_FISCAL,
    ],
    TipoExpediente.UNIDAD_COPROPIEDAD: [
        TipoDocumento.ESCRITURA_PROPIEDAD,
        TipoDocumento.CERTIFICADO_DOMINIO,
        TipoDocumento.CERTIFICADO_GRAVAMENES,
        TipoDocumento.REGLAMENTO_COPROPIEDAD,
        TipoDocumento.AVALUO_FISCAL,
    ],
    TipoExpediente.CONDOMINIO: [
        TipoDocumento.ESCRITURA_PROPIEDAD,
        TipoDocumento.REGLAMENTO_COPROPIEDAD,
        TipoDocumento.CERTIFICADO_RECEPCION,
        TipoDocumento.PLANO_ARQUITECTURA,
        TipoDocumento.AVALUO_FISCAL,
    ],
    TipoExpediente.TERRENO: [
        TipoDocumento.ESCRITURA_PROPIEDAD,
        TipoDocumento.CERTIFICADO_DOMINIO,
        TipoDocumento.CERTIFICADO_GRAVAMENES,
        TipoDocumento.CERTIFICADO_LITIGIOS,
        TipoDocumento.AVALUO_FISCAL,
    ],
    TipoExpediente.PROYECTO_INMOBILIARIO: [
        TipoDocumento.ESCRITURA_PROPIEDAD,
        TipoDocumento.PERMISO_EDIFICACION,
        TipoDocumento.PLANO_ARQUITECTURA,
        TipoDocumento.PLANO_ESTRUCTURA,
        TipoDocumento.CERTIFICADO_DOMINIO,
    ],
}

# Vigencia de documentos (días)
VIGENCIA_DOCUMENTOS: Dict[TipoDocumento, int] = {
    TipoDocumento.CERTIFICADO_DOMINIO: 30,
    TipoDocumento.CERTIFICADO_GRAVAMENES: 30,
    TipoDocumento.CERTIFICADO_LITIGIOS: 30,
    TipoDocumento.CERTIFICADO_DEUDA_CONTRIBUCIONES: 30,
    TipoDocumento.CERTIFICADO_AGUA: 60,
    TipoDocumento.CERTIFICADO_LUZ: 60,
    TipoDocumento.CERTIFICADO_GAS: 60,
    TipoDocumento.AVALUO_FISCAL: 365,
    TipoDocumento.INFORME_TASACION: 180,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Documento:
    """Representación de un documento en el expediente"""
    id: str
    tipo: TipoDocumento
    nombre: str
    descripcion: Optional[str]
    archivo_url: str
    archivo_hash: str
    tamano_bytes: int
    mime_type: str
    estado: EstadoDocumento
    confidencialidad: NivelConfidencialidad
    version: int
    version_anterior_id: Optional[str]
    fecha_emision: Optional[date]
    fecha_vencimiento: Optional[date]
    emisor: Optional[str]
    numero_documento: Optional[str]
    metadata: Dict[str, Any]
    creado_por: str
    creado_en: datetime
    modificado_en: datetime
    aprobado_por: Optional[str] = None
    aprobado_en: Optional[datetime] = None
    comentarios: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def esta_vigente(self) -> bool:
        """Verifica si el documento está vigente"""
        if self.fecha_vencimiento is None:
            return True
        return self.fecha_vencimiento >= date.today()
    
    def dias_para_vencer(self) -> Optional[int]:
        """Días restantes de vigencia"""
        if self.fecha_vencimiento is None:
            return None
        return (self.fecha_vencimiento - date.today()).days


@dataclass
class EventoExpediente:
    """Registro de eventos/cambios en el expediente"""
    id: str
    tipo: TipoEvento
    descripcion: str
    detalle: Dict[str, Any]
    usuario_id: str
    usuario_nombre: str
    timestamp: datetime
    ip_address: Optional[str] = None
    documento_id: Optional[str] = None


@dataclass
class WorkflowAprobacion:
    """Workflow de aprobación de documentos"""
    id: str
    tipo: TipoWorkflow
    documento_id: str
    estado: str  # pendiente, en_progreso, aprobado, rechazado
    etapas: List[Dict[str, Any]]
    etapa_actual: int
    creado_por: str
    creado_en: datetime
    completado_en: Optional[datetime] = None
    resultado: Optional[str] = None
    comentarios: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AlertaExpediente:
    """Alerta asociada al expediente"""
    id: str
    tipo: str  # vencimiento, pendiente, urgente, informativa
    titulo: str
    mensaje: str
    severidad: str  # baja, media, alta, critica
    fecha_generacion: datetime
    fecha_vencimiento: Optional[datetime]
    documento_id: Optional[str]
    leida: bool = False
    resuelta: bool = False
    acciones: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PropiedadBasica:
    """Información básica de la propiedad asociada"""
    rol_sii: str
    direccion: str
    comuna: str
    region: str
    tipo_propiedad: str
    superficie_terreno_m2: Optional[float]
    superficie_construida_m2: Optional[float]
    ano_construccion: Optional[int]
    coordenadas: Optional[Dict[str, float]]  # lat, lon
    avaluo_fiscal_uf: Optional[float]


@dataclass
class Expediente:
    """Expediente Universal completo"""
    id: str
    codigo: str  # EXP-2026-000001
    tipo: TipoExpediente
    estado: EstadoExpediente
    titulo: str
    descripcion: Optional[str]
    propiedad: PropiedadBasica
    propietario_id: str
    propietario_nombre: str
    administrador_id: Optional[str]
    documentos: List[Documento]
    eventos: List[EventoExpediente]
    alertas: List[AlertaExpediente]
    workflows: List[WorkflowAprobacion]
    metadata: Dict[str, Any]
    tags: List[str]
    creado_por: str
    creado_en: datetime
    modificado_en: datetime
    completitud_pct: float = 0.0
    documentos_pendientes: List[TipoDocumento] = field(default_factory=list)
    documentos_vencidos: List[str] = field(default_factory=list)
    modulos_vinculados: List[str] = field(default_factory=list)


@dataclass
class BusquedaResultado:
    """Resultado de búsqueda en expedientes"""
    expediente_id: str
    codigo: str
    titulo: str
    tipo: TipoExpediente
    estado: EstadoExpediente
    rol_sii: str
    direccion: str
    comuna: str
    completitud_pct: float
    alertas_activas: int
    relevancia_score: float
    fragmentos_relevantes: List[Dict[str, Any]]


@dataclass
class EstadisticasExpedientes:
    """Estadísticas agregadas de expedientes"""
    total_expedientes: int
    por_tipo: Dict[str, int]
    por_estado: Dict[str, int]
    completitud_promedio: float
    documentos_totales: int
    documentos_pendientes: int
    documentos_vencidos: int
    alertas_activas: int
    expedientes_activos_mes: int
    tendencia_creacion: List[Dict[str, Any]]


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class ServicioExpedienteUniversal:
    """
    Servicio para gestión del Expediente Universal.
    Centraliza toda la información documental de propiedades.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ServicioExpedienteUniversal")
        self._expedientes_cache: Dict[str, Expediente] = {}
        self._contador_expedientes = 0
    
    # =========================================================================
    # GESTIÓN DE EXPEDIENTES
    # =========================================================================
    
    async def crear_expediente(
        self,
        tipo: TipoExpediente,
        titulo: str,
        propiedad: PropiedadBasica,
        propietario_id: str,
        propietario_nombre: str,
        descripcion: Optional[str] = None,
        creado_por: str = "sistema",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Expediente:
        """
        Crea un nuevo expediente universal.
        
        Args:
            tipo: Tipo de expediente
            titulo: Título descriptivo
            propiedad: Datos básicos de la propiedad
            propietario_id: ID del propietario
            propietario_nombre: Nombre del propietario
            descripcion: Descripción opcional
            creado_por: Usuario que crea
            metadata: Metadata adicional
            
        Returns:
            Expediente creado
        """
        self.logger.info(f"Creando expediente tipo {tipo.value} para {propiedad.rol_sii}")
        
        # Generar código único
        self._contador_expedientes += 1
        codigo = f"EXP-{datetime.now().year}-{self._contador_expedientes:06d}"
        
        # Determinar documentos requeridos
        docs_requeridos = REQUISITOS_DOCUMENTALES.get(tipo, [])
        
        ahora = datetime.now()
        
        expediente = Expediente(
            id=str(uuid.uuid4()),
            codigo=codigo,
            tipo=tipo,
            estado=EstadoExpediente.BORRADOR,
            titulo=titulo,
            descripcion=descripcion,
            propiedad=propiedad,
            propietario_id=propietario_id,
            propietario_nombre=propietario_nombre,
            administrador_id=None,
            documentos=[],
            eventos=[],
            alertas=[],
            workflows=[],
            metadata=metadata or {},
            tags=[],
            creado_por=creado_por,
            creado_en=ahora,
            modificado_en=ahora,
            completitud_pct=0.0,
            documentos_pendientes=docs_requeridos.copy(),
            documentos_vencidos=[],
            modulos_vinculados=[]
        )
        
        # Registrar evento de creación
        evento = EventoExpediente(
            id=str(uuid.uuid4()),
            tipo=TipoEvento.CREACION,
            descripcion=f"Expediente {codigo} creado",
            detalle={
                "tipo": tipo.value,
                "propiedad_rol": propiedad.rol_sii,
                "propietario": propietario_nombre
            },
            usuario_id=creado_por,
            usuario_nombre=creado_por,
            timestamp=ahora
        )
        expediente.eventos.append(evento)
        
        # Generar alertas iniciales por documentos pendientes
        for tipo_doc in docs_requeridos:
            alerta = AlertaExpediente(
                id=str(uuid.uuid4()),
                tipo="pendiente",
                titulo=f"Documento pendiente: {tipo_doc.value}",
                mensaje=f"Se requiere cargar el documento {tipo_doc.value}",
                severidad="media",
                fecha_generacion=ahora,
                fecha_vencimiento=ahora + timedelta(days=30),
                documento_id=None,
                acciones=[
                    {"tipo": "cargar_documento", "label": "Cargar documento"}
                ]
            )
            expediente.alertas.append(alerta)
        
        # Guardar en caché
        self._expedientes_cache[expediente.id] = expediente
        
        self.logger.info(f"Expediente {codigo} creado exitosamente")
        return expediente
    
    async def obtener_expediente(
        self,
        expediente_id: str,
        incluir_documentos: bool = True,
        incluir_eventos: bool = True,
        incluir_alertas: bool = True
    ) -> Optional[Expediente]:
        """
        Obtiene un expediente por ID.
        
        Args:
            expediente_id: ID del expediente
            incluir_documentos: Incluir lista de documentos
            incluir_eventos: Incluir historial de eventos
            incluir_alertas: Incluir alertas activas
            
        Returns:
            Expediente o None si no existe
        """
        if expediente_id in self._expedientes_cache:
            exp = self._expedientes_cache[expediente_id]
            # Filtrar según parámetros
            if not incluir_documentos:
                exp = Expediente(**{**exp.__dict__, "documentos": []})
            if not incluir_eventos:
                exp = Expediente(**{**exp.__dict__, "eventos": []})
            if not incluir_alertas:
                exp = Expediente(**{**exp.__dict__, "alertas": []})
            return exp
        
        # Mock: generar expediente de ejemplo
        return self._generar_expediente_ejemplo(expediente_id)
    
    async def actualizar_expediente(
        self,
        expediente_id: str,
        actualizaciones: Dict[str, Any],
        usuario_id: str
    ) -> Expediente:
        """
        Actualiza campos de un expediente.
        
        Args:
            expediente_id: ID del expediente
            actualizaciones: Campos a actualizar
            usuario_id: Usuario que actualiza
            
        Returns:
            Expediente actualizado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        ahora = datetime.now()
        cambios = []
        
        for campo, valor in actualizaciones.items():
            if hasattr(expediente, campo):
                valor_anterior = getattr(expediente, campo)
                setattr(expediente, campo, valor)
                cambios.append({
                    "campo": campo,
                    "valor_anterior": str(valor_anterior),
                    "valor_nuevo": str(valor)
                })
        
        expediente.modificado_en = ahora
        
        # Registrar evento
        evento = EventoExpediente(
            id=str(uuid.uuid4()),
            tipo=TipoEvento.MODIFICACION,
            descripcion=f"Expediente actualizado: {len(cambios)} campos",
            detalle={"cambios": cambios},
            usuario_id=usuario_id,
            usuario_nombre=usuario_id,
            timestamp=ahora
        )
        expediente.eventos.append(evento)
        
        # Actualizar caché
        self._expedientes_cache[expediente_id] = expediente
        
        return expediente
    
    async def cambiar_estado(
        self,
        expediente_id: str,
        nuevo_estado: EstadoExpediente,
        usuario_id: str,
        comentario: Optional[str] = None
    ) -> Expediente:
        """
        Cambia el estado de un expediente.
        
        Args:
            expediente_id: ID del expediente
            nuevo_estado: Nuevo estado
            usuario_id: Usuario que cambia
            comentario: Comentario opcional
            
        Returns:
            Expediente con nuevo estado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        estado_anterior = expediente.estado
        expediente.estado = nuevo_estado
        expediente.modificado_en = datetime.now()
        
        # Validar transición de estado
        transiciones_validas = {
            EstadoExpediente.BORRADOR: [EstadoExpediente.EN_REVISION, EstadoExpediente.PENDIENTE_DOCUMENTOS],
            EstadoExpediente.EN_REVISION: [EstadoExpediente.COMPLETO, EstadoExpediente.PENDIENTE_DOCUMENTOS, EstadoExpediente.BORRADOR],
            EstadoExpediente.PENDIENTE_DOCUMENTOS: [EstadoExpediente.EN_REVISION, EstadoExpediente.COMPLETO],
            EstadoExpediente.COMPLETO: [EstadoExpediente.ACTIVO, EstadoExpediente.EN_REVISION],
            EstadoExpediente.ACTIVO: [EstadoExpediente.SUSPENDIDO, EstadoExpediente.ARCHIVADO, EstadoExpediente.CERRADO],
            EstadoExpediente.SUSPENDIDO: [EstadoExpediente.ACTIVO, EstadoExpediente.CERRADO],
            EstadoExpediente.ARCHIVADO: [EstadoExpediente.ACTIVO],
            EstadoExpediente.CERRADO: [],
        }
        
        if nuevo_estado not in transiciones_validas.get(estado_anterior, []):
            self.logger.warning(f"Transición de estado forzada: {estado_anterior} -> {nuevo_estado}")
        
        # Registrar evento
        evento = EventoExpediente(
            id=str(uuid.uuid4()),
            tipo=TipoEvento.CAMBIO_ESTADO,
            descripcion=f"Estado cambiado: {estado_anterior.value} → {nuevo_estado.value}",
            detalle={
                "estado_anterior": estado_anterior.value,
                "estado_nuevo": nuevo_estado.value,
                "comentario": comentario
            },
            usuario_id=usuario_id,
            usuario_nombre=usuario_id,
            timestamp=datetime.now()
        )
        expediente.eventos.append(evento)
        
        self._expedientes_cache[expediente_id] = expediente
        
        return expediente
    
    async def eliminar_expediente(
        self,
        expediente_id: str,
        usuario_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Elimina o archiva un expediente.
        
        Args:
            expediente_id: ID del expediente
            usuario_id: Usuario que elimina
            hard_delete: Si es True, elimina permanentemente
            
        Returns:
            True si se eliminó/archivó correctamente
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return False
        
        if hard_delete:
            # Eliminar permanentemente
            if expediente_id in self._expedientes_cache:
                del self._expedientes_cache[expediente_id]
            self.logger.warning(f"Expediente {expediente_id} eliminado permanentemente por {usuario_id}")
        else:
            # Soft delete: cambiar a archivado
            await self.cambiar_estado(
                expediente_id,
                EstadoExpediente.ARCHIVADO,
                usuario_id,
                "Expediente archivado por solicitud de usuario"
            )
        
        return True
    
    # =========================================================================
    # GESTIÓN DE DOCUMENTOS
    # =========================================================================
    
    async def agregar_documento(
        self,
        expediente_id: str,
        tipo: TipoDocumento,
        nombre: str,
        archivo_url: str,
        archivo_contenido: bytes,
        mime_type: str,
        usuario_id: str,
        descripcion: Optional[str] = None,
        fecha_emision: Optional[date] = None,
        numero_documento: Optional[str] = None,
        emisor: Optional[str] = None,
        confidencialidad: NivelConfidencialidad = NivelConfidencialidad.INTERNO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Documento:
        """
        Agrega un documento al expediente.
        
        Args:
            expediente_id: ID del expediente
            tipo: Tipo de documento
            nombre: Nombre del archivo
            archivo_url: URL de almacenamiento
            archivo_contenido: Contenido binario (para hash)
            mime_type: Tipo MIME
            usuario_id: Usuario que carga
            descripcion: Descripción opcional
            fecha_emision: Fecha de emisión
            numero_documento: Número identificador
            emisor: Entidad emisora
            confidencialidad: Nivel de acceso
            metadata: Metadata adicional
            
        Returns:
            Documento creado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        ahora = datetime.now()
        
        # Calcular hash del contenido
        archivo_hash = hashlib.sha256(archivo_contenido).hexdigest()
        
        # Determinar fecha de vencimiento según tipo
        fecha_vencimiento = None
        if tipo in VIGENCIA_DOCUMENTOS:
            dias_vigencia = VIGENCIA_DOCUMENTOS[tipo]
            fecha_base = fecha_emision or date.today()
            fecha_vencimiento = fecha_base + timedelta(days=dias_vigencia)
        
        # Buscar versión anterior del mismo tipo
        version = 1
        version_anterior_id = None
        for doc in expediente.documentos:
            if doc.tipo == tipo and doc.estado != EstadoDocumento.REEMPLAZADO:
                version = doc.version + 1
                version_anterior_id = doc.id
                doc.estado = EstadoDocumento.REEMPLAZADO
                break
        
        documento = Documento(
            id=str(uuid.uuid4()),
            tipo=tipo,
            nombre=nombre,
            descripcion=descripcion,
            archivo_url=archivo_url,
            archivo_hash=archivo_hash,
            tamano_bytes=len(archivo_contenido),
            mime_type=mime_type,
            estado=EstadoDocumento.CARGADO,
            confidencialidad=confidencialidad,
            version=version,
            version_anterior_id=version_anterior_id,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            emisor=emisor,
            numero_documento=numero_documento,
            metadata=metadata or {},
            creado_por=usuario_id,
            creado_en=ahora,
            modificado_en=ahora,
            tags=[]
        )
        
        expediente.documentos.append(documento)
        
        # Actualizar documentos pendientes
        if tipo in expediente.documentos_pendientes:
            expediente.documentos_pendientes.remove(tipo)
        
        # Recalcular completitud
        await self._recalcular_completitud(expediente)
        
        # Registrar evento
        evento = EventoExpediente(
            id=str(uuid.uuid4()),
            tipo=TipoEvento.DOCUMENTO_AGREGADO,
            descripcion=f"Documento agregado: {nombre}",
            detalle={
                "tipo_documento": tipo.value,
                "version": version,
                "tamano_bytes": len(archivo_contenido),
                "hash": archivo_hash[:16] + "..."
            },
            usuario_id=usuario_id,
            usuario_nombre=usuario_id,
            timestamp=ahora,
            documento_id=documento.id
        )
        expediente.eventos.append(evento)
        
        # Resolver alerta de documento pendiente
        for alerta in expediente.alertas:
            if alerta.tipo == "pendiente" and tipo.value in alerta.titulo:
                alerta.resuelta = True
        
        expediente.modificado_en = ahora
        self._expedientes_cache[expediente_id] = expediente
        
        self.logger.info(f"Documento {tipo.value} v{version} agregado a expediente {expediente.codigo}")
        
        return documento
    
    async def actualizar_documento(
        self,
        expediente_id: str,
        documento_id: str,
        actualizaciones: Dict[str, Any],
        usuario_id: str
    ) -> Documento:
        """
        Actualiza metadatos de un documento.
        
        Args:
            expediente_id: ID del expediente
            documento_id: ID del documento
            actualizaciones: Campos a actualizar
            usuario_id: Usuario que actualiza
            
        Returns:
            Documento actualizado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        documento = None
        for doc in expediente.documentos:
            if doc.id == documento_id:
                documento = doc
                break
        
        if not documento:
            raise ValueError(f"Documento {documento_id} no encontrado")
        
        for campo, valor in actualizaciones.items():
            if hasattr(documento, campo) and campo not in ['id', 'archivo_hash', 'creado_en', 'creado_por']:
                setattr(documento, campo, valor)
        
        documento.modificado_en = datetime.now()
        
        self._expedientes_cache[expediente_id] = expediente
        
        return documento
    
    async def aprobar_documento(
        self,
        expediente_id: str,
        documento_id: str,
        usuario_id: str,
        comentario: Optional[str] = None
    ) -> Documento:
        """
        Aprueba un documento.
        
        Args:
            expediente_id: ID del expediente
            documento_id: ID del documento
            usuario_id: Usuario que aprueba
            comentario: Comentario opcional
            
        Returns:
            Documento aprobado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        documento = None
        for doc in expediente.documentos:
            if doc.id == documento_id:
                documento = doc
                break
        
        if not documento:
            raise ValueError(f"Documento {documento_id} no encontrado")
        
        ahora = datetime.now()
        documento.estado = EstadoDocumento.APROBADO
        documento.aprobado_por = usuario_id
        documento.aprobado_en = ahora
        documento.modificado_en = ahora
        
        if comentario:
            documento.comentarios.append({
                "usuario_id": usuario_id,
                "texto": comentario,
                "tipo": "aprobacion",
                "timestamp": ahora.isoformat()
            })
        
        self._expedientes_cache[expediente_id] = expediente
        
        return documento
    
    async def rechazar_documento(
        self,
        expediente_id: str,
        documento_id: str,
        usuario_id: str,
        motivo: str
    ) -> Documento:
        """
        Rechaza un documento.
        
        Args:
            expediente_id: ID del expediente
            documento_id: ID del documento
            usuario_id: Usuario que rechaza
            motivo: Motivo del rechazo
            
        Returns:
            Documento rechazado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        documento = None
        for doc in expediente.documentos:
            if doc.id == documento_id:
                documento = doc
                break
        
        if not documento:
            raise ValueError(f"Documento {documento_id} no encontrado")
        
        ahora = datetime.now()
        documento.estado = EstadoDocumento.RECHAZADO
        documento.modificado_en = ahora
        
        documento.comentarios.append({
            "usuario_id": usuario_id,
            "texto": motivo,
            "tipo": "rechazo",
            "timestamp": ahora.isoformat()
        })
        
        # Crear alerta de documento rechazado
        alerta = AlertaExpediente(
            id=str(uuid.uuid4()),
            tipo="urgente",
            titulo=f"Documento rechazado: {documento.tipo.value}",
            mensaje=f"Motivo: {motivo}",
            severidad="alta",
            fecha_generacion=ahora,
            fecha_vencimiento=ahora + timedelta(days=7),
            documento_id=documento_id,
            acciones=[
                {"tipo": "ver_documento", "label": "Ver documento"},
                {"tipo": "cargar_nuevo", "label": "Cargar versión corregida"}
            ]
        )
        expediente.alertas.append(alerta)
        
        self._expedientes_cache[expediente_id] = expediente
        
        return documento
    
    async def obtener_documento(
        self,
        expediente_id: str,
        documento_id: str
    ) -> Optional[Documento]:
        """
        Obtiene un documento específico.
        
        Args:
            expediente_id: ID del expediente
            documento_id: ID del documento
            
        Returns:
            Documento o None
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return None
        
        for doc in expediente.documentos:
            if doc.id == documento_id:
                return doc
        
        return None
    
    async def obtener_versiones_documento(
        self,
        expediente_id: str,
        tipo_documento: TipoDocumento
    ) -> List[Documento]:
        """
        Obtiene todas las versiones de un tipo de documento.
        
        Args:
            expediente_id: ID del expediente
            tipo_documento: Tipo de documento
            
        Returns:
            Lista de versiones ordenadas
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return []
        
        versiones = [doc for doc in expediente.documentos if doc.tipo == tipo_documento]
        versiones.sort(key=lambda d: d.version, reverse=True)
        
        return versiones
    
    # =========================================================================
    # WORKFLOWS DE APROBACIÓN
    # =========================================================================
    
    async def iniciar_workflow(
        self,
        expediente_id: str,
        documento_id: str,
        tipo_workflow: TipoWorkflow,
        usuario_id: str,
        aprobadores: List[str]
    ) -> WorkflowAprobacion:
        """
        Inicia un workflow de aprobación para un documento.
        
        Args:
            expediente_id: ID del expediente
            documento_id: ID del documento
            tipo_workflow: Tipo de workflow
            usuario_id: Usuario que inicia
            aprobadores: Lista de IDs de aprobadores
            
        Returns:
            Workflow creado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        ahora = datetime.now()
        
        # Crear etapas según tipo de workflow
        etapas = []
        if tipo_workflow == TipoWorkflow.REVISION_SIMPLE:
            etapas = [
                {"orden": 1, "tipo": "revision", "aprobador": aprobadores[0] if aprobadores else usuario_id, "estado": "pendiente"}
            ]
        elif tipo_workflow == TipoWorkflow.APROBACION_LEGAL:
            etapas = [
                {"orden": 1, "tipo": "revision_legal", "aprobador": aprobadores[0] if len(aprobadores) > 0 else usuario_id, "estado": "pendiente"},
                {"orden": 2, "tipo": "aprobacion_final", "aprobador": aprobadores[1] if len(aprobadores) > 1 else usuario_id, "estado": "pendiente"}
            ]
        elif tipo_workflow == TipoWorkflow.APROBACION_TECNICA:
            etapas = [
                {"orden": 1, "tipo": "revision_tecnica", "aprobador": aprobadores[0] if len(aprobadores) > 0 else usuario_id, "estado": "pendiente"},
                {"orden": 2, "tipo": "validacion", "aprobador": aprobadores[1] if len(aprobadores) > 1 else usuario_id, "estado": "pendiente"}
            ]
        elif tipo_workflow == TipoWorkflow.APROBACION_MULTIPLE:
            etapas = [
                {"orden": i+1, "tipo": "aprobacion", "aprobador": aprobador, "estado": "pendiente"}
                for i, aprobador in enumerate(aprobadores)
            ]
        
        workflow = WorkflowAprobacion(
            id=str(uuid.uuid4()),
            tipo=tipo_workflow,
            documento_id=documento_id,
            estado="en_progreso",
            etapas=etapas,
            etapa_actual=1,
            creado_por=usuario_id,
            creado_en=ahora
        )
        
        expediente.workflows.append(workflow)
        
        # Actualizar estado del documento
        for doc in expediente.documentos:
            if doc.id == documento_id:
                doc.estado = EstadoDocumento.EN_REVISION
                break
        
        # Registrar evento
        evento = EventoExpediente(
            id=str(uuid.uuid4()),
            tipo=TipoEvento.WORKFLOW,
            descripcion=f"Workflow {tipo_workflow.value} iniciado",
            detalle={
                "workflow_id": workflow.id,
                "documento_id": documento_id,
                "etapas": len(etapas)
            },
            usuario_id=usuario_id,
            usuario_nombre=usuario_id,
            timestamp=ahora,
            documento_id=documento_id
        )
        expediente.eventos.append(evento)
        
        self._expedientes_cache[expediente_id] = expediente
        
        return workflow
    
    async def avanzar_workflow(
        self,
        expediente_id: str,
        workflow_id: str,
        usuario_id: str,
        accion: str,  # aprobar, rechazar
        comentario: Optional[str] = None
    ) -> WorkflowAprobacion:
        """
        Avanza una etapa del workflow.
        
        Args:
            expediente_id: ID del expediente
            workflow_id: ID del workflow
            usuario_id: Usuario que ejecuta
            accion: Acción (aprobar/rechazar)
            comentario: Comentario opcional
            
        Returns:
            Workflow actualizado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        workflow = None
        for wf in expediente.workflows:
            if wf.id == workflow_id:
                workflow = wf
                break
        
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} no encontrado")
        
        ahora = datetime.now()
        
        # Actualizar etapa actual
        etapa_idx = workflow.etapa_actual - 1
        if etapa_idx < len(workflow.etapas):
            workflow.etapas[etapa_idx]["estado"] = "aprobado" if accion == "aprobar" else "rechazado"
            workflow.etapas[etapa_idx]["fecha"] = ahora.isoformat()
            workflow.etapas[etapa_idx]["usuario"] = usuario_id
            if comentario:
                workflow.etapas[etapa_idx]["comentario"] = comentario
        
        if accion == "rechazar":
            workflow.estado = "rechazado"
            workflow.resultado = "rechazado"
            workflow.completado_en = ahora
            
            # Rechazar documento
            await self.rechazar_documento(
                expediente_id,
                workflow.documento_id,
                usuario_id,
                comentario or "Rechazado en workflow"
            )
        else:
            # Verificar si hay más etapas
            if workflow.etapa_actual < len(workflow.etapas):
                workflow.etapa_actual += 1
            else:
                # Workflow completado
                workflow.estado = "aprobado"
                workflow.resultado = "aprobado"
                workflow.completado_en = ahora
                
                # Aprobar documento
                await self.aprobar_documento(
                    expediente_id,
                    workflow.documento_id,
                    usuario_id,
                    "Aprobado por workflow"
                )
        
        if comentario:
            workflow.comentarios.append({
                "usuario_id": usuario_id,
                "texto": comentario,
                "accion": accion,
                "timestamp": ahora.isoformat()
            })
        
        self._expedientes_cache[expediente_id] = expediente
        
        return workflow
    
    # =========================================================================
    # BÚSQUEDA Y CONSULTAS
    # =========================================================================
    
    async def buscar_expedientes(
        self,
        query: Optional[str] = None,
        tipo: Optional[TipoExpediente] = None,
        estado: Optional[EstadoExpediente] = None,
        propietario_id: Optional[str] = None,
        comuna: Optional[str] = None,
        region: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        completitud_min: Optional[float] = None,
        tiene_alertas: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        ordenar_por: str = "modificado_en",
        orden: str = "desc",
        limite: int = 20,
        offset: int = 0
    ) -> Tuple[List[BusquedaResultado], int]:
        """
        Búsqueda avanzada de expedientes.
        
        Args:
            query: Texto de búsqueda (rol, dirección, título)
            tipo: Filtro por tipo
            estado: Filtro por estado
            propietario_id: Filtro por propietario
            comuna: Filtro por comuna
            region: Filtro por región
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            completitud_min: Completitud mínima (0-100)
            tiene_alertas: Filtrar por alertas activas
            tags: Filtrar por tags
            ordenar_por: Campo de ordenamiento
            orden: asc/desc
            limite: Máximo resultados
            offset: Paginación
            
        Returns:
            Tuple (resultados, total)
        """
        # Mock: generar resultados de ejemplo
        resultados = []
        
        comunas_ejemplo = ["Providencia", "Las Condes", "Ñuñoa", "Santiago", "Vitacura"]
        
        for i in range(min(limite, 15)):
            comunas = comuna if comuna else comunas_ejemplo[i % len(comunas_ejemplo)]
            
            resultado = BusquedaResultado(
                expediente_id=str(uuid.uuid4()),
                codigo=f"EXP-2026-{1000+i:06d}",
                titulo=f"Propiedad {comunas} #{i+1}",
                tipo=tipo or TipoExpediente.UNIDAD_COPROPIEDAD,
                estado=estado or EstadoExpediente.ACTIVO,
                rol_sii=f"{100+i}-{500+i}",
                direccion=f"Av. Principal {1000+i*10}, {comunas}",
                comuna=comunas,
                completitud_pct=65.0 + (i * 2.5) if i < 14 else 100.0,
                alertas_activas=max(0, 3 - i),
                relevancia_score=0.95 - (i * 0.03),
                fragmentos_relevantes=[]
            )
            resultados.append(resultado)
        
        total = 150  # Mock total
        
        return resultados, total
    
    async def buscar_documentos(
        self,
        query: Optional[str] = None,
        tipo_documento: Optional[TipoDocumento] = None,
        estado: Optional[EstadoDocumento] = None,
        expediente_id: Optional[str] = None,
        vencidos: Optional[bool] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda de documentos across expedientes.
        
        Args:
            query: Texto de búsqueda
            tipo_documento: Filtro por tipo
            estado: Filtro por estado
            expediente_id: Filtro por expediente
            vencidos: Solo documentos vencidos
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            limite: Máximo resultados
            
        Returns:
            Lista de documentos con contexto
        """
        resultados = []
        
        # Mock resultados
        tipos_mock = list(TipoDocumento)[:10]
        
        for i in range(min(limite, 20)):
            tipo = tipo_documento or tipos_mock[i % len(tipos_mock)]
            
            doc_info = {
                "documento_id": str(uuid.uuid4()),
                "expediente_id": str(uuid.uuid4()),
                "expediente_codigo": f"EXP-2026-{2000+i:06d}",
                "tipo": tipo.value,
                "nombre": f"{tipo.value}_{i+1}.pdf",
                "estado": estado.value if estado else "aprobado",
                "fecha_emision": (date.today() - timedelta(days=30+i*5)).isoformat(),
                "fecha_vencimiento": (date.today() + timedelta(days=60-i*5)).isoformat() if i < 12 else None,
                "esta_vencido": i >= 12,
                "relevancia": 0.9 - (i * 0.02)
            }
            resultados.append(doc_info)
        
        return resultados
    
    # =========================================================================
    # ALERTAS Y NOTIFICACIONES
    # =========================================================================
    
    async def obtener_alertas(
        self,
        expediente_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        severidad: Optional[str] = None,
        solo_no_leidas: bool = False,
        solo_activas: bool = True,
        limite: int = 50
    ) -> List[AlertaExpediente]:
        """
        Obtiene alertas según filtros.
        
        Args:
            expediente_id: Filtro por expediente
            usuario_id: Filtro por usuario
            severidad: Filtro por severidad
            solo_no_leidas: Solo alertas no leídas
            solo_activas: Solo alertas no resueltas
            limite: Máximo resultados
            
        Returns:
            Lista de alertas
        """
        if expediente_id:
            expediente = await self.obtener_expediente(expediente_id)
            if expediente:
                alertas = expediente.alertas
                
                if solo_no_leidas:
                    alertas = [a for a in alertas if not a.leida]
                if solo_activas:
                    alertas = [a for a in alertas if not a.resuelta]
                if severidad:
                    alertas = [a for a in alertas if a.severidad == severidad]
                
                return alertas[:limite]
        
        # Mock alertas globales
        alertas = []
        severidades = ["baja", "media", "alta", "critica"]
        tipos = ["vencimiento", "pendiente", "urgente", "informativa"]
        
        for i in range(min(limite, 25)):
            alerta = AlertaExpediente(
                id=str(uuid.uuid4()),
                tipo=tipos[i % len(tipos)],
                titulo=f"Alerta #{i+1}",
                mensaje=f"Descripción de la alerta {i+1}",
                severidad=severidades[i % len(severidades)],
                fecha_generacion=datetime.now() - timedelta(days=i),
                fecha_vencimiento=datetime.now() + timedelta(days=7-i) if i < 7 else None,
                documento_id=None,
                leida=i > 10,
                resuelta=i > 20
            )
            alertas.append(alerta)
        
        return alertas
    
    async def marcar_alerta_leida(
        self,
        expediente_id: str,
        alerta_id: str,
        usuario_id: str
    ) -> bool:
        """
        Marca una alerta como leída.
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return False
        
        for alerta in expediente.alertas:
            if alerta.id == alerta_id:
                alerta.leida = True
                self._expedientes_cache[expediente_id] = expediente
                return True
        
        return False
    
    async def resolver_alerta(
        self,
        expediente_id: str,
        alerta_id: str,
        usuario_id: str,
        resolucion: Optional[str] = None
    ) -> bool:
        """
        Marca una alerta como resuelta.
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return False
        
        for alerta in expediente.alertas:
            if alerta.id == alerta_id:
                alerta.resuelta = True
                alerta.acciones.append({
                    "tipo": "resolucion",
                    "usuario_id": usuario_id,
                    "detalle": resolucion,
                    "timestamp": datetime.now().isoformat()
                })
                self._expedientes_cache[expediente_id] = expediente
                return True
        
        return False
    
    async def verificar_documentos_vencidos(
        self,
        expediente_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Verifica documentos próximos a vencer o vencidos.
        
        Args:
            expediente_id: Opcional, verificar solo un expediente
            
        Returns:
            Lista de documentos con estado de vencimiento
        """
        documentos_alerta = []
        ahora = date.today()
        
        # Si se especifica expediente, verificar solo ese
        if expediente_id:
            expediente = await self.obtener_expediente(expediente_id)
            if expediente:
                for doc in expediente.documentos:
                    if doc.fecha_vencimiento:
                        dias_restantes = (doc.fecha_vencimiento - ahora).days
                        
                        if dias_restantes <= 30:
                            documentos_alerta.append({
                                "expediente_id": expediente.id,
                                "expediente_codigo": expediente.codigo,
                                "documento_id": doc.id,
                                "tipo": doc.tipo.value,
                                "nombre": doc.nombre,
                                "fecha_vencimiento": doc.fecha_vencimiento.isoformat(),
                                "dias_restantes": dias_restantes,
                                "estado": "vencido" if dias_restantes < 0 else "por_vencer"
                            })
        
        # Mock global
        else:
            for i in range(15):
                dias = -5 + i * 3
                documentos_alerta.append({
                    "expediente_id": str(uuid.uuid4()),
                    "expediente_codigo": f"EXP-2026-{3000+i:06d}",
                    "documento_id": str(uuid.uuid4()),
                    "tipo": list(VIGENCIA_DOCUMENTOS.keys())[i % len(VIGENCIA_DOCUMENTOS)].value,
                    "nombre": f"documento_{i}.pdf",
                    "fecha_vencimiento": (ahora + timedelta(days=dias)).isoformat(),
                    "dias_restantes": dias,
                    "estado": "vencido" if dias < 0 else "por_vencer"
                })
        
        return documentos_alerta
    
    # =========================================================================
    # ESTADÍSTICAS Y REPORTES
    # =========================================================================
    
    async def obtener_estadisticas(
        self,
        usuario_id: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None
    ) -> EstadisticasExpedientes:
        """
        Obtiene estadísticas agregadas de expedientes.
        
        Args:
            usuario_id: Filtrar por propietario
            fecha_desde: Fecha inicio
            fecha_hasta: Fecha fin
            
        Returns:
            Estadísticas agregadas
        """
        # Mock estadísticas
        stats = EstadisticasExpedientes(
            total_expedientes=1250,
            por_tipo={
                TipoExpediente.UNIDAD_COPROPIEDAD.value: 680,
                TipoExpediente.PROPIEDAD_INDIVIDUAL.value: 320,
                TipoExpediente.CONDOMINIO.value: 85,
                TipoExpediente.TERRENO.value: 95,
                TipoExpediente.LOCAL_COMERCIAL.value: 45,
                TipoExpediente.OFICINA.value: 25,
            },
            por_estado={
                EstadoExpediente.ACTIVO.value: 890,
                EstadoExpediente.COMPLETO.value: 180,
                EstadoExpediente.EN_REVISION.value: 85,
                EstadoExpediente.PENDIENTE_DOCUMENTOS.value: 55,
                EstadoExpediente.BORRADOR.value: 25,
                EstadoExpediente.ARCHIVADO.value: 15,
            },
            completitud_promedio=78.5,
            documentos_totales=8750,
            documentos_pendientes=342,
            documentos_vencidos=67,
            alertas_activas=156,
            expedientes_activos_mes=89,
            tendencia_creacion=[
                {"mes": "2025-09", "cantidad": 65},
                {"mes": "2025-10", "cantidad": 72},
                {"mes": "2025-11", "cantidad": 81},
                {"mes": "2025-12", "cantidad": 78},
                {"mes": "2026-01", "cantidad": 89},
            ]
        )
        
        return stats
    
    async def generar_reporte_expediente(
        self,
        expediente_id: str,
        formato: str = "json",
        secciones: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Genera reporte completo de un expediente.
        
        Args:
            expediente_id: ID del expediente
            formato: json, pdf, xlsx
            secciones: Secciones a incluir
            
        Returns:
            Reporte estructurado
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            raise ValueError(f"Expediente {expediente_id} no encontrado")
        
        secciones = secciones or ["general", "documentos", "eventos", "alertas", "cumplimiento"]
        
        reporte = {
            "expediente_id": expediente.id,
            "codigo": expediente.codigo,
            "generado_en": datetime.now().isoformat(),
            "formato": formato,
            "secciones": {}
        }
        
        if "general" in secciones:
            reporte["secciones"]["general"] = {
                "tipo": expediente.tipo.value,
                "estado": expediente.estado.value,
                "titulo": expediente.titulo,
                "propiedad": {
                    "rol_sii": expediente.propiedad.rol_sii,
                    "direccion": expediente.propiedad.direccion,
                    "comuna": expediente.propiedad.comuna,
                    "superficie_terreno": expediente.propiedad.superficie_terreno_m2,
                    "superficie_construida": expediente.propiedad.superficie_construida_m2,
                    "ano_construccion": expediente.propiedad.ano_construccion,
                    "avaluo_fiscal_uf": expediente.propiedad.avaluo_fiscal_uf,
                },
                "propietario": expediente.propietario_nombre,
                "completitud": expediente.completitud_pct,
                "creado_en": expediente.creado_en.isoformat(),
                "modificado_en": expediente.modificado_en.isoformat(),
            }
        
        if "documentos" in secciones:
            docs_resumen = []
            for doc in expediente.documentos:
                docs_resumen.append({
                    "tipo": doc.tipo.value,
                    "nombre": doc.nombre,
                    "estado": doc.estado.value,
                    "version": doc.version,
                    "vigente": doc.esta_vigente(),
                    "dias_para_vencer": doc.dias_para_vencer(),
                })
            
            reporte["secciones"]["documentos"] = {
                "total": len(expediente.documentos),
                "aprobados": len([d for d in expediente.documentos if d.estado == EstadoDocumento.APROBADO]),
                "pendientes": len(expediente.documentos_pendientes),
                "vencidos": len([d for d in expediente.documentos if not d.esta_vigente()]),
                "listado": docs_resumen
            }
        
        if "eventos" in secciones:
            reporte["secciones"]["eventos"] = {
                "total": len(expediente.eventos),
                "ultimos_10": [
                    {
                        "tipo": e.tipo.value,
                        "descripcion": e.descripcion,
                        "usuario": e.usuario_nombre,
                        "timestamp": e.timestamp.isoformat()
                    }
                    for e in sorted(expediente.eventos, key=lambda x: x.timestamp, reverse=True)[:10]
                ]
            }
        
        if "alertas" in secciones:
            alertas_activas = [a for a in expediente.alertas if not a.resuelta]
            reporte["secciones"]["alertas"] = {
                "total_activas": len(alertas_activas),
                "por_severidad": {
                    "critica": len([a for a in alertas_activas if a.severidad == "critica"]),
                    "alta": len([a for a in alertas_activas if a.severidad == "alta"]),
                    "media": len([a for a in alertas_activas if a.severidad == "media"]),
                    "baja": len([a for a in alertas_activas if a.severidad == "baja"]),
                },
                "listado": [
                    {
                        "tipo": a.tipo,
                        "titulo": a.titulo,
                        "severidad": a.severidad,
                        "fecha_generacion": a.fecha_generacion.isoformat()
                    }
                    for a in alertas_activas
                ]
            }
        
        if "cumplimiento" in secciones:
            docs_requeridos = REQUISITOS_DOCUMENTALES.get(expediente.tipo, [])
            docs_presentes = [d.tipo for d in expediente.documentos if d.estado in [EstadoDocumento.APROBADO, EstadoDocumento.CARGADO]]
            
            cumplimiento = []
            for req in docs_requeridos:
                cumplimiento.append({
                    "documento": req.value,
                    "requerido": True,
                    "presente": req in docs_presentes,
                    "estado": "cumple" if req in docs_presentes else "pendiente"
                })
            
            reporte["secciones"]["cumplimiento"] = {
                "porcentaje": (len([c for c in cumplimiento if c["presente"]]) / len(cumplimiento) * 100) if cumplimiento else 100,
                "documentos_requeridos": len(docs_requeridos),
                "documentos_presentes": len([c for c in cumplimiento if c["presente"]]),
                "detalle": cumplimiento
            }
        
        return reporte
    
    # =========================================================================
    # INTEGRACIONES CON OTROS MÓDULOS
    # =========================================================================
    
    async def vincular_modulo(
        self,
        expediente_id: str,
        modulo: str,
        referencia_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Vincula el expediente con otro módulo DATAPOLIS.
        
        Args:
            expediente_id: ID del expediente
            modulo: Código del módulo (M01, M03, M04, etc.)
            referencia_id: ID en el módulo vinculado
            metadata: Metadata adicional
            
        Returns:
            True si se vinculó correctamente
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return False
        
        vinculo = f"{modulo}:{referencia_id}"
        if vinculo not in expediente.modulos_vinculados:
            expediente.modulos_vinculados.append(vinculo)
            
            # Registrar evento
            evento = EventoExpediente(
                id=str(uuid.uuid4()),
                tipo=TipoEvento.INTEGRACION,
                descripcion=f"Vinculado con módulo {modulo}",
                detalle={
                    "modulo": modulo,
                    "referencia_id": referencia_id,
                    "metadata": metadata
                },
                usuario_id="sistema",
                usuario_nombre="Sistema",
                timestamp=datetime.now()
            )
            expediente.eventos.append(evento)
            
            self._expedientes_cache[expediente_id] = expediente
        
        return True
    
    async def obtener_referencias_modulos(
        self,
        expediente_id: str
    ) -> Dict[str, List[str]]:
        """
        Obtiene referencias a otros módulos.
        
        Args:
            expediente_id: ID del expediente
            
        Returns:
            Diccionario modulo -> lista de referencias
        """
        expediente = await self.obtener_expediente(expediente_id)
        if not expediente:
            return {}
        
        referencias = {}
        for vinculo in expediente.modulos_vinculados:
            partes = vinculo.split(":")
            if len(partes) == 2:
                modulo, ref_id = partes
                if modulo not in referencias:
                    referencias[modulo] = []
                referencias[modulo].append(ref_id)
        
        return referencias
    
    # =========================================================================
    # UTILIDADES INTERNAS
    # =========================================================================
    
    async def _recalcular_completitud(self, expediente: Expediente) -> None:
        """Recalcula el porcentaje de completitud del expediente."""
        docs_requeridos = REQUISITOS_DOCUMENTALES.get(expediente.tipo, [])
        
        if not docs_requeridos:
            expediente.completitud_pct = 100.0
            return
        
        docs_presentes = set()
        for doc in expediente.documentos:
            if doc.estado in [EstadoDocumento.APROBADO, EstadoDocumento.CARGADO]:
                docs_presentes.add(doc.tipo)
        
        cumplidos = len([r for r in docs_requeridos if r in docs_presentes])
        expediente.completitud_pct = (cumplidos / len(docs_requeridos)) * 100
        
        # Actualizar documentos pendientes
        expediente.documentos_pendientes = [r for r in docs_requeridos if r not in docs_presentes]
    
    def _generar_expediente_ejemplo(self, expediente_id: str) -> Expediente:
        """Genera un expediente de ejemplo para desarrollo."""
        ahora = datetime.now()
        
        propiedad = PropiedadBasica(
            rol_sii="123-456",
            direccion="Av. Providencia 1234, Depto 501",
            comuna="Providencia",
            region="Metropolitana",
            tipo_propiedad="departamento",
            superficie_terreno_m2=None,
            superficie_construida_m2=85.5,
            ano_construccion=2015,
            coordenadas={"lat": -33.4289, "lon": -70.6093},
            avaluo_fiscal_uf=4500.0
        )
        
        documentos = [
            Documento(
                id=str(uuid.uuid4()),
                tipo=TipoDocumento.ESCRITURA_PROPIEDAD,
                nombre="escritura_propiedad.pdf",
                descripcion="Escritura de compraventa",
                archivo_url="/storage/docs/escritura_123456.pdf",
                archivo_hash="abc123...",
                tamano_bytes=2500000,
                mime_type="application/pdf",
                estado=EstadoDocumento.APROBADO,
                confidencialidad=NivelConfidencialidad.CONFIDENCIAL,
                version=1,
                version_anterior_id=None,
                fecha_emision=date(2020, 3, 15),
                fecha_vencimiento=None,
                emisor="Notaría González",
                numero_documento="REP-2020-00456",
                metadata={},
                creado_por="admin",
                creado_en=ahora - timedelta(days=180),
                modificado_en=ahora - timedelta(days=90),
                aprobado_por="supervisor",
                aprobado_en=ahora - timedelta(days=89)
            ),
            Documento(
                id=str(uuid.uuid4()),
                tipo=TipoDocumento.CERTIFICADO_DOMINIO,
                nombre="certificado_dominio_vigente.pdf",
                descripcion="Certificado de dominio vigente CBR",
                archivo_url="/storage/docs/cert_dom_123456.pdf",
                archivo_hash="def456...",
                tamano_bytes=850000,
                mime_type="application/pdf",
                estado=EstadoDocumento.APROBADO,
                confidencialidad=NivelConfidencialidad.INTERNO,
                version=3,
                version_anterior_id=None,
                fecha_emision=date.today() - timedelta(days=15),
                fecha_vencimiento=date.today() + timedelta(days=15),
                emisor="CBR Santiago",
                numero_documento="CD-2026-123456",
                metadata={},
                creado_por="sistema",
                creado_en=ahora - timedelta(days=15),
                modificado_en=ahora - timedelta(days=15),
                aprobado_por="legal",
                aprobado_en=ahora - timedelta(days=14)
            )
        ]
        
        eventos = [
            EventoExpediente(
                id=str(uuid.uuid4()),
                tipo=TipoEvento.CREACION,
                descripcion="Expediente creado",
                detalle={},
                usuario_id="admin",
                usuario_nombre="Administrador",
                timestamp=ahora - timedelta(days=180)
            )
        ]
        
        alertas = [
            AlertaExpediente(
                id=str(uuid.uuid4()),
                tipo="vencimiento",
                titulo="Certificado de dominio próximo a vencer",
                mensaje="El certificado de dominio vence en 15 días",
                severidad="media",
                fecha_generacion=ahora,
                fecha_vencimiento=datetime.now() + timedelta(days=15),
                documento_id=documentos[1].id
            )
        ]
        
        return Expediente(
            id=expediente_id,
            codigo="EXP-2026-000001",
            tipo=TipoExpediente.UNIDAD_COPROPIEDAD,
            estado=EstadoExpediente.ACTIVO,
            titulo="Departamento Providencia 501",
            descripcion="Unidad de copropiedad en edificio residencial",
            propiedad=propiedad,
            propietario_id="prop-001",
            propietario_nombre="Juan Pérez González",
            administrador_id=None,
            documentos=documentos,
            eventos=eventos,
            alertas=alertas,
            workflows=[],
            metadata={},
            tags=["copropiedad", "providencia", "residencial"],
            creado_por="admin",
            creado_en=ahora - timedelta(days=180),
            modificado_en=ahora - timedelta(days=15),
            completitud_pct=75.0,
            documentos_pendientes=[TipoDocumento.CERTIFICADO_GRAVAMENES],
            documentos_vencidos=[],
            modulos_vinculados=["M03:score-001", "M04:val-001"]
        )


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_servicio_expediente: Optional[ServicioExpedienteUniversal] = None


def get_servicio_expediente() -> ServicioExpedienteUniversal:
    """Obtiene instancia singleton del servicio."""
    global _servicio_expediente
    if _servicio_expediente is None:
        _servicio_expediente = ServicioExpedienteUniversal()
    return _servicio_expediente


# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Enums
    "TipoExpediente",
    "EstadoExpediente",
    "TipoDocumento",
    "EstadoDocumento",
    "NivelConfidencialidad",
    "TipoEvento",
    "TipoWorkflow",
    # Data classes
    "Documento",
    "EventoExpediente",
    "WorkflowAprobacion",
    "AlertaExpediente",
    "PropiedadBasica",
    "Expediente",
    "BusquedaResultado",
    "EstadisticasExpedientes",
    # Constantes
    "REQUISITOS_DOCUMENTALES",
    "VIGENCIA_DOCUMENTOS",
    # Servicio
    "ServicioExpedienteUniversal",
    "get_servicio_expediente",
]
