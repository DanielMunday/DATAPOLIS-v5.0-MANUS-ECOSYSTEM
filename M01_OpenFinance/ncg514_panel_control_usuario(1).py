"""
DATAPOLIS v3.0 - NCG 514 PANEL DE CONTROL DE USUARIO
====================================================
Dashboard para gestión de consentimientos y accesos del usuario final
Según NCG 514 CMF Chile Art. 12-15 - Deadline Abril 2026

Autor: DATAPOLIS SpA
Versión: 1.0.0
Fecha: 2026-02-01
Normativa: NCG 514 CMF - Sistema de Finanzas Abiertas Chile
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Set, Callable
from enum import Enum
import hashlib
import secrets
import json
from abc import ABC, abstractmethod


# ============================================================================
# ENUMERACIONES
# ============================================================================

class TipoNotificacion(Enum):
    """Tipos de notificaciones al usuario"""
    CONSENTIMIENTO_CREADO = "consentimiento_creado"
    CONSENTIMIENTO_RENOVADO = "consentimiento_renovado"
    CONSENTIMIENTO_PROXIMO_EXPIRAR = "consentimiento_proximo_expirar"
    CONSENTIMIENTO_EXPIRADO = "consentimiento_expirado"
    CONSENTIMIENTO_REVOCADO = "consentimiento_revocado"
    ACCESO_DATOS = "acceso_datos"
    PAGO_INICIADO = "pago_iniciado"
    PAGO_COMPLETADO = "pago_completado"
    PAGO_FALLIDO = "pago_fallido"
    ALERTA_SEGURIDAD = "alerta_seguridad"
    NUEVO_TPP_AUTORIZADO = "nuevo_tpp_autorizado"
    ACTUALIZACION_TERMINOS = "actualizacion_terminos"


class PrioridadNotificacion(Enum):
    """Prioridad de notificaciones"""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class CanalNotificacion(Enum):
    """Canales de notificación"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"


class EstadoConsentimiento(Enum):
    """Estados de consentimiento para dashboard"""
    ACTIVO = "activo"
    PENDIENTE = "pendiente"
    EXPIRADO = "expirado"
    REVOCADO = "revocado"
    SUSPENDIDO = "suspendido"


class TipoAcceso(Enum):
    """Tipos de acceso a datos"""
    CONSULTA_SALDOS = "consulta_saldos"
    CONSULTA_MOVIMIENTOS = "consulta_movimientos"
    CONSULTA_PRODUCTOS = "consulta_productos"
    INICIACION_PAGO = "iniciacion_pago"
    CONFIRMACION_FONDOS = "confirmacion_fondos"


# ============================================================================
# DATACLASSES - ESTRUCTURAS DEL PANEL
# ============================================================================

@dataclass
class PreferenciasNotificacion:
    """Preferencias de notificación del usuario"""
    usuario_id: str
    canales_habilitados: List[CanalNotificacion] = field(default_factory=lambda: [
        CanalNotificacion.EMAIL,
        CanalNotificacion.IN_APP
    ])
    notificaciones_habilitadas: Dict[TipoNotificacion, bool] = field(default_factory=dict)
    horario_no_molestar_inicio: Optional[str] = "22:00"
    horario_no_molestar_fin: Optional[str] = "08:00"
    idioma: str = "es"
    
    def __post_init__(self):
        # Habilitar todas las notificaciones por defecto
        for tipo in TipoNotificacion:
            if tipo not in self.notificaciones_habilitadas:
                self.notificaciones_habilitadas[tipo] = True


@dataclass
class Notificacion:
    """Notificación para el usuario"""
    id: str
    usuario_id: str
    tipo: TipoNotificacion
    prioridad: PrioridadNotificacion
    titulo: str
    mensaje: str
    fecha_creacion: datetime
    fecha_lectura: Optional[datetime] = None
    leida: bool = False
    datos_adicionales: Dict[str, Any] = field(default_factory=dict)
    acciones_disponibles: List[Dict[str, str]] = field(default_factory=list)
    canal_enviado: Optional[CanalNotificacion] = None
    
    def marcar_leida(self):
        self.leida = True
        self.fecha_lectura = datetime.now()


@dataclass
class ResumenConsentimiento:
    """Resumen de consentimiento para dashboard"""
    id: str
    tpp_id: str
    tpp_nombre: str
    tpp_logo_url: Optional[str]
    estado: EstadoConsentimiento
    fecha_creacion: datetime
    fecha_expiracion: datetime
    alcances: List[str]
    instituciones_conectadas: List[Dict[str, str]]
    ultimo_acceso: Optional[datetime]
    total_accesos: int
    puede_revocar: bool = True
    puede_renovar: bool = True


@dataclass
class RegistroAcceso:
    """Registro de acceso a datos del usuario"""
    id: str
    consentimiento_id: str
    tpp_id: str
    tpp_nombre: str
    tipo_acceso: TipoAcceso
    timestamp: datetime
    institucion_origen: str
    datos_accedidos: List[str]
    ip_origen: str
    user_agent: Optional[str]
    exitoso: bool
    detalle_error: Optional[str] = None


