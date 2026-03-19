# satisfactiva/backend/app/routers/reservas.py
"""
DATAPOLIS v3.0 - ROUTER M16: RESERVAS DE ÁREAS COMUNES
Sistema completo de gestión de reservas según Ley 21.442
Autor: Cascade AI para DATAPOLIS SpA
Fecha: 2026-02-01
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
import uuid

router = APIRouter(prefix="/reservas", tags=["M16 - Reservas Áreas Comunes"])

# ============================================================================
# ENUMS
# ============================================================================

class TipoAreaComun(str, Enum):
    SALON_EVENTOS = "salon_eventos"
    QUINCHO = "quincho"
    PISCINA = "piscina"
    GIMNASIO = "gimnasio"
    SALA_REUNION = "sala_reunion"
    CANCHA_TENIS = "cancha_tenis"
    CANCHA_PADEL = "cancha_padel"
    MULTICANCHA = "multicancha"
    SALA_CINE = "sala_cine"
    TERRAZA = "terraza"
    PARRILLA = "parrilla"
    SALA_JUEGOS = "sala_juegos"

class EstadoReserva(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    EN_USO = "en_uso"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"
    NO_SHOW = "no_show"

class EstadoArea(str, Enum):
    DISPONIBLE = "disponible"
    OCUPADA = "ocupada"
    MANTENCION = "mantencion"
    CERRADA = "cerrada"

# ============================================================================
# CONFIGURACIÓN DE ÁREAS POR DEFECTO
# ============================================================================

AREAS_CONFIG = {
    TipoAreaComun.SALON_EVENTOS: {
        "nombre": "Salón de Eventos",
        "capacidad_maxima": 80,
        "tarifa_hora": 25000,
        "tarifa_dia": 150000,
        "garantia": 100000,
        "horario_inicio": "09:00",
        "horario_fin": "00:00",
        "duracion_minima_horas": 2,
        "duracion_maxima_horas": 8,
        "anticipacion_maxima_dias": 60,
        "cancelacion_sin_cargo_horas": 48,
        "requiere_aprobacion": True,
        "permite_alcohol": True,
        "permite_musica": True,
        "nivel_ruido_max_db": 70
    },
    TipoAreaComun.QUINCHO: {
        "nombre": "Quincho",
        "capacidad_maxima": 30,
        "tarifa_hora": 15000,
        "tarifa_dia": 80000,
        "garantia": 50000,
        "horario_inicio": "10:00",
        "horario_fin": "22:00",
        "duracion_minima_horas": 2,
        "duracion_maxima_horas": 6,
        "anticipacion_maxima_dias": 30,
        "cancelacion_sin_cargo_horas": 24,
        "requiere_aprobacion": False,
        "permite_alcohol": True,
        "permite_musica": True,
        "nivel_ruido_max_db": 65
    },
    TipoAreaComun.PISCINA: {
        "nombre": "Piscina",
        "capacidad_maxima": 40,
        "tarifa_hora": 0,
        "tarifa_dia": 0,
        "garantia": 0,
        "horario_inicio": "08:00",
        "horario_fin": "20:00",
        "duracion_minima_horas": 1,
        "duracion_maxima_horas": 3,
        "anticipacion_maxima_dias": 7,
        "cancelacion_sin_cargo_horas": 2,
        "requiere_aprobacion": False,
        "permite_alcohol": False,
        "permite_musica": False,
        "nivel_ruido_max_db": 50,
        "requiere_salvavidas": True
    },
    TipoAreaComun.GIMNASIO: {
        "nombre": "Gimnasio",
        "capacidad_maxima": 15,
        "tarifa_hora": 0,
        "tarifa_dia": 0,
        "garantia": 0,
        "horario_inicio": "06:00",
        "horario_fin": "22:00",
        "duracion_minima_horas": 1,
        "duracion_maxima_horas": 2,
        "anticipacion_maxima_dias": 7,
        "cancelacion_sin_cargo_horas": 2,
        "requiere_aprobacion": False,
        "permite_alcohol": False,
        "permite_musica": False,
        "nivel_ruido_max_db": 60
    },
    TipoAreaComun.SALA_REUNION: {
        "nombre": "Sala de Reuniones",
        "capacidad_maxima": 12,
        "tarifa_hora": 5000,
        "tarifa_dia": 30000,
        "garantia": 0,
        "horario_inicio": "08:00",
        "horario_fin": "21:00",
        "duracion_minima_horas": 1,
        "duracion_maxima_horas": 4,
        "anticipacion_maxima_dias": 14,
        "cancelacion_sin_cargo_horas": 12,
        "requiere_aprobacion": False,
        "permite_alcohol": False,
        "permite_musica": False,
        "nivel_ruido_max_db": 50
    }
}

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class AreaComunCreate(BaseModel):
    copropiedad_id: str
    tipo: TipoAreaComun
    nombre_personalizado: Optional[str] = None
    capacidad: Optional[int] = None
    tarifa_hora: Optional[Decimal] = None
    tarifa_dia: Optional[Decimal] = None
    garantia: Optional[Decimal] = None
    descripcion: Optional[str] = None
    ubicacion: Optional[str] = None
    equipamiento: List[str] = []

class ReservaCreate(BaseModel):
    area_id: str
    unidad_id: str
    fecha: date
    hora_inicio: time
    hora_fin: time
    cantidad_personas: int = Field(..., ge=1)
    motivo: Optional[str] = None
    requiere_equipamiento: List[str] = []
    observaciones: Optional[str] = None

class BloqueoArea(BaseModel):
    area_id: str
    fecha_desde: date
    fecha_hasta: date
    motivo: str
    tipo: str = "mantencion"  # mantencion, evento_privado, cierre_temporal

# ============================================================================
# ALMACENAMIENTO EN MEMORIA
# ============================================================================

areas_db: Dict[str, Dict] = {}
reservas_db: Dict[str, Dict] = {}
bloqueos_db: Dict[str, Dict] = {}
garantias_db: Dict[str, Dict] = {}

# ============================================================================
# ENDPOINTS - GESTIÓN DE ÁREAS
# ============================================================================

@router.post("/areas", response_model=Dict[str, Any])
async def crear_area_comun(area: AreaComunCreate):
    """Crear o configurar área común"""
    area_id = f"AREA-{area.copropiedad_id[:6]}-{uuid.uuid4().hex[:6]}"
    
    # Obtener configuración por defecto
    config_default = AREAS_CONFIG.get(area.tipo, {})
    
    registro = {
        "id": area_id,
        "copropiedad_id": area.copropiedad_id,
        "tipo": area.tipo.value,
        "nombre": area.nombre_personalizado or config_default.get("nombre", area.tipo.value),
        "capacidad": area.capacidad or config_default.get("capacidad_maxima", 20),
        "tarifa_hora": float(area.tarifa_hora) if area.tarifa_hora else config_default.get("tarifa_hora", 0),
        "tarifa_dia": float(area.tarifa_dia) if area.tarifa_dia else config_default.get("tarifa_dia", 0),
        "garantia": float(area.garantia) if area.garantia else config_default.get("garantia", 0),
        "horario_inicio": config_default.get("horario_inicio", "08:00"),
        "horario_fin": config_default.get("horario_fin", "22:00"),
        "duracion_minima": config_default.get("duracion_minima_horas", 1),
        "duracion_maxima": config_default.get("duracion_maxima_horas", 4),
        "anticipacion_maxima_dias": config_default.get("anticipacion_maxima_dias", 30),
        "cancelacion_sin_cargo_horas": config_default.get("cancelacion_sin_cargo_horas", 24),
        "requiere_aprobacion": config_default.get("requiere_aprobacion", False),
        "descripcion": area.descripcion,
        "ubicacion": area.ubicacion,
        "equipamiento": area.equipamiento,
        "estado": EstadoArea.DISPONIBLE.value,
        "fecha_creacion": datetime.now().isoformat(),
        "activa": True
    }
    
    areas_db[area_id] = registro
    
    return {
        "success": True,
        "area_id": area_id,
        "nombre": registro["nombre"],
        "mensaje": "Área común creada exitosamente"
    }


@router.get("/areas", response_model=Dict[str, Any])
async def listar_areas(
    copropiedad_id: str,
    tipo: Optional[TipoAreaComun] = None,
    solo_disponibles: bool = False
):
    """Listar áreas comunes de una copropiedad"""
    resultados = [a for a in areas_db.values() if a["copropiedad_id"] == copropiedad_id and a["activa"]]
    
    if tipo:
        resultados = [a for a in resultados if a["tipo"] == tipo.value]
    if solo_disponibles:
        resultados = [a for a in resultados if a["estado"] == EstadoArea.DISPONIBLE.value]
    
    return {
        "total": len(resultados),
        "areas": resultados
    }


@router.get("/areas/{area_id}", response_model=Dict[str, Any])
async def obtener_area(area_id: str):
    """Obtener detalle de área común"""
    if area_id not in areas_db:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    return areas_db[area_id]


# ============================================================================
# ENDPOINTS - RESERVAS
# ============================================================================

@router.post("/", response_model=Dict[str, Any])
async def crear_reserva(reserva: ReservaCreate):
    """
    Crear reserva de área común
    
    Validaciones:
    - Disponibilidad del área
    - Capacidad máxima
    - Horarios permitidos
    - Anticipación máxima
    - Conflictos con otras reservas
    """
    if reserva.area_id not in areas_db:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    area = areas_db[reserva.area_id]
    
    # Validar capacidad
    if reserva.cantidad_personas > area["capacidad"]:
        raise HTTPException(
            status_code=400,
            detail=f"Capacidad máxima del área: {area['capacidad']} personas"
        )
    
    # Validar horarios
    hora_inicio_str = reserva.hora_inicio.isoformat()[:5]
    hora_fin_str = reserva.hora_fin.isoformat()[:5]
    
    if hora_inicio_str < area["horario_inicio"]:
        raise HTTPException(
            status_code=400,
            detail=f"Horario de inicio mínimo: {area['horario_inicio']}"
        )
    
    if hora_fin_str > area["horario_fin"] and area["horario_fin"] != "00:00":
        raise HTTPException(
            status_code=400,
            detail=f"Horario de cierre: {area['horario_fin']}"
        )
    
    # Validar duración
    inicio = datetime.combine(date.today(), reserva.hora_inicio)
    fin = datetime.combine(date.today(), reserva.hora_fin)
    duracion_horas = (fin - inicio).seconds / 3600
    
    if duracion_horas < area["duracion_minima"]:
        raise HTTPException(
            status_code=400,
            detail=f"Duración mínima: {area['duracion_minima']} horas"
        )
    
    if duracion_horas > area["duracion_maxima"]:
        raise HTTPException(
            status_code=400,
            detail=f"Duración máxima: {area['duracion_maxima']} horas"
        )
    
    # Validar anticipación
    dias_anticipacion = (reserva.fecha - date.today()).days
    if dias_anticipacion > area["anticipacion_maxima_dias"]:
        raise HTTPException(
            status_code=400,
            detail=f"Anticipación máxima: {area['anticipacion_maxima_dias']} días"
        )
    
    if dias_anticipacion < 0:
        raise HTTPException(status_code=400, detail="No se puede reservar en fechas pasadas")
    
    # Verificar conflictos
    conflictos = _verificar_conflictos(
        reserva.area_id,
        reserva.fecha,
        reserva.hora_inicio,
        reserva.hora_fin
    )
    
    if conflictos:
        raise HTTPException(
            status_code=409,
            detail=f"Conflicto con reserva existente: {conflictos[0]['id']}"
        )
    
    # Verificar bloqueos
    if _verificar_bloqueo(reserva.area_id, reserva.fecha):
        raise HTTPException(
            status_code=400,
            detail="El área está bloqueada en esa fecha"
        )
    
    # Calcular costo
    costo = area["tarifa_hora"] * duracion_horas
    garantia = area["garantia"]
    
    # Crear reserva
    reserva_id = f"RES-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": reserva_id,
        "area_id": reserva.area_id,
        "area_nombre": area["nombre"],
        "unidad_id": reserva.unidad_id,
        "copropiedad_id": area["copropiedad_id"],
        "fecha": reserva.fecha.isoformat(),
        "hora_inicio": reserva.hora_inicio.isoformat(),
        "hora_fin": reserva.hora_fin.isoformat(),
        "duracion_horas": duracion_horas,
        "cantidad_personas": reserva.cantidad_personas,
        "motivo": reserva.motivo,
        "equipamiento_solicitado": reserva.requiere_equipamiento,
        "observaciones": reserva.observaciones,
        "costo": costo,
        "garantia": garantia,
        "total": costo + garantia,
        "estado": EstadoReserva.PENDIENTE.value if area["requiere_aprobacion"] else EstadoReserva.CONFIRMADA.value,
        "requiere_aprobacion": area["requiere_aprobacion"],
        "fecha_creacion": datetime.now().isoformat(),
        "codigo_confirmacion": f"CONF-{uuid.uuid4().hex[:6].upper()}"
    }
    
    reservas_db[reserva_id] = registro
    
    return {
        "success": True,
        "reserva_id": reserva_id,
        "codigo_confirmacion": registro["codigo_confirmacion"],
        "area": area["nombre"],
        "fecha": reserva.fecha.isoformat(),
        "horario": f"{hora_inicio_str} - {hora_fin_str}",
        "costo": costo,
        "garantia": garantia,
        "total": costo + garantia,
        "estado": registro["estado"],
        "mensaje": "Reserva pendiente de aprobación" if area["requiere_aprobacion"] else "Reserva confirmada"
    }


@router.get("/", response_model=Dict[str, Any])
async def listar_reservas(
    copropiedad_id: Optional[str] = None,
    unidad_id: Optional[str] = None,
    area_id: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[EstadoReserva] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Listar reservas con filtros"""
    resultados = list(reservas_db.values())
    
    if copropiedad_id:
        resultados = [r for r in resultados if r["copropiedad_id"] == copropiedad_id]
    if unidad_id:
        resultados = [r for r in resultados if r["unidad_id"] == unidad_id]
    if area_id:
        resultados = [r for r in resultados if r["area_id"] == area_id]
    if fecha_desde:
        resultados = [r for r in resultados if r["fecha"] >= fecha_desde.isoformat()]
    if fecha_hasta:
        resultados = [r for r in resultados if r["fecha"] <= fecha_hasta.isoformat()]
    if estado:
        resultados = [r for r in resultados if r["estado"] == estado.value]
    
    resultados.sort(key=lambda x: (x["fecha"], x["hora_inicio"]))
    
    return {
        "total": len(resultados),
        "reservas": resultados[:limit]
    }


