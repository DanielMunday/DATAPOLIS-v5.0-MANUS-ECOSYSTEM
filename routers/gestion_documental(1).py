# =====================================================================
# DATAPOLIS v3.0 - ROUTER M11: GESTIÓN DOCUMENTAL
# API REST para gestión documentos, firmas electrónicas, versionamiento
# Ley 21.442 Copropiedades + Ley 19.799 Firma Electrónica Chile
# =====================================================================

from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field
import hashlib
import uuid

router = APIRouter(prefix="/gestion-documental", tags=["M11 - Gestión Documental"])

# =====================================================================
# ENUMS
# =====================================================================

class TipoDocumento(str, Enum):
    # Administrativos
    ACTA_ASAMBLEA = "acta_asamblea"
    ACTA_COMITE = "acta_comite"
    REGLAMENTO_COPROPIEDAD = "reglamento_copropiedad"
    ESTATUTOS = "estatutos"
    # Financieros
    BALANCE = "balance"
    ESTADO_CUENTA = "estado_cuenta"
    PRESUPUESTO = "presupuesto"
    LIQUIDACION = "liquidacion"
    FACTURA = "factura"
    BOLETA = "boleta"
    # Contratos
    CONTRATO_TRABAJO = "contrato_trabajo"
    CONTRATO_SERVICIOS = "contrato_servicios"
    CONTRATO_ARRIENDO = "contrato_arriendo"
    FINIQUITO = "finiquito"
    # Legales
    PODER_NOTARIAL = "poder_notarial"
    CERTIFICADO = "certificado"
    ESCRITURA = "escritura"
    # Operativos
    ORDEN_TRABAJO = "orden_trabajo"
    COTIZACION = "cotizacion"
    INFORME_TECNICO = "informe_tecnico"
    # Otros
    CORRESPONDENCIA = "correspondencia"
    OTRO = "otro"

class EstadoDocumento(str, Enum):
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    VIGENTE = "vigente"
    PENDIENTE_FIRMA = "pendiente_firma"
    FIRMADO = "firmado"
    ARCHIVADO = "archivado"
    ANULADO = "anulado"

class NivelAcceso(str, Enum):
    PUBLICO = "publico"              # Todos los copropietarios
    RESTRINGIDO = "restringido"      # Solo comité/admin
    CONFIDENCIAL = "confidencial"    # Solo admin/contador
    PRIVADO = "privado"              # Solo propietario
    SOLO_LECTURA = "solo_lectura"    # Sin descarga

class TipoFirma(str, Enum):
    SIMPLE = "simple"                # Click aceptar
    AVANZADA = "avanzada"            # Con certificado
    CALIFICADA = "calificada"        # e-Firma AC autorizada
    MANUSCRITA = "manuscrita"        # Escaneada

class AccionAuditoria(str, Enum):
    CREAR = "crear"
    LEER = "leer"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"
    DESCARGAR = "descargar"
    FIRMAR = "firmar"
    COMPARTIR = "compartir"
    CAMBIAR_ESTADO = "cambiar_estado"

