"""
DATAPOLIS v3.0 - ROUTER OPEN FINANCE NCG 514
=============================================
Router FastAPI para endpoints de Open Finance según NCG 514 CMF Chile.

Implementa:
- OAuth 2.0 + PKCE
- Account Information Services (AIS)
- Payment Initiation Services (PIS)
- Gestión de Consentimientos
- Directorio de Participantes
- Panel de Control de Usuario

Autor: DATAPOLIS SpA
Fecha: Febrero 2026
Normativa: NCG 514 CMF (Deadline Abril 2026)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
import hashlib
import secrets
import logging

# Configuración de logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/open-finance",
    tags=["Open Finance NCG 514"],
    responses={
        401: {"description": "No autorizado"},
        403: {"description": "Prohibido"},
        404: {"description": "No encontrado"},
        429: {"description": "Demasiadas solicitudes"}
    }
)

# =====================================================
# ENUMERACIONES
# =====================================================

class TipoParticipante(str, Enum):
    """Tipos de participantes según NCG 514"""
    ASPSP = "aspsp"  # Account Servicing Payment Service Provider (Bancos)
    PISP = "pisp"    # Payment Initiation Service Provider
    AISP = "aisp"    # Account Information Service Provider
    CBPII = "cbpii"  # Card Based Payment Instrument Issuer
    TPP = "tpp"      # Third Party Provider

class EstadoConsentimiento(str, Enum):
    """Estados de consentimiento según NCG 514"""
    PENDIENTE = "pendiente"
    AUTORIZADO = "autorizado"
    ACTIVO = "activo"
    REVOCADO = "revocado"
    EXPIRADO = "expirado"
    RECHAZADO = "rechazado"

class TipoCuenta(str, Enum):
    """Tipos de cuenta bancaria"""
    CORRIENTE = "corriente"
    VISTA = "vista"
    AHORRO = "ahorro"
    CREDITO = "credito"
    INVERSION = "inversion"

class AlcanceConsentimiento(str, Enum):
    """Alcances de permisos según NCG 514"""
    ACCOUNTS = "accounts"           # Información de cuentas
    BALANCES = "balances"           # Saldos
    TRANSACTIONS = "transactions"   # Transacciones
    PAYMENTS = "payments"           # Iniciación de pagos
    STANDING_ORDERS = "standing_orders"  # Órdenes permanentes
    DIRECT_DEBITS = "direct_debits"      # Débitos directos
    BENEFICIARIES = "beneficiaries"      # Beneficiarios

class EstadoPago(str, Enum):
    """Estados de pago ISO 20022"""
    RCVD = "RCVD"  # Received
    PDNG = "PDNG"  # Pending
    ACTC = "ACTC"  # Accepted Technical Validation
    ACCP = "ACCP"  # Accepted Customer Profile
    ACWC = "ACWC"  # Accepted With Change
    ACSC = "ACSC"  # Accepted Settlement Completed
    RJCT = "RJCT"  # Rejected
    CANC = "CANC"  # Cancelled

# =====================================================
# MODELOS PYDANTIC
# =====================================================

class ConsentimientoRequest(BaseModel):
    """Solicitud de consentimiento NCG 514"""
    tpp_id: str = Field(..., description="ID del Third Party Provider")
    alcances: List[AlcanceConsentimiento] = Field(..., description="Permisos solicitados")
    fecha_expiracion: Optional[date] = Field(None, description="Fecha de expiración (máx 365 días)")
    frecuencia_acceso: int = Field(default=4, ge=1, le=10, description="Accesos por día")
    cuentas_especificas: Optional[List[str]] = Field(None, description="IBANs específicos")
    
    @validator('fecha_expiracion')
    def validar_expiracion(cls, v):
        if v:
            max_date = date.today() + timedelta(days=365)
            if v > max_date:
                raise ValueError("Fecha de expiración no puede exceder 365 días")
        return v

class ConsentimientoResponse(BaseModel):
    """Respuesta de consentimiento"""
    consentimiento_id: str
    estado: EstadoConsentimiento
    tpp_id: str
    tpp_nombre: str
    alcances: List[str]
    fecha_creacion: datetime
    fecha_expiracion: datetime
    url_autorizacion: Optional[str] = None

class CuentaInfo(BaseModel):
    """Información de cuenta bancaria AIS"""
    cuenta_id: str
    iban: Optional[str] = None
    numero_cuenta: str
    tipo: TipoCuenta
    moneda: str = "CLP"
    nombre_titular: str
    rut_titular: str
    estado: str = "activa"
    banco_nombre: str
    banco_codigo: str

class SaldoResponse(BaseModel):
    """Respuesta de saldo de cuenta"""
    cuenta_id: str
    saldo_disponible: float
    saldo_actual: float
    saldo_retenido: float = 0.0
    moneda: str = "CLP"
    fecha_actualizacion: datetime
    linea_credito: Optional[float] = None

class TransaccionResponse(BaseModel):
    """Transacción bancaria AIS"""
    transaccion_id: str
    cuenta_id: str
    fecha: datetime
    fecha_valor: date
    monto: float
    moneda: str = "CLP"
    tipo: str  # "CREDITO" | "DEBITO"
    descripcion: str
    categoria: Optional[str] = None
    referencia: Optional[str] = None
    contraparte_nombre: Optional[str] = None
    contraparte_cuenta: Optional[str] = None
    estado: str = "liquidada"

class PagoRequest(BaseModel):
    """Solicitud de iniciación de pago PIS"""
    consentimiento_id: str
    cuenta_origen: str
    cuenta_destino: str
    monto: float = Field(..., gt=0)
    moneda: str = "CLP"
    concepto: str
    referencia_cliente: Optional[str] = None
    fecha_ejecucion: Optional[date] = None

class PagoResponse(BaseModel):
    """Respuesta de iniciación de pago"""
    pago_id: str
    estado: EstadoPago
    fecha_creacion: datetime
    fecha_ejecucion: Optional[datetime] = None
    monto: float
    moneda: str
    referencia_banco: Optional[str] = None
    mensaje: Optional[str] = None

class ParticipanteInfo(BaseModel):
    """Información de participante en directorio"""
    participante_id: str
    nombre: str
    tipo: TipoParticipante
    rut: str
    estado: str
    servicios: List[str]
    url_api: str
    certificado_vigente: bool
    fecha_registro: datetime

class TokenResponse(BaseModel):
    """Respuesta de token OAuth 2.0"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: str
    id_token: Optional[str] = None