@router.get("/{reserva_id}", response_model=Dict[str, Any])
async def obtener_reserva(reserva_id: str):
    """Obtener detalle de reserva"""
    if reserva_id not in reservas_db:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    return reservas_db[reserva_id]


@router.post("/{reserva_id}/aprobar", response_model=Dict[str, Any])
async def aprobar_reserva(reserva_id: str):
    """Aprobar reserva pendiente"""
    if reserva_id not in reservas_db:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    reserva = reservas_db[reserva_id]
    
    if reserva["estado"] != EstadoReserva.PENDIENTE.value:
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar reservas pendientes")
    
    reserva["estado"] = EstadoReserva.CONFIRMADA.value
    reserva["fecha_aprobacion"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "reserva_id": reserva_id,
        "estado": "confirmada",
        "mensaje": "Reserva aprobada exitosamente"
    }


@router.post("/{reserva_id}/cancelar", response_model=Dict[str, Any])
async def cancelar_reserva(reserva_id: str, motivo: Optional[str] = None):
    """Cancelar reserva"""
    if reserva_id not in reservas_db:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    reserva = reservas_db[reserva_id]
    
    if reserva["estado"] in [EstadoReserva.FINALIZADA.value, EstadoReserva.CANCELADA.value]:
        raise HTTPException(status_code=400, detail="No se puede cancelar esta reserva")
    
    # Calcular si aplica devolución de garantía
    area = areas_db.get(reserva["area_id"], {})
    fecha_reserva = datetime.strptime(reserva["fecha"], "%Y-%m-%d")
    horas_anticipacion = (fecha_reserva - datetime.now()).total_seconds() / 3600
    
    devolucion_garantia = horas_anticipacion >= area.get("cancelacion_sin_cargo_horas", 24)
    
    reserva["estado"] = EstadoReserva.CANCELADA.value
    reserva["fecha_cancelacion"] = datetime.now().isoformat()
    reserva["motivo_cancelacion"] = motivo
    reserva["devolucion_garantia"] = devolucion_garantia
    
    return {
        "success": True,
        "reserva_id": reserva_id,
        "estado": "cancelada",
        "devolucion_garantia": devolucion_garantia,
        "mensaje": f"Reserva cancelada. {'Garantía será devuelta.' if devolucion_garantia else 'No aplica devolución de garantía.'}"
    }


