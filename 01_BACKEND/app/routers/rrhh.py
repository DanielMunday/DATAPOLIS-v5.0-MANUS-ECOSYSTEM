# ============================================================================
# DATAPOLIS v3.0 - ROUTER M09 RECURSOS HUMANOS
# ============================================================================
# Gestión integral RRHH según Código del Trabajo Chile
# Liquidaciones, contratos, vacaciones, finiquitos, Previred
# ============================================================================

from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

router = APIRouter(prefix="/rrhh", tags=["M09 - Recursos Humanos"])

# ============================================================================
# ENUMS
# ============================================================================

class TipoContrato(str, Enum):
    INDEFINIDO = "indefinido"
    PLAZO_FIJO = "plazo_fijo"
    POR_OBRA = "por_obra"
    PART_TIME = "part_time"
    HONORARIOS = "honorarios"

class EstadoTrabajador(str, Enum):
    ACTIVO = "activo"
    LICENCIA = "licencia_medica"
    VACACIONES = "vacaciones"
    SUSPENDIDO = "suspendido"
    DESPEDIDO = "despedido"
    RENUNCIA = "renuncia"

class TipoAFP(str, Enum):
    CAPITAL = "capital"
    CUPRUM = "cuprum"
    HABITAT = "habitat"
    MODELO = "modelo"
    PLANVITAL = "planvital"
    PROVIDA = "provida"
    UNO = "uno"

class TipoSalud(str, Enum):
    FONASA = "fonasa"
    ISAPRE = "isapre"

class CausalDespido(str, Enum):
    MUTUO_ACUERDO = "mutuo_acuerdo"
    RENUNCIA = "renuncia"
    VENCIMIENTO_PLAZO = "vencimiento_plazo"
    FIN_OBRA = "fin_obra"
    NECESIDADES_EMPRESA = "necesidades_empresa"
    FALTA_PROBIDAD = "falta_probidad"
    INCUMPLIMIENTO_GRAVE = "incumplimiento_grave"

# ============================================================================
# SCHEMAS
# ============================================================================

class TrabajadorCreate(BaseModel):
    rut: str = Field(..., description="RUT trabajador")
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    sexo: str = Field(..., pattern="^(M|F)$")
    nacionalidad: str = "Chilena"
    direccion: str
    comuna: str
    telefono: str
    email: str
    tipo_contrato: TipoContrato
    fecha_ingreso: date
    cargo: str
    departamento: str
    sueldo_base: Decimal = Field(..., gt=0)
    afp: TipoAFP
    salud: TipoSalud
    isapre_nombre: Optional[str] = None
    isapre_uf: Optional[Decimal] = None
    cuenta_banco: Optional[str] = None
    banco: Optional[str] = None
    cargas_familiares: int = 0
    copropiedad_id: Optional[str] = None

class TrabajadorResponse(BaseModel):
    id: str
    rut: str
    nombres: str
    apellidos: str
    nombre_completo: str
    cargo: str
    departamento: str
    tipo_contrato: TipoContrato
    estado: EstadoTrabajador
    fecha_ingreso: date
    antiguedad_anos: float
    sueldo_base: Decimal

class ContratoCreate(BaseModel):
    trabajador_id: str
    tipo: TipoContrato
    fecha_inicio: date
    fecha_termino: Optional[date] = None
    sueldo_base: Decimal
    cargo: str
    funciones: str
    lugar_trabajo: str

class LiquidacionRequest(BaseModel):
    trabajador_id: str
    periodo: str = Field(..., pattern="^\\d{4}-\\d{2}$")
    dias_trabajados: int = Field(30, ge=0, le=31)
    horas_extra: float = 0
    bonos_adicionales: List[Dict[str, Any]] = []
    descuentos_adicionales: List[Dict[str, Any]] = []
    valor_uf: Decimal = Field(..., gt=0)
    valor_utm: Decimal = Field(..., gt=0)

class LiquidacionResponse(BaseModel):
    id: str
    trabajador: Dict[str, Any]
    periodo: str
    haberes: List[Dict[str, Any]]
    descuentos: List[Dict[str, Any]]
    total_haberes_imponibles: Decimal
    total_haberes_no_imponibles: Decimal
    total_haberes: Decimal
    total_descuentos_legales: Decimal
    total_descuentos_voluntarios: Decimal
    total_descuentos: Decimal
    sueldo_liquido: Decimal
    costo_empleador: Decimal

class VacacionesRequest(BaseModel):
    trabajador_id: str
    fecha_inicio: date
    fecha_termino: date
    observaciones: Optional[str] = None

class FiniquitoRequest(BaseModel):
    trabajador_id: str
    fecha_termino: date
    causal: CausalDespido
    fecha_aviso: Optional[date] = None
    valor_uf: Decimal

# ============================================================================
# CONSTANTES PREVISIONALES 2026
# ============================================================================

TOPE_IMPONIBLE_AFP_UF = Decimal("81.6")
TOPE_IMPONIBLE_AFC_UF = Decimal("126.6")
SUELDO_MINIMO_2026 = Decimal("500000")
GRATIFICACION_TOPE_IMM = Decimal("4.75")

TASAS_AFP = {
    "capital": Decimal("11.44"),
    "cuprum": Decimal("11.44"),
    "habitat": Decimal("11.27"),
    "modelo": Decimal("10.58"),
    "planvital": Decimal("11.16"),
    "provida": Decimal("11.45"),
    "uno": Decimal("10.69")
}

TASA_FONASA = Decimal("7.0")
TASA_AFC_INDEFINIDO = Decimal("0.6")
TASA_AFC_PLAZO = Decimal("0.0")
TASA_AFC_EMPLEADOR_INDEFINIDO = Decimal("2.4")
TASA_AFC_EMPLEADOR_PLAZO = Decimal("3.0")

