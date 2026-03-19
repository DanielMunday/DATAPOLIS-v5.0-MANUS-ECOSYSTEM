"""
DATAPOLIS v3.0 - Router M07 Liquidación Concursal
=================================================
API REST para gestión de liquidaciones según Ley 20.720

Endpoints:
- Gestión de procedimientos concursales
- Verificación de créditos
- Inventario y realización de activos
- Distribución según prelación legal
- Informes para Superintendencia

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid

router = APIRouter(prefix="/liquidacion", tags=["M07 - Liquidación Concursal"])

# ============================================================================
# ENUMERACIONES
# ============================================================================

class TipoProcedimiento(str, Enum):
    LIQUIDACION_VOLUNTARIA = "liquidacion_voluntaria"
    LIQUIDACION_FORZOSA = "liquidacion_forzosa"
    REORGANIZACION_JUDICIAL = "reorganizacion_judicial"
    RENEGOCIACION_PERSONA = "renegociacion_persona"
    LIQUIDACION_SIMPLIFICADA = "liquidacion_simplificada"

class EstadoProcedimiento(str, Enum):
    INICIADO = "iniciado"
    VERIFICACION_CREDITOS = "verificacion_creditos"
    REALIZACION_ACTIVOS = "realizacion_activos"
    DISTRIBUCION = "distribucion"
    CUENTA_FINAL = "cuenta_final"
    TERMINADO = "terminado"

class ClaseCredito(str, Enum):
    PRIMERA_CLASE = "primera_clase"
    SEGUNDA_CLASE = "segunda_clase"
    TERCERA_CLASE = "tercera_clase"
    CUARTA_CLASE = "cuarta_clase"
    QUINTA_CLASE = "quinta_clase"

class TipoActivo(str, Enum):
    INMUEBLE = "inmueble"
    VEHICULO = "vehiculo"
    MAQUINARIA = "maquinaria"
    INVENTARIO = "inventario"
    CUENTAS_COBRAR = "cuentas_por_cobrar"
    EFECTIVO = "efectivo"
    INVERSIONES = "inversiones"

class MetodoRealizacion(str, Enum):
    SUBASTA_PUBLICA = "subasta_publica"
    VENTA_DIRECTA = "venta_directa"
    LICITACION_PRIVADA = "licitacion_privada"
    VENTA_UNIDAD_ECONOMICA = "venta_unidad_economica"

# ============================================================================
# SCHEMAS
# ============================================================================

class DeudorCreate(BaseModel):
    rut: str = Field(..., example="76.123.456-7")
    nombre: str = Field(..., example="Constructora XYZ Ltda.")
    tipo: str = Field(..., example="persona_juridica")
    domicilio: str = Field(..., example="Av. Providencia 1234, Santiago")
    actividad_economica: Optional[str] = None
    representante_legal: Optional[str] = None
    capital_social: Optional[float] = None

class ProcedimientoCreate(BaseModel):
    tipo: TipoProcedimiento
    deudor: DeudorCreate
    liquidador: str = Field(..., example="Juan Pérez González")
    tribunal: str = Field(..., example="1° Juzgado Civil de Santiago")
    rol_causa: str = Field(..., example="C-1234-2026")

class CreditoCreate(BaseModel):
    acreedor_rut: str = Field(..., example="12.345.678-9")
    acreedor_nombre: str = Field(..., example="Proveedor SA")
    monto: float = Field(..., gt=0, example=50000000)
    clase: ClaseCredito
    garantia: Optional[str] = None
    bien_afecto: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    documentos: List[str] = []

class ActivoCreate(BaseModel):
    tipo: TipoActivo
    descripcion: str = Field(..., example="Oficina comercial 150m2")
    ubicacion: Optional[str] = None
    valor_libro: float = Field(..., gt=0, example=150000000)
    gravamenes: List[str] = []

class TasacionCreate(BaseModel):
    valor_tasacion: float = Field(..., gt=0)
    tasador: str
    fecha_tasacion: date = Field(default_factory=date.today)
    metodologia: str = "comparación de mercado"

class RealizacionCreate(BaseModel):
    metodo: MetodoRealizacion
    valor_realizacion: float = Field(..., gt=0)
    comprador: str
    fecha_realizacion: date = Field(default_factory=date.today)

class ImpugnacionCreate(BaseModel):
    motivo: str
    monto_propuesto: Optional[float] = None

# ============================================================================
# BASE DE DATOS EN MEMORIA (Simulación)
# ============================================================================

procedimientos_db: Dict[str, Dict] = {}
creditos_db: Dict[str, Dict] = {}
activos_db: Dict[str, Dict] = {}

def generar_id() -> str:
    return str(uuid.uuid4())[:8].upper()

# ============================================================================
# CONSTANTES LEGALES
# ============================================================================

PRELACION_CREDITOS = {
    "primera_clase": {
        "orden": 1,
        "descripcion": "Créditos laborales, previsionales, indemnizaciones",
        "articulos": ["Art. 2472 CC", "Art. 61 Ley 20.720"]
    },
    "segunda_clase": {
        "orden": 2,
        "descripcion": "Posadero, acarreador, prenda",
        "articulos": ["Art. 2474 CC"]
    },
    "tercera_clase": {
        "orden": 3,
        "descripcion": "Créditos hipotecarios",
        "articulos": ["Art. 2477 CC"]
    },
    "cuarta_clase": {
        "orden": 4,
        "descripcion": "Fisco, instituciones públicas",
        "articulos": ["Art. 2481 CC"]
    },
    "quinta_clase": {
        "orden": 5,
        "descripcion": "Créditos valistas o quirografarios",
        "articulos": ["Art. 2489 CC"]
    }
}

PLAZOS_LEY_20720 = {
    "verificacion_ordinaria": 30,
    "verificacion_extraordinaria": 90,
    "impugnacion_creditos": 10,
    "realizacion_bienes": 120,
    "cuenta_final": 30
}

# ============================================================================
# ENDPOINTS - INFORMACIÓN DEL MÓDULO
# ============================================================================

@router.get("/info")
async def obtener_info_modulo():
    """
    Información del módulo de Liquidación Concursal.
    
    Retorna detalles sobre funcionalidades, normativas y estadísticas.
    """
    return {
        "modulo": "M07 - Liquidación Concursal",
        "version": "3.0.0",
        "normativa_principal": "Ley 20.720",
        "descripcion": "Gestión de procedimientos de reorganización y liquidación de empresas y personas",
        "funcionalidades": [
            "Liquidación voluntaria (Libro I)",
            "Liquidación forzosa (Libro II)",
            "Reorganización judicial (Libro III)",
            "Renegociación persona deudora (Libro IV)",
            "Verificación de créditos (Art. 170-179)",
            "Inventario y tasación de activos",
            "Realización de bienes (Art. 203+)",
            "Distribución según prelación legal",
            "Informes para Superintendencia",
            "Cuenta final del liquidador"
        ],
        "normativas_integradas": [
            {"ley": "Ley 20.720", "descripcion": "Reorganización y Liquidación"},
            {"ley": "Código Civil", "descripcion": "Prelación de créditos (Art. 2470+)"},
            {"ley": "DS 29/2014", "descripcion": "Reglamento Ley 20.720"},
            {"ley": "Circular SIR", "descripcion": "Instrucciones Superintendencia"}
        ],
        "tipos_procedimiento": [t.value for t in TipoProcedimiento],
        "clases_creditos": PRELACION_CREDITOS,
        "plazos_legales": PLAZOS_LEY_20720,
        "estadisticas": {
            "procedimientos_activos": len([p for p in procedimientos_db.values() if p["estado"] != "terminado"]),
            "procedimientos_terminados": len([p for p in procedimientos_db.values() if p["estado"] == "terminado"]),
            "total_creditos_verificados": len(creditos_db),
            "total_activos_inventariados": len(activos_db)
        }
    }

# ============================================================================
# ENDPOINTS - PROCEDIMIENTOS
# ============================================================================

@router.post("/procedimientos", status_code=201)
async def crear_procedimiento(data: ProcedimientoCreate):
    """
    Inicia un nuevo procedimiento concursal.
    
    Tipos disponibles:
    - liquidacion_voluntaria: Deudor solicita su propia liquidación
    - liquidacion_forzosa: Acreedor solicita liquidación del deudor
    - reorganizacion_judicial: Reestructuración de deudas
    - renegociacion_persona: Para personas naturales
    """
    proc_id = generar_id()
    
    procedimiento = {
        "id": proc_id,
        "tipo": data.tipo.value,
        "estado": EstadoProcedimiento.INICIADO.value,
        "fecha_inicio": date.today().isoformat(),
        "fecha_resolucion": None,
        "deudor": data.deudor.dict(),
        "liquidador": data.liquidador,
        "tribunal": data.tribunal,
        "rol_causa": data.rol_causa,
        "creditos_ids": [],
        "activos_ids": [],
        "resultado": None,
        "created_at": datetime.now().isoformat()
    }
    
    procedimientos_db[proc_id] = procedimiento
    
    return {
        "mensaje": "Procedimiento concursal iniciado exitosamente",
        "procedimiento_id": proc_id,
        "tipo": data.tipo.value,
        "deudor": data.deudor.nombre,
        "tribunal": data.tribunal,
        "rol_causa": data.rol_causa,
        "estado": "iniciado",
        "proximos_pasos": [
            f"1. Publicar resolución en Boletín Concursal",
            f"2. Iniciar verificación de créditos (plazo: {PLAZOS_LEY_20720['verificacion_ordinaria']} días)",
            f"3. Realizar inventario de activos",
            f"4. Proceder a tasación de bienes"
        ]
    }

@router.get("/procedimientos")
async def listar_procedimientos(
    estado: Optional[EstadoProcedimiento] = None,
    tipo: Optional[TipoProcedimiento] = None,
    limit: int = Query(20, le=100)
):
    """
    Lista procedimientos concursales con filtros opcionales.
    """
    resultado = list(procedimientos_db.values())
    
    if estado:
        resultado = [p for p in resultado if p["estado"] == estado.value]
    
    if tipo:
        resultado = [p for p in resultado if p["tipo"] == tipo.value]
    
    return {
        "procedimientos": resultado[:limit],
        "total": len(resultado),
        "filtros_aplicados": {
            "estado": estado.value if estado else None,
            "tipo": tipo.value if tipo else None
        }
    }

@router.get("/procedimientos/{proc_id}")
async def obtener_procedimiento(proc_id: str = Path(...)):
    """
    Obtiene detalle completo de un procedimiento.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    
    # Obtener créditos y activos relacionados
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    activos = [activos_db[a_id] for a_id in proc["activos_ids"] if a_id in activos_db]
    
    # Calcular totales
    total_creditos = sum(c.get("monto_verificado", 0) for c in creditos)
    total_activos_libro = sum(a.get("valor_libro", 0) for a in activos)
    total_activos_tasacion = sum(a.get("valor_tasacion", 0) for a in activos if a.get("valor_tasacion"))
    total_realizado = sum(a.get("valor_realizacion", 0) for a in activos if a.get("valor_realizacion"))
    
    return {
        **proc,
        "creditos": creditos,
        "activos": activos,
        "resumen": {
            "total_creditos_verificados": total_creditos,
            "cantidad_acreedores": len(creditos),
            "total_activos_libro": total_activos_libro,
            "total_activos_tasacion": total_activos_tasacion,
            "total_realizado": total_realizado,
            "cantidad_activos": len(activos),
            "dias_transcurridos": (date.today() - date.fromisoformat(proc["fecha_inicio"])).days
        }
    }

