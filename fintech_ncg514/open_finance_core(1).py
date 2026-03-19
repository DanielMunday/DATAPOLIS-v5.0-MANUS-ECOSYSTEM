"""
================================================================================
MÓDULO M01: OPEN FINANCE CORE - SISTEMA DE FINANZAS ABIERTAS
DATAPOLIS SpA - Plataforma Integrada FinTech/PropTech
================================================================================

Implementación del Sistema de Finanzas Abiertas (SFA) según:
- Ley 21.521 (Ley Fintech Chile) - Título III
- NCG 514 CMF - Norma del Sistema de Finanzas Abiertas (Julio 2024)
- Estándares FAPI 2.0 (Financial-grade API)
- OAuth 2.0 / OpenID Connect con PKCE

Fecha límite cumplimiento: Abril 2026 (Fase 4)
Autor: DATAPOLIS SpA
Versión: 2.0.0
Fecha: Febrero 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from decimal import Decimal
import hashlib
import secrets
import uuid
import base64
import json


# ==============================================================================
# ENUMERACIONES NCG 514
# ==============================================================================

class TipoInstitucion(Enum):
    """Tipos de instituciones participantes en el SFA (Art. 2 NCG 514)."""
    BANCO = "banco"
    COOPERATIVA = "cooperativa"
    CAJA_COMPENSACION = "caja_compensacion"
    ASEGURADORA = "aseguradora"
    AFP = "afp"
    FINTECH = "fintech"
    PSBI = "proveedor_servicios_basados_informacion"  # Third Party Provider
    PSIP = "proveedor_servicios_iniciacion_pago"  # Payment Initiation Provider
    
class EstadoConsentimiento(Enum):
    """Estados del consentimiento del usuario (Art. 12-15 NCG 514)."""
    PENDIENTE = "pendiente"
    ACTIVO = "activo"
    REVOCADO = "revocado"
    EXPIRADO = "expirado"
    RECHAZADO = "rechazado"
    SUSPENDIDO = "suspendido"
    
class AlcanceConsentimiento(Enum):
    """Alcances permitidos para consentimiento (Anexo 2 NCG 514)."""
    # Account Information Services (AIS)
    SALDOS = "saldos"
    MOVIMIENTOS = "movimientos"
    PRODUCTOS = "productos"
    DATOS_CLIENTE = "datos_cliente"
    # Payment Initiation Services (PIS)
    INICIACION_PAGOS = "iniciacion_pagos"
    TRANSFERENCIAS = "transferencias"
    PAGOS_SERVICIOS = "pagos_servicios"
    # Productos Financieros
    CREDITOS = "creditos"
    INVERSIONES = "inversiones"
    SEGUROS = "seguros"
    AFP = "afp"

class TipoCuenta(Enum):
    """Tipos de cuenta bancaria."""
    CORRIENTE = "corriente"
    VISTA = "vista"
    AHORRO = "ahorro"
    RUT = "cuenta_rut"
    CREDITO = "linea_credito"
    
class MetodoAutenticacion(Enum):
    """Métodos de autenticación fuerte SCA (Art. 18 NCG 514)."""
    BIOMETRICO = "biometrico"
    PIN = "pin"
    OTP_SMS = "otp_sms"
    OTP_APP = "otp_app"
    PUSH = "push_notification"
    FIDO2 = "fido2_webauthn"
    CLAVE_UNICA = "clave_unica"  # ClaveÚnica Chile

class EstadoTransaccion(Enum):
    """Estados de transacción."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADA = "completada"
    RECHAZADA = "rechazada"
    CANCELADA = "cancelada"
    
class TipoPago(Enum):
    """Tipos de pago iniciado."""
    TRANSFERENCIA_MISMA_ENTIDAD = "transferencia_interna"
    TRANSFERENCIA_OTRA_ENTIDAD = "transferencia_tef"
    PAC = "pago_automatico_cuentas"
    PAT = "pago_automatico_tarjetas"
    TEF = "transferencia_electronica_fondos"


# ==============================================================================
# DATACLASSES - ESTRUCTURAS DE DATOS NCG 514
# ==============================================================================

@dataclass
class Institucion:
    """Representa una institución participante del SFA."""
    id: str
    nombre: str
    tipo: TipoInstitucion
    rut: str
    codigo_sbif: str = ""
    endpoints: Dict[str, str] = field(default_factory=dict)
    certificado_x509: Optional[str] = None
    estado_certificacion: str = "pendiente"
    fecha_registro: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.endpoints:
            self.endpoints = {
                "authorization": f"https://api.{self.id}.cl/oauth/authorize",
                "token": f"https://api.{self.id}.cl/oauth/token",
                "accounts": f"https://api.{self.id}.cl/v1/accounts",
                "balances": f"https://api.{self.id}.cl/v1/balances",
                "transactions": f"https://api.{self.id}.cl/v1/transactions",
                "payments": f"https://api.{self.id}.cl/v1/payments"
            }

