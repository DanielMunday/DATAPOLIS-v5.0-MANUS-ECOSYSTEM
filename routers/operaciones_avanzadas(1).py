# satisfactiva/backend/app/routers/operaciones_avanzadas.py
"""
DATAPOLIS v3.0 - ROUTERS M18-M22 CONSOLIDADOS
M18: Seguridad | M19: Conciliación Bancaria | M20: Presupuestos
M21: Cobranza | M22: Auditoría Interna
Autor: Cascade AI para DATAPOLIS SpA
Fecha: 2026-02-01
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import hashlib

# ============================================================================
# M18: SEGURIDAD
# ============================================================================

router_seguridad = APIRouter(prefix="/seguridad", tags=["M18 - Seguridad"])

class TipoIncidente(str, Enum):
    ROBO = "robo"
    VANDALISMO = "vandalismo"
    EMERGENCIA_MEDICA = "emergencia_medica"
    INCENDIO = "incendio"
    SISMO = "sismo"
    INUNDACION = "inundacion"
    RUIDOS_MOLESTOS = "ruidos_molestos"
    PELEA = "pelea"
    ACCIDENTE = "accidente"
    INTRUSION = "intrusion"
    OTRO = "otro"

class GravedadIncidente(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class EstadoIncidente(str, Enum):
    REPORTADO = "reportado"
    EN_ATENCION = "en_atencion"
    RESUELTO = "resuelto"
    ESCALADO = "escalado"
    CERRADO = "cerrado"

class IncidenteCreate(BaseModel):
    copropiedad_id: str
    tipo: TipoIncidente
    gravedad: GravedadIncidente
    ubicacion: str
    descripcion: str
    reportado_por: str
    unidad_afectada: Optional[str] = None
    testigos: List[str] = []
    requiere_policia: bool = False
    requiere_ambulancia: bool = False
    requiere_bomberos: bool = False

class RondaCreate(BaseModel):
    copropiedad_id: str
    guardia_id: str
    guardia_nombre: str
    puntos_control: List[str]
    observaciones: Optional[str] = None

incidentes_db: Dict[str, Dict] = {}
rondas_db: Dict[str, Dict] = {}
alertas_seguridad_db: List[Dict] = []

@router_seguridad.post("/incidentes", response_model=Dict[str, Any])
async def reportar_incidente(incidente: IncidenteCreate):
    """Reportar incidente de seguridad"""
    incidente_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    
    registro = {
        "id": incidente_id,
        "copropiedad_id": incidente.copropiedad_id,
        "tipo": incidente.tipo.value,
        "gravedad": incidente.gravedad.value,
        "ubicacion": incidente.ubicacion,
        "descripcion": incidente.descripcion,
        "reportado_por": incidente.reportado_por,
        "unidad_afectada": incidente.unidad_afectada,
        "testigos": incidente.testigos,
        "requiere_policia": incidente.requiere_policia,
        "requiere_ambulancia": incidente.requiere_ambulancia,
        "requiere_bomberos": incidente.requiere_bomberos,
        "estado": EstadoIncidente.REPORTADO.value,
        "fecha_reporte": datetime.now().isoformat(),
        "fecha_resolucion": None,
        "acciones_tomadas": [],
        "evidencias": []
    }
    
    incidentes_db[incidente_id] = registro
    
    # Generar alerta si es crítico
    if incidente.gravedad == GravedadIncidente.CRITICA:
        alertas_seguridad_db.append({
            "id": f"ALT-{uuid.uuid4().hex[:6]}",
            "incidente_id": incidente_id,
            "tipo": "CRITICO",
            "mensaje": f"Incidente crítico: {incidente.tipo.value} en {incidente.ubicacion}",
            "fecha": datetime.now().isoformat(),
            "atendida": False
        })
    
    return {
        "success": True,
        "incidente_id": incidente_id,
        "gravedad": incidente.gravedad.value,
        "servicios_emergencia": {
            "policia": incidente.requiere_policia,
            "ambulancia": incidente.requiere_ambulancia,
            "bomberos": incidente.requiere_bomberos
        },
        "mensaje": "Incidente reportado. Se notificará a los responsables."
    }

@router_seguridad.get("/incidentes", response_model=Dict[str, Any])
async def listar_incidentes(
    copropiedad_id: str,
    tipo: Optional[TipoIncidente] = None,
    gravedad: Optional[GravedadIncidente] = None,
    estado: Optional[EstadoIncidente] = None,
    fecha_desde: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Listar incidentes con filtros"""
    resultados = [i for i in incidentes_db.values() if i["copropiedad_id"] == copropiedad_id]
    
    if tipo:
        resultados = [i for i in resultados if i["tipo"] == tipo.value]
    if gravedad:
        resultados = [i for i in resultados if i["gravedad"] == gravedad.value]
    if estado:
        resultados = [i for i in resultados if i["estado"] == estado.value]
    if fecha_desde:
        resultados = [i for i in resultados if i["fecha_reporte"][:10] >= fecha_desde.isoformat()]
    
    resultados.sort(key=lambda x: x["fecha_reporte"], reverse=True)
    
    return {"total": len(resultados), "incidentes": resultados[:limit]}