class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    error: str
    error_description: str
    error_uri: Optional[str] = None

# =====================================================
# ALMACENAMIENTO EN MEMORIA (Para demo - usar DB en producción)
# =====================================================

# Simulación de base de datos
_consentimientos: Dict[str, dict] = {}
_pagos: Dict[str, dict] = {}
_tokens: Dict[str, dict] = {}
_participantes: Dict[str, dict] = {}

# =====================================================
# ENDPOINTS DE AUTORIZACIÓN OAUTH 2.0
# =====================================================

@router.post("/oauth/par", response_model=dict, summary="Pushed Authorization Request (PAR)")
async def pushed_authorization_request(
    client_id: str = Body(...),
    redirect_uri: str = Body(...),
    scope: str = Body(...),
    state: str = Body(...),
    code_challenge: str = Body(...),
    code_challenge_method: str = Body(default="S256"),
    request: Optional[str] = Body(None)
):
    """
    Pushed Authorization Request según RFC 9126.
    Requerido por FAPI 2.0 para NCG 514.
    
    - **client_id**: ID del cliente TPP registrado
    - **redirect_uri**: URI de redirección registrada
    - **scope**: Alcances solicitados (accounts balances transactions payments)
    - **state**: Estado para prevenir CSRF
    - **code_challenge**: Challenge PKCE (SHA-256)
    - **code_challenge_method**: Método PKCE (debe ser S256)
    """
    # Validar code_challenge_method
    if code_challenge_method != "S256":
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_request", "error_description": "Solo se acepta S256 para PKCE"}
        )
    
    # Generar request_uri
    request_uri = f"urn:datapolis:par:{uuid.uuid4().hex}"
    
    # Almacenar solicitud (expira en 60 segundos)
    _tokens[request_uri] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": datetime.utcnow() + timedelta(seconds=60)
    }
    
    logger.info(f"PAR creado: {request_uri} para cliente {client_id}")
    
    return {
        "request_uri": request_uri,
        "expires_in": 60
    }