@dataclass
class Consentimiento:
    """Consentimiento del usuario según NCG 514 Art. 12-15."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str = ""
    usuario_rut: str = ""
    tpp_id: str = ""  # ID del TPP solicitante
    institucion_id: str = ""  # ASPSP origen de datos
    alcances: List[AlcanceConsentimiento] = field(default_factory=list)
    estado: EstadoConsentimiento = EstadoConsentimiento.PENDIENTE
    fecha_creacion: datetime = field(default_factory=datetime.now)
    fecha_expiracion: Optional[datetime] = None
    fecha_revocacion: Optional[datetime] = None
    proposito: str = ""  # Descripción del uso
    frecuencia_acceso: int = 4  # Máximo accesos por día
    ip_origen: str = ""
    metodo_autenticacion: MetodoAutenticacion = MetodoAutenticacion.CLAVE_UNICA
    
    def __post_init__(self):
        # NCG 514: Duración máxima 365 días
        if self.fecha_expiracion is None:
            self.fecha_expiracion = self.fecha_creacion + timedelta(days=365)
        elif (self.fecha_expiracion - self.fecha_creacion).days > 365:
            self.fecha_expiracion = self.fecha_creacion + timedelta(days=365)
    
    @property
    def esta_vigente(self) -> bool:
        """Verifica si el consentimiento está vigente."""
        if self.estado != EstadoConsentimiento.ACTIVO:
            return False
        if self.fecha_expiracion and datetime.now() > self.fecha_expiracion:
            return False
        return True
    
    @property
    def dias_restantes(self) -> int:
        """Días restantes de vigencia."""
        if not self.fecha_expiracion:
            return 0
        delta = self.fecha_expiracion - datetime.now()
        return max(0, delta.days)

@dataclass
class CuentaBancaria:
    """Información de cuenta bancaria según estándar NCG 514."""
    id: str
    numero: str
    tipo: TipoCuenta
    moneda: str = "CLP"
    institucion_id: str = ""
    nombre_titular: str = ""
    rut_titular: str = ""
    saldo_disponible: Decimal = Decimal("0")
    saldo_contable: Decimal = Decimal("0")
    fecha_apertura: Optional[datetime] = None
    estado: str = "activa"
    iban: str = ""  # Identificador internacional
    bic: str = ""   # Bank Identifier Code

@dataclass
class Transaccion:
    """Transacción bancaria según ISO 20022."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cuenta_id: str = ""
    tipo: str = ""  # debito/credito
    monto: Decimal = Decimal("0")
    moneda: str = "CLP"
    fecha: datetime = field(default_factory=datetime.now)
    descripcion: str = ""
    categoria: str = ""
    comercio: str = ""
    referencia: str = ""
    saldo_posterior: Decimal = Decimal("0")
    estado: EstadoTransaccion = EstadoTransaccion.COMPLETADA