@router_seguridad.post("/incidentes/{incidente_id}/accion", response_model=Dict[str, Any])
async def registrar_accion_incidente(
    incidente_id: str,
    accion: str,
    responsable: str
):
    """Registrar acción tomada en incidente"""
    if incidente_id not in incidentes_db:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    incidente = incidentes_db[incidente_id]
    incidente["acciones_tomadas"].append({
        "accion": accion,
        "responsable": responsable,
        "fecha": datetime.now().isoformat()
    })
    
    return {"success": True, "mensaje": "Acción registrada"}

@router_seguridad.post("/incidentes/{incidente_id}/resolver", response_model=Dict[str, Any])
async def resolver_incidente(
    incidente_id: str,
    resolucion: str
):
    """Marcar incidente como resuelto"""
    if incidente_id not in incidentes_db:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    
    incidente = incidentes_db[incidente_id]
    incidente["estado"] = EstadoIncidente.RESUELTO.value
    incidente["fecha_resolucion"] = datetime.now().isoformat()
    incidente["resolucion"] = resolucion
    
    return {"success": True, "mensaje": "Incidente resuelto"}

@router_seguridad.post("/rondas", response_model=Dict[str, Any])
async def registrar_ronda(ronda: RondaCreate):
    """Registrar ronda de vigilancia"""
    ronda_id = f"RON-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    registro = {
        "id": ronda_id,
        "copropiedad_id": ronda.copropiedad_id,
        "guardia_id": ronda.guardia_id,
        "guardia_nombre": ronda.guardia_nombre,
        "fecha_inicio": datetime.now().isoformat(),
        "fecha_fin": None,
        "puntos_control": [
            {"punto": p, "verificado": False, "hora": None}
            for p in ronda.puntos_control
        ],
        "observaciones": ronda.observaciones,
        "incidentes_reportados": [],
        "estado": "en_curso"
    }
    
    rondas_db[ronda_id] = registro
    
    return {
        "success": True,
        "ronda_id": ronda_id,
        "puntos_control": len(ronda.puntos_control),
        "mensaje": "Ronda iniciada"
    }

@router_seguridad.post("/rondas/{ronda_id}/punto/{punto}", response_model=Dict[str, Any])
async def verificar_punto_control(ronda_id: str, punto: str, novedad: Optional[str] = None):
    """Verificar punto de control en ronda"""
    if ronda_id not in rondas_db:
        raise HTTPException(status_code=404, detail="Ronda no encontrada")
    
    ronda = rondas_db[ronda_id]
    
    for p in ronda["puntos_control"]:
        if p["punto"] == punto:
            p["verificado"] = True
            p["hora"] = datetime.now().isoformat()
            p["novedad"] = novedad
            break
    
    verificados = len([p for p in ronda["puntos_control"] if p["verificado"]])
    
    return {
        "success": True,
        "punto": punto,
        "verificados": verificados,
        "total": len(ronda["puntos_control"]),
        "progreso": f"{(verificados/len(ronda['puntos_control'])*100):.0f}%"
    }

@router_seguridad.get("/estadisticas/{copropiedad_id}", response_model=Dict[str, Any])
async def estadisticas_seguridad(copropiedad_id: str, dias: int = 30):
    """Estadísticas de seguridad"""
    fecha_desde = (datetime.now() - timedelta(days=dias)).isoformat()
    
    incidentes = [
        i for i in incidentes_db.values()
        if i["copropiedad_id"] == copropiedad_id and i["fecha_reporte"] >= fecha_desde
    ]
    
    rondas = [
        r for r in rondas_db.values()
        if r["copropiedad_id"] == copropiedad_id and r["fecha_inicio"] >= fecha_desde
    ]
    
    por_tipo = {}
    por_gravedad = {}
    for inc in incidentes:
        por_tipo[inc["tipo"]] = por_tipo.get(inc["tipo"], 0) + 1
        por_gravedad[inc["gravedad"]] = por_gravedad.get(inc["gravedad"], 0) + 1
    
    return {
        "periodo_dias": dias,
        "incidentes": {
            "total": len(incidentes),
            "por_tipo": por_tipo,
            "por_gravedad": por_gravedad,
            "criticos": por_gravedad.get("critica", 0),
            "resueltos": len([i for i in incidentes if i["estado"] == "resuelto"])
        },
        "rondas": {
            "total": len(rondas),
            "completadas": len([r for r in rondas if r["estado"] == "completada"])
        }
    }

# ============================================================================
# M19: CONCILIACIÓN BANCARIA
# ============================================================================

router_conciliacion = APIRouter(prefix="/conciliacion", tags=["M19 - Conciliación Bancaria"])

class TipoMovimientoBanco(str, Enum):
    DEPOSITO = "deposito"
    TRANSFERENCIA = "transferencia"
    CHEQUE = "cheque"
    CARGO = "cargo"
    ABONO = "abono"
    COMISION = "comision"
    IMPUESTO = "impuesto"

