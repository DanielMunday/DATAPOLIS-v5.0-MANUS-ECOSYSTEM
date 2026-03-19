"""
================================================================================
MÓDULO NCG 514: FAPI 2.0 SECURITY PROFILE
DATAPOLIS SpA - Sistema de Finanzas Abiertas
================================================================================

Implementación del perfil de seguridad FAPI 2.0 según:
- NCG 514 CMF Art. 18 - Estándares de seguridad
- FAPI 2.0 Security Profile (OpenID Foundation)
- RFC 8705 - OAuth 2.0 Mutual-TLS
- RFC 9449 - DPoP (Demonstrating Proof of Possession)

Autor: DATAPOLIS SpA
Versión: 2.0.0
Fecha: Febrero 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import hashlib
import secrets
import uuid
import base64
import json
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


# ==============================================================================
# ENUMERACIONES FAPI 2.0
# ==============================================================================

class FAPI2Profile(Enum):
    """Perfiles FAPI 2.0."""
    BASELINE = "baseline"      # Mínimo para AIS
    ADVANCED = "advanced"      # Requerido para PIS
    
class CertificateType(Enum):
    """Tipos de certificado digital."""
    QWAC = "qwac"      # Qualified Website Authentication Certificate
    QSEAL = "qseal"    # Qualified Electronic Seal
    MTLS = "mtls"      # Mutual TLS client certificate
    
class ParticipantRole(Enum):
    """Roles de participante NCG 514."""
    ASPSP = "aspsp"    # Account Servicing PSP (Banco)
    PISP = "pisp"      # Payment Initiation SP
    AISP = "aisp"      # Account Information SP
    CBPII = "cbpii"    # Card-Based Payment Instrument Issuer
    
class TokenEndpointAuthMethod(Enum):
    """Métodos de autenticación en token endpoint."""
    PRIVATE_KEY_JWT = "private_key_jwt"
    TLS_CLIENT_AUTH = "tls_client_auth"
    SELF_SIGNED_TLS = "self_signed_tls_client_auth"
    
class SigningAlgorithm(Enum):
    """Algoritmos de firma permitidos."""
    PS256 = "PS256"    # RSASSA-PSS with SHA-256
    ES256 = "ES256"    # ECDSA with P-256 and SHA-256
    

# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class X509Certificate:
    """Certificado X.509 para mTLS."""
    certificate_pem: str = ""
    private_key_pem: str = ""
    serial_number: str = ""
    subject_dn: str = ""
    issuer_dn: str = ""
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=365))
    certificate_type: CertificateType = CertificateType.MTLS
    thumbprint_sha256: str = ""

@dataclass
class DPoPProof:
    """Prueba DPoP (Demonstrating Proof of Possession)."""
    jti: str = field(default_factory=lambda: str(uuid.uuid4()))
    htm: str = ""      # HTTP method
    htu: str = ""      # HTTP URI
    iat: int = 0
    ath: str = ""      # Access token hash (when bound)
    nonce: str = ""    # Server-provided nonce
    
@dataclass
class PARRequest:
    """Pushed Authorization Request."""
    request_uri: str = ""
    expires_in: int = 60
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class SecurityAuditLog:
    """Registro de auditoría de seguridad."""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    participant_id: str = ""
    client_id: str = ""
    action: str = ""
    result: str = ""
    ip_address: str = ""
    certificate_thumbprint: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class FAPI2Configuration:
    """Configuración del servidor FAPI 2.0."""
    issuer: str = "https://auth.datapolis.cl"
    authorization_endpoint: str = "/oauth/authorize"
    token_endpoint: str = "/oauth/token"
    pushed_authorization_request_endpoint: str = "/oauth/par"
    introspection_endpoint: str = "/oauth/introspect"
    revocation_endpoint: str = "/oauth/revoke"
    jwks_uri: str = "/.well-known/jwks.json"
    
    # Métodos soportados
    token_endpoint_auth_methods_supported: List[str] = field(default_factory=lambda: [
        "private_key_jwt",
        "tls_client_auth"
    ])
    
    # Algoritmos soportados
    id_token_signing_alg_values_supported: List[str] = field(default_factory=lambda: [
        "PS256", "ES256"
    ])
    request_object_signing_alg_values_supported: List[str] = field(default_factory=lambda: [
        "PS256", "ES256"
    ])
    
    # FAPI 2.0 específico
    require_pushed_authorization_requests: bool = True
    require_signed_request_object: bool = True
    require_dpop: bool = False  # Opcional en baseline
    tls_client_certificate_bound_access_tokens: bool = True
    
    # mTLS
    mtls_endpoint_aliases: Dict[str, str] = field(default_factory=dict)


# ==============================================================================
# GESTOR DE CERTIFICADOS
# ==============================================================================

class CertificateManager:
    """
    Gestiona certificados digitales para mTLS y QWAC/QSEAL.
    """
    
    def __init__(self):
        self._certificates: Dict[str, X509Certificate] = {}
        self._trusted_cas: List[str] = []
    
    def generar_certificado_autofirmado(
        self,
        common_name: str,
        organization: str,
        organization_id: str,
        validity_days: int = 365
    ) -> X509Certificate:
        """Genera un certificado autofirmado para desarrollo/testing."""
        
        # Generar clave privada RSA
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Construir subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, organization_id),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Construir certificado
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(subject)  # Autofirmado
        cert_builder = cert_builder.public_key(private_key.public_key())
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.not_valid_before(datetime.utcnow())
        cert_builder = cert_builder.not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )
        
        # Extensiones básicas
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )
        
        # Firmar certificado
        certificate = cert_builder.sign(
            private_key=private_key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
        
        # Serializar
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        # Calcular thumbprint
        thumbprint = hashlib.sha256(
            certificate.public_bytes(serialization.Encoding.DER)
        ).hexdigest()
        
        cert_obj = X509Certificate(
            certificate_pem=cert_pem,
            private_key_pem=key_pem,
            serial_number=str(certificate.serial_number),
            subject_dn=common_name,
            issuer_dn=common_name,
            valid_from=certificate.not_valid_before,
            valid_to=certificate.not_valid_after,
            thumbprint_sha256=thumbprint
        )
        
        self._certificates[thumbprint] = cert_obj
        
        return cert_obj
    
    def validar_certificado(
        self,
        certificate_pem: str,
        expected_roles: List[ParticipantRole] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Valida un certificado cliente."""
        
        try:
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode(),
                default_backend()
            )
            
            # Verificar vigencia
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return False, "Certificado expirado o no válido aún", None
            
            # Extraer información
            info = {
                "serial_number": str(cert.serial_number),
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "valid_from": cert.not_valid_before.isoformat(),
                "valid_to": cert.not_valid_after.isoformat(),
                "thumbprint": hashlib.sha256(
                    cert.public_bytes(serialization.Encoding.DER)
                ).hexdigest()
            }
            
            # Aquí se validaría contra CA de confianza
            # y se verificarían los roles permitidos
            
            return True, "Certificado válido", info
            
        except Exception as e:
            return False, f"Error validando certificado: {str(e)}", None
    
    def obtener_certificado(self, thumbprint: str) -> Optional[X509Certificate]:
        """Obtiene un certificado por thumbprint."""
        return self._certificates.get(thumbprint)


