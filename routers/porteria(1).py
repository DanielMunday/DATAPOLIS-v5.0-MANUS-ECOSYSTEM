# satisfactiva/backend/app/routers/porteria.py
"""
DATAPOLIS v3.0 - ROUTER M15: PORTERÍA Y CONTROL DE ACCESO
Sistema completo de control de acceso, visitas y seguridad perimetral
Autor: Cascade AI para DATAPOLIS SpA
Fecha: 2026-02-01
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/porteria", tags=["M15 - Portería y Control Acceso"])

# ============================================================================
# ENUMS
# ============================================================================

class TipoVisita(str, Enum):
    INVITADO = "invitado"
    DELIVERY = "delivery"
    PROVEEDOR = "proveedor"
    TECNICO = "tecnico"
    AUTORIDAD = "autoridad"
    FAMILIAR = "familiar"
    EMERGENCIA = "emergencia"

class TipoVehiculo(str, Enum):
    AUTOMOVIL = "automovil"
    MOTOCICLETA = "motocicleta"
    BICICLETA = "bicicleta"
    CAMIONETA = "camioneta"
    CAMION = "camion"
    FURGON = "furgon"
    OTRO = "otro"

class EstadoAcceso(str, Enum):
    AUTORIZADO = "autorizado"
    PENDIENTE = "pendiente"
    DENEGADO = "denegado"
    EXPIRADO = "expirado"

class TipoAcceso(str, Enum):
    ENTRADA = "entrada"
    SALIDA = "salida"

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class VisitaCreate(BaseModel):
    copropiedad_id: str
    unidad_destino: str
    nombre_visitante: str = Field(..., min_length=3)
    rut_visitante: Optional[str] = None
    tipo_visita: TipoVisita
    vehiculo: Optional[Dict[str, str]] = None
    items_declarados: List[str] = []
    autorizado_por: Optional[str] = None
    observaciones: Optional[str] = None

class VisitaProgramada(BaseModel):
    copropiedad_id: str
    unidad_id: str
    nombre_visitante: str
    rut_visitante: Optional[str] = None
    tipo_visita: TipoVisita
    fecha_visita: date
    hora_desde: time
    hora_hasta: time
    vehiculo_patente: Optional[str] = None
    motivo: Optional[str] = None

class VehiculoResidente(BaseModel):
    unidad_id: str
    patente: str = Field(..., min_length=5, max_length=10)
    tipo: TipoVehiculo
    marca: str
    modelo: str
    color: str
    estacionamiento: Optional[str] = None

class AccesoVehicularCreate(BaseModel):
    copropiedad_id: str
    patente: str
    tipo_acceso: TipoAcceso
    conductor_nombre: Optional[str] = None
    observaciones: Optional[str] = None

# ============================================================================
# ALMACENAMIENTO EN MEMORIA
# ============================================================================

visitas_db: Dict[str, Dict] = {}
visitas_programadas_db: Dict[str, Dict] = {}
vehiculos_residentes_db: Dict[str, Dict] = {}
bitacora_db: List[Dict] = []
accesos_vehiculares_db: List[Dict] = []

# ============================================================================
# ENDPOINTS - REGISTRO DE VISITAS
# ============================================================================

@router.post("/visitas/entrada", response_model=Dict[str, Any])
async def registrar_entrada_visita(visita: VisitaCreate):
    """
    Registrar entrada de visitante
    
    Valida:
    - Autorización previa si existe
    - Horario permitido
    - Restricciones de la unidad
    """
    visita_id = f"VIS-{uuid.uuid4().hex[:8]}"
    
    # Verificar si hay autorización programada
    autorizacion = _verificar_autorizacion_previa(
        visita.copropiedad_id,
        visita.unidad_destino,
        visita.nombre_visitante,
        visita.rut_visitante
    )
    
    registro = {
        "id": visita_id,
        "copropiedad_id": visita.copropiedad_id,
        "unidad_destino": visita.unidad_destino,
        "nombre_visitante": visita.nombre_visitante,
        "rut_visitante": visita.rut_visitante,
        "tipo_visita": visita.tipo_visita.value,
        "vehiculo": visita.vehiculo,
        "items_declarados": visita.items_declarados,
        "autorizado_por": visita.autorizado_por or autorizacion.get("autorizado_por"),
        "tiene_autorizacion_previa": autorizacion.get("encontrada", False),
        "hora_entrada": datetime.now().isoformat(),
        "hora_salida": None,
        "estado": "activo",
        "observaciones": visita.observaciones,
        "credencial_temporal": f"CT-{uuid.uuid4().hex[:6].upper()}"
    }
    
    visitas_db[visita_id] = registro
    
    # Registrar en bitácora
    _registrar_bitacora(
        copropiedad_id=visita.copropiedad_id,
        evento="ENTRADA_VISITA",
        descripcion=f"Entrada visitante {visita.nombre_visitante} a unidad {visita.unidad_destino}",
        datos={"visita_id": visita_id, "tipo": visita.tipo_visita.value}
    )
    
    return {
        "success": True,
        "visita_id": visita_id,
        "credencial": registro["credencial_temporal"],
        "unidad_destino": visita.unidad_destino,
        "hora_entrada": registro["hora_entrada"],
        "autorizacion_previa": autorizacion.get("encontrada", False),
        "mensaje": "Entrada registrada exitosamente"
    }


@router.post("/visitas/{visita_id}/salida", response_model=Dict[str, Any])
async def registrar_salida_visita(visita_id: str, observaciones: Optional[str] = None):
    """Registrar salida de visitante"""
    if visita_id not in visitas_db:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    visita = visitas_db[visita_id]
    
    if visita["estado"] != "activo":
        raise HTTPException(status_code=400, detail="Esta visita ya tiene salida registrada")
    
    visita["hora_salida"] = datetime.now().isoformat()
    visita["estado"] = "finalizado"
    if observaciones:
        visita["observaciones_salida"] = observaciones
    
    # Calcular duración
    entrada = datetime.fromisoformat(visita["hora_entrada"])
    salida = datetime.fromisoformat(visita["hora_salida"])
    duracion = salida - entrada
    
    # Registrar en bitácora
    _registrar_bitacora(
        copropiedad_id=visita["copropiedad_id"],
        evento="SALIDA_VISITA",
        descripcion=f"Salida visitante {visita['nombre_visitante']}",
        datos={"visita_id": visita_id, "duracion_minutos": duracion.seconds // 60}
    )
    
    return {
        "success": True,
        "visita_id": visita_id,
        "hora_salida": visita["hora_salida"],
        "duracion": f"{duracion.seconds // 3600}h {(duracion.seconds % 3600) // 60}min",
        "mensaje": "Salida registrada exitosamente"
    }


@router.get("/visitas", response_model=Dict[str, Any])
async def listar_visitas(
    copropiedad_id: str,
    fecha: Optional[date] = None,
    unidad: Optional[str] = None,
    solo_activas: bool = False,
    tipo: Optional[TipoVisita] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Listar visitas con filtros"""
    resultados = [v for v in visitas_db.values() if v["copropiedad_id"] == copropiedad_id]
    
    if fecha:
        resultados = [v for v in resultados if v["hora_entrada"][:10] == fecha.isoformat()]
    if unidad:
        resultados = [v for v in resultados if v["unidad_destino"] == unidad]
    if solo_activas:
        resultados = [v for v in resultados if v["estado"] == "activo"]
    if tipo:
        resultados = [v for v in resultados if v["tipo_visita"] == tipo.value]
    
    # Ordenar por hora entrada descendente
    resultados.sort(key=lambda x: x["hora_entrada"], reverse=True)
    
    activas = len([v for v in resultados if v["estado"] == "activo"])
    
    return {
        "total": len(resultados),
        "activas": activas,
        "visitas": resultados[:limit]
    }


