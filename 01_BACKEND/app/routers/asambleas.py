# satisfactiva/backend/app/routers/asambleas.py
"""
DATAPOLIS v3.0 - ROUTER M13: ASAMBLEAS DE COPROPIETARIOS
API REST completa para gestión de asambleas según Ley 21.442 y Reglamento de Copropiedad
Autor: Cascade AI para DATAPOLIS SpA
Fecha: 2026-02-01
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time, timedelta
from enum import Enum
from decimal import Decimal
import uuid
import hashlib

router = APIRouter(prefix="/asambleas", tags=["M13 - Asambleas"])

# ============================================================================
# ENUMS - TIPOS DE ASAMBLEA LEY 21.442
# ============================================================================

class TipoAsamblea(str, Enum):
    """Tipos de asamblea según Ley 21.442"""
    ORDINARIA = "ordinaria"  # Art. 17 - Una vez al año mínimo
    EXTRAORDINARIA = "extraordinaria"  # Art. 17 - Convocada cuando sea necesario
    COMITE_ADMINISTRACION = "comite_administracion"  # Comité de Administración
    PRIMERA_CONSTITUCION = "primera_constitucion"  # Primera asamblea constitutiva
    SEGUNDA_CITACION = "segunda_citacion"  # Por falta de quórum en primera

class EstadoAsamblea(str, Enum):
    """Estados del ciclo de vida de asamblea"""
    PROGRAMADA = "programada"
    CONVOCADA = "convocada"
    EN_CURSO = "en_curso"
    SUSPENDIDA = "suspendida"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"
    ACTA_PENDIENTE = "acta_pendiente"
    ACTA_APROBADA = "acta_aprobada"

class TipoQuorum(str, Enum):
    """Tipos de quórum según Ley 21.442"""
    CONSTITUCION = "constitucion"  # Para iniciar asamblea
    MAYORIA_SIMPLE = "mayoria_simple"  # 50% + 1 de presentes
    MAYORIA_ABSOLUTA = "mayoria_absoluta"  # 50% + 1 de derechos totales
    DOS_TERCIOS = "dos_tercios"  # 66.67% de derechos
    TRES_CUARTOS = "tres_cuartos"  # 75% de derechos
    UNANIMIDAD = "unanimidad"  # 100% de derechos

class TipoVotacion(str, Enum):
    """Tipos de votación"""
    MANO_ALZADA = "mano_alzada"
    SECRETA = "secreta"
    NOMINAL = "nominal"
    ELECTRONICA = "electronica"
    MIXTA = "mixta"

class ResultadoVotacion(str, Enum):
    """Resultado de votación"""
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    EMPATE = "empate"
    SIN_QUORUM = "sin_quorum"
    PENDIENTE = "pendiente"

class TipoAsistencia(str, Enum):
    """Tipos de asistencia"""
    PRESENCIAL = "presencial"
    REMOTA = "remota"
    PODER = "poder"
    MIXTA = "mixta"

# ============================================================================
# QUÓRUMS LEGALES SEGÚN LEY 21.442
# ============================================================================

QUORUMS_LEGALES = {
    # Art. 19 - Quórum de constitución primera citación
    "constitucion_primera": {
        "minimo_derechos": Decimal("0.6667"),  # 2/3 de derechos
        "descripcion": "Quórum constitución primera citación: 2/3 derechos"
    },
    # Art. 19 - Quórum de constitución segunda citación
    "constitucion_segunda": {
        "minimo_derechos": Decimal("0.3333"),  # 1/3 de derechos
        "descripcion": "Quórum constitución segunda citación: 1/3 derechos"
    },
    # Art. 19 - Materias que requieren 2/3
    "dos_tercios": {
        "minimo_derechos": Decimal("0.6667"),
        "materias": [
            "modificacion_reglamento_copropiedad",
            "cambio_destino_bienes_comunes",
            "construccion_nuevas_obras",
            "enajenacion_bienes_comunes",
            "demolicion_edificio"
        ],
        "descripcion": "Requiere 2/3 de derechos totales"
    },
    # Art. 19 - Materias que requieren 3/4
    "tres_cuartos": {
        "minimo_derechos": Decimal("0.75"),
        "materias": [
            "modificacion_prorrateo_gastos",
            "cambio_administrador",
            "acciones_judiciales_administrador"
        ],
        "descripcion": "Requiere 3/4 de derechos totales"
    },
    # Art. 19 - Materias que requieren unanimidad
    "unanimidad": {
        "minimo_derechos": Decimal("1.0"),
        "materias": [
            "disolucion_copropiedad",
            "modificacion_porcentajes_dominio"
        ],
        "descripcion": "Requiere unanimidad (100%) de derechos"
    },
    # Mayoría absoluta de presentes
    "mayoria_simple": {
        "minimo_derechos": Decimal("0.5001"),
        "base": "presentes",
        "descripcion": "Mayoría simple de presentes"
    }
}

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class ConvocatoriaCreate(BaseModel):
    """Datos para crear convocatoria de asamblea"""
    copropiedad_id: str
    tipo_asamblea: TipoAsamblea
    fecha_asamblea: date
    hora_inicio: time
    lugar: str = Field(..., min_length=5)
    modalidad: TipoAsistencia = TipoAsistencia.PRESENCIAL
    enlace_virtual: Optional[str] = None
    tabla_puntos: List[Dict[str, Any]] = Field(..., min_items=1)
    documentos_adjuntos: List[str] = []
    observaciones: Optional[str] = None

class PuntoTabla(BaseModel):
    """Punto de la tabla de asamblea"""
    numero: int
    titulo: str
    descripcion: Optional[str] = None
    tipo_quorum: TipoQuorum = TipoQuorum.MAYORIA_SIMPLE
    requiere_votacion: bool = True
    documentos_soporte: List[str] = []
    tiempo_estimado_minutos: int = 15

class RegistroAsistencia(BaseModel):
    """Registro de asistente a asamblea"""
    unidad_id: str
    propietario_nombre: str
    propietario_rut: str
    tipo_asistencia: TipoAsistencia
    porcentaje_derechos: Decimal
    representante_nombre: Optional[str] = None
    representante_rut: Optional[str] = None
    poder_notarial: bool = False
    hora_llegada: datetime = Field(default_factory=datetime.now)
    firma_digital: Optional[str] = None

class VotacionCreate(BaseModel):
    """Datos para registrar votación"""
    punto_tabla_numero: int
    tipo_votacion: TipoVotacion = TipoVotacion.MANO_ALZADA
    descripcion_mocion: str
    opciones: List[str] = ["A favor", "En contra", "Abstención"]

class VotoRegistro(BaseModel):
    """Registro de voto individual"""
    unidad_id: str
    opcion_votada: str
    porcentaje_derechos: Decimal
    hora_voto: datetime = Field(default_factory=datetime.now)
    verificacion_hash: Optional[str] = None

class AcuerdoCreate(BaseModel):
    """Crear acuerdo de asamblea"""
    punto_tabla_numero: int
    descripcion_acuerdo: str
    votos_favor: Decimal
    votos_contra: Decimal
    abstenciones: Decimal
    resultado: ResultadoVotacion
    responsable_ejecucion: Optional[str] = None
    plazo_ejecucion: Optional[date] = None
    presupuesto_asociado: Optional[Decimal] = None

class ActaCreate(BaseModel):
    """Crear acta de asamblea"""
    asamblea_id: str
    presidente_asamblea: str
    secretario_acta: str
    resumen_desarrollo: str
    acuerdos: List[AcuerdoCreate]
    observaciones_generales: Optional[str] = None
    hora_termino: datetime

# ============================================================================
# ALMACENAMIENTO EN MEMORIA (Producción: PostgreSQL)
# ============================================================================

asambleas_db: Dict[str, Dict] = {}
asistencias_db: Dict[str, List[Dict]] = {}
votaciones_db: Dict[str, List[Dict]] = {}
acuerdos_db: Dict[str, List[Dict]] = {}
actas_db: Dict[str, Dict] = {}

# ============================================================================
# ENDPOINTS - CONVOCATORIA Y PROGRAMACIÓN
# ============================================================================

@router.post("/convocar", response_model=Dict[str, Any])
async def convocar_asamblea(
    datos: ConvocatoriaCreate,
    background_tasks: BackgroundTasks
):
    """
    Convocar asamblea de copropietarios según Ley 21.442
    
    Requisitos legales:
    - Art. 17: Ordinaria al menos 1 vez al año
    - Art. 18: Citación con 5 días hábiles de anticipación mínimo
    - Art. 18: Debe indicar lugar, día, hora y tabla de materias
    """
    # Validar anticipación mínima (5 días hábiles)
    dias_anticipacion = (datos.fecha_asamblea - date.today()).days
    if dias_anticipacion < 5:
        raise HTTPException(
            status_code=400,
            detail="La convocatoria debe realizarse con al menos 5 días hábiles de anticipación (Art. 18 Ley 21.442)"
        )
    
    # Generar ID único
    asamblea_id = f"ASM-{datos.copropiedad_id[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Determinar quórum requerido según tipo
    quorum_constitucion = QUORUMS_LEGALES["constitucion_primera"]["minimo_derechos"]
    if datos.tipo_asamblea == TipoAsamblea.SEGUNDA_CITACION:
        quorum_constitucion = QUORUMS_LEGALES["constitucion_segunda"]["minimo_derechos"]
    
    # Procesar puntos de tabla con quórums
    puntos_procesados = []
    for i, punto in enumerate(datos.tabla_puntos, 1):
        punto_procesado = {
            "numero": i,
            "titulo": punto.get("titulo", f"Punto {i}"),
            "descripcion": punto.get("descripcion", ""),
            "tipo_quorum": punto.get("tipo_quorum", "mayoria_simple"),
            "requiere_votacion": punto.get("requiere_votacion", True),
            "quorum_requerido": _determinar_quorum_punto(punto.get("tipo_quorum", "mayoria_simple")),
            "estado": "pendiente"
        }
        puntos_procesados.append(punto_procesado)
    
    # Crear asamblea
    asamblea = {
        "id": asamblea_id,
        "copropiedad_id": datos.copropiedad_id,
        "tipo": datos.tipo_asamblea.value,
        "estado": EstadoAsamblea.CONVOCADA.value,
        "fecha_asamblea": datos.fecha_asamblea.isoformat(),
        "hora_inicio": datos.hora_inicio.isoformat(),
        "lugar": datos.lugar,
        "modalidad": datos.modalidad.value,
        "enlace_virtual": datos.enlace_virtual,
        "tabla_puntos": puntos_procesados,
        "documentos_adjuntos": datos.documentos_adjuntos,
        "quorum_constitucion_requerido": float(quorum_constitucion),
        "quorum_presente": 0,
        "total_asistentes": 0,
        "fecha_convocatoria": datetime.now().isoformat(),
        "observaciones": datos.observaciones,
        "metadata": {
            "dias_anticipacion": dias_anticipacion,
            "citacion_legal": True,
            "ley_aplicable": "21.442"
        }
    }
    
    asambleas_db[asamblea_id] = asamblea
    asistencias_db[asamblea_id] = []
    votaciones_db[asamblea_id] = []
    acuerdos_db[asamblea_id] = []
    
    # Programar envío de notificaciones (background)
    background_tasks.add_task(_enviar_convocatorias, asamblea_id, datos.copropiedad_id)
    
    return {
        "success": True,
        "asamblea_id": asamblea_id,
        "mensaje": f"Asamblea {datos.tipo_asamblea.value} convocada exitosamente",
        "fecha": datos.fecha_asamblea.isoformat(),
        "hora": datos.hora_inicio.isoformat(),
        "lugar": datos.lugar,
        "quorum_requerido": f"{float(quorum_constitucion)*100:.1f}%",
        "puntos_tabla": len(puntos_procesados),
        "notificaciones": "En proceso de envío"
    }


@router.get("/", response_model=Dict[str, Any])
async def listar_asambleas(
    copropiedad_id: Optional[str] = None,
    tipo: Optional[TipoAsamblea] = None,
    estado: Optional[EstadoAsamblea] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Listar asambleas con filtros"""
    resultados = list(asambleas_db.values())
    
    # Aplicar filtros
    if copropiedad_id:
        resultados = [a for a in resultados if a["copropiedad_id"] == copropiedad_id]
    if tipo:
        resultados = [a for a in resultados if a["tipo"] == tipo.value]
    if estado:
        resultados = [a for a in resultados if a["estado"] == estado.value]
    if fecha_desde:
        resultados = [a for a in resultados if a["fecha_asamblea"] >= fecha_desde.isoformat()]
    if fecha_hasta:
        resultados = [a for a in resultados if a["fecha_asamblea"] <= fecha_hasta.isoformat()]
    
    # Ordenar por fecha descendente
    resultados.sort(key=lambda x: x["fecha_asamblea"], reverse=True)
    
    total = len(resultados)
    resultados_paginados = resultados[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "asambleas": resultados_paginados
    }