class EstadoConciliacion(str, Enum):
    PENDIENTE = "pendiente"
    CONCILIADO = "conciliado"
    PARCIAL = "parcial"
    NO_IDENTIFICADO = "no_identificado"

class MovimientoBancario(BaseModel):
    fecha: date
    descripcion: str
    referencia: Optional[str] = None
    tipo: TipoMovimientoBanco
    monto: Decimal
    saldo: Optional[Decimal] = None

class ImportarCartola(BaseModel):
    copropiedad_id: str
    cuenta_bancaria: str
    banco: str
    periodo: str  # YYYY-MM
    movimientos: List[MovimientoBancario]

movimientos_banco_db: Dict[str, List[Dict]] = {}
conciliaciones_db: Dict[str, Dict] = {}

@router_conciliacion.post("/importar-cartola", response_model=Dict[str, Any])
async def importar_cartola(datos: ImportarCartola):
    """Importar cartola bancaria para conciliación"""
    cartola_id = f"CART-{datos.copropiedad_id[:6]}-{datos.periodo}"
    
    movimientos_procesados = []
    for mov in datos.movimientos:
        registro = {
            "id": f"MOV-{uuid.uuid4().hex[:8]}",
            "fecha": mov.fecha.isoformat(),
            "descripcion": mov.descripcion,
            "referencia": mov.referencia,
            "tipo": mov.tipo.value,
            "monto": float(mov.monto),
            "saldo": float(mov.saldo) if mov.saldo else None,
            "estado_conciliacion": EstadoConciliacion.PENDIENTE.value,
            "documento_asociado": None
        }
        movimientos_procesados.append(registro)
    
    if cartola_id not in movimientos_banco_db:
        movimientos_banco_db[cartola_id] = []
    
    movimientos_banco_db[cartola_id].extend(movimientos_procesados)
    
    return {
        "success": True,
        "cartola_id": cartola_id,
        "movimientos_importados": len(movimientos_procesados),
        "banco": datos.banco,
        "cuenta": datos.cuenta_bancaria,
        "periodo": datos.periodo
    }

@router_conciliacion.post("/conciliar-automatico/{cartola_id}", response_model=Dict[str, Any])
async def conciliar_automatico(cartola_id: str):
    """Conciliación automática de movimientos"""
    if cartola_id not in movimientos_banco_db:
        raise HTTPException(status_code=404, detail="Cartola no encontrada")
    
    movimientos = movimientos_banco_db[cartola_id]
    conciliados = 0
    no_identificados = 0
    
    for mov in movimientos:
        if mov["estado_conciliacion"] == EstadoConciliacion.PENDIENTE.value:
            # Intentar matching por referencia
            if mov["referencia"]:
                # Simular búsqueda en sistema contable
                mov["estado_conciliacion"] = EstadoConciliacion.CONCILIADO.value
                mov["documento_asociado"] = f"DOC-{mov['referencia']}"
                conciliados += 1
            else:
                mov["estado_conciliacion"] = EstadoConciliacion.NO_IDENTIFICADO.value
                no_identificados += 1
    
    return {
        "success": True,
        "cartola_id": cartola_id,
        "total_movimientos": len(movimientos),
        "conciliados_automatico": conciliados,
        "no_identificados": no_identificados,
        "pendientes_revision": len([m for m in movimientos if m["estado_conciliacion"] == EstadoConciliacion.PENDIENTE.value])
    }

@router_conciliacion.post("/conciliar-manual", response_model=Dict[str, Any])
async def conciliar_manual(
    cartola_id: str,
    movimiento_id: str,
    documento_contable_id: str
):
    """Conciliación manual de movimiento"""
    if cartola_id not in movimientos_banco_db:
        raise HTTPException(status_code=404, detail="Cartola no encontrada")
    
    for mov in movimientos_banco_db[cartola_id]:
        if mov["id"] == movimiento_id:
            mov["estado_conciliacion"] = EstadoConciliacion.CONCILIADO.value
            mov["documento_asociado"] = documento_contable_id
            mov["conciliacion_manual"] = True
            mov["fecha_conciliacion"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "movimiento_id": movimiento_id,
                "documento_asociado": documento_contable_id,
                "mensaje": "Movimiento conciliado manualmente"
            }
    
    raise HTTPException(status_code=404, detail="Movimiento no encontrado")

@router_conciliacion.get("/reporte/{cartola_id}", response_model=Dict[str, Any])
async def generar_reporte_conciliacion(cartola_id: str):
    """Generar reporte de conciliación bancaria"""
    if cartola_id not in movimientos_banco_db:
        raise HTTPException(status_code=404, detail="Cartola no encontrada")
    
    movimientos = movimientos_banco_db[cartola_id]
    
    # Calcular totales
    total_abonos = sum(m["monto"] for m in movimientos if m["monto"] > 0)
    total_cargos = sum(abs(m["monto"]) for m in movimientos if m["monto"] < 0)
    
    por_estado = {}
    for mov in movimientos:
        estado = mov["estado_conciliacion"]
        por_estado[estado] = por_estado.get(estado, 0) + 1
    
    pendientes = [m for m in movimientos if m["estado_conciliacion"] != EstadoConciliacion.CONCILIADO.value]
    
    return {
        "cartola_id": cartola_id,
        "fecha_reporte": datetime.now().isoformat(),
        "resumen": {
            "total_movimientos": len(movimientos),
            "total_abonos": total_abonos,
            "total_cargos": total_cargos,
            "saldo_neto": total_abonos - total_cargos
        },
        "conciliacion": {
            "por_estado": por_estado,
            "tasa_conciliacion": (por_estado.get("conciliado", 0) / len(movimientos) * 100) if movimientos else 0
        },
        "pendientes": pendientes,
        "observaciones": f"{len(pendientes)} movimientos pendientes de conciliar"
    }