@router.patch("/procedimientos/{proc_id}/estado")
async def cambiar_estado_procedimiento(
    proc_id: str = Path(...),
    nuevo_estado: EstadoProcedimiento = Body(..., embed=True)
):
    """
    Cambia el estado de un procedimiento concursal.
    
    Flujo típico:
    iniciado → verificacion_creditos → realizacion_activos → distribucion → cuenta_final → terminado
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    estado_anterior = proc["estado"]
    proc["estado"] = nuevo_estado.value
    
    if nuevo_estado == EstadoProcedimiento.TERMINADO:
        proc["fecha_resolucion"] = date.today().isoformat()
    
    return {
        "mensaje": "Estado actualizado",
        "procedimiento_id": proc_id,
        "estado_anterior": estado_anterior,
        "estado_nuevo": nuevo_estado.value
    }

# ============================================================================
# ENDPOINTS - CRÉDITOS
# ============================================================================

@router.post("/procedimientos/{proc_id}/creditos", status_code=201)
async def verificar_credito(
    proc_id: str = Path(...),
    data: CreditoCreate = Body(...)
):
    """
    Verifica un crédito en el procedimiento (Art. 170-179 Ley 20.720).
    
    Clases de créditos según prelación:
    - primera_clase: Laborales, previsionales (Art. 2472 CC)
    - segunda_clase: Prenda, posadero (Art. 2474 CC)
    - tercera_clase: Hipotecarios (Art. 2477 CC)
    - cuarta_clase: Fisco, administradores (Art. 2481 CC)
    - quinta_clase: Valistas/quirografarios (Art. 2489 CC)
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    credito_id = generar_id()
    
    credito = {
        "id": credito_id,
        "procedimiento_id": proc_id,
        "acreedor_rut": data.acreedor_rut,
        "acreedor_nombre": data.acreedor_nombre,
        "monto_original": data.monto,
        "monto_verificado": data.monto,
        "clase": data.clase.value,
        "garantia": data.garantia,
        "bien_afecto": data.bien_afecto,
        "fecha_vencimiento": data.fecha_vencimiento.isoformat() if data.fecha_vencimiento else None,
        "documentos": data.documentos,
        "estado": "verificado",
        "fecha_verificacion": date.today().isoformat(),
        "prelacion": PRELACION_CREDITOS[data.clase.value]
    }
    
    creditos_db[credito_id] = credito
    procedimientos_db[proc_id]["creditos_ids"].append(credito_id)
    
    return {
        "mensaje": "Crédito verificado exitosamente",
        "credito_id": credito_id,
        "acreedor": data.acreedor_nombre,
        "monto": data.monto,
        "clase": data.clase.value,
        "prelacion": PRELACION_CREDITOS[data.clase.value],
        "plazo_impugnacion_dias": PLAZOS_LEY_20720["impugnacion_creditos"]
    }