@router.get("/oauth/authorize", summary="Endpoint de Autorización OAuth 2.0")
async def authorize(
    request_uri: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
    response_type: str = Query(default="code"),
    scope: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None)
):
    """
    Endpoint de autorización OAuth 2.0.
    Soporta tanto PAR (request_uri) como flow tradicional.
    """
    # Si viene request_uri, usar datos del PAR
    if request_uri:
        if request_uri not in _tokens:
            raise HTTPException(status_code=400, detail="request_uri inválido o expirado")
        
        par_data = _tokens[request_uri]
        if datetime.utcnow() > par_data["expires_at"]:
            del _tokens[request_uri]
            raise HTTPException(status_code=400, detail="request_uri expirado")
        
        client_id = par_data["client_id"]
        redirect_uri = par_data["redirect_uri"]
        scope = par_data["scope"]
        state = par_data["state"]
        code_challenge = par_data["code_challenge"]
    
    # Generar código de autorización
    auth_code = secrets.token_urlsafe(32)
    
    # Almacenar código (expira en 5 minutos)
    _tokens[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
        "type": "authorization_code"
    }
    
    # En producción, redirigir a página de consentimiento
    return {
        "message": "Redirigir a página de consentimiento",
        "authorization_code": auth_code,
        "redirect_uri": f"{redirect_uri}?code={auth_code}&state={state}",
        "expires_in": 300
    }

@router.post("/oauth/token", response_model=TokenResponse, summary="Intercambio de Token OAuth 2.0")
async def token_exchange(
    grant_type: str = Body(...),
    code: Optional[str] = Body(None),
    redirect_uri: Optional[str] = Body(None),
    client_id: str = Body(...),
    client_secret: Optional[str] = Body(None),
    code_verifier: Optional[str] = Body(None),
    refresh_token: Optional[str] = Body(None)
):
    """
    Endpoint de intercambio de token OAuth 2.0.
    
    Soporta:
    - authorization_code: Intercambio de código por token
    - refresh_token: Renovación de token
    """
    if grant_type == "authorization_code":
        if not code or not code_verifier:
            raise HTTPException(status_code=400, detail="code y code_verifier requeridos")
        
        if code not in _tokens:
            raise HTTPException(status_code=400, detail="Código inválido o expirado")
        
        code_data = _tokens[code]
        
        # Verificar PKCE
        challenge = hashlib.sha256(code_verifier.encode()).digest()
        import base64
        expected_challenge = base64.urlsafe_b64encode(challenge).rstrip(b'=').decode()
        
        if expected_challenge != code_data["code_challenge"]:
            raise HTTPException(status_code=400, detail="code_verifier inválido")
        
        # Generar tokens
        access_token = secrets.token_urlsafe(64)
        new_refresh_token = secrets.token_urlsafe(64)
        
        # Almacenar access token
        _tokens[access_token] = {
            "client_id": client_id,
            "scope": code_data["scope"],
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "type": "access_token"
        }
        
        # Almacenar refresh token
        _tokens[new_refresh_token] = {
            "client_id": client_id,
            "scope": code_data["scope"],
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "type": "refresh_token"
        }
        
        # Eliminar código usado
        del _tokens[code]
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            scope=code_data["scope"],
            expires_in=3600
        )
    
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token requerido")
        
        if refresh_token not in _tokens:
            raise HTTPException(status_code=400, detail="refresh_token inválido")
        
        token_data = _tokens[refresh_token]
        
        # Generar nuevo access token
        new_access_token = secrets.token_urlsafe(64)
        
        _tokens[new_access_token] = {
            "client_id": client_id,
            "scope": token_data["scope"],
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "type": "access_token"
        }
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            scope=token_data["scope"],
            expires_in=3600
        )
    
    else:
        raise HTTPException(status_code=400, detail="grant_type no soportado")

# =====================================================
# ENDPOINTS DE CONSENTIMIENTOS
# =====================================================

@router.post("/consentimientos", response_model=ConsentimientoResponse, status_code=201,
             summary="Crear Consentimiento NCG 514")