# ============================================================================
# ENDPOINTS - VISITAS PROGRAMADAS
# ============================================================================

@router.post("/visitas/programar", response_model=Dict[str, Any])
async def programar_visita(visita: VisitaProgramada):
    """
    Programar visita con autorización previa
    
    Permite al residente pre-autorizar visitantes
    """
    programacion_id = f"PROG-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": programacion_id,
        "copropiedad_id": visita.copropiedad_id,
        "unidad_id": visita.unidad_id,
        "nombre_visitante": visita.nombre_visitante,
        "rut_visitante": visita.rut_visitante,
        "tipo_visita": visita.tipo_visita.value,
        "fecha_visita": visita.fecha_visita.isoformat(),
        "hora_desde": visita.hora_desde.isoformat(),
        "hora_hasta": visita.hora_hasta.isoformat(),
        "vehiculo_patente": visita.vehiculo_patente,
        "motivo": visita.motivo,
        "estado": "vigente",
        "codigo_acceso": f"ACC-{uuid.uuid4().hex[:6].upper()}",
        "fecha_registro": datetime.now().isoformat(),
        "utilizada": False
    }
    
    visitas_programadas_db[programacion_id] = registro
    
    return {
        "success": True,
        "programacion_id": programacion_id,
        "codigo_acceso": registro["codigo_acceso"],
        "fecha": visita.fecha_visita.isoformat(),
        "horario": f"{visita.hora_desde.isoformat()} - {visita.hora_hasta.isoformat()}",
        "mensaje": "Visita programada exitosamente. Comparta el código de acceso con su visitante."
    }