# ============================================================================
# M20: PRESUPUESTOS
# ============================================================================

router_presupuestos = APIRouter(prefix="/presupuestos", tags=["M20 - Presupuestos"])

class TipoPresupuesto(str, Enum):
    ANUAL = "anual"
    EXTRAORDINARIO = "extraordinario"
    PROYECTO = "proyecto"

class EstadoPresupuesto(str, Enum):
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    EN_EJECUCION = "en_ejecucion"
    CERRADO = "cerrado"

class LineaPresupuesto(BaseModel):
    categoria: str
    subcategoria: Optional[str] = None
    descripcion: str
    montos_mensuales: List[Decimal]  # 12 meses
    cuenta_contable: Optional[str] = None

class PresupuestoCreate(BaseModel):
    copropiedad_id: str
    tipo: TipoPresupuesto
    nombre: str
    anio: int
    lineas: List[LineaPresupuesto]
    observaciones: Optional[str] = None

presupuestos_db: Dict[str, Dict] = {}
ejecucion_db: Dict[str, List[Dict]] = {}

@router_presupuestos.post("/", response_model=Dict[str, Any])
async def crear_presupuesto(presupuesto: PresupuestoCreate):
    """Crear presupuesto anual o extraordinario"""
    presupuesto_id = f"PRES-{presupuesto.copropiedad_id[:6]}-{presupuesto.anio}"
    
    lineas_procesadas = []
    total_anual = Decimal(0)
    
    for linea in presupuesto.lineas:
        total_linea = sum(linea.montos_mensuales)
        linea_dict = {
            "id": f"LIN-{uuid.uuid4().hex[:6]}",
            "categoria": linea.categoria,
            "subcategoria": linea.subcategoria,
            "descripcion": linea.descripcion,
            "montos_mensuales": [float(m) for m in linea.montos_mensuales],
            "total_anual": float(total_linea),
            "cuenta_contable": linea.cuenta_contable,
            "ejecutado": [0] * 12
        }
        lineas_procesadas.append(linea_dict)
        total_anual += total_linea
    
    registro = {
        "id": presupuesto_id,
        "copropiedad_id": presupuesto.copropiedad_id,
        "tipo": presupuesto.tipo.value,
        "nombre": presupuesto.nombre,
        "anio": presupuesto.anio,
        "lineas": lineas_procesadas,
        "total_anual": float(total_anual),
        "estado": EstadoPresupuesto.BORRADOR.value,
        "fecha_creacion": datetime.now().isoformat(),
        "observaciones": presupuesto.observaciones
    }
    
    presupuestos_db[presupuesto_id] = registro
    ejecucion_db[presupuesto_id] = []
    
    return {
        "success": True,
        "presupuesto_id": presupuesto_id,
        "total_anual": float(total_anual),
        "lineas": len(lineas_procesadas),
        "estado": "borrador"
    }

@router_presupuestos.get("/", response_model=Dict[str, Any])
async def listar_presupuestos(
    copropiedad_id: str,
    anio: Optional[int] = None,
    tipo: Optional[TipoPresupuesto] = None
):
    """Listar presupuestos"""
    resultados = [p for p in presupuestos_db.values() if p["copropiedad_id"] == copropiedad_id]
    
    if anio:
        resultados = [p for p in resultados if p["anio"] == anio]
    if tipo:
        resultados = [p for p in resultados if p["tipo"] == tipo.value]
    
    return {"total": len(resultados), "presupuestos": resultados}

@router_presupuestos.get("/{presupuesto_id}", response_model=Dict[str, Any])
async def obtener_presupuesto(presupuesto_id: str):
    """Obtener detalle de presupuesto"""
    if presupuesto_id not in presupuestos_db:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    return presupuestos_db[presupuesto_id]

@router_presupuestos.post("/{presupuesto_id}/aprobar", response_model=Dict[str, Any])
async def aprobar_presupuesto(presupuesto_id: str, aprobado_por: str):
    """Aprobar presupuesto"""
    if presupuesto_id not in presupuestos_db:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    presupuesto = presupuestos_db[presupuesto_id]
    presupuesto["estado"] = EstadoPresupuesto.APROBADO.value
    presupuesto["fecha_aprobacion"] = datetime.now().isoformat()
    presupuesto["aprobado_por"] = aprobado_por
    
    return {"success": True, "mensaje": "Presupuesto aprobado"}