@dataclass
class OperacionPago:
    """Operación de pago iniciada vía Open Finance"""
    id: str
    consentimiento_id: str
    tpp_id: str
    tpp_nombre: str
    fecha_iniciacion: datetime
    fecha_ejecucion: Optional[datetime]
    monto: float
    moneda: str
    cuenta_origen: str
    cuenta_destino: str
    descripcion: str
    estado: str  # pendiente, completado, fallido, cancelado
    referencia_bancaria: Optional[str] = None
    puede_cancelar: bool = False


@dataclass
class AlertaSeguridad:
    """Alerta de seguridad para el usuario"""
    id: str
    usuario_id: str
    tipo: str  # acceso_sospechoso, multiples_intentos, cambio_dispositivo
    severidad: str  # baja, media, alta, critica
    titulo: str
    descripcion: str
    timestamp: datetime
    ip_origen: Optional[str]
    ubicacion_aproximada: Optional[str]
    dispositivo: Optional[str]
    resuelta: bool = False
    acciones_tomadas: List[str] = field(default_factory=list)


@dataclass
class EstadisticasUsuario:
    """Estadísticas de uso del usuario"""
    usuario_id: str
    total_consentimientos_activos: int
    total_consentimientos_historicos: int
    total_tpps_conectados: int
    total_accesos_mes: int
    total_pagos_mes: int
    monto_total_pagos_mes: float
    instituciones_conectadas: List[str]
    ultimo_acceso_general: Optional[datetime]
    fecha_calculo: datetime = field(default_factory=datetime.now)


# ============================================================================
# PANEL DE CONTROL DEL USUARIO
# ============================================================================