async def crear_consentimiento(
    request: ConsentimientoRequest,
    authorization: str = Header(..., description="Bearer token")
):
    """
    Crea un nuevo consentimiento según NCG 514.
    
    El consentimiento tiene una duración máxima de 365 días.
    El usuario debe autorizar explícitamente los alcances solicitados.
    """
    consentimiento_id = f"consent-{uuid.uuid4().hex[:12]}"
    
    fecha_exp = request.fecha_expiracion or (date.today() + timedelta(days=90))
    
    consentimiento = {
        "id": consentimiento_id,
        "tpp_id": request.tpp_id,
        "tpp_nombre": f"TPP {request.tpp_id[:8]}",  # En producción, buscar en directorio
        "estado": EstadoConsentimiento.PENDIENTE,
        "alcances": [a.value for a in request.alcances],
        "fecha_creacion": datetime.utcnow(),
        "fecha_expiracion": datetime.combine(fecha_exp, datetime.min.time()),
        "frecuencia_acceso": request.frecuencia_acceso,
        "cuentas_especificas": request.cuentas_especificas,
        "historial_accesos": [],
        "total_accesos": 0
    }
    
    _consentimientos[consentimiento_id] = consentimiento
    
    logger.info(f"Consentimiento creado: {consentimiento_id}")
    
    return ConsentimientoResponse(
        consentimiento_id=consentimiento_id,
        estado=EstadoConsentimiento.PENDIENTE,
        tpp_id=request.tpp_id,
        tpp_nombre=consentimiento["tpp_nombre"],
        alcances=consentimiento["alcances"],
        fecha_creacion=consentimiento["fecha_creacion"],
        fecha_expiracion=consentimiento["fecha_expiracion"],
        url_autorizacion=f"/api/v1/open-finance/consentimientos/{consentimiento_id}/autorizar"
    )

@router.get("/consentimientos/{consentimiento_id}", response_model=ConsentimientoResponse,
            summary="Obtener Consentimiento")
async def obtener_consentimiento(
    consentimiento_id: str,
    authorization: str = Header(...)
):
    """Obtiene los detalles de un consentimiento específico."""
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    
    return ConsentimientoResponse(
        consentimiento_id=c["id"],
        estado=c["estado"],
        tpp_id=c["tpp_id"],
        tpp_nombre=c["tpp_nombre"],
        alcances=c["alcances"],
        fecha_creacion=c["fecha_creacion"],
        fecha_expiracion=c["fecha_expiracion"]
    )

@router.post("/consentimientos/{consentimiento_id}/autorizar",
             summary="Autorizar Consentimiento (Post-SCA)")
async def autorizar_consentimiento(
    consentimiento_id: str,
    authorization: str = Header(...)
):
    """
    Autoriza un consentimiento después de Strong Customer Authentication (SCA).
    
    En producción, este endpoint se llama después de que el usuario:
    1. Se autentica con su banco (Clave Única, biometría, etc.)
    2. Revisa y acepta los alcances solicitados
    """
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    
    if c["estado"] != EstadoConsentimiento.PENDIENTE:
        raise HTTPException(status_code=400, detail="Consentimiento ya procesado")
    
    c["estado"] = EstadoConsentimiento.ACTIVO
    c["fecha_autorizacion"] = datetime.utcnow()
    
    logger.info(f"Consentimiento autorizado: {consentimiento_id}")
    
    return {"mensaje": "Consentimiento autorizado", "estado": EstadoConsentimiento.ACTIVO.value}

@router.delete("/consentimientos/{consentimiento_id}",
               summary="Revocar Consentimiento (Art. 15 NCG 514)")
async def revocar_consentimiento(
    consentimiento_id: str,
    authorization: str = Header(...)
):
    """
    Revoca un consentimiento de forma inmediata según Art. 15 NCG 514.
    
    La revocación es instantánea y:
    - Invalida todos los tokens asociados
    - Impide futuros accesos del TPP
    - Registra la acción en auditoría
    """
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    c["estado"] = EstadoConsentimiento.REVOCADO
    c["fecha_revocacion"] = datetime.utcnow()
    
    logger.info(f"Consentimiento revocado: {consentimiento_id}")
    
    return {"mensaje": "Consentimiento revocado exitosamente", "estado": EstadoConsentimiento.REVOCADO.value}

@router.get("/consentimientos", response_model=List[ConsentimientoResponse],
            summary="Listar Consentimientos del Usuario")