@router_presupuestos.post("/{presupuesto_id}/registrar-gasto", response_model=Dict[str, Any])
async def registrar_gasto(
    presupuesto_id: str,
    linea_id: str,
    mes: int,
    monto: Decimal,
    descripcion: str
):
    """Registrar gasto ejecutado contra presupuesto"""
    if presupuesto_id not in presupuestos_db:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    presupuesto = presupuestos_db[presupuesto_id]
    
    for linea in presupuesto["lineas"]:
        if linea["id"] == linea_id:
            linea["ejecutado"][mes - 1] += float(monto)
            
            # Registrar detalle
            ejecucion_db[presupuesto_id].append({
                "linea_id": linea_id,
                "mes": mes,
                "monto": float(monto),
                "descripcion": descripcion,
                "fecha": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "presupuestado": linea["montos_mensuales"][mes - 1],
                "ejecutado": linea["ejecutado"][mes - 1],
                "disponible": linea["montos_mensuales"][mes - 1] - linea["ejecutado"][mes - 1]
            }
    
    raise HTTPException(status_code=404, detail="Línea no encontrada")

@router_presupuestos.get("/{presupuesto_id}/ejecucion", response_model=Dict[str, Any])
async def obtener_ejecucion(presupuesto_id: str, mes: Optional[int] = None):
    """Obtener reporte de ejecución presupuestaria"""
    if presupuesto_id not in presupuestos_db:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    presupuesto = presupuestos_db[presupuesto_id]
    
    resumen = []
    total_presupuestado = 0
    total_ejecutado = 0
    
    for linea in presupuesto["lineas"]:
        if mes:
            presupuestado = linea["montos_mensuales"][mes - 1]
            ejecutado = linea["ejecutado"][mes - 1]
        else:
            presupuestado = sum(linea["montos_mensuales"])
            ejecutado = sum(linea["ejecutado"])
        
        variacion = ejecutado - presupuestado
        porcentaje = (ejecutado / presupuestado * 100) if presupuestado > 0 else 0
        
        resumen.append({
            "linea_id": linea["id"],
            "categoria": linea["categoria"],
            "descripcion": linea["descripcion"],
            "presupuestado": presupuestado,
            "ejecutado": ejecutado,
            "variacion": variacion,
            "porcentaje_ejecucion": round(porcentaje, 1)
        })
        
        total_presupuestado += presupuestado
        total_ejecutado += ejecutado
    
    return {
        "presupuesto_id": presupuesto_id,
        "periodo": f"Mes {mes}" if mes else "Anual",
        "total_presupuestado": total_presupuestado,
        "total_ejecutado": total_ejecutado,
        "variacion_total": total_ejecutado - total_presupuestado,
        "porcentaje_ejecucion": round((total_ejecutado / total_presupuestado * 100) if total_presupuestado > 0 else 0, 1),
        "detalle": resumen
    }

# ============================================================================
# M21: COBRANZA
# ============================================================================

router_cobranza = APIRouter(prefix="/cobranza", tags=["M21 - Cobranza"])

class EstadoDeuda(str, Enum):
    VIGENTE = "vigente"
    VENCIDO = "vencido"
    EN_GESTION = "en_gestion"
    CONVENIO = "convenio"
    JUDICIAL = "judicial"
    PAGADO = "pagado"
    INCOBRABLE = "incobrable"

class TipoAccionCobranza(str, Enum):
    AVISO = "aviso"
    RECORDATORIO = "recordatorio"
    LLAMADA = "llamada"
    CARTA = "carta"
    CORTE_SERVICIO = "corte_servicio"
    DEMANDA = "demanda"
    CONVENIO = "convenio"

class DeudaCreate(BaseModel):
    copropiedad_id: str
    unidad_id: str
    concepto: str
    monto: Decimal
    fecha_emision: date
    fecha_vencimiento: date
    documento_origen: Optional[str] = None

class GestionCobranzaCreate(BaseModel):
    deuda_id: str
    accion: TipoAccionCobranza
    descripcion: str
    responsable: str
    resultado: Optional[str] = None
    compromiso_pago: Optional[date] = None

class ConvenioCreate(BaseModel):
    deuda_ids: List[str]
    monto_total: Decimal
    cuotas: int
    fecha_primera_cuota: date
    observaciones: Optional[str] = None

deudas_db: Dict[str, Dict] = {}
gestiones_db: Dict[str, List[Dict]] = {}
convenios_db: Dict[str, Dict] = {}

@router_cobranza.post("/deudas", response_model=Dict[str, Any])
async def registrar_deuda(deuda: DeudaCreate):
    """Registrar cuenta por cobrar"""
    deuda_id = f"DDA-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": deuda_id,
        "copropiedad_id": deuda.copropiedad_id,
        "unidad_id": deuda.unidad_id,
        "concepto": deuda.concepto,
        "monto_original": float(deuda.monto),
        "monto_pendiente": float(deuda.monto),
        "fecha_emision": deuda.fecha_emision.isoformat(),
        "fecha_vencimiento": deuda.fecha_vencimiento.isoformat(),
        "dias_mora": 0,
        "estado": EstadoDeuda.VIGENTE.value,
        "documento_origen": deuda.documento_origen,
        "pagos_aplicados": [],
        "fecha_registro": datetime.now().isoformat()
    }
    
    deudas_db[deuda_id] = registro
    gestiones_db[deuda_id] = []
    
    return {"success": True, "deuda_id": deuda_id, "monto": float(deuda.monto)}