# ============================================================================
# ENDPOINTS - DISPONIBILIDAD
# ============================================================================

@router.get("/disponibilidad/{area_id}", response_model=Dict[str, Any])
async def obtener_disponibilidad(
    area_id: str,
    fecha: date
):
    """
    Obtener disponibilidad de un área para una fecha específica
    
    Retorna bloques horarios disponibles y ocupados
    """
    if area_id not in areas_db:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    area = areas_db[area_id]
    
    # Verificar si hay bloqueo
    if _verificar_bloqueo(area_id, fecha):
        return {
            "area_id": area_id,
            "fecha": fecha.isoformat(),
            "disponible": False,
            "motivo": "Área bloqueada",
            "bloques": []
        }
    
    # Obtener reservas del día
    reservas_dia = [
        r for r in reservas_db.values()
        if r["area_id"] == area_id
        and r["fecha"] == fecha.isoformat()
        and r["estado"] in [EstadoReserva.CONFIRMADA.value, EstadoReserva.PENDIENTE.value, EstadoReserva.EN_USO.value]
    ]
    
    # Generar bloques horarios
    inicio = datetime.strptime(area["horario_inicio"], "%H:%M")
    fin = datetime.strptime(area["horario_fin"], "%H:%M") if area["horario_fin"] != "00:00" else datetime.strptime("23:59", "%H:%M")
    
    bloques = []
    hora_actual = inicio
    
    while hora_actual < fin:
        hora_siguiente = hora_actual + timedelta(hours=1)
        bloque_inicio = hora_actual.strftime("%H:%M")
        bloque_fin = hora_siguiente.strftime("%H:%M")
        
        # Verificar si está ocupado
        ocupado = False
        reserva_id = None
        
        for reserva in reservas_dia:
            res_inicio = reserva["hora_inicio"][:5]
            res_fin = reserva["hora_fin"][:5]
            
            if res_inicio <= bloque_inicio < res_fin or res_inicio < bloque_fin <= res_fin:
                ocupado = True
                reserva_id = reserva["id"]
                break
        
        bloques.append({
            "hora_inicio": bloque_inicio,
            "hora_fin": bloque_fin,
            "disponible": not ocupado,
            "reserva_id": reserva_id
        })
        
        hora_actual = hora_siguiente
    
    disponibles = len([b for b in bloques if b["disponible"]])
    
    return {
        "area_id": area_id,
        "area_nombre": area["nombre"],
        "fecha": fecha.isoformat(),
        "horario_operacion": f"{area['horario_inicio']} - {area['horario_fin']}",
        "bloques_totales": len(bloques),
        "bloques_disponibles": disponibles,
        "bloques_ocupados": len(bloques) - disponibles,
        "bloques": bloques
    }