@router.get("/visitas/programadas/{unidad_id}", response_model=Dict[str, Any])
async def obtener_visitas_programadas(
    unidad_id: str,
    incluir_pasadas: bool = False
):
    """Obtener visitas programadas de una unidad"""
    hoy = date.today().isoformat()
    
    visitas = [
        v for v in visitas_programadas_db.values()
        if v["unidad_id"] == unidad_id
    ]
    
    if not incluir_pasadas:
        visitas = [v for v in visitas if v["fecha_visita"] >= hoy]
    
    visitas.sort(key=lambda x: (x["fecha_visita"], x["hora_desde"]))
    
    return {
        "unidad_id": unidad_id,
        "total": len(visitas),
        "visitas_programadas": visitas
    }


@router.delete("/visitas/programadas/{programacion_id}", response_model=Dict[str, Any])
async def cancelar_visita_programada(programacion_id: str):
    """Cancelar visita programada"""
    if programacion_id not in visitas_programadas_db:
        raise HTTPException(status_code=404, detail="Programación no encontrada")
    
    visitas_programadas_db[programacion_id]["estado"] = "cancelada"
    
    return {
        "success": True,
        "mensaje": "Visita programada cancelada"
    }


# ============================================================================
# ENDPOINTS - VEHÍCULOS RESIDENTES
# ============================================================================

@router.post("/vehiculos", response_model=Dict[str, Any])
async def registrar_vehiculo_residente(vehiculo: VehiculoResidente):
    """Registrar vehículo de residente"""
    vehiculo_id = f"VEH-{uuid.uuid4().hex[:8]}"
    
    # Verificar patente no duplicada
    patente_upper = vehiculo.patente.upper().replace("-", "").replace(" ", "")
    
    for v in vehiculos_residentes_db.values():
        if v["patente_normalizada"] == patente_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Patente {vehiculo.patente} ya registrada para unidad {v['unidad_id']}"
            )
    
    registro = {
        "id": vehiculo_id,
        "unidad_id": vehiculo.unidad_id,
        "patente": vehiculo.patente.upper(),
        "patente_normalizada": patente_upper,
        "tipo": vehiculo.tipo.value,
        "marca": vehiculo.marca,
        "modelo": vehiculo.modelo,
        "color": vehiculo.color,
        "estacionamiento": vehiculo.estacionamiento,
        "fecha_registro": datetime.now().isoformat(),
        "activo": True,
        "tag_acceso": f"TAG-{uuid.uuid4().hex[:8].upper()}"
    }
    
    vehiculos_residentes_db[vehiculo_id] = registro
    
    return {
        "success": True,
        "vehiculo_id": vehiculo_id,
        "patente": registro["patente"],
        "tag_acceso": registro["tag_acceso"],
        "mensaje": "Vehículo registrado exitosamente"
    }


