"""
DATAPOLIS v3.0 - NCG 514 SISTEMA INTEGRADO
==========================================
Orquestador principal del Sistema de Finanzas Abiertas (SFA)
Integra todos los módulos NCG 514 en una solución unificada

Autor: DATAPOLIS SpA
Versión: 1.0.0
Fecha: 2026-02-01
Normativa: NCG 514 CMF Chile - Deadline Abril 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union, Callable
from enum import Enum
import hashlib
import secrets
import json
import asyncio
from abc import ABC, abstractmethod

# Importar módulos internos (en producción serían imports reales)
# from .open_finance_core import *
# from .ncg514_fapi_security import *
# from .ncg514_directorio_participantes import *
# from .ncg514_iso20022_messaging import *
# from .ncg514_panel_control_usuario import *


# ============================================================================
# ENUMERACIONES DEL SISTEMA
# ============================================================================

class EstadoSistema(Enum):
    """Estados del sistema SFA"""
    INICIANDO = "iniciando"
    OPERATIVO = "operativo"
    DEGRADADO = "degradado"
    MANTENIMIENTO = "mantenimiento"
    ERROR = "error"


class TipoEvento(Enum):
    """Tipos de eventos del sistema"""
    CONSENTIMIENTO = "consentimiento"
    ACCESO_DATOS = "acceso_datos"
    PAGO = "pago"
    SEGURIDAD = "seguridad"
    SISTEMA = "sistema"
    AUDITORIA = "auditoria"


class NivelLog(Enum):
    """Niveles de log"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FaseSFA(Enum):
    """Fases de implementación NCG 514"""
    FASE_1 = "fase_1"  # Datos básicos - Octubre 2025
    FASE_2 = "fase_2"  # Productos crediticios - Enero 2026
    FASE_3 = "fase_3"  # Inversiones y seguros - Marzo 2026
    FASE_4 = "fase_4"  # Iniciación de pagos - Abril 2026


# ============================================================================
# DATACLASSES DE CONFIGURACIÓN
# ============================================================================

@dataclass
class ConfiguracionSFA:
    """Configuración del Sistema de Finanzas Abiertas"""
    # Identificación
    participante_id: str
    nombre_participante: str
    tipo_participante: str  # ASPSP, AISP, PISP, etc.
    
    # Endpoints
    base_url: str
    authorization_endpoint: str
    token_endpoint: str
    par_endpoint: str
    jwks_endpoint: str
    
    # Certificados
    qwac_cert_path: str
    qwac_key_path: str
    qseal_cert_path: str
    qseal_key_path: str
    
    # Seguridad
    fapi_profile: str = "FAPI2_ADVANCED"
    mtls_enabled: bool = True
    dpop_enabled: bool = True
    token_lifetime_seconds: int = 3600
    refresh_token_lifetime_days: int = 30
    
    # Consentimientos
    max_consent_duration_days: int = 365
    require_sca: bool = True
    allowed_scopes: List[str] = field(default_factory=lambda: [
        "openid", "accounts", "transactions", "balances", "payments"
    ])
    
    # Límites operacionales
    max_requests_per_minute: int = 100
    max_transactions_per_page: int = 50
    transaction_history_months: int = 24
    
    # Fase actual
    fase_actual: FaseSFA = FaseSFA.FASE_4
    
    # Directorio
    directorio_url: str = "https://directorio.sfa.cmf.cl"


@dataclass
class MetricasSistema:
    """Métricas de operación del sistema"""
    timestamp: datetime
    estado: EstadoSistema
    
    # Consentimientos
    consentimientos_activos: int = 0
    consentimientos_creados_hoy: int = 0
    consentimientos_revocados_hoy: int = 0
    
    # Accesos
    accesos_ais_hoy: int = 0
    accesos_ais_exitosos: int = 0
    accesos_ais_fallidos: int = 0
    
    # Pagos
    pagos_pis_hoy: int = 0
    pagos_completados: int = 0
    pagos_fallidos: int = 0
    monto_total_pagos: float = 0.0
    
    # Rendimiento
    latencia_promedio_ms: float = 0.0
    disponibilidad_porcentaje: float = 100.0
    errores_ultimo_hora: int = 0
    
    # Seguridad
    intentos_autenticacion_fallidos: int = 0
    alertas_seguridad: int = 0