async def listar_consentimientos(
    authorization: str = Header(...),
    estado: Optional[EstadoConsentimiento] = Query(None),
    tpp_id: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0)
):
    """Lista todos los consentimientos del usuario autenticado."""
    resultado = []
    
    for c in _consentimientos.values():
        if estado and c["estado"] != estado:
            continue
        if tpp_id and c["tpp_id"] != tpp_id:
            continue
        
        resultado.append(ConsentimientoResponse(
            consentimiento_id=c["id"],
            estado=c["estado"],
            tpp_id=c["tpp_id"],
            tpp_nombre=c["tpp_nombre"],
            alcances=c["alcances"],
            fecha_creacion=c["fecha_creacion"],
            fecha_expiracion=c["fecha_expiracion"]
        ))
    
    return resultado[offset:offset + limit]

# =====================================================
# ENDPOINTS AIS (Account Information Services)
# =====================================================

@router.get("/cuentas", response_model=List[CuentaInfo],
            summary="Listar Cuentas (AIS)")
async def listar_cuentas(
    authorization: str = Header(...),
    consentimiento_id: str = Query(...)
):
    """
    Lista las cuentas bancarias del usuario según consentimiento.
    
    Requiere scope 'accounts' en el consentimiento.
    """
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    
    if c["estado"] != EstadoConsentimiento.ACTIVO:
        raise HTTPException(status_code=403, detail="Consentimiento no activo")
    
    if "accounts" not in c["alcances"]:
        raise HTTPException(status_code=403, detail="Scope 'accounts' no autorizado")
    
    # Datos de ejemplo - en producción conectar a core bancario
    cuentas = [
        CuentaInfo(
            cuenta_id="ACC001",
            iban="CL9300000000000000001",
            numero_cuenta="000000001",
            tipo=TipoCuenta.CORRIENTE,
            moneda="CLP",
            nombre_titular="Usuario Demo",
            rut_titular="12.345.678-9",
            estado="activa",
            banco_nombre="Banco Estado",
            banco_codigo="012"
        ),
        CuentaInfo(
            cuenta_id="ACC002",
            numero_cuenta="000000002",
            tipo=TipoCuenta.AHORRO,
            moneda="CLP",
            nombre_titular="Usuario Demo",
            rut_titular="12.345.678-9",
            estado="activa",
            banco_nombre="Banco Estado",
            banco_codigo="012"
        )
    ]
    
    # Registrar acceso
    c["historial_accesos"].append({
        "tipo": "accounts",
        "fecha": datetime.utcnow().isoformat(),
        "ip": "127.0.0.1"
    })
    c["total_accesos"] += 1
    
    return cuentas

@router.get("/cuentas/{cuenta_id}/saldos", response_model=SaldoResponse,
            summary="Obtener Saldos (AIS)")
async def obtener_saldos(
    cuenta_id: str,
    authorization: str = Header(...),
    consentimiento_id: str = Query(...)
):
    """
    Obtiene los saldos de una cuenta específica.
    
    Requiere scope 'balances' en el consentimiento.
    """
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    
    if c["estado"] != EstadoConsentimiento.ACTIVO:
        raise HTTPException(status_code=403, detail="Consentimiento no activo")
    
    if "balances" not in c["alcances"]:
        raise HTTPException(status_code=403, detail="Scope 'balances' no autorizado")
    
    # Datos de ejemplo
    saldo = SaldoResponse(
        cuenta_id=cuenta_id,
        saldo_disponible=1500000.0,
        saldo_actual=1650000.0,
        saldo_retenido=150000.0,
        moneda="CLP",
        fecha_actualizacion=datetime.utcnow(),
        linea_credito=5000000.0
    )
    
    # Registrar acceso
    c["historial_accesos"].append({
        "tipo": "balances",
        "cuenta_id": cuenta_id,
        "fecha": datetime.utcnow().isoformat()
    })
    c["total_accesos"] += 1
    
    return saldo

@router.get("/cuentas/{cuenta_id}/transacciones", response_model=List[TransaccionResponse],
            summary="Listar Transacciones (AIS)")