@router.get("/{asamblea_id}", response_model=Dict[str, Any])
async def obtener_asamblea(asamblea_id: str):
    """Obtener detalle completo de asamblea"""
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    asistencias = asistencias_db.get(asamblea_id, [])
    votaciones = votaciones_db.get(asamblea_id, [])
    acuerdos = acuerdos_db.get(asamblea_id, [])
    acta = actas_db.get(asamblea_id)
    
    return {
        "asamblea": asamblea,
        "asistencias": {
            "total": len(asistencias),
            "quorum_presente": asamblea.get("quorum_presente", 0),
            "detalle": asistencias
        },
        "votaciones": votaciones,
        "acuerdos": acuerdos,
        "acta": acta,
        "resumen": {
            "puntos_totales": len(asamblea.get("tabla_puntos", [])),
            "puntos_tratados": len([p for p in asamblea.get("tabla_puntos", []) if p.get("estado") == "tratado"]),
            "acuerdos_aprobados": len([a for a in acuerdos if a.get("resultado") == "aprobado"]),
            "acuerdos_rechazados": len([a for a in acuerdos if a.get("resultado") == "rechazado"])
        }
    }


# ============================================================================
# ENDPOINTS - ASISTENCIA Y QUÓRUM
# ============================================================================

@router.post("/{asamblea_id}/asistencia", response_model=Dict[str, Any])
async def registrar_asistencia(
    asamblea_id: str,
    asistente: RegistroAsistencia
):
    """
    Registrar asistencia de copropietario
    
    Valida:
    - Asamblea existe y está en estado válido
    - Unidad no registrada previamente
    - Cálculo de quórum acumulado
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    
    # Validar estado
    if asamblea["estado"] not in [EstadoAsamblea.CONVOCADA.value, EstadoAsamblea.EN_CURSO.value]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede registrar asistencia. Estado actual: {asamblea['estado']}"
        )
    
    # Verificar no duplicado
    asistencias = asistencias_db.get(asamblea_id, [])
    if any(a["unidad_id"] == asistente.unidad_id for a in asistencias):
        raise HTTPException(
            status_code=400,
            detail="Esta unidad ya tiene asistencia registrada"
        )
    
    # Generar hash de verificación
    verificacion = hashlib.sha256(
        f"{asamblea_id}{asistente.unidad_id}{asistente.propietario_rut}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]
    
    # Crear registro
    registro = {
        "id": f"ASIS-{uuid.uuid4().hex[:8]}",
        "asamblea_id": asamblea_id,
        "unidad_id": asistente.unidad_id,
        "propietario_nombre": asistente.propietario_nombre,
        "propietario_rut": asistente.propietario_rut,
        "tipo_asistencia": asistente.tipo_asistencia.value,
        "porcentaje_derechos": float(asistente.porcentaje_derechos),
        "representante_nombre": asistente.representante_nombre,
        "representante_rut": asistente.representante_rut,
        "poder_notarial": asistente.poder_notarial,
        "hora_llegada": asistente.hora_llegada.isoformat(),
        "verificacion_hash": verificacion,
        "fecha_registro": datetime.now().isoformat()
    }
    
    asistencias_db[asamblea_id].append(registro)
    
    # Actualizar quórum
    quorum_actual = sum(a["porcentaje_derechos"] for a in asistencias_db[asamblea_id])
    asambleas_db[asamblea_id]["quorum_presente"] = quorum_actual
    asambleas_db[asamblea_id]["total_asistentes"] = len(asistencias_db[asamblea_id])
    
    # Verificar si hay quórum de constitución
    quorum_requerido = asamblea["quorum_constitucion_requerido"]
    hay_quorum = quorum_actual >= quorum_requerido
    
    return {
        "success": True,
        "registro_id": registro["id"],
        "verificacion": verificacion,
        "unidad": asistente.unidad_id,
        "derechos_registrados": f"{float(asistente.porcentaje_derechos)*100:.2f}%",
        "quorum_acumulado": f"{quorum_actual*100:.2f}%",
        "quorum_requerido": f"{quorum_requerido*100:.2f}%",
        "hay_quorum_constitucion": hay_quorum,
        "asistentes_totales": len(asistencias_db[asamblea_id])
    }


@router.get("/{asamblea_id}/quorum", response_model=Dict[str, Any])
async def verificar_quorum(asamblea_id: str):
    """
    Verificar estado de quórum según Ley 21.442
    
    Calcula:
    - Quórum de constitución
    - Quórum por tipo de materia
    - Proyección de votos necesarios
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    asistencias = asistencias_db.get(asamblea_id, [])
    
    # Calcular quórum presente
    quorum_presente = sum(a["porcentaje_derechos"] for a in asistencias)
    quorum_constitucion = asamblea["quorum_constitucion_requerido"]
    
    # Análisis por tipo de materia
    analisis_materias = {}
    for tipo, config in QUORUMS_LEGALES.items():
        if tipo in ["constitucion_primera", "constitucion_segunda"]:
            continue
        
        minimo = float(config["minimo_derechos"])
        base = config.get("base", "totales")
        
        if base == "presentes":
            # Mayoría de presentes
            alcanzable = quorum_presente > 0
            votos_necesarios = (quorum_presente * minimo) if alcanzable else 0
        else:
            # Porcentaje de derechos totales
            alcanzable = quorum_presente >= minimo
            votos_necesarios = minimo
        
        analisis_materias[tipo] = {
            "descripcion": config["descripcion"],
            "minimo_requerido": f"{minimo*100:.1f}%",
            "quorum_presente": f"{quorum_presente*100:.2f}%",
            "es_alcanzable": alcanzable,
            "materias_aplicables": config.get("materias", ["materias_generales"])
        }
    
    return {
        "asamblea_id": asamblea_id,
        "tipo_asamblea": asamblea["tipo"],
        "estado": asamblea["estado"],
        "quorum_constitucion": {
            "requerido": f"{quorum_constitucion*100:.1f}%",
            "presente": f"{quorum_presente*100:.2f}%",
            "cumple": quorum_presente >= quorum_constitucion,
            "faltante": f"{max(0, (quorum_constitucion - quorum_presente))*100:.2f}%"
        },
        "asistentes": {
            "total": len(asistencias),
            "presenciales": len([a for a in asistencias if a["tipo_asistencia"] == "presencial"]),
            "remotos": len([a for a in asistencias if a["tipo_asistencia"] == "remota"]),
            "por_poder": len([a for a in asistencias if a["tipo_asistencia"] == "poder"])
        },
        "analisis_materias": analisis_materias,
        "recomendacion": _generar_recomendacion_quorum(quorum_presente, quorum_constitucion, asamblea["tipo"])
    }


