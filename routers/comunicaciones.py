# satisfactiva/backend/app/routers/comunicaciones.py
"""
DATAPOLIS v3.0 - ROUTER M14: COMUNICACIONES MULTICANAL
Sistema completo de notificaciones, alertas y comunicaciones
Autor: Cascade AI para DATAPOLIS SpA
Fecha: 2026-02-01
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
import hashlib

router = APIRouter(prefix="/comunicaciones", tags=["M14 - Comunicaciones"])

# ============================================================================
# ENUMS
# ============================================================================

class TipoComunicacion(str, Enum):
    AVISO = "aviso"
    CIRCULAR = "circular"
    NOTIFICACION = "notificacion"
    EMERGENCIA = "emergencia"
    COBRANZA = "cobranza"
    ASAMBLEA = "asamblea"
    MANTENCION = "mantencion"
    BIENVENIDA = "bienvenida"
    RECORDATORIO = "recordatorio"
    NEWSLETTER = "newsletter"

class CanalEnvio(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    PLATAFORMA = "plataforma"
    TODOS = "todos"

class PrioridadMensaje(str, Enum):
    BAJA = "baja"
    NORMAL = "normal"
    ALTA = "alta"
    URGENTE = "urgente"
    CRITICA = "critica"

class EstadoEnvio(str, Enum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    LEIDO = "leido"
    FALLIDO = "fallido"
    REBOTADO = "rebotado"

# ============================================================================
# PLANTILLAS PREDEFINIDAS
# ============================================================================

PLANTILLAS_COMUNICACION = {
    "cobranza_amigable": {
        "asunto": "Recordatorio de pago - {copropiedad}",
        "contenido": """Estimado/a {nombre},

Le recordamos que tiene pendiente el pago de gastos comunes correspondiente al período {periodo}.

Monto: ${monto:,.0f}
Fecha vencimiento: {vencimiento}

Puede realizar su pago a través de nuestra plataforma o en las cuentas habilitadas.

Atentamente,
Administración {copropiedad}""",
        "canales": ["email", "push"]
    },
    "cobranza_formal": {
        "asunto": "Aviso de Morosidad - Acción Requerida",
        "contenido": """Estimado/a {nombre},

Mediante la presente, le informamos que mantiene una deuda vencida por concepto de gastos comunes.

Unidad: {unidad}
Monto adeudado: ${monto:,.0f}
Días de mora: {dias_mora}

De no regularizar su situación en los próximos 5 días hábiles, se procederá según lo establecido en el Reglamento de Copropiedad y la Ley 21.442.

Atentamente,
Administración {copropiedad}""",
        "canales": ["email", "sms"]
    },
    "convocatoria_asamblea": {
        "asunto": "Convocatoria Asamblea {tipo} - {fecha}",
        "contenido": """Estimado/a Copropietario/a,

Se convoca a Asamblea {tipo} de Copropietarios conforme a lo dispuesto en la Ley 21.442.

Fecha: {fecha}
Hora: {hora}
Lugar: {lugar}

TABLA:
{tabla}

Se requiere su asistencia personal o mediante poder notarial.

Administración {copropiedad}""",
        "canales": ["email", "push", "plataforma"]
    },
    "emergencia": {
        "asunto": "⚠️ ALERTA EMERGENCIA - {copropiedad}",
        "contenido": """ALERTA DE EMERGENCIA

{mensaje}

Hora: {hora}
Ubicación: {ubicacion}

Siga las instrucciones de seguridad.

Administración""",
        "canales": ["email", "sms", "push", "whatsapp"]
    },
    "mantencion_programada": {
        "asunto": "Aviso de Mantención Programada",
        "contenido": """Estimados Residentes,

Les informamos que se realizará mantención programada:

Tipo: {tipo_mantencion}
Fecha: {fecha}
Horario: {horario}
Áreas afectadas: {areas}

{observaciones}