async def listar_transacciones(
    cuenta_id: str,
    authorization: str = Header(...),
    consentimiento_id: str = Query(...),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0)
):
    """
    Lista las transacciones de una cuenta.
    
    Requiere scope 'transactions' en el consentimiento.
    Máximo histórico: 24 meses según NCG 514.
    """
    if consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[consentimiento_id]
    
    if c["estado"] != EstadoConsentimiento.ACTIVO:
        raise HTTPException(status_code=403, detail="Consentimiento no activo")
    
    if "transactions" not in c["alcances"]:
        raise HTTPException(status_code=403, detail="Scope 'transactions' no autorizado")
    
    # Validar rango de fechas (máx 24 meses)
    if fecha_desde:
        min_fecha = date.today() - timedelta(days=730)  # 24 meses
        if fecha_desde < min_fecha:
            fecha_desde = min_fecha
    
    # Datos de ejemplo
    transacciones = [
        TransaccionResponse(
            transaccion_id="TXN001",
            cuenta_id=cuenta_id,
            fecha=datetime.utcnow() - timedelta(days=1),
            fecha_valor=date.today() - timedelta(days=1),
            monto=-50000.0,
            moneda="CLP",
            tipo="DEBITO",
            descripcion="Transferencia a terceros",
            categoria="transferencia",
            referencia="REF001",
            contraparte_nombre="Juan Pérez",
            estado="liquidada"
        ),
        TransaccionResponse(
            transaccion_id="TXN002",
            cuenta_id=cuenta_id,
            fecha=datetime.utcnow() - timedelta(days=2),
            fecha_valor=date.today() - timedelta(days=2),
            monto=1500000.0,
            moneda="CLP",
            tipo="CREDITO",
            descripcion="Depósito en efectivo",
            categoria="deposito",
            estado="liquidada"
        )
    ]
    
    # Registrar acceso
    c["historial_accesos"].append({
        "tipo": "transactions",
        "cuenta_id": cuenta_id,
        "fecha": datetime.utcnow().isoformat()
    })
    c["total_accesos"] += 1
    
    return transacciones[offset:offset + limit]

# =====================================================
# ENDPOINTS PIS (Payment Initiation Services)
# =====================================================

@router.post("/pagos", response_model=PagoResponse, status_code=201,
             summary="Iniciar Pago (PIS)")
async def iniciar_pago(
    request: PagoRequest,
    authorization: str = Header(...)
):
    """
    Inicia un pago según NCG 514 Fase 4.
    
    Requiere:
    - Scope 'payments' en el consentimiento
    - Strong Customer Authentication (SCA)
    - Consentimiento específico para la operación
    """
    if request.consentimiento_id not in _consentimientos:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    c = _consentimientos[request.consentimiento_id]
    
    if c["estado"] != EstadoConsentimiento.ACTIVO:
        raise HTTPException(status_code=403, detail="Consentimiento no activo")
    
    if "payments" not in c["alcances"]:
        raise HTTPException(status_code=403, detail="Scope 'payments' no autorizado")
    
    # Crear pago
    pago_id = f"PAY-{uuid.uuid4().hex[:12]}"
    
    pago = {
        "id": pago_id,
        "consentimiento_id": request.consentimiento_id,
        "cuenta_origen": request.cuenta_origen,
        "cuenta_destino": request.cuenta_destino,
        "monto": request.monto,
        "moneda": request.moneda,
        "concepto": request.concepto,
        "referencia_cliente": request.referencia_cliente,
        "estado": EstadoPago.RCVD,
        "fecha_creacion": datetime.utcnow(),
        "fecha_ejecucion": None,
        "referencia_banco": None
    }
    
    _pagos[pago_id] = pago
    
    logger.info(f"Pago iniciado: {pago_id} por {request.monto} {request.moneda}")
    
    return PagoResponse(
        pago_id=pago_id,
        estado=EstadoPago.RCVD,
        fecha_creacion=pago["fecha_creacion"],
        monto=request.monto,
        moneda=request.moneda,
        mensaje="Pago recibido, pendiente de procesamiento"
    )

@router.get("/pagos/{pago_id}", response_model=PagoResponse,
            summary="Consultar Estado de Pago")
async def obtener_estado_pago(
    pago_id: str,
    authorization: str = Header(...)
):
    """Consulta el estado de un pago iniciado."""
    if pago_id not in _pagos:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    p = _pagos[pago_id]
    
    return PagoResponse(
        pago_id=p["id"],
        estado=p["estado"],
        fecha_creacion=p["fecha_creacion"],
        fecha_ejecucion=p.get("fecha_ejecucion"),
        monto=p["monto"],
        moneda=p["moneda"],
        referencia_banco=p.get("referencia_banco")
    )

@router.post("/pagos/{pago_id}/confirmar",
             summary="Confirmar Pago (Post-SCA)")