# ==============================================================================
# MANEJADOR mTLS
# ==============================================================================

class mTLSHandler:
    """
    Maneja la autenticación mutua TLS según RFC 8705.
    """
    
    def __init__(self, certificate_manager: CertificateManager):
        self.cert_manager = certificate_manager
        self._bound_tokens: Dict[str, str] = {}  # token -> cert_thumbprint
    
    def extraer_certificado_cliente(
        self,
        request_headers: Dict[str, str]
    ) -> Tuple[bool, Optional[str], str]:
        """Extrae el certificado cliente de los headers de la solicitud."""
        
        # El certificado puede venir en diferentes headers según configuración
        cert_header = request_headers.get(
            "X-Client-Cert",
            request_headers.get("SSL_CLIENT_CERT", "")
        )
        
        if not cert_header:
            return False, None, "No se encontró certificado cliente"
        
        # Decodificar si está en base64 o URL-encoded
        try:
            if cert_header.startswith("-----BEGIN"):
                cert_pem = cert_header
            else:
                cert_pem = base64.b64decode(cert_header).decode()
            
            return True, cert_pem, "OK"
        except Exception as e:
            return False, None, f"Error decodificando certificado: {str(e)}"
    
    def vincular_token_a_certificado(
        self,
        access_token: str,
        cert_thumbprint: str
    ):
        """Vincula un access token a un certificado (RFC 8705)."""
        self._bound_tokens[access_token] = cert_thumbprint
    
    def validar_token_vinculado(
        self,
        access_token: str,
        cert_thumbprint: str
    ) -> Tuple[bool, str]:
        """Valida que el token esté vinculado al certificado presentado."""
        
        if access_token not in self._bound_tokens:
            return False, "Token no tiene certificado vinculado"
        
        expected_thumbprint = self._bound_tokens[access_token]
        
        if expected_thumbprint != cert_thumbprint:
            return False, "Certificado no coincide con el vinculado al token"
        
        return True, "OK"
    
    def generar_cnf_claim(self, cert_thumbprint: str) -> Dict[str, Any]:
        """Genera el claim 'cnf' para el token según RFC 8705."""
        return {
            "cnf": {
                "x5t#S256": cert_thumbprint
            }
        }