class FormatoArchivo(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PNG = "png"
    JPG = "jpg"
    XML = "xml"

# =====================================================================
# MODELOS PYDANTIC
# =====================================================================

class ArchivoInfo(BaseModel):
    nombre: str
    extension: str
    tamano_bytes: int
    hash_sha256: str
    mime_type: str
    url_almacenamiento: Optional[str] = None

class MetadataDocumento(BaseModel):
    autor: Optional[str] = None
    palabras_clave: List[str] = []
    descripcion_corta: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    numero_paginas: Optional[int] = None
    origen: Optional[str] = None  # interno, externo, escaneo
    idioma: str = "es"

class VersionDocumento(BaseModel):
    version: int
    fecha: datetime
    usuario_id: str
    cambios: str
    hash_archivo: str

class FirmaRegistrada(BaseModel):
    id: str
    firmante_id: str
    firmante_nombre: str
    firmante_rut: str
    tipo_firma: TipoFirma
    fecha_firma: datetime
    hash_documento: str
    firma_digital: Optional[str] = None
    certificado_id: Optional[str] = None
    ip_origen: str
    ubicacion_gps: Optional[Dict[str, float]] = None
    valida: bool = True

class DocumentoCreate(BaseModel):
    tipo: TipoDocumento
    titulo: str
    descripcion: Optional[str] = None
    nivel_acceso: NivelAcceso = NivelAcceso.RESTRINGIDO
    copropiedad_id: str
    unidad_id: Optional[str] = None
    metadata: Optional[MetadataDocumento] = None
    tags: List[str] = []

class DocumentoResponse(BaseModel):
    id: str
    codigo: str
    tipo: TipoDocumento
    titulo: str
    descripcion: Optional[str]
    estado: EstadoDocumento
    version: int
    nivel_acceso: NivelAcceso
    archivo: Optional[ArchivoInfo]
    metadata: Optional[MetadataDocumento]
    tags: List[str]
    propietario_id: str
    copropiedad_id: str
    unidad_id: Optional[str]
    fecha_creacion: datetime
    fecha_modificacion: datetime
    firmado: bool
    firmas: List[FirmaRegistrada]
    versiones_anteriores: List[VersionDocumento]

class CarpetaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    carpeta_padre_id: Optional[str] = None
    nivel_acceso: NivelAcceso = NivelAcceso.RESTRINGIDO
    copropiedad_id: str

class CarpetaResponse(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str]
    ruta_completa: str
    carpeta_padre_id: Optional[str]
    nivel_acceso: NivelAcceso
    propietario_id: str
    copropiedad_id: str
    fecha_creacion: datetime
    cantidad_documentos: int
    cantidad_subcarpetas: int
    tamano_total_bytes: int

class SolicitudFirma(BaseModel):
    documento_id: str
    firmantes: List[Dict[str, str]]  # [{id, nombre, rut, email}]
    tipo_firma: TipoFirma = TipoFirma.SIMPLE
    mensaje: Optional[str] = None
    fecha_limite: Optional[date] = None
    orden_firmas: bool = False  # True = secuencial

class PlantillaCreate(BaseModel):
    nombre: str
    tipo: TipoDocumento
    descripcion: Optional[str] = None
    contenido_html: str
    variables: List[str]  # [{nombre}, {fecha}, etc.]
    copropiedad_id: Optional[str] = None  # None = global

class RegistroAuditoria(BaseModel):
    id: str
    documento_id: str
    usuario_id: str
    usuario_nombre: str
    accion: AccionAuditoria
    descripcion: str
    ip_origen: str
    fecha: datetime
    metadata: Optional[Dict[str, Any]] = None

# =====================================================================
# ALMACENAMIENTO SIMULADO
# =====================================================================

documentos_db: Dict[str, Dict] = {}
carpetas_db: Dict[str, Dict] = {}
plantillas_db: Dict[str, Dict] = {}
firmas_pendientes_db: Dict[str, Dict] = {}
auditoria_db: List[Dict] = []
contadores_codigo: Dict[str, int] = {}

# Prefijos códigos por tipo
PREFIJOS_CODIGO = {
    TipoDocumento.ACTA_ASAMBLEA: "ACT",
    TipoDocumento.ACTA_COMITE: "COM",
    TipoDocumento.REGLAMENTO_COPROPIEDAD: "REG",
    TipoDocumento.BALANCE: "BAL",
    TipoDocumento.ESTADO_CUENTA: "EDC",
    TipoDocumento.PRESUPUESTO: "PRE",
    TipoDocumento.LIQUIDACION: "LIQ",
    TipoDocumento.FACTURA: "FAC",
    TipoDocumento.BOLETA: "BOL",
    TipoDocumento.CONTRATO_TRABAJO: "CTR",
    TipoDocumento.CONTRATO_SERVICIOS: "CSV",
    TipoDocumento.CONTRATO_ARRIENDO: "CAR",
    TipoDocumento.FINIQUITO: "FIN",
    TipoDocumento.ORDEN_TRABAJO: "OTR",
    TipoDocumento.COTIZACION: "COT",
    TipoDocumento.INFORME_TECNICO: "INF",
    TipoDocumento.CORRESPONDENCIA: "COR",
    TipoDocumento.OTRO: "DOC",
}

# Carpetas estándar Ley 21.442
CARPETAS_ESTANDAR = [
    {"nombre": "Actas", "descripcion": "Actas de asambleas y comités"},
    {"nombre": "Contratos", "descripcion": "Contratos laborales y de servicios"},
    {"nombre": "Financiero", "descripcion": "Balances, presupuestos, estados de cuenta"},
    {"nombre": "Legal", "descripcion": "Documentos legales y notariales"},
    {"nombre": "Operacional", "descripcion": "Órdenes de trabajo, informes técnicos"},
    {"nombre": "Correspondencia", "descripcion": "Comunicaciones enviadas y recibidas"},
    {"nombre": "Archivo Histórico", "descripcion": "Documentos archivados"},
]

# =====================================================================
# FUNCIONES AUXILIARES
# =====================================================================

def generar_codigo_documento(tipo: TipoDocumento) -> str:
    """Genera código único para documento"""
    prefijo = PREFIJOS_CODIGO.get(tipo, "DOC")
    fecha = datetime.now().strftime("%Y%m")
    key = f"{prefijo}_{fecha}"
    
    if key not in contadores_codigo:
        contadores_codigo[key] = 0
    contadores_codigo[key] += 1
    
    return f"{prefijo}-{fecha}-{contadores_codigo[key]:04d}"

def calcular_hash_archivo(contenido: bytes) -> str:
    """Calcula SHA-256 del contenido"""
    return hashlib.sha256(contenido).hexdigest()

def registrar_auditoria(
    documento_id: str,
    usuario_id: str,
    usuario_nombre: str,
    accion: AccionAuditoria,
    descripcion: str,
    ip_origen: str = "127.0.0.1",
    metadata: Optional[Dict] = None
):
    """Registra acción en auditoría"""
    registro = {
        "id": str(uuid.uuid4()),
        "documento_id": documento_id,
        "usuario_id": usuario_id,
        "usuario_nombre": usuario_nombre,
        "accion": accion,
        "descripcion": descripcion,
        "ip_origen": ip_origen,
        "fecha": datetime.now(),
        "metadata": metadata or {}
    }
    auditoria_db.append(registro)
    return registro

def validar_transicion_estado(actual: EstadoDocumento, nuevo: EstadoDocumento) -> bool:
    """Valida transiciones de estado permitidas"""
    transiciones_permitidas = {
        EstadoDocumento.BORRADOR: [EstadoDocumento.EN_REVISION, EstadoDocumento.ANULADO],
        EstadoDocumento.EN_REVISION: [EstadoDocumento.BORRADOR, EstadoDocumento.APROBADO, EstadoDocumento.ANULADO],
        EstadoDocumento.APROBADO: [EstadoDocumento.VIGENTE, EstadoDocumento.PENDIENTE_FIRMA, EstadoDocumento.ANULADO],
        EstadoDocumento.VIGENTE: [EstadoDocumento.ARCHIVADO, EstadoDocumento.PENDIENTE_FIRMA, EstadoDocumento.ANULADO],
        EstadoDocumento.PENDIENTE_FIRMA: [EstadoDocumento.FIRMADO, EstadoDocumento.ANULADO],
        EstadoDocumento.FIRMADO: [EstadoDocumento.ARCHIVADO],
        EstadoDocumento.ARCHIVADO: [],  # Estado final
        EstadoDocumento.ANULADO: [],    # Estado final
    }
    return nuevo in transiciones_permitidas.get(actual, [])

# =====================================================================
# ENDPOINTS - DOCUMENTOS
# =====================================================================

@router.post("/documentos", response_model=Dict[str, Any])
async def crear_documento(
    datos: DocumentoCreate,
    usuario_id: str = Query(..., description="ID usuario creador"),
    usuario_nombre: str = Query(..., description="Nombre usuario")
):
    """
    Crea nuevo documento en el sistema.
    
    - Genera código único automático
    - Estado inicial: BORRADOR
    - Registra auditoría
    """
    doc_id = str(uuid.uuid4())
    codigo = generar_codigo_documento(datos.tipo)
    ahora = datetime.now()
    
    documento = {
        "id": doc_id,
        "codigo": codigo,
        "tipo": datos.tipo,
        "titulo": datos.titulo,
        "descripcion": datos.descripcion,
        "estado": EstadoDocumento.BORRADOR,
        "version": 1,
        "nivel_acceso": datos.nivel_acceso,
        "archivo": None,
        "metadata": datos.metadata.dict() if datos.metadata else None,
        "tags": datos.tags,
        "propietario_id": usuario_id,
        "copropiedad_id": datos.copropiedad_id,
        "unidad_id": datos.unidad_id,
        "fecha_creacion": ahora,
        "fecha_modificacion": ahora,
        "firmado": False,
        "firmas": [],
        "versiones_anteriores": []
    }
    
    documentos_db[doc_id] = documento
    
    registrar_auditoria(
        documento_id=doc_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.CREAR,
        descripcion=f"Documento creado: {datos.titulo}"
    )
    
    return {
        "success": True,
        "mensaje": "Documento creado exitosamente",
        "documento": documento
    }

@router.get("/documentos", response_model=Dict[str, Any])
async def listar_documentos(
    copropiedad_id: str = Query(..., description="ID copropiedad"),
    tipo: Optional[TipoDocumento] = None,
    estado: Optional[EstadoDocumento] = None,
    texto_busqueda: Optional[str] = None,
    tags: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    nivel_acceso: Optional[NivelAcceso] = None,
    solo_firmados: bool = False,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100)
):
    """
    Lista documentos con filtros avanzados.
    
    - Búsqueda por texto en título y descripción
    - Filtros por tipo, estado, tags, fechas
    - Paginación incluida
    """
    documentos = list(documentos_db.values())
    
    # Filtrar por copropiedad
    documentos = [d for d in documentos if d["copropiedad_id"] == copropiedad_id]
    
    # Aplicar filtros
    if tipo:
        documentos = [d for d in documentos if d["tipo"] == tipo]
    
    if estado:
        documentos = [d for d in documentos if d["estado"] == estado]
    
    if texto_busqueda:
        texto_lower = texto_busqueda.lower()
        documentos = [d for d in documentos 
                     if texto_lower in d["titulo"].lower() 
                     or (d["descripcion"] and texto_lower in d["descripcion"].lower())]
    
    if tags:
        tags_list = [t.strip() for t in tags.split(",")]
        documentos = [d for d in documentos 
                     if any(tag in d.get("tags", []) for tag in tags_list)]
    
    if fecha_desde:
        documentos = [d for d in documentos 
                     if d["fecha_creacion"].date() >= fecha_desde]
    
    if fecha_hasta:
        documentos = [d for d in documentos 
                     if d["fecha_creacion"].date() <= fecha_hasta]
    
    if nivel_acceso:
        documentos = [d for d in documentos if d["nivel_acceso"] == nivel_acceso]
    
    if solo_firmados:
        documentos = [d for d in documentos if d["firmado"]]
    
    # Ordenar por fecha más reciente
    documentos.sort(key=lambda x: x["fecha_modificacion"], reverse=True)
    
    # Paginación
    total = len(documentos)
    inicio = (pagina - 1) * por_pagina
    documentos_pagina = documentos[inicio:inicio + por_pagina]
    
    return {
        "success": True,
        "documentos": documentos_pagina,
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "paginas": (total + por_pagina - 1) // por_pagina
        },
        "resumen": {
            "total_documentos": total,
            "por_tipo": {},
            "por_estado": {}
        }
    }