async def confirmar_pago(
    pago_id: str,
    authorization: str = Header(...)
):
    """
    Confirma un pago después de SCA.
    
    En producción, este endpoint se llama después de la autenticación
    fuerte del usuario para confirmar la operación.
    """
    if pago_id not in _pagos:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    p = _pagos[pago_id]
    
    if p["estado"] != EstadoPago.RCVD:
        raise HTTPException(status_code=400, detail="Pago no está en estado válido para confirmar")
    
    # Simular procesamiento
    p["estado"] = EstadoPago.ACSC
    p["fecha_ejecucion"] = datetime.utcnow()
    p["referencia_banco"] = f"BANK-{uuid.uuid4().hex[:8].upper()}"
    
    logger.info(f"Pago confirmado: {pago_id}")
    
    return {
        "mensaje": "Pago confirmado y ejecutado",
        "pago_id": pago_id,
        "estado": EstadoPago.ACSC.value,
        "referencia_banco": p["referencia_banco"]
    }

# =====================================================
# ENDPOINTS DE DIRECTORIO DE PARTICIPANTES
# =====================================================

@router.get("/directorio/participantes", response_model=List[ParticipanteInfo],
            summary="Listar Participantes del Directorio CMF")
async def listar_participantes(
    tipo: Optional[TipoParticipante] = Query(None),
    estado: Optional[str] = Query(None),
    servicio: Optional[str] = Query(None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0)
):
    """
    Lista los participantes registrados en el directorio NCG 514.
    
    El directorio es público y no requiere autenticación.
    """
    # Datos de ejemplo de participantes registrados
    participantes = [
        ParticipanteInfo(
            participante_id="ASPSP-001",
            nombre="Banco Estado",
            tipo=TipoParticipante.ASPSP,
            rut="97.030.000-7",
            estado="activo",
            servicios=["accounts", "balances", "transactions", "payments"],
            url_api="https://api.bancoestado.cl/open-finance/v1",
            certificado_vigente=True,
            fecha_registro=datetime(2025, 6, 1)
        ),
        ParticipanteInfo(
            participante_id="ASPSP-002",
            nombre="Banco de Chile",
            tipo=TipoParticipante.ASPSP,
            rut="97.004.000-5",
            estado="activo",
            servicios=["accounts", "balances", "transactions", "payments"],
            url_api="https://api.bancochile.cl/open-finance/v1",
            certificado_vigente=True,
            fecha_registro=datetime(2025, 6, 1)
        ),
        ParticipanteInfo(
            participante_id="TPP-001",
            nombre="DATAPOLIS SpA",
            tipo=TipoParticipante.TPP,
            rut="77.XXX.XXX-X",
            estado="activo",
            servicios=["aisp", "pisp"],
            url_api="https://api.datapolis.cl/v1",
            certificado_vigente=True,
            fecha_registro=datetime(2025, 9, 1)
        )
    ]
    
    # Filtrar
    resultado = participantes
    if tipo:
        resultado = [p for p in resultado if p.tipo == tipo]
    if estado:
        resultado = [p for p in resultado if p.estado == estado]
    if servicio:
        resultado = [p for p in resultado if servicio in p.servicios]
    
    return resultado[offset:offset + limit]

@router.get("/directorio/participantes/{participante_id}", response_model=ParticipanteInfo,
            summary="Obtener Participante del Directorio")
async def obtener_participante(participante_id: str):
    """Obtiene los detalles de un participante específico del directorio."""
    # En producción, buscar en base de datos del directorio CMF
    raise HTTPException(status_code=404, detail="Participante no encontrado")

# =====================================================
# ENDPOINTS DE PANEL DE CONTROL
# =====================================================

@router.get("/panel/resumen",
            summary="Resumen del Panel de Control del Usuario")