@router.post("/{asamblea_id}/iniciar", response_model=Dict[str, Any])
async def iniciar_asamblea(asamblea_id: str):
    """
    Iniciar asamblea verificando quórum de constitución
    
    Art. 19 Ley 21.442: Requiere quórum mínimo para constituirse
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    
    if asamblea["estado"] != EstadoAsamblea.CONVOCADA.value:
        raise HTTPException(
            status_code=400,
            detail=f"Solo se pueden iniciar asambleas convocadas. Estado actual: {asamblea['estado']}"
        )
    
    # Verificar quórum
    quorum_presente = asamblea.get("quorum_presente", 0)
    quorum_requerido = asamblea["quorum_constitucion_requerido"]
    
    if quorum_presente < quorum_requerido:
        return {
            "success": False,
            "mensaje": "No hay quórum suficiente para constituir la asamblea",
            "quorum_presente": f"{quorum_presente*100:.2f}%",
            "quorum_requerido": f"{quorum_requerido*100:.2f}%",
            "faltante": f"{(quorum_requerido - quorum_presente)*100:.2f}%",
            "recomendacion": "Puede convocar a segunda citación con quórum reducido (1/3 de derechos)"
        }
    
    # Iniciar asamblea
    asambleas_db[asamblea_id]["estado"] = EstadoAsamblea.EN_CURSO.value
    asambleas_db[asamblea_id]["hora_inicio_real"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "mensaje": "Asamblea iniciada exitosamente",
        "asamblea_id": asamblea_id,
        "hora_inicio": datetime.now().isoformat(),
        "quorum_constituido": f"{quorum_presente*100:.2f}%",
        "asistentes": asamblea.get("total_asistentes", 0),
        "puntos_a_tratar": len(asamblea.get("tabla_puntos", []))
    }


# ============================================================================
# ENDPOINTS - VOTACIONES
# ============================================================================

@router.post("/{asamblea_id}/votacion", response_model=Dict[str, Any])
async def iniciar_votacion(
    asamblea_id: str,
    votacion: VotacionCreate
):
    """
    Iniciar votación sobre punto de tabla
    
    Valida quórum según tipo de materia (Art. 19 Ley 21.442)
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    
    if asamblea["estado"] != EstadoAsamblea.EN_CURSO.value:
        raise HTTPException(
            status_code=400,
            detail="La asamblea debe estar en curso para votar"
        )
    
    # Buscar punto en tabla
    punto = None
    for p in asamblea.get("tabla_puntos", []):
        if p["numero"] == votacion.punto_tabla_numero:
            punto = p
            break
    
    if not punto:
        raise HTTPException(
            status_code=404,
            detail=f"Punto {votacion.punto_tabla_numero} no existe en la tabla"
        )
    
    # Crear votación
    votacion_id = f"VOT-{asamblea_id}-{votacion.punto_tabla_numero}"
    
    registro_votacion = {
        "id": votacion_id,
        "asamblea_id": asamblea_id,
        "punto_numero": votacion.punto_tabla_numero,
        "punto_titulo": punto["titulo"],
        "tipo_votacion": votacion.tipo_votacion.value,
        "descripcion_mocion": votacion.descripcion_mocion,
        "opciones": votacion.opciones,
        "quorum_requerido": punto.get("quorum_requerido", 0.5001),
        "tipo_quorum": punto.get("tipo_quorum", "mayoria_simple"),
        "votos": [],
        "estado": "abierta",
        "fecha_apertura": datetime.now().isoformat(),
        "resultado": None
    }
    
    votaciones_db[asamblea_id].append(registro_votacion)
    
    return {
        "success": True,
        "votacion_id": votacion_id,
        "punto": votacion.punto_tabla_numero,
        "titulo": punto["titulo"],
        "mocion": votacion.descripcion_mocion,
        "tipo_votacion": votacion.tipo_votacion.value,
        "opciones": votacion.opciones,
        "quorum_requerido": f"{punto.get('quorum_requerido', 0.5001)*100:.1f}%",
        "mensaje": "Votación abierta. Los asistentes pueden emitir sus votos."
    }