@dataclass
class SolicitudPago:
    """Solicitud de iniciación de pago (PIS) según NCG 514."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    consentimiento_id: str = ""
    cuenta_origen_id: str = ""
    cuenta_destino: str = ""
    banco_destino: str = ""
    rut_beneficiario: str = ""
    nombre_beneficiario: str = ""
    monto: Decimal = Decimal("0")
    moneda: str = "CLP"
    concepto: str = ""
    tipo_pago: TipoPago = TipoPago.TRANSFERENCIA_OTRA_ENTIDAD
    fecha_ejecucion: Optional[datetime] = None
    estado: EstadoTransaccion = EstadoTransaccion.PENDIENTE
    referencia_tpp: str = ""
    referencia_banco: str = ""
    fecha_creacion: datetime = field(default_factory=datetime.now)
    
@dataclass
class TokenOAuth:
    """Token OAuth 2.0 con PKCE."""
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: str = ""
    id_token: str = ""  # OpenID Connect
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def esta_expirado(self) -> bool:
        """Verifica si el token ha expirado."""
        expira = self.created_at + timedelta(seconds=self.expires_in)
        return datetime.now() > expira


# ==============================================================================
# GESTOR DE CONSENTIMIENTOS
# ==============================================================================

class GestorConsentimientos:
    """
    Gestiona el ciclo de vida de consentimientos según NCG 514.
    """
    
    def __init__(self):
        self._consentimientos: Dict[str, Consentimiento] = {}
        self._historial: List[Dict[str, Any]] = []
    
    def crear_consentimiento(
        self,
        usuario_rut: str,
        tpp_id: str,
        institucion_id: str,
        alcances: List[AlcanceConsentimiento],
        proposito: str,
        duracion_dias: int = 365,
        metodo_auth: MetodoAutenticacion = MetodoAutenticacion.CLAVE_UNICA
    ) -> Consentimiento:
        """Crea un nuevo consentimiento pendiente de autorización."""
        
        # Validar duración máxima (NCG 514: 365 días)
        duracion_dias = min(duracion_dias, 365)
        
        consentimiento = Consentimiento(
            usuario_rut=usuario_rut,
            tpp_id=tpp_id,
            institucion_id=institucion_id,
            alcances=alcances,
            proposito=proposito,
            fecha_expiracion=datetime.now() + timedelta(days=duracion_dias),
            metodo_autenticacion=metodo_auth
        )
        
        self._consentimientos[consentimiento.id] = consentimiento
        self._registrar_evento(consentimiento.id, "creado", "Consentimiento creado")
        
        return consentimiento
    
    def autorizar_consentimiento(
        self,
        consentimiento_id: str,
        ip_origen: str
    ) -> bool:
        """Autoriza un consentimiento pendiente tras autenticación SCA."""
        
        if consentimiento_id not in self._consentimientos:
            return False
        
        consentimiento = self._consentimientos[consentimiento_id]
        
        if consentimiento.estado != EstadoConsentimiento.PENDIENTE:
            return False
        
        consentimiento.estado = EstadoConsentimiento.ACTIVO
        consentimiento.ip_origen = ip_origen
        
        self._registrar_evento(consentimiento_id, "autorizado", f"IP: {ip_origen}")
        
        return True
    
    def revocar_consentimiento(
        self,
        consentimiento_id: str,
        motivo: str = ""
    ) -> bool:
        """Revoca un consentimiento activo (Art. 15 NCG 514)."""
        
        if consentimiento_id not in self._consentimientos:
            return False
        
        consentimiento = self._consentimientos[consentimiento_id]
        consentimiento.estado = EstadoConsentimiento.REVOCADO
        consentimiento.fecha_revocacion = datetime.now()
        
        self._registrar_evento(consentimiento_id, "revocado", motivo)
        
        return True
    
    def validar_consentimiento(
        self,
        consentimiento_id: str,
        alcance_requerido: AlcanceConsentimiento
    ) -> Tuple[bool, str]:
        """Valida si un consentimiento permite un alcance específico."""
        
        if consentimiento_id not in self._consentimientos:
            return False, "Consentimiento no encontrado"
        
        consentimiento = self._consentimientos[consentimiento_id]
        
        if not consentimiento.esta_vigente:
            return False, "Consentimiento no vigente"
        
        if alcance_requerido not in consentimiento.alcances:
            return False, f"Alcance {alcance_requerido.value} no autorizado"
        
        return True, "Válido"
    
    def obtener_consentimiento(self, consentimiento_id: str) -> Optional[Consentimiento]:
        """Obtiene un consentimiento por ID."""
        return self._consentimientos.get(consentimiento_id)
    
    def listar_consentimientos_usuario(
        self,
        usuario_rut: str,
        solo_activos: bool = False
    ) -> List[Consentimiento]:
        """Lista todos los consentimientos de un usuario."""
        consentimientos = [
            c for c in self._consentimientos.values()
            if c.usuario_rut == usuario_rut
        ]
        
        if solo_activos:
            consentimientos = [c for c in consentimientos if c.esta_vigente]
        
        return consentimientos
    
    def _registrar_evento(self, consentimiento_id: str, accion: str, detalle: str):
        """Registra evento en historial de auditoría."""
        self._historial.append({
            "timestamp": datetime.now().isoformat(),
            "consentimiento_id": consentimiento_id,
            "accion": accion,
            "detalle": detalle
        })


# ==============================================================================
# PROVEEDOR AIS (Account Information Services)
# ==============================================================================

class ProveedorAIS:
    """
    Proveedor de Servicios de Información de Cuentas según NCG 514.
    Permite consultar saldos, movimientos y productos del cliente.
    """
    
    def __init__(self, gestor_consentimientos: GestorConsentimientos):
        self.gestor = gestor_consentimientos
        self._cache_cuentas: Dict[str, List[CuentaBancaria]] = {}
        self._logs_acceso: List[Dict[str, Any]] = []
    
    def obtener_cuentas(
        self,
        consentimiento_id: str,
        usuario_rut: str
    ) -> Tuple[bool, List[CuentaBancaria], str]:
        """Obtiene las cuentas del usuario con consentimiento válido."""
        
        valido, mensaje = self.gestor.validar_consentimiento(
            consentimiento_id, 
            AlcanceConsentimiento.PRODUCTOS
        )
        
        if not valido:
            return False, [], mensaje
        
        # Simulación de consulta a institución
        cuentas = self._consultar_cuentas_institucion(usuario_rut)
        
        self._registrar_acceso(consentimiento_id, "obtener_cuentas", len(cuentas))
        
        return True, cuentas, "OK"
    
    def obtener_saldo(
        self,
        consentimiento_id: str,
        cuenta_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Obtiene el saldo de una cuenta específica."""
        
        valido, mensaje = self.gestor.validar_consentimiento(
            consentimiento_id,
            AlcanceConsentimiento.SALDOS
        )
        
        if not valido:
            return False, None, mensaje
        
        # Simulación
        saldo = {
            "cuenta_id": cuenta_id,
            "saldo_disponible": Decimal("1500000"),
            "saldo_contable": Decimal("1520000"),
            "moneda": "CLP",
            "fecha_consulta": datetime.now().isoformat()
        }
        
        self._registrar_acceso(consentimiento_id, "obtener_saldo", 1)
        
        return True, saldo, "OK"
    
    def obtener_movimientos(
        self,
        consentimiento_id: str,
        cuenta_id: str,
        fecha_desde: datetime,
        fecha_hasta: datetime,
        pagina: int = 1,
        por_pagina: int = 50
    ) -> Tuple[bool, List[Transaccion], str]:
        """Obtiene los movimientos de una cuenta en un período."""
        
        valido, mensaje = self.gestor.validar_consentimiento(
            consentimiento_id,
            AlcanceConsentimiento.MOVIMIENTOS
        )
        
        if not valido:
            return False, [], mensaje
        
        # NCG 514: Máximo 24 meses de histórico
        max_antiguedad = datetime.now() - timedelta(days=730)
        if fecha_desde < max_antiguedad:
            fecha_desde = max_antiguedad
        
        # Simulación
        movimientos = self._consultar_movimientos_institucion(
            cuenta_id, fecha_desde, fecha_hasta
        )
        
        # Paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        movimientos_paginados = movimientos[inicio:fin]
        
        self._registrar_acceso(
            consentimiento_id, 
            "obtener_movimientos", 
            len(movimientos_paginados)
        )
        
        return True, movimientos_paginados, "OK"
    
    def _consultar_cuentas_institucion(self, usuario_rut: str) -> List[CuentaBancaria]:
        """Simula consulta a institución financiera."""
        return [
            CuentaBancaria(
                id=str(uuid.uuid4()),
                numero="****1234",
                tipo=TipoCuenta.CORRIENTE,
                rut_titular=usuario_rut,
                saldo_disponible=Decimal("1500000"),
                saldo_contable=Decimal("1520000")
            ),
            CuentaBancaria(
                id=str(uuid.uuid4()),
                numero="****5678",
                tipo=TipoCuenta.VISTA,
                rut_titular=usuario_rut,
                saldo_disponible=Decimal("350000"),
                saldo_contable=Decimal("350000")
            )
        ]
    
    def _consultar_movimientos_institucion(
        self,
        cuenta_id: str,
        fecha_desde: datetime,
        fecha_hasta: datetime
    ) -> List[Transaccion]:
        """Simula consulta de movimientos."""
        return [
            Transaccion(
                cuenta_id=cuenta_id,
                tipo="credito",
                monto=Decimal("2500000"),
                descripcion="Depósito nómina",
                categoria="ingreso_nomina",
                fecha=fecha_desde + timedelta(days=1)
            ),
            Transaccion(
                cuenta_id=cuenta_id,
                tipo="debito",
                monto=Decimal("150000"),
                descripcion="Pago gastos comunes",
                categoria="vivienda",
                comercio="Administración Edificio",
                fecha=fecha_desde + timedelta(days=5)
            )
        ]
    
    def _registrar_acceso(self, consentimiento_id: str, operacion: str, registros: int):
        """Registra acceso para auditoría."""
        self._logs_acceso.append({
            "timestamp": datetime.now().isoformat(),
            "consentimiento_id": consentimiento_id,
            "operacion": operacion,
            "registros": registros
        })


