"""
DATAPOLIS v3.0 - NCG 514 DIRECTORIO DE PARTICIPANTES
=====================================================
Gestión del Directorio de Participantes del Sistema de Finanzas Abiertas (SFA)
Según NCG 514 CMF Chile - Deadline Abril 2026

Autor: DATAPOLIS SpA
Versión: 1.0.0
Fecha: 2026-02-01
Normativa: NCG 514 CMF - Sistema de Finanzas Abiertas Chile
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Set
from enum import Enum
import hashlib
import secrets
import json
import re
from abc import ABC, abstractmethod


# ============================================================================
# ENUMERACIONES NCG 514 - DIRECTORIO PARTICIPANTES
# ============================================================================

class TipoParticipante(Enum):
    """Tipos de participantes según NCG 514 Art. 5"""
    ASPSP = "ASPSP"  # Account Servicing Payment Service Provider (Bancos, Cooperativas)
    PISP = "PISP"    # Payment Initiation Service Provider
    AISP = "AISP"    # Account Information Service Provider
    CBPII = "CBPII"  # Card Based Payment Instrument Issuer
    TPP = "TPP"      # Third Party Provider (genérico)
    PSBI = "PSBI"    # Proveedor de Servicios Basados en Información
    PSIP = "PSIP"    # Proveedor de Servicios de Iniciación de Pagos


class EstadoParticipante(Enum):
    """Estados de registro en el directorio"""
    PENDIENTE = "pendiente"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    REVOCADO = "revocado"
    INACTIVO = "inactivo"


class TipoCertificado(Enum):
    """Tipos de certificados según eIDAS/NCG 514"""
    QWAC = "QWAC"    # Qualified Website Authentication Certificate
    QSEAL = "QSEAL"  # Qualified Electronic Seal Certificate
    MTLS = "MTLS"    # Mutual TLS Certificate
    SIGNING = "SIGNING"  # Signing Certificate


class NivelSeguridad(Enum):
    """Niveles de seguridad requeridos"""
    BASICO = "basico"       # Solo lectura de información
    ESTANDAR = "estandar"   # Lectura + operaciones limitadas
    AVANZADO = "avanzado"   # Lectura + iniciación de pagos


class CategoriaServicio(Enum):
    """Categorías de servicios del SFA"""
    AIS = "AIS"  # Account Information Services
    PIS = "PIS"  # Payment Initiation Services
    CBPII = "CBPII"  # Card Based Payment Instrument Issuance
    AGREGACION = "AGREGACION"  # Agregación financiera
    ANALISIS = "ANALISIS"  # Análisis financiero
    CREDITO = "CREDITO"  # Evaluación crediticia
    INVERSION = "INVERSION"  # Servicios de inversión


# ============================================================================
# DATACLASSES - ESTRUCTURAS DE DATOS DEL DIRECTORIO
# ============================================================================

@dataclass
class CertificadoParticipante:
    """Certificado digital de un participante"""
    id: str
    tipo: TipoCertificado
    thumbprint_sha256: str
    subject_dn: str
    issuer_dn: str
    serial_number: str
    fecha_emision: datetime
    fecha_expiracion: datetime
    pem_encoded: str
    roles_autorizados: List[TipoParticipante]
    estado: str = "activo"
    revocado_fecha: Optional[datetime] = None
    revocado_razon: Optional[str] = None
    
    def esta_vigente(self) -> bool:
        """Verifica si el certificado está vigente"""
        ahora = datetime.now()
        return (
            self.estado == "activo" and
            self.fecha_emision <= ahora <= self.fecha_expiracion and
            self.revocado_fecha is None
        )
    
    def dias_hasta_expiracion(self) -> int:
        """Días hasta expiración"""
        return (self.fecha_expiracion - datetime.now()).days


@dataclass
class EndpointAPI:
    """Endpoint API de un participante"""
    id: str
    nombre: str
    url_base: str
    url_well_known: str
    version_api: str
    servicios_soportados: List[CategoriaServicio]
    metodos_autenticacion: List[str]
    fecha_registro: datetime
    estado: str = "activo"
    latencia_promedio_ms: Optional[float] = None
    disponibilidad_porcentaje: Optional[float] = None
    ultima_verificacion: Optional[datetime] = None


@dataclass
class ContactoParticipante:
    """Información de contacto del participante"""
    nombre_contacto: str
    cargo: str
    email: str
    telefono: str
    tipo_contacto: str  # tecnico, comercial, legal, dpo
    es_principal: bool = False


@dataclass
class Participante:
    """Participante registrado en el directorio SFA"""
    id: str
    rut: str
    razon_social: str
    nombre_fantasia: str
    tipos: List[TipoParticipante]
    estado: EstadoParticipante
    nivel_seguridad: NivelSeguridad
    
    # Información de registro
    fecha_solicitud: datetime
    fecha_aprobacion: Optional[datetime]
    fecha_activacion: Optional[datetime]
    numero_registro_cmf: Optional[str]
    
    # Certificados y endpoints
    certificados: List[CertificadoParticipante] = field(default_factory=list)
    endpoints: List[EndpointAPI] = field(default_factory=list)
    
    # Servicios autorizados
    servicios_autorizados: List[CategoriaServicio] = field(default_factory=list)
    alcances_autorizados: List[str] = field(default_factory=list)
    
    # Contactos
    contactos: List[ContactoParticipante] = field(default_factory=list)
    
    # Información adicional
    sitio_web: Optional[str] = None
    logo_url: Optional[str] = None
    descripcion: Optional[str] = None
    
    # Auditoría
    ultima_actualizacion: Optional[datetime] = None
    actualizado_por: Optional[str] = None
    historial_estados: List[Dict] = field(default_factory=list)
    
    def esta_activo(self) -> bool:
        """Verifica si el participante está activo"""
        return self.estado == EstadoParticipante.ACTIVO
    
    def tiene_certificado_vigente(self, tipo: TipoCertificado) -> bool:
        """Verifica si tiene certificado vigente del tipo especificado"""
        return any(
            c.tipo == tipo and c.esta_vigente()
            for c in self.certificados
        )
    
    def puede_ofrecer_servicio(self, servicio: CategoriaServicio) -> bool:
        """Verifica si puede ofrecer un servicio específico"""
        return (
            self.esta_activo() and
            servicio in self.servicios_autorizados
        )


@dataclass
class SolicitudRegistro:
    """Solicitud de registro de nuevo participante"""
    id: str
    rut_solicitante: str
    razon_social: str
    nombre_fantasia: str
    tipos_solicitados: List[TipoParticipante]
    servicios_solicitados: List[CategoriaServicio]
    
    # Documentación
    documentos_adjuntos: List[Dict] = field(default_factory=list)
    declaracion_cumplimiento: bool = False
    acepta_terminos: bool = False
    
    # Estado
    fecha_solicitud: datetime = field(default_factory=datetime.now)
    estado: str = "pendiente"
    observaciones: List[Dict] = field(default_factory=list)
    
    # Resolución
    fecha_resolucion: Optional[datetime] = None
    resuelto_por: Optional[str] = None
    resultado: Optional[str] = None  # aprobado, rechazado, requiere_info


@dataclass
class AuditLogDirectorio:
    """Log de auditoría del directorio"""
    id: str
    timestamp: datetime
    tipo_evento: str
    participante_id: Optional[str]
    usuario_id: str
    ip_origen: str
    accion: str
    detalles: Dict
    resultado: str


# ============================================================================
# VALIDADORES
# ============================================================================

class ValidadorParticipante:
    """Validador de datos de participantes"""
    
    @staticmethod
    def validar_rut(rut: str) -> Dict[str, Any]:
        """Valida RUT chileno"""
        rut_limpio = rut.replace(".", "").replace("-", "").upper()
        
        if len(rut_limpio) < 2:
            return {"valido": False, "error": "RUT muy corto"}
        
        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1]
        
        if not cuerpo.isdigit():
            return {"valido": False, "error": "Cuerpo del RUT debe ser numérico"}
        
        # Calcular dígito verificador
        suma = 0
        multiplo = 2
        for d in reversed(cuerpo):
            suma += int(d) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2
        
        resto = suma % 11
        dv_calculado = "K" if resto == 1 else "0" if resto == 0 else str(11 - resto)
        
        if dv != dv_calculado:
            return {"valido": False, "error": "Dígito verificador inválido"}
        
        return {"valido": True, "rut_formateado": f"{int(cuerpo):,}".replace(",", ".") + "-" + dv}
    
    @staticmethod
    def validar_url(url: str) -> Dict[str, Any]:
        """Valida formato de URL"""
        patron = re.compile(
            r'^https://'  # Solo HTTPS
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        if patron.match(url):
            return {"valido": True}
        return {"valido": False, "error": "URL debe usar HTTPS y tener formato válido"}
    
    @staticmethod
    def validar_certificado(cert: CertificadoParticipante) -> Dict[str, Any]:
        """Valida certificado de participante"""
        errores = []
        
        # Verificar vigencia
        if not cert.esta_vigente():
            errores.append("Certificado no vigente o revocado")
        
        # Verificar próxima expiración (alerta 30 días)
        dias = cert.dias_hasta_expiracion()
        advertencias = []
        if dias < 30:
            advertencias.append(f"Certificado expira en {dias} días")
        
        # Verificar thumbprint
        if len(cert.thumbprint_sha256) != 64:
            errores.append("Thumbprint SHA256 inválido")
        
        return {
            "valido": len(errores) == 0,
            "errores": errores,
            "advertencias": advertencias
        }


# ============================================================================
# GESTOR DEL DIRECTORIO DE PARTICIPANTES
# ============================================================================

class DirectorioParticipantes:
    """
    Gestor central del Directorio de Participantes del SFA
    Según NCG 514 CMF Chile
    """
    
    def __init__(self):
        self.participantes: Dict[str, Participante] = {}
        self.solicitudes: Dict[str, SolicitudRegistro] = {}
        self.logs_auditoria: List[AuditLogDirectorio] = []
        self.validador = ValidadorParticipante()
        self._cache_endpoints: Dict[str, datetime] = {}
    
    # -------------------------------------------------------------------------
    # GESTIÓN DE PARTICIPANTES
    # -------------------------------------------------------------------------
    
    def registrar_participante(
        self,
        rut: str,
        razon_social: str,
        nombre_fantasia: str,
        tipos: List[TipoParticipante],
        servicios: List[CategoriaServicio],
        contacto_principal: ContactoParticipante,
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """
        Inicia el proceso de registro de un nuevo participante.
        Según NCG 514 Art. 6-7
        """
        # Validar RUT
        validacion_rut = self.validador.validar_rut(rut)
        if not validacion_rut["valido"]:
            return {"exito": False, "error": validacion_rut["error"]}
        
        # Verificar no existe
        if any(p.rut == rut for p in self.participantes.values()):
            return {"exito": False, "error": "Participante ya registrado"}
        
        # Crear solicitud
        solicitud_id = f"SOL-{secrets.token_hex(8).upper()}"
        solicitud = SolicitudRegistro(
            id=solicitud_id,
            rut_solicitante=rut,
            razon_social=razon_social,
            nombre_fantasia=nombre_fantasia,
            tipos_solicitados=tipos,
            servicios_solicitados=servicios
        )
        
        self.solicitudes[solicitud_id] = solicitud
        
        # Log auditoría
        self._registrar_log(
            tipo_evento="SOLICITUD_REGISTRO",
            participante_id=None,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion="Solicitud de registro iniciada",
            detalles={
                "solicitud_id": solicitud_id,
                "rut": rut,
                "tipos": [t.value for t in tipos]
            },
            resultado="pendiente"
        )
        
        return {
            "exito": True,
            "solicitud_id": solicitud_id,
            "mensaje": "Solicitud de registro creada. Pendiente de revisión CMF."
        }
    
    def aprobar_solicitud(
        self,
        solicitud_id: str,
        numero_registro_cmf: str,
        nivel_seguridad: NivelSeguridad,
        aprobador_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Aprueba una solicitud de registro y crea el participante"""
        if solicitud_id not in self.solicitudes:
            return {"exito": False, "error": "Solicitud no encontrada"}
        
        solicitud = self.solicitudes[solicitud_id]
        
        if solicitud.estado != "pendiente":
            return {"exito": False, "error": f"Solicitud ya procesada: {solicitud.estado}"}
        
        # Crear participante
        participante_id = f"PART-{secrets.token_hex(8).upper()}"
        ahora = datetime.now()
        
        participante = Participante(
            id=participante_id,
            rut=solicitud.rut_solicitante,
            razon_social=solicitud.razon_social,
            nombre_fantasia=solicitud.nombre_fantasia,
            tipos=solicitud.tipos_solicitados,
            estado=EstadoParticipante.APROBADO,
            nivel_seguridad=nivel_seguridad,
            fecha_solicitud=solicitud.fecha_solicitud,
            fecha_aprobacion=ahora,
            fecha_activacion=None,
            numero_registro_cmf=numero_registro_cmf,
            servicios_autorizados=solicitud.servicios_solicitados
        )
        
        # Registrar cambio de estado
        participante.historial_estados.append({
            "estado_anterior": None,
            "estado_nuevo": EstadoParticipante.APROBADO.value,
            "fecha": ahora.isoformat(),
            "usuario": aprobador_id,
            "motivo": "Aprobación inicial CMF"
        })
        
        self.participantes[participante_id] = participante
        
        # Actualizar solicitud
        solicitud.estado = "aprobado"
        solicitud.fecha_resolucion = ahora
        solicitud.resuelto_por = aprobador_id
        solicitud.resultado = "aprobado"
        
        # Log auditoría
        self._registrar_log(
            tipo_evento="APROBACION_REGISTRO",
            participante_id=participante_id,
            usuario_id=aprobador_id,
            ip_origen=ip_origen,
            accion="Solicitud aprobada, participante creado",
            detalles={
                "solicitud_id": solicitud_id,
                "numero_registro_cmf": numero_registro_cmf
            },
            resultado="exito"
        )
        
        return {
            "exito": True,
            "participante_id": participante_id,
            "numero_registro_cmf": numero_registro_cmf,
            "mensaje": "Participante aprobado. Pendiente de activación tras registro de certificados."
        }
    
    def activar_participante(
        self,
        participante_id: str,
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Activa un participante aprobado (requiere certificados válidos)"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        participante = self.participantes[participante_id]
        
        if participante.estado != EstadoParticipante.APROBADO:
            return {"exito": False, "error": f"Estado inválido: {participante.estado.value}"}
        
        # Verificar certificados
        if not participante.tiene_certificado_vigente(TipoCertificado.QWAC):
            return {"exito": False, "error": "Requiere certificado QWAC vigente"}
        
        if not participante.tiene_certificado_vigente(TipoCertificado.QSEAL):
            return {"exito": False, "error": "Requiere certificado QSEAL vigente"}
        
        # Verificar endpoints
        if not participante.endpoints:
            return {"exito": False, "error": "Requiere al menos un endpoint registrado"}
        
        # Activar
        ahora = datetime.now()
        estado_anterior = participante.estado
        participante.estado = EstadoParticipante.ACTIVO
        participante.fecha_activacion = ahora
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        participante.historial_estados.append({
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": EstadoParticipante.ACTIVO.value,
            "fecha": ahora.isoformat(),
            "usuario": usuario_id,
            "motivo": "Activación tras verificación de certificados"
        })
        
        # Log auditoría
        self._registrar_log(
            tipo_evento="ACTIVACION_PARTICIPANTE",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion="Participante activado en directorio SFA",
            detalles={"numero_registro_cmf": participante.numero_registro_cmf},
            resultado="exito"
        )
        
        return {
            "exito": True,
            "participante_id": participante_id,
            "fecha_activacion": ahora.isoformat(),
            "mensaje": "Participante activo en el Sistema de Finanzas Abiertas"
        }
    
    def suspender_participante(
        self,
        participante_id: str,
        motivo: str,
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Suspende temporalmente un participante"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        participante = self.participantes[participante_id]
        
        if participante.estado not in [EstadoParticipante.ACTIVO, EstadoParticipante.APROBADO]:
            return {"exito": False, "error": f"No se puede suspender desde estado: {participante.estado.value}"}
        
        ahora = datetime.now()
        estado_anterior = participante.estado
        participante.estado = EstadoParticipante.SUSPENDIDO
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        participante.historial_estados.append({
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": EstadoParticipante.SUSPENDIDO.value,
            "fecha": ahora.isoformat(),
            "usuario": usuario_id,
            "motivo": motivo
        })
        
        self._registrar_log(
            tipo_evento="SUSPENSION_PARTICIPANTE",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=f"Participante suspendido: {motivo}",
            detalles={"motivo": motivo},
            resultado="exito"
        )
        
        return {
            "exito": True,
            "mensaje": "Participante suspendido",
            "fecha_suspension": ahora.isoformat()
        }
    
    def revocar_participante(
        self,
        participante_id: str,
        motivo: str,
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Revoca definitivamente un participante"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        participante = self.participantes[participante_id]
        
        ahora = datetime.now()
        estado_anterior = participante.estado
        participante.estado = EstadoParticipante.REVOCADO
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        # Revocar todos los certificados
        for cert in participante.certificados:
            if cert.estado == "activo":
                cert.estado = "revocado"
                cert.revocado_fecha = ahora
                cert.revocado_razon = f"Revocación de participante: {motivo}"
        
        participante.historial_estados.append({
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": EstadoParticipante.REVOCADO.value,
            "fecha": ahora.isoformat(),
            "usuario": usuario_id,
            "motivo": motivo
        })
        
        self._registrar_log(
            tipo_evento="REVOCACION_PARTICIPANTE",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=f"Participante revocado: {motivo}",
            detalles={"motivo": motivo, "certificados_revocados": len(participante.certificados)},
            resultado="exito"
        )
        
        return {
            "exito": True,
            "mensaje": "Participante revocado definitivamente",
            "fecha_revocacion": ahora.isoformat()
        }
    
    # -------------------------------------------------------------------------
    # GESTIÓN DE CERTIFICADOS
    # -------------------------------------------------------------------------
    
    def registrar_certificado(
        self,
        participante_id: str,
        tipo: TipoCertificado,
        pem_encoded: str,
        roles_autorizados: List[TipoParticipante],
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Registra un nuevo certificado para un participante"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        participante = self.participantes[participante_id]
        
        # Simular extracción de datos del certificado
        # En producción, usar cryptography library
        cert_id = f"CERT-{secrets.token_hex(8).upper()}"
        thumbprint = hashlib.sha256(pem_encoded.encode()).hexdigest()
        ahora = datetime.now()
        
        certificado = CertificadoParticipante(
            id=cert_id,
            tipo=tipo,
            thumbprint_sha256=thumbprint,
            subject_dn=f"CN={participante.nombre_fantasia}, O={participante.razon_social}, C=CL",
            issuer_dn="CN=CMF Chile CA, O=CMF, C=CL",
            serial_number=secrets.token_hex(16).upper(),
            fecha_emision=ahora,
            fecha_expiracion=ahora + timedelta(days=365),  # 1 año
            pem_encoded=pem_encoded,
            roles_autorizados=roles_autorizados
        )
        
        participante.certificados.append(certificado)
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        self._registrar_log(
            tipo_evento="REGISTRO_CERTIFICADO",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=f"Certificado {tipo.value} registrado",
            detalles={
                "cert_id": cert_id,
                "tipo": tipo.value,
                "thumbprint": thumbprint[:16] + "..."
            },
            resultado="exito"
        )
        
        return {
            "exito": True,
            "cert_id": cert_id,
            "thumbprint": thumbprint,
            "expiracion": certificado.fecha_expiracion.isoformat()
        }
    
    def revocar_certificado(
        self,
        participante_id: str,
        cert_id: str,
        razon: str,
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Revoca un certificado específico"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        participante = self.participantes[participante_id]
        certificado = next((c for c in participante.certificados if c.id == cert_id), None)
        
        if not certificado:
            return {"exito": False, "error": "Certificado no encontrado"}
        
        if certificado.estado != "activo":
            return {"exito": False, "error": f"Certificado ya está: {certificado.estado}"}
        
        ahora = datetime.now()
        certificado.estado = "revocado"
        certificado.revocado_fecha = ahora
        certificado.revocado_razon = razon
        
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        self._registrar_log(
            tipo_evento="REVOCACION_CERTIFICADO",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=f"Certificado {cert_id} revocado",
            detalles={"cert_id": cert_id, "razon": razon},
            resultado="exito"
        )
        
        return {
            "exito": True,
            "mensaje": "Certificado revocado",
            "fecha_revocacion": ahora.isoformat()
        }
    
    # -------------------------------------------------------------------------
    # GESTIÓN DE ENDPOINTS
    # -------------------------------------------------------------------------
    
    def registrar_endpoint(
        self,
        participante_id: str,
        nombre: str,
        url_base: str,
        version_api: str,
        servicios: List[CategoriaServicio],
        metodos_auth: List[str],
        usuario_id: str,
        ip_origen: str
    ) -> Dict[str, Any]:
        """Registra un nuevo endpoint API para un participante"""
        if participante_id not in self.participantes:
            return {"exito": False, "error": "Participante no encontrado"}
        
        # Validar URL
        validacion_url = self.validador.validar_url(url_base)
        if not validacion_url["valido"]:
            return {"exito": False, "error": validacion_url["error"]}
        
        participante = self.participantes[participante_id]
        
        endpoint_id = f"EP-{secrets.token_hex(6).upper()}"
        ahora = datetime.now()
        
        endpoint = EndpointAPI(
            id=endpoint_id,
            nombre=nombre,
            url_base=url_base,
            url_well_known=f"{url_base}/.well-known/openid-configuration",
            version_api=version_api,
            servicios_soportados=servicios,
            metodos_autenticacion=metodos_auth,
            fecha_registro=ahora
        )
        
        participante.endpoints.append(endpoint)
        participante.ultima_actualizacion = ahora
        participante.actualizado_por = usuario_id
        
        self._registrar_log(
            tipo_evento="REGISTRO_ENDPOINT",
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=f"Endpoint {nombre} registrado",
            detalles={
                "endpoint_id": endpoint_id,
                "url_base": url_base,
                "servicios": [s.value for s in servicios]
            },
            resultado="exito"
        )
        
        return {
            "exito": True,
            "endpoint_id": endpoint_id,
            "url_well_known": endpoint.url_well_known
        }
    
    # -------------------------------------------------------------------------
    # CONSULTAS AL DIRECTORIO
    # -------------------------------------------------------------------------
    
    def buscar_participantes(
        self,
        tipos: Optional[List[TipoParticipante]] = None,
        servicios: Optional[List[CategoriaServicio]] = None,
        estado: Optional[EstadoParticipante] = None,
        solo_activos: bool = True
    ) -> List[Dict[str, Any]]:
        """Busca participantes según criterios"""
        resultados = []
        
        for p in self.participantes.values():
            # Filtro por estado
            if solo_activos and p.estado != EstadoParticipante.ACTIVO:
                continue
            if estado and p.estado != estado:
                continue
            
            # Filtro por tipos
            if tipos and not any(t in p.tipos for t in tipos):
                continue
            
            # Filtro por servicios
            if servicios and not any(s in p.servicios_autorizados for s in servicios):
                continue
            
            resultados.append(self._participante_a_dict_publico(p))
        
        return resultados
    
    def obtener_participante(self, participante_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un participante específico"""
        if participante_id not in self.participantes:
            return None
        return self._participante_a_dict_publico(self.participantes[participante_id])
    
    def obtener_participante_por_rut(self, rut: str) -> Optional[Dict[str, Any]]:
        """Busca participante por RUT"""
        for p in self.participantes.values():
            if p.rut == rut:
                return self._participante_a_dict_publico(p)
        return None
    
    def verificar_certificado(self, thumbprint: str) -> Dict[str, Any]:
        """Verifica un certificado por su thumbprint"""
        for p in self.participantes.values():
            for cert in p.certificados:
                if cert.thumbprint_sha256 == thumbprint:
                    return {
                        "encontrado": True,
                        "participante_id": p.id,
                        "participante_nombre": p.nombre_fantasia,
                        "participante_activo": p.esta_activo(),
                        "certificado_vigente": cert.esta_vigente(),
                        "tipo_certificado": cert.tipo.value,
                        "roles": [r.value for r in cert.roles_autorizados],
                        "expiracion": cert.fecha_expiracion.isoformat()
                    }
        
        return {"encontrado": False}
    
    def obtener_endpoints_servicio(
        self,
        servicio: CategoriaServicio
    ) -> List[Dict[str, Any]]:
        """Obtiene todos los endpoints que ofrecen un servicio específico"""
        endpoints = []
        
        for p in self.participantes.values():
            if not p.esta_activo():
                continue
            
            for ep in p.endpoints:
                if ep.estado == "activo" and servicio in ep.servicios_soportados:
                    endpoints.append({
                        "participante_id": p.id,
                        "participante_nombre": p.nombre_fantasia,
                        "endpoint_id": ep.id,
                        "url_base": ep.url_base,
                        "url_well_known": ep.url_well_known,
                        "version_api": ep.version_api,
                        "disponibilidad": ep.disponibilidad_porcentaje
                    })
        
        return endpoints
    
    # -------------------------------------------------------------------------
    # ESTADÍSTICAS Y MÉTRICAS
    # -------------------------------------------------------------------------
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas del directorio"""
        total = len(self.participantes)
        por_estado = {}
        por_tipo = {}
        por_servicio = {}
        
        for p in self.participantes.values():
            # Por estado
            estado = p.estado.value
            por_estado[estado] = por_estado.get(estado, 0) + 1
            
            # Por tipo
            for t in p.tipos:
                tipo = t.value
                por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
            
            # Por servicio
            for s in p.servicios_autorizados:
                servicio = s.value
                por_servicio[servicio] = por_servicio.get(servicio, 0) + 1
        
        # Certificados próximos a expirar (30 días)
        certs_por_expirar = []
        for p in self.participantes.values():
            for cert in p.certificados:
                if cert.esta_vigente() and cert.dias_hasta_expiracion() < 30:
                    certs_por_expirar.append({
                        "participante_id": p.id,
                        "cert_id": cert.id,
                        "tipo": cert.tipo.value,
                        "dias_restantes": cert.dias_hasta_expiracion()
                    })
        
        return {
            "total_participantes": total,
            "por_estado": por_estado,
            "por_tipo": por_tipo,
            "por_servicio": por_servicio,
            "certificados_proximos_expirar": certs_por_expirar,
            "solicitudes_pendientes": len([s for s in self.solicitudes.values() if s.estado == "pendiente"]),
            "fecha_consulta": datetime.now().isoformat()
        }
    
    # -------------------------------------------------------------------------
    # MÉTODOS AUXILIARES PRIVADOS
    # -------------------------------------------------------------------------
    
    def _participante_a_dict_publico(self, p: Participante) -> Dict[str, Any]:
        """Convierte participante a diccionario para exposición pública"""
        return {
            "id": p.id,
            "rut": p.rut,
            "razon_social": p.razon_social,
            "nombre_fantasia": p.nombre_fantasia,
            "tipos": [t.value for t in p.tipos],
            "estado": p.estado.value,
            "nivel_seguridad": p.nivel_seguridad.value,
            "numero_registro_cmf": p.numero_registro_cmf,
            "servicios_autorizados": [s.value for s in p.servicios_autorizados],
            "fecha_activacion": p.fecha_activacion.isoformat() if p.fecha_activacion else None,
            "endpoints": [
                {
                    "id": ep.id,
                    "url_base": ep.url_base,
                    "version_api": ep.version_api,
                    "servicios": [s.value for s in ep.servicios_soportados]
                }
                for ep in p.endpoints if ep.estado == "activo"
            ],
            "certificados_vigentes": [
                {
                    "tipo": c.tipo.value,
                    "expiracion": c.fecha_expiracion.isoformat()
                }
                for c in p.certificados if c.esta_vigente()
            ],
            "sitio_web": p.sitio_web,
            "logo_url": p.logo_url
        }
    
    def _registrar_log(
        self,
        tipo_evento: str,
        participante_id: Optional[str],
        usuario_id: str,
        ip_origen: str,
        accion: str,
        detalles: Dict,
        resultado: str
    ):
        """Registra evento en log de auditoría"""
        log = AuditLogDirectorio(
            id=f"LOG-{secrets.token_hex(8).upper()}",
            timestamp=datetime.now(),
            tipo_evento=tipo_evento,
            participante_id=participante_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen,
            accion=accion,
            detalles=detalles,
            resultado=resultado
        )
        self.logs_auditoria.append(log)


# ============================================================================
# CLIENTE DEL DIRECTORIO (PARA TPPs)
# ============================================================================

class ClienteDirectorio:
    """
    Cliente para consultar el Directorio de Participantes
    Para uso de TPPs (Third Party Providers)
    """
    
    def __init__(self, url_directorio: str, cert_path: str, key_path: str):
        self.url_directorio = url_directorio
        self.cert_path = cert_path
        self.key_path = key_path
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hora
    
    def buscar_aspsp(
        self,
        servicio: Optional[CategoriaServicio] = None
    ) -> List[Dict[str, Any]]:
        """Busca ASPSPs (bancos/cooperativas) en el directorio"""
        # En producción: llamada HTTP con mTLS
        # Simulación para desarrollo
        return [
            {
                "id": "ASPSP-001",
                "nombre": "Banco de Chile",
                "url_base": "https://api.bancochile.cl/openbanking/v1",
                "servicios": ["AIS", "PIS"]
            },
            {
                "id": "ASPSP-002",
                "nombre": "Banco Santander",
                "url_base": "https://api.santander.cl/openbanking/v1",
                "servicios": ["AIS", "PIS"]
            },
            {
                "id": "ASPSP-003",
                "nombre": "BancoEstado",
                "url_base": "https://api.bancoestado.cl/openbanking/v1",
                "servicios": ["AIS"]
            }
        ]
    
    def verificar_participante(self, participante_id: str) -> Dict[str, Any]:
        """Verifica que un participante esté activo en el directorio"""
        # En producción: verificación en tiempo real
        return {
            "activo": True,
            "tipos": ["ASPSP"],
            "certificado_valido": True,
            "ultima_verificacion": datetime.now().isoformat()
        }
    
    def obtener_well_known(self, participante_id: str) -> Dict[str, Any]:
        """Obtiene la configuración OpenID del participante"""
        # En producción: fetch del endpoint .well-known
        return {
            "issuer": f"https://api.ejemplo.cl",
            "authorization_endpoint": f"https://api.ejemplo.cl/oauth/authorize",
            "token_endpoint": f"https://api.ejemplo.cl/oauth/token",
            "pushed_authorization_request_endpoint": f"https://api.ejemplo.cl/oauth/par",
            "jwks_uri": f"https://api.ejemplo.cl/.well-known/jwks.json",
            "registration_endpoint": f"https://api.ejemplo.cl/oauth/register",
            "scopes_supported": ["openid", "accounts", "payments"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["private_key_jwt", "tls_client_auth"],
            "tls_client_certificate_bound_access_tokens": True,
            "dpop_signing_alg_values_supported": ["PS256", "ES256"]
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Crear directorio
    directorio = DirectorioParticipantes()
    
    # Simular registro de participante
    resultado_registro = directorio.registrar_participante(
        rut="96.000.000-1",
        razon_social="FinTech Ejemplo S.A.",
        nombre_fantasia="EjemploFintech",
        tipos=[TipoParticipante.AISP, TipoParticipante.PISP],
        servicios=[CategoriaServicio.AIS, CategoriaServicio.PIS],
        contacto_principal=ContactoParticipante(
            nombre_contacto="Juan Pérez",
            cargo="CTO",
            email="juan.perez@ejemplo.cl",
            telefono="+56912345678",
            tipo_contacto="tecnico",
            es_principal=True
        ),
        usuario_id="admin-001",
        ip_origen="192.168.1.1"
    )
    
    print("Registro:", json.dumps(resultado_registro, indent=2, ensure_ascii=False))
    
    # Aprobar solicitud
    if resultado_registro["exito"]:
        aprobacion = directorio.aprobar_solicitud(
            solicitud_id=resultado_registro["solicitud_id"],
            numero_registro_cmf="REG-2026-001",
            nivel_seguridad=NivelSeguridad.AVANZADO,
            aprobador_id="cmf-admin-001",
            ip_origen="10.0.0.1"
        )
        print("Aprobación:", json.dumps(aprobacion, indent=2, ensure_ascii=False))
    
    # Estadísticas
    stats = directorio.obtener_estadisticas()
    print("Estadísticas:", json.dumps(stats, indent=2, ensure_ascii=False))