@router.get("/documentos/{documento_id}", response_model=Dict[str, Any])
async def obtener_documento(
    documento_id: str,
    usuario_id: str = Query(..., description="ID usuario"),
    usuario_nombre: str = Query("Sistema", description="Nombre usuario"),
    registrar_lectura: bool = True
):
    """
    Obtiene documento por ID.
    
    - Registra lectura en auditoría opcional
    - Incluye historial de versiones
    """
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    
    if registrar_lectura:
        registrar_auditoria(
            documento_id=documento_id,
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            accion=AccionAuditoria.LEER,
            descripcion=f"Documento visualizado"
        )
    
    return {
        "success": True,
        "documento": documento
    }

@router.put("/documentos/{documento_id}", response_model=Dict[str, Any])
async def actualizar_documento(
    documento_id: str,
    titulo: Optional[str] = Body(None),
    descripcion: Optional[str] = Body(None),
    tags: Optional[List[str]] = Body(None),
    metadata: Optional[Dict] = Body(None),
    nivel_acceso: Optional[NivelAcceso] = Body(None),
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Actualiza documento existente.
    
    - Incrementa versión automáticamente
    - Guarda versión anterior en historial
    - Registra auditoría
    """
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    ahora = datetime.now()
    
    # Guardar versión anterior
    version_anterior = {
        "version": documento["version"],
        "fecha": documento["fecha_modificacion"],
        "usuario_id": usuario_id,
        "cambios": "Actualización de documento",
        "hash_archivo": documento["archivo"]["hash_sha256"] if documento["archivo"] else None
    }
    documento["versiones_anteriores"].append(version_anterior)
    
    # Aplicar cambios
    cambios = []
    if titulo:
        documento["titulo"] = titulo
        cambios.append("título")
    if descripcion is not None:
        documento["descripcion"] = descripcion
        cambios.append("descripción")
    if tags is not None:
        documento["tags"] = tags
        cambios.append("tags")
    if metadata:
        documento["metadata"] = metadata
        cambios.append("metadata")
    if nivel_acceso:
        documento["nivel_acceso"] = nivel_acceso
        cambios.append("nivel_acceso")
    
    documento["version"] += 1
    documento["fecha_modificacion"] = ahora
    
    registrar_auditoria(
        documento_id=documento_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.ACTUALIZAR,
        descripcion=f"Campos actualizados: {', '.join(cambios)}",
        metadata={"version": documento["version"]}
    )
    
    return {
        "success": True,
        "mensaje": "Documento actualizado",
        "documento": documento
    }

@router.post("/documentos/{documento_id}/cambiar-estado", response_model=Dict[str, Any])
async def cambiar_estado_documento(
    documento_id: str,
    nuevo_estado: EstadoDocumento = Body(..., embed=True),
    comentario: Optional[str] = Body(None, embed=True),
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Cambia estado del documento.
    
    Estados posibles:
    - BORRADOR → EN_REVISION, ANULADO
    - EN_REVISION → BORRADOR, APROBADO, ANULADO  
    - APROBADO → VIGENTE, PENDIENTE_FIRMA, ANULADO
    - VIGENTE → ARCHIVADO, PENDIENTE_FIRMA, ANULADO
    - PENDIENTE_FIRMA → FIRMADO, ANULADO
    - FIRMADO → ARCHIVADO
    """
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    estado_actual = documento["estado"]
    
    if not validar_transicion_estado(estado_actual, nuevo_estado):
        raise HTTPException(
            status_code=400,
            detail=f"Transición no permitida: {estado_actual} → {nuevo_estado}"
        )
    
    estado_anterior = documento["estado"]
    documento["estado"] = nuevo_estado
    documento["fecha_modificacion"] = datetime.now()
    
    registrar_auditoria(
        documento_id=documento_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.CAMBIAR_ESTADO,
        descripcion=f"Estado cambiado: {estado_anterior} → {nuevo_estado}",
        metadata={"comentario": comentario} if comentario else None
    )
    
    return {
        "success": True,
        "mensaje": f"Estado cambiado a {nuevo_estado}",
        "documento": documento
    }

@router.delete("/documentos/{documento_id}", response_model=Dict[str, Any])
async def eliminar_documento(
    documento_id: str,
    motivo: str = Query(..., description="Motivo eliminación"),
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Elimina (anula) documento.
    
    - No elimina físicamente, cambia estado a ANULADO
    - Documentos firmados no pueden eliminarse
    """
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    
    if documento["firmado"]:
        raise HTTPException(
            status_code=400,
            detail="Documentos firmados no pueden eliminarse"
        )
    
    documento["estado"] = EstadoDocumento.ANULADO
    documento["fecha_modificacion"] = datetime.now()
    
    registrar_auditoria(
        documento_id=documento_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.ELIMINAR,
        descripcion=f"Documento anulado. Motivo: {motivo}"
    )
    
    return {
        "success": True,
        "mensaje": "Documento anulado exitosamente"
    }

# =====================================================================
# ENDPOINTS - CARPETAS
# =====================================================================

@router.post("/carpetas", response_model=Dict[str, Any])
async def crear_carpeta(
    datos: CarpetaCreate,
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Crea nueva carpeta.
    
    - Soporta jerarquía (subcarpetas)
    - Genera ruta completa automática
    """
    carpeta_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Calcular ruta completa
    ruta = datos.nombre
    if datos.carpeta_padre_id:
        if datos.carpeta_padre_id not in carpetas_db:
            raise HTTPException(status_code=404, detail="Carpeta padre no encontrada")
        padre = carpetas_db[datos.carpeta_padre_id]
        ruta = f"{padre['ruta_completa']}/{datos.nombre}"
    
    carpeta = {
        "id": carpeta_id,
        "nombre": datos.nombre,
        "descripcion": datos.descripcion,
        "ruta_completa": ruta,
        "carpeta_padre_id": datos.carpeta_padre_id,
        "nivel_acceso": datos.nivel_acceso,
        "propietario_id": usuario_id,
        "copropiedad_id": datos.copropiedad_id,
        "fecha_creacion": ahora
    }
    
    carpetas_db[carpeta_id] = carpeta
    
    return {
        "success": True,
        "mensaje": "Carpeta creada",
        "carpeta": carpeta
    }

@router.get("/carpetas", response_model=Dict[str, Any])
async def listar_carpetas(
    copropiedad_id: str = Query(...),
    carpeta_padre_id: Optional[str] = None
):
    """Lista carpetas de una copropiedad"""
    carpetas = [c for c in carpetas_db.values() 
               if c["copropiedad_id"] == copropiedad_id 
               and c.get("carpeta_padre_id") == carpeta_padre_id]
    
    # Agregar contadores
    for carpeta in carpetas:
        carpeta["cantidad_documentos"] = len([
            d for d in documentos_db.values() 
            if d.get("carpeta_id") == carpeta["id"]
        ])
        carpeta["cantidad_subcarpetas"] = len([
            c for c in carpetas_db.values() 
            if c.get("carpeta_padre_id") == carpeta["id"]
        ])
    
    return {
        "success": True,
        "carpetas": carpetas
    }

@router.get("/carpetas/estructura", response_model=Dict[str, Any])
async def obtener_estructura_carpetas(copropiedad_id: str = Query(...)):
    """
    Obtiene árbol jerárquico completo de carpetas.
    
    Retorna estructura anidada con documentos por carpeta.
    """
    def construir_arbol(padre_id: Optional[str] = None) -> List[Dict]:
        hijos = [c for c in carpetas_db.values() 
                if c["copropiedad_id"] == copropiedad_id 
                and c.get("carpeta_padre_id") == padre_id]
        
        resultado = []
        for carpeta in hijos:
            nodo = {
                **carpeta,
                "documentos": [d for d in documentos_db.values() 
                              if d.get("carpeta_id") == carpeta["id"]],
                "subcarpetas": construir_arbol(carpeta["id"])
            }
            resultado.append(nodo)
        
        return resultado
    
    return {
        "success": True,
        "estructura": construir_arbol()
    }

@router.post("/carpetas/inicializar-estandar", response_model=Dict[str, Any])
async def inicializar_carpetas_estandar(
    copropiedad_id: str = Query(...),
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Crea estructura de carpetas estándar según Ley 21.442.
    
    Carpetas: Actas, Contratos, Financiero, Legal, Operacional,
    Correspondencia, Archivo Histórico
    """
    carpetas_creadas = []
    
    for carpeta_info in CARPETAS_ESTANDAR:
        carpeta_id = str(uuid.uuid4())
        carpeta = {
            "id": carpeta_id,
            "nombre": carpeta_info["nombre"],
            "descripcion": carpeta_info["descripcion"],
            "ruta_completa": carpeta_info["nombre"],
            "carpeta_padre_id": None,
            "nivel_acceso": NivelAcceso.RESTRINGIDO,
            "propietario_id": usuario_id,
            "copropiedad_id": copropiedad_id,
            "fecha_creacion": datetime.now()
        }
        carpetas_db[carpeta_id] = carpeta
        carpetas_creadas.append(carpeta)
    
    return {
        "success": True,
        "mensaje": f"{len(carpetas_creadas)} carpetas estándar creadas",
        "carpetas": carpetas_creadas
    }

# =====================================================================
# ENDPOINTS - FIRMAS ELECTRÓNICAS
# =====================================================================

@router.post("/firmas/solicitar", response_model=Dict[str, Any])
async def solicitar_firma(
    solicitud: SolicitudFirma,
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Solicita firma electrónica a uno o más firmantes.
    
    - Cambia estado documento a PENDIENTE_FIRMA
    - Genera solicitudes individuales por firmante
    - Soporta firmas secuenciales (orden)
    """
    if solicitud.documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[solicitud.documento_id]
    
    # Validar estado
    if documento["estado"] not in [EstadoDocumento.APROBADO, EstadoDocumento.VIGENTE]:
        raise HTTPException(
            status_code=400,
            detail="Solo documentos aprobados o vigentes pueden solicitar firma"
        )
    
    solicitud_id = str(uuid.uuid4())
    ahora = datetime.now()
    
    # Crear solicitudes por firmante
    firmas_solicitadas = []
    for i, firmante in enumerate(solicitud.firmantes):
        firma_id = str(uuid.uuid4())
        firma_solicitud = {
            "id": firma_id,
            "solicitud_id": solicitud_id,
            "documento_id": solicitud.documento_id,
            "firmante": firmante,
            "tipo_firma": solicitud.tipo_firma,
            "orden": i + 1 if solicitud.orden_firmas else 0,
            "estado": "pendiente",
            "fecha_solicitud": ahora,
            "fecha_limite": solicitud.fecha_limite,
            "mensaje": solicitud.mensaje
        }
        firmas_pendientes_db[firma_id] = firma_solicitud
        firmas_solicitadas.append(firma_solicitud)
    
    # Cambiar estado documento
    documento["estado"] = EstadoDocumento.PENDIENTE_FIRMA
    documento["fecha_modificacion"] = ahora
    
    registrar_auditoria(
        documento_id=solicitud.documento_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.COMPARTIR,
        descripcion=f"Firma solicitada a {len(solicitud.firmantes)} firmante(s)",
        metadata={"firmantes": [f["nombre"] for f in solicitud.firmantes]}
    )
    
    return {
        "success": True,
        "mensaje": f"Firma solicitada a {len(solicitud.firmantes)} firmante(s)",
        "solicitud_id": solicitud_id,
        "firmas_solicitadas": firmas_solicitadas
    }

@router.post("/firmas/{firma_id}/firmar", response_model=Dict[str, Any])
async def firmar_documento(
    firma_id: str,
    firmante_id: str = Query(...),
    firmante_nombre: str = Query(...),
    firmante_rut: str = Query(...),
    firma_digital: Optional[str] = Body(None, embed=True),
    certificado_id: Optional[str] = Body(None, embed=True),
    ip_origen: str = Query("127.0.0.1"),
    ubicacion_lat: Optional[float] = Query(None),
    ubicacion_lon: Optional[float] = Query(None)
):
    """
    Registra firma electrónica según Ley 19.799.
    
    - Calcula hash del documento
    - Registra firma digital, IP, ubicación GPS
    - Si todas las firmas completas, cambia estado a FIRMADO
    """
    if firma_id not in firmas_pendientes_db:
        raise HTTPException(status_code=404, detail="Solicitud de firma no encontrada")
    
    solicitud_firma = firmas_pendientes_db[firma_id]
    documento_id = solicitud_firma["documento_id"]
    
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    ahora = datetime.now()
    
    # Calcular hash documento (simulado)
    hash_documento = hashlib.sha256(
        f"{documento['id']}{documento['version']}".encode()
    ).hexdigest()
    
    # Crear registro de firma
    firma = {
        "id": firma_id,
        "firmante_id": firmante_id,
        "firmante_nombre": firmante_nombre,
        "firmante_rut": firmante_rut,
        "tipo_firma": solicitud_firma["tipo_firma"],
        "fecha_firma": ahora,
        "hash_documento": hash_documento,
        "firma_digital": firma_digital,
        "certificado_id": certificado_id,
        "ip_origen": ip_origen,
        "ubicacion_gps": {"lat": ubicacion_lat, "lon": ubicacion_lon} if ubicacion_lat else None,
        "valida": True
    }
    
    # Agregar firma al documento
    documento["firmas"].append(firma)
    documento["fecha_modificacion"] = ahora
    
    # Actualizar solicitud
    solicitud_firma["estado"] = "firmado"
    solicitud_firma["fecha_firma"] = ahora
    
    # Verificar si todas las firmas están completas
    solicitud_id = solicitud_firma["solicitud_id"]
    firmas_misma_solicitud = [f for f in firmas_pendientes_db.values() 
                             if f["solicitud_id"] == solicitud_id]
    todas_firmadas = all(f["estado"] == "firmado" for f in firmas_misma_solicitud)
    
    if todas_firmadas:
        documento["firmado"] = True
        documento["estado"] = EstadoDocumento.FIRMADO
    
    registrar_auditoria(
        documento_id=documento_id,
        usuario_id=firmante_id,
        usuario_nombre=firmante_nombre,
        accion=AccionAuditoria.FIRMAR,
        descripcion=f"Documento firmado electrónicamente ({solicitud_firma['tipo_firma']})",
        ip_origen=ip_origen,
        metadata={
            "hash": hash_documento,
            "rut_firmante": firmante_rut,
            "tipo_firma": solicitud_firma["tipo_firma"]
        }
    )
    
    return {
        "success": True,
        "mensaje": "Documento firmado exitosamente",
        "firma": firma,
        "documento_completamente_firmado": todas_firmadas
    }

@router.get("/firmas/pendientes", response_model=Dict[str, Any])
async def listar_firmas_pendientes(
    firmante_id: Optional[str] = None,
    documento_id: Optional[str] = None
):
    """Lista firmas pendientes filtradas"""
    firmas = list(firmas_pendientes_db.values())
    
    firmas = [f for f in firmas if f["estado"] == "pendiente"]
    
    if firmante_id:
        firmas = [f for f in firmas if f["firmante"]["id"] == firmante_id]
    
    if documento_id:
        firmas = [f for f in firmas if f["documento_id"] == documento_id]
    
    return {
        "success": True,
        "firmas_pendientes": firmas,
        "total": len(firmas)
    }

@router.get("/firmas/verificar/{documento_id}", response_model=Dict[str, Any])
async def verificar_firmas_documento(documento_id: str):
    """
    Verifica integridad de firmas de un documento.
    
    - Compara hash actual vs hash firmado
    - Detecta modificaciones post-firma
    """
    if documento_id not in documentos_db:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    documento = documentos_db[documento_id]
    
    if not documento["firmas"]:
        return {
            "success": True,
            "documento_id": documento_id,
            "tiene_firmas": False,
            "mensaje": "Documento sin firmas"
        }
    
    # Calcular hash actual
    hash_actual = hashlib.sha256(
        f"{documento['id']}{documento['version']}".encode()
    ).hexdigest()
    
    verificaciones = []
    documento_modificado = False
    
    for firma in documento["firmas"]:
        hash_coincide = firma["hash_documento"] == hash_actual
        if not hash_coincide:
            documento_modificado = True
        
        verificaciones.append({
            "firmante": firma["firmante_nombre"],
            "rut": firma["firmante_rut"],
            "fecha_firma": firma["fecha_firma"],
            "tipo_firma": firma["tipo_firma"],
            "hash_original": firma["hash_documento"],
            "hash_actual": hash_actual,
            "integridad_verificada": hash_coincide,
            "firma_valida": firma["valida"]
        })
    
    return {
        "success": True,
        "documento_id": documento_id,
        "tiene_firmas": True,
        "total_firmas": len(documento["firmas"]),
        "documento_modificado_post_firma": documento_modificado,
        "verificaciones": verificaciones,
        "alerta": "⚠️ DOCUMENTO MODIFICADO DESPUÉS DE FIRMAR" if documento_modificado else None
    }

# =====================================================================
# ENDPOINTS - PLANTILLAS
# =====================================================================

@router.post("/plantillas", response_model=Dict[str, Any])
async def crear_plantilla(
    plantilla: PlantillaCreate,
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Crea plantilla de documento con variables.
    
    Variables formato: {variable_nombre}
    Ejemplo: {nombre_copropiedad}, {fecha_asamblea}, {numero_acta}
    """
    plantilla_id = str(uuid.uuid4())
    
    plantilla_data = {
        "id": plantilla_id,
        "nombre": plantilla.nombre,
        "tipo": plantilla.tipo,
        "descripcion": plantilla.descripcion,
        "contenido_html": plantilla.contenido_html,
        "variables": plantilla.variables,
        "copropiedad_id": plantilla.copropiedad_id,
        "activa": True,
        "usos": 0,
        "fecha_creacion": datetime.now(),
        "creador_id": usuario_id,
        "creador_nombre": usuario_nombre
    }
    
    plantillas_db[plantilla_id] = plantilla_data
    
    return {
        "success": True,
        "mensaje": "Plantilla creada",
        "plantilla": plantilla_data
    }

@router.get("/plantillas", response_model=Dict[str, Any])
async def listar_plantillas(
    copropiedad_id: Optional[str] = None,
    tipo: Optional[TipoDocumento] = None,
    solo_activas: bool = True
):
    """Lista plantillas disponibles"""
    plantillas = list(plantillas_db.values())
    
    if copropiedad_id:
        plantillas = [p for p in plantillas 
                     if p["copropiedad_id"] == copropiedad_id or p["copropiedad_id"] is None]
    
    if tipo:
        plantillas = [p for p in plantillas if p["tipo"] == tipo]
    
    if solo_activas:
        plantillas = [p for p in plantillas if p["activa"]]
    
    return {
        "success": True,
        "plantillas": plantillas,
        "total": len(plantillas)
    }

@router.post("/plantillas/{plantilla_id}/generar", response_model=Dict[str, Any])
async def generar_desde_plantilla(
    plantilla_id: str,
    variables: Dict[str, str] = Body(...),
    titulo: str = Body(...),
    copropiedad_id: str = Body(...),
    usuario_id: str = Query(...),
    usuario_nombre: str = Query(...)
):
    """
    Genera documento desde plantilla reemplazando variables.
    
    Enviar diccionario con valores para cada variable definida.
    """
    if plantilla_id not in plantillas_db:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    plantilla = plantillas_db[plantilla_id]
    
    # Validar variables requeridas
    variables_faltantes = [v for v in plantilla["variables"] if v not in variables]
    if variables_faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Variables faltantes: {', '.join(variables_faltantes)}"
        )
    
    # Generar contenido reemplazando variables
    contenido = plantilla["contenido_html"]
    for var, valor in variables.items():
        contenido = contenido.replace(f"{{{var}}}", str(valor))
    
    # Crear documento
    doc_id = str(uuid.uuid4())
    codigo = generar_codigo_documento(plantilla["tipo"])
    ahora = datetime.now()
    
    documento = {
        "id": doc_id,
        "codigo": codigo,
        "tipo": plantilla["tipo"],
        "titulo": titulo,
        "descripcion": f"Generado desde plantilla: {plantilla['nombre']}",
        "estado": EstadoDocumento.BORRADOR,
        "version": 1,
        "nivel_acceso": NivelAcceso.RESTRINGIDO,
        "archivo": None,
        "metadata": {"plantilla_id": plantilla_id, "variables": variables},
        "tags": ["generado-plantilla"],
        "propietario_id": usuario_id,
        "copropiedad_id": copropiedad_id,
        "unidad_id": None,
        "fecha_creacion": ahora,
        "fecha_modificacion": ahora,
        "firmado": False,
        "firmas": [],
        "versiones_anteriores": [],
        "contenido_generado": contenido
    }
    
    documentos_db[doc_id] = documento
    
    # Incrementar usos plantilla
    plantilla["usos"] += 1
    
    registrar_auditoria(
        documento_id=doc_id,
        usuario_id=usuario_id,
        usuario_nombre=usuario_nombre,
        accion=AccionAuditoria.CREAR,
        descripcion=f"Documento generado desde plantilla: {plantilla['nombre']}"
    )
    
    return {
        "success": True,
        "mensaje": "Documento generado desde plantilla",
        "documento": documento,
        "contenido_html": contenido
    }

# =====================================================================
# ENDPOINTS - AUDITORÍA
# =====================================================================

@router.get("/auditoria/{documento_id}", response_model=Dict[str, Any])
async def obtener_auditoria_documento(
    documento_id: str,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    accion: Optional[AccionAuditoria] = None
):
    """
    Obtiene historial completo de auditoría de un documento.
    
    Muestra todas las acciones: crear, leer, actualizar, firmar, etc.
    """
    registros = [r for r in auditoria_db if r["documento_id"] == documento_id]
    
    if fecha_desde:
        registros = [r for r in registros if r["fecha"].date() >= fecha_desde]
    
    if fecha_hasta:
        registros = [r for r in registros if r["fecha"].date() <= fecha_hasta]
    
    if accion:
        registros = [r for r in registros if r["accion"] == accion]
    
    # Ordenar por fecha descendente
    registros.sort(key=lambda x: x["fecha"], reverse=True)
    
    return {
        "success": True,
        "documento_id": documento_id,
        "registros": registros,
        "total": len(registros)
    }

@router.get("/auditoria", response_model=Dict[str, Any])
async def obtener_auditoria_general(
    copropiedad_id: str = Query(...),
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    usuario_id: Optional[str] = None,
    accion: Optional[AccionAuditoria] = None,
    limite: int = Query(100, le=500)
):
    """Obtiene auditoría general de la copropiedad"""
    # Obtener documentos de la copropiedad
    docs_copropiedad = [d["id"] for d in documentos_db.values() 
                       if d["copropiedad_id"] == copropiedad_id]
    
    registros = [r for r in auditoria_db if r["documento_id"] in docs_copropiedad]
    
    if fecha_desde:
        registros = [r for r in registros if r["fecha"].date() >= fecha_desde]
    
    if fecha_hasta:
        registros = [r for r in registros if r["fecha"].date() <= fecha_hasta]
    
    if usuario_id:
        registros = [r for r in registros if r["usuario_id"] == usuario_id]
    
    if accion:
        registros = [r for r in registros if r["accion"] == accion]
    
    registros.sort(key=lambda x: x["fecha"], reverse=True)
    registros = registros[:limite]
    
    return {
        "success": True,
        "registros": registros,
        "total": len(registros)
    }

# =====================================================================
# ENDPOINTS - ESTADÍSTICAS
# =====================================================================

@router.get("/estadisticas", response_model=Dict[str, Any])
async def obtener_estadisticas(copropiedad_id: str = Query(...)):
    """
    Obtiene estadísticas completas de gestión documental.
    
    Incluye: totales, por tipo, por estado, firmados, espacio, etc.
    """
    documentos = [d for d in documentos_db.values() 
                 if d["copropiedad_id"] == copropiedad_id]
    
    # Por tipo
    por_tipo = {}
    for doc in documentos:
        tipo = doc["tipo"]
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
    
    # Por estado
    por_estado = {}
    for doc in documentos:
        estado = doc["estado"]
        por_estado[estado] = por_estado.get(estado, 0) + 1
    
    # Firmados
    firmados = len([d for d in documentos if d["firmado"]])
    
    # Por vencer (documentos con fecha_vencimiento en metadata)
    por_vencer = 0
    hoy = date.today()
    for doc in documentos:
        if doc.get("metadata") and doc["metadata"].get("fecha_vencimiento"):
            fecha_venc = doc["metadata"]["fecha_vencimiento"]
            if isinstance(fecha_venc, str):
                fecha_venc = date.fromisoformat(fecha_venc)
            if fecha_venc <= hoy + timedelta(days=30):
                por_vencer += 1
    
    # Espacio utilizado
    espacio_bytes = sum(
        doc["archivo"]["tamano_bytes"] 
        for doc in documentos 
        if doc.get("archivo")
    )
    
    # Actividad reciente
    actividad_30_dias = len([
        r for r in auditoria_db 
        if r["fecha"].date() >= hoy - timedelta(days=30)
    ])
    
    return {
        "success": True,
        "estadisticas": {
            "total_documentos": len(documentos),
            "por_tipo": por_tipo,
            "por_estado": por_estado,
            "documentos_firmados": firmados,
            "documentos_por_vencer": por_vencer,
            "espacio_utilizado_bytes": espacio_bytes,
            "espacio_utilizado_mb": round(espacio_bytes / (1024 * 1024), 2),
            "actividad_30_dias": actividad_30_dias,
            "total_carpetas": len([c for c in carpetas_db.values() 
                                  if c["copropiedad_id"] == copropiedad_id]),
            "total_plantillas": len([p for p in plantillas_db.values() 
                                    if p.get("copropiedad_id") == copropiedad_id or p.get("copropiedad_id") is None])
        }
    }

# =====================================================================
# ENDPOINTS - BÚSQUEDA AVANZADA
# =====================================================================

@router.get("/buscar", response_model=Dict[str, Any])
async def buscar_documentos_avanzado(
    copropiedad_id: str = Query(...),
    q: str = Query(..., min_length=2, description="Texto de búsqueda"),
    en_titulo: bool = True,
    en_descripcion: bool = True,
    en_tags: bool = True,
    en_contenido: bool = False,
    tipos: Optional[str] = None,
    estados: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None
):
    """
    Búsqueda avanzada full-text en documentos.
    
    - Busca en título, descripción, tags y contenido
    - Múltiples filtros combinables
    """
    documentos = [d for d in documentos_db.values() 
                 if d["copropiedad_id"] == copropiedad_id]
    
    q_lower = q.lower()
    resultados = []
    
    for doc in documentos:
        coincide = False
        campos_coincidencia = []
        
        if en_titulo and q_lower in doc["titulo"].lower():
            coincide = True
            campos_coincidencia.append("titulo")
        
        if en_descripcion and doc.get("descripcion") and q_lower in doc["descripcion"].lower():
            coincide = True
            campos_coincidencia.append("descripcion")
        
        if en_tags and any(q_lower in tag.lower() for tag in doc.get("tags", [])):
            coincide = True
            campos_coincidencia.append("tags")
        
        if en_contenido and doc.get("contenido_generado") and q_lower in doc["contenido_generado"].lower():
            coincide = True
            campos_coincidencia.append("contenido")
        
        if coincide:
            resultados.append({
                **doc,
                "campos_coincidencia": campos_coincidencia
            })
    
    # Aplicar filtros adicionales
    if tipos:
        tipos_list = tipos.split(",")
        resultados = [r for r in resultados if r["tipo"] in tipos_list]
    
    if estados:
        estados_list = estados.split(",")
        resultados = [r for r in resultados if r["estado"] in estados_list]
    
    if fecha_desde:
        resultados = [r for r in resultados if r["fecha_creacion"].date() >= fecha_desde]
    
    if fecha_hasta:
        resultados = [r for r in resultados if r["fecha_creacion"].date() <= fecha_hasta]
    
    return {
        "success": True,
        "query": q,
        "resultados": resultados,
        "total": len(resultados)
    }