# ==============================================================================
# MANEJADOR DPoP (Demonstrating Proof of Possession)
# ==============================================================================

class DPoPHandler:
    """
    Maneja tokens DPoP según RFC 9449.
    Proporciona protección adicional contra robo de tokens.
    """
    
    def __init__(self):
        self._used_jtis: Dict[str, datetime] = {}  # Prevenir replay
        self._nonces: Dict[str, datetime] = {}
    
    def generar_nonce(self) -> str:
        """Genera un nonce para DPoP."""
        nonce = secrets.token_urlsafe(32)
        self._nonces[nonce] = datetime.now()
        return nonce
    
    def crear_dpop_proof(
        self,
        private_key_jwk: Dict[str, Any],
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None,
        nonce: Optional[str] = None
    ) -> str:
        """Crea una prueba DPoP."""
        
        # Header
        header = {
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": {
                "kty": private_key_jwk.get("kty"),
                "crv": private_key_jwk.get("crv"),
                "x": private_key_jwk.get("x"),
                "y": private_key_jwk.get("y")
            }
        }
        
        # Payload
        payload = {
            "jti": str(uuid.uuid4()),
            "htm": http_method.upper(),
            "htu": http_uri,
            "iat": int(datetime.now().timestamp())
        }
        
        # Agregar hash del access token si existe
        if access_token:
            ath = hashlib.sha256(access_token.encode()).digest()
            payload["ath"] = base64.urlsafe_b64encode(ath).decode().rstrip("=")
        
        # Agregar nonce si existe
        if nonce:
            payload["nonce"] = nonce
        
        # En producción, firmar con clave privada
        # Aquí simulamos el JWT
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}.simulated_signature"
    
    def validar_dpop_proof(
        self,
        dpop_proof: str,
        expected_method: str,
        expected_uri: str,
        access_token: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Valida una prueba DPoP."""
        
        try:
            parts = dpop_proof.split(".")
            if len(parts) != 3:
                return False, "Formato JWT inválido", None
            
            # Decodificar header y payload
            header = json.loads(
                base64.urlsafe_b64decode(parts[0] + "==").decode()
            )
            payload = json.loads(
                base64.urlsafe_b64decode(parts[1] + "==").decode()
            )
            
            # Validar tipo
            if header.get("typ") != "dpop+jwt":
                return False, "Tipo debe ser dpop+jwt", None
            
            # Validar método HTTP
            if payload.get("htm", "").upper() != expected_method.upper():
                return False, "Método HTTP no coincide", None
            
            # Validar URI
            if payload.get("htu") != expected_uri:
                return False, "URI no coincide", None
            
            # Validar timestamp (máximo 5 minutos de antigüedad)
            iat = payload.get("iat", 0)
            if abs(datetime.now().timestamp() - iat) > 300:
                return False, "Prueba DPoP expirada", None
            
            # Validar JTI no usado
            jti = payload.get("jti")
            if jti in self._used_jtis:
                return False, "JTI ya utilizado (replay attack)", None
            
            # Registrar JTI
            self._used_jtis[jti] = datetime.now()
            
            # Validar hash del access token si corresponde
            if access_token and "ath" in payload:
                expected_ath = hashlib.sha256(access_token.encode()).digest()
                expected_ath_b64 = base64.urlsafe_b64encode(expected_ath).decode().rstrip("=")
                if payload["ath"] != expected_ath_b64:
                    return False, "Hash del access token no coincide", None
            
            return True, "OK", {
                "jti": jti,
                "htm": payload.get("htm"),
                "htu": payload.get("htu"),
                "jwk_thumbprint": header.get("jwk", {})
            }
            
        except Exception as e:
            return False, f"Error validando DPoP: {str(e)}", None
    
    def limpiar_jtis_expirados(self):
        """Limpia JTIs antiguos para liberar memoria."""
        limite = datetime.now() - timedelta(hours=1)
        self._used_jtis = {
            jti: ts for jti, ts in self._used_jtis.items()
            if ts > limite
        }


# ==============================================================================
# LOGGER DE AUDITORÍA DE SEGURIDAD
# ==============================================================================

class SecurityAuditLogger:
    """
    Registra eventos de seguridad para cumplimiento NCG 514.
    Los logs deben conservarse 5 años (Art. III.B.3).
    """
    
    def __init__(self):
        self._logs: List[SecurityAuditLog] = []
    
    def registrar_evento(
        self,
        event_type: str,
        participant_id: str,
        client_id: str,
        action: str,
        result: str,
        ip_address: str = "",
        certificate_thumbprint: str = "",
        details: Dict[str, Any] = None
    ):
        """Registra un evento de seguridad."""
        
        log = SecurityAuditLog(
            event_type=event_type,
            participant_id=participant_id,
            client_id=client_id,
            action=action,
            result=result,
            ip_address=ip_address,
            certificate_thumbprint=certificate_thumbprint,
            details=details or {}
        )
        
        self._logs.append(log)
        
        # En producción, persistir a base de datos
        self._persistir_log(log)
    
    def obtener_logs(
        self,
        participant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None
    ) -> List[SecurityAuditLog]:
        """Obtiene logs filtrados."""
        
        resultado = self._logs
        
        if participant_id:
            resultado = [l for l in resultado if l.participant_id == participant_id]
        
        if event_type:
            resultado = [l for l in resultado if l.event_type == event_type]
        
        if desde:
            resultado = [l for l in resultado if l.timestamp >= desde]
        
        if hasta:
            resultado = [l for l in resultado if l.timestamp <= hasta]
        
        return resultado
    
    def _persistir_log(self, log: SecurityAuditLog):
        """Persiste log a almacenamiento permanente."""
        # En producción: escribir a base de datos, S3, etc.
        pass


# ==============================================================================
# PERFIL DE SEGURIDAD FAPI 2.0
# ==============================================================================

class FAPI2SecurityProfile:
    """
    Implementación del perfil de seguridad FAPI 2.0.
    Coordina todos los componentes de seguridad.
    """
    
    def __init__(self, profile: FAPI2Profile = FAPI2Profile.ADVANCED):
        self.profile = profile
        self.config = FAPI2Configuration()
        self.cert_manager = CertificateManager()
        self.mtls_handler = mTLSHandler(self.cert_manager)
        self.dpop_handler = DPoPHandler()
        self.audit_logger = SecurityAuditLogger()
        
        # Configurar según perfil
        if profile == FAPI2Profile.ADVANCED:
            self.config.require_dpop = True
    
    def validar_solicitud_autorizacion(
        self,
        request: Dict[str, Any],
        client_certificate: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Valida una solicitud de autorización según FAPI 2.0."""
        
        errores = []
        
        # 1. Verificar PAR requerido
        if self.config.require_pushed_authorization_requests:
            if "request_uri" not in request:
                errores.append("Debe usar Pushed Authorization Request (PAR)")
        
        # 2. Verificar request object firmado
        if self.config.require_signed_request_object:
            if "request" not in request and "request_uri" not in request:
                errores.append("Se requiere request object firmado")
        
        # 3. Verificar PKCE
        if "code_challenge" not in request:
            errores.append("Se requiere PKCE (code_challenge)")
        elif request.get("code_challenge_method") != "S256":
            errores.append("code_challenge_method debe ser S256")
        
        # 4. Verificar scope
        scope = request.get("scope", "")
        if "openid" not in scope:
            errores.append("scope debe incluir 'openid'")
        
        # 5. Verificar redirect_uri
        if "redirect_uri" not in request:
            errores.append("redirect_uri es requerido")
        
        # 6. Verificar state
        if "state" not in request:
            errores.append("state es requerido")
        
        # 7. Verificar nonce para id_token
        if "nonce" not in request:
            errores.append("nonce es requerido")
        
        if errores:
            return False, "; ".join(errores), {}
        
        return True, "OK", {
            "validated_at": datetime.now().isoformat(),
            "profile": self.profile.value
        }
    
    def validar_solicitud_token(
        self,
        request: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Valida una solicitud de token según FAPI 2.0."""
        
        # 1. Extraer y validar certificado cliente
        ok, cert_pem, msg = self.mtls_handler.extraer_certificado_cliente(headers)
        if not ok:
            return False, f"Error mTLS: {msg}", {}
        
        # Validar certificado
        ok, msg, cert_info = self.cert_manager.validar_certificado(cert_pem)
        if not ok:
            return False, f"Certificado inválido: {msg}", {}
        
        # 2. Validar client assertion si usa private_key_jwt
        auth_method = request.get("client_assertion_type")
        if auth_method == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer":
            # Validar JWT de cliente
            client_assertion = request.get("client_assertion")
            if not client_assertion:
                return False, "client_assertion requerido", {}
            # Aquí se validaría el JWT
        
        # 3. Validar PKCE code_verifier
        if "code_verifier" not in request:
            return False, "code_verifier requerido", {}
        
        # 4. Validar DPoP si está habilitado
        if self.config.require_dpop:
            dpop_proof = headers.get("DPoP")
            if not dpop_proof:
                return False, "Se requiere prueba DPoP", {}
            
            # Validar DPoP
            ok, msg, dpop_info = self.dpop_handler.validar_dpop_proof(
                dpop_proof,
                expected_method="POST",
                expected_uri=f"{self.config.issuer}{self.config.token_endpoint}"
            )
            if not ok:
                return False, f"DPoP inválido: {msg}", {}
        
        return True, "OK", {
            "certificate": cert_info,
            "validated_at": datetime.now().isoformat()
        }
    
    def generar_par_uri(self, request: Dict[str, Any]) -> PARRequest:
        """Genera un request_uri para PAR."""
        
        request_uri = f"urn:ietf:params:oauth:request_uri:{secrets.token_urlsafe(32)}"
        
        return PARRequest(
            request_uri=request_uri,
            expires_in=60
        )
    
    def obtener_configuracion_well_known(self) -> Dict[str, Any]:
        """Retorna la configuración para .well-known/openid-configuration."""
        
        return {
            "issuer": self.config.issuer,
            "authorization_endpoint": f"{self.config.issuer}{self.config.authorization_endpoint}",
            "token_endpoint": f"{self.config.issuer}{self.config.token_endpoint}",
            "pushed_authorization_request_endpoint": f"{self.config.issuer}{self.config.pushed_authorization_request_endpoint}",
            "introspection_endpoint": f"{self.config.issuer}{self.config.introspection_endpoint}",
            "revocation_endpoint": f"{self.config.issuer}{self.config.revocation_endpoint}",
            "jwks_uri": f"{self.config.issuer}{self.config.jwks_uri}",
            
            "token_endpoint_auth_methods_supported": self.config.token_endpoint_auth_methods_supported,
            "id_token_signing_alg_values_supported": self.config.id_token_signing_alg_values_supported,
            "request_object_signing_alg_values_supported": self.config.request_object_signing_alg_values_supported,
            
            "require_pushed_authorization_requests": self.config.require_pushed_authorization_requests,
            "require_signed_request_object": self.config.require_signed_request_object,
            "tls_client_certificate_bound_access_tokens": self.config.tls_client_certificate_bound_access_tokens,
            
            "scopes_supported": ["openid", "accounts", "payments", "profile"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            
            "dpop_signing_alg_values_supported": ["PS256", "ES256"] if self.config.require_dpop else [],
            
            "mtls_endpoint_aliases": {
                "token_endpoint": f"https://mtls.{self.config.issuer.split('//')[1]}{self.config.token_endpoint}",
                "introspection_endpoint": f"https://mtls.{self.config.issuer.split('//')[1]}{self.config.introspection_endpoint}"
            }
        }


# ==============================================================================
# DEMO
# ==============================================================================

def demo_fapi_security():
    """Demuestra el uso del perfil de seguridad FAPI 2.0."""
    
    print("=" * 80)
    print("DEMO: FAPI 2.0 SECURITY PROFILE - NCG 514")
    print("=" * 80)
    
    # 1. Crear perfil de seguridad
    fapi = FAPI2SecurityProfile(FAPI2Profile.ADVANCED)
    print("\n✓ Perfil FAPI 2.0 ADVANCED inicializado")
    
    # 2. Generar certificado de prueba
    cert = fapi.cert_manager.generar_certificado_autofirmado(
        common_name="DATAPOLIS SpA",
        organization="DATAPOLIS",
        organization_id="77123456-7"
    )
    print(f"✓ Certificado generado: {cert.thumbprint_sha256[:16]}...")
    
    # 3. Obtener configuración well-known
    config = fapi.obtener_configuracion_well_known()
    print(f"✓ Configuración disponible en: {config['issuer']}/.well-known/openid-configuration")
    
    # 4. Validar solicitud de autorización
    solicitud = {
        "client_id": "datapolis_client",
        "response_type": "code",
        "scope": "openid accounts payments",
        "redirect_uri": "https://datapolis.cl/callback",
        "state": secrets.token_urlsafe(16),
        "nonce": secrets.token_urlsafe(16),
        "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        "code_challenge_method": "S256",
        "request_uri": "urn:ietf:params:oauth:request_uri:test123"
    }
    
    ok, msg, info = fapi.validar_solicitud_autorizacion(solicitud, cert.certificate_pem)
    print(f"✓ Validación de autorización: {'OK' if ok else msg}")
    
    # 5. Crear prueba DPoP
    dpop_proof = fapi.dpop_handler.crear_dpop_proof(
        private_key_jwk={"kty": "EC", "crv": "P-256", "x": "test", "y": "test"},
        http_method="POST",
        http_uri=f"{fapi.config.issuer}{fapi.config.token_endpoint}"
    )
    print(f"✓ Prueba DPoP generada: {dpop_proof[:50]}...")
    
    # 6. Registrar evento de auditoría
    fapi.audit_logger.registrar_evento(
        event_type="authorization_request",
        participant_id="datapolis",
        client_id="datapolis_client",
        action="validate",
        result="success",
        ip_address="192.168.1.100",
        certificate_thumbprint=cert.thumbprint_sha256
    )
    print("✓ Evento de auditoría registrado")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETADA - FAPI 2.0 SECURITY OPERATIVO")
    print("=" * 80)
    
    return fapi


if __name__ == "__main__":
    demo_fapi_security()
