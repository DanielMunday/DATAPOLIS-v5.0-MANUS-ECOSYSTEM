"""
DATAPOLIS v3.0 - Módulo M06: Gestión de Mantenciones
=====================================================
Sistema integral de gestión de mantenciones inmobiliarias.

Características principales:
- Mantenciones preventivas programadas
- Mantenciones correctivas (reparaciones)
- Gestión de proveedores y contratistas
- Control de garantías de equipos
- Presupuestos y cotizaciones
- Historial de intervenciones
- Alertas y recordatorios
- Análisis de costos de mantenimiento

Tipos de mantención:
- Preventiva: Planificada para evitar fallas
- Correctiva: Reparación de fallas existentes
- Predictiva: Basada en análisis de datos
- Mejorativa: Upgrades y mejoras

Autor: DATAPOLIS SpA
Versión: 3.0.0
Última actualización: 2025
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES
# =============================================================================

class TipoMantencion(str, Enum):
    """Tipos de mantención"""
    PREVENTIVA = "preventiva"                        # Planificada
    CORRECTIVA = "correctiva"                        # Reparación
    PREDICTIVA = "predictiva"                        # Basada en datos
    MEJORATIVA = "mejorativa"                        # Upgrades
    EMERGENCIA = "emergencia"                        # Urgente


class EstadoMantencion(str, Enum):
    """Estados del ciclo de mantención"""
    PROGRAMADA = "programada"                        # Planificada futura
    PENDIENTE = "pendiente"                          # Esperando ejecución
    EN_COTIZACION = "en_cotizacion"                 # Solicitando presupuestos
    COTIZADA = "cotizada"                            # Presupuesto recibido
    APROBADA = "aprobada"                            # Autorizada
    EN_EJECUCION = "en_ejecucion"                   # En proceso
    EN_REVISION = "en_revision"                      # Verificando trabajo
    COMPLETADA = "completada"                        # Finalizada OK
    RECHAZADA = "rechazada"                          # No aprobada
    CANCELADA = "cancelada"                          # Anulada


class PrioridadMantencion(str, Enum):
    """Niveles de prioridad"""
    CRITICA = "critica"                              # Seguridad/habitabilidad
    ALTA = "alta"                                    # Afecta funcionamiento
    MEDIA = "media"                                  # Puede esperar días
    BAJA = "baja"                                    # Puede esperar semanas
    PLANIFICADA = "planificada"                      # Preventiva programada


class CategoriaMantencion(str, Enum):
    """Categorías de sistemas/elementos"""
    ESTRUCTURA = "estructura"                        # Muros, losas, vigas
    TECHUMBRE = "techumbre"                         # Techo, impermeabilización
    FACHADA = "fachada"                             # Exterior, pintura
    ELECTRICIDAD = "electricidad"                    # Sistema eléctrico
    GASFITERIA = "gasfiteria"                       # Agua, desagües
    GAS = "gas"                                      # Instalación de gas
    CLIMATIZACION = "climatizacion"                  # AC, calefacción
    ASCENSORES = "ascensores"                        # Elevadores
    SEGURIDAD = "seguridad"                          # Alarmas, CCTV, accesos
    AREAS_COMUNES = "areas_comunes"                  # Jardines, piscina
    EQUIPAMIENTO = "equipamiento"                    # Electrodomésticos
    TERMINACIONES = "terminaciones"                  # Pisos, pintura interior
    VENTANAS = "ventanas"                            # Ventanas, vidrios
    CERRAJERIA = "cerrajeria"                        # Chapas, cerraduras
    CONTROL_PLAGAS = "control_plagas"               # Fumigación, sanitización
    LIMPIEZA = "limpieza"                            # Aseo profundo
    OTRO = "otro"


class TipoProveedor(str, Enum):
    """Tipos de proveedor"""
    EMPRESA = "empresa"                              # Empresa establecida
    CONTRATISTA = "contratista"                      # Contratista independiente
    MAESTRO = "maestro"                              # Maestro particular
    SERVICIO_TECNICO = "servicio_tecnico"           # SAT autorizado
    ESPECIALISTA = "especialista"                    # Especialista certificado


class EstadoProveedor(str, Enum):
    """Estado del proveedor"""
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    EN_EVALUACION = "en_evaluacion"
    RECHAZADO = "rechazado"


class Frecuencia(str, Enum):
    """Frecuencia de mantención preventiva"""
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    BIMENSUAL = "bimensual"
    TRIMESTRAL = "trimestral"
    CUATRIMESTRAL = "cuatrimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"
    BIANUAL = "bianual"


class UnidadGarantia(str, Enum):
    """Unidad de tiempo para garantías"""
    DIAS = "dias"
    MESES = "meses"
    ANOS = "anos"


# =============================================================================
# DATACLASSES - ESTRUCTURA DE DATOS
# =============================================================================

@dataclass
class Proveedor:
    """Proveedor/Contratista de mantenciones"""
    id: str = field(default_factory=lambda: str(uuid4()))
    codigo: str = ""                                  # PROV-NNNN
    
    # Datos básicos
    tipo: TipoProveedor = TipoProveedor.EMPRESA
    razon_social: str = ""
    rut: str = ""
    giro: str = ""
    
    # Contacto
    contacto_nombre: str = ""
    email: str = ""
    telefono: str = ""
    telefono_emergencia: str = ""
    direccion: str = ""
    comuna: str = ""
    
    # Especialidades
    categorias: List[CategoriaMantencion] = field(default_factory=list)
    servicios: List[str] = field(default_factory=list)
    zonas_cobertura: List[str] = field(default_factory=list)  # Comunas
    
    # Evaluación
    estado: EstadoProveedor = EstadoProveedor.EN_EVALUACION
    calificacion_promedio: Decimal = Decimal("0")     # 1-5
    total_trabajos: int = 0
    trabajos_satisfactorios: int = 0
    
    # Documentos
    tiene_inicio_actividades: bool = False
    tiene_boleta_garantia: bool = False
    monto_boleta_garantia_uf: Decimal = Decimal("0")
    certificaciones: List[str] = field(default_factory=list)  # SEC, Gas, etc.
    seguros: List[Dict[str, Any]] = field(default_factory=list)
    
    # Comercial
    forma_pago: str = "30 dias"
    acepta_retencion: bool = True                     # 10% retención
    
    # Auditoría
    fecha_registro: datetime = field(default_factory=datetime.now)
    ultima_evaluacion: Optional[date] = None
    notas: str = ""


@dataclass
class Cotizacion:
    """Cotización/Presupuesto de mantención"""
    id: str = field(default_factory=lambda: str(uuid4()))
    numero: str = ""                                  # COT-YYYY-NNNNNN
    mantencion_id: str = ""
    proveedor_id: str = ""
    
    # Fechas
    fecha_solicitud: date = field(default_factory=date.today)
    fecha_recepcion: Optional[date] = None
    fecha_validez: Optional[date] = None
    
    # Montos
    subtotal: Decimal = Decimal("0")
    descuento_pct: Decimal = Decimal("0")
    iva: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    moneda: str = "CLP"                               # CLP, UF, USD
    
    # Detalle
    items: List[Dict[str, Any]] = field(default_factory=list)
    # [{descripcion, cantidad, unidad, precio_unitario, subtotal}]
    
    # Condiciones
    plazo_ejecucion_dias: int = 0
    garantia_meses: int = 0
    forma_pago: str = ""
    incluye_materiales: bool = True
    observaciones: str = ""
    
    # Estado
    seleccionada: bool = False
    motivo_rechazo: str = ""
    
    # Documento
    documento_url: str = ""


@dataclass
class PlanMantencionPreventiva:
    """Plan de mantención preventiva programada"""
    id: str = field(default_factory=lambda: str(uuid4()))
    codigo: str = ""                                  # PMP-YYYY-NNNN
    
    # Propiedad
    propiedad_id: str = ""
    expediente_id: Optional[str] = None
    
    # Configuración
    nombre: str = ""
    descripcion: str = ""
    categoria: CategoriaMantencion = CategoriaMantencion.OTRO
    equipo_sistema: str = ""                          # Ej: "Caldera Junkers X"
    
    # Programación
    frecuencia: Frecuencia = Frecuencia.ANUAL
    dia_preferido: Optional[int] = None               # 1-31
    hora_preferida: str = "09:00"
    duracion_estimada_horas: Decimal = Decimal("2")
    
    # Proveedor preferido
    proveedor_id: Optional[str] = None
    
    # Control
    activo: bool = True
    ultima_ejecucion: Optional[date] = None
    proxima_ejecucion: Optional[date] = None
    
    # Checklist
    tareas: List[str] = field(default_factory=list)
    
    # Costos estimados
    costo_estimado_uf: Decimal = Decimal("0")
    
    # Auditoría
    creado_en: datetime = field(default_factory=datetime.now)
    creado_por: str = ""


@dataclass
class GarantiaEquipo:
    """Garantía de equipo o trabajo"""
    id: str = field(default_factory=lambda: str(uuid4()))
    
    # Referencia
    propiedad_id: str = ""
    mantencion_id: Optional[str] = None              # Si viene de una mantención
    
    # Equipo/Sistema
    nombre_equipo: str = ""
    marca: str = ""
    modelo: str = ""
    numero_serie: str = ""
    ubicacion: str = ""
    
    # Garantía
    tipo: str = ""                                    # fabricante, instalacion, trabajo
    proveedor_garantia: str = ""
    duracion: int = 0
    unidad: UnidadGarantia = UnidadGarantia.MESES
    fecha_inicio: date = field(default_factory=date.today)
    fecha_termino: date = field(default_factory=date.today)
    
    # Cobertura
    cobertura_descripcion: str = ""
    exclusiones: List[str] = field(default_factory=list)
    condiciones: str = ""
    
    # Contacto
    telefono_garantia: str = ""
    email_garantia: str = ""
    numero_poliza: str = ""
    
    # Estado
    vigente: bool = True
    utilizada: bool = False
    fecha_utilizacion: Optional[date] = None
    motivo_utilizacion: str = ""
    
    # Documentos
    documento_url: str = ""
    factura_url: str = ""


@dataclass
class OrdenTrabajo:
    """Orden de trabajo para ejecución"""
    id: str = field(default_factory=lambda: str(uuid4()))
    numero: str = ""                                  # OT-YYYY-NNNNNN
    mantencion_id: str = ""
    
    # Asignación
    proveedor_id: str = ""
    cotizacion_id: Optional[str] = None
    
    # Fechas
    fecha_emision: date = field(default_factory=date.today)
    fecha_programada: date = field(default_factory=date.today)
    hora_inicio: str = "09:00"
    fecha_inicio_real: Optional[datetime] = None
    fecha_termino_real: Optional[datetime] = None
    
    # Ejecución
    trabajos_realizados: str = ""
    materiales_utilizados: List[Dict[str, Any]] = field(default_factory=list)
    horas_trabajadas: Decimal = Decimal("0")
    personal_asignado: List[str] = field(default_factory=list)
    
    # Verificación
    verificado_por: str = ""
    fecha_verificacion: Optional[date] = None
    resultado_verificacion: str = ""                  # aprobado, observaciones, rechazado
    observaciones_verificacion: str = ""
    
    # Firmas
    firma_proveedor_url: str = ""
    firma_cliente_url: str = ""
    
    # Fotos
    fotos_antes: List[str] = field(default_factory=list)
    fotos_durante: List[str] = field(default_factory=list)
    fotos_despues: List[str] = field(default_factory=list)
    
    # Documentos
    documento_url: str = ""


@dataclass
class EvaluacionProveedor:
    """Evaluación de trabajo del proveedor"""
    id: str = field(default_factory=lambda: str(uuid4()))
    mantencion_id: str = ""
    proveedor_id: str = ""
    orden_trabajo_id: str = ""
    
    fecha_evaluacion: date = field(default_factory=date.today)
    evaluador: str = ""
    
    # Criterios (1-5)
    calidad_trabajo: int = 0
    cumplimiento_plazo: int = 0
    precio_justo: int = 0
    limpieza: int = 0
    trato_personal: int = 0
    comunicacion: int = 0
    
    # Promedio
    calificacion_promedio: Decimal = Decimal("0")
    
    # Adicionales
    recomendaria: bool = True
    comentarios: str = ""
    aspectos_positivos: List[str] = field(default_factory=list)
    aspectos_mejorar: List[str] = field(default_factory=list)


@dataclass
class Mantencion:
    """Registro de mantención"""
    id: str = field(default_factory=lambda: str(uuid4()))
    codigo: str = ""                                  # MNT-YYYY-NNNNNN
    
    # Tipo y estado
    tipo: TipoMantencion = TipoMantencion.CORRECTIVA
    estado: EstadoMantencion = EstadoMantencion.PENDIENTE
    prioridad: PrioridadMantencion = PrioridadMantencion.MEDIA
    categoria: CategoriaMantencion = CategoriaMantencion.OTRO
    
    # Propiedad
    propiedad_id: str = ""
    expediente_id: Optional[str] = None
    unidad_id: Optional[str] = None                   # Si es en condominio
    
    # Ubicación específica
    ubicacion_especifica: str = ""                    # Ej: "Baño principal"
    
    # Descripción
    titulo: str = ""
    descripcion: str = ""
    sintomas: str = ""                                # Para correctivas
    
    # Reportado por
    reportado_por: str = ""
    fecha_reporte: datetime = field(default_factory=datetime.now)
    medio_reporte: str = ""                           # telefono, email, app, presencial
    
    # Plan preventivo (si aplica)
    plan_preventivo_id: Optional[str] = None
    
    # Fechas
    fecha_programada: Optional[date] = None
    fecha_limite: Optional[date] = None               # Deadline
    fecha_inicio: Optional[datetime] = None
    fecha_termino: Optional[datetime] = None
    
    # Cotizaciones
    cotizaciones: List[Cotizacion] = field(default_factory=list)
    cotizacion_seleccionada_id: Optional[str] = None
    
    # Orden de trabajo
    orden_trabajo: Optional[OrdenTrabajo] = None
    
    # Proveedor asignado
    proveedor_id: Optional[str] = None
    
    # Costos
    presupuesto_estimado: Decimal = Decimal("0")
    costo_final: Decimal = Decimal("0")
    factura_numero: str = ""
    factura_url: str = ""
    
    # Garantía del trabajo
    garantia_meses: int = 0
    garantia_hasta: Optional[date] = None
    
    # Verificación
    verificado: bool = False
    verificado_por: str = ""
    fecha_verificacion: Optional[date] = None
    resultado_verificacion: str = ""
    
    # Evaluación proveedor
    evaluacion: Optional[EvaluacionProveedor] = None
    
    # Fotos y documentos
    fotos_problema: List[str] = field(default_factory=list)
    fotos_solucion: List[str] = field(default_factory=list)
    documentos: List[str] = field(default_factory=list)
    
    # Historial
    historial: List[Dict[str, Any]] = field(default_factory=list)
    
    # Auditoría
    creado_en: datetime = field(default_factory=datetime.now)
    actualizado_en: datetime = field(default_factory=datetime.now)
    creado_por: str = ""
    version: int = 1


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class MantencionesService:
    """
    Servicio de Gestión de Mantenciones M06.
    
    Funcionalidades:
    - CRUD de mantenciones
    - Gestión de proveedores
    - Planes de mantención preventiva
    - Control de garantías
    - Cotizaciones y órdenes de trabajo
    - Evaluación de proveedores
    - Reportes y estadísticas
    """
    
    def __init__(self):
        self._mantenciones: Dict[str, Mantencion] = {}
        self._proveedores: Dict[str, Proveedor] = {}
        self._planes: Dict[str, PlanMantencionPreventiva] = {}
        self._garantias: Dict[str, GarantiaEquipo] = {}
        self._contador_mantenciones = 0
        self._contador_proveedores = 0
        self._contador_planes = 0
        self._contador_cotizaciones = 0
        self._contador_ot = 0
        self._uf_actual = Decimal("38500.00")
        
        logger.info("MantencionesService M06 inicializado")
    
    # =========================================================================
    # GESTIÓN DE MANTENCIONES
    # =========================================================================
    
    async def crear_mantencion(
        self,
        propiedad_id: str,
        tipo: TipoMantencion,
        categoria: CategoriaMantencion,
        titulo: str,
        descripcion: str,
        prioridad: PrioridadMantencion = PrioridadMantencion.MEDIA,
        ubicacion_especifica: str = "",
        reportado_por: str = "",
        fecha_programada: Optional[date] = None,
        usuario: str = "system"
    ) -> Mantencion:
        """
        Crear nueva mantención.
        
        Args:
            propiedad_id: ID de la propiedad
            tipo: Tipo de mantención
            categoria: Categoría del sistema/elemento
            titulo: Título descriptivo
            descripcion: Descripción detallada
            prioridad: Nivel de prioridad
            ubicacion_especifica: Ubicación dentro de la propiedad
            reportado_por: Quién reporta
            fecha_programada: Fecha programada (opcional)
            usuario: Usuario que crea
        """
        # Generar código
        self._contador_mantenciones += 1
        year = datetime.now().year
        codigo = f"MNT-{year}-{self._contador_mantenciones:06d}"
        
        # Determinar fecha límite según prioridad
        fecha_limite = None
        hoy = date.today()
        if prioridad == PrioridadMantencion.CRITICA:
            fecha_limite = hoy + timedelta(days=1)
        elif prioridad == PrioridadMantencion.ALTA:
            fecha_limite = hoy + timedelta(days=3)
        elif prioridad == PrioridadMantencion.MEDIA:
            fecha_limite = hoy + timedelta(days=7)
        elif prioridad == PrioridadMantencion.BAJA:
            fecha_limite = hoy + timedelta(days=30)
        
        # Crear mantención
        mantencion = Mantencion(
            codigo=codigo,
            tipo=tipo,
            estado=EstadoMantencion.PENDIENTE,
            prioridad=prioridad,
            categoria=categoria,
            propiedad_id=propiedad_id,
            ubicacion_especifica=ubicacion_especifica,
            titulo=titulo,
            descripcion=descripcion,
            reportado_por=reportado_por,
            fecha_programada=fecha_programada,
            fecha_limite=fecha_limite,
            creado_por=usuario
        )
        
        # Registrar evento
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "creacion",
            "descripcion": f"Mantención {codigo} creada",
            "usuario": usuario
        })
        
        # Guardar
        self._mantenciones[mantencion.id] = mantencion
        
        logger.info(f"Mantención {codigo} creada - {tipo.value} - {prioridad.value}")
        
        return mantencion
    
    async def obtener_mantencion(self, mantencion_id: str) -> Optional[Mantencion]:
        """Obtener mantención por ID o código"""
        if mantencion_id in self._mantenciones:
            return self._mantenciones[mantencion_id]
        
        for m in self._mantenciones.values():
            if m.codigo == mantencion_id:
                return m
        
        return None
    
    async def listar_mantenciones(
        self,
        propiedad_id: Optional[str] = None,
        tipo: Optional[TipoMantencion] = None,
        estado: Optional[EstadoMantencion] = None,
        categoria: Optional[CategoriaMantencion] = None,
        prioridad: Optional[PrioridadMantencion] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        proveedor_id: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 20
    ) -> Tuple[List[Mantencion], int]:
        """Listar mantenciones con filtros"""
        resultados = list(self._mantenciones.values())
        
        if propiedad_id:
            resultados = [m for m in resultados if m.propiedad_id == propiedad_id]
        
        if tipo:
            resultados = [m for m in resultados if m.tipo == tipo]
        
        if estado:
            resultados = [m for m in resultados if m.estado == estado]
        
        if categoria:
            resultados = [m for m in resultados if m.categoria == categoria]
        
        if prioridad:
            resultados = [m for m in resultados if m.prioridad == prioridad]
        
        if fecha_desde:
            resultados = [m for m in resultados 
                         if m.fecha_reporte.date() >= fecha_desde]
        
        if fecha_hasta:
            resultados = [m for m in resultados 
                         if m.fecha_reporte.date() <= fecha_hasta]
        
        if proveedor_id:
            resultados = [m for m in resultados if m.proveedor_id == proveedor_id]
        
        # Ordenar por prioridad y fecha
        prioridad_orden = {
            PrioridadMantencion.CRITICA: 0,
            PrioridadMantencion.ALTA: 1,
            PrioridadMantencion.MEDIA: 2,
            PrioridadMantencion.BAJA: 3,
            PrioridadMantencion.PLANIFICADA: 4
        }
        resultados.sort(key=lambda m: (prioridad_orden.get(m.prioridad, 5), m.fecha_reporte))
        
        total = len(resultados)
        
        # Paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        resultados = resultados[inicio:fin]
        
        return resultados, total
    
    async def actualizar_estado(
        self,
        mantencion_id: str,
        nuevo_estado: EstadoMantencion,
        observaciones: str = "",
        usuario: str = "system"
    ) -> Mantencion:
        """Cambiar estado de mantención"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        estado_anterior = mantencion.estado
        mantencion.estado = nuevo_estado
        mantencion.actualizado_en = datetime.now()
        mantencion.version += 1
        
        # Acciones según estado
        if nuevo_estado == EstadoMantencion.EN_EJECUCION:
            mantencion.fecha_inicio = datetime.now()
        elif nuevo_estado == EstadoMantencion.COMPLETADA:
            mantencion.fecha_termino = datetime.now()
        
        # Registrar evento
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "cambio_estado",
            "estado_anterior": estado_anterior.value,
            "estado_nuevo": nuevo_estado.value,
            "observaciones": observaciones,
            "usuario": usuario
        })
        
        logger.info(f"Mantención {mantencion.codigo}: {estado_anterior.value} -> {nuevo_estado.value}")
        
        return mantencion
    
    async def asignar_proveedor(
        self,
        mantencion_id: str,
        proveedor_id: str,
        usuario: str = "system"
    ) -> Mantencion:
        """Asignar proveedor a mantención"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        proveedor = await self.obtener_proveedor(proveedor_id)
        if not proveedor:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        
        mantencion.proveedor_id = proveedor_id
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "asignacion_proveedor",
            "proveedor_id": proveedor_id,
            "proveedor_nombre": proveedor.razon_social,
            "usuario": usuario
        })
        
        return mantencion
    
    # =========================================================================
    # GESTIÓN DE COTIZACIONES
    # =========================================================================
    
    async def solicitar_cotizacion(
        self,
        mantencion_id: str,
        proveedor_id: str,
        fecha_limite: Optional[date] = None,
        usuario: str = "system"
    ) -> Cotizacion:
        """Solicitar cotización a proveedor"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        proveedor = await self.obtener_proveedor(proveedor_id)
        if not proveedor:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        
        # Generar número
        self._contador_cotizaciones += 1
        year = datetime.now().year
        numero = f"COT-{year}-{self._contador_cotizaciones:06d}"
        
        cotizacion = Cotizacion(
            numero=numero,
            mantencion_id=mantencion_id,
            proveedor_id=proveedor_id,
            fecha_solicitud=date.today(),
            fecha_validez=fecha_limite or (date.today() + timedelta(days=15))
        )
        
        mantencion.cotizaciones.append(cotizacion)
        
        if mantencion.estado == EstadoMantencion.PENDIENTE:
            mantencion.estado = EstadoMantencion.EN_COTIZACION
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "solicitud_cotizacion",
            "cotizacion_numero": numero,
            "proveedor": proveedor.razon_social,
            "usuario": usuario
        })
        
        logger.info(f"Cotización {numero} solicitada a {proveedor.razon_social}")
        
        return cotizacion
    
    async def registrar_cotizacion(
        self,
        mantencion_id: str,
        cotizacion_id: str,
        items: List[Dict[str, Any]],
        plazo_ejecucion_dias: int,
        garantia_meses: int,
        forma_pago: str,
        observaciones: str = "",
        usuario: str = "system"
    ) -> Cotizacion:
        """Registrar respuesta de cotización"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        cotizacion = None
        for c in mantencion.cotizaciones:
            if c.id == cotizacion_id:
                cotizacion = c
                break
        
        if not cotizacion:
            raise ValueError(f"Cotización {cotizacion_id} no encontrada")
        
        # Calcular totales
        subtotal = Decimal("0")
        for item in items:
            item_subtotal = Decimal(str(item.get("cantidad", 1))) * Decimal(str(item.get("precio_unitario", 0)))
            item["subtotal"] = str(item_subtotal)
            subtotal += item_subtotal
        
        cotizacion.items = items
        cotizacion.subtotal = subtotal
        cotizacion.iva = (subtotal * Decimal("0.19")).quantize(Decimal("1"), ROUND_HALF_UP)
        cotizacion.total = subtotal + cotizacion.iva
        cotizacion.fecha_recepcion = date.today()
        cotizacion.plazo_ejecucion_dias = plazo_ejecucion_dias
        cotizacion.garantia_meses = garantia_meses
        cotizacion.forma_pago = forma_pago
        cotizacion.observaciones = observaciones
        
        mantencion.estado = EstadoMantencion.COTIZADA
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "cotizacion_recibida",
            "cotizacion_numero": cotizacion.numero,
            "total": str(cotizacion.total),
            "usuario": usuario
        })
        
        return cotizacion
    
    async def seleccionar_cotizacion(
        self,
        mantencion_id: str,
        cotizacion_id: str,
        motivo: str = "",
        usuario: str = "system"
    ) -> Mantencion:
        """Seleccionar cotización ganadora"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        cotizacion_seleccionada = None
        for c in mantencion.cotizaciones:
            if c.id == cotizacion_id:
                c.seleccionada = True
                cotizacion_seleccionada = c
            else:
                c.seleccionada = False
                if not c.motivo_rechazo:
                    c.motivo_rechazo = "No seleccionada"
        
        if not cotizacion_seleccionada:
            raise ValueError(f"Cotización {cotizacion_id} no encontrada")
        
        mantencion.cotizacion_seleccionada_id = cotizacion_id
        mantencion.proveedor_id = cotizacion_seleccionada.proveedor_id
        mantencion.presupuesto_estimado = cotizacion_seleccionada.total
        mantencion.estado = EstadoMantencion.APROBADA
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "cotizacion_seleccionada",
            "cotizacion_numero": cotizacion_seleccionada.numero,
            "total": str(cotizacion_seleccionada.total),
            "motivo": motivo,
            "usuario": usuario
        })
        
        return mantencion
    
    # =========================================================================
    # GESTIÓN DE ÓRDENES DE TRABAJO
    # =========================================================================
    
    async def generar_orden_trabajo(
        self,
        mantencion_id: str,
        fecha_programada: date,
        hora_inicio: str = "09:00",
        usuario: str = "system"
    ) -> OrdenTrabajo:
        """Generar orden de trabajo"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        if mantencion.estado != EstadoMantencion.APROBADA:
            raise ValueError("La mantención debe estar aprobada para generar OT")
        
        # Generar número
        self._contador_ot += 1
        year = datetime.now().year
        numero = f"OT-{year}-{self._contador_ot:06d}"
        
        ot = OrdenTrabajo(
            numero=numero,
            mantencion_id=mantencion_id,
            proveedor_id=mantencion.proveedor_id or "",
            cotizacion_id=mantencion.cotizacion_seleccionada_id,
            fecha_programada=fecha_programada,
            hora_inicio=hora_inicio
        )
        
        mantencion.orden_trabajo = ot
        mantencion.fecha_programada = fecha_programada
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "orden_trabajo_generada",
            "ot_numero": numero,
            "fecha_programada": fecha_programada.isoformat(),
            "usuario": usuario
        })
        
        logger.info(f"Orden de trabajo {numero} generada para {mantencion.codigo}")
        
        return ot
    
    async def registrar_ejecucion(
        self,
        mantencion_id: str,
        trabajos_realizados: str,
        materiales_utilizados: List[Dict[str, Any]],
        horas_trabajadas: Decimal,
        fotos_despues: List[str],
        usuario: str = "system"
    ) -> Mantencion:
        """Registrar ejecución de mantención"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        if not mantencion.orden_trabajo:
            raise ValueError("No existe orden de trabajo")
        
        ot = mantencion.orden_trabajo
        ot.trabajos_realizados = trabajos_realizados
        ot.materiales_utilizados = materiales_utilizados
        ot.horas_trabajadas = horas_trabajadas
        ot.fotos_despues = fotos_despues
        ot.fecha_termino_real = datetime.now()
        
        mantencion.estado = EstadoMantencion.EN_REVISION
        mantencion.fecha_termino = datetime.now()
        mantencion.fotos_solucion = fotos_despues
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "ejecucion_registrada",
            "trabajos": trabajos_realizados,
            "horas": str(horas_trabajadas),
            "usuario": usuario
        })
        
        return mantencion
    
    async def verificar_trabajo(
        self,
        mantencion_id: str,
        resultado: str,  # aprobado, observaciones, rechazado
        observaciones: str = "",
        usuario: str = "system"
    ) -> Mantencion:
        """Verificar trabajo realizado"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        mantencion.verificado = True
        mantencion.verificado_por = usuario
        mantencion.fecha_verificacion = date.today()
        mantencion.resultado_verificacion = resultado
        
        if mantencion.orden_trabajo:
            mantencion.orden_trabajo.verificado_por = usuario
            mantencion.orden_trabajo.fecha_verificacion = date.today()
            mantencion.orden_trabajo.resultado_verificacion = resultado
            mantencion.orden_trabajo.observaciones_verificacion = observaciones
        
        if resultado == "aprobado":
            mantencion.estado = EstadoMantencion.COMPLETADA
            
            # Configurar garantía del trabajo
            for cot in mantencion.cotizaciones:
                if cot.seleccionada and cot.garantia_meses > 0:
                    mantencion.garantia_meses = cot.garantia_meses
                    mantencion.garantia_hasta = date.today() + timedelta(
                        days=cot.garantia_meses * 30
                    )
        elif resultado == "rechazado":
            mantencion.estado = EstadoMantencion.EN_EJECUCION  # Volver a ejecutar
        
        mantencion.actualizado_en = datetime.now()
        
        mantencion.historial.append({
            "fecha": datetime.now().isoformat(),
            "evento": "verificacion",
            "resultado": resultado,
            "observaciones": observaciones,
            "usuario": usuario
        })
        
        return mantencion
    
    # =========================================================================
    # GESTIÓN DE PROVEEDORES
    # =========================================================================
    
    async def registrar_proveedor(
        self,
        tipo: TipoProveedor,
        razon_social: str,
        rut: str,
        categorias: List[CategoriaMantencion],
        contacto_nombre: str,
        email: str,
        telefono: str,
        direccion: str,
        comuna: str,
        usuario: str = "system"
    ) -> Proveedor:
        """Registrar nuevo proveedor"""
        # Generar código
        self._contador_proveedores += 1
        codigo = f"PROV-{self._contador_proveedores:04d}"
        
        proveedor = Proveedor(
            codigo=codigo,
            tipo=tipo,
            razon_social=razon_social,
            rut=rut,
            categorias=categorias,
            contacto_nombre=contacto_nombre,
            email=email,
            telefono=telefono,
            direccion=direccion,
            comuna=comuna
        )
        
        self._proveedores[proveedor.id] = proveedor
        
        logger.info(f"Proveedor {codigo} registrado: {razon_social}")
        
        return proveedor
    
    async def obtener_proveedor(self, proveedor_id: str) -> Optional[Proveedor]:
        """Obtener proveedor por ID o código"""
        if proveedor_id in self._proveedores:
            return self._proveedores[proveedor_id]
        
        for p in self._proveedores.values():
            if p.codigo == proveedor_id:
                return p
        
        return None
    
    async def listar_proveedores(
        self,
        categoria: Optional[CategoriaMantencion] = None,
        comuna: Optional[str] = None,
        estado: Optional[EstadoProveedor] = None,
        calificacion_minima: Optional[Decimal] = None
    ) -> List[Proveedor]:
        """Listar proveedores con filtros"""
        resultados = list(self._proveedores.values())
        
        if categoria:
            resultados = [p for p in resultados if categoria in p.categorias]
        
        if comuna:
            resultados = [p for p in resultados 
                         if comuna in p.zonas_cobertura or p.comuna == comuna]
        
        if estado:
            resultados = [p for p in resultados if p.estado == estado]
        
        if calificacion_minima:
            resultados = [p for p in resultados 
                         if p.calificacion_promedio >= calificacion_minima]
        
        # Ordenar por calificación
        resultados.sort(key=lambda p: p.calificacion_promedio, reverse=True)
        
        return resultados
    
    async def evaluar_proveedor(
        self,
        mantencion_id: str,
        calidad_trabajo: int,
        cumplimiento_plazo: int,
        precio_justo: int,
        limpieza: int,
        trato_personal: int,
        comunicacion: int,
        recomendaria: bool,
        comentarios: str = "",
        usuario: str = "system"
    ) -> EvaluacionProveedor:
        """Evaluar trabajo del proveedor"""
        mantencion = await self.obtener_mantencion(mantencion_id)
        if not mantencion:
            raise ValueError(f"Mantención {mantencion_id} no encontrada")
        
        if not mantencion.proveedor_id:
            raise ValueError("Mantención sin proveedor asignado")
        
        proveedor = await self.obtener_proveedor(mantencion.proveedor_id)
        if not proveedor:
            raise ValueError("Proveedor no encontrado")
        
        # Calcular promedio
        promedio = Decimal(str(
            (calidad_trabajo + cumplimiento_plazo + precio_justo + 
             limpieza + trato_personal + comunicacion) / 6
        )).quantize(Decimal("0.1"), ROUND_HALF_UP)
        
        evaluacion = EvaluacionProveedor(
            mantencion_id=mantencion_id,
            proveedor_id=mantencion.proveedor_id,
            orden_trabajo_id=mantencion.orden_trabajo.id if mantencion.orden_trabajo else "",
            evaluador=usuario,
            calidad_trabajo=calidad_trabajo,
            cumplimiento_plazo=cumplimiento_plazo,
            precio_justo=precio_justo,
            limpieza=limpieza,
            trato_personal=trato_personal,
            comunicacion=comunicacion,
            calificacion_promedio=promedio,
            recomendaria=recomendaria,
            comentarios=comentarios
        )
        
        mantencion.evaluacion = evaluacion
        
        # Actualizar estadísticas del proveedor
        proveedor.total_trabajos += 1
        if promedio >= Decimal("3.5"):
            proveedor.trabajos_satisfactorios += 1
        
        # Recalcular calificación promedio
        if proveedor.calificacion_promedio == 0:
            proveedor.calificacion_promedio = promedio
        else:
            # Promedio ponderado
            proveedor.calificacion_promedio = (
                (proveedor.calificacion_promedio * (proveedor.total_trabajos - 1) + promedio) /
                proveedor.total_trabajos
            ).quantize(Decimal("0.1"), ROUND_HALF_UP)
        
        proveedor.ultima_evaluacion = date.today()
        
        logger.info(f"Proveedor {proveedor.codigo} evaluado: {promedio}/5")
        
        return evaluacion
    
    # =========================================================================
    # PLANES DE MANTENCIÓN PREVENTIVA
    # =========================================================================
    
    async def crear_plan_preventivo(
        self,
        propiedad_id: str,
        nombre: str,
        descripcion: str,
        categoria: CategoriaMantencion,
        frecuencia: Frecuencia,
        tareas: List[str],
        equipo_sistema: str = "",
        proveedor_id: Optional[str] = None,
        costo_estimado_uf: Decimal = Decimal("0"),
        usuario: str = "system"
    ) -> PlanMantencionPreventiva:
        """Crear plan de mantención preventiva"""
        self._contador_planes += 1
        year = datetime.now().year
        codigo = f"PMP-{year}-{self._contador_planes:04d}"
        
        # Calcular próxima ejecución
        proxima = self._calcular_proxima_ejecucion(frecuencia, date.today())
        
        plan = PlanMantencionPreventiva(
            codigo=codigo,
            propiedad_id=propiedad_id,
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            equipo_sistema=equipo_sistema,
            frecuencia=frecuencia,
            proveedor_id=proveedor_id,
            proxima_ejecucion=proxima,
            tareas=tareas,
            costo_estimado_uf=costo_estimado_uf,
            creado_por=usuario
        )
        
        self._planes[plan.id] = plan
        
        logger.info(f"Plan preventivo {codigo} creado: {nombre}")
        
        return plan
    
    def _calcular_proxima_ejecucion(
        self, 
        frecuencia: Frecuencia, 
        desde: date
    ) -> date:
        """Calcular próxima fecha de ejecución"""
        dias = {
            Frecuencia.SEMANAL: 7,
            Frecuencia.QUINCENAL: 15,
            Frecuencia.MENSUAL: 30,
            Frecuencia.BIMENSUAL: 60,
            Frecuencia.TRIMESTRAL: 90,
            Frecuencia.CUATRIMESTRAL: 120,
            Frecuencia.SEMESTRAL: 180,
            Frecuencia.ANUAL: 365,
            Frecuencia.BIANUAL: 730
        }
        return desde + timedelta(days=dias.get(frecuencia, 365))
    
    async def obtener_planes_propiedad(
        self,
        propiedad_id: str,
        solo_activos: bool = True
    ) -> List[PlanMantencionPreventiva]:
        """Obtener planes de mantención de una propiedad"""
        planes = [p for p in self._planes.values() if p.propiedad_id == propiedad_id]
        
        if solo_activos:
            planes = [p for p in planes if p.activo]
        
        return planes
    
    async def ejecutar_plan_preventivo(
        self,
        plan_id: str,
        usuario: str = "system"
    ) -> Mantencion:
        """Generar mantención desde plan preventivo"""
        plan = self._planes.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} no encontrado")
        
        # Crear mantención
        mantencion = await self.crear_mantencion(
            propiedad_id=plan.propiedad_id,
            tipo=TipoMantencion.PREVENTIVA,
            categoria=plan.categoria,
            titulo=f"[Preventiva] {plan.nombre}",
            descripcion=plan.descripcion,
            prioridad=PrioridadMantencion.PLANIFICADA,
            usuario=usuario
        )
        
        mantencion.plan_preventivo_id = plan_id
        mantencion.presupuesto_estimado = plan.costo_estimado_uf * self._uf_actual
        
        if plan.proveedor_id:
            mantencion.proveedor_id = plan.proveedor_id
        
        # Actualizar plan
        plan.ultima_ejecucion = date.today()
        plan.proxima_ejecucion = self._calcular_proxima_ejecucion(
            plan.frecuencia, 
            date.today()
        )
        
        return mantencion
    
    # =========================================================================
    # GESTIÓN DE GARANTÍAS
    # =========================================================================
    
    async def registrar_garantia(
        self,
        propiedad_id: str,
        nombre_equipo: str,
        marca: str,
        modelo: str,
        numero_serie: str,
        ubicacion: str,
        tipo_garantia: str,
        proveedor_garantia: str,
        duracion: int,
        unidad: UnidadGarantia,
        fecha_inicio: date,
        cobertura_descripcion: str = "",
        telefono_garantia: str = "",
        usuario: str = "system"
    ) -> GarantiaEquipo:
        """Registrar garantía de equipo"""
        # Calcular fecha término
        if unidad == UnidadGarantia.DIAS:
            fecha_termino = fecha_inicio + timedelta(days=duracion)
        elif unidad == UnidadGarantia.MESES:
            fecha_termino = fecha_inicio + timedelta(days=duracion * 30)
        else:  # ANOS
            fecha_termino = fecha_inicio + timedelta(days=duracion * 365)
        
        garantia = GarantiaEquipo(
            propiedad_id=propiedad_id,
            nombre_equipo=nombre_equipo,
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie,
            ubicacion=ubicacion,
            tipo=tipo_garantia,
            proveedor_garantia=proveedor_garantia,
            duracion=duracion,
            unidad=unidad,
            fecha_inicio=fecha_inicio,
            fecha_termino=fecha_termino,
            cobertura_descripcion=cobertura_descripcion,
            telefono_garantia=telefono_garantia,
            vigente=fecha_termino >= date.today()
        )
        
        self._garantias[garantia.id] = garantia
        
        logger.info(f"Garantía registrada: {nombre_equipo} hasta {fecha_termino}")
        
        return garantia
    
    async def obtener_garantias_propiedad(
        self,
        propiedad_id: str,
        solo_vigentes: bool = True
    ) -> List[GarantiaEquipo]:
        """Obtener garantías de una propiedad"""
        garantias = [g for g in self._garantias.values() 
                    if g.propiedad_id == propiedad_id]
        
        # Actualizar vigencia
        hoy = date.today()
        for g in garantias:
            g.vigente = g.fecha_termino >= hoy
        
        if solo_vigentes:
            garantias = [g for g in garantias if g.vigente]
        
        return garantias
    
    async def obtener_garantias_por_vencer(
        self,
        dias_anticipacion: int = 30
    ) -> List[GarantiaEquipo]:
        """Obtener garantías próximas a vencer"""
        hoy = date.today()
        limite = hoy + timedelta(days=dias_anticipacion)
        
        return [
            g for g in self._garantias.values()
            if g.vigente and hoy <= g.fecha_termino <= limite
        ]
    
    # =========================================================================
    # REPORTES Y ESTADÍSTICAS
    # =========================================================================
    
    async def generar_reporte_mantenciones(
        self,
        propiedad_id: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generar reporte de mantenciones"""
        mantenciones = list(self._mantenciones.values())
        
        if propiedad_id:
            mantenciones = [m for m in mantenciones if m.propiedad_id == propiedad_id]
        
        if fecha_desde:
            mantenciones = [m for m in mantenciones 
                          if m.fecha_reporte.date() >= fecha_desde]
        
        if fecha_hasta:
            mantenciones = [m for m in mantenciones 
                          if m.fecha_reporte.date() <= fecha_hasta]
        
        # Estadísticas
        total = len(mantenciones)
        completadas = len([m for m in mantenciones if m.estado == EstadoMantencion.COMPLETADA])
        pendientes = len([m for m in mantenciones if m.estado in [
            EstadoMantencion.PENDIENTE, EstadoMantencion.PROGRAMADA
        ]])
        
        # Por tipo
        por_tipo = {}
        for m in mantenciones:
            tipo = m.tipo.value
            if tipo not in por_tipo:
                por_tipo[tipo] = {"cantidad": 0, "costo_total": Decimal("0")}
            por_tipo[tipo]["cantidad"] += 1
            por_tipo[tipo]["costo_total"] += m.costo_final
        
        # Por categoría
        por_categoria = {}
        for m in mantenciones:
            cat = m.categoria.value
            if cat not in por_categoria:
                por_categoria[cat] = {"cantidad": 0, "costo_total": Decimal("0")}
            por_categoria[cat]["cantidad"] += 1
            por_categoria[cat]["costo_total"] += m.costo_final
        
        # Costos
        costo_total = sum(m.costo_final for m in mantenciones)
        costo_promedio = costo_total / total if total > 0 else Decimal("0")
        
        return {
            "periodo": {
                "desde": fecha_desde.isoformat() if fecha_desde else None,
                "hasta": fecha_hasta.isoformat() if fecha_hasta else None
            },
            "resumen": {
                "total_mantenciones": total,
                "completadas": completadas,
                "pendientes": pendientes,
                "en_proceso": total - completadas - pendientes,
                "tasa_cumplimiento_pct": round(completadas / total * 100, 1) if total > 0 else 0
            },
            "costos": {
                "total_pesos": str(costo_total),
                "total_uf": str((costo_total / self._uf_actual).quantize(Decimal("0.01"))),
                "promedio_pesos": str(costo_promedio.quantize(Decimal("1")))
            },
            "por_tipo": {
                k: {"cantidad": v["cantidad"], "costo_total": str(v["costo_total"])}
                for k, v in por_tipo.items()
            },
            "por_categoria": {
                k: {"cantidad": v["cantidad"], "costo_total": str(v["costo_total"])}
                for k, v in por_categoria.items()
            }
        }
    
    async def obtener_calendario_mantenciones(
        self,
        propiedad_id: str,
        mes: int,
        ano: int
    ) -> List[Dict[str, Any]]:
        """Obtener calendario de mantenciones del mes"""
        inicio_mes = date(ano, mes, 1)
        if mes == 12:
            fin_mes = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            fin_mes = date(ano, mes + 1, 1) - timedelta(days=1)
        
        eventos = []
        
        # Mantenciones programadas
        for m in self._mantenciones.values():
            if m.propiedad_id == propiedad_id and m.fecha_programada:
                if inicio_mes <= m.fecha_programada <= fin_mes:
                    eventos.append({
                        "fecha": m.fecha_programada.isoformat(),
                        "tipo": "mantencion",
                        "titulo": m.titulo,
                        "codigo": m.codigo,
                        "categoria": m.categoria.value,
                        "prioridad": m.prioridad.value,
                        "estado": m.estado.value
                    })
        
        # Planes preventivos
        for p in self._planes.values():
            if p.propiedad_id == propiedad_id and p.activo and p.proxima_ejecucion:
                if inicio_mes <= p.proxima_ejecucion <= fin_mes:
                    eventos.append({
                        "fecha": p.proxima_ejecucion.isoformat(),
                        "tipo": "preventiva",
                        "titulo": f"[Preventiva] {p.nombre}",
                        "codigo": p.codigo,
                        "categoria": p.categoria.value,
                        "prioridad": "planificada",
                        "estado": "programada"
                    })
        
        # Garantías por vencer
        for g in self._garantias.values():
            if g.propiedad_id == propiedad_id and g.vigente:
                if inicio_mes <= g.fecha_termino <= fin_mes:
                    eventos.append({
                        "fecha": g.fecha_termino.isoformat(),
                        "tipo": "garantia_vence",
                        "titulo": f"Vence garantía: {g.nombre_equipo}",
                        "equipo": g.nombre_equipo,
                        "proveedor": g.proveedor_garantia
                    })
        
        # Ordenar por fecha
        eventos.sort(key=lambda e: e["fecha"])
        
        return eventos


# =============================================================================
# INSTANCIA SINGLETON
# =============================================================================

_mantenciones_service: Optional[MantencionesService] = None


def get_mantenciones_service() -> MantencionesService:
    """Obtener instancia singleton del servicio"""
    global _mantenciones_service
    if _mantenciones_service is None:
        _mantenciones_service = MantencionesService()
    return _mantenciones_service