# Tabla Impuesto Único 2026 (en UTM)
TABLA_IMPUESTO_UNICO = [
    (Decimal("13.5"), Decimal("0"), Decimal("0")),
    (Decimal("30"), Decimal("4"), Decimal("0.54")),
    (Decimal("50"), Decimal("8"), Decimal("1.74")),
    (Decimal("70"), Decimal("13.5"), Decimal("4.49")),
    (Decimal("90"), Decimal("23"), Decimal("11.14")),
    (Decimal("120"), Decimal("30.4"), Decimal("17.8")),
    (Decimal("310"), Decimal("35"), Decimal("23.32")),
    (Decimal("999999"), Decimal("40"), Decimal("38.82"))
]

# ============================================================================
# STORAGE EN MEMORIA (producción usar PostgreSQL)
# ============================================================================

trabajadores_db: Dict[str, Dict] = {}
contratos_db: Dict[str, Dict] = {}
liquidaciones_db: Dict[str, Dict] = {}
vacaciones_db: Dict[str, Dict] = {}
finiquitos_db: Dict[str, Dict] = {}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_impuesto_unico(base_imponible: Decimal, valor_utm: Decimal) -> Decimal:
    """Calcula impuesto único según tabla 2026"""
    base_utm = base_imponible / valor_utm
    
    for tope, tasa, rebaja in TABLA_IMPUESTO_UNICO:
        if base_utm <= tope:
            impuesto_utm = (base_utm * tasa / 100) - rebaja
            return max(Decimal("0"), impuesto_utm * valor_utm)
    
    return Decimal("0")

def calcular_dias_habiles(fecha_inicio: date, fecha_termino: date) -> int:
    """Calcula días hábiles entre dos fechas"""
    dias = 0
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_termino:
        if fecha_actual.weekday() < 5:  # Lunes a Viernes
            dias += 1
        fecha_actual = fecha_actual.replace(day=fecha_actual.day + 1) if fecha_actual.day < 28 else fecha_actual
    return dias

def generar_id() -> str:
    """Genera ID único"""
    import uuid
    return str(uuid.uuid4())[:8]

# ============================================================================
# ENDPOINTS TRABAJADORES
# ============================================================================

@router.post("/trabajadores", response_model=TrabajadorResponse)
async def crear_trabajador(data: TrabajadorCreate):
    """
    Crear nuevo trabajador
    
    Validaciones:
    - RUT único
    - Sueldo >= mínimo legal
    - Datos previsionales completos
    """
    # Validar RUT único
    for t in trabajadores_db.values():
        if t["rut"] == data.rut:
            raise HTTPException(400, "RUT ya registrado")
    
    # Validar sueldo mínimo
    if data.sueldo_base < SUELDO_MINIMO_2026:
        raise HTTPException(400, f"Sueldo base debe ser >= ${SUELDO_MINIMO_2026:,.0f}")
    
    trabajador_id = generar_id()
    trabajador = {
        "id": trabajador_id,
        **data.dict(),
        "estado": EstadoTrabajador.ACTIVO,
        "fecha_creacion": datetime.now().isoformat()
    }
    trabajadores_db[trabajador_id] = trabajador
    
    # Calcular antigüedad
    antiguedad = (date.today() - data.fecha_ingreso).days / 365.25
    
    return TrabajadorResponse(
        id=trabajador_id,
        rut=data.rut,
        nombres=data.nombres,
        apellidos=data.apellidos,
        nombre_completo=f"{data.nombres} {data.apellidos}",
        cargo=data.cargo,
        departamento=data.departamento,
        tipo_contrato=data.tipo_contrato,
        estado=EstadoTrabajador.ACTIVO,
        fecha_ingreso=data.fecha_ingreso,
        antiguedad_anos=round(antiguedad, 1),
        sueldo_base=data.sueldo_base
    )