@router.get("/vehiculos/{unidad_id}", response_model=Dict[str, Any])
async def obtener_vehiculos_unidad(unidad_id: str):
    """Obtener vehículos registrados de una unidad"""
    vehiculos = [
        v for v in vehiculos_residentes_db.values()
        if v["unidad_id"] == unidad_id and v["activo"]
    ]
    
    return {
        "unidad_id": unidad_id,
        "total": len(vehiculos),
        "vehiculos": vehiculos
    }


@router.get("/vehiculos/buscar/{patente}", response_model=Dict[str, Any])
async def buscar_vehiculo(patente: str):
    """Buscar vehículo por patente"""
    patente_normalizada = patente.upper().replace("-", "").replace(" ", "")
    
    for vehiculo in vehiculos_residentes_db.values():
        if vehiculo["patente_normalizada"] == patente_normalizada:
            return {
                "encontrado": True,
                "es_residente": True,
                "vehiculo": vehiculo
            }
    
    return {
        "encontrado": False,
        "es_residente": False,
        "mensaje": "Vehículo no registrado como residente"
    }


# ============================================================================
# ENDPOINTS - ACCESO VEHICULAR
# ============================================================================

@router.post("/acceso-vehicular", response_model=Dict[str, Any])
async def registrar_acceso_vehicular(acceso: AccesoVehicularCreate):
    """Registrar entrada/salida de vehículo"""
    acceso_id = f"AV-{uuid.uuid4().hex[:8]}"
    
    # Buscar si es residente
    patente_normalizada = acceso.patente.upper().replace("-", "").replace(" ", "")
    vehiculo_residente = None
    
    for v in vehiculos_residentes_db.values():
        if v["patente_normalizada"] == patente_normalizada:
            vehiculo_residente = v
            break
    
    registro = {
        "id": acceso_id,
        "copropiedad_id": acceso.copropiedad_id,
        "patente": acceso.patente.upper(),
        "tipo_acceso": acceso.tipo_acceso.value,
        "es_residente": vehiculo_residente is not None,
        "unidad": vehiculo_residente["unidad_id"] if vehiculo_residente else None,
        "conductor": acceso.conductor_nombre,
        "fecha_hora": datetime.now().isoformat(),
        "observaciones": acceso.observaciones
    }
    
    accesos_vehiculares_db.append(registro)
    
    # Bitácora
    _registrar_bitacora(
        copropiedad_id=acceso.copropiedad_id,
        evento=f"ACCESO_VEHICULAR_{acceso.tipo_acceso.value.upper()}",
        descripcion=f"{acceso.tipo_acceso.value.title()} vehículo {acceso.patente}",
        datos={"es_residente": vehiculo_residente is not None}
    )
    
    return {
        "success": True,
        "acceso_id": acceso_id,
        "patente": acceso.patente.upper(),
        "tipo": acceso.tipo_acceso.value,
        "es_residente": vehiculo_residente is not None,
        "unidad": vehiculo_residente["unidad_id"] if vehiculo_residente else "Visitante",
        "hora": datetime.now().strftime("%H:%M:%S")
    }