# ==============================================================================
# PROVEEDOR PIS (Payment Initiation Services)
# ==============================================================================

class ProveedorPIS:
    """
    Proveedor de Servicios de Iniciación de Pagos según NCG 514.
    Permite iniciar transferencias y pagos en nombre del usuario.
    """
    
    def __init__(self, gestor_consentimientos: GestorConsentimientos):
        self.gestor = gestor_consentimientos
        self._solicitudes: Dict[str, SolicitudPago] = {}
        self._logs_pagos: List[Dict[str, Any]] = []
    
    def crear_solicitud_pago(
        self,
        consentimiento_id: str,
        cuenta_origen_id: str,
        cuenta_destino: str,
        banco_destino: str,
        rut_beneficiario: str,
        nombre_beneficiario: str,
        monto: Decimal,
        concepto: str,
        tipo_pago: TipoPago = TipoPago.TRANSFERENCIA_OTRA_ENTIDAD
    ) -> Tuple[bool, Optional[SolicitudPago], str]:
        """Crea una solicitud de pago pendiente de confirmación."""
        
        valido, mensaje = self.gestor.validar_consentimiento(
            consentimiento_id,
            AlcanceConsentimiento.INICIACION_PAGOS
        )
        
        if not valido:
            return False, None, mensaje
        
        # Validar monto (NCG 514: límites por tipo de pago)
        if monto <= 0:
            return False, None, "Monto debe ser positivo"
        
        # Validar RUT beneficiario
        if not self._validar_rut(rut_beneficiario):
            return False, None, "RUT beneficiario inválido"
        
        solicitud = SolicitudPago(
            consentimiento_id=consentimiento_id,
            cuenta_origen_id=cuenta_origen_id,
            cuenta_destino=cuenta_destino,
            banco_destino=banco_destino,
            rut_beneficiario=rut_beneficiario,
            nombre_beneficiario=nombre_beneficiario,
            monto=monto,
            concepto=concepto,
            tipo_pago=tipo_pago,
            referencia_tpp=str(uuid.uuid4())[:8]
        )
        
        self._solicitudes[solicitud.id] = solicitud
        
        self._registrar_pago(solicitud.id, "creada", f"Monto: {monto}")
        
        return True, solicitud, "Solicitud creada. Requiere confirmación SCA."
    
    def confirmar_pago(
        self,
        solicitud_id: str,
        codigo_sca: str
    ) -> Tuple[bool, str]:
        """Confirma un pago con autenticación fuerte (SCA)."""
        
        if solicitud_id not in self._solicitudes:
            return False, "Solicitud no encontrada"
        
        solicitud = self._solicitudes[solicitud_id]
        
        if solicitud.estado != EstadoTransaccion.PENDIENTE:
            return False, f"Solicitud en estado {solicitud.estado.value}"
        
        # Validar código SCA (simulado)
        if not self._validar_sca(codigo_sca):
            return False, "Código SCA inválido"
        
        # Procesar pago
        solicitud.estado = EstadoTransaccion.PROCESANDO
        
        # Simular envío a banco
        resultado = self._enviar_a_banco(solicitud)
        
        if resultado["exito"]:
            solicitud.estado = EstadoTransaccion.COMPLETADA
            solicitud.referencia_banco = resultado["referencia"]
            self._registrar_pago(solicitud_id, "completada", resultado["referencia"])
            return True, f"Pago completado. Ref: {resultado['referencia']}"
        else:
            solicitud.estado = EstadoTransaccion.RECHAZADA
            self._registrar_pago(solicitud_id, "rechazada", resultado["motivo"])
            return False, resultado["motivo"]
    
    def cancelar_pago(self, solicitud_id: str) -> Tuple[bool, str]:
        """Cancela una solicitud de pago pendiente."""
        
        if solicitud_id not in self._solicitudes:
            return False, "Solicitud no encontrada"
        
        solicitud = self._solicitudes[solicitud_id]
        
        if solicitud.estado != EstadoTransaccion.PENDIENTE:
            return False, "Solo se pueden cancelar pagos pendientes"
        
        solicitud.estado = EstadoTransaccion.CANCELADA
        self._registrar_pago(solicitud_id, "cancelada", "Por usuario")
        
        return True, "Pago cancelado"
    
    def obtener_estado_pago(self, solicitud_id: str) -> Optional[Dict[str, Any]]:
        """Consulta el estado de una solicitud de pago."""
        
        if solicitud_id not in self._solicitudes:
            return None
        
        solicitud = self._solicitudes[solicitud_id]
        
        return {
            "id": solicitud.id,
            "estado": solicitud.estado.value,
            "monto": float(solicitud.monto),
            "beneficiario": solicitud.nombre_beneficiario,
            "fecha_creacion": solicitud.fecha_creacion.isoformat(),
            "referencia_tpp": solicitud.referencia_tpp,
            "referencia_banco": solicitud.referencia_banco
        }
    
    def _validar_rut(self, rut: str) -> bool:
        """Valida formato de RUT chileno."""
        rut_limpio = rut.replace(".", "").replace("-", "").upper()
        if len(rut_limpio) < 8:
            return False
        return True
    
    def _validar_sca(self, codigo: str) -> bool:
        """Valida código SCA (simulado)."""
        return len(codigo) >= 6
    
    def _enviar_a_banco(self, solicitud: SolicitudPago) -> Dict[str, Any]:
        """Simula envío de instrucción de pago al banco."""
        return {
            "exito": True,
            "referencia": f"TEF{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
    
    def _registrar_pago(self, solicitud_id: str, estado: str, detalle: str):
        """Registra evento de pago."""
        self._logs_pagos.append({
            "timestamp": datetime.now().isoformat(),
            "solicitud_id": solicitud_id,
            "estado": estado,
            "detalle": detalle
        })


# ==============================================================================
# AUTENTICADOR OAUTH 2.0 CON PKCE
# ==============================================================================

class AutenticadorOAuth:
    """
    Implementación de OAuth 2.0 con PKCE según FAPI 2.0.
    Requerido por NCG 514 Art. 18.
    """
    
    def __init__(self):
        self._tokens: Dict[str, TokenOAuth] = {}
        self._authorization_codes: Dict[str, Dict[str, Any]] = {}
        self._code_verifiers: Dict[str, str] = {}
    
    def generar_code_verifier(self) -> str:
        """Genera un code_verifier para PKCE."""
        return secrets.token_urlsafe(64)
    
    def generar_code_challenge(self, code_verifier: str) -> str:
        """Genera el code_challenge a partir del verifier (SHA256)."""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")
    
    def iniciar_autorizacion(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> str:
        """Inicia el flujo de autorización. Retorna URL de autorización."""
        
        # Generar código de autorización temporal
        auth_code = secrets.token_urlsafe(32)
        
        self._authorization_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=10)
        }
        
        # Construir URL de autorización (simulado)
        auth_url = (
            f"https://auth.datapolis.cl/authorize?"
            f"response_type=code&"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scope}&"
            f"state={state}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method={code_challenge_method}"
        )
        
        return auth_url
    
    def intercambiar_codigo(
        self,
        authorization_code: str,
        code_verifier: str,
        client_id: str
    ) -> Tuple[bool, Optional[TokenOAuth], str]:
        """Intercambia código de autorización por tokens."""
        
        if authorization_code not in self._authorization_codes:
            return False, None, "Código de autorización inválido"
        
        auth_data = self._authorization_codes[authorization_code]
        
        # Verificar expiración
        if datetime.now() > auth_data["expires_at"]:
            del self._authorization_codes[authorization_code]
            return False, None, "Código expirado"
        
        # Verificar client_id
        if auth_data["client_id"] != client_id:
            return False, None, "Client ID no coincide"
        
        # Verificar PKCE
        expected_challenge = self.generar_code_challenge(code_verifier)
        if expected_challenge != auth_data["code_challenge"]:
            return False, None, "PKCE verification failed"
        
        # Generar tokens
        token = TokenOAuth(
            access_token=secrets.token_urlsafe(64),
            refresh_token=secrets.token_urlsafe(64),
            scope=auth_data["scope"],
            expires_in=3600,
            id_token=self._generar_id_token(client_id)
        )
        
        self._tokens[token.access_token] = token
        
        # Limpiar código usado
        del self._authorization_codes[authorization_code]
        
        return True, token, "OK"
    
    def renovar_token(self, refresh_token: str) -> Tuple[bool, Optional[TokenOAuth], str]:
        """Renueva un access token usando refresh token."""
        
        # Buscar token con este refresh
        token_actual = None
        for t in self._tokens.values():
            if t.refresh_token == refresh_token:
                token_actual = t
                break
        
        if not token_actual:
            return False, None, "Refresh token inválido"
        
        # Generar nuevo access token
        nuevo_token = TokenOAuth(
            access_token=secrets.token_urlsafe(64),
            refresh_token=refresh_token,  # Mantener refresh
            scope=token_actual.scope,
            expires_in=3600
        )
        
        # Reemplazar token antiguo
        del self._tokens[token_actual.access_token]
        self._tokens[nuevo_token.access_token] = nuevo_token
        
        return True, nuevo_token, "OK"
    
    def validar_token(self, access_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Valida un access token y retorna claims."""
        
        if access_token not in self._tokens:
            return False, None
        
        token = self._tokens[access_token]
        
        if token.esta_expirado:
            return False, None
        
        return True, {
            "scope": token.scope,
            "expires_in": token.expires_in - int((datetime.now() - token.created_at).total_seconds())
        }
    
    def revocar_token(self, access_token: str) -> bool:
        """Revoca un access token."""
        if access_token in self._tokens:
            del self._tokens[access_token]
            return True
        return False
    
    def _generar_id_token(self, client_id: str) -> str:
        """Genera un ID token JWT (simulado)."""
        payload = {
            "iss": "https://auth.datapolis.cl",
            "sub": str(uuid.uuid4()),
            "aud": client_id,
            "iat": int(datetime.now().timestamp()),
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
        }
        # En producción, firmar con RSA/ECDSA
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


# ==============================================================================
# AGREGADOR FINANCIERO
# ==============================================================================

class AgregadorFinanciero:
    """
    Agrega información de múltiples instituciones financieras.
    Permite vista consolidada de productos del cliente.
    """
    
    def __init__(self):
        self.instituciones: Dict[str, Institucion] = {}
        self.proveedores_ais: Dict[str, ProveedorAIS] = {}
    
    def registrar_institucion(self, institucion: Institucion):
        """Registra una institución en el directorio."""
        self.instituciones[institucion.id] = institucion
    
    def obtener_vision_consolidada(
        self,
        usuario_rut: str,
        consentimientos: List[str]
    ) -> Dict[str, Any]:
        """Obtiene visión consolidada de todas las cuentas del usuario."""
        
        resultado = {
            "usuario_rut": usuario_rut,
            "fecha_consulta": datetime.now().isoformat(),
            "instituciones": [],
            "resumen": {
                "total_saldo_disponible": Decimal("0"),
                "total_cuentas": 0,
                "monedas": []
            }
        }
        
        for consentimiento_id in consentimientos:
            # Aquí se consultaría cada institución
            pass
        
        return resultado
    
    def calcular_patrimonio_neto(
        self,
        cuentas: List[CuentaBancaria],
        creditos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calcula el patrimonio neto del usuario."""
        
        total_activos = sum(c.saldo_disponible for c in cuentas)
        total_pasivos = sum(Decimal(str(c.get("saldo_pendiente", 0))) for c in creditos)
        
        return {
            "activos": float(total_activos),
            "pasivos": float(total_pasivos),
            "patrimonio_neto": float(total_activos - total_pasivos),
            "fecha_calculo": datetime.now().isoformat()
        }


# ==============================================================================
# SISTEMA OPEN FINANCE INTEGRADO
# ==============================================================================

class SistemaOpenFinance:
    """
    Sistema integrado de Open Finance según NCG 514.
    Coordina todos los componentes del SFA.
    """
    
    def __init__(self):
        self.gestor_consentimientos = GestorConsentimientos()
        self.proveedor_ais = ProveedorAIS(self.gestor_consentimientos)
        self.proveedor_pis = ProveedorPIS(self.gestor_consentimientos)
        self.autenticador = AutenticadorOAuth()
        self.agregador = AgregadorFinanciero()
        
        self._metricas = {
            "consentimientos_creados": 0,
            "consultas_ais": 0,
            "pagos_iniciados": 0,
            "tokens_emitidos": 0
        }
    
    def registrar_tpp(self, tpp_data: Dict[str, Any]) -> str:
        """Registra un TPP en el directorio."""
        institucion = Institucion(
            id=str(uuid.uuid4()),
            nombre=tpp_data.get("nombre", ""),
            tipo=TipoInstitucion[tpp_data.get("tipo", "PSBI")],
            rut=tpp_data.get("rut", ""),
            codigo_sbif=tpp_data.get("codigo_sbif", "")
        )
        self.agregador.registrar_institucion(institucion)
        return institucion.id
    
    def flujo_consentimiento_completo(
        self,
        usuario_rut: str,
        tpp_id: str,
        institucion_id: str,
        alcances: List[str],
        proposito: str
    ) -> Dict[str, Any]:
        """Ejecuta flujo completo de obtención de consentimiento."""
        
        # Convertir alcances
        alcances_enum = [AlcanceConsentimiento[a.upper()] for a in alcances]
        
        # Crear consentimiento
        consentimiento = self.gestor_consentimientos.crear_consentimiento(
            usuario_rut=usuario_rut,
            tpp_id=tpp_id,
            institucion_id=institucion_id,
            alcances=alcances_enum,
            proposito=proposito
        )
        
        self._metricas["consentimientos_creados"] += 1
        
        # Generar URL de autorización con PKCE
        code_verifier = self.autenticador.generar_code_verifier()
        code_challenge = self.autenticador.generar_code_challenge(code_verifier)
        
        auth_url = self.autenticador.iniciar_autorizacion(
            client_id=tpp_id,
            redirect_uri=f"https://{tpp_id}.cl/callback",
            scope=" ".join([a.value for a in alcances_enum]),
            state=consentimiento.id,
            code_challenge=code_challenge
        )
        
        return {
            "consentimiento_id": consentimiento.id,
            "estado": consentimiento.estado.value,
            "auth_url": auth_url,
            "code_verifier": code_verifier,  # TPP debe guardar esto
            "expira_en_dias": consentimiento.dias_restantes
        }
    
    def consultar_informacion_financiera(
        self,
        consentimiento_id: str,
        usuario_rut: str,
        tipo_consulta: str
    ) -> Dict[str, Any]:
        """Realiza consulta de información financiera."""
        
        self._metricas["consultas_ais"] += 1
        
        if tipo_consulta == "cuentas":
            exito, cuentas, msg = self.proveedor_ais.obtener_cuentas(
                consentimiento_id, usuario_rut
            )
            if exito:
                return {
                    "exito": True,
                    "cuentas": [
                        {
                            "id": c.id,
                            "numero": c.numero,
                            "tipo": c.tipo.value,
                            "saldo": float(c.saldo_disponible)
                        }
                        for c in cuentas
                    ]
                }
            return {"exito": False, "error": msg}
        
        elif tipo_consulta == "saldos":
            # Implementar consulta de saldos
            pass
        
        return {"exito": False, "error": "Tipo de consulta no soportado"}
    
    def iniciar_pago(
        self,
        consentimiento_id: str,
        datos_pago: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inicia un pago."""
        
        self._metricas["pagos_iniciados"] += 1
        
        exito, solicitud, msg = self.proveedor_pis.crear_solicitud_pago(
            consentimiento_id=consentimiento_id,
            cuenta_origen_id=datos_pago.get("cuenta_origen", ""),
            cuenta_destino=datos_pago.get("cuenta_destino", ""),
            banco_destino=datos_pago.get("banco_destino", ""),
            rut_beneficiario=datos_pago.get("rut_beneficiario", ""),
            nombre_beneficiario=datos_pago.get("nombre_beneficiario", ""),
            monto=Decimal(str(datos_pago.get("monto", 0))),
            concepto=datos_pago.get("concepto", "")
        )
        
        if exito and solicitud:
            return {
                "exito": True,
                "solicitud_id": solicitud.id,
                "referencia": solicitud.referencia_tpp,
                "mensaje": msg
            }
        
        return {"exito": False, "error": msg}
    
    def obtener_metricas(self) -> Dict[str, Any]:
        """Retorna métricas del sistema."""
        return {
            **self._metricas,
            "consentimientos_activos": len([
                c for c in self.gestor_consentimientos._consentimientos.values()
                if c.esta_vigente
            ]),
            "timestamp": datetime.now().isoformat()
        }


# ==============================================================================
# DEMO Y PRUEBAS
# ==============================================================================

def demo_open_finance():
    """Demuestra el uso del sistema Open Finance NCG 514."""
    
    print("=" * 80)
    print("DEMO: SISTEMA OPEN FINANCE NCG 514 - DATAPOLIS")
    print("=" * 80)
    
    # 1. Crear sistema
    sistema = SistemaOpenFinance()
    print("\n✓ Sistema Open Finance inicializado")
    
    # 2. Registrar TPP
    tpp_id = sistema.registrar_tpp({
        "nombre": "DATAPOLIS SpA",
        "tipo": "PSBI",
        "rut": "77.123.456-7"
    })
    print(f"✓ TPP registrado: {tpp_id}")
    
    # 3. Flujo de consentimiento
    resultado = sistema.flujo_consentimiento_completo(
        usuario_rut="12.345.678-9",
        tpp_id=tpp_id,
        institucion_id="banco_estado",
        alcances=["saldos", "movimientos", "productos"],
        proposito="Análisis de gastos comunes y morosidad"
    )
    print(f"✓ Consentimiento creado: {resultado['consentimiento_id']}")
    print(f"  Estado: {resultado['estado']}")
    print(f"  Expira en: {resultado['expira_en_dias']} días")
    
    # 4. Simular autorización
    sistema.gestor_consentimientos.autorizar_consentimiento(
        resultado['consentimiento_id'],
        ip_origen="192.168.1.100"
    )
    print("✓ Consentimiento autorizado")
    
    # 5. Consultar cuentas
    info = sistema.consultar_informacion_financiera(
        consentimiento_id=resultado['consentimiento_id'],
        usuario_rut="12.345.678-9",
        tipo_consulta="cuentas"
    )
    if info["exito"]:
        print(f"✓ Cuentas obtenidas: {len(info['cuentas'])}")
        for cuenta in info['cuentas']:
            print(f"  - {cuenta['tipo']}: ${cuenta['saldo']:,.0f}")
    
    # 6. Métricas
    metricas = sistema.obtener_metricas()
    print(f"\nMétricas del sistema:")
    print(f"  Consentimientos creados: {metricas['consentimientos_creados']}")
    print(f"  Consultas AIS: {metricas['consultas_ais']}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETADA - SISTEMA NCG 514 OPERATIVO")
    print("=" * 80)
    
    return sistema


if __name__ == "__main__":
    demo_open_finance()