@router_cobranza.get("/deudas", response_model=Dict[str, Any])
async def listar_deudas(
    copropiedad_id: str,
    unidad_id: Optional[str] = None,
    estado: Optional[EstadoDeuda] = None,
    solo_vencidas: bool = False
):
    """Listar deudas con filtros"""
    resultados = [d for d in deudas_db.values() if d["copropiedad_id"] == copropiedad_id]
    
    if unidad_id:
        resultados = [d for d in resultados if d["unidad_id"] == unidad_id]
    if estado:
        resultados = [d for d in resultados if d["estado"] == estado.value]
    if solo_vencidas:
        hoy = date.today().isoformat()
        resultados = [d for d in resultados if d["fecha_vencimiento"] < hoy and d["estado"] != EstadoDeuda.PAGADO.value]
    
    return {
        "total": len(resultados),
        "monto_total": sum(d["monto_pendiente"] for d in resultados),
        "deudas": resultados
    }

@router_cobranza.post("/gestiones", response_model=Dict[str, Any])
async def registrar_gestion(gestion: GestionCobranzaCreate):
    """Registrar gestión de cobranza"""
    if gestion.deuda_id not in deudas_db:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    
    gestion_id = f"GES-{uuid.uuid4().hex[:6]}"
    
    registro = {
        "id": gestion_id,
        "deuda_id": gestion.deuda_id,
        "accion": gestion.accion.value,
        "descripcion": gestion.descripcion,
        "responsable": gestion.responsable,
        "resultado": gestion.resultado,
        "compromiso_pago": gestion.compromiso_pago.isoformat() if gestion.compromiso_pago else None,
        "fecha": datetime.now().isoformat()
    }
    
    gestiones_db[gestion.deuda_id].append(registro)
    
    # Actualizar estado de deuda
    deudas_db[gestion.deuda_id]["estado"] = EstadoDeuda.EN_GESTION.value
    
    return {"success": True, "gestion_id": gestion_id}

@router_cobranza.post("/convenios", response_model=Dict[str, Any])
async def crear_convenio(convenio: ConvenioCreate):
    """Crear convenio de pago"""
    convenio_id = f"CONV-{uuid.uuid4().hex[:8]}"
    
    # Calcular cuotas
    monto_cuota = float(convenio.monto_total) / convenio.cuotas
    cuotas = []
    
    for i in range(convenio.cuotas):
        fecha_cuota = convenio.fecha_primera_cuota + timedelta(days=30 * i)
        cuotas.append({
            "numero": i + 1,
            "monto": round(monto_cuota, 0),
            "fecha_vencimiento": fecha_cuota.isoformat(),
            "estado": "pendiente",
            "fecha_pago": None
        })
    
    registro = {
        "id": convenio_id,
        "deudas_consolidadas": convenio.deuda_ids,
        "monto_total": float(convenio.monto_total),
        "cuotas": cuotas,
        "total_cuotas": convenio.cuotas,
        "cuotas_pagadas": 0,
        "saldo_pendiente": float(convenio.monto_total),
        "estado": "vigente",
        "fecha_creacion": datetime.now().isoformat(),
        "observaciones": convenio.observaciones
    }
    
    convenios_db[convenio_id] = registro
    
    # Actualizar estado de deudas
    for deuda_id in convenio.deuda_ids:
        if deuda_id in deudas_db:
            deudas_db[deuda_id]["estado"] = EstadoDeuda.CONVENIO.value
            deudas_db[deuda_id]["convenio_id"] = convenio_id
    
    return {
        "success": True,
        "convenio_id": convenio_id,
        "cuotas": convenio.cuotas,
        "monto_cuota": round(monto_cuota, 0),
        "mensaje": "Convenio de pago creado"
    }