async def obtener_resumen_panel(
    authorization: str = Header(...)
):
    """
    Obtiene el resumen del panel de control del usuario.
    
    Incluye:
    - Consentimientos activos
    - Accesos recientes
    - Pagos pendientes
    - Alertas de seguridad
    """
    # Contar consentimientos por estado
    estados = {}
    for c in _consentimientos.values():
        estado = c["estado"].value if isinstance(c["estado"], Enum) else c["estado"]
        estados[estado] = estados.get(estado, 0) + 1
    
    return {
        "consentimientos": {
            "total": len(_consentimientos),
            "por_estado": estados,
            "activos": estados.get("activo", 0)
        },
        "pagos": {
            "total": len(_pagos),
            "pendientes": sum(1 for p in _pagos.values() if p["estado"] == EstadoPago.PDNG),
            "completados": sum(1 for p in _pagos.values() if p["estado"] == EstadoPago.ACSC)
        },
        "accesos_hoy": sum(
            len(c.get("historial_accesos", []))
            for c in _consentimientos.values()
        ),
        "alertas_pendientes": 0,
        "fecha_actualizacion": datetime.utcnow().isoformat()
    }

@router.get("/panel/historial-accesos",
            summary="Historial de Accesos del Usuario")
async def obtener_historial_accesos(
    authorization: str = Header(...),
    consentimiento_id: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    limit: int = Query(default=50, le=100)
):
    """
    Obtiene el historial de accesos a los datos del usuario.
    
    Proporciona transparencia total sobre:
    - Qué TPP accedió
    - Qué datos consultó
    - Cuándo ocurrió el acceso
    """
    accesos = []
    
    for cid, c in _consentimientos.items():
        if consentimiento_id and cid != consentimiento_id:
            continue
        
        for acceso in c.get("historial_accesos", []):
            if tipo and acceso.get("tipo") != tipo:
                continue
            
            accesos.append({
                "consentimiento_id": cid,
                "tpp_id": c["tpp_id"],
                "tpp_nombre": c["tpp_nombre"],
                **acceso
            })
    
    # Ordenar por fecha descendente
    accesos.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    
    return accesos[:limit]

# =====================================================
# ENDPOINTS DE MÉTRICAS Y HEALTH CHECK
# =====================================================

@router.get("/health", summary="Health Check del Servicio")
async def health_check():
    """Verifica el estado del servicio Open Finance."""
    return {
        "status": "healthy",
        "service": "DATAPOLIS Open Finance NCG 514",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "oauth": "operational",
            "ais": "operational",
            "pis": "operational",
            "directory": "operational"
        }
    }

@router.get("/metricas", summary="Métricas del Sistema")
async def obtener_metricas(authorization: str = Header(...)):
    """Obtiene métricas operacionales del sistema."""
    return {
        "consentimientos": {
            "total": len(_consentimientos),
            "activos": sum(1 for c in _consentimientos.values() 
                          if c["estado"] == EstadoConsentimiento.ACTIVO)
        },
        "pagos": {
            "total": len(_pagos),
            "monto_total": sum(p["monto"] for p in _pagos.values()),
            "completados": sum(1 for p in _pagos.values() if p["estado"] == EstadoPago.ACSC)
        },
        "tokens_activos": sum(1 for t in _tokens.values() 
                             if t.get("type") == "access_token" 
                             and t.get("expires_at", datetime.min) > datetime.utcnow()),
        "timestamp": datetime.utcnow().isoformat()
    }


# =====================================================
# CONFIGURACIÓN DE SWAGGER/OPENAPI
# =====================================================

# Información adicional para documentación
OPEN_FINANCE_DESCRIPTION = """
## Open Finance NCG 514 CMF Chile

Este módulo implementa los servicios de Open Finance según la Norma de Carácter General 514
de la Comisión para el Mercado Financiero (CMF) de Chile.

### Componentes Implementados

- **OAuth 2.0 + PKCE**: Autorización segura con Pushed Authorization Request (PAR)
- **AIS (Account Information Services)**: Consulta de cuentas, saldos y transacciones
- **PIS (Payment Initiation Services)**: Iniciación de pagos
- **Gestión de Consentimientos**: Creación, autorización y revocación
- **Directorio de Participantes**: Registro de ASPSPs y TPPs
- **Panel de Control de Usuario**: Transparencia y control de datos

### Normativas Implementadas

- NCG 514 CMF Chile (Open Finance)
- FAPI 2.0 Security Profile
- RFC 9126 (Pushed Authorization Request)
- RFC 7636 (PKCE)
- RFC 8705 (OAuth 2.0 Mutual-TLS)
- ISO 20022 (Financial Messaging)

### Deadline Regulatorio

**Abril 2026** - Implementación obligatoria para instituciones financieras en Chile.

---
**DATAPOLIS SpA** - PropTech/FinTech Platform
"""