@router.post("/{asamblea_id}/votacion/{punto_numero}/votar", response_model=Dict[str, Any])
async def registrar_voto(
    asamblea_id: str,
    punto_numero: int,
    voto: VotoRegistro
):
    """Registrar voto individual con verificación de integridad"""
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    # Buscar votación activa
    votacion = None
    for v in votaciones_db.get(asamblea_id, []):
        if v["punto_numero"] == punto_numero and v["estado"] == "abierta":
            votacion = v
            break
    
    if not votacion:
        raise HTTPException(
            status_code=404,
            detail="No hay votación abierta para este punto"
        )
    
    # Verificar no duplicado
    if any(v["unidad_id"] == voto.unidad_id for v in votacion["votos"]):
        raise HTTPException(
            status_code=400,
            detail="Esta unidad ya emitió su voto"
        )
    
    # Verificar opción válida
    if voto.opcion_votada not in votacion["opciones"]:
        raise HTTPException(
            status_code=400,
            detail=f"Opción inválida. Opciones: {votacion['opciones']}"
        )
    
    # Generar hash de verificación
    hash_voto = hashlib.sha256(
        f"{asamblea_id}{punto_numero}{voto.unidad_id}{voto.opcion_votada}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]
    
    # Registrar voto
    registro = {
        "unidad_id": voto.unidad_id,
        "opcion": voto.opcion_votada,
        "porcentaje_derechos": float(voto.porcentaje_derechos),
        "hora_voto": datetime.now().isoformat(),
        "hash_verificacion": hash_voto
    }
    
    votacion["votos"].append(registro)
    
    # Calcular parciales
    parciales = _calcular_resultados_votacion(votacion)
    
    return {
        "success": True,
        "voto_registrado": True,
        "hash_verificacion": hash_voto,
        "parciales": parciales,
        "votos_emitidos": len(votacion["votos"])
    }


@router.post("/{asamblea_id}/votacion/{punto_numero}/cerrar", response_model=Dict[str, Any])
async def cerrar_votacion(
    asamblea_id: str,
    punto_numero: int
):
    """
    Cerrar votación y calcular resultado según quórum requerido
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    # Buscar votación
    votacion = None
    for v in votaciones_db.get(asamblea_id, []):
        if v["punto_numero"] == punto_numero and v["estado"] == "abierta":
            votacion = v
            break
    
    if not votacion:
        raise HTTPException(
            status_code=404,
            detail="No hay votación abierta para este punto"
        )
    
    # Calcular resultados finales
    resultados = _calcular_resultados_votacion(votacion)
    
    # Determinar resultado según quórum
    quorum_requerido = votacion["quorum_requerido"]
    votos_favor = resultados["por_opcion"].get("A favor", 0)
    votos_contra = resultados["por_opcion"].get("En contra", 0)
    abstenciones = resultados["por_opcion"].get("Abstención", 0)
    
    # Lógica según tipo de quórum
    tipo_quorum = votacion["tipo_quorum"]
    if tipo_quorum == "mayoria_simple":
        # Mayoría de presentes que votan
        total_votantes = votos_favor + votos_contra
        aprobado = votos_favor > votos_contra if total_votantes > 0 else False
    else:
        # Porcentaje de derechos totales
        aprobado = votos_favor >= quorum_requerido
    
    if votos_favor == votos_contra and votos_favor > 0:
        resultado_final = ResultadoVotacion.EMPATE.value
    elif aprobado:
        resultado_final = ResultadoVotacion.APROBADO.value
    else:
        resultado_final = ResultadoVotacion.RECHAZADO.value
    
    # Actualizar votación
    votacion["estado"] = "cerrada"
    votacion["fecha_cierre"] = datetime.now().isoformat()
    votacion["resultado"] = resultado_final
    votacion["resultados_finales"] = resultados
    
    # Actualizar punto en tabla
    for punto in asambleas_db[asamblea_id]["tabla_puntos"]:
        if punto["numero"] == punto_numero:
            punto["estado"] = "tratado"
            punto["resultado_votacion"] = resultado_final
            break
    
    # Crear acuerdo automático si aprobado
    if resultado_final == ResultadoVotacion.APROBADO.value:
        acuerdo = {
            "id": f"ACU-{asamblea_id}-{punto_numero}",
            "punto_numero": punto_numero,
            "descripcion": votacion["descripcion_mocion"],
            "votos_favor": votos_favor,
            "votos_contra": votos_contra,
            "abstenciones": abstenciones,
            "porcentaje_aprobacion": f"{votos_favor*100:.2f}%",
            "resultado": resultado_final,
            "fecha_acuerdo": datetime.now().isoformat(),
            "estado_ejecucion": "pendiente"
        }
        acuerdos_db[asamblea_id].append(acuerdo)
    
    return {
        "success": True,
        "votacion_cerrada": True,
        "punto": punto_numero,
        "titulo": votacion["punto_titulo"],
        "mocion": votacion["descripcion_mocion"],
        "resultados": {
            "a_favor": f"{votos_favor*100:.2f}%",
            "en_contra": f"{votos_contra*100:.2f}%",
            "abstenciones": f"{abstenciones*100:.2f}%",
            "total_participacion": f"{resultados['total_participacion']*100:.2f}%"
        },
        "quorum_requerido": f"{quorum_requerido*100:.1f}%",
        "resultado_final": resultado_final,
        "acuerdo_generado": resultado_final == ResultadoVotacion.APROBADO.value
    }


# ============================================================================
# ENDPOINTS - ACTAS Y ACUERDOS
# ============================================================================

@router.post("/{asamblea_id}/finalizar", response_model=Dict[str, Any])
async def finalizar_asamblea(
    asamblea_id: str,
    presidente: str,
    secretario: str,
    observaciones: Optional[str] = None
):
    """
    Finalizar asamblea y preparar acta
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    
    if asamblea["estado"] != EstadoAsamblea.EN_CURSO.value:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden finalizar asambleas en curso"
        )
    
    # Actualizar estado
    asambleas_db[asamblea_id]["estado"] = EstadoAsamblea.ACTA_PENDIENTE.value
    asambleas_db[asamblea_id]["hora_termino"] = datetime.now().isoformat()
    asambleas_db[asamblea_id]["presidente"] = presidente
    asambleas_db[asamblea_id]["secretario"] = secretario
    
    # Generar resumen
    votaciones = votaciones_db.get(asamblea_id, [])
    acuerdos = acuerdos_db.get(asamblea_id, [])
    asistencias = asistencias_db.get(asamblea_id, [])
    
    resumen = {
        "asamblea_id": asamblea_id,
        "tipo": asamblea["tipo"],
        "fecha": asamblea["fecha_asamblea"],
        "duracion": _calcular_duracion(
            asamblea.get("hora_inicio_real"),
            datetime.now().isoformat()
        ),
        "asistentes": len(asistencias),
        "quorum_final": f"{asamblea.get('quorum_presente', 0)*100:.2f}%",
        "puntos_tratados": len([p for p in asamblea["tabla_puntos"] if p.get("estado") == "tratado"]),
        "puntos_pendientes": len([p for p in asamblea["tabla_puntos"] if p.get("estado") == "pendiente"]),
        "votaciones_realizadas": len(votaciones),
        "acuerdos_aprobados": len([a for a in acuerdos if a["resultado"] == "aprobado"]),
        "presidente": presidente,
        "secretario": secretario,
        "observaciones": observaciones
    }
    
    return {
        "success": True,
        "mensaje": "Asamblea finalizada. Acta pendiente de aprobación.",
        "resumen": resumen
    }


