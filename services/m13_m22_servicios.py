# ============================================================================
# DATAPOLIS v3.0 - SERVICES M13-M22 CONSOLIDADO
# ============================================================================
# M13: Asambleas | M14: Comunicaciones | M15: Portería/Control Acceso
# M16: Reservas Áreas Comunes | M18: Seguridad | M19: Conciliación Bancaria
# M20: Presupuestos | M21: Cobranza | M22: Auditoría
# ============================================================================

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
import uuid

# ============================================================================
# M13 - ASAMBLEAS
# ============================================================================

class TipoAsamblea(str, Enum):
    ORDINARIA = "ordinaria"
    EXTRAORDINARIA = "extraordinaria"
    COMITE = "comite"

class EstadoAsamblea(str, Enum):
    PROGRAMADA = "programada"
    CONVOCADA = "convocada"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    SUSPENDIDA = "suspendida"

class TipoVotacion(str, Enum):
    MAYORIA_SIMPLE = "mayoria_simple"
    MAYORIA_ABSOLUTA = "mayoria_absoluta"
    UNANIMIDAD = "unanimidad"
    DOS_TERCIOS = "dos_tercios"

@dataclass
class Asamblea:
    id: str
    tipo: TipoAsamblea
    numero: int
    fecha_programada: datetime
    lugar: str
    estado: EstadoAsamblea
    quorum_requerido: float
    quorum_presente: float
    tabla: List[Dict]
    asistentes: List[Dict]
    acuerdos: List[Dict]
    acta_id: Optional[str]
    copropiedad_id: str

class AsambleasService:
    def __init__(self):
        self.asambleas: Dict[str, Asamblea] = {}
    
    def programar_asamblea(self, tipo: TipoAsamblea, fecha: datetime, 
                          lugar: str, tabla: List[Dict], copropiedad_id: str,
                          quorum_requerido: float = 50.0) -> Dict:
        asamblea_id = str(uuid.uuid4())[:8]
        numero = len([a for a in self.asambleas.values() 
                     if a.copropiedad_id == copropiedad_id and a.tipo == tipo]) + 1
        
        asamblea = Asamblea(
            id=asamblea_id, tipo=tipo, numero=numero,
            fecha_programada=fecha, lugar=lugar,
            estado=EstadoAsamblea.PROGRAMADA,
            quorum_requerido=quorum_requerido, quorum_presente=0,
            tabla=tabla, asistentes=[], acuerdos=[],
            acta_id=None, copropiedad_id=copropiedad_id
        )
        self.asambleas[asamblea_id] = asamblea
        return {"asamblea_id": asamblea_id, "numero": numero, "mensaje": "Asamblea programada"}
    
    def registrar_asistencia(self, asamblea_id: str, asistente: Dict) -> Dict:
        if asamblea_id not in self.asambleas:
            return {"error": "Asamblea no encontrada"}
        asamblea = self.asambleas[asamblea_id]
        asamblea.asistentes.append({**asistente, "hora_registro": datetime.now().isoformat()})
        asamblea.quorum_presente = sum(a.get("prorrateo", 0) for a in asamblea.asistentes)
        return {"quorum_actual": asamblea.quorum_presente, "hay_quorum": asamblea.quorum_presente >= asamblea.quorum_requerido}
    
    def registrar_votacion(self, asamblea_id: str, punto_tabla: int,
                          descripcion: str, tipo_votacion: TipoVotacion,
                          votos_favor: int, votos_contra: int, abstenciones: int) -> Dict:
        if asamblea_id not in self.asambleas:
            return {"error": "Asamblea no encontrada"}
        
        total_votos = votos_favor + votos_contra + abstenciones
        porcentaje_favor = (votos_favor / total_votos * 100) if total_votos > 0 else 0
        
        umbrales = {
            TipoVotacion.MAYORIA_SIMPLE: 50.0,
            TipoVotacion.MAYORIA_ABSOLUTA: 50.0,
            TipoVotacion.DOS_TERCIOS: 66.67,
            TipoVotacion.UNANIMIDAD: 100.0
        }
        aprobado = porcentaje_favor > umbrales.get(tipo_votacion, 50.0)
        
        acuerdo = {
            "punto": punto_tabla, "descripcion": descripcion,
            "tipo_votacion": tipo_votacion.value,
            "votos_favor": votos_favor, "votos_contra": votos_contra,
            "abstenciones": abstenciones, "porcentaje_favor": round(porcentaje_favor, 2),
            "aprobado": aprobado
        }
        self.asambleas[asamblea_id].acuerdos.append(acuerdo)
        return {"acuerdo": acuerdo, "aprobado": aprobado}