@router.get("/procedimientos/{proc_id}/creditos")
async def listar_creditos_procedimiento(
    proc_id: str = Path(...),
    clase: Optional[ClaseCredito] = None
):
    """
    Lista créditos verificados en un procedimiento.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    
    if clase:
        creditos = [c for c in creditos if c["clase"] == clase.value]
    
    # Agrupar por clase
    por_clase = {}
    for c in creditos:
        cl = c["clase"]
        if cl not in por_clase:
            por_clase[cl] = {"creditos": [], "total": 0}
        por_clase[cl]["creditos"].append(c)
        por_clase[cl]["total"] += c["monto_verificado"]
    
    return {
        "procedimiento_id": proc_id,
        "creditos": creditos,
        "resumen_por_clase": por_clase,
        "total_general": sum(c["monto_verificado"] for c in creditos),
        "cantidad_acreedores": len(creditos)
    }

@router.post("/creditos/{credito_id}/impugnar")
async def impugnar_credito(
    credito_id: str = Path(...),
    data: ImpugnacionCreate = Body(...)
):
    """
    Impugna un crédito verificado (Art. 174-176 Ley 20.720).
    
    Plazo para impugnar: 10 días desde publicación de nómina.
    """
    if credito_id not in creditos_db:
        raise HTTPException(status_code=404, detail="Crédito no encontrado")
    
    credito = creditos_db[credito_id]
    credito["estado"] = "impugnado"
    credito["impugnacion"] = {
        "motivo": data.motivo,
        "monto_propuesto": data.monto_propuesto,
        "fecha_impugnacion": date.today().isoformat()
    }
    
    if data.monto_propuesto is not None:
        credito["monto_verificado"] = data.monto_propuesto
    
    return {
        "mensaje": "Crédito impugnado",
        "credito_id": credito_id,
        "estado": "impugnado",
        "plazo_resolucion_dias": PLAZOS_LEY_20720["impugnacion_creditos"]
    }

# ============================================================================
# ENDPOINTS - ACTIVOS
# ============================================================================

@router.post("/procedimientos/{proc_id}/activos", status_code=201)
async def agregar_activo(
    proc_id: str = Path(...),
    data: ActivoCreate = Body(...)
):
    """
    Agrega un activo al inventario del procedimiento.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    activo_id = generar_id()
    
    activo = {
        "id": activo_id,
        "procedimiento_id": proc_id,
        "tipo": data.tipo.value,
        "descripcion": data.descripcion,
        "ubicacion": data.ubicacion,
        "valor_libro": data.valor_libro,
        "valor_tasacion": None,
        "valor_realizacion": None,
        "gravamenes": data.gravamenes,
        "estado": "inventariado",
        "fecha_inventario": date.today().isoformat(),
        "tasacion": None,
        "realizacion": None
    }
    
    activos_db[activo_id] = activo
    procedimientos_db[proc_id]["activos_ids"].append(activo_id)
    
    return {
        "mensaje": "Activo agregado al inventario",
        "activo_id": activo_id,
        "tipo": data.tipo.value,
        "descripcion": data.descripcion,
        "valor_libro": data.valor_libro,
        "tiene_gravamenes": len(data.gravamenes) > 0,
        "proximo_paso": "Proceder a tasación del activo"
    }