@router.post("/{asamblea_id}/acta", response_model=Dict[str, Any])
async def generar_acta(asamblea_id: str):
    """
    Generar acta oficial de asamblea según formato Ley 21.442
    
    Art. 20: El acta debe contener resumen de lo tratado, acuerdos adoptados,
    constancia de votos, y ser firmada por quienes presidieron.
    """
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    asamblea = asambleas_db[asamblea_id]
    asistencias = asistencias_db.get(asamblea_id, [])
    votaciones = votaciones_db.get(asamblea_id, [])
    acuerdos = acuerdos_db.get(asamblea_id, [])
    
    # Generar número de acta
    numero_acta = f"ACTA-{asamblea['copropiedad_id'][:8]}-{datetime.now().strftime('%Y%m%d')}-001"
    
    acta = {
        "numero_acta": numero_acta,
        "asamblea_id": asamblea_id,
        "fecha_generacion": datetime.now().isoformat(),
        
        # Encabezado
        "encabezado": {
            "tipo_asamblea": asamblea["tipo"],
            "copropiedad_id": asamblea["copropiedad_id"],
            "fecha_celebracion": asamblea["fecha_asamblea"],
            "hora_inicio": asamblea.get("hora_inicio_real", asamblea["hora_inicio"]),
            "hora_termino": asamblea.get("hora_termino"),
            "lugar": asamblea["lugar"],
            "modalidad": asamblea["modalidad"],
            "presidente": asamblea.get("presidente", "Por designar"),
            "secretario": asamblea.get("secretario", "Por designar")
        },
        
        # Quórum
        "quorum": {
            "requerido": f"{asamblea['quorum_constitucion_requerido']*100:.1f}%",
            "presente": f"{asamblea.get('quorum_presente', 0)*100:.2f}%",
            "constituido": asamblea.get("quorum_presente", 0) >= asamblea["quorum_constitucion_requerido"]
        },
        
        # Asistencia
        "asistencia": {
            "total_asistentes": len(asistencias),
            "derechos_representados": f"{sum(a['porcentaje_derechos'] for a in asistencias)*100:.2f}%",
            "presenciales": len([a for a in asistencias if a["tipo_asistencia"] == "presencial"]),
            "remotos": len([a for a in asistencias if a["tipo_asistencia"] == "remota"]),
            "por_poder": len([a for a in asistencias if a["tipo_asistencia"] == "poder"]),
            "listado": [
                {
                    "unidad": a["unidad_id"],
                    "propietario": a["propietario_nombre"],
                    "derechos": f"{a['porcentaje_derechos']*100:.2f}%",
                    "tipo": a["tipo_asistencia"]
                }
                for a in asistencias
            ]
        },
        
        # Tabla tratada
        "tabla_materias": [
            {
                "numero": p["numero"],
                "titulo": p["titulo"],
                "estado": p.get("estado", "pendiente"),
                "resultado": p.get("resultado_votacion")
            }
            for p in asamblea.get("tabla_puntos", [])
        ],
        
        # Votaciones
        "votaciones": [
            {
                "punto": v["punto_numero"],
                "mocion": v["descripcion_mocion"],
                "tipo": v["tipo_votacion"],
                "resultado": v.get("resultado"),
                "detalles": v.get("resultados_finales", {})
            }
            for v in votaciones
        ],
        
        # Acuerdos
        "acuerdos": [
            {
                "numero": i + 1,
                "punto_relacionado": a["punto_numero"],
                "descripcion": a["descripcion"],
                "votos_favor": a["votos_favor"],
                "votos_contra": a["votos_contra"],
                "abstenciones": a["abstenciones"],
                "resultado": a["resultado"]
            }
            for i, a in enumerate(acuerdos)
        ],
        
        # Certificación
        "certificacion": {
            "texto": f"Certifico que la presente acta es fiel reflejo de lo acontecido en la "
                     f"Asamblea {asamblea['tipo'].title()} celebrada el {asamblea['fecha_asamblea']}, "
                     f"conforme a lo dispuesto en la Ley 21.442 sobre Copropiedad Inmobiliaria.",
            "firma_presidente": None,
            "firma_secretario": None,
            "fecha_certificacion": None
        },
        
        "estado": "borrador",
        "hash_integridad": hashlib.sha256(
            f"{numero_acta}{asamblea_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()
    }
    
    actas_db[asamblea_id] = acta
    
    return {
        "success": True,
        "numero_acta": numero_acta,
        "acta": acta,
        "mensaje": "Acta generada en estado borrador. Requiere firmas para aprobación."
    }


@router.post("/{asamblea_id}/acta/aprobar", response_model=Dict[str, Any])
async def aprobar_acta(
    asamblea_id: str,
    firma_presidente: str,
    firma_secretario: str
):
    """
    Aprobar y firmar acta de asamblea
    """
    if asamblea_id not in actas_db:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    
    acta = actas_db[asamblea_id]
    
    # Registrar firmas
    acta["certificacion"]["firma_presidente"] = firma_presidente
    acta["certificacion"]["firma_secretario"] = firma_secretario
    acta["certificacion"]["fecha_certificacion"] = datetime.now().isoformat()
    acta["estado"] = "aprobada"
    
    # Actualizar estado asamblea
    asambleas_db[asamblea_id]["estado"] = EstadoAsamblea.ACTA_APROBADA.value
    
    # Generar hash final
    acta["hash_final"] = hashlib.sha256(
        f"{acta['numero_acta']}{firma_presidente}{firma_secretario}{datetime.now().isoformat()}".encode()
    ).hexdigest()
    
    return {
        "success": True,
        "mensaje": "Acta aprobada y firmada",
        "numero_acta": acta["numero_acta"],
        "hash_integridad": acta["hash_final"],
        "firmantes": {
            "presidente": firma_presidente,
            "secretario": firma_secretario
        },
        "fecha_aprobacion": datetime.now().isoformat()
    }


@router.get("/{asamblea_id}/acuerdos", response_model=Dict[str, Any])
async def listar_acuerdos(asamblea_id: str):
    """Listar acuerdos de asamblea"""
    if asamblea_id not in asambleas_db:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    
    acuerdos = acuerdos_db.get(asamblea_id, [])
    
    return {
        "asamblea_id": asamblea_id,
        "total_acuerdos": len(acuerdos),
        "aprobados": len([a for a in acuerdos if a["resultado"] == "aprobado"]),
        "acuerdos": acuerdos
    }


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS Y REPORTES
# ============================================================================

@router.get("/estadisticas/{copropiedad_id}", response_model=Dict[str, Any])
async def estadisticas_asambleas(
    copropiedad_id: str,
    year: Optional[int] = None
):
    """Estadísticas de asambleas de una copropiedad"""
    asambleas = [a for a in asambleas_db.values() if a["copropiedad_id"] == copropiedad_id]
    
    if year:
        asambleas = [a for a in asambleas if a["fecha_asamblea"].startswith(str(year))]
    
    if not asambleas:
        return {
            "copropiedad_id": copropiedad_id,
            "mensaje": "No hay asambleas registradas",
            "estadisticas": None
        }
    
    # Calcular estadísticas
    total = len(asambleas)
    por_tipo = {}
    por_estado = {}
    quorums = []
    acuerdos_total = 0
    
    for asamblea in asambleas:
        tipo = asamblea["tipo"]
        estado = asamblea["estado"]
        
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        por_estado[estado] = por_estado.get(estado, 0) + 1
        
        if asamblea.get("quorum_presente"):
            quorums.append(asamblea["quorum_presente"])
        
        acuerdos_total += len(acuerdos_db.get(asamblea["id"], []))
    
    return {
        "copropiedad_id": copropiedad_id,
        "periodo": year or "todos",
        "estadisticas": {
            "total_asambleas": total,
            "por_tipo": por_tipo,
            "por_estado": por_estado,
            "quorum_promedio": f"{(sum(quorums)/len(quorums)*100):.2f}%" if quorums else "N/A",
            "total_acuerdos": acuerdos_total,
            "cumplimiento_legal": {
                "ordinarias_anuales": por_tipo.get("ordinaria", 0) >= 1,
                "actas_aprobadas": por_estado.get("acta_aprobada", 0)
            }
        }
    }


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _determinar_quorum_punto(tipo_quorum: str) -> float:
    """Determinar porcentaje de quórum según tipo"""
    quorums = {
        "mayoria_simple": 0.5001,
        "mayoria_absoluta": 0.5001,
        "dos_tercios": 0.6667,
        "tres_cuartos": 0.75,
        "unanimidad": 1.0
    }
    return quorums.get(tipo_quorum, 0.5001)


def _calcular_resultados_votacion(votacion: Dict) -> Dict[str, Any]:
    """Calcular resultados de votación"""
    votos = votacion.get("votos", [])
    
    por_opcion = {}
    for voto in votos:
        opcion = voto["opcion"]
        derechos = voto["porcentaje_derechos"]
        por_opcion[opcion] = por_opcion.get(opcion, 0) + derechos
    
    total_participacion = sum(v["porcentaje_derechos"] for v in votos)
    
    return {
        "total_votos": len(votos),
        "total_participacion": total_participacion,
        "por_opcion": por_opcion
    }


def _generar_recomendacion_quorum(presente: float, requerido: float, tipo: str) -> str:
    """Generar recomendación según estado de quórum"""
    if presente >= requerido:
        return "Quórum suficiente para constituir asamblea y votar materias según tabla."
    
    faltante = requerido - presente
    if faltante <= 0.1:
        return f"Falta {faltante*100:.1f}% para quórum. Se recomienda esperar más asistentes."
    
    if tipo == "ordinaria":
        return f"Falta {faltante*100:.1f}% para quórum. Puede convocar segunda citación con quórum reducido."
    
    return f"Falta {faltante*100:.1f}% para constituir asamblea. Revise lista de convocados."


def _calcular_duracion(inicio: str, fin: str) -> str:
    """Calcular duración de asamblea"""
    try:
        inicio_dt = datetime.fromisoformat(inicio)
        fin_dt = datetime.fromisoformat(fin)
        duracion = fin_dt - inicio_dt
        horas = duracion.seconds // 3600
        minutos = (duracion.seconds % 3600) // 60
        return f"{horas}h {minutos}min"
    except:
        return "N/A"


async def _enviar_convocatorias(asamblea_id: str, copropiedad_id: str):
    """Tarea background para enviar convocatorias"""
    # En producción: integrar con servicio de comunicaciones
    print(f"Enviando convocatorias asamblea {asamblea_id} a copropiedad {copropiedad_id}")