@dataclass
class EventoSistema:
    """Evento del sistema para auditoría"""
    id: str
    timestamp: datetime
    tipo: TipoEvento
    nivel: NivelLog
    origen: str
    descripcion: str
    usuario_id: Optional[str]
    participante_id: Optional[str]
    datos: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None


# ============================================================================
# SISTEMA INTEGRADO NCG 514
# ============================================================================

class SistemaIntegradoSFA:
    """
    Sistema Integrado de Finanzas Abiertas NCG 514.
    
    Orquesta todos los componentes:
    - Gestión de consentimientos
    - Seguridad FAPI 2.0
    - Directorio de participantes
    - Mensajería ISO 20022
    - Panel de control de usuarios
    - Auditoría y cumplimiento
    """
    
    def __init__(self, config: ConfiguracionSFA):
        self.config = config
        self.estado = EstadoSistema.INICIANDO
        
        # Componentes del sistema
        self._consentimientos: Dict[str, Dict] = {}
        self._tokens: Dict[str, Dict] = {}
        self._accesos_log: List[Dict] = []
        self._pagos: Dict[str, Dict] = {}
        self._eventos: List[EventoSistema] = []
        
        # Métricas
        self._metricas_actuales = MetricasSistema(
            timestamp=datetime.now(),
            estado=EstadoSistema.INICIANDO
        )
        
        # Rate limiting
        self._request_counts: Dict[str, List[datetime]] = {}
        
        # Callbacks
        self._event_handlers: Dict[TipoEvento, List[Callable]] = {}
        
        # Inicializar
        self._inicializar_sistema()
    
    def _inicializar_sistema(self):
        """Inicializa el sistema y sus componentes"""
        self._registrar_evento(
            tipo=TipoEvento.SISTEMA,
            nivel=NivelLog.INFO,
            origen="SistemaIntegradoSFA",
            descripcion="Iniciando Sistema de Finanzas Abiertas NCG 514"
        )
        
        # Verificar configuración
        errores = self._validar_configuracion()
        if errores:
            self.estado = EstadoSistema.ERROR
            self._registrar_evento(
                tipo=TipoEvento.SISTEMA,
                nivel=NivelLog.ERROR,
                origen="SistemaIntegradoSFA",
                descripcion=f"Errores de configuración: {', '.join(errores)}"
            )
            return
        
        self.estado = EstadoSistema.OPERATIVO
        self._metricas_actuales.estado = EstadoSistema.OPERATIVO
        
        self._registrar_evento(
            tipo=TipoEvento.SISTEMA,
            nivel=NivelLog.INFO,
            origen="SistemaIntegradoSFA",
            descripcion=f"Sistema operativo - Fase: {self.config.fase_actual.value}"
        )
    
    def _validar_configuracion(self) -> List[str]:
        """Valida la configuración del sistema"""
        errores = []
        
        if not self.config.participante_id:
            errores.append("Falta participante_id")
        
        if not self.config.base_url.startswith("https://"):
            errores.append("base_url debe usar HTTPS")
        
        if self.config.max_consent_duration_days > 365:
            errores.append("Duración máxima de consentimiento es 365 días (NCG 514)")
        
        if self.config.fapi_profile not in ["FAPI2_BASELINE", "FAPI2_ADVANCED"]:
            errores.append("fapi_profile debe ser FAPI2_BASELINE o FAPI2_ADVANCED")
        
        return errores
    
    # =========================================================================
    # FLUJO DE AUTORIZACIÓN Y CONSENTIMIENTO
    # =========================================================================
    
    async def iniciar_flujo_autorizacion(
        self,
        cliente_id: str,
        redirect_uri: str,
        scope: List[str],
        state: str,
        nonce: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> Dict[str, Any]:
        """
        Inicia el flujo de autorización OAuth 2.0 + PKCE.
        Según FAPI 2.0 Advanced Profile y NCG 514.
        """
        # Verificar rate limiting
        if not self._verificar_rate_limit(cliente_id):
            return {
                "error": "rate_limit_exceeded",
                "error_description": "Demasiadas solicitudes. Intente más tarde."
            }
        
        # Validar scopes
        scopes_invalidos = [s for s in scope if s not in self.config.allowed_scopes]
        if scopes_invalidos:
            return {
                "error": "invalid_scope",
                "error_description": f"Scopes no permitidos: {', '.join(scopes_invalidos)}"
            }
        
        # Validar PKCE
        if code_challenge_method != "S256":
            return {
                "error": "invalid_request",
                "error_description": "Solo se acepta S256 para code_challenge_method"
            }
        
        # Crear PAR (Pushed Authorization Request)
        request_uri = f"urn:ietf:params:oauth:request_uri:{secrets.token_urlsafe(32)}"
        
        par_data = {
            "request_uri": request_uri,
            "client_id": cliente_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=60)  # PAR válido 60 segundos
        }
        
        # Almacenar PAR
        self._tokens[request_uri] = par_data
        
        self._registrar_evento(
            tipo=TipoEvento.CONSENTIMIENTO,
            nivel=NivelLog.INFO,
            origen="flujo_autorizacion",
            descripcion="PAR creado",
            datos={"client_id": cliente_id, "scope": scope}
        )
        
        return {
            "request_uri": request_uri,
            "expires_in": 60
        }
    
    async def crear_consentimiento(
        self,
        usuario_id: str,
        tpp_id: str,
        tpp_nombre: str,
        alcances: List[str],
        duracion_dias: int,
        instituciones: List[str],
        proposito: str
    ) -> Dict[str, Any]:
        """
        Crea un nuevo consentimiento.
        NCG 514 Art. 12-15
        """
        # Validar duración máxima
        if duracion_dias > self.config.max_consent_duration_days:
            return {
                "exito": False,
                "error": f"Duración máxima es {self.config.max_consent_duration_days} días"
            }
        
        # Crear consentimiento
        consent_id = f"CONS-{secrets.token_hex(12).upper()}"
        ahora = datetime.now()
        
        consentimiento = {
            "id": consent_id,
            "usuario_id": usuario_id,
            "tpp_id": tpp_id,
            "tpp_nombre": tpp_nombre,
            "estado": "pendiente",
            "alcances": alcances,
            "instituciones": instituciones,
            "proposito": proposito,
            "fecha_creacion": ahora,
            "fecha_expiracion": ahora + timedelta(days=duracion_dias),
            "fecha_autorizacion": None,
            "fecha_revocacion": None,
            "metodo_autenticacion": None,
            "historial": [{
                "accion": "creado",
                "timestamp": ahora.isoformat(),
                "detalle": "Consentimiento creado, pendiente de autorización"
            }]
        }
        
        # Almacenar
        if usuario_id not in self._consentimientos:
            self._consentimientos[usuario_id] = {}
        self._consentimientos[usuario_id][consent_id] = consentimiento
        
        # Actualizar métricas
        self._metricas_actuales.consentimientos_creados_hoy += 1
        
        self._registrar_evento(
            tipo=TipoEvento.CONSENTIMIENTO,
            nivel=NivelLog.INFO,
            origen="crear_consentimiento",
            descripcion=f"Consentimiento {consent_id} creado",
            usuario_id=usuario_id,
            participante_id=tpp_id,
            datos={"alcances": alcances, "duracion_dias": duracion_dias}
        )
        
        return {
            "exito": True,
            "consent_id": consent_id,
            "estado": "pendiente",
            "requiere_sca": self.config.require_sca,
            "expiracion": consentimiento["fecha_expiracion"].isoformat()
        }
    
    async def autorizar_consentimiento(
        self,
        consent_id: str,
        usuario_id: str,
        metodo_autenticacion: str,
        datos_autenticacion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Autoriza un consentimiento tras SCA exitosa.
        """
        # Buscar consentimiento
        if usuario_id not in self._consentimientos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        if consent_id not in self._consentimientos[usuario_id]:
            return {"exito": False, "error": "Consentimiento no encontrado"}
        
        consent = self._consentimientos[usuario_id][consent_id]
        
        if consent["estado"] != "pendiente":
            return {"exito": False, "error": f"Estado inválido: {consent['estado']}"}
        
        # Verificar SCA (simplificado - en producción sería más robusto)
        if not self._verificar_sca(metodo_autenticacion, datos_autenticacion):
            return {"exito": False, "error": "Autenticación SCA fallida"}
        
        # Autorizar
        ahora = datetime.now()
        consent["estado"] = "activo"
        consent["fecha_autorizacion"] = ahora
        consent["metodo_autenticacion"] = metodo_autenticacion
        consent["historial"].append({
            "accion": "autorizado",
            "timestamp": ahora.isoformat(),
            "metodo": metodo_autenticacion
        })
        
        # Actualizar métricas
        self._metricas_actuales.consentimientos_activos += 1
        
        self._registrar_evento(
            tipo=TipoEvento.CONSENTIMIENTO,
            nivel=NivelLog.INFO,
            origen="autorizar_consentimiento",
            descripcion=f"Consentimiento {consent_id} autorizado",
            usuario_id=usuario_id,
            participante_id=consent["tpp_id"]
        )
        
        # Generar tokens
        tokens = self._generar_tokens(consent_id, usuario_id, consent["alcances"])
        
        return {
            "exito": True,
            "consent_id": consent_id,
            "estado": "activo",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "DPoP" if self.config.dpop_enabled else "Bearer",
            "expires_in": self.config.token_lifetime_seconds,
            "scope": " ".join(consent["alcances"])
        }
    
    async def revocar_consentimiento(
        self,
        consent_id: str,
        usuario_id: str,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoca un consentimiento con efecto inmediato.
        NCG 514 Art. 15
        """
        if usuario_id not in self._consentimientos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        if consent_id not in self._consentimientos[usuario_id]:
            return {"exito": False, "error": "Consentimiento no encontrado"}
        
        consent = self._consentimientos[usuario_id][consent_id]
        
        if consent["estado"] != "activo":
            return {"exito": False, "error": f"No se puede revocar: {consent['estado']}"}
        
        # Revocar inmediatamente
        ahora = datetime.now()
        consent["estado"] = "revocado"
        consent["fecha_revocacion"] = ahora
        consent["motivo_revocacion"] = motivo or "Revocado por el usuario"
        consent["historial"].append({
            "accion": "revocado",
            "timestamp": ahora.isoformat(),
            "motivo": motivo
        })
        
        # Invalidar tokens asociados
        self._invalidar_tokens_consentimiento(consent_id)
        
        # Actualizar métricas
        self._metricas_actuales.consentimientos_activos -= 1
        self._metricas_actuales.consentimientos_revocados_hoy += 1
        
        self._registrar_evento(
            tipo=TipoEvento.CONSENTIMIENTO,
            nivel=NivelLog.INFO,
            origen="revocar_consentimiento",
            descripcion=f"Consentimiento {consent_id} revocado inmediatamente",
            usuario_id=usuario_id,
            participante_id=consent["tpp_id"],
            datos={"motivo": motivo}
        )
        
        return {
            "exito": True,
            "consent_id": consent_id,
            "estado": "revocado",
            "fecha_revocacion": ahora.isoformat(),
            "efecto_inmediato": True
        }
    
    # =========================================================================
    # SERVICIOS AIS (Account Information Services)
    # =========================================================================
    
    async def consultar_cuentas(
        self,
        access_token: str,
        consent_id: str
    ) -> Dict[str, Any]:
        """
        Consulta cuentas del usuario (AIS).
        Requiere scope 'accounts'
        """
        # Validar token
        validacion = self._validar_access_token(access_token, ["accounts"])
        if not validacion["valido"]:
            return {"error": validacion["error"]}
        
        # Validar consentimiento
        consent = self._obtener_consentimiento(consent_id)
        if not consent or consent["estado"] != "activo":
            return {"error": "consent_invalid", "error_description": "Consentimiento no válido"}
        
        # Registrar acceso
        self._registrar_acceso_ais(consent_id, "cuentas")
        
        # Simular respuesta (en producción: llamada a core bancario)
        return {
            "data": {
                "accounts": [
                    {
                        "account_id": "ACC001",
                        "iban": None,
                        "account_number": "0012345678",
                        "account_type": "CACC",
                        "currency": "CLP",
                        "name": "Cuenta Corriente",
                        "product": "Cuenta Vista Personal",
                        "status": "enabled"
                    }
                ]
            },
            "links": {
                "self": f"{self.config.base_url}/accounts"
            },
            "meta": {
                "total_pages": 1,
                "first_available_date": "2024-01-01"
            }
        }
    
    async def consultar_saldos(
        self,
        access_token: str,
        consent_id: str,
        account_id: str
    ) -> Dict[str, Any]:
        """
        Consulta saldos de una cuenta (AIS).
        Requiere scope 'balances'
        """
        validacion = self._validar_access_token(access_token, ["balances"])
        if not validacion["valido"]:
            return {"error": validacion["error"]}
        
        consent = self._obtener_consentimiento(consent_id)
        if not consent or consent["estado"] != "activo":
            return {"error": "consent_invalid"}
        
        self._registrar_acceso_ais(consent_id, "saldos")
        
        return {
            "data": {
                "account_id": account_id,
                "balances": [
                    {
                        "balance_type": "CLAV",  # Closing Available
                        "amount": {
                            "amount": "1500000.00",
                            "currency": "CLP"
                        },
                        "credit_debit_indicator": "CRDT",
                        "date_time": datetime.now().isoformat()
                    },
                    {
                        "balance_type": "CLBD",  # Closing Booked
                        "amount": {
                            "amount": "1450000.00",
                            "currency": "CLP"
                        },
                        "credit_debit_indicator": "CRDT",
                        "date_time": datetime.now().isoformat()
                    }
                ]
            }
        }
    
    async def consultar_transacciones(
        self,
        access_token: str,
        consent_id: str,
        account_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Consulta transacciones de una cuenta (AIS).
        Requiere scope 'transactions'.
        Máximo 24 meses de historia según NCG 514.
        """
        validacion = self._validar_access_token(access_token, ["transactions"])
        if not validacion["valido"]:
            return {"error": validacion["error"]}
        
        consent = self._obtener_consentimiento(consent_id)
        if not consent or consent["estado"] != "activo":
            return {"error": "consent_invalid"}
        
        # Validar rango de fechas (máximo 24 meses)
        if from_date:
            fecha_minima = date.today() - timedelta(days=self.config.transaction_history_months * 30)
            if from_date < fecha_minima:
                return {
                    "error": "invalid_request",
                    "error_description": f"Máximo {self.config.transaction_history_months} meses de historia"
                }
        
        self._registrar_acceso_ais(consent_id, "transacciones")
        
        # Limitar page_size
        page_size = min(page_size, self.config.max_transactions_per_page)
        
        return {
            "data": {
                "account_id": account_id,
                "transactions": [
                    {
                        "transaction_id": f"TXN{i:06d}",
                        "entry_reference": f"REF{i:06d}",
                        "amount": {
                            "amount": f"{50000 + i * 1000}",
                            "currency": "CLP"
                        },
                        "credit_debit_indicator": "DBIT" if i % 2 == 0 else "CRDT",
                        "status": "BOOK",
                        "booking_date": (date.today() - timedelta(days=i)).isoformat(),
                        "value_date": (date.today() - timedelta(days=i)).isoformat(),
                        "transaction_information": f"Transacción de ejemplo {i}",
                        "bank_transaction_code": {
                            "domain": "PMNT",
                            "family": "RCDT",
                            "sub_family": "ESCT"
                        }
                    }
                    for i in range(min(10, page_size))
                ]
            },
            "links": {
                "self": f"{self.config.base_url}/accounts/{account_id}/transactions?page={page}",
                "next": f"{self.config.base_url}/accounts/{account_id}/transactions?page={page+1}"
            },
            "meta": {
                "total_pages": 5,
                "first_available_date": (date.today() - timedelta(days=365)).isoformat()
            }
        }
    
    # =========================================================================
    # SERVICIOS PIS (Payment Initiation Services)
    # =========================================================================
    
    async def iniciar_pago(
        self,
        access_token: str,
        consent_id: str,
        debtor_account: str,
        creditor_account: str,
        creditor_name: str,
        amount: float,
        currency: str,
        reference: str,
        end_to_end_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia un pago (PIS).
        Requiere scope 'payments' y FAPI 2.0 Advanced.
        NCG 514 Fase 4 (Abril 2026)
        """
        # Verificar fase
        if self.config.fase_actual.value < FaseSFA.FASE_4.value:
            return {
                "error": "service_unavailable",
                "error_description": "PIS disponible desde Fase 4 (Abril 2026)"
            }
        
        # Validar token con scope payments
        validacion = self._validar_access_token(access_token, ["payments"])
        if not validacion["valido"]:
            return {"error": validacion["error"]}
        
        consent = self._obtener_consentimiento(consent_id)
        if not consent or consent["estado"] != "activo":
            return {"error": "consent_invalid"}
        
        if "payments" not in consent["alcances"]:
            return {"error": "insufficient_scope"}
        
        # Crear pago
        pago_id = f"PAY-{secrets.token_hex(10).upper()}"
        e2e_id = end_to_end_id or f"E2E-{secrets.token_hex(8).upper()}"
        ahora = datetime.now()
        
        pago = {
            "payment_id": pago_id,
            "consent_id": consent_id,
            "end_to_end_id": e2e_id,
            "estado": "RCVD",  # Received
            "debtor_account": debtor_account,
            "creditor_account": creditor_account,
            "creditor_name": creditor_name,
            "amount": amount,
            "currency": currency,
            "reference": reference,
            "fecha_creacion": ahora,
            "fecha_ejecucion": None,
            "historial": [{
                "estado": "RCVD",
                "timestamp": ahora.isoformat()
            }]
        }
        
        self._pagos[pago_id] = pago
        
        # Actualizar métricas
        self._metricas_actuales.pagos_pis_hoy += 1
        
        self._registrar_evento(
            tipo=TipoEvento.PAGO,
            nivel=NivelLog.INFO,
            origen="iniciar_pago",
            descripcion=f"Pago {pago_id} iniciado",
            usuario_id=consent["usuario_id"],
            participante_id=consent["tpp_id"],
            datos={
                "amount": amount,
                "currency": currency,
                "creditor": creditor_name
            }
        )
        
        # Simular procesamiento asíncrono
        # En producción: enviar a core bancario
        
        return {
            "data": {
                "payment_id": pago_id,
                "consent_id": consent_id,
                "status": "RCVD",
                "creation_date_time": ahora.isoformat(),
                "initiation": {
                    "instruction_identification": pago_id,
                    "end_to_end_identification": e2e_id,
                    "instructed_amount": {
                        "amount": str(amount),
                        "currency": currency
                    },
                    "debtor_account": {
                        "identification": debtor_account
                    },
                    "creditor_account": {
                        "identification": creditor_account
                    },
                    "creditor_name": creditor_name,
                    "remittance_information": reference
                }
            },
            "links": {
                "self": f"{self.config.base_url}/payments/{pago_id}"
            }
        }
    
    async def consultar_estado_pago(
        self,
        access_token: str,
        payment_id: str
    ) -> Dict[str, Any]:
        """Consulta el estado de un pago"""
        validacion = self._validar_access_token(access_token, ["payments"])
        if not validacion["valido"]:
            return {"error": validacion["error"]}
        
        if payment_id not in self._pagos:
            return {"error": "not_found", "error_description": "Pago no encontrado"}
        
        pago = self._pagos[payment_id]
        
        return {
            "data": {
                "payment_id": payment_id,
                "status": pago["estado"],
                "creation_date_time": pago["fecha_creacion"].isoformat(),
                "status_update_date_time": pago["historial"][-1]["timestamp"]
            }
        }
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _verificar_rate_limit(self, client_id: str) -> bool:
        """Verifica rate limiting por cliente"""
        ahora = datetime.now()
        minuto_atras = ahora - timedelta(minutes=1)
        
        if client_id not in self._request_counts:
            self._request_counts[client_id] = []
        
        # Limpiar requests antiguos
        self._request_counts[client_id] = [
            t for t in self._request_counts[client_id]
            if t > minuto_atras
        ]
        
        # Verificar límite
        if len(self._request_counts[client_id]) >= self.config.max_requests_per_minute:
            return False
        
        self._request_counts[client_id].append(ahora)
        return True
    
    def _verificar_sca(self, metodo: str, datos: Dict) -> bool:
        """Verifica Strong Customer Authentication (simplificado)"""
        metodos_validos = ["biometric", "otp_sms", "otp_app", "push", "fido2", "clave_unica"]
        return metodo.lower() in metodos_validos
    
    def _generar_tokens(
        self,
        consent_id: str,
        usuario_id: str,
        scopes: List[str]
    ) -> Dict[str, str]:
        """Genera access y refresh tokens"""
        ahora = datetime.now()
        
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "consent_id": consent_id,
            "usuario_id": usuario_id,
            "scopes": scopes,
            "created_at": ahora,
            "access_expires_at": ahora + timedelta(seconds=self.config.token_lifetime_seconds),
            "refresh_expires_at": ahora + timedelta(days=self.config.refresh_token_lifetime_days),
            "revocado": False
        }
        
        self._tokens[access_token] = token_data
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    def _validar_access_token(
        self,
        token: str,
        required_scopes: List[str]
    ) -> Dict[str, Any]:
        """Valida un access token"""
        if token not in self._tokens:
            return {"valido": False, "error": "invalid_token"}
        
        token_data = self._tokens[token]
        
        if token_data["revocado"]:
            return {"valido": False, "error": "token_revoked"}
        
        if datetime.now() > token_data["access_expires_at"]:
            return {"valido": False, "error": "token_expired"}
        
        # Verificar scopes
        for scope in required_scopes:
            if scope not in token_data["scopes"]:
                return {"valido": False, "error": "insufficient_scope"}
        
        return {"valido": True, "token_data": token_data}
    
    def _invalidar_tokens_consentimiento(self, consent_id: str):
        """Invalida todos los tokens de un consentimiento"""
        for token_data in self._tokens.values():
            if token_data["consent_id"] == consent_id:
                token_data["revocado"] = True
    
    def _obtener_consentimiento(self, consent_id: str) -> Optional[Dict]:
        """Obtiene un consentimiento por ID"""
        for user_consents in self._consentimientos.values():
            if consent_id in user_consents:
                return user_consents[consent_id]
        return None
    
    def _registrar_acceso_ais(self, consent_id: str, tipo: str):
        """Registra un acceso AIS"""
        self._accesos_log.append({
            "consent_id": consent_id,
            "tipo": tipo,
            "timestamp": datetime.now()
        })
        self._metricas_actuales.accesos_ais_hoy += 1
        self._metricas_actuales.accesos_ais_exitosos += 1
    
    def _registrar_evento(
        self,
        tipo: TipoEvento,
        nivel: NivelLog,
        origen: str,
        descripcion: str,
        usuario_id: Optional[str] = None,
        participante_id: Optional[str] = None,
        datos: Dict[str, Any] = None
    ):
        """Registra un evento del sistema"""
        evento = EventoSistema(
            id=f"EVT-{secrets.token_hex(8).upper()}",
            timestamp=datetime.now(),
            tipo=tipo,
            nivel=nivel,
            origen=origen,
            descripcion=descripcion,
            usuario_id=usuario_id,
            participante_id=participante_id,
            datos=datos or {},
            trace_id=secrets.token_hex(16)
        )
        
        self._eventos.append(evento)
        
        # Ejecutar handlers registrados
        if tipo in self._event_handlers:
            for handler in self._event_handlers[tipo]:
                try:
                    handler(evento)
                except Exception:
                    pass
    
    # =========================================================================
    # MÉTRICAS Y MONITOREO
    # =========================================================================
    
    def obtener_metricas(self) -> MetricasSistema:
        """Obtiene métricas actuales del sistema"""
        self._metricas_actuales.timestamp = datetime.now()
        return self._metricas_actuales
    
    def obtener_estado(self) -> Dict[str, Any]:
        """Obtiene estado general del sistema"""
        return {
            "estado": self.estado.value,
            "participante_id": self.config.participante_id,
            "fase_actual": self.config.fase_actual.value,
            "fapi_profile": self.config.fapi_profile,
            "metricas": {
                "consentimientos_activos": self._metricas_actuales.consentimientos_activos,
                "accesos_hoy": self._metricas_actuales.accesos_ais_hoy,
                "pagos_hoy": self._metricas_actuales.pagos_pis_hoy,
                "disponibilidad": self._metricas_actuales.disponibilidad_porcentaje
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def obtener_eventos(
        self,
        tipo: Optional[TipoEvento] = None,
        nivel_minimo: Optional[NivelLog] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limite: int = 100
    ) -> List[EventoSistema]:
        """Obtiene eventos del sistema filtrados"""
        eventos = self._eventos
        
        if tipo:
            eventos = [e for e in eventos if e.tipo == tipo]
        
        if nivel_minimo:
            niveles = list(NivelLog)
            nivel_idx = niveles.index(nivel_minimo)
            eventos = [e for e in eventos if niveles.index(e.nivel) >= nivel_idx]
        
        if desde:
            eventos = [e for e in eventos if e.timestamp >= desde]
        
        if hasta:
            eventos = [e for e in eventos if e.timestamp <= hasta]
        
        return sorted(eventos, key=lambda x: x.timestamp, reverse=True)[:limite]
    
    def registrar_event_handler(self, tipo: TipoEvento, handler: Callable):
        """Registra un handler para eventos"""
        if tipo not in self._event_handlers:
            self._event_handlers[tipo] = []
        self._event_handlers[tipo].append(handler)


# ============================================================================
# FACTORY Y CONFIGURACIÓN
# ============================================================================

class SFAFactory:
    """Factory para crear instancias del sistema SFA"""
    
    @staticmethod
    def crear_aspsp(
        participante_id: str,
        nombre: str,
        base_url: str,
        cert_paths: Dict[str, str]
    ) -> SistemaIntegradoSFA:
        """Crea instancia para ASPSP (banco/cooperativa)"""
        config = ConfiguracionSFA(
            participante_id=participante_id,
            nombre_participante=nombre,
            tipo_participante="ASPSP",
            base_url=base_url,
            authorization_endpoint=f"{base_url}/oauth/authorize",
            token_endpoint=f"{base_url}/oauth/token",
            par_endpoint=f"{base_url}/oauth/par",
            jwks_endpoint=f"{base_url}/.well-known/jwks.json",
            qwac_cert_path=cert_paths.get("qwac", ""),
            qwac_key_path=cert_paths.get("qwac_key", ""),
            qseal_cert_path=cert_paths.get("qseal", ""),
            qseal_key_path=cert_paths.get("qseal_key", "")
        )
        return SistemaIntegradoSFA(config)
    
    @staticmethod
    def crear_tpp(
        participante_id: str,
        nombre: str,
        tipo: str,  # AISP, PISP
        base_url: str,
        cert_paths: Dict[str, str]
    ) -> SistemaIntegradoSFA:
        """Crea instancia para TPP (fintech)"""
        config = ConfiguracionSFA(
            participante_id=participante_id,
            nombre_participante=nombre,
            tipo_participante=tipo,
            base_url=base_url,
            authorization_endpoint=f"{base_url}/oauth/authorize",
            token_endpoint=f"{base_url}/oauth/token",
            par_endpoint=f"{base_url}/oauth/par",
            jwks_endpoint=f"{base_url}/.well-known/jwks.json",
            qwac_cert_path=cert_paths.get("qwac", ""),
            qwac_key_path=cert_paths.get("qwac_key", ""),
            qseal_cert_path=cert_paths.get("qseal", ""),
            qseal_key_path=cert_paths.get("qseal_key", "")
        )
        return SistemaIntegradoSFA(config)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Crear sistema para ASPSP (banco)
        sistema = SFAFactory.crear_aspsp(
            participante_id="ASPSP-001",
            nombre="Banco Ejemplo",
            base_url="https://api.bancoejemplo.cl/openbanking/v1",
            cert_paths={
                "qwac": "/certs/qwac.pem",
                "qwac_key": "/certs/qwac.key",
                "qseal": "/certs/qseal.pem",
                "qseal_key": "/certs/qseal.key"
            }
        )
        
        print("=== ESTADO DEL SISTEMA ===")
        print(json.dumps(sistema.obtener_estado(), indent=2, ensure_ascii=False))
        
        # Crear consentimiento
        resultado = await sistema.crear_consentimiento(
            usuario_id="USR-001",
            tpp_id="TPP-FINTECH-001",
            tpp_nombre="MiFintech App",
            alcances=["accounts", "balances", "transactions"],
            duracion_dias=365,
            instituciones=["Banco Ejemplo"],
            proposito="Agregación financiera"
        )
        print("\n=== CONSENTIMIENTO CREADO ===")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        if resultado["exito"]:
            # Autorizar
            autorizacion = await sistema.autorizar_consentimiento(
                consent_id=resultado["consent_id"],
                usuario_id="USR-001",
                metodo_autenticacion="biometric",
                datos_autenticacion={"fingerprint_verified": True}
            )
            print("\n=== CONSENTIMIENTO AUTORIZADO ===")
            print(json.dumps(autorizacion, indent=2, ensure_ascii=False))
            
            if autorizacion["exito"]:
                # Consultar cuentas
                cuentas = await sistema.consultar_cuentas(
                    access_token=autorizacion["access_token"],
                    consent_id=resultado["consent_id"]
                )
                print("\n=== CUENTAS ===")
                print(json.dumps(cuentas, indent=2, ensure_ascii=False))
        
        # Métricas
        metricas = sistema.obtener_metricas()
        print("\n=== MÉTRICAS ===")
        print(f"Estado: {metricas.estado.value}")
        print(f"Consentimientos activos: {metricas.consentimientos_activos}")
        print(f"Accesos AIS hoy: {metricas.accesos_ais_hoy}")
    
    asyncio.run(main())