@router.get("/disponibilidad/{area_id}/calendario", response_model=Dict[str, Any])
async def calendario_disponibilidad(
    area_id: str,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2020, le=2030)
):
    """Obtener calendario de disponibilidad para un mes"""
    if area_id not in areas_db:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    area = areas_db[area_id]
    
    # Generar días del mes
    from calendar import monthrange
    dias_mes = monthrange(anio, mes)[1]
    
    calendario = []
    for dia in range(1, dias_mes + 1):
        fecha = date(anio, mes, dia)
        
        # Contar reservas
        reservas_dia = len([
            r for r in reservas_db.values()
            if r["area_id"] == area_id
            and r["fecha"] == fecha.isoformat()
            and r["estado"] in [EstadoReserva.CONFIRMADA.value, EstadoReserva.PENDIENTE.value]
        ])
        
        # Verificar bloqueo
        bloqueado = _verificar_bloqueo(area_id, fecha)
        
        calendario.append({
            "fecha": fecha.isoformat(),
            "dia": dia,
            "dia_semana": fecha.strftime("%A"),
            "reservas": reservas_dia,
            "bloqueado": bloqueado,
            "disponible": not bloqueado and reservas_dia < 3  # Asume máximo 3 reservas/día
        })
    
    return {
        "area_id": area_id,
        "area_nombre": area["nombre"],
        "mes": mes,
        "anio": anio,
        "dias": calendario
    }