@router.get("/procedimientos/{proc_id}/activos")
async def listar_activos_procedimiento(proc_id: str = Path(...)):
    """
    Lista activos del procedimiento con estado de realización.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    activos = [activos_db[a_id] for a_id in proc["activos_ids"] if a_id in activos_db]
    
    return {
        "procedimiento_id": proc_id,
        "activos": activos,
        "resumen": {
            "total_inventariados": len(activos),
            "total_tasados": len([a for a in activos if a["valor_tasacion"]]),
            "total_realizados": len([a for a in activos if a["valor_realizacion"]]),
            "valor_libro_total": sum(a["valor_libro"] for a in activos),
            "valor_tasacion_total": sum(a["valor_tasacion"] or 0 for a in activos),
            "valor_realizado_total": sum(a["valor_realizacion"] or 0 for a in activos)
        }
    }

@router.post("/activos/{activo_id}/tasar")
async def tasar_activo(
    activo_id: str = Path(...),
    data: TasacionCreate = Body(...)
):
    """
    Registra tasación de un activo.
    """
    if activo_id not in activos_db:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    
    activo = activos_db[activo_id]
    activo["valor_tasacion"] = data.valor_tasacion
    activo["estado"] = "tasado"
    activo["tasacion"] = {
        "valor": data.valor_tasacion,
        "tasador": data.tasador,
        "fecha": data.fecha_tasacion.isoformat(),
        "metodologia": data.metodologia
    }
    
    variacion = ((data.valor_tasacion - activo["valor_libro"]) / activo["valor_libro"]) * 100
    
    return {
        "mensaje": "Activo tasado exitosamente",
        "activo_id": activo_id,
        "valor_libro": activo["valor_libro"],
        "valor_tasacion": data.valor_tasacion,
        "variacion_porcentual": round(variacion, 2),
        "tasador": data.tasador,
        "proximo_paso": "Proceder a realización del activo"
    }

@router.post("/activos/{activo_id}/realizar")
async def realizar_activo(
    activo_id: str = Path(...),
    data: RealizacionCreate = Body(...)
):
    """
    Registra la realización (venta) de un activo (Art. 203+ Ley 20.720).
    
    Métodos de realización:
    - subasta_publica: Remate público
    - venta_directa: Venta directa autorizada
    - licitacion_privada: Ofertas cerradas
    - venta_unidad_economica: Venta como empresa en marcha
    """
    if activo_id not in activos_db:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    
    activo = activos_db[activo_id]
    activo["valor_realizacion"] = data.valor_realizacion
    activo["estado"] = "realizado"
    activo["realizacion"] = {
        "metodo": data.metodo.value,
        "valor": data.valor_realizacion,
        "comprador": data.comprador,
        "fecha": data.fecha_realizacion.isoformat()
    }
    
    # Calcular eficiencia vs tasación
    if activo["valor_tasacion"]:
        eficiencia = (data.valor_realizacion / activo["valor_tasacion"]) * 100
    else:
        eficiencia = (data.valor_realizacion / activo["valor_libro"]) * 100
    
    return {
        "mensaje": "Activo realizado exitosamente",
        "activo_id": activo_id,
        "metodo": data.metodo.value,
        "valor_realizacion": data.valor_realizacion,
        "comprador": data.comprador,
        "eficiencia_realizacion": round(eficiencia, 2),
        "comparacion": {
            "valor_libro": activo["valor_libro"],
            "valor_tasacion": activo["valor_tasacion"],
            "valor_realizado": data.valor_realizacion
        }
    }

# ============================================================================
# ENDPOINTS - DISTRIBUCIÓN
# ============================================================================

@router.post("/procedimientos/{proc_id}/calcular-distribucion")
async def calcular_distribucion(proc_id: str = Path(...)):
    """
    Calcula la distribución de fondos según prelación legal.
    
    Orden de prelación (Código Civil):
    1. Primera clase: Laborales, previsionales (100%)
    2. Segunda clase: Prenda (hasta valor del bien)
    3. Tercera clase: Hipotecarios (hasta valor inmueble)
    4. Cuarta clase: Fisco
    5. Quinta clase: Valistas (a prorrata del saldo)
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    
    # Obtener datos
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    activos = [activos_db[a_id] for a_id in proc["activos_ids"] if a_id in activos_db]
    
    # Total realizado
    total_realizado = sum(a.get("valor_realizacion", 0) for a in activos if a.get("valor_realizacion"))
    
    # Costos del procedimiento (5% estimado)
    costos_procedimiento = total_realizado * 0.05
    
    # Fondos disponibles
    fondos_disponibles = total_realizado - costos_procedimiento
    
    # Totales por clase
    totales = {
        "primera_clase": sum(c["monto_verificado"] for c in creditos if c["clase"] == "primera_clase"),
        "segunda_clase": sum(c["monto_verificado"] for c in creditos if c["clase"] == "segunda_clase"),
        "tercera_clase": sum(c["monto_verificado"] for c in creditos if c["clase"] == "tercera_clase"),
        "cuarta_clase": sum(c["monto_verificado"] for c in creditos if c["clase"] == "cuarta_clase"),
        "quinta_clase": sum(c["monto_verificado"] for c in creditos if c["clase"] == "quinta_clase"),
    }
    
    # Distribución según prelación
    pagos = {}
    remanente = fondos_disponibles
    
    for clase in ["primera_clase", "segunda_clase", "tercera_clase", "cuarta_clase", "quinta_clase"]:
        if remanente > 0:
            pago = min(remanente, totales[clase])
            pagos[clase] = pago
            remanente -= pago
        else:
            pagos[clase] = 0
    
    # Porcentaje de recuperación valistas
    if totales["quinta_clase"] > 0:
        pct_valistas = (pagos["quinta_clase"] / totales["quinta_clase"]) * 100
    else:
        pct_valistas = 0
    
    # Guardar resultado
    resultado = {
        "fecha_calculo": datetime.now().isoformat(),
        "total_activos_realizados": total_realizado,
        "costos_procedimiento": costos_procedimiento,
        "fondos_distribuibles": fondos_disponibles,
        "total_creditos_verificados": sum(totales.values()),
        "distribucion": {
            "primera_clase": {"monto_creditos": totales["primera_clase"], "monto_pagar": pagos["primera_clase"]},
            "segunda_clase": {"monto_creditos": totales["segunda_clase"], "monto_pagar": pagos["segunda_clase"]},
            "tercera_clase": {"monto_creditos": totales["tercera_clase"], "monto_pagar": pagos["tercera_clase"]},
            "cuarta_clase": {"monto_creditos": totales["cuarta_clase"], "monto_pagar": pagos["cuarta_clase"]},
            "quinta_clase": {"monto_creditos": totales["quinta_clase"], "monto_pagar": pagos["quinta_clase"]},
        },
        "total_a_distribuir": sum(pagos.values()),
        "porcentaje_recuperacion_valistas": round(pct_valistas, 2),
        "remanente": remanente
    }
    
    proc["resultado"] = resultado
    
    return {
        "mensaje": "Distribución calculada según prelación legal",
        "procedimiento_id": proc_id,
        **resultado,
        "normativa_aplicada": [
            "Art. 2470+ Código Civil (Prelación de créditos)",
            "Art. 39 Ley 20.720 (Costos procedimiento)",
            "Art. 243+ Ley 20.720 (Distribución)"
        ]
    }