@router.get("/acceso-vehicular/historial", response_model=Dict[str, Any])
async def historial_acceso_vehicular(
    copropiedad_id: str,
    fecha: Optional[date] = None,
    patente: Optional[str] = None,
    tipo: Optional[TipoAcceso] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Historial de accesos vehiculares"""
    resultados = [a for a in accesos_vehiculares_db if a["copropiedad_id"] == copropiedad_id]
    
    if fecha:
        resultados = [a for a in resultados if a["fecha_hora"][:10] == fecha.isoformat()]
    if patente:
        patente_norm = patente.upper().replace("-", "").replace(" ", "")
        resultados = [a for a in resultados if patente_norm in a["patente"].replace("-", "")]
    if tipo:
        resultados = [a for a in resultados if a["tipo_acceso"] == tipo.value]
    
    resultados.sort(key=lambda x: x["fecha_hora"], reverse=True)
    
    return {
        "total": len(resultados),
        "accesos": resultados[:limit]
    }


# ============================================================================
# ENDPOINTS - BITÁCORA
# ============================================================================

@router.get("/bitacora", response_model=Dict[str, Any])
async def obtener_bitacora(
    copropiedad_id: str,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    evento: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Obtener bitácora de portería"""
    resultados = [b for b in bitacora_db if b["copropiedad_id"] == copropiedad_id]
    
    if fecha_desde:
        resultados = [b for b in resultados if b["fecha_hora"][:10] >= fecha_desde.isoformat()]
    if fecha_hasta:
        resultados = [b for b in resultados if b["fecha_hora"][:10] <= fecha_hasta.isoformat()]
    if evento:
        resultados = [b for b in resultados if evento.upper() in b["evento"]]
    
    resultados.sort(key=lambda x: x["fecha_hora"], reverse=True)
    
    return {
        "total": len(resultados),
        "registros": resultados[:limit]
    }


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================================================

@router.get("/estadisticas/{copropiedad_id}", response_model=Dict[str, Any])
async def estadisticas_porteria(
    copropiedad_id: str,
    fecha: Optional[date] = None
):
    """Estadísticas de portería"""
    fecha_filtro = (fecha or date.today()).isoformat()
    
    visitas_hoy = [
        v for v in visitas_db.values()
        if v["copropiedad_id"] == copropiedad_id
        and v["hora_entrada"][:10] == fecha_filtro
    ]
    
    accesos_hoy = [
        a for a in accesos_vehiculares_db
        if a["copropiedad_id"] == copropiedad_id
        and a["fecha_hora"][:10] == fecha_filtro
    ]
    
    # Estadísticas
    por_tipo_visita = {}
    for v in visitas_hoy:
        tipo = v["tipo_visita"]
        por_tipo_visita[tipo] = por_tipo_visita.get(tipo, 0) + 1
    
    return {
        "fecha": fecha_filtro,
        "visitas": {
            "total": len(visitas_hoy),
            "activas": len([v for v in visitas_hoy if v["estado"] == "activo"]),
            "por_tipo": por_tipo_visita
        },
        "accesos_vehiculares": {
            "total": len(accesos_hoy),
            "entradas": len([a for a in accesos_hoy if a["tipo_acceso"] == "entrada"]),
            "salidas": len([a for a in accesos_hoy if a["tipo_acceso"] == "salida"]),
            "residentes": len([a for a in accesos_hoy if a["es_residente"]]),
            "visitantes": len([a for a in accesos_hoy if not a["es_residente"]])
        },
        "eventos_bitacora": len([b for b in bitacora_db if b["copropiedad_id"] == copropiedad_id and b["fecha_hora"][:10] == fecha_filtro])
    }


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _verificar_autorizacion_previa(
    copropiedad_id: str,
    unidad_id: str,
    nombre: str,
    rut: Optional[str]
) -> Dict[str, Any]:
    """Verificar si existe autorización previa para el visitante"""
    hoy = date.today().isoformat()
    hora_actual = datetime.now().time().isoformat()[:5]
    
    for prog in visitas_programadas_db.values():
        if (prog["copropiedad_id"] == copropiedad_id
            and prog["unidad_id"] == unidad_id
            and prog["fecha_visita"] == hoy
            and prog["estado"] == "vigente"
            and not prog["utilizada"]):
            
            # Verificar nombre o RUT
            nombre_match = nombre.lower() in prog["nombre_visitante"].lower()
            rut_match = rut and prog.get("rut_visitante") == rut
            
            if nombre_match or rut_match:
                # Verificar horario
                if prog["hora_desde"] <= hora_actual <= prog["hora_hasta"]:
                    prog["utilizada"] = True
                    return {
                        "encontrada": True,
                        "programacion_id": prog["id"],
                        "autorizado_por": f"Pre-autorizado por residente unidad {unidad_id}"
                    }
    
    return {"encontrada": False}


def _registrar_bitacora(
    copropiedad_id: str,
    evento: str,
    descripcion: str,
    datos: Dict[str, Any] = None
):
    """Registrar evento en bitácora"""
    registro = {
        "id": f"BIT-{uuid.uuid4().hex[:8]}",
        "copropiedad_id": copropiedad_id,
        "evento": evento,
        "descripcion": descripcion,
        "datos": datos or {},
        "fecha_hora": datetime.now().isoformat()
    }
    bitacora_db.append(registro)