# ============================================================================
# ENDPOINTS - BLOQUEOS
# ============================================================================

@router.post("/bloqueos", response_model=Dict[str, Any])
async def crear_bloqueo(bloqueo: BloqueoArea):
    """Bloquear área por mantención o evento especial"""
    if bloqueo.area_id not in areas_db:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    
    bloqueo_id = f"BLQ-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": bloqueo_id,
        "area_id": bloqueo.area_id,
        "fecha_desde": bloqueo.fecha_desde.isoformat(),
        "fecha_hasta": bloqueo.fecha_hasta.isoformat(),
        "motivo": bloqueo.motivo,
        "tipo": bloqueo.tipo,
        "fecha_creacion": datetime.now().isoformat(),
        "activo": True
    }
    
    bloqueos_db[bloqueo_id] = registro
    
    # Actualizar estado del área si bloqueo es inmediato
    if bloqueo.fecha_desde <= date.today() <= bloqueo.fecha_hasta:
        areas_db[bloqueo.area_id]["estado"] = EstadoArea.MANTENCION.value
    
    return {
        "success": True,
        "bloqueo_id": bloqueo_id,
        "mensaje": f"Área bloqueada del {bloqueo.fecha_desde} al {bloqueo.fecha_hasta}"
    }


@router.get("/bloqueos/{area_id}", response_model=Dict[str, Any])
async def listar_bloqueos(area_id: str):
    """Listar bloqueos de un área"""
    bloqueos = [b for b in bloqueos_db.values() if b["area_id"] == area_id and b["activo"]]
    
    return {
        "area_id": area_id,
        "total": len(bloqueos),
        "bloqueos": bloqueos
    }


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================================================