@router.get("/procedimientos/{proc_id}/proyecto-reparto")
async def generar_proyecto_reparto(proc_id: str = Path(...)):
    """
    Genera proyecto de reparto para aprobación judicial.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    
    if not proc.get("resultado"):
        raise HTTPException(
            status_code=400, 
            detail="Debe calcular la distribución primero usando POST /calcular-distribucion"
        )
    
    resultado = proc["resultado"]
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    
    # Generar detalle por acreedor
    detalle_acreedores = []
    for clase in ["primera_clase", "segunda_clase", "tercera_clase", "cuarta_clase", "quinta_clase"]:
        creditos_clase = [c for c in creditos if c["clase"] == clase]
        total_clase = sum(c["monto_verificado"] for c in creditos_clase)
        monto_pagar_clase = resultado["distribucion"][clase]["monto_pagar"]
        
        for credito in creditos_clase:
            if total_clase > 0:
                pago_individual = (credito["monto_verificado"] / total_clase) * monto_pagar_clase
            else:
                pago_individual = 0
            
            detalle_acreedores.append({
                "clase": clase,
                "acreedor_rut": credito["acreedor_rut"],
                "acreedor_nombre": credito["acreedor_nombre"],
                "credito_verificado": credito["monto_verificado"],
                "monto_a_pagar": round(pago_individual, 0),
                "porcentaje_recuperacion": round((pago_individual / credito["monto_verificado"] * 100) if credito["monto_verificado"] > 0 else 0, 2)
            })
    
    return {
        "titulo": "PROYECTO DE REPARTO",
        "procedimiento_id": proc_id,
        "fecha_proyecto": date.today().isoformat(),
        "deudor": proc["deudor"],
        "tribunal": proc["tribunal"],
        "rol_causa": proc["rol_causa"],
        "resumen_distribucion": resultado["distribucion"],
        "detalle_acreedores": detalle_acreedores,
        "total_a_distribuir": resultado["total_a_distribuir"],
        "observacion": f"Porcentaje de recuperación para acreedores valistas: {resultado['porcentaje_recuperacion_valistas']}%"
    }

# ============================================================================
# ENDPOINTS - INFORMES
# ============================================================================

@router.get("/procedimientos/{proc_id}/informe-superintendencia")
async def generar_informe_superintendencia(proc_id: str = Path(...)):
    """
    Genera informe periódico para Superintendencia de Insolvencia y Reemprendimiento.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    activos = [activos_db[a_id] for a_id in proc["activos_ids"] if a_id in activos_db]
    
    return {
        "encabezado": {
            "tipo_informe": "Informe Periódico Liquidador",
            "procedimiento_id": proc["id"],
            "tipo_procedimiento": proc["tipo"],
            "tribunal": proc["tribunal"],
            "rol_causa": proc["rol_causa"],
            "liquidador": proc["liquidador"],
            "fecha_informe": date.today().isoformat()
        },
        "deudor": proc["deudor"],
        "estado_procedimiento": {
            "estado_actual": proc["estado"],
            "fecha_inicio": proc["fecha_inicio"],
            "dias_transcurridos": (date.today() - date.fromisoformat(proc["fecha_inicio"])).days
        },
        "activos": {
            "total_inventariados": len(activos),
            "total_realizados": len([a for a in activos if a.get("valor_realizacion")]),
            "valor_libro": sum(a["valor_libro"] for a in activos),
            "valor_tasacion": sum(a.get("valor_tasacion", 0) for a in activos),
            "valor_realizado": sum(a.get("valor_realizacion", 0) for a in activos)
        },
        "creditos": {
            "total_verificados": len(creditos),
            "por_clase": {
                clase: {
                    "cantidad": len([c for c in creditos if c["clase"] == clase]),
                    "monto": sum(c["monto_verificado"] for c in creditos if c["clase"] == clase)
                }
                for clase in ["primera_clase", "segunda_clase", "tercera_clase", "cuarta_clase", "quinta_clase"]
            },
            "monto_total": sum(c["monto_verificado"] for c in creditos)
        },
        "cumplimiento_plazos": {
            "verificacion_creditos": "cumplido" if proc["estado"] != "iniciado" else "en_curso",
            "realizacion_bienes": "cumplido" if len([a for a in activos if a.get("valor_realizacion")]) > 0 else "pendiente"
        }
    }

