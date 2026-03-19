# ============================================================================
# DATAPOLIS v3.0 - SERVICE M11 GESTIÓN DOCUMENTAL
# ============================================================================
# Gestión de documentos, archivos, versionamiento, firmas electrónicas
# Cumplimiento Ley 21.442, Ley 19.799 Firma Electrónica
# ============================================================================

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
import hashlib
import uuid

# ============================================================================
# ENUMS
# ============================================================================

class TipoDocumento(str, Enum):
    ACTA_ASAMBLEA = "acta_asamblea"
    ACTA_COMITE = "acta_comite"
    REGLAMENTO_COPROPIEDAD = "reglamento_copropiedad"
    CONTRATO_ARRIENDO = "contrato_arriendo"
    CONTRATO_TRABAJO = "contrato_trabajo"
    CONTRATO_SERVICIO = "contrato_servicio"
    FACTURA = "factura"
    BOLETA = "boleta"
    COTIZACION = "cotizacion"
    ORDEN_COMPRA = "orden_compra"
    POLIZA_SEGURO = "poliza_seguro"
    CERTIFICADO = "certificado"
    PODER = "poder"
    ESCRITURA = "escritura"
    PLANO = "plano"
    PRESUPUESTO = "presupuesto"
    INFORME = "informe"
    COMUNICACION = "comunicacion"
    CORRESPONDENCIA = "correspondencia"
    OTRO = "otro"

class EstadoDocumento(str, Enum):
    BORRADOR = "borrador"
    REVISION = "revision"
    APROBADO = "aprobado"
    VIGENTE = "vigente"
    FIRMADO = "firmado"
    ARCHIVADO = "archivado"
    ANULADO = "anulado"
    VENCIDO = "vencido"

class NivelAcceso(str, Enum):
    PUBLICO = "publico"
    RESIDENTES = "residentes"
    COMITE = "comite"
    ADMINISTRACION = "administracion"
    CONFIDENCIAL = "confidencial"

class TipoFirma(str, Enum):
    SIMPLE = "simple"
    AVANZADA = "avanzada"
    ELECTRONICA_SIMPLE = "electronica_simple"
    ELECTRONICA_AVANZADA = "electronica_avanzada"

class AccionAuditoria(str, Enum):
    CREAR = "crear"
    LEER = "leer"
    MODIFICAR = "modificar"
    ELIMINAR = "eliminar"
    FIRMAR = "firmar"
    COMPARTIR = "compartir"
    DESCARGAR = "descargar"
    IMPRIMIR = "imprimir"

# ============================================================================
# MODELOS
# ============================================================================

@dataclass
class Documento:
    id: str
    codigo: str
    tipo: TipoDocumento
    titulo: str
    descripcion: str
    estado: EstadoDocumento
    version: int
    nivel_acceso: NivelAcceso
    archivo_nombre: str
    archivo_extension: str
    archivo_tamano_bytes: int
    archivo_hash: str
    archivo_url: str
    metadata: Dict[str, Any]
    tags: List[str]
    propietario_id: str
    copropiedad_id: Optional[str]
    fecha_creacion: datetime
    fecha_modificacion: datetime
    fecha_vencimiento: Optional[date]
    firmado: bool = False
    firmas: List[Dict] = field(default_factory=list)
    versiones_anteriores: List[str] = field(default_factory=list)

@dataclass
class Carpeta:
    id: str
    nombre: str
    descripcion: str
    carpeta_padre_id: Optional[str]
    nivel_acceso: NivelAcceso
    propietario_id: str
    copropiedad_id: Optional[str]
    documentos: List[str] = field(default_factory=list)
    subcarpetas: List[str] = field(default_factory=list)
    fecha_creacion: datetime = field(default_factory=datetime.now)