@router.get("/trabajadores")
async def listar_trabajadores(
    copropiedad_id: Optional[str] = None,
    estado: Optional[EstadoTrabajador] = None,
    departamento: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Listar trabajadores con filtros"""
    resultado = list(trabajadores_db.values())
    
    if copropiedad_id:
        resultado = [t for t in resultado if t.get("copropiedad_id") == copropiedad_id]
    if estado:
        resultado = [t for t in resultado if t.get("estado") == estado]
    if departamento:
        resultado = [t for t in resultado if t.get("departamento") == departamento]
    
    total = len(resultado)
    resultado = resultado[offset:offset + limit]
    
    return {
        "total": total,
        "trabajadores": resultado,
        "estadisticas": {
            "total_activos": len([t for t in trabajadores_db.values() if t.get("estado") == "activo"]),
            "total_licencia": len([t for t in trabajadores_db.values() if t.get("estado") == "licencia_medica"]),
            "total_vacaciones": len([t for t in trabajadores_db.values() if t.get("estado") == "vacaciones"])
        }
    }

@router.get("/trabajadores/{trabajador_id}")
async def obtener_trabajador(trabajador_id: str = Path(...)):
    """Obtener detalle de trabajador"""
    if trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    trabajador = trabajadores_db[trabajador_id]
    
    # Calcular datos adicionales
    fecha_ingreso = datetime.fromisoformat(str(trabajador["fecha_ingreso"])).date() if isinstance(trabajador["fecha_ingreso"], str) else trabajador["fecha_ingreso"]
    antiguedad = (date.today() - fecha_ingreso).days / 365.25
    
    # Vacaciones disponibles
    dias_vacaciones_base = 15
    dias_progresivos = max(0, int((antiguedad - 10) / 3)) if antiguedad > 10 else 0
    
    return {
        **trabajador,
        "antiguedad_anos": round(antiguedad, 2),
        "antiguedad_meses": int(antiguedad * 12),
        "vacaciones_disponibles": dias_vacaciones_base + dias_progresivos,
        "vacaciones_progresivos": dias_progresivos
    }

@router.put("/trabajadores/{trabajador_id}")
async def actualizar_trabajador(
    trabajador_id: str = Path(...),
    data: Dict[str, Any] = Body(...)
):
    """Actualizar datos de trabajador"""
    if trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    trabajador = trabajadores_db[trabajador_id]
    
    campos_actualizables = [
        "direccion", "comuna", "telefono", "email", "cargo",
        "departamento", "sueldo_base", "afp", "salud", "isapre_nombre",
        "isapre_uf", "cuenta_banco", "banco", "cargas_familiares"
    ]
    
    for campo in campos_actualizables:
        if campo in data:
            trabajador[campo] = data[campo]
    
    trabajador["fecha_actualizacion"] = datetime.now().isoformat()
    trabajadores_db[trabajador_id] = trabajador
    
    return {"mensaje": "Trabajador actualizado", "trabajador": trabajador}

# ============================================================================
# ENDPOINTS CONTRATOS
# ============================================================================

@router.post("/contratos")
async def crear_contrato(data: ContratoCreate):
    """Crear contrato de trabajo"""
    if data.trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    contrato_id = generar_id()
    contrato = {
        "id": contrato_id,
        **data.dict(),
        "firmado": False,
        "fecha_creacion": datetime.now().isoformat()
    }
    contratos_db[contrato_id] = contrato
    
    return {
        "mensaje": "Contrato creado",
        "contrato_id": contrato_id,
        "contrato": contrato
    }

@router.get("/contratos/{trabajador_id}")
async def obtener_contratos_trabajador(trabajador_id: str = Path(...)):
    """Obtener contratos de un trabajador"""
    contratos = [c for c in contratos_db.values() if c["trabajador_id"] == trabajador_id]
    return {"contratos": contratos, "total": len(contratos)}

@router.post("/contratos/{contrato_id}/firmar")
async def firmar_contrato(contrato_id: str = Path(...)):
    """Registrar firma de contrato"""
    if contrato_id not in contratos_db:
        raise HTTPException(404, "Contrato no encontrado")
    
    contratos_db[contrato_id]["firmado"] = True
    contratos_db[contrato_id]["fecha_firma"] = datetime.now().isoformat()
    
    return {"mensaje": "Contrato firmado", "contrato": contratos_db[contrato_id]}

# ============================================================================
# ENDPOINTS LIQUIDACIONES
# ============================================================================

@router.post("/liquidaciones/calcular", response_model=LiquidacionResponse)
async def calcular_liquidacion(data: LiquidacionRequest):
    """
    Calcular liquidación de sueldo completa
    
    Según normativa chilena:
    - Gratificación legal Art. 50 (25% sueldo, tope 4.75 IMM)
    - Horas extra con 50% recargo
    - Descuentos AFP según tasa
    - Descuento salud (FONASA 7% o Isapre)
    - AFC según tipo contrato
    - Impuesto único según tabla
    """
    if data.trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    trabajador = trabajadores_db[data.trabajador_id]
    sueldo_base = Decimal(str(trabajador["sueldo_base"]))
    
    # ========== HABERES ==========
    haberes = []
    
    # Sueldo base proporcional
    sueldo_proporcional = sueldo_base * data.dias_trabajados / 30
    haberes.append({
        "codigo": "H001",
        "nombre": "Sueldo Base",
        "monto": float(sueldo_proporcional),
        "imponible": True
    })
    
    # Gratificación legal Art. 50 (25% sueldo, tope 4.75 IMM/12)
    gratificacion_calculada = sueldo_proporcional * Decimal("0.25")
    gratificacion_tope = (GRATIFICACION_TOPE_IMM * SUELDO_MINIMO_2026) / 12
    gratificacion = min(gratificacion_calculada, gratificacion_tope)
    haberes.append({
        "codigo": "H002",
        "nombre": "Gratificación Legal",
        "monto": float(gratificacion),
        "imponible": True
    })
    
    # Horas extra (50% recargo)
    if data.horas_extra > 0:
        valor_hora = sueldo_base / 180
        valor_hora_extra = valor_hora * Decimal("1.5")
        monto_horas_extra = valor_hora_extra * Decimal(str(data.horas_extra))
        haberes.append({
            "codigo": "H003",
            "nombre": "Horas Extra",
            "cantidad": data.horas_extra,
            "monto": float(monto_horas_extra),
            "imponible": True
        })
    
    # Colación (no imponible)
    colacion = Decimal("50000")  # Valor ejemplo
    haberes.append({
        "codigo": "H010",
        "nombre": "Colación",
        "monto": float(colacion),
        "imponible": False
    })
    
    # Movilización (no imponible)
    movilizacion = Decimal("40000")  # Valor ejemplo
    haberes.append({
        "codigo": "H011",
        "nombre": "Movilización",
        "monto": float(movilizacion),
        "imponible": False
    })
    
    # Bonos adicionales
    for bono in data.bonos_adicionales:
        haberes.append({
            "codigo": bono.get("codigo", "H099"),
            "nombre": bono.get("nombre", "Bono"),
            "monto": float(bono.get("monto", 0)),
            "imponible": bono.get("imponible", True)
        })
    
    # Totales haberes
    total_imponibles = sum(Decimal(str(h["monto"])) for h in haberes if h["imponible"])
    total_no_imponibles = sum(Decimal(str(h["monto"])) for h in haberes if not h["imponible"])
    total_haberes = total_imponibles + total_no_imponibles
    
    # Aplicar tope imponible
    tope_imponible = TOPE_IMPONIBLE_AFP_UF * data.valor_uf
    base_imponible_afp = min(total_imponibles, tope_imponible)
    
    # ========== DESCUENTOS ==========
    descuentos = []
    
    # AFP
    tasa_afp = TASAS_AFP.get(trabajador["afp"], Decimal("11.0"))
    descuento_afp = base_imponible_afp * tasa_afp / 100
    descuentos.append({
        "codigo": "D001",
        "nombre": f"AFP {trabajador['afp'].upper()} ({tasa_afp}%)",
        "monto": float(descuento_afp),
        "tipo": "legal"
    })
    
    # Salud
    if trabajador["salud"] == "fonasa":
        descuento_salud = base_imponible_afp * TASA_FONASA / 100
        descuentos.append({
            "codigo": "D002",
            "nombre": f"FONASA ({TASA_FONASA}%)",
            "monto": float(descuento_salud),
            "tipo": "legal"
        })
    else:
        # Isapre - mínimo 7% o pactado
        isapre_uf = Decimal(str(trabajador.get("isapre_uf", 0)))
        descuento_isapre_pactado = isapre_uf * data.valor_uf
        descuento_isapre_minimo = base_imponible_afp * TASA_FONASA / 100
        descuento_salud = max(descuento_isapre_pactado, descuento_isapre_minimo)
        descuentos.append({
            "codigo": "D002",
            "nombre": f"ISAPRE {trabajador.get('isapre_nombre', '')}",
            "monto": float(descuento_salud),
            "tipo": "legal"
        })
    
    # AFC (Seguro de Cesantía)
    tope_afc = TOPE_IMPONIBLE_AFC_UF * data.valor_uf
    base_imponible_afc = min(total_imponibles, tope_afc)
    
    if trabajador["tipo_contrato"] == "indefinido":
        tasa_afc = TASA_AFC_INDEFINIDO
    else:
        tasa_afc = TASA_AFC_PLAZO
    
    descuento_afc = base_imponible_afc * tasa_afc / 100
    descuentos.append({
        "codigo": "D003",
        "nombre": f"AFC ({tasa_afc}%)",
        "monto": float(descuento_afc),
        "tipo": "legal"
    })
    
    # Base para impuesto único
    total_descuentos_previsionales = descuento_afp + descuento_salud + descuento_afc
    base_impuesto = total_imponibles - total_descuentos_previsionales
    
    # Impuesto único
    impuesto = calcular_impuesto_unico(base_impuesto, data.valor_utm)
    if impuesto > 0:
        descuentos.append({
            "codigo": "D004",
            "nombre": "Impuesto Único",
            "monto": float(impuesto),
            "tipo": "legal"
        })
    
    # Descuentos adicionales
    for desc in data.descuentos_adicionales:
        descuentos.append({
            "codigo": desc.get("codigo", "D099"),
            "nombre": desc.get("nombre", "Descuento"),
            "monto": float(desc.get("monto", 0)),
            "tipo": "voluntario"
        })
    
    # Totales descuentos
    total_descuentos_legales = sum(Decimal(str(d["monto"])) for d in descuentos if d["tipo"] == "legal")
    total_descuentos_voluntarios = sum(Decimal(str(d["monto"])) for d in descuentos if d["tipo"] == "voluntario")
    total_descuentos = total_descuentos_legales + total_descuentos_voluntarios
    
    # Sueldo líquido
    sueldo_liquido = total_haberes - total_descuentos
    
    # Costo empleador
    if trabajador["tipo_contrato"] == "indefinido":
        afc_empleador = base_imponible_afc * TASA_AFC_EMPLEADOR_INDEFINIDO / 100
    else:
        afc_empleador = base_imponible_afc * TASA_AFC_EMPLEADOR_PLAZO / 100
    
    mutual = base_imponible_afp * Decimal("0.93") / 100  # Tasa básica mutual
    costo_empleador = total_haberes + afc_empleador + mutual
    
    # Guardar liquidación
    liquidacion_id = generar_id()
    liquidacion = {
        "id": liquidacion_id,
        "trabajador_id": data.trabajador_id,
        "periodo": data.periodo,
        "dias_trabajados": data.dias_trabajados,
        "haberes": haberes,
        "descuentos": descuentos,
        "total_haberes_imponibles": float(total_imponibles),
        "total_haberes_no_imponibles": float(total_no_imponibles),
        "total_descuentos_legales": float(total_descuentos_legales),
        "total_descuentos_voluntarios": float(total_descuentos_voluntarios),
        "sueldo_liquido": float(sueldo_liquido),
        "costo_empleador": float(costo_empleador),
        "valor_uf": float(data.valor_uf),
        "valor_utm": float(data.valor_utm),
        "fecha_calculo": datetime.now().isoformat()
    }
    liquidaciones_db[liquidacion_id] = liquidacion
    
    return LiquidacionResponse(
        id=liquidacion_id,
        trabajador={
            "id": trabajador["id"],
            "rut": trabajador["rut"],
            "nombre": f"{trabajador['nombres']} {trabajador['apellidos']}",
            "cargo": trabajador["cargo"]
        },
        periodo=data.periodo,
        haberes=haberes,
        descuentos=descuentos,
        total_haberes_imponibles=total_imponibles,
        total_haberes_no_imponibles=total_no_imponibles,
        total_haberes=total_haberes,
        total_descuentos_legales=total_descuentos_legales,
        total_descuentos_voluntarios=total_descuentos_voluntarios,
        total_descuentos=total_descuentos,
        sueldo_liquido=sueldo_liquido,
        costo_empleador=costo_empleador
    )

@router.get("/liquidaciones")
async def listar_liquidaciones(
    trabajador_id: Optional[str] = None,
    periodo: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """Listar liquidaciones con filtros"""
    resultado = list(liquidaciones_db.values())
    
    if trabajador_id:
        resultado = [l for l in resultado if l["trabajador_id"] == trabajador_id]
    if periodo:
        resultado = [l for l in resultado if l["periodo"] == periodo]
    
    return {"liquidaciones": resultado[:limit], "total": len(resultado)}

@router.get("/liquidaciones/{liquidacion_id}")
async def obtener_liquidacion(liquidacion_id: str = Path(...)):
    """Obtener detalle de liquidación"""
    if liquidacion_id not in liquidaciones_db:
        raise HTTPException(404, "Liquidación no encontrada")
    
    liquidacion = liquidaciones_db[liquidacion_id]
    trabajador = trabajadores_db.get(liquidacion["trabajador_id"], {})
    
    return {
        **liquidacion,
        "trabajador_detalle": trabajador
    }

# ============================================================================
# ENDPOINTS VACACIONES
# ============================================================================

@router.post("/vacaciones/solicitar")
async def solicitar_vacaciones(data: VacacionesRequest):
    """
    Solicitar vacaciones
    
    Calcula días hábiles y valida disponibilidad
    """
    if data.trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    trabajador = trabajadores_db[data.trabajador_id]
    
    # Calcular antigüedad y días disponibles
    fecha_ingreso = trabajador["fecha_ingreso"]
    if isinstance(fecha_ingreso, str):
        fecha_ingreso = datetime.fromisoformat(fecha_ingreso).date()
    
    antiguedad = (date.today() - fecha_ingreso).days / 365.25
    dias_base = 15
    dias_progresivos = max(0, int((antiguedad - 10) / 3)) if antiguedad > 10 else 0
    dias_disponibles = dias_base + dias_progresivos
    
    # Calcular días hábiles solicitados
    dias_habiles = 0
    fecha_actual = data.fecha_inicio
    while fecha_actual <= data.fecha_termino:
        if fecha_actual.weekday() < 5:
            dias_habiles += 1
        fecha_actual = date(
            fecha_actual.year,
            fecha_actual.month,
            fecha_actual.day + 1
        ) if fecha_actual.day < 28 else fecha_actual
    
    # Validar
    if dias_habiles > dias_disponibles:
        raise HTTPException(400, f"Solo tiene {dias_disponibles} días disponibles")
    
    vacacion_id = generar_id()
    vacacion = {
        "id": vacacion_id,
        "trabajador_id": data.trabajador_id,
        "fecha_inicio": data.fecha_inicio.isoformat(),
        "fecha_termino": data.fecha_termino.isoformat(),
        "dias_habiles": dias_habiles,
        "dias_progresivos": dias_progresivos,
        "estado": "pendiente",
        "observaciones": data.observaciones,
        "fecha_solicitud": datetime.now().isoformat()
    }
    vacaciones_db[vacacion_id] = vacacion
    
    return {
        "mensaje": "Solicitud de vacaciones registrada",
        "vacacion_id": vacacion_id,
        "vacacion": vacacion,
        "dias_restantes": dias_disponibles - dias_habiles
    }

@router.get("/vacaciones/{trabajador_id}")
async def obtener_vacaciones_trabajador(trabajador_id: str = Path(...)):
    """Obtener historial de vacaciones de un trabajador"""
    vacaciones = [v for v in vacaciones_db.values() if v["trabajador_id"] == trabajador_id]
    
    # Calcular días disponibles actuales
    if trabajador_id in trabajadores_db:
        trabajador = trabajadores_db[trabajador_id]
        fecha_ingreso = trabajador["fecha_ingreso"]
        if isinstance(fecha_ingreso, str):
            fecha_ingreso = datetime.fromisoformat(fecha_ingreso).date()
        antiguedad = (date.today() - fecha_ingreso).days / 365.25
        dias_base = 15
        dias_progresivos = max(0, int((antiguedad - 10) / 3)) if antiguedad > 10 else 0
        
        # Descontar vacaciones tomadas este año
        dias_usados = sum(v.get("dias_habiles", 0) for v in vacaciones if v.get("estado") == "aprobada")
        dias_disponibles = max(0, dias_base + dias_progresivos - dias_usados)
    else:
        dias_disponibles = 0
    
    return {
        "vacaciones": vacaciones,
        "total_registros": len(vacaciones),
        "dias_disponibles": dias_disponibles
    }

@router.post("/vacaciones/{vacacion_id}/aprobar")
async def aprobar_vacaciones(vacacion_id: str = Path(...)):
    """Aprobar solicitud de vacaciones"""
    if vacacion_id not in vacaciones_db:
        raise HTTPException(404, "Solicitud no encontrada")
    
    vacaciones_db[vacacion_id]["estado"] = "aprobada"
    vacaciones_db[vacacion_id]["fecha_aprobacion"] = datetime.now().isoformat()
    
    # Actualizar estado trabajador
    trabajador_id = vacaciones_db[vacacion_id]["trabajador_id"]
    if trabajador_id in trabajadores_db:
        trabajadores_db[trabajador_id]["estado"] = EstadoTrabajador.VACACIONES
    
    return {"mensaje": "Vacaciones aprobadas", "vacacion": vacaciones_db[vacacion_id]}

# ============================================================================
# ENDPOINTS FINIQUITOS
# ============================================================================

@router.post("/finiquitos/calcular")
async def calcular_finiquito(data: FiniquitoRequest):
    """
    Calcular finiquito según causal
    
    Art. 159: Sin indemnización (mutuo acuerdo, renuncia, vencimiento)
    Art. 160: Sin indemnización (causales imputables al trabajador)
    Art. 161: Con indemnización (necesidades empresa)
    """
    if data.trabajador_id not in trabajadores_db:
        raise HTTPException(404, "Trabajador no encontrado")
    
    trabajador = trabajadores_db[data.trabajador_id]
    sueldo_base = Decimal(str(trabajador["sueldo_base"]))
    
    # Calcular antigüedad
    fecha_ingreso = trabajador["fecha_ingreso"]
    if isinstance(fecha_ingreso, str):
        fecha_ingreso = datetime.fromisoformat(fecha_ingreso).date()
    
    antiguedad_dias = (data.fecha_termino - fecha_ingreso).days
    antiguedad_anos = antiguedad_dias / 365.25
    
    # ========== HABERES FINIQUITO ==========
    haberes = []
    
    # Sueldo proporcional del mes
    dia_termino = data.fecha_termino.day
    sueldo_proporcional = sueldo_base * dia_termino / 30
    haberes.append({
        "concepto": "Sueldo Proporcional",
        "dias": dia_termino,
        "monto": float(sueldo_proporcional)
    })
    
    # Vacaciones proporcionales (días trabajados en año actual / 365 * 15)
    inicio_ano = date(data.fecha_termino.year, 1, 1)
    dias_ano = (data.fecha_termino - inicio_ano).days + 1
    vacaciones_proporcionales = (dias_ano / 365) * 15 * (sueldo_base / 30)
    haberes.append({
        "concepto": "Vacaciones Proporcionales",
        "dias": round(dias_ano / 365 * 15, 2),
        "monto": float(vacaciones_proporcionales)
    })
    
    # Vacaciones pendientes (si las hay)
    vacaciones_pendientes = Decimal("0")  # Debería calcularse de historial
    haberes.append({
        "concepto": "Vacaciones Pendientes",
        "dias": 0,
        "monto": float(vacaciones_pendientes)
    })
    
    # Gratificación proporcional
    gratificacion_mensual = min(sueldo_base * Decimal("0.25"), (GRATIFICACION_TOPE_IMM * SUELDO_MINIMO_2026) / 12)
    meses_ano = data.fecha_termino.month + (data.fecha_termino.day / 30)
    gratificacion_proporcional = gratificacion_mensual * Decimal(str(meses_ano))
    haberes.append({
        "concepto": "Gratificación Proporcional",
        "meses": round(float(meses_ano), 2),
        "monto": float(gratificacion_proporcional)
    })
    
    # ========== INDEMNIZACIONES ==========
    indemnizacion_anos = Decimal("0")
    indemnizacion_aviso = Decimal("0")
    
    # Determinar si corresponde indemnización según causal
    causales_con_indemnizacion = [
        CausalDespido.NECESIDADES_EMPRESA
    ]
    
    if data.causal in causales_con_indemnizacion:
        # Indemnización por años de servicio (30 días por año, tope 11 años)
        anos_indemnizables = min(int(antiguedad_anos), 11)
        if anos_indemnizables > 0:
            indemnizacion_anos = sueldo_base * anos_indemnizables
            haberes.append({
                "concepto": "Indemnización Años Servicio",
                "anos": anos_indemnizables,
                "monto": float(indemnizacion_anos)
            })
        
        # Indemnización sustitutiva aviso previo (si no hubo aviso de 30 días)
        if data.fecha_aviso:
            dias_aviso = (data.fecha_termino - data.fecha_aviso).days
            if dias_aviso < 30:
                indemnizacion_aviso = sueldo_base
                haberes.append({
                    "concepto": "Indemnización Sustitutiva Aviso Previo",
                    "dias": 30,
                    "monto": float(indemnizacion_aviso)
                })
        else:
            indemnizacion_aviso = sueldo_base
            haberes.append({
                "concepto": "Indemnización Sustitutiva Aviso Previo",
                "dias": 30,
                "monto": float(indemnizacion_aviso)
            })
    
    # Total haberes
    total_haberes = sum(Decimal(str(h["monto"])) for h in haberes)
    
    # ========== DESCUENTOS ==========
    # Solo sobre haberes imponibles (no sobre indemnizaciones)
    base_imponible = sueldo_proporcional + vacaciones_proporcionales + gratificacion_proporcional
    
    descuentos = []
    
    # AFP
    tasa_afp = TASAS_AFP.get(trabajador["afp"], Decimal("11.0"))
    descuento_afp = base_imponible * tasa_afp / 100
    descuentos.append({
        "concepto": f"AFP {trabajador['afp'].upper()}",
        "monto": float(descuento_afp)
    })
    
    # Salud
    descuento_salud = base_imponible * TASA_FONASA / 100
    descuentos.append({
        "concepto": "Salud",
        "monto": float(descuento_salud)
    })
    
    # AFC
    tasa_afc = TASA_AFC_INDEFINIDO if trabajador["tipo_contrato"] == "indefinido" else TASA_AFC_PLAZO
    descuento_afc = base_imponible * tasa_afc / 100
    descuentos.append({
        "concepto": "AFC",
        "monto": float(descuento_afc)
    })
    
    total_descuentos = sum(Decimal(str(d["monto"])) for d in descuentos)
    
    # Total líquido
    total_liquido = total_haberes - total_descuentos
    
    # Guardar finiquito
    finiquito_id = generar_id()
    finiquito = {
        "id": finiquito_id,
        "trabajador_id": data.trabajador_id,
        "trabajador": {
            "rut": trabajador["rut"],
            "nombre": f"{trabajador['nombres']} {trabajador['apellidos']}",
            "cargo": trabajador["cargo"]
        },
        "fecha_termino": data.fecha_termino.isoformat(),
        "causal": data.causal.value,
        "causal_descripcion": obtener_descripcion_causal(data.causal),
        "antiguedad_anos": round(antiguedad_anos, 2),
        "sueldo_base": float(sueldo_base),
        "haberes": haberes,
        "descuentos": descuentos,
        "total_haberes": float(total_haberes),
        "total_descuentos": float(total_descuentos),
        "total_liquido": float(total_liquido),
        "indemnizacion_anos_servicio": float(indemnizacion_anos),
        "indemnizacion_aviso_previo": float(indemnizacion_aviso),
        "estado": "calculado",
        "fecha_calculo": datetime.now().isoformat()
    }
    finiquitos_db[finiquito_id] = finiquito
    
    return {
        "mensaje": "Finiquito calculado",
        "finiquito_id": finiquito_id,
        "finiquito": finiquito,
        "advertencias": generar_advertencias_finiquito(data.causal, antiguedad_anos)
    }

def obtener_descripcion_causal(causal: CausalDespido) -> str:
    """Obtiene descripción legal de la causal"""
    descripciones = {
        CausalDespido.MUTUO_ACUERDO: "Art. 159 N°1 - Mutuo acuerdo de las partes",
        CausalDespido.RENUNCIA: "Art. 159 N°2 - Renuncia del trabajador",
        CausalDespido.VENCIMIENTO_PLAZO: "Art. 159 N°4 - Vencimiento del plazo convenido",
        CausalDespido.FIN_OBRA: "Art. 159 N°5 - Conclusión del trabajo o servicio",
        CausalDespido.NECESIDADES_EMPRESA: "Art. 161 - Necesidades de la empresa",
        CausalDespido.FALTA_PROBIDAD: "Art. 160 N°1 - Falta de probidad",
        CausalDespido.INCUMPLIMIENTO_GRAVE: "Art. 160 N°7 - Incumplimiento grave de obligaciones"
    }
    return descripciones.get(causal, "Causal no especificada")

def generar_advertencias_finiquito(causal: CausalDespido, antiguedad: float) -> List[str]:
    """Genera advertencias sobre el finiquito"""
    advertencias = []
    
    if causal == CausalDespido.NECESIDADES_EMPRESA and antiguedad < 1:
        advertencias.append("Trabajador con menos de 1 año: No corresponde indemnización por años de servicio")
    
    if causal in [CausalDespido.FALTA_PROBIDAD, CausalDespido.INCUMPLIMIENTO_GRAVE]:
        advertencias.append("Causal imputable al trabajador: No corresponde indemnización")
        advertencias.append("Se recomienda documentar causal con evidencia")
    
    advertencias.append("Finiquito debe ser ratificado ante Inspección del Trabajo o Notaría")
    advertencias.append("Plazo de pago: 10 días hábiles desde fecha de término")
    
    return advertencias

@router.get("/finiquitos/{finiquito_id}")
async def obtener_finiquito(finiquito_id: str = Path(...)):
    """Obtener detalle de finiquito"""
    if finiquito_id not in finiquitos_db:
        raise HTTPException(404, "Finiquito no encontrado")
    return finiquitos_db[finiquito_id]

# ============================================================================
# ENDPOINTS PREVIRED
# ============================================================================

@router.post("/previred/generar")
async def generar_archivo_previred(
    periodo: str = Query(..., pattern="^\\d{4}-\\d{2}$"),
    copropiedad_id: Optional[str] = None
):
    """
    Generar archivo Previred para pago de cotizaciones
    
    Formato estándar Previred con registros de trabajadores
    """
    # Filtrar trabajadores activos
    trabajadores = [
        t for t in trabajadores_db.values()
        if t.get("estado") == "activo"
    ]
    
    if copropiedad_id:
        trabajadores = [t for t in trabajadores if t.get("copropiedad_id") == copropiedad_id]
    
    if not trabajadores:
        raise HTTPException(404, "No hay trabajadores activos para el período")
    
    registros = []
    totales = {
        "total_afp": Decimal("0"),
        "total_salud": Decimal("0"),
        "total_afc": Decimal("0"),
        "total_afc_empleador": Decimal("0")
    }
    
    for trabajador in trabajadores:
        sueldo = Decimal(str(trabajador["sueldo_base"]))
        
        # Calcular cotizaciones
        tasa_afp = TASAS_AFP.get(trabajador["afp"], Decimal("11.0"))
        cotizacion_afp = sueldo * tasa_afp / 100
        cotizacion_salud = sueldo * TASA_FONASA / 100
        
        if trabajador["tipo_contrato"] == "indefinido":
            cotizacion_afc = sueldo * TASA_AFC_INDEFINIDO / 100
            cotizacion_afc_empleador = sueldo * TASA_AFC_EMPLEADOR_INDEFINIDO / 100
        else:
            cotizacion_afc = Decimal("0")
            cotizacion_afc_empleador = sueldo * TASA_AFC_EMPLEADOR_PLAZO / 100
        
        registro = {
            "rut": trabajador["rut"],
            "nombre": f"{trabajador['apellidos']} {trabajador['nombres']}",
            "afp": trabajador["afp"],
            "salud": trabajador["salud"],
            "renta_imponible": float(sueldo),
            "cotizacion_afp": float(cotizacion_afp),
            "cotizacion_salud": float(cotizacion_salud),
            "cotizacion_afc_trabajador": float(cotizacion_afc),
            "cotizacion_afc_empleador": float(cotizacion_afc_empleador)
        }
        registros.append(registro)
        
        totales["total_afp"] += cotizacion_afp
        totales["total_salud"] += cotizacion_salud
        totales["total_afc"] += cotizacion_afc
        totales["total_afc_empleador"] += cotizacion_afc_empleador
    
    return {
        "periodo": periodo,
        "fecha_generacion": datetime.now().isoformat(),
        "total_trabajadores": len(registros),
        "registros": registros,
        "totales": {k: float(v) for k, v in totales.items()},
        "total_general": float(sum(totales.values()))
    }

# ============================================================================
# ENDPOINTS ESTADÍSTICAS
# ============================================================================

@router.get("/estadisticas")
async def obtener_estadisticas_rrhh(copropiedad_id: Optional[str] = None):
    """Obtener estadísticas generales de RRHH"""
    trabajadores = list(trabajadores_db.values())
    
    if copropiedad_id:
        trabajadores = [t for t in trabajadores if t.get("copropiedad_id") == copropiedad_id]
    
    activos = [t for t in trabajadores if t.get("estado") == "activo"]
    
    # Nómina mensual estimada
    nomina_mensual = sum(Decimal(str(t.get("sueldo_base", 0))) for t in activos)
    
    # Costo empleador estimado (nómina + 3% AFC empleador + 0.93% mutual)
    costo_empleador = nomina_mensual * Decimal("1.0393")
    
    return {
        "resumen": {
            "total_trabajadores": len(trabajadores),
            "activos": len(activos),
            "en_licencia": len([t for t in trabajadores if t.get("estado") == "licencia_medica"]),
            "en_vacaciones": len([t for t in trabajadores if t.get("estado") == "vacaciones"])
        },
        "por_tipo_contrato": {
            "indefinido": len([t for t in activos if t.get("tipo_contrato") == "indefinido"]),
            "plazo_fijo": len([t for t in activos if t.get("tipo_contrato") == "plazo_fijo"]),
            "honorarios": len([t for t in activos if t.get("tipo_contrato") == "honorarios"])
        },
        "financiero": {
            "nomina_mensual": float(nomina_mensual),
            "costo_empleador_mensual": float(costo_empleador),
            "costo_anual_estimado": float(costo_empleador * 12)
        },
        "liquidaciones_periodo_actual": len(liquidaciones_db),
        "finiquitos_pendientes": len([f for f in finiquitos_db.values() if f.get("estado") == "calculado"])
    }

# ============================================================================
# ENDPOINTS LIBRO REMUNERACIONES
# ============================================================================

@router.get("/libro-remuneraciones")
async def generar_libro_remuneraciones(
    periodo: str = Query(..., pattern="^\\d{4}-\\d{2}$"),
    formato: str = Query("json", pattern="^(json|csv|excel)$")
):
    """
    Generar Libro de Remuneraciones
    
    Obligatorio según Art. 62 Código del Trabajo
    """
    liquidaciones_periodo = [
        l for l in liquidaciones_db.values()
        if l.get("periodo") == periodo
    ]
    
    registros = []
    for liq in liquidaciones_periodo:
        trabajador = trabajadores_db.get(liq["trabajador_id"], {})
        
        registro = {
            "rut": trabajador.get("rut", ""),
            "nombre": f"{trabajador.get('apellidos', '')} {trabajador.get('nombres', '')}",
            "cargo": trabajador.get("cargo", ""),
            "dias_trabajados": liq.get("dias_trabajados", 0),
            "sueldo_base": next((h["monto"] for h in liq.get("haberes", []) if h["codigo"] == "H001"), 0),
            "gratificacion": next((h["monto"] for h in liq.get("haberes", []) if h["codigo"] == "H002"), 0),
            "horas_extra": next((h["monto"] for h in liq.get("haberes", []) if h["codigo"] == "H003"), 0),
            "otros_haberes": liq.get("total_haberes_no_imponibles", 0),
            "total_haberes": liq.get("total_haberes_imponibles", 0) + liq.get("total_haberes_no_imponibles", 0),
            "afp": next((d["monto"] for d in liq.get("descuentos", []) if "AFP" in d["nombre"]), 0),
            "salud": next((d["monto"] for d in liq.get("descuentos", []) if d["codigo"] == "D002"), 0),
            "afc": next((d["monto"] for d in liq.get("descuentos", []) if d["codigo"] == "D003"), 0),
            "impuesto": next((d["monto"] for d in liq.get("descuentos", []) if d["codigo"] == "D004"), 0),
            "otros_descuentos": liq.get("total_descuentos_voluntarios", 0),
            "total_descuentos": liq.get("total_descuentos_legales", 0) + liq.get("total_descuentos_voluntarios", 0),
            "liquido": liq.get("sueldo_liquido", 0)
        }
        registros.append(registro)
    
    # Totales
    totales = {
        "total_haberes": sum(r["total_haberes"] for r in registros),
        "total_afp": sum(r["afp"] for r in registros),
        "total_salud": sum(r["salud"] for r in registros),
        "total_afc": sum(r["afc"] for r in registros),
        "total_impuesto": sum(r["impuesto"] for r in registros),
        "total_descuentos": sum(r["total_descuentos"] for r in registros),
        "total_liquido": sum(r["liquido"] for r in registros)
    }
    
    return {
        "periodo": periodo,
        "fecha_generacion": datetime.now().isoformat(),
        "total_trabajadores": len(registros),
        "registros": registros,
        "totales": totales
    }