@router.get("/procedimientos/{proc_id}/cuenta-final")
async def generar_cuenta_final(proc_id: str = Path(...)):
    """
    Genera cuenta final del liquidador (Art. 49-51 Ley 20.720).
    
    Plazo para objeciones: 15 días desde notificación.
    """
    if proc_id not in procedimientos_db:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    
    proc = procedimientos_db[proc_id]
    
    if not proc.get("resultado"):
        raise HTTPException(
            status_code=400,
            detail="Debe calcular la distribución primero"
        )
    
    resultado = proc["resultado"]
    creditos = [creditos_db[c_id] for c_id in proc["creditos_ids"] if c_id in creditos_db]
    activos = [activos_db[a_id] for a_id in proc["activos_ids"] if a_id in activos_db]
    
    return {
        "titulo": "CUENTA FINAL DE ADMINISTRACIÓN",
        "procedimiento": {
            "id": proc["id"],
            "tipo": proc["tipo"],
            "deudor": proc["deudor"]["nombre"],
            "tribunal": proc["tribunal"],
            "rol": proc["rol_causa"]
        },
        "periodo": {
            "fecha_inicio": proc["fecha_inicio"],
            "fecha_termino": date.today().isoformat(),
            "dias_totales": (date.today() - date.fromisoformat(proc["fecha_inicio"])).days
        },
        "resumen_activos": {
            "inventariados": len(activos),
            "realizados": len([a for a in activos if a.get("valor_realizacion")]),
            "valor_total_realizado": resultado["total_activos_realizados"]
        },
        "resumen_pasivos": {
            "creditos_verificados": len(creditos),
            "monto_total_creditos": resultado["total_creditos_verificados"]
        },
        "distribucion_efectuada": resultado["distribucion"],
        "costos_procedimiento": resultado["costos_procedimiento"],
        "remanente": resultado["remanente"],
        "porcentaje_recuperacion_valistas": resultado["porcentaje_recuperacion_valistas"],
        "liquidador": proc["liquidador"],
        "fecha_cuenta": date.today().isoformat(),
        "plazo_objeciones_dias": PLAZOS_LEY_20720["cuenta_final"],
        "normativa": [
            "Art. 49-51 Ley 20.720 (Cuenta Final)",
            "Art. 39 Ley 20.720 (Honorarios)",
            "Art. 243+ Ley 20.720 (Distribución)"
        ]
    }