@router_cobranza.get("/cartera-morosa/{copropiedad_id}", response_model=Dict[str, Any])
async def cartera_morosa(copropiedad_id: str):
    """Obtener cartera morosa por antigüedad"""
    hoy = date.today()
    
    deudas = [
        d for d in deudas_db.values()
        if d["copropiedad_id"] == copropiedad_id
        and d["estado"] not in [EstadoDeuda.PAGADO.value, EstadoDeuda.INCOBRABLE.value]
    ]
    
    # Actualizar días de mora y clasificar
    cartera = {
        "corriente": {"cantidad": 0, "monto": 0},
        "1_30_dias": {"cantidad": 0, "monto": 0},
        "31_60_dias": {"cantidad": 0, "monto": 0},
        "61_90_dias": {"cantidad": 0, "monto": 0},
        "mas_90_dias": {"cantidad": 0, "monto": 0}
    }
    
    for deuda in deudas:
        vencimiento = date.fromisoformat(deuda["fecha_vencimiento"])
        dias_mora = max(0, (hoy - vencimiento).days)
        deuda["dias_mora"] = dias_mora
        
        if dias_mora == 0:
            cartera["corriente"]["cantidad"] += 1
            cartera["corriente"]["monto"] += deuda["monto_pendiente"]
        elif dias_mora <= 30:
            cartera["1_30_dias"]["cantidad"] += 1
            cartera["1_30_dias"]["monto"] += deuda["monto_pendiente"]
        elif dias_mora <= 60:
            cartera["31_60_dias"]["cantidad"] += 1
            cartera["31_60_dias"]["monto"] += deuda["monto_pendiente"]
        elif dias_mora <= 90:
            cartera["61_90_dias"]["cantidad"] += 1
            cartera["61_90_dias"]["monto"] += deuda["monto_pendiente"]
        else:
            cartera["mas_90_dias"]["cantidad"] += 1
            cartera["mas_90_dias"]["monto"] += deuda["monto_pendiente"]
    
    total_monto = sum(c["monto"] for c in cartera.values())
    total_deudores = len(set(d["unidad_id"] for d in deudas))
    
    return {
        "copropiedad_id": copropiedad_id,
        "fecha": hoy.isoformat(),
        "resumen": {
            "total_deudas": len(deudas),
            "total_deudores": total_deudores,
            "monto_total": total_monto
        },
        "por_antiguedad": cartera,
        "tasa_morosidad": round((len(deudas) / 100) * 100, 1) if deudas else 0  # Simplificado
    }

# ============================================================================
# M22: AUDITORÍA INTERNA
# ============================================================================

router_auditoria = APIRouter(prefix="/auditoria", tags=["M22 - Auditoría Interna"])

class TipoAuditoria(str, Enum):
    FINANCIERA = "financiera"
    OPERACIONAL = "operacional"
    CUMPLIMIENTO = "cumplimiento"
    SISTEMAS = "sistemas"
    INTEGRAL = "integral"

class ResultadoAuditoria(str, Enum):
    CONFORME = "conforme"
    OBSERVACIONES = "observaciones"
    NO_CONFORME = "no_conforme"

class SeveridadHallazgo(str, Enum):
    INFORMATIVO = "informativo"
    MENOR = "menor"
    MAYOR = "mayor"
    CRITICO = "critico"

class AuditoriaCreate(BaseModel):
    copropiedad_id: str
    tipo: TipoAuditoria
    titulo: str
    alcance: str
    periodo_auditado: str
    auditor_responsable: str
    equipo_auditor: List[str] = []

class HallazgoCreate(BaseModel):
    auditoria_id: str
    titulo: str
    descripcion: str
    severidad: SeveridadHallazgo
    area_afectada: str
    recomendacion: str
    responsable_accion: Optional[str] = None
    fecha_limite: Optional[date] = None
    evidencias: List[str] = []

auditorias_db: Dict[str, Dict] = {}
hallazgos_db: Dict[str, List[Dict]] = {}
planes_accion_db: Dict[str, Dict] = {}

@router_auditoria.post("/", response_model=Dict[str, Any])
async def iniciar_auditoria(auditoria: AuditoriaCreate):
    """Iniciar proceso de auditoría"""
    auditoria_id = f"AUD-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6]}"
    
    registro = {
        "id": auditoria_id,
        "copropiedad_id": auditoria.copropiedad_id,
        "tipo": auditoria.tipo.value,
        "titulo": auditoria.titulo,
        "alcance": auditoria.alcance,
        "periodo_auditado": auditoria.periodo_auditado,
        "auditor_responsable": auditoria.auditor_responsable,
        "equipo_auditor": auditoria.equipo_auditor,
        "estado": "en_proceso",
        "fecha_inicio": datetime.now().isoformat(),
        "fecha_fin": None,
        "resultado": None,
        "informe_final": None
    }
    
    auditorias_db[auditoria_id] = registro
    hallazgos_db[auditoria_id] = []
    
    return {
        "success": True,
        "auditoria_id": auditoria_id,
        "tipo": auditoria.tipo.value,
        "estado": "en_proceso"
    }

@router_auditoria.get("/", response_model=Dict[str, Any])
async def listar_auditorias(
    copropiedad_id: str,
    tipo: Optional[TipoAuditoria] = None,
    anio: Optional[int] = None
):
    """Listar auditorías"""
    resultados = [a for a in auditorias_db.values() if a["copropiedad_id"] == copropiedad_id]
    
    if tipo:
        resultados = [a for a in resultados if a["tipo"] == tipo.value]
    if anio:
        resultados = [a for a in resultados if a["fecha_inicio"][:4] == str(anio)]
    
    return {"total": len(resultados), "auditorias": resultados}