# ============================================================================
# M14 - COMUNICACIONES
# ============================================================================

class TipoComunicacion(str, Enum):
    AVISO = "aviso"
    CIRCULAR = "circular"
    NOTIFICACION = "notificacion"
    EMERGENCIA = "emergencia"
    COBRANZA = "cobranza"
    ASAMBLEA = "asamblea"

class CanalEnvio(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    PLATAFORMA = "plataforma"

@dataclass
class Comunicacion:
    id: str
    tipo: TipoComunicacion
    asunto: str
    contenido: str
    canales: List[CanalEnvio]
    destinatarios: List[Dict]
    fecha_envio: datetime
    enviada: bool
    estadisticas: Dict

class ComunicacionesService:
    def __init__(self):
        self.comunicaciones: Dict[str, Comunicacion] = {}
        self.plantillas: Dict[str, Dict] = {}
    
    def enviar_comunicacion(self, tipo: TipoComunicacion, asunto: str,
                           contenido: str, destinatarios: List[Dict],
                           canales: List[CanalEnvio] = None) -> Dict:
        com_id = str(uuid.uuid4())[:8]
        canales = canales or [CanalEnvio.EMAIL, CanalEnvio.PLATAFORMA]
        
        comunicacion = Comunicacion(
            id=com_id, tipo=tipo, asunto=asunto, contenido=contenido,
            canales=canales, destinatarios=destinatarios,
            fecha_envio=datetime.now(), enviada=True,
            estadisticas={"enviados": len(destinatarios), "leidos": 0, "fallidos": 0}
        )
        self.comunicaciones[com_id] = comunicacion
        return {"comunicacion_id": com_id, "enviados": len(destinatarios), "canales": [c.value for c in canales]}
    
    def enviar_alerta_emergencia(self, mensaje: str, copropiedad_id: str) -> Dict:
        return self.enviar_comunicacion(
            TipoComunicacion.EMERGENCIA, "🚨 ALERTA DE EMERGENCIA",
            mensaje, [{"tipo": "todos", "copropiedad_id": copropiedad_id}],
            [CanalEnvio.PUSH, CanalEnvio.SMS, CanalEnvio.WHATSAPP]
        )

# ============================================================================
# M15 - PORTERÍA Y CONTROL DE ACCESO
# ============================================================================

class TipoVisita(str, Enum):
    INVITADO = "invitado"
    DELIVERY = "delivery"
    PROVEEDOR = "proveedor"
    TECNICO = "tecnico"
    AUTORIDAD = "autoridad"

class TipoVehiculo(str, Enum):
    AUTO = "auto"
    MOTO = "moto"
    CAMION = "camion"
    BICICLETA = "bicicleta"

@dataclass
class RegistroAcceso:
    id: str
    tipo: str  # entrada/salida
    persona_tipo: str  # residente/visita/trabajador
    persona_nombre: str
    persona_rut: Optional[str]
    unidad_destino: str
    autorizado_por: Optional[str]
    vehiculo: Optional[Dict]
    portero_id: str
    fecha_hora: datetime
    observaciones: str

class PorteriaService:
    def __init__(self):
        self.registros: List[RegistroAcceso] = []
        self.visitas_programadas: Dict[str, Dict] = {}
        self.vehiculos_autorizados: Dict[str, Dict] = {}
    
    def registrar_entrada(self, persona_tipo: str, nombre: str, unidad: str,
                         portero_id: str, rut: str = None, vehiculo: Dict = None,
                         autorizado_por: str = None) -> Dict:
        registro_id = str(uuid.uuid4())[:8]
        registro = RegistroAcceso(
            id=registro_id, tipo="entrada", persona_tipo=persona_tipo,
            persona_nombre=nombre, persona_rut=rut, unidad_destino=unidad,
            autorizado_por=autorizado_por, vehiculo=vehiculo,
            portero_id=portero_id, fecha_hora=datetime.now(), observaciones=""
        )
        self.registros.append(registro)
        return {"registro_id": registro_id, "hora": registro.fecha_hora.isoformat(), "tipo": "entrada"}
    
    def registrar_salida(self, persona_nombre: str, portero_id: str) -> Dict:
        registro_id = str(uuid.uuid4())[:8]
        registro = RegistroAcceso(
            id=registro_id, tipo="salida", persona_tipo="",
            persona_nombre=persona_nombre, persona_rut=None,
            unidad_destino="", autorizado_por=None, vehiculo=None,
            portero_id=portero_id, fecha_hora=datetime.now(), observaciones=""
        )
        self.registros.append(registro)
        return {"registro_id": registro_id, "hora": registro.fecha_hora.isoformat(), "tipo": "salida"}
    
    def programar_visita(self, unidad: str, nombre_visita: str, fecha: date,
                        hora_desde: str, hora_hasta: str, tipo: TipoVisita) -> Dict:
        visita_id = str(uuid.uuid4())[:8]
        self.visitas_programadas[visita_id] = {
            "id": visita_id, "unidad": unidad, "nombre": nombre_visita,
            "fecha": fecha.isoformat(), "hora_desde": hora_desde,
            "hora_hasta": hora_hasta, "tipo": tipo.value, "estado": "pendiente"
        }
        return {"visita_id": visita_id, "mensaje": "Visita programada"}
    
    def obtener_bitacora(self, fecha: date = None, limit: int = 100) -> Dict:
        registros = self.registros
        if fecha:
            registros = [r for r in registros if r.fecha_hora.date() == fecha]
        registros = sorted(registros, key=lambda x: x.fecha_hora, reverse=True)[:limit]
        return {
            "registros": [
                {"id": r.id, "tipo": r.tipo, "persona": r.persona_nombre,
                 "unidad": r.unidad_destino, "hora": r.fecha_hora.isoformat()}
                for r in registros
            ],
            "total": len(registros)
        }

# ============================================================================
# M16 - RESERVAS ÁREAS COMUNES
# ============================================================================

class TipoAreaComun(str, Enum):
    SALON_EVENTOS = "salon_eventos"
    QUINCHO = "quincho"
    PISCINA = "piscina"
    GIMNASIO = "gimnasio"
    SALA_REUNION = "sala_reunion"
    CANCHA = "cancha"
    ESTACIONAMIENTO_VISITAS = "estacionamiento_visitas"

class EstadoReserva(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    COMPLETADA = "completada"

@dataclass
class AreaComun:
    id: str
    nombre: str
    tipo: TipoAreaComun
    capacidad: int
    horario_inicio: str
    horario_fin: str
    requiere_garantia: bool
    monto_garantia: Decimal
    tarifa_hora: Decimal
    dias_anticipacion_max: int
    reglas: List[str]

@dataclass
class Reserva:
    id: str
    area_id: str
    unidad_id: str
    residente_nombre: str
    fecha: date
    hora_inicio: str
    hora_fin: str
    asistentes: int
    estado: EstadoReserva
    monto_total: Decimal
    garantia_pagada: bool

class ReservasService:
    def __init__(self):
        self.areas: Dict[str, AreaComun] = {}
        self.reservas: Dict[str, Reserva] = {}
        self._inicializar_areas()
    
    def _inicializar_areas(self):
        areas_default = [
            ("salon", "Salón de Eventos", TipoAreaComun.SALON_EVENTOS, 80, "10:00", "23:00", True, Decimal("100000"), Decimal("15000")),
            ("quincho", "Quincho", TipoAreaComun.QUINCHO, 30, "10:00", "22:00", True, Decimal("50000"), Decimal("10000")),
            ("piscina", "Piscina", TipoAreaComun.PISCINA, 50, "08:00", "20:00", False, Decimal("0"), Decimal("5000")),
            ("gimnasio", "Gimnasio", TipoAreaComun.GIMNASIO, 20, "06:00", "22:00", False, Decimal("0"), Decimal("0")),
        ]
        for aid, nombre, tipo, cap, hi, hf, req_gar, gar, tarifa in areas_default:
            self.areas[aid] = AreaComun(
                id=aid, nombre=nombre, tipo=tipo, capacidad=cap,
                horario_inicio=hi, horario_fin=hf, requiere_garantia=req_gar,
                monto_garantia=gar, tarifa_hora=tarifa, dias_anticipacion_max=30, reglas=[]
            )
    
    def crear_reserva(self, area_id: str, unidad_id: str, residente: str,
                     fecha: date, hora_inicio: str, hora_fin: str, asistentes: int) -> Dict:
        if area_id not in self.areas:
            return {"error": "Área no encontrada"}
        
        area = self.areas[area_id]
        if asistentes > area.capacidad:
            return {"error": f"Capacidad máxima: {area.capacidad}"}
        
        # Verificar disponibilidad
        for reserva in self.reservas.values():
            if reserva.area_id == area_id and reserva.fecha == fecha and reserva.estado == EstadoReserva.CONFIRMADA:
                if not (hora_fin <= reserva.hora_inicio or hora_inicio >= reserva.hora_fin):
                    return {"error": "Horario no disponible"}
        
        # Calcular monto
        horas = int(hora_fin.split(":")[0]) - int(hora_inicio.split(":")[0])
        monto = area.tarifa_hora * horas
        
        reserva_id = str(uuid.uuid4())[:8]
        reserva = Reserva(
            id=reserva_id, area_id=area_id, unidad_id=unidad_id,
            residente_nombre=residente, fecha=fecha, hora_inicio=hora_inicio,
            hora_fin=hora_fin, asistentes=asistentes,
            estado=EstadoReserva.PENDIENTE, monto_total=monto, garantia_pagada=False
        )
        self.reservas[reserva_id] = reserva
        
        return {
            "reserva_id": reserva_id, "monto": float(monto),
            "garantia_requerida": float(area.monto_garantia) if area.requiere_garantia else 0,
            "mensaje": "Reserva creada, pendiente confirmación"
        }
    
    def obtener_disponibilidad(self, area_id: str, fecha: date) -> Dict:
        if area_id not in self.areas:
            return {"error": "Área no encontrada"}
        
        area = self.areas[area_id]
        reservas_dia = [r for r in self.reservas.values() 
                       if r.area_id == area_id and r.fecha == fecha 
                       and r.estado == EstadoReserva.CONFIRMADA]
        
        bloques_ocupados = [(r.hora_inicio, r.hora_fin) for r in reservas_dia]
        
        return {
            "area": area.nombre, "fecha": fecha.isoformat(),
            "horario": f"{area.horario_inicio} - {area.horario_fin}",
            "bloques_ocupados": bloques_ocupados,
            "capacidad": area.capacidad
        }

# ============================================================================
# M18 - SEGURIDAD
# ============================================================================

class TipoIncidente(str, Enum):
    ROBO = "robo"
    VANDALISMO = "vandalismo"
    EMERGENCIA_MEDICA = "emergencia_medica"
    INCENDIO = "incendio"
    SISMO = "sismo"
    INUNDACION = "inundacion"
    RUIDOS = "ruidos_molestos"
    PELEA = "pelea"
    ACCIDENTE = "accidente"

class GravedadIncidente(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

@dataclass
class Incidente:
    id: str
    tipo: TipoIncidente
    gravedad: GravedadIncidente
    descripcion: str
    ubicacion: str
    reportado_por: str
    fecha_hora: datetime
    estado: str
    acciones: List[Dict]
    evidencias: List[str]

class SeguridadService:
    def __init__(self):
        self.incidentes: Dict[str, Incidente] = {}
        self.rondas: List[Dict] = []
        self.camaras: Dict[str, Dict] = {}
    
    def reportar_incidente(self, tipo: TipoIncidente, gravedad: GravedadIncidente,
                          descripcion: str, ubicacion: str, reportado_por: str) -> Dict:
        incidente_id = str(uuid.uuid4())[:8]
        incidente = Incidente(
            id=incidente_id, tipo=tipo, gravedad=gravedad,
            descripcion=descripcion, ubicacion=ubicacion,
            reportado_por=reportado_por, fecha_hora=datetime.now(),
            estado="abierto", acciones=[], evidencias=[]
        )
        self.incidentes[incidente_id] = incidente
        
        # Si es crítico, generar alerta
        alerta = None
        if gravedad in [GravedadIncidente.ALTA, GravedadIncidente.CRITICA]:
            alerta = {"tipo": "emergencia", "mensaje": f"Incidente {tipo.value} en {ubicacion}"}
        
        return {"incidente_id": incidente_id, "alerta_generada": alerta}
    
    def registrar_ronda(self, guardia_id: str, puntos_control: List[Dict]) -> Dict:
        ronda_id = str(uuid.uuid4())[:8]
        ronda = {
            "id": ronda_id, "guardia_id": guardia_id,
            "fecha_inicio": datetime.now().isoformat(),
            "puntos_control": puntos_control, "novedades": [], "completada": False
        }
        self.rondas.append(ronda)
        return {"ronda_id": ronda_id, "puntos": len(puntos_control)}
    
    def obtener_estadisticas_seguridad(self, fecha_desde: date, fecha_hasta: date) -> Dict:
        incidentes = [i for i in self.incidentes.values() 
                     if fecha_desde <= i.fecha_hora.date() <= fecha_hasta]
        
        por_tipo = {}
        for inc in incidentes:
            por_tipo[inc.tipo.value] = por_tipo.get(inc.tipo.value, 0) + 1
        
        return {
            "total_incidentes": len(incidentes),
            "por_tipo": por_tipo,
            "criticos": len([i for i in incidentes if i.gravedad == GravedadIncidente.CRITICA]),
            "rondas_periodo": len([r for r in self.rondas if r.get("completada")])
        }

# ============================================================================
# M19 - CONCILIACIÓN BANCARIA
# ============================================================================

class TipoMovimientoBanco(str, Enum):
    DEPOSITO = "deposito"
    TRANSFERENCIA = "transferencia"
    CHEQUE = "cheque"
    CARGO = "cargo"
    ABONO = "abono"
    COMISION = "comision"

class EstadoConciliacion(str, Enum):
    PENDIENTE = "pendiente"
    CONCILIADO = "conciliado"
    DESCUADRADO = "descuadrado"

@dataclass
class MovimientoBanco:
    id: str
    cuenta_id: str
    fecha: date
    tipo: TipoMovimientoBanco
    descripcion: str
    referencia: str
    monto: Decimal
    saldo: Decimal
    conciliado: bool
    documento_contable_id: Optional[str]

class ConciliacionBancariaService:
    def __init__(self):
        self.movimientos: Dict[str, MovimientoBanco] = {}
        self.cuentas: Dict[str, Dict] = {}
        self.conciliaciones: Dict[str, Dict] = {}
    
    def importar_cartola(self, cuenta_id: str, movimientos: List[Dict]) -> Dict:
        importados = 0
        for mov in movimientos:
            mov_id = str(uuid.uuid4())[:8]
            self.movimientos[mov_id] = MovimientoBanco(
                id=mov_id, cuenta_id=cuenta_id,
                fecha=date.fromisoformat(mov["fecha"]),
                tipo=TipoMovimientoBanco(mov.get("tipo", "abono")),
                descripcion=mov.get("descripcion", ""),
                referencia=mov.get("referencia", ""),
                monto=Decimal(str(mov["monto"])),
                saldo=Decimal(str(mov.get("saldo", 0))),
                conciliado=False, documento_contable_id=None
            )
            importados += 1
        return {"importados": importados, "mensaje": "Cartola importada"}
    
    def conciliar_automatico(self, cuenta_id: str, periodo: str) -> Dict:
        movimientos = [m for m in self.movimientos.values() 
                      if m.cuenta_id == cuenta_id and not m.conciliado]
        
        conciliados = 0
        for mov in movimientos:
            # Lógica de matching automático (simplificada)
            if mov.referencia and len(mov.referencia) > 5:
                mov.conciliado = True
                conciliados += 1
        
        pendientes = len(movimientos) - conciliados
        return {
            "conciliados_automatico": conciliados,
            "pendientes_revision": pendientes,
            "porcentaje_conciliacion": round(conciliados / len(movimientos) * 100, 2) if movimientos else 100
        }
    
    def generar_conciliacion(self, cuenta_id: str, periodo: str) -> Dict:
        movimientos = [m for m in self.movimientos.values() if m.cuenta_id == cuenta_id]
        
        saldo_banco = sum(m.monto for m in movimientos if m.conciliado)
        movimientos_pendientes = [m for m in movimientos if not m.conciliado]
        
        return {
            "cuenta_id": cuenta_id, "periodo": periodo,
            "saldo_banco": float(saldo_banco),
            "movimientos_pendientes": len(movimientos_pendientes),
            "monto_pendiente": float(sum(m.monto for m in movimientos_pendientes)),
            "estado": EstadoConciliacion.CONCILIADO.value if not movimientos_pendientes else EstadoConciliacion.PENDIENTE.value
        }

# ============================================================================
# M20 - PRESUPUESTOS
# ============================================================================

class TipoPresupuesto(str, Enum):
    ANUAL = "anual"
    EXTRAORDINARIO = "extraordinario"
    PROYECTO = "proyecto"

class EstadoPresupuesto(str, Enum):
    BORRADOR = "borrador"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    VIGENTE = "vigente"
    CERRADO = "cerrado"

@dataclass
class LineaPresupuesto:
    id: str
    cuenta_id: str
    cuenta_nombre: str
    presupuesto_mes: List[Decimal]  # 12 meses
    ejecutado_mes: List[Decimal]
    
    @property
    def total_presupuestado(self) -> Decimal:
        return sum(self.presupuesto_mes)
    
    @property
    def total_ejecutado(self) -> Decimal:
        return sum(self.ejecutado_mes)

@dataclass
class Presupuesto:
    id: str
    tipo: TipoPresupuesto
    periodo: str
    nombre: str
    estado: EstadoPresupuesto
    lineas: List[LineaPresupuesto]
    total_ingresos: Decimal
    total_gastos: Decimal
    fecha_aprobacion: Optional[datetime]
    copropiedad_id: str

class PresupuestosService:
    def __init__(self):
        self.presupuestos: Dict[str, Presupuesto] = {}
    
    def crear_presupuesto(self, tipo: TipoPresupuesto, periodo: str,
                         nombre: str, copropiedad_id: str) -> Dict:
        ppto_id = str(uuid.uuid4())[:8]
        presupuesto = Presupuesto(
            id=ppto_id, tipo=tipo, periodo=periodo, nombre=nombre,
            estado=EstadoPresupuesto.BORRADOR, lineas=[],
            total_ingresos=Decimal("0"), total_gastos=Decimal("0"),
            fecha_aprobacion=None, copropiedad_id=copropiedad_id
        )
        self.presupuestos[ppto_id] = presupuesto
        return {"presupuesto_id": ppto_id, "mensaje": "Presupuesto creado"}
    
    def agregar_linea(self, ppto_id: str, cuenta_id: str, cuenta_nombre: str,
                     montos_mensuales: List[float]) -> Dict:
        if ppto_id not in self.presupuestos:
            return {"error": "Presupuesto no encontrado"}
        
        linea_id = str(uuid.uuid4())[:8]
        linea = LineaPresupuesto(
            id=linea_id, cuenta_id=cuenta_id, cuenta_nombre=cuenta_nombre,
            presupuesto_mes=[Decimal(str(m)) for m in montos_mensuales],
            ejecutado_mes=[Decimal("0")] * 12
        )
        self.presupuestos[ppto_id].lineas.append(linea)
        return {"linea_id": linea_id, "total_anual": float(linea.total_presupuestado)}
    
    def obtener_ejecucion(self, ppto_id: str) -> Dict:
        if ppto_id not in self.presupuestos:
            return {"error": "Presupuesto no encontrado"}
        
        ppto = self.presupuestos[ppto_id]
        lineas_detalle = []
        for linea in ppto.lineas:
            lineas_detalle.append({
                "cuenta": linea.cuenta_nombre,
                "presupuestado": float(linea.total_presupuestado),
                "ejecutado": float(linea.total_ejecutado),
                "variacion": float(linea.total_ejecutado - linea.total_presupuestado),
                "ejecucion_pct": round(float(linea.total_ejecutado / linea.total_presupuestado * 100), 2) if linea.total_presupuestado else 0
            })
        
        total_ppto = sum(l.total_presupuestado for l in ppto.lineas)
        total_ejec = sum(l.total_ejecutado for l in ppto.lineas)
        
        return {
            "presupuesto_id": ppto_id, "periodo": ppto.periodo,
            "lineas": lineas_detalle,
            "total_presupuestado": float(total_ppto),
            "total_ejecutado": float(total_ejec),
            "ejecucion_global_pct": round(float(total_ejec / total_ppto * 100), 2) if total_ppto else 0
        }

# ============================================================================
# M21 - COBRANZA
# ============================================================================

class EstadoCobranza(str, Enum):
    VIGENTE = "vigente"
    VENCIDO = "vencido"
    EN_GESTION = "en_gestion"
    CONVENIO = "convenio"
    JUDICIAL = "judicial"
    PAGADO = "pagado"
    INCOBRABLE = "incobrable"

class AccionCobranza(str, Enum):
    AVISO_VENCIMIENTO = "aviso_vencimiento"
    RECORDATORIO = "recordatorio"
    LLAMADA = "llamada"
    CARTA_COBRANZA = "carta_cobranza"
    CORTE_SERVICIO = "corte_servicio"
    DEMANDA = "demanda"
    CONVENIO = "convenio"

@dataclass
class CuentaPorCobrar:
    id: str
    unidad_id: str
    propietario_nombre: str
    propietario_rut: str
    concepto: str
    monto_original: Decimal
    monto_pendiente: Decimal
    fecha_emision: date
    fecha_vencimiento: date
    estado: EstadoCobranza
    gestiones: List[Dict]
    dias_mora: int

class CobranzaService:
    def __init__(self):
        self.cuentas: Dict[str, CuentaPorCobrar] = {}
        self.convenios: Dict[str, Dict] = {}
    
    def registrar_deuda(self, unidad_id: str, propietario: str, rut: str,
                       concepto: str, monto: Decimal, fecha_vencimiento: date) -> Dict:
        cuenta_id = str(uuid.uuid4())[:8]
        cuenta = CuentaPorCobrar(
            id=cuenta_id, unidad_id=unidad_id, propietario_nombre=propietario,
            propietario_rut=rut, concepto=concepto, monto_original=monto,
            monto_pendiente=monto, fecha_emision=date.today(),
            fecha_vencimiento=fecha_vencimiento, estado=EstadoCobranza.VIGENTE,
            gestiones=[], dias_mora=0
        )
        self.cuentas[cuenta_id] = cuenta
        return {"cuenta_id": cuenta_id, "monto": float(monto)}
    
    def registrar_gestion(self, cuenta_id: str, accion: AccionCobranza,
                         descripcion: str, resultado: str, gestor: str) -> Dict:
        if cuenta_id not in self.cuentas:
            return {"error": "Cuenta no encontrada"}
        
        gestion = {
            "fecha": datetime.now().isoformat(),
            "accion": accion.value,
            "descripcion": descripcion,
            "resultado": resultado,
            "gestor": gestor
        }
        self.cuentas[cuenta_id].gestiones.append(gestion)
        return {"mensaje": "Gestión registrada", "gestion": gestion}
    
    def crear_convenio(self, cuenta_id: str, cuotas: int, monto_cuota: Decimal,
                      fecha_primera_cuota: date) -> Dict:
        if cuenta_id not in self.cuentas:
            return {"error": "Cuenta no encontrada"}
        
        convenio_id = str(uuid.uuid4())[:8]
        self.convenios[convenio_id] = {
            "id": convenio_id, "cuenta_id": cuenta_id,
            "cuotas_total": cuotas, "cuotas_pagadas": 0,
            "monto_cuota": float(monto_cuota),
            "fecha_inicio": fecha_primera_cuota.isoformat(),
            "estado": "vigente"
        }
        self.cuentas[cuenta_id].estado = EstadoCobranza.CONVENIO
        return {"convenio_id": convenio_id, "cuotas": cuotas, "monto_cuota": float(monto_cuota)}
    
    def actualizar_mora(self) -> Dict:
        """Actualiza días de mora de todas las cuentas"""
        hoy = date.today()
        actualizados = 0
        for cuenta in self.cuentas.values():
            if cuenta.estado in [EstadoCobranza.VIGENTE, EstadoCobranza.VENCIDO, EstadoCobranza.EN_GESTION]:
                dias = (hoy - cuenta.fecha_vencimiento).days
                if dias > 0:
                    cuenta.dias_mora = dias
                    if cuenta.estado == EstadoCobranza.VIGENTE:
                        cuenta.estado = EstadoCobranza.VENCIDO
                    actualizados += 1
        return {"cuentas_actualizadas": actualizados}
    
    def obtener_cartera_morosa(self) -> Dict:
        morosos = [c for c in self.cuentas.values() if c.dias_mora > 0]
        
        por_antiguedad = {
            "1_30": [], "31_60": [], "61_90": [], "mas_90": []
        }
        for c in morosos:
            if c.dias_mora <= 30:
                por_antiguedad["1_30"].append(c)
            elif c.dias_mora <= 60:
                por_antiguedad["31_60"].append(c)
            elif c.dias_mora <= 90:
                por_antiguedad["61_90"].append(c)
            else:
                por_antiguedad["mas_90"].append(c)
        
        return {
            "total_morosos": len(morosos),
            "monto_total": float(sum(c.monto_pendiente for c in morosos)),
            "por_antiguedad": {
                k: {"cantidad": len(v), "monto": float(sum(c.monto_pendiente for c in v))}
                for k, v in por_antiguedad.items()
            }
        }

# ============================================================================
# M22 - AUDITORÍA
# ============================================================================

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

@dataclass
class Hallazgo:
    id: str
    descripcion: str
    area: str
    severidad: SeveridadHallazgo
    recomendacion: str
    responsable: str
    fecha_limite: Optional[date]
    estado: str

@dataclass
class Auditoria:
    id: str
    tipo: TipoAuditoria
    periodo: str
    alcance: str
    auditor: str
    fecha_inicio: date
    fecha_fin: Optional[date]
    hallazgos: List[Hallazgo]
    resultado: Optional[ResultadoAuditoria]
    informe_url: Optional[str]

class AuditoriaService:
    def __init__(self):
        self.auditorias: Dict[str, Auditoria] = {}
        self.planes_accion: Dict[str, Dict] = {}
    
    def iniciar_auditoria(self, tipo: TipoAuditoria, periodo: str,
                         alcance: str, auditor: str) -> Dict:
        audit_id = str(uuid.uuid4())[:8]
        auditoria = Auditoria(
            id=audit_id, tipo=tipo, periodo=periodo, alcance=alcance,
            auditor=auditor, fecha_inicio=date.today(), fecha_fin=None,
            hallazgos=[], resultado=None, informe_url=None
        )
        self.auditorias[audit_id] = auditoria
        return {"auditoria_id": audit_id, "mensaje": "Auditoría iniciada"}
    
    def registrar_hallazgo(self, audit_id: str, descripcion: str, area: str,
                          severidad: SeveridadHallazgo, recomendacion: str,
                          responsable: str, fecha_limite: date = None) -> Dict:
        if audit_id not in self.auditorias:
            return {"error": "Auditoría no encontrada"}
        
        hallazgo_id = str(uuid.uuid4())[:8]
        hallazgo = Hallazgo(
            id=hallazgo_id, descripcion=descripcion, area=area,
            severidad=severidad, recomendacion=recomendacion,
            responsable=responsable, fecha_limite=fecha_limite, estado="abierto"
        )
        self.auditorias[audit_id].hallazgos.append(hallazgo)
        return {"hallazgo_id": hallazgo_id, "severidad": severidad.value}
    
    def finalizar_auditoria(self, audit_id: str, resultado: ResultadoAuditoria,
                           informe_url: str = None) -> Dict:
        if audit_id not in self.auditorias:
            return {"error": "Auditoría no encontrada"}
        
        auditoria = self.auditorias[audit_id]
        auditoria.fecha_fin = date.today()
        auditoria.resultado = resultado
        auditoria.informe_url = informe_url
        
        return {
            "mensaje": "Auditoría finalizada",
            "resultado": resultado.value,
            "total_hallazgos": len(auditoria.hallazgos),
            "hallazgos_criticos": len([h for h in auditoria.hallazgos if h.severidad == SeveridadHallazgo.CRITICO])
        }
    
    def obtener_resumen_auditorias(self, periodo: str = None) -> Dict:
        auditorias = list(self.auditorias.values())
        if periodo:
            auditorias = [a for a in auditorias if a.periodo == periodo]
        
        total_hallazgos = sum(len(a.hallazgos) for a in auditorias)
        hallazgos_abiertos = sum(
            len([h for h in a.hallazgos if h.estado == "abierto"])
            for a in auditorias
        )
        
        return {
            "total_auditorias": len(auditorias),
            "finalizadas": len([a for a in auditorias if a.fecha_fin]),
            "total_hallazgos": total_hallazgos,
            "hallazgos_abiertos": hallazgos_abiertos,
            "por_resultado": {
                r.value: len([a for a in auditorias if a.resultado == r])
                for r in ResultadoAuditoria
            }
        }


# ============================================================================
# INSTANCIAS SINGLETON
# ============================================================================

asambleas_service = AsambleasService()
comunicaciones_service = ComunicacionesService()
porteria_service = PorteriaService()
reservas_service = ReservasService()
seguridad_service = SeguridadService()
conciliacion_service = ConciliacionBancariaService()
presupuestos_service = PresupuestosService()
cobranza_service = CobranzaService()
auditoria_service = AuditoriaService()