class PanelControlUsuario:
    """
    Panel de Control para usuarios finales del Sistema de Finanzas Abiertas.
    Según NCG 514 CMF Chile Art. 12-15
    
    Proporciona:
    - Vista consolidada de consentimientos
    - Gestión de revocación inmediata (Art. 15)
    - Historial de accesos a datos
    - Registro de operaciones de pago
    - Notificaciones y alertas
    - Preferencias de privacidad
    """
    
    def __init__(self):
        self.consentimientos: Dict[str, Dict[str, Any]] = {}  # usuario_id -> {consent_id -> consent}
        self.accesos: Dict[str, List[RegistroAcceso]] = {}  # usuario_id -> [accesos]
        self.pagos: Dict[str, List[OperacionPago]] = {}  # usuario_id -> [pagos]
        self.notificaciones: Dict[str, List[Notificacion]] = {}  # usuario_id -> [notificaciones]
        self.alertas: Dict[str, List[AlertaSeguridad]] = {}  # usuario_id -> [alertas]
        self.preferencias: Dict[str, PreferenciasNotificacion] = {}  # usuario_id -> preferencias
        self._callbacks_notificacion: List[Callable] = []
    
    # -------------------------------------------------------------------------
    # GESTIÓN DE CONSENTIMIENTOS
    # -------------------------------------------------------------------------
    
    def obtener_consentimientos_activos(self, usuario_id: str) -> List[ResumenConsentimiento]:
        """
        Obtiene todos los consentimientos activos del usuario.
        NCG 514 Art. 14: Usuario debe poder ver sus consentimientos vigentes.
        """
        if usuario_id not in self.consentimientos:
            return []
        
        activos = []
        ahora = datetime.now()
        
        for consent_id, consent in self.consentimientos[usuario_id].items():
            if consent["estado"] == EstadoConsentimiento.ACTIVO:
                # Calcular total de accesos
                total_accesos = len([
                    a for a in self.accesos.get(usuario_id, [])
                    if a.consentimiento_id == consent_id
                ])
                
                # Último acceso
                accesos_consent = [
                    a for a in self.accesos.get(usuario_id, [])
                    if a.consentimiento_id == consent_id
                ]
                ultimo_acceso = max(
                    (a.timestamp for a in accesos_consent),
                    default=None
                )
                
                resumen = ResumenConsentimiento(
                    id=consent_id,
                    tpp_id=consent["tpp_id"],
                    tpp_nombre=consent["tpp_nombre"],
                    tpp_logo_url=consent.get("tpp_logo_url"),
                    estado=EstadoConsentimiento.ACTIVO,
                    fecha_creacion=consent["fecha_creacion"],
                    fecha_expiracion=consent["fecha_expiracion"],
                    alcances=consent["alcances"],
                    instituciones_conectadas=consent.get("instituciones", []),
                    ultimo_acceso=ultimo_acceso,
                    total_accesos=total_accesos
                )
                activos.append(resumen)
        
        return sorted(activos, key=lambda x: x.fecha_creacion, reverse=True)
    
    def obtener_historial_consentimientos(
        self,
        usuario_id: str,
        incluir_activos: bool = True,
        incluir_revocados: bool = True,
        incluir_expirados: bool = True
    ) -> List[ResumenConsentimiento]:
        """Obtiene historial completo de consentimientos"""
        if usuario_id not in self.consentimientos:
            return []
        
        historial = []
        estados_incluir = set()
        
        if incluir_activos:
            estados_incluir.add(EstadoConsentimiento.ACTIVO)
        if incluir_revocados:
            estados_incluir.add(EstadoConsentimiento.REVOCADO)
        if incluir_expirados:
            estados_incluir.add(EstadoConsentimiento.EXPIRADO)
        
        for consent_id, consent in self.consentimientos[usuario_id].items():
            if consent["estado"] in estados_incluir:
                resumen = ResumenConsentimiento(
                    id=consent_id,
                    tpp_id=consent["tpp_id"],
                    tpp_nombre=consent["tpp_nombre"],
                    tpp_logo_url=consent.get("tpp_logo_url"),
                    estado=consent["estado"],
                    fecha_creacion=consent["fecha_creacion"],
                    fecha_expiracion=consent["fecha_expiracion"],
                    alcances=consent["alcances"],
                    instituciones_conectadas=consent.get("instituciones", []),
                    ultimo_acceso=consent.get("ultimo_acceso"),
                    total_accesos=consent.get("total_accesos", 0),
                    puede_revocar=consent["estado"] == EstadoConsentimiento.ACTIVO,
                    puede_renovar=consent["estado"] == EstadoConsentimiento.ACTIVO
                )
                historial.append(resumen)
        
        return sorted(historial, key=lambda x: x.fecha_creacion, reverse=True)
    
    def revocar_consentimiento(
        self,
        usuario_id: str,
        consentimiento_id: str,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoca un consentimiento con efecto inmediato.
        NCG 514 Art. 15: Revocación debe ser inmediata.
        """
        if usuario_id not in self.consentimientos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        if consentimiento_id not in self.consentimientos[usuario_id]:
            return {"exito": False, "error": "Consentimiento no encontrado"}
        
        consent = self.consentimientos[usuario_id][consentimiento_id]
        
        if consent["estado"] != EstadoConsentimiento.ACTIVO:
            return {"exito": False, "error": f"Consentimiento ya está: {consent['estado'].value}"}
        
        # Revocar inmediatamente
        ahora = datetime.now()
        consent["estado"] = EstadoConsentimiento.REVOCADO
        consent["fecha_revocacion"] = ahora
        consent["motivo_revocacion"] = motivo or "Revocado por el usuario"
        
        # Crear notificación
        self._crear_notificacion(
            usuario_id=usuario_id,
            tipo=TipoNotificacion.CONSENTIMIENTO_REVOCADO,
            prioridad=PrioridadNotificacion.ALTA,
            titulo="Consentimiento revocado",
            mensaje=f"Has revocado el acceso de {consent['tpp_nombre']} a tus datos financieros.",
            datos_adicionales={
                "consentimiento_id": consentimiento_id,
                "tpp_nombre": consent["tpp_nombre"]
            }
        )
        
        return {
            "exito": True,
            "mensaje": "Consentimiento revocado exitosamente",
            "fecha_revocacion": ahora.isoformat(),
            "efecto_inmediato": True
        }
    
    def revocar_todos_tpp(
        self,
        usuario_id: str,
        tpp_id: str,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Revoca todos los consentimientos de un TPP específico"""
        if usuario_id not in self.consentimientos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        revocados = 0
        for consent_id, consent in self.consentimientos[usuario_id].items():
            if consent["tpp_id"] == tpp_id and consent["estado"] == EstadoConsentimiento.ACTIVO:
                resultado = self.revocar_consentimiento(
                    usuario_id, consent_id, motivo or f"Revocación masiva TPP: {tpp_id}"
                )
                if resultado["exito"]:
                    revocados += 1
        
        return {
            "exito": True,
            "consentimientos_revocados": revocados,
            "tpp_id": tpp_id
        }
    
    def renovar_consentimiento(
        self,
        usuario_id: str,
        consentimiento_id: str,
        nueva_duracion_dias: int = 365
    ) -> Dict[str, Any]:
        """
        Renueva un consentimiento existente.
        NCG 514: Máximo 365 días.
        """
        if nueva_duracion_dias > 365:
            return {"exito": False, "error": "Duración máxima es 365 días según NCG 514"}
        
        if usuario_id not in self.consentimientos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        if consentimiento_id not in self.consentimientos[usuario_id]:
            return {"exito": False, "error": "Consentimiento no encontrado"}
        
        consent = self.consentimientos[usuario_id][consentimiento_id]
        
        if consent["estado"] != EstadoConsentimiento.ACTIVO:
            return {"exito": False, "error": "Solo se pueden renovar consentimientos activos"}
        
        ahora = datetime.now()
        nueva_expiracion = ahora + timedelta(days=nueva_duracion_dias)
        
        consent["fecha_expiracion"] = nueva_expiracion
        consent["fecha_renovacion"] = ahora
        consent["renovaciones"] = consent.get("renovaciones", 0) + 1
        
        # Notificación
        self._crear_notificacion(
            usuario_id=usuario_id,
            tipo=TipoNotificacion.CONSENTIMIENTO_RENOVADO,
            prioridad=PrioridadNotificacion.MEDIA,
            titulo="Consentimiento renovado",
            mensaje=f"El acceso de {consent['tpp_nombre']} ha sido renovado hasta {nueva_expiracion.strftime('%d/%m/%Y')}.",
            datos_adicionales={
                "consentimiento_id": consentimiento_id,
                "nueva_expiracion": nueva_expiracion.isoformat()
            }
        )
        
        return {
            "exito": True,
            "nueva_expiracion": nueva_expiracion.isoformat(),
            "dias_agregados": nueva_duracion_dias
        }
    
    # -------------------------------------------------------------------------
    # HISTORIAL DE ACCESOS
    # -------------------------------------------------------------------------
    
    def registrar_acceso(
        self,
        usuario_id: str,
        consentimiento_id: str,
        tpp_id: str,
        tpp_nombre: str,
        tipo_acceso: TipoAcceso,
        institucion_origen: str,
        datos_accedidos: List[str],
        ip_origen: str,
        user_agent: Optional[str] = None,
        exitoso: bool = True,
        detalle_error: Optional[str] = None
    ) -> RegistroAcceso:
        """Registra un acceso a datos del usuario"""
        if usuario_id not in self.accesos:
            self.accesos[usuario_id] = []
        
        acceso = RegistroAcceso(
            id=f"ACC-{secrets.token_hex(8).upper()}",
            consentimiento_id=consentimiento_id,
            tpp_id=tpp_id,
            tpp_nombre=tpp_nombre,
            tipo_acceso=tipo_acceso,
            timestamp=datetime.now(),
            institucion_origen=institucion_origen,
            datos_accedidos=datos_accedidos,
            ip_origen=ip_origen,
            user_agent=user_agent,
            exitoso=exitoso,
            detalle_error=detalle_error
        )
        
        self.accesos[usuario_id].append(acceso)
        
        # Notificación si está habilitada
        prefs = self.preferencias.get(usuario_id)
        if prefs and prefs.notificaciones_habilitadas.get(TipoNotificacion.ACCESO_DATOS, True):
            self._crear_notificacion(
                usuario_id=usuario_id,
                tipo=TipoNotificacion.ACCESO_DATOS,
                prioridad=PrioridadNotificacion.BAJA,
                titulo="Acceso a tus datos",
                mensaje=f"{tpp_nombre} accedió a {', '.join(datos_accedidos)} en {institucion_origen}.",
                datos_adicionales={
                    "acceso_id": acceso.id,
                    "tipo": tipo_acceso.value
                }
            )
        
        return acceso
    
    def obtener_historial_accesos(
        self,
        usuario_id: str,
        consentimiento_id: Optional[str] = None,
        tpp_id: Optional[str] = None,
        tipo_acceso: Optional[TipoAcceso] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limite: int = 100
    ) -> List[RegistroAcceso]:
        """Obtiene historial de accesos filtrado"""
        if usuario_id not in self.accesos:
            return []
        
        accesos = self.accesos[usuario_id]
        
        # Aplicar filtros
        if consentimiento_id:
            accesos = [a for a in accesos if a.consentimiento_id == consentimiento_id]
        
        if tpp_id:
            accesos = [a for a in accesos if a.tpp_id == tpp_id]
        
        if tipo_acceso:
            accesos = [a for a in accesos if a.tipo_acceso == tipo_acceso]
        
        if desde:
            accesos = [a for a in accesos if a.timestamp >= desde]
        
        if hasta:
            accesos = [a for a in accesos if a.timestamp <= hasta]
        
        # Ordenar por fecha descendente y limitar
        accesos = sorted(accesos, key=lambda x: x.timestamp, reverse=True)[:limite]
        
        return accesos
    
    def obtener_resumen_accesos(
        self,
        usuario_id: str,
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """Obtiene resumen de accesos del período"""
        desde = datetime.now() - timedelta(days=periodo_dias)
        accesos = self.obtener_historial_accesos(usuario_id, desde=desde)
        
        # Agrupar por TPP
        por_tpp = {}
        for acc in accesos:
            if acc.tpp_nombre not in por_tpp:
                por_tpp[acc.tpp_nombre] = {"total": 0, "tipos": {}}
            por_tpp[acc.tpp_nombre]["total"] += 1
            tipo = acc.tipo_acceso.value
            por_tpp[acc.tpp_nombre]["tipos"][tipo] = por_tpp[acc.tpp_nombre]["tipos"].get(tipo, 0) + 1
        
        # Agrupar por tipo
        por_tipo = {}
        for acc in accesos:
            tipo = acc.tipo_acceso.value
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        
        return {
            "periodo_dias": periodo_dias,
            "total_accesos": len(accesos),
            "accesos_exitosos": len([a for a in accesos if a.exitoso]),
            "accesos_fallidos": len([a for a in accesos if not a.exitoso]),
            "por_tpp": por_tpp,
            "por_tipo": por_tipo
        }
    
    # -------------------------------------------------------------------------
    # OPERACIONES DE PAGO
    # -------------------------------------------------------------------------
    
    def registrar_pago(
        self,
        usuario_id: str,
        consentimiento_id: str,
        tpp_id: str,
        tpp_nombre: str,
        monto: float,
        moneda: str,
        cuenta_origen: str,
        cuenta_destino: str,
        descripcion: str
    ) -> OperacionPago:
        """Registra una operación de pago iniciada vía PIS"""
        if usuario_id not in self.pagos:
            self.pagos[usuario_id] = []
        
        pago = OperacionPago(
            id=f"PAY-{secrets.token_hex(8).upper()}",
            consentimiento_id=consentimiento_id,
            tpp_id=tpp_id,
            tpp_nombre=tpp_nombre,
            fecha_iniciacion=datetime.now(),
            fecha_ejecucion=None,
            monto=monto,
            moneda=moneda,
            cuenta_origen=cuenta_origen,
            cuenta_destino=cuenta_destino,
            descripcion=descripcion,
            estado="pendiente",
            puede_cancelar=True
        )
        
        self.pagos[usuario_id].append(pago)
        
        # Notificación
        self._crear_notificacion(
            usuario_id=usuario_id,
            tipo=TipoNotificacion.PAGO_INICIADO,
            prioridad=PrioridadNotificacion.ALTA,
            titulo="Pago iniciado",
            mensaje=f"{tpp_nombre} ha iniciado un pago de ${monto:,.0f} {moneda}.",
            datos_adicionales={
                "pago_id": pago.id,
                "monto": monto,
                "destino": cuenta_destino
            },
            acciones_disponibles=[
                {"accion": "ver_detalle", "label": "Ver detalle"},
                {"accion": "cancelar", "label": "Cancelar pago"}
            ]
        )
        
        return pago
    
    def actualizar_estado_pago(
        self,
        usuario_id: str,
        pago_id: str,
        nuevo_estado: str,
        referencia_bancaria: Optional[str] = None
    ) -> Dict[str, Any]:
        """Actualiza el estado de un pago"""
        if usuario_id not in self.pagos:
            return {"exito": False, "error": "Usuario no encontrado"}
        
        pago = next((p for p in self.pagos[usuario_id] if p.id == pago_id), None)
        if not pago:
            return {"exito": False, "error": "Pago no encontrado"}
        
        pago.estado = nuevo_estado
        if nuevo_estado == "completado":
            pago.fecha_ejecucion = datetime.now()
            pago.puede_cancelar = False
            if referencia_bancaria:
                pago.referencia_bancaria = referencia_bancaria
            
            tipo_notif = TipoNotificacion.PAGO_COMPLETADO
            mensaje = f"Tu pago de ${pago.monto:,.0f} {pago.moneda} se completó exitosamente."
        elif nuevo_estado == "fallido":
            pago.puede_cancelar = False
            tipo_notif = TipoNotificacion.PAGO_FALLIDO
            mensaje = f"El pago de ${pago.monto:,.0f} {pago.moneda} no pudo completarse."
        else:
            return {"exito": True, "estado": nuevo_estado}
        
        # Notificación de estado
        self._crear_notificacion(
            usuario_id=usuario_id,
            tipo=tipo_notif,
            prioridad=PrioridadNotificacion.ALTA,
            titulo=f"Pago {nuevo_estado}",
            mensaje=mensaje,
            datos_adicionales={"pago_id": pago_id}
        )
        
        return {"exito": True, "estado": nuevo_estado}
    
    def obtener_historial_pagos(
        self,
        usuario_id: str,
        estado: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        limite: int = 50
    ) -> List[OperacionPago]:
        """Obtiene historial de pagos"""
        if usuario_id not in self.pagos:
            return []
        
        pagos = self.pagos[usuario_id]
        
        if estado:
            pagos = [p for p in pagos if p.estado == estado]
        if desde:
            pagos = [p for p in pagos if p.fecha_iniciacion >= desde]
        if hasta:
            pagos = [p for p in pagos if p.fecha_iniciacion <= hasta]
        
        return sorted(pagos, key=lambda x: x.fecha_iniciacion, reverse=True)[:limite]
    
    # -------------------------------------------------------------------------
    # NOTIFICACIONES
    # -------------------------------------------------------------------------
    
    def _crear_notificacion(
        self,
        usuario_id: str,
        tipo: TipoNotificacion,
        prioridad: PrioridadNotificacion,
        titulo: str,
        mensaje: str,
        datos_adicionales: Dict[str, Any] = None,
        acciones_disponibles: List[Dict[str, str]] = None
    ) -> Notificacion:
        """Crea y almacena una notificación"""
        if usuario_id not in self.notificaciones:
            self.notificaciones[usuario_id] = []
        
        notif = Notificacion(
            id=f"NOTIF-{secrets.token_hex(6).upper()}",
            usuario_id=usuario_id,
            tipo=tipo,
            prioridad=prioridad,
            titulo=titulo,
            mensaje=mensaje,
            fecha_creacion=datetime.now(),
            datos_adicionales=datos_adicionales or {},
            acciones_disponibles=acciones_disponibles or []
        )
        
        self.notificaciones[usuario_id].append(notif)
        
        # Ejecutar callbacks registrados
        for callback in self._callbacks_notificacion:
            try:
                callback(notif)
            except Exception:
                pass  # No interrumpir por errores en callbacks
        
        return notif
    
    def obtener_notificaciones(
        self,
        usuario_id: str,
        solo_no_leidas: bool = False,
        tipo: Optional[TipoNotificacion] = None,
        limite: int = 50
    ) -> List[Notificacion]:
        """Obtiene notificaciones del usuario"""
        if usuario_id not in self.notificaciones:
            return []
        
        notifs = self.notificaciones[usuario_id]
        
        if solo_no_leidas:
            notifs = [n for n in notifs if not n.leida]
        
        if tipo:
            notifs = [n for n in notifs if n.tipo == tipo]
        
        return sorted(notifs, key=lambda x: x.fecha_creacion, reverse=True)[:limite]
    
    def marcar_notificacion_leida(self, usuario_id: str, notificacion_id: str) -> bool:
        """Marca una notificación como leída"""
        if usuario_id not in self.notificaciones:
            return False
        
        notif = next((n for n in self.notificaciones[usuario_id] if n.id == notificacion_id), None)
        if notif:
            notif.marcar_leida()
            return True
        return False
    
    def marcar_todas_leidas(self, usuario_id: str) -> int:
        """Marca todas las notificaciones como leídas"""
        if usuario_id not in self.notificaciones:
            return 0
        
        count = 0
        for notif in self.notificaciones[usuario_id]:
            if not notif.leida:
                notif.marcar_leida()
                count += 1
        return count
    
    def registrar_callback_notificacion(self, callback: Callable):
        """Registra callback para nuevas notificaciones"""
        self._callbacks_notificacion.append(callback)
    
    # -------------------------------------------------------------------------
    # ALERTAS DE SEGURIDAD
    # -------------------------------------------------------------------------
    
    def crear_alerta_seguridad(
        self,
        usuario_id: str,
        tipo: str,
        severidad: str,
        titulo: str,
        descripcion: str,
        ip_origen: Optional[str] = None,
        ubicacion: Optional[str] = None,
        dispositivo: Optional[str] = None
    ) -> AlertaSeguridad:
        """Crea una alerta de seguridad"""
        if usuario_id not in self.alertas:
            self.alertas[usuario_id] = []
        
        alerta = AlertaSeguridad(
            id=f"ALERT-{secrets.token_hex(6).upper()}",
            usuario_id=usuario_id,
            tipo=tipo,
            severidad=severidad,
            titulo=titulo,
            descripcion=descripcion,
            timestamp=datetime.now(),
            ip_origen=ip_origen,
            ubicacion_aproximada=ubicacion,
            dispositivo=dispositivo
        )
        
        self.alertas[usuario_id].append(alerta)
        
        # Notificación urgente
        self._crear_notificacion(
            usuario_id=usuario_id,
            tipo=TipoNotificacion.ALERTA_SEGURIDAD,
            prioridad=PrioridadNotificacion.URGENTE,
            titulo=f"⚠️ {titulo}",
            mensaje=descripcion,
            datos_adicionales={"alerta_id": alerta.id},
            acciones_disponibles=[
                {"accion": "revisar", "label": "Revisar actividad"},
                {"accion": "revocar_todo", "label": "Revocar todos los accesos"}
            ]
        )
        
        return alerta
    
    def obtener_alertas(
        self,
        usuario_id: str,
        solo_activas: bool = True
    ) -> List[AlertaSeguridad]:
        """Obtiene alertas de seguridad"""
        if usuario_id not in self.alertas:
            return []
        
        alertas = self.alertas[usuario_id]
        if solo_activas:
            alertas = [a for a in alertas if not a.resuelta]
        
        return sorted(alertas, key=lambda x: x.timestamp, reverse=True)
    
    def resolver_alerta(
        self,
        usuario_id: str,
        alerta_id: str,
        accion_tomada: str
    ) -> bool:
        """Marca una alerta como resuelta"""
        if usuario_id not in self.alertas:
            return False
        
        alerta = next((a for a in self.alertas[usuario_id] if a.id == alerta_id), None)
        if alerta:
            alerta.resuelta = True
            alerta.acciones_tomadas.append(accion_tomada)
            return True
        return False
    
    # -------------------------------------------------------------------------
    # PREFERENCIAS DE USUARIO
    # -------------------------------------------------------------------------
    
    def obtener_preferencias(self, usuario_id: str) -> PreferenciasNotificacion:
        """Obtiene preferencias del usuario"""
        if usuario_id not in self.preferencias:
            self.preferencias[usuario_id] = PreferenciasNotificacion(usuario_id=usuario_id)
        return self.preferencias[usuario_id]
    
    def actualizar_preferencias(
        self,
        usuario_id: str,
        canales: Optional[List[CanalNotificacion]] = None,
        notificaciones: Optional[Dict[TipoNotificacion, bool]] = None,
        horario_inicio: Optional[str] = None,
        horario_fin: Optional[str] = None
    ) -> PreferenciasNotificacion:
        """Actualiza preferencias del usuario"""
        prefs = self.obtener_preferencias(usuario_id)
        
        if canales is not None:
            prefs.canales_habilitados = canales
        
        if notificaciones is not None:
            prefs.notificaciones_habilitadas.update(notificaciones)
        
        if horario_inicio is not None:
            prefs.horario_no_molestar_inicio = horario_inicio
        
        if horario_fin is not None:
            prefs.horario_no_molestar_fin = horario_fin
        
        return prefs
    
    # -------------------------------------------------------------------------
    # ESTADÍSTICAS Y DASHBOARD
    # -------------------------------------------------------------------------
    
    def obtener_estadisticas(self, usuario_id: str) -> EstadisticasUsuario:
        """Genera estadísticas del usuario para dashboard"""
        ahora = datetime.now()
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Contar consentimientos
        consents = self.consentimientos.get(usuario_id, {})
        activos = len([c for c in consents.values() if c["estado"] == EstadoConsentimiento.ACTIVO])
        total_historico = len(consents)
        
        # TPPs únicos
        tpps = set(c["tpp_id"] for c in consents.values() if c["estado"] == EstadoConsentimiento.ACTIVO)
        
        # Accesos del mes
        accesos_mes = [
            a for a in self.accesos.get(usuario_id, [])
            if a.timestamp >= inicio_mes
        ]
        
        # Pagos del mes
        pagos_mes = [
            p for p in self.pagos.get(usuario_id, [])
            if p.fecha_iniciacion >= inicio_mes
        ]
        monto_total = sum(p.monto for p in pagos_mes if p.estado == "completado")
        
        # Instituciones conectadas
        instituciones = set()
        for consent in consents.values():
            for inst in consent.get("instituciones", []):
                instituciones.add(inst.get("nombre", ""))
        
        # Último acceso
        ultimo_acceso = None
        if self.accesos.get(usuario_id):
            ultimo_acceso = max(a.timestamp for a in self.accesos[usuario_id])
        
        return EstadisticasUsuario(
            usuario_id=usuario_id,
            total_consentimientos_activos=activos,
            total_consentimientos_historicos=total_historico,
            total_tpps_conectados=len(tpps),
            total_accesos_mes=len(accesos_mes),
            total_pagos_mes=len(pagos_mes),
            monto_total_pagos_mes=monto_total,
            instituciones_conectadas=list(instituciones),
            ultimo_acceso_general=ultimo_acceso
        )
    
    def generar_reporte_privacidad(self, usuario_id: str) -> Dict[str, Any]:
        """
        Genera reporte de privacidad para el usuario.
        Derecho del usuario según NCG 514 y normativas de protección de datos.
        """
        stats = self.obtener_estadisticas(usuario_id)
        consentimientos = self.obtener_historial_consentimientos(usuario_id)
        
        # Datos compartidos por categoría
        datos_compartidos = {}
        for acc in self.accesos.get(usuario_id, []):
            for dato in acc.datos_accedidos:
                datos_compartidos[dato] = datos_compartidos.get(dato, 0) + 1
        
        return {
            "fecha_generacion": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "resumen": {
                "tpps_con_acceso_activo": stats.total_tpps_conectados,
                "consentimientos_activos": stats.total_consentimientos_activos,
                "total_accesos_historicos": len(self.accesos.get(usuario_id, [])),
                "instituciones_financieras_conectadas": stats.instituciones_conectadas
            },
            "consentimientos": [
                {
                    "tpp": c.tpp_nombre,
                    "estado": c.estado.value,
                    "alcances": c.alcances,
                    "vigencia": c.fecha_expiracion.isoformat() if c.estado == EstadoConsentimiento.ACTIVO else None
                }
                for c in consentimientos
            ],
            "datos_compartidos": datos_compartidos,
            "derechos_disponibles": [
                "Revocar cualquier consentimiento en cualquier momento (efecto inmediato)",
                "Solicitar copia de todos tus datos",
                "Solicitar eliminación de datos (donde aplique)",
                "Reportar uso indebido de datos"
            ]
        }


# ============================================================================
# API REST PARA PANEL (EJEMPLO FastAPI)
# ============================================================================

class PanelControlAPI:
    """
    Ejemplo de endpoints API para el Panel de Control
    """
    
    def __init__(self, panel: PanelControlUsuario):
        self.panel = panel
    
    def get_dashboard(self, usuario_id: str) -> Dict[str, Any]:
        """GET /api/v1/dashboard"""
        stats = self.panel.obtener_estadisticas(usuario_id)
        notifs_no_leidas = len(self.panel.obtener_notificaciones(usuario_id, solo_no_leidas=True))
        alertas_activas = len(self.panel.obtener_alertas(usuario_id, solo_activas=True))
        
        return {
            "estadisticas": {
                "consentimientos_activos": stats.total_consentimientos_activos,
                "tpps_conectados": stats.total_tpps_conectados,
                "accesos_este_mes": stats.total_accesos_mes,
                "pagos_este_mes": stats.total_pagos_mes,
                "monto_pagos_mes": stats.monto_total_pagos_mes
            },
            "notificaciones_pendientes": notifs_no_leidas,
            "alertas_activas": alertas_activas,
            "instituciones_conectadas": stats.instituciones_conectadas,
            "ultimo_acceso": stats.ultimo_acceso_general.isoformat() if stats.ultimo_acceso_general else None
        }
    
    def get_consentimientos(self, usuario_id: str) -> List[Dict]:
        """GET /api/v1/consentimientos"""
        consentimientos = self.panel.obtener_consentimientos_activos(usuario_id)
        return [
            {
                "id": c.id,
                "tpp_nombre": c.tpp_nombre,
                "tpp_logo": c.tpp_logo_url,
                "estado": c.estado.value,
                "alcances": c.alcances,
                "expira": c.fecha_expiracion.isoformat(),
                "ultimo_acceso": c.ultimo_acceso.isoformat() if c.ultimo_acceso else None,
                "total_accesos": c.total_accesos
            }
            for c in consentimientos
        ]
    
    def post_revocar(self, usuario_id: str, consentimiento_id: str) -> Dict:
        """POST /api/v1/consentimientos/{id}/revocar"""
        return self.panel.revocar_consentimiento(usuario_id, consentimiento_id)
    
    def get_accesos(self, usuario_id: str, limite: int = 50) -> List[Dict]:
        """GET /api/v1/accesos"""
        accesos = self.panel.obtener_historial_accesos(usuario_id, limite=limite)
        return [
            {
                "id": a.id,
                "tpp": a.tpp_nombre,
                "tipo": a.tipo_acceso.value,
                "fecha": a.timestamp.isoformat(),
                "institucion": a.institucion_origen,
                "datos": a.datos_accedidos,
                "exitoso": a.exitoso
            }
            for a in accesos
        ]


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Crear panel
    panel = PanelControlUsuario()
    
    # Simular registro de consentimiento
    usuario_id = "USR-001"
    panel.consentimientos[usuario_id] = {
        "CONS-001": {
            "tpp_id": "TPP-FINTECH-001",
            "tpp_nombre": "MiFintech App",
            "tpp_logo_url": "https://mifintech.cl/logo.png",
            "estado": EstadoConsentimiento.ACTIVO,
            "fecha_creacion": datetime.now() - timedelta(days=30),
            "fecha_expiracion": datetime.now() + timedelta(days=335),
            "alcances": ["saldos", "movimientos"],
            "instituciones": [{"id": "BCH", "nombre": "Banco de Chile"}]
        }
    }
    
    # Registrar acceso
    panel.registrar_acceso(
        usuario_id=usuario_id,
        consentimiento_id="CONS-001",
        tpp_id="TPP-FINTECH-001",
        tpp_nombre="MiFintech App",
        tipo_acceso=TipoAcceso.CONSULTA_SALDOS,
        institucion_origen="Banco de Chile",
        datos_accedidos=["saldo_disponible", "saldo_contable"],
        ip_origen="192.168.1.100"
    )
    
    # Obtener estadísticas
    stats = panel.obtener_estadisticas(usuario_id)
    print("=== ESTADÍSTICAS ===")
    print(f"Consentimientos activos: {stats.total_consentimientos_activos}")
    print(f"Accesos este mes: {stats.total_accesos_mes}")
    
    # Obtener notificaciones
    notifs = panel.obtener_notificaciones(usuario_id)
    print(f"\n=== NOTIFICACIONES ({len(notifs)}) ===")
    for n in notifs:
        print(f"- [{n.tipo.value}] {n.titulo}")
    
    # Generar reporte de privacidad
    reporte = panel.generar_reporte_privacidad(usuario_id)
    print("\n=== REPORTE PRIVACIDAD ===")
    print(json.dumps(reporte, indent=2, ensure_ascii=False, default=str))