@router_auditoria.post("/hallazgos", response_model=Dict[str, Any])
async def registrar_hallazgo(hallazgo: HallazgoCreate):
    """Registrar hallazgo de auditoría"""
    if hallazgo.auditoria_id not in auditorias_db:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    hallazgo_id = f"HAL-{uuid.uuid4().hex[:8]}"
    
    registro = {
        "id": hallazgo_id,
        "auditoria_id": hallazgo.auditoria_id,
        "titulo": hallazgo.titulo,
        "descripcion": hallazgo.descripcion,
        "severidad": hallazgo.severidad.value,
        "area_afectada": hallazgo.area_afectada,
        "recomendacion": hallazgo.recomendacion,
        "responsable_accion": hallazgo.responsable_accion,
        "fecha_limite": hallazgo.fecha_limite.isoformat() if hallazgo.fecha_limite else None,
        "evidencias": hallazgo.evidencias,
        "estado": "abierto",
        "fecha_registro": datetime.now().isoformat()
    }
    
    hallazgos_db[hallazgo.auditoria_id].append(registro)
    
    return {
        "success": True,
        "hallazgo_id": hallazgo_id,
        "severidad": hallazgo.severidad.value
    }

@router_auditoria.get("/{auditoria_id}/hallazgos", response_model=Dict[str, Any])
async def obtener_hallazgos(auditoria_id: str):
    """Obtener hallazgos de una auditoría"""
    if auditoria_id not in auditorias_db:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    hallazgos = hallazgos_db.get(auditoria_id, [])
    
    por_severidad = {}
    for h in hallazgos:
        sev = h["severidad"]
        por_severidad[sev] = por_severidad.get(sev, 0) + 1
    
    return {
        "auditoria_id": auditoria_id,
        "total_hallazgos": len(hallazgos),
        "por_severidad": por_severidad,
        "abiertos": len([h for h in hallazgos if h["estado"] == "abierto"]),
        "hallazgos": hallazgos
    }

@router_auditoria.post("/{auditoria_id}/finalizar", response_model=Dict[str, Any])
async def finalizar_auditoria(
    auditoria_id: str,
    resultado: ResultadoAuditoria,
    conclusion: str
):
    """Finalizar auditoría con informe"""
    if auditoria_id not in auditorias_db:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    
    auditoria = auditorias_db[auditoria_id]
    hallazgos = hallazgos_db.get(auditoria_id, [])
    
    # Generar resumen
    por_severidad = {}
    for h in hallazgos:
        sev = h["severidad"]
        por_severidad[sev] = por_severidad.get(sev, 0) + 1
    
    auditoria["estado"] = "finalizada"
    auditoria["fecha_fin"] = datetime.now().isoformat()
    auditoria["resultado"] = resultado.value
    auditoria["informe_final"] = {
        "conclusion": conclusion,
        "total_hallazgos": len(hallazgos),
        "por_severidad": por_severidad,
        "criticos": por_severidad.get("critico", 0),
        "mayores": por_severidad.get("mayor", 0),
        "fecha_emision": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "auditoria_id": auditoria_id,
        "resultado": resultado.value,
        "hallazgos": len(hallazgos),
        "mensaje": "Auditoría finalizada"
    }

@router_auditoria.post("/hallazgos/{hallazgo_id}/cerrar", response_model=Dict[str, Any])
async def cerrar_hallazgo(
    hallazgo_id: str,
    accion_tomada: str,
    evidencia_cierre: Optional[str] = None
):
    """Cerrar hallazgo con acción correctiva"""
    for auditoria_id, hallazgos in hallazgos_db.items():
        for hallazgo in hallazgos:
            if hallazgo["id"] == hallazgo_id:
                hallazgo["estado"] = "cerrado"
                hallazgo["accion_tomada"] = accion_tomada
                hallazgo["evidencia_cierre"] = evidencia_cierre
                hallazgo["fecha_cierre"] = datetime.now().isoformat()
                
                return {"success": True, "mensaje": "Hallazgo cerrado"}
    
    raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

@router_auditoria.get("/resumen/{copropiedad_id}", response_model=Dict[str, Any])
async def resumen_auditorias(copropiedad_id: str):
    """Resumen ejecutivo de auditorías"""
    auditorias = [a for a in auditorias_db.values() if a["copropiedad_id"] == copropiedad_id]
    
    total_hallazgos = 0
    hallazgos_abiertos = 0
    por_resultado = {}
    
    for auditoria in auditorias:
        if auditoria.get("resultado"):
            res = auditoria["resultado"]
            por_resultado[res] = por_resultado.get(res, 0) + 1
        
        hallazgos = hallazgos_db.get(auditoria["id"], [])
        total_hallazgos += len(hallazgos)
        hallazgos_abiertos += len([h for h in hallazgos if h["estado"] == "abierto"])
    
    return {
        "copropiedad_id": copropiedad_id,
        "total_auditorias": len(auditorias),
        "finalizadas": len([a for a in auditorias if a["estado"] == "finalizada"]),
        "en_proceso": len([a for a in auditorias if a["estado"] == "en_proceso"]),
        "por_resultado": por_resultado,
        "hallazgos": {
            "total": total_hallazgos,
            "abiertos": hallazgos_abiertos,
            "cerrados": total_hallazgos - hallazgos_abiertos
        }
    }