# ============================================================================
# ENDPOINTS - UTILIDADES
# ============================================================================

@router.get("/simulador-distribucion")
async def simular_distribucion(
    total_activos: float = Query(..., gt=0, description="Total activos a realizar"),
    creditos_primera: float = Query(0, ge=0, description="Créditos primera clase"),
    creditos_segunda: float = Query(0, ge=0, description="Créditos segunda clase"),
    creditos_tercera: float = Query(0, ge=0, description="Créditos tercera clase"),
    creditos_cuarta: float = Query(0, ge=0, description="Créditos cuarta clase"),
    creditos_quinta: float = Query(0, ge=0, description="Créditos quinta clase (valistas)")
):
    """
    Simulador de distribución de fondos según prelación legal.
    
    Útil para estimar recuperación antes de iniciar procedimiento.
    """
    # Costos estimados (5%)
    costos = total_activos * 0.05
    fondos = total_activos - costos
    
    totales = {
        "primera_clase": creditos_primera,
        "segunda_clase": creditos_segunda,
        "tercera_clase": creditos_tercera,
        "cuarta_clase": creditos_cuarta,
        "quinta_clase": creditos_quinta,
    }
    
    pagos = {}
    remanente = fondos
    
    for clase in ["primera_clase", "segunda_clase", "tercera_clase", "cuarta_clase", "quinta_clase"]:
        if remanente > 0:
            pago = min(remanente, totales[clase])
            pagos[clase] = pago
            remanente -= pago
        else:
            pagos[clase] = 0
    
    # Porcentajes de recuperación
    recuperacion = {}
    for clase, monto in totales.items():
        if monto > 0:
            recuperacion[clase] = round((pagos[clase] / monto) * 100, 2)
        else:
            recuperacion[clase] = 0
    
    return {
        "titulo": "Simulación de Distribución",
        "inputs": {
            "total_activos": total_activos,
            "creditos": totales,
            "total_creditos": sum(totales.values())
        },
        "resultado": {
            "costos_procedimiento_estimados": costos,
            "fondos_distribuibles": fondos,
            "distribucion_por_clase": {
                clase: {
                    "creditos": totales[clase],
                    "pago": pagos[clase],
                    "recuperacion_pct": recuperacion[clase]
                }
                for clase in totales
            },
            "total_a_distribuir": sum(pagos.values()),
            "remanente": remanente,
            "deficit": max(0, sum(totales.values()) - fondos)
        },
        "conclusion": (
            f"Los acreedores valistas (quinta clase) recuperarían aproximadamente "
            f"{recuperacion['quinta_clase']}% de sus créditos."
        )
    }