@router.get("/estadisticas/{copropiedad_id}", response_model=Dict[str, Any])
async def estadisticas_reservas(
    copropiedad_id: str,
    mes: Optional[int] = None,
    anio: Optional[int] = None
):
    """Estadísticas de uso de áreas comunes"""
    reservas = [r for r in reservas_db.values() if r["copropiedad_id"] == copropiedad_id]
    
    if mes and anio:
        prefix = f"{anio}-{mes:02d}"
        reservas = [r for r in reservas if r["fecha"].startswith(prefix)]
    
    # Estadísticas por área
    por_area = {}
    ingresos_total = 0
    
    for reserva in reservas:
        area_nombre = reserva["area_nombre"]
        if area_nombre not in por_area:
            por_area[area_nombre] = {"reservas": 0, "ingresos": 0, "horas": 0}
        
        por_area[area_nombre]["reservas"] += 1
        por_area[area_nombre]["ingresos"] += reserva.get("costo", 0)
        por_area[area_nombre]["horas"] += reserva.get("duracion_horas", 0)
        ingresos_total += reserva.get("costo", 0)
    
    # Por estado
    por_estado = {}
    for reserva in reservas:
        estado = reserva["estado"]
        por_estado[estado] = por_estado.get(estado, 0) + 1
    
    return {
        "copropiedad_id": copropiedad_id,
        "periodo": f"{mes}/{anio}" if mes and anio else "total",
        "estadisticas": {
            "total_reservas": len(reservas),
            "ingresos_total": ingresos_total,
            "por_area": por_area,
            "por_estado": por_estado,
            "promedio_duracion_horas": sum(r.get("duracion_horas", 0) for r in reservas) / len(reservas) if reservas else 0,
            "tasa_cancelacion": (por_estado.get("cancelada", 0) / len(reservas) * 100) if reservas else 0
        }
    }


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _verificar_conflictos(
    area_id: str,
    fecha: date,
    hora_inicio: time,
    hora_fin: time
) -> List[Dict]:
    """Verificar conflictos con reservas existentes"""
    conflictos = []
    
    for reserva in reservas_db.values():
        if (reserva["area_id"] == area_id
            and reserva["fecha"] == fecha.isoformat()
            and reserva["estado"] in [EstadoReserva.CONFIRMADA.value, EstadoReserva.PENDIENTE.value]):
            
            res_inicio = time.fromisoformat(reserva["hora_inicio"])
            res_fin = time.fromisoformat(reserva["hora_fin"])
            
            # Verificar solapamiento
            if not (hora_fin <= res_inicio or hora_inicio >= res_fin):
                conflictos.append(reserva)
    
    return conflictos


def _verificar_bloqueo(area_id: str, fecha: date) -> bool:
    """Verificar si hay bloqueo activo para la fecha"""
    fecha_str = fecha.isoformat()
    
    for bloqueo in bloqueos_db.values():
        if (bloqueo["area_id"] == area_id
            and bloqueo["activo"]
            and bloqueo["fecha_desde"] <= fecha_str <= bloqueo["fecha_hasta"]):
            return True
    
    return False