@dataclass
class FirmaElectronica:
    id: str
    documento_id: str
    firmante_id: str
    firmante_nombre: str
    firmante_rut: str
    tipo_firma: TipoFirma
    certificado_id: Optional[str]
    hash_documento: str
    firma_digital: str
    fecha_firma: datetime
    ip_origen: str
    ubicacion_gps: Optional[Dict[str, float]]
    valida: bool = True

@dataclass
class PlantillaDocumento:
    id: str
    nombre: str
    tipo: TipoDocumento
    descripcion: str
    contenido_html: str
    variables: List[Dict[str, Any]]
    activa: bool = True
    usos: int = 0

@dataclass
class RegistroAuditoria:
    id: str
    documento_id: str
    usuario_id: str
    usuario_nombre: str
    accion: AccionAuditoria
    descripcion: str
    ip_origen: str
    fecha: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================

class GestionDocumentalService:
    """Servicio de gestión documental completo"""
    
    def __init__(self):
        self.documentos: Dict[str, Documento] = {}
        self.carpetas: Dict[str, Carpeta] = {}
        self.firmas: Dict[str, FirmaElectronica] = {}
        self.plantillas: Dict[str, PlantillaDocumento] = {}
        self.auditoria: List[RegistroAuditoria] = []
        self._inicializar_estructura()
    
    def _inicializar_estructura(self):
        """Inicializa estructura de carpetas estándar"""
        carpetas_base = [
            ("actas", "Actas de Asambleas y Comités"),
            ("contratos", "Contratos y Convenios"),
            ("financiero", "Documentos Financieros"),
            ("legal", "Documentos Legales"),
            ("operacional", "Documentos Operacionales"),
            ("correspondencia", "Correspondencia"),
            ("archivo_historico", "Archivo Histórico")
        ]
        
        for codigo, nombre in carpetas_base:
            carpeta_id = f"carpeta_{codigo}"
            self.carpetas[carpeta_id] = Carpeta(
                id=carpeta_id,
                nombre=nombre,
                descripcion=f"Carpeta de {nombre.lower()}",
                carpeta_padre_id=None,
                nivel_acceso=NivelAcceso.ADMINISTRACION,
                propietario_id="sistema",
                copropiedad_id=None
            )
    
    def _generar_codigo(self, tipo: TipoDocumento) -> str:
        """Genera código único para documento"""
        prefijos = {
            TipoDocumento.ACTA_ASAMBLEA: "ACT-ASM",
            TipoDocumento.ACTA_COMITE: "ACT-COM",
            TipoDocumento.CONTRATO_ARRIENDO: "CTR-ARR",
            TipoDocumento.CONTRATO_TRABAJO: "CTR-TRB",
            TipoDocumento.FACTURA: "FAC",
            TipoDocumento.COTIZACION: "COT",
            TipoDocumento.INFORME: "INF"
        }
        prefijo = prefijos.get(tipo, "DOC")
        fecha = datetime.now().strftime("%Y%m")
        correlativo = len([d for d in self.documentos.values() if d.tipo == tipo]) + 1
        return f"{prefijo}-{fecha}-{correlativo:04d}"
    
    def _calcular_hash(self, contenido: bytes) -> str:
        """Calcula hash SHA-256 del contenido"""
        return hashlib.sha256(contenido).hexdigest()
    
    def _registrar_auditoria(self, documento_id: str, usuario_id: str, 
                            usuario_nombre: str, accion: AccionAuditoria,
                            descripcion: str, ip_origen: str = "0.0.0.0",
                            metadata: Dict = None):
        """Registra acción en log de auditoría"""
        registro = RegistroAuditoria(
            id=str(uuid.uuid4())[:8],
            documento_id=documento_id,
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            accion=accion,
            descripcion=descripcion,
            ip_origen=ip_origen,
            fecha=datetime.now(),
            metadata=metadata or {}
        )
        self.auditoria.append(registro)
    
    # ========== GESTIÓN DE DOCUMENTOS ==========
    
    def crear_documento(
        self,
        tipo: TipoDocumento,
        titulo: str,
        descripcion: str,
        archivo_nombre: str,
        archivo_contenido: bytes,
        propietario_id: str,
        copropiedad_id: Optional[str] = None,
        nivel_acceso: NivelAcceso = NivelAcceso.ADMINISTRACION,
        tags: List[str] = None,
        metadata: Dict = None,
        carpeta_id: Optional[str] = None,
        fecha_vencimiento: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Crea nuevo documento en el sistema
        
        Args:
            tipo: Tipo de documento
            titulo: Título del documento
            descripcion: Descripción
            archivo_nombre: Nombre del archivo
            archivo_contenido: Contenido en bytes
            propietario_id: ID del creador
            copropiedad_id: ID de la copropiedad (opcional)
            nivel_acceso: Nivel de acceso requerido
            tags: Etiquetas para búsqueda
            metadata: Metadata adicional
            carpeta_id: Carpeta destino
            fecha_vencimiento: Fecha de vencimiento
            
        Returns:
            Dict con documento creado
        """
        doc_id = str(uuid.uuid4())[:8]
        codigo = self._generar_codigo(tipo)
        
        # Extraer extensión
        extension = archivo_nombre.split(".")[-1] if "." in archivo_nombre else ""
        
        # Calcular hash
        archivo_hash = self._calcular_hash(archivo_contenido)
        
        documento = Documento(
            id=doc_id,
            codigo=codigo,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            estado=EstadoDocumento.BORRADOR,
            version=1,
            nivel_acceso=nivel_acceso,
            archivo_nombre=archivo_nombre,
            archivo_extension=extension,
            archivo_tamano_bytes=len(archivo_contenido),
            archivo_hash=archivo_hash,
            archivo_url=f"/storage/documentos/{doc_id}/{archivo_nombre}",
            metadata=metadata or {},
            tags=tags or [],
            propietario_id=propietario_id,
            copropiedad_id=copropiedad_id,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now(),
            fecha_vencimiento=fecha_vencimiento
        )
        
        self.documentos[doc_id] = documento
        
        # Agregar a carpeta si se especifica
        if carpeta_id and carpeta_id in self.carpetas:
            self.carpetas[carpeta_id].documentos.append(doc_id)
        
        # Registrar auditoría
        self._registrar_auditoria(
            doc_id, propietario_id, "Sistema",
            AccionAuditoria.CREAR,
            f"Documento creado: {titulo}"
        )
        
        return {
            "documento_id": doc_id,
            "codigo": codigo,
            "mensaje": "Documento creado exitosamente",
            "documento": self._documento_to_dict(documento)
        }
    
    def obtener_documento(
        self,
        documento_id: str,
        usuario_id: str,
        registrar_lectura: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Obtiene documento por ID"""
        if documento_id not in self.documentos:
            return None
        
        documento = self.documentos[documento_id]
        
        if registrar_lectura:
            self._registrar_auditoria(
                documento_id, usuario_id, "Usuario",
                AccionAuditoria.LEER,
                f"Documento consultado: {documento.titulo}"
            )
        
        return self._documento_to_dict(documento)
    
    def actualizar_documento(
        self,
        documento_id: str,
        archivo_contenido: bytes,
        usuario_id: str,
        comentario: str = ""
    ) -> Dict[str, Any]:
        """
        Actualiza documento creando nueva versión
        
        Mantiene historial de versiones anteriores
        """
        if documento_id not in self.documentos:
            return {"error": "Documento no encontrado"}
        
        documento = self.documentos[documento_id]
        
        # Guardar versión anterior
        documento.versiones_anteriores.append({
            "version": documento.version,
            "hash": documento.archivo_hash,
            "fecha": documento.fecha_modificacion.isoformat(),
            "modificado_por": usuario_id
        })
        
        # Actualizar documento
        documento.version += 1
        documento.archivo_hash = self._calcular_hash(archivo_contenido)
        documento.archivo_tamano_bytes = len(archivo_contenido)
        documento.fecha_modificacion = datetime.now()
        
        self._registrar_auditoria(
            documento_id, usuario_id, "Usuario",
            AccionAuditoria.MODIFICAR,
            f"Nueva versión {documento.version}: {comentario}"
        )
        
        return {
            "mensaje": "Documento actualizado",
            "version": documento.version,
            "documento": self._documento_to_dict(documento)
        }
    
    def cambiar_estado(
        self,
        documento_id: str,
        nuevo_estado: EstadoDocumento,
        usuario_id: str,
        comentario: str = ""
    ) -> Dict[str, Any]:
        """Cambia estado del documento"""
        if documento_id not in self.documentos:
            return {"error": "Documento no encontrado"}
        
        documento = self.documentos[documento_id]
        estado_anterior = documento.estado
        documento.estado = nuevo_estado
        documento.fecha_modificacion = datetime.now()
        
        self._registrar_auditoria(
            documento_id, usuario_id, "Usuario",
            AccionAuditoria.MODIFICAR,
            f"Estado cambiado de {estado_anterior.value} a {nuevo_estado.value}: {comentario}"
        )
        
        return {
            "mensaje": "Estado actualizado",
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": nuevo_estado.value
        }
    
    def buscar_documentos(
        self,
        query: str = "",
        tipo: Optional[TipoDocumento] = None,
        estado: Optional[EstadoDocumento] = None,
        copropiedad_id: Optional[str] = None,
        tags: List[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Búsqueda avanzada de documentos
        
        Soporta búsqueda por texto, tipo, estado, tags y fechas
        """
        resultados = list(self.documentos.values())
        
        # Filtrar por query (título, descripción, código)
        if query:
            query_lower = query.lower()
            resultados = [
                d for d in resultados
                if query_lower in d.titulo.lower()
                or query_lower in d.descripcion.lower()
                or query_lower in d.codigo.lower()
            ]
        
        # Filtrar por tipo
        if tipo:
            resultados = [d for d in resultados if d.tipo == tipo]
        
        # Filtrar por estado
        if estado:
            resultados = [d for d in resultados if d.estado == estado]
        
        # Filtrar por copropiedad
        if copropiedad_id:
            resultados = [d for d in resultados if d.copropiedad_id == copropiedad_id]
        
        # Filtrar por tags
        if tags:
            resultados = [
                d for d in resultados
                if any(tag in d.tags for tag in tags)
            ]
        
        # Filtrar por fechas
        if fecha_desde:
            resultados = [d for d in resultados if d.fecha_creacion.date() >= fecha_desde]
        if fecha_hasta:
            resultados = [d for d in resultados if d.fecha_creacion.date() <= fecha_hasta]
        
        total = len(resultados)
        resultados = resultados[offset:offset + limit]
        
        return {
            "documentos": [self._documento_to_dict(d) for d in resultados],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    # ========== GESTIÓN DE CARPETAS ==========
    
    def crear_carpeta(
        self,
        nombre: str,
        descripcion: str,
        propietario_id: str,
        carpeta_padre_id: Optional[str] = None,
        nivel_acceso: NivelAcceso = NivelAcceso.ADMINISTRACION,
        copropiedad_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea nueva carpeta"""
        carpeta_id = str(uuid.uuid4())[:8]
        
        carpeta = Carpeta(
            id=carpeta_id,
            nombre=nombre,
            descripcion=descripcion,
            carpeta_padre_id=carpeta_padre_id,
            nivel_acceso=nivel_acceso,
            propietario_id=propietario_id,
            copropiedad_id=copropiedad_id
        )
        
        self.carpetas[carpeta_id] = carpeta
        
        # Agregar a carpeta padre
        if carpeta_padre_id and carpeta_padre_id in self.carpetas:
            self.carpetas[carpeta_padre_id].subcarpetas.append(carpeta_id)
        
        return {
            "carpeta_id": carpeta_id,
            "mensaje": "Carpeta creada",
            "carpeta": self._carpeta_to_dict(carpeta)
        }
    
    def obtener_estructura_carpetas(
        self,
        carpeta_raiz_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene estructura jerárquica de carpetas"""
        
        def construir_arbol(carpeta_id: Optional[str]) -> List[Dict]:
            carpetas = [
                c for c in self.carpetas.values()
                if c.carpeta_padre_id == carpeta_id
            ]
            
            resultado = []
            for carpeta in carpetas:
                item = self._carpeta_to_dict(carpeta)
                item["subcarpetas"] = construir_arbol(carpeta.id)
                item["total_documentos"] = len(carpeta.documentos)
                resultado.append(item)
            
            return resultado
        
        return {
            "estructura": construir_arbol(carpeta_raiz_id),
            "total_carpetas": len(self.carpetas),
            "total_documentos": len(self.documentos)
        }
    
    # ========== FIRMA ELECTRÓNICA ==========
    
    def solicitar_firma(
        self,
        documento_id: str,
        firmantes: List[Dict[str, str]],
        tipo_firma: TipoFirma = TipoFirma.ELECTRONICA_SIMPLE,
        mensaje: str = ""
    ) -> Dict[str, Any]:
        """
        Solicita firma electrónica para documento
        
        Args:
            documento_id: ID del documento
            firmantes: Lista de firmantes con id, nombre, email, rut
            tipo_firma: Tipo de firma requerida
            mensaje: Mensaje para firmantes
        """
        if documento_id not in self.documentos:
            return {"error": "Documento no encontrado"}
        
        documento = self.documentos[documento_id]
        
        # Validar documento está en estado apropiado
        if documento.estado not in [EstadoDocumento.APROBADO, EstadoDocumento.REVISION]:
            return {"error": "Documento debe estar aprobado para firma"}
        
        solicitud_id = str(uuid.uuid4())[:8]
        
        # Crear registros de firma pendiente
        firmas_pendientes = []
        for firmante in firmantes:
            firma_id = str(uuid.uuid4())[:8]
            firmas_pendientes.append({
                "firma_id": firma_id,
                "firmante_id": firmante.get("id"),
                "firmante_nombre": firmante.get("nombre"),
                "firmante_email": firmante.get("email"),
                "firmante_rut": firmante.get("rut"),
                "estado": "pendiente",
                "tipo_firma": tipo_firma.value
            })
        
        return {
            "solicitud_id": solicitud_id,
            "documento_id": documento_id,
            "firmas_pendientes": firmas_pendientes,
            "mensaje": f"Solicitud de firma enviada a {len(firmantes)} firmantes",
            "tipo_firma": tipo_firma.value
        }
    
    def firmar_documento(
        self,
        documento_id: str,
        firmante_id: str,
        firmante_nombre: str,
        firmante_rut: str,
        tipo_firma: TipoFirma,
        firma_digital: str,
        ip_origen: str,
        ubicacion_gps: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Registra firma electrónica en documento
        
        Ley 19.799 sobre Firma Electrónica Chile
        """
        if documento_id not in self.documentos:
            return {"error": "Documento no encontrado"}
        
        documento = self.documentos[documento_id]
        
        firma_id = str(uuid.uuid4())[:8]
        firma = FirmaElectronica(
            id=firma_id,
            documento_id=documento_id,
            firmante_id=firmante_id,
            firmante_nombre=firmante_nombre,
            firmante_rut=firmante_rut,
            tipo_firma=tipo_firma,
            certificado_id=None,
            hash_documento=documento.archivo_hash,
            firma_digital=firma_digital,
            fecha_firma=datetime.now(),
            ip_origen=ip_origen,
            ubicacion_gps=ubicacion_gps
        )
        
        self.firmas[firma_id] = firma
        documento.firmas.append({
            "firma_id": firma_id,
            "firmante": firmante_nombre,
            "rut": firmante_rut,
            "fecha": firma.fecha_firma.isoformat()
        })
        documento.firmado = True
        documento.estado = EstadoDocumento.FIRMADO
        
        self._registrar_auditoria(
            documento_id, firmante_id, firmante_nombre,
            AccionAuditoria.FIRMAR,
            f"Documento firmado electrónicamente ({tipo_firma.value})"
        )
        
        return {
            "firma_id": firma_id,
            "mensaje": "Documento firmado exitosamente",
            "documento": self._documento_to_dict(documento),
            "firma": {
                "firmante": firmante_nombre,
                "rut": firmante_rut,
                "fecha": firma.fecha_firma.isoformat(),
                "tipo": tipo_firma.value,
                "valida": firma.valida
            }
        }
    
    def verificar_firma(
        self,
        documento_id: str,
        firma_id: str
    ) -> Dict[str, Any]:
        """Verifica validez de firma electrónica"""
        if firma_id not in self.firmas:
            return {"valida": False, "error": "Firma no encontrada"}
        
        firma = self.firmas[firma_id]
        documento = self.documentos.get(documento_id)
        
        if not documento:
            return {"valida": False, "error": "Documento no encontrado"}
        
        # Verificar que el hash coincida
        hash_actual = documento.archivo_hash
        hash_firmado = firma.hash_documento
        
        integridad = hash_actual == hash_firmado
        
        return {
            "valida": firma.valida and integridad,
            "firma": {
                "firmante": firma.firmante_nombre,
                "rut": firma.firmante_rut,
                "fecha": firma.fecha_firma.isoformat(),
                "tipo": firma.tipo_firma.value
            },
            "verificacion": {
                "integridad_documento": integridad,
                "hash_original": hash_firmado[:16] + "...",
                "hash_actual": hash_actual[:16] + "...",
                "documento_modificado": not integridad
            }
        }
    
    # ========== PLANTILLAS ==========
    
    def crear_plantilla(
        self,
        nombre: str,
        tipo: TipoDocumento,
        descripcion: str,
        contenido_html: str,
        variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crea plantilla de documento"""
        plantilla_id = str(uuid.uuid4())[:8]
        
        plantilla = PlantillaDocumento(
            id=plantilla_id,
            nombre=nombre,
            tipo=tipo,
            descripcion=descripcion,
            contenido_html=contenido_html,
            variables=variables
        )
        
        self.plantillas[plantilla_id] = plantilla
        
        return {
            "plantilla_id": plantilla_id,
            "mensaje": "Plantilla creada",
            "plantilla": {
                "id": plantilla_id,
                "nombre": nombre,
                "tipo": tipo.value,
                "variables": variables
            }
        }
    
    def generar_desde_plantilla(
        self,
        plantilla_id: str,
        valores: Dict[str, Any],
        propietario_id: str,
        copropiedad_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera documento desde plantilla
        
        Reemplaza variables con valores proporcionados
        """
        if plantilla_id not in self.plantillas:
            return {"error": "Plantilla no encontrada"}
        
        plantilla = self.plantillas[plantilla_id]
        
        # Reemplazar variables
        contenido = plantilla.contenido_html
        for variable in plantilla.variables:
            nombre_var = variable.get("nombre")
            valor = valores.get(nombre_var, variable.get("valor_default", ""))
            contenido = contenido.replace(f"{{{{{nombre_var}}}}}", str(valor))
        
        # Incrementar contador de usos
        plantilla.usos += 1
        
        # Crear documento
        titulo = valores.get("titulo", f"Documento desde {plantilla.nombre}")
        
        return self.crear_documento(
            tipo=plantilla.tipo,
            titulo=titulo,
            descripcion=f"Generado desde plantilla: {plantilla.nombre}",
            archivo_nombre=f"{titulo.replace(' ', '_')}.html",
            archivo_contenido=contenido.encode('utf-8'),
            propietario_id=propietario_id,
            copropiedad_id=copropiedad_id,
            metadata={"plantilla_id": plantilla_id, "valores": valores}
        )
    
    # ========== AUDITORÍA ==========
    
    def obtener_auditoria_documento(
        self,
        documento_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Obtiene historial de auditoría de un documento"""
        registros = [
            r for r in self.auditoria
            if r.documento_id == documento_id
        ]
        registros.sort(key=lambda x: x.fecha, reverse=True)
        
        return {
            "documento_id": documento_id,
            "registros": [
                {
                    "id": r.id,
                    "accion": r.accion.value,
                    "usuario": r.usuario_nombre,
                    "descripcion": r.descripcion,
                    "fecha": r.fecha.isoformat(),
                    "ip": r.ip_origen
                }
                for r in registros[:limit]
            ],
            "total": len(registros)
        }
    
    # ========== ESTADÍSTICAS ==========
    
    def obtener_estadisticas(
        self,
        copropiedad_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema documental"""
        documentos = list(self.documentos.values())
        
        if copropiedad_id:
            documentos = [d for d in documentos if d.copropiedad_id == copropiedad_id]
        
        # Por tipo
        por_tipo = {}
        for doc in documentos:
            tipo = doc.tipo.value
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        
        # Por estado
        por_estado = {}
        for doc in documentos:
            estado = doc.estado.value
            por_estado[estado] = por_estado.get(estado, 0) + 1
        
        # Documentos por vencer
        hoy = date.today()
        por_vencer = [
            d for d in documentos
            if d.fecha_vencimiento and d.fecha_vencimiento <= hoy + timedelta(days=30)
        ]
        
        # Espacio utilizado
        espacio_total = sum(d.archivo_tamano_bytes for d in documentos)
        
        return {
            "total_documentos": len(documentos),
            "total_carpetas": len(self.carpetas),
            "total_plantillas": len(self.plantillas),
            "por_tipo": por_tipo,
            "por_estado": por_estado,
            "documentos_firmados": len([d for d in documentos if d.firmado]),
            "documentos_por_vencer": len(por_vencer),
            "espacio_utilizado_mb": round(espacio_total / (1024 * 1024), 2),
            "registros_auditoria": len(self.auditoria)
        }
    
    # ========== HELPERS ==========
    
    def _documento_to_dict(self, doc: Documento) -> Dict[str, Any]:
        """Convierte documento a diccionario"""
        return {
            "id": doc.id,
            "codigo": doc.codigo,
            "tipo": doc.tipo.value,
            "titulo": doc.titulo,
            "descripcion": doc.descripcion,
            "estado": doc.estado.value,
            "version": doc.version,
            "nivel_acceso": doc.nivel_acceso.value,
            "archivo": {
                "nombre": doc.archivo_nombre,
                "extension": doc.archivo_extension,
                "tamano_bytes": doc.archivo_tamano_bytes,
                "url": doc.archivo_url
            },
            "tags": doc.tags,
            "firmado": doc.firmado,
            "firmas": doc.firmas,
            "versiones_anteriores": len(doc.versiones_anteriores),
            "fecha_creacion": doc.fecha_creacion.isoformat(),
            "fecha_modificacion": doc.fecha_modificacion.isoformat(),
            "fecha_vencimiento": doc.fecha_vencimiento.isoformat() if doc.fecha_vencimiento else None
        }
    
    def _carpeta_to_dict(self, carpeta: Carpeta) -> Dict[str, Any]:
        """Convierte carpeta a diccionario"""
        return {
            "id": carpeta.id,
            "nombre": carpeta.nombre,
            "descripcion": carpeta.descripcion,
            "nivel_acceso": carpeta.nivel_acceso.value,
            "carpeta_padre_id": carpeta.carpeta_padre_id,
            "documentos": carpeta.documentos,
            "fecha_creacion": carpeta.fecha_creacion.isoformat()
        }


# Instancia singleton
gestion_documental_service = GestionDocumentalService()