@router.get("/normativa")
async def obtener_normativa_aplicable():
    """
    Retorna normativa aplicable a procedimientos concursales.
    """
    return {
        "ley_principal": {
            "nombre": "Ley 20.720",
            "titulo": "Ley de Reorganización y Liquidación de Empresas y Personas",
            "fecha_publicacion": "2014-01-09",
            "libros": [
                {"numero": "I", "titulo": "Liquidación Voluntaria", "articulos": "Art. 115-170"},
                {"numero": "II", "titulo": "Liquidación Forzosa", "articulos": "Art. 171-193"},
                {"numero": "III", "titulo": "Reorganización Judicial", "articulos": "Art. 54-114"},
                {"numero": "IV", "titulo": "Renegociación de Persona Deudora", "articulos": "Art. 260-283"}
            ]
        },
        "prelacion_creditos": {
            "fuente": "Código Civil (Art. 2470+)",
            "clases": PRELACION_CREDITOS
        },
        "plazos_legales": PLAZOS_LEY_20720,
        "instituciones": [
            {
                "nombre": "Superintendencia de Insolvencia y Reemprendimiento",
                "sigla": "SUPERIR",
                "rol": "Fiscalización de procedimientos concursales",
                "web": "https://www.superir.gob.cl"
            },
            {
                "nombre": "Boletín Concursal",
                "rol": "Publicidad de actuaciones",
                "web": "https://www.boletinconcursal.cl"
            }
        ],
        "reglamentos": [
            "DS 29/2014 - Reglamento Ley 20.720",
            "Circulares SUPERIR"
        ]
    }