Disculpe las molestias.
Administración {copropiedad}""",
        "canales": ["email", "plataforma"]
    }
}

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class ComunicacionCreate(BaseModel):
    copropiedad_id: str
    tipo: TipoComunicacion
    asunto: str = Field(..., min_length=5, max_length=200)
    contenido: str = Field(..., min_length=10)
    canales: List[CanalEnvio]
    prioridad: PrioridadMensaje = PrioridadMensaje.NORMAL
    destinatarios: List[str] = []  # IDs de unidades, vacío = todos
    programar_envio: Optional[datetime] = None
    adjuntos: List[str] = []
    variables: Dict[str, Any] = {}

class PlantillaPersonalizada(BaseModel):
    nombre: str
    tipo: TipoComunicacion
    asunto: str
    contenido: str
    canales: List[CanalEnvio]
    variables_requeridas: List[str] = []

class ConfiguracionNotificaciones(BaseModel):
    unidad_id: str
    email_habilitado: bool = True
    sms_habilitado: bool = True
    push_habilitado: bool = True
    whatsapp_habilitado: bool = False
    horario_permitido_inicio: str = "08:00"
    horario_permitido_fin: str = "21:00"
    tipos_silenciados: List[TipoComunicacion] = []

# ============================================================================
# ALMACENAMIENTO EN MEMORIA
# ============================================================================

comunicaciones_db: Dict[str, Dict] = {}
envios_db: Dict[str, List[Dict]] = {}
plantillas_personalizadas_db: Dict[str, Dict] = {}
configuraciones_db: Dict[str, Dict] = {}
estadisticas_envio: Dict[str, Dict] = {}

# ============================================================================
# ENDPOINTS - ENVÍO DE COMUNICACIONES
# ============================================================================

@router.post("/enviar", response_model=Dict[str, Any])
async def enviar_comunicacion(
    datos: ComunicacionCreate,
    background_tasks: BackgroundTasks
):
    """
    Enviar comunicación multicanal a destinatarios
    
    Soporta:
    - Envío inmediato o programado
    - Múltiples canales simultáneos
    - Priorización de mensajes
    - Tracking de entregas
    """
    comunicacion_id = f"COM-{uuid.uuid4().hex[:12]}"
    
    # Determinar destinatarios
    if not datos.destinatarios:
        # Todos los residentes de la copropiedad
        destinatarios_finales = _obtener_todos_destinatarios(datos.copropiedad_id)
    else:
        destinatarios_finales = datos.destinatarios
    
    # Procesar contenido con variables
    contenido_procesado = datos.contenido
    asunto_procesado = datos.asunto
    for var, valor in datos.variables.items():
        contenido_procesado = contenido_procesado.replace(f"{{{var}}}", str(valor))
        asunto_procesado = asunto_procesado.replace(f"{{{var}}}", str(valor))
    
    # Crear registro de comunicación
    comunicacion = {
        "id": comunicacion_id,
        "copropiedad_id": datos.copropiedad_id,
        "tipo": datos.tipo.value,
        "asunto": asunto_procesado,
        "contenido": contenido_procesado,
        "canales": [c.value for c in datos.canales],
        "prioridad": datos.prioridad.value,
        "total_destinatarios": len(destinatarios_finales),
        "adjuntos": datos.adjuntos,
        "fecha_creacion": datetime.now().isoformat(),
        "programado_para": datos.programar_envio.isoformat() if datos.programar_envio else None,
        "estado": "programado" if datos.programar_envio else "en_proceso",
        "estadisticas": {
            "enviados": 0,
            "entregados": 0,
            "leidos": 0,
            "fallidos": 0
        }
    }
    
    comunicaciones_db[comunicacion_id] = comunicacion
    envios_db[comunicacion_id] = []
    
    # Procesar envíos
    if datos.programar_envio and datos.programar_envio > datetime.now():
        # Programar para después
        mensaje = f"Comunicación programada para {datos.programar_envio.isoformat()}"
    else:
        # Enviar ahora
        for destinatario_id in destinatarios_finales:
            for canal in datos.canales:
                envio = {
                    "id": f"ENV-{uuid.uuid4().hex[:8]}",
                    "comunicacion_id": comunicacion_id,
                    "destinatario_id": destinatario_id,
                    "canal": canal.value,
                    "estado": EstadoEnvio.PENDIENTE.value,
                    "fecha_envio": None,
                    "fecha_entrega": None,
                    "fecha_lectura": None,
                    "intentos": 0,
                    "error": None
                }
                envios_db[comunicacion_id].append(envio)
        
        # Procesar en background
        background_tasks.add_task(_procesar_envios, comunicacion_id)
        mensaje = f"Procesando envío a {len(destinatarios_finales)} destinatarios"
    
    return {
        "success": True,
        "comunicacion_id": comunicacion_id,
        "tipo": datos.tipo.value,
        "destinatarios": len(destinatarios_finales),
        "canales": [c.value for c in datos.canales],
        "prioridad": datos.prioridad.value,
        "mensaje": mensaje
    }


@router.post("/enviar-plantilla/{plantilla_nombre}", response_model=Dict[str, Any])
async def enviar_desde_plantilla(
    plantilla_nombre: str,
    copropiedad_id: str,
    destinatarios: List[str] = [],
    variables: Dict[str, Any] = {},
    background_tasks: BackgroundTasks = None
):
    """Enviar comunicación usando plantilla predefinida"""
    # Buscar plantilla
    if plantilla_nombre in PLANTILLAS_COMUNICACION:
        plantilla = PLANTILLAS_COMUNICACION[plantilla_nombre]
    elif plantilla_nombre in plantillas_personalizadas_db:
        plantilla = plantillas_personalizadas_db[plantilla_nombre]
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Plantilla '{plantilla_nombre}' no encontrada"
        )
    
    # Procesar con variables
    asunto = plantilla["asunto"]
    contenido = plantilla["contenido"]
    
    for var, valor in variables.items():
        asunto = asunto.replace(f"{{{var}}}", str(valor))
        contenido = contenido.replace(f"{{{var}}}", str(valor))
    
    # Crear comunicación
    datos = ComunicacionCreate(
        copropiedad_id=copropiedad_id,
        tipo=TipoComunicacion.NOTIFICACION,
        asunto=asunto,
        contenido=contenido,
        canales=[CanalEnvio(c) for c in plantilla.get("canales", ["email"])],
        destinatarios=destinatarios,
        variables=variables
    )
    
    return await enviar_comunicacion(datos, background_tasks)


@router.post("/emergencia", response_model=Dict[str, Any])
async def enviar_alerta_emergencia(
    copropiedad_id: str,
    mensaje: str,
    ubicacion: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Enviar alerta de emergencia a todos los residentes
    
    Máxima prioridad, todos los canales disponibles
    """
    comunicacion_id = f"EME-{uuid.uuid4().hex[:8]}"
    
    plantilla = PLANTILLAS_COMUNICACION["emergencia"]
    contenido = plantilla["contenido"].format(
        mensaje=mensaje,
        hora=datetime.now().strftime("%H:%M"),
        ubicacion=ubicacion or "General"
    )
    
    comunicacion = {
        "id": comunicacion_id,
        "copropiedad_id": copropiedad_id,
        "tipo": TipoComunicacion.EMERGENCIA.value,
        "asunto": f"⚠️ ALERTA EMERGENCIA",
        "contenido": contenido,
        "canales": ["email", "sms", "push", "whatsapp"],
        "prioridad": PrioridadMensaje.CRITICA.value,
        "fecha_creacion": datetime.now().isoformat(),
        "estado": "enviado_inmediato",
        "metadata": {
            "ubicacion": ubicacion,
            "es_emergencia": True
        }
    }
    
    comunicaciones_db[comunicacion_id] = comunicacion
    
    # En producción: envío inmediato sin cola
    if background_tasks:
        background_tasks.add_task(_enviar_emergencia_inmediata, comunicacion_id, copropiedad_id)
    
    return {
        "success": True,
        "alerta_id": comunicacion_id,
        "mensaje": "Alerta de emergencia enviada a todos los canales",
        "prioridad": "CRÍTICA",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# ENDPOINTS - GESTIÓN DE COMUNICACIONES
# ============================================================================

@router.get("/", response_model=Dict[str, Any])
async def listar_comunicaciones(
    copropiedad_id: Optional[str] = None,
    tipo: Optional[TipoComunicacion] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Listar comunicaciones con filtros"""
    resultados = list(comunicaciones_db.values())
    
    if copropiedad_id:
        resultados = [c for c in resultados if c["copropiedad_id"] == copropiedad_id]
    if tipo:
        resultados = [c for c in resultados if c["tipo"] == tipo.value]
    if estado:
        resultados = [c for c in resultados if c["estado"] == estado]
    if fecha_desde:
        resultados = [c for c in resultados if c["fecha_creacion"][:10] >= fecha_desde.isoformat()]
    if fecha_hasta:
        resultados = [c for c in resultados if c["fecha_creacion"][:10] <= fecha_hasta.isoformat()]
    
    # Ordenar por fecha
    resultados.sort(key=lambda x: x["fecha_creacion"], reverse=True)
    
    total = len(resultados)
    
    return {
        "total": total,
        "comunicaciones": resultados[offset:offset + limit]
    }


@router.get("/{comunicacion_id}", response_model=Dict[str, Any])
async def obtener_comunicacion(comunicacion_id: str):
    """Obtener detalle de comunicación con estadísticas de envío"""
    if comunicacion_id not in comunicaciones_db:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    
    comunicacion = comunicaciones_db[comunicacion_id]
    envios = envios_db.get(comunicacion_id, [])
    
    # Calcular estadísticas
    stats = {
        "total_envios": len(envios),
        "por_estado": {},
        "por_canal": {},
        "tasa_entrega": 0,
        "tasa_lectura": 0
    }
    
    for envio in envios:
        estado = envio["estado"]
        canal = envio["canal"]
        
        stats["por_estado"][estado] = stats["por_estado"].get(estado, 0) + 1
        stats["por_canal"][canal] = stats["por_canal"].get(canal, 0) + 1
    
    if len(envios) > 0:
        entregados = stats["por_estado"].get("entregado", 0) + stats["por_estado"].get("leido", 0)
        leidos = stats["por_estado"].get("leido", 0)
        stats["tasa_entrega"] = (entregados / len(envios)) * 100
        stats["tasa_lectura"] = (leidos / len(envios)) * 100 if entregados > 0 else 0
    
    return {
        "comunicacion": comunicacion,
        "estadisticas": stats,
        "envios_recientes": envios[:20]
    }


@router.get("/{comunicacion_id}/tracking", response_model=Dict[str, Any])
async def tracking_envios(
    comunicacion_id: str,
    canal: Optional[CanalEnvio] = None,
    estado: Optional[EstadoEnvio] = None
):
    """Tracking detallado de envíos de una comunicación"""
    if comunicacion_id not in comunicaciones_db:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    
    envios = envios_db.get(comunicacion_id, [])
    
    if canal:
        envios = [e for e in envios if e["canal"] == canal.value]
    if estado:
        envios = [e for e in envios if e["estado"] == estado.value]
    
    return {
        "comunicacion_id": comunicacion_id,
        "total_envios": len(envios),
        "envios": envios
    }


@router.post("/{comunicacion_id}/reenviar", response_model=Dict[str, Any])
async def reenviar_fallidos(
    comunicacion_id: str,
    background_tasks: BackgroundTasks
):
    """Reenviar comunicación a destinatarios con envío fallido"""
    if comunicacion_id not in comunicaciones_db:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    
    envios = envios_db.get(comunicacion_id, [])
    fallidos = [e for e in envios if e["estado"] == EstadoEnvio.FALLIDO.value]
    
    if not fallidos:
        return {
            "success": True,
            "mensaje": "No hay envíos fallidos para reenviar",
            "reenviados": 0
        }
    
    # Marcar para reenvío
    for envio in fallidos:
        envio["estado"] = EstadoEnvio.PENDIENTE.value
        envio["intentos"] += 1
        envio["error"] = None
    
    background_tasks.add_task(_procesar_envios, comunicacion_id)
    
    return {
        "success": True,
        "mensaje": f"Reintentando {len(fallidos)} envíos fallidos",
        "reenviados": len(fallidos)
    }


# ============================================================================
# ENDPOINTS - PLANTILLAS
# ============================================================================

@router.get("/plantillas/predefinidas", response_model=Dict[str, Any])
async def listar_plantillas_predefinidas():
    """Listar plantillas predefinidas del sistema"""
    return {
        "plantillas": [
            {
                "nombre": nombre,
                "asunto": config["asunto"],
                "canales": config["canales"],
                "preview": config["contenido"][:200] + "..."
            }
            for nombre, config in PLANTILLAS_COMUNICACION.items()
        ]
    }


@router.post("/plantillas", response_model=Dict[str, Any])
async def crear_plantilla_personalizada(plantilla: PlantillaPersonalizada):
    """Crear plantilla de comunicación personalizada"""
    plantilla_id = f"TPL-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": plantilla_id,
        "nombre": plantilla.nombre,
        "tipo": plantilla.tipo.value,
        "asunto": plantilla.asunto,
        "contenido": plantilla.contenido,
        "canales": [c.value for c in plantilla.canales],
        "variables_requeridas": plantilla.variables_requeridas,
        "fecha_creacion": datetime.now().isoformat(),
        "usos": 0
    }
    
    plantillas_personalizadas_db[plantilla.nombre] = registro
    
    return {
        "success": True,
        "plantilla_id": plantilla_id,
        "nombre": plantilla.nombre,
        "mensaje": "Plantilla creada exitosamente"
    }


@router.get("/plantillas/personalizadas", response_model=Dict[str, Any])
async def listar_plantillas_personalizadas():
    """Listar plantillas personalizadas"""
    return {
        "total": len(plantillas_personalizadas_db),
        "plantillas": list(plantillas_personalizadas_db.values())
    }


# ============================================================================
# ENDPOINTS - CONFIGURACIÓN DE NOTIFICACIONES
# ============================================================================

@router.post("/configuracion", response_model=Dict[str, Any])
async def configurar_notificaciones(config: ConfiguracionNotificaciones):
    """Configurar preferencias de notificación para una unidad"""
    configuraciones_db[config.unidad_id] = {
        "unidad_id": config.unidad_id,
        "email_habilitado": config.email_habilitado,
        "sms_habilitado": config.sms_habilitado,
        "push_habilitado": config.push_habilitado,
        "whatsapp_habilitado": config.whatsapp_habilitado,
        "horario_inicio": config.horario_permitido_inicio,
        "horario_fin": config.horario_permitido_fin,
        "tipos_silenciados": [t.value for t in config.tipos_silenciados],
        "fecha_actualizacion": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "unidad_id": config.unidad_id,
        "mensaje": "Configuración actualizada"
    }


@router.get("/configuracion/{unidad_id}", response_model=Dict[str, Any])
async def obtener_configuracion(unidad_id: str):
    """Obtener configuración de notificaciones de una unidad"""
    if unidad_id not in configuraciones_db:
        # Configuración por defecto
        return {
            "unidad_id": unidad_id,
            "configuracion": {
                "email_habilitado": True,
                "sms_habilitado": True,
                "push_habilitado": True,
                "whatsapp_habilitado": False,
                "horario_inicio": "08:00",
                "horario_fin": "21:00",
                "tipos_silenciados": []
            },
            "es_default": True
        }
    
    return {
        "unidad_id": unidad_id,
        "configuracion": configuraciones_db[unidad_id],
        "es_default": False
    }


# ============================================================================
# ENDPOINTS - BANDEJA DE ENTRADA
# ============================================================================

@router.get("/bandeja/{unidad_id}", response_model=Dict[str, Any])
async def obtener_bandeja_entrada(
    unidad_id: str,
    solo_no_leidos: bool = False,
    tipo: Optional[TipoComunicacion] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """Obtener bandeja de entrada de una unidad"""
    mensajes = []
    
    for com_id, envios in envios_db.items():
        for envio in envios:
            if envio["destinatario_id"] == unidad_id:
                comunicacion = comunicaciones_db.get(com_id, {})
                
                if solo_no_leidos and envio["estado"] == EstadoEnvio.LEIDO.value:
                    continue
                if tipo and comunicacion.get("tipo") != tipo.value:
                    continue
                
                mensajes.append({
                    "envio_id": envio["id"],
                    "comunicacion_id": com_id,
                    "tipo": comunicacion.get("tipo"),
                    "asunto": comunicacion.get("asunto"),
                    "contenido_preview": comunicacion.get("contenido", "")[:100],
                    "fecha": envio.get("fecha_envio") or comunicacion.get("fecha_creacion"),
                    "leido": envio["estado"] == EstadoEnvio.LEIDO.value,
                    "prioridad": comunicacion.get("prioridad")
                })
    
    # Ordenar por fecha
    mensajes.sort(key=lambda x: x["fecha"] or "", reverse=True)
    
    no_leidos = len([m for m in mensajes if not m["leido"]])
    
    return {
        "unidad_id": unidad_id,
        "total_mensajes": len(mensajes),
        "no_leidos": no_leidos,
        "mensajes": mensajes[:limit]
    }


@router.post("/bandeja/{unidad_id}/marcar-leido", response_model=Dict[str, Any])
async def marcar_como_leido(
    unidad_id: str,
    envio_ids: List[str]
):
    """Marcar mensajes como leídos"""
    marcados = 0
    
    for com_id, envios in envios_db.items():
        for envio in envios:
            if envio["id"] in envio_ids and envio["destinatario_id"] == unidad_id:
                envio["estado"] = EstadoEnvio.LEIDO.value
                envio["fecha_lectura"] = datetime.now().isoformat()
                marcados += 1
    
    return {
        "success": True,
        "marcados": marcados
    }


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================================================

@router.get("/estadisticas/{copropiedad_id}", response_model=Dict[str, Any])
async def estadisticas_comunicaciones(
    copropiedad_id: str,
    periodo_dias: int = 30
):
    """Estadísticas de comunicaciones de una copropiedad"""
    fecha_inicio = (datetime.now() - timedelta(days=periodo_dias)).isoformat()
    
    comunicaciones = [
        c for c in comunicaciones_db.values()
        if c["copropiedad_id"] == copropiedad_id
        and c["fecha_creacion"] >= fecha_inicio
    ]
    
    stats = {
        "total_comunicaciones": len(comunicaciones),
        "por_tipo": {},
        "por_canal": {},
        "por_prioridad": {},
        "envios": {
            "total": 0,
            "entregados": 0,
            "fallidos": 0,
            "leidos": 0
        },
        "tasas": {
            "entrega": 0,
            "lectura": 0
        }
    }
    
    for com in comunicaciones:
        tipo = com["tipo"]
        prioridad = com["prioridad"]
        stats["por_tipo"][tipo] = stats["por_tipo"].get(tipo, 0) + 1
        stats["por_prioridad"][prioridad] = stats["por_prioridad"].get(prioridad, 0) + 1
        
        for canal in com.get("canales", []):
            stats["por_canal"][canal] = stats["por_canal"].get(canal, 0) + 1
        
        envios = envios_db.get(com["id"], [])
        stats["envios"]["total"] += len(envios)
        
        for envio in envios:
            if envio["estado"] in ["entregado", "leido"]:
                stats["envios"]["entregados"] += 1
            elif envio["estado"] == "fallido":
                stats["envios"]["fallidos"] += 1
            if envio["estado"] == "leido":
                stats["envios"]["leidos"] += 1
    
    if stats["envios"]["total"] > 0:
        stats["tasas"]["entrega"] = (stats["envios"]["entregados"] / stats["envios"]["total"]) * 100
        if stats["envios"]["entregados"] > 0:
            stats["tasas"]["lectura"] = (stats["envios"]["leidos"] / stats["envios"]["entregados"]) * 100
    
    return {
        "copropiedad_id": copropiedad_id,
        "periodo_dias": periodo_dias,
        "estadisticas": stats
    }


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _obtener_todos_destinatarios(copropiedad_id: str) -> List[str]:
    """Obtener todos los destinatarios de una copropiedad"""
    # En producción: consultar base de datos
    return [f"UNIT-{i:03d}" for i in range(1, 51)]


async def _procesar_envios(comunicacion_id: str):
    """Procesar envíos pendientes en background"""
    envios = envios_db.get(comunicacion_id, [])
    
    for envio in envios:
        if envio["estado"] == EstadoEnvio.PENDIENTE.value:
            # Simular envío
            envio["estado"] = EstadoEnvio.ENVIADO.value
            envio["fecha_envio"] = datetime.now().isoformat()
            
            # Simular entrega (90% éxito)
            import random
            if random.random() < 0.9:
                envio["estado"] = EstadoEnvio.ENTREGADO.value
                envio["fecha_entrega"] = datetime.now().isoformat()
            else:
                envio["estado"] = EstadoEnvio.FALLIDO.value
                envio["error"] = "Error de conectividad"
    
    # Actualizar estadísticas
    comunicacion = comunicaciones_db.get(comunicacion_id)
    if comunicacion:
        enviados = len([e for e in envios if e["estado"] != EstadoEnvio.PENDIENTE.value])
        entregados = len([e for e in envios if e["estado"] in [EstadoEnvio.ENTREGADO.value, EstadoEnvio.LEIDO.value]])
        fallidos = len([e for e in envios if e["estado"] == EstadoEnvio.FALLIDO.value])
        
        comunicacion["estadisticas"] = {
            "enviados": enviados,
            "entregados": entregados,
            "fallidos": fallidos,
            "leidos": 0
        }
        comunicacion["estado"] = "completado"


async def _enviar_emergencia_inmediata(comunicacion_id: str, copropiedad_id: str):
    """Enviar alerta de emergencia por todos los canales"""
    # En producción: envío real multicanal
    print(f"[EMERGENCIA] Enviando alerta {comunicacion_id} a copropiedad {copropiedad_id}")
