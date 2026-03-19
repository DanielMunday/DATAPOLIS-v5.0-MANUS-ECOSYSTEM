"""
DATAPOLIS v3.0 - M07 LIQUIDACIÓN CONCURSAL
==========================================
Módulo completo para gestión de liquidaciones según Ley 20.720

Funcionalidades:
- Liquidación voluntaria (Libro I)
- Liquidación forzosa (Libro II)
- Reorganización judicial (Libro III)
- Renegociación de persona deudora (Libro IV)
- Valorización de activos para liquidación
- Distribución de créditos por prelación
- Generación de informes para Superintendencia

Normativas:
- Ley 20.720: Reorganización y Liquidación de Empresas y Personas
- Reglamento DS 29/2014
- Instrucciones Superintendencia de Insolvencia y Reemprendimiento

Autor: DATAPOLIS SpA
Versión: 3.0.0
Fecha: Febrero 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import uuid
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMERACIONES
# ============================================================================

class TipoProcedimiento(str, Enum):
    """Tipos de procedimiento según Ley 20.720."""
    LIQUIDACION_VOLUNTARIA = "liquidacion_voluntaria"  # Libro I
    LIQUIDACION_FORZOSA = "liquidacion_forzosa"        # Libro II
    REORGANIZACION_JUDICIAL = "reorganizacion_judicial"  # Libro III
    RENEGOCIACION_PERSONA = "renegociacion_persona"    # Libro IV
    LIQUIDACION_SIMPLIFICADA = "liquidacion_simplificada"

class EstadoProcedimiento(str, Enum):
    """Estados del procedimiento concursal."""
    INICIADO = "iniciado"
    VERIFICACION_CREDITOS = "verificacion_creditos"
    REALIZACION_ACTIVOS = "realizacion_activos"
    DISTRIBUCION = "distribucion"
    CUENTA_FINAL = "cuenta_final"
    TERMINADO = "terminado"
    SUSPENDIDO = "suspendido"

class ClaseCredito(str, Enum):
    """Clases de créditos según prelación (Art. 2470+ Código Civil)."""
    PRIMERA_CLASE = "primera_clase"    # Laborales, previsión, etc.
    SEGUNDA_CLASE = "segunda_clase"    # Posadero, acarreador, prenda
    TERCERA_CLASE = "tercera_clase"    # Hipotecarios
    CUARTA_CLASE = "cuarta_clase"      # Fisco, administradores
    QUINTA_CLASE = "quinta_clase"      # Valistas/quirografarios

class TipoActivo(str, Enum):
    """Tipos de activos en liquidación."""
    INMUEBLE = "inmueble"
    VEHICULO = "vehiculo"
    MAQUINARIA = "maquinaria"
    INVENTARIO = "inventario"
    CUENTAS_COBRAR = "cuentas_por_cobrar"
    EFECTIVO = "efectivo"
    INVERSIONES = "inversiones"
    INTANGIBLES = "intangibles"
    OTROS = "otros"

class MetodoRealizacion(str, Enum):
    """Métodos de realización de activos."""
    SUBASTA_PUBLICA = "subasta_publica"
    VENTA_DIRECTA = "venta_directa"
    LICITACION_PRIVADA = "licitacion_privada"
    VENTA_UNIDAD_ECONOMICA = "venta_unidad_economica"
    DACION_PAGO = "dacion_en_pago"

# ============================================================================
# CONSTANTES LEGALES
# ============================================================================

# Plazos legales (días hábiles)
PLAZOS_LEY_20720 = {
    "verificacion_ordinaria": 30,      # Art. 170
    "verificacion_extraordinaria": 90,  # Art. 179
    "impugnacion_creditos": 10,        # Art. 174
    "resolucion_impugnacion": 10,      # Art. 176
    "realizacion_bienes": 120,         # Art. 203
    "cuenta_final": 30,                # Art. 49
    "objeciones_cuenta": 15,           # Art. 50
    "prescripcion_acciones": 365 * 2,  # 2 años
}

# Prelación de créditos según Código Civil
PRELACION_CREDITOS = {
    ClaseCredito.PRIMERA_CLASE: {
        "orden": 1,
        "descripcion": "Créditos laborales, previsionales, indemnizaciones",
        "limite": None,  # Sin límite
        "articulos": ["Art. 2472 CC", "Art. 61 Ley 20.720"]
    },
    ClaseCredito.SEGUNDA_CLASE: {
        "orden": 2,
        "descripcion": "Posadero, acarreador, prenda",
        "limite": "valor_bien",
        "articulos": ["Art. 2474 CC"]
    },
    ClaseCredito.TERCERA_CLASE: {
        "orden": 3,
        "descripcion": "Créditos hipotecarios",
        "limite": "valor_inmueble",
        "articulos": ["Art. 2477 CC"]
    },
    ClaseCredito.CUARTA_CLASE: {
        "orden": 4,
        "descripcion": "Fisco, instituciones públicas, administradores",
        "limite": None,
        "articulos": ["Art. 2481 CC"]
    },
    ClaseCredito.QUINTA_CLASE: {
        "orden": 5,
        "descripcion": "Créditos valistas o quirografarios",
        "limite": None,
        "articulos": ["Art. 2489 CC"]
    }
}

# Costos del procedimiento (Art. 39)
COSTOS_PROCEDIMIENTO = {
    "honorarios_liquidador_base": 0.02,  # 2% del total realizado
    "honorarios_liquidador_max": 0.05,   # 5% máximo
    "gastos_administracion": 0.03,       # 3% estimado
    "publicaciones": 50_000,             # CLP por publicación
    "inscripciones": 30_000,             # CLP por inscripción
}

# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class Deudor:
    """Información del deudor."""
    id: str
    rut: str
    nombre: str
    tipo: str  # "persona_natural" o "persona_juridica"
    domicilio: str
    actividad_economica: Optional[str] = None
    representante_legal: Optional[str] = None
    fecha_constitucion: Optional[date] = None
    capital_social: Optional[float] = None

@dataclass
class Credito:
    """Crédito verificado en el procedimiento."""
    id: str
    acreedor_rut: str
    acreedor_nombre: str
    monto_original: float
    monto_verificado: float
    clase: ClaseCredito
    garantia: Optional[str] = None
    bien_afecto: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    documentos: List[str] = field(default_factory=list)
    estado: str = "pendiente"  # pendiente, verificado, impugnado, rechazado
    
    @property
    def es_preferente(self) -> bool:
        """Verifica si es crédito preferente."""
        return self.clase in [
            ClaseCredito.PRIMERA_CLASE,
            ClaseCredito.SEGUNDA_CLASE,
            ClaseCredito.TERCERA_CLASE,
            ClaseCredito.CUARTA_CLASE
        ]

@dataclass
class ActivoLiquidacion:
    """Activo incluido en la liquidación."""
    id: str
    tipo: TipoActivo
    descripcion: str
    ubicacion: Optional[str] = None
    valor_libro: float = 0
    valor_tasacion: float = 0
    valor_realizacion: float = 0
    metodo_realizacion: Optional[MetodoRealizacion] = None
    gravamenes: List[str] = field(default_factory=list)
    estado: str = "inventariado"  # inventariado, tasado, en_venta, realizado
    fecha_realizacion: Optional[date] = None
    comprador: Optional[str] = None
    
    @property
    def valor_neto(self) -> float:
        """Valor neto después de gravámenes."""
        # Simplificación: asumir 80% del valor si tiene gravámenes
        if self.gravamenes:
            return self.valor_realizacion * 0.8
        return self.valor_realizacion

@dataclass
class ResultadoLiquidacion:
    """Resultado del proceso de liquidación."""
    procedimiento_id: str
    total_activos_realizados: float
    total_costos_procedimiento: float
    total_creditos_verificados: float
    total_pagado_primera_clase: float
    total_pagado_segunda_clase: float
    total_pagado_tercera_clase: float
    total_pagado_cuarta_clase: float
    total_pagado_quinta_clase: float
    porcentaje_recuperacion_valistas: float
    remanente: float
    fecha_calculo: datetime = field(default_factory=datetime.now)
    
    @property
    def total_pagado(self) -> float:
        return (
            self.total_pagado_primera_clase +
            self.total_pagado_segunda_clase +
            self.total_pagado_tercera_clase +
            self.total_pagado_cuarta_clase +
            self.total_pagado_quinta_clase
        )

@dataclass
class ProcedimientoConcursal:
    """Procedimiento concursal completo."""
    id: str
    tipo: TipoProcedimiento
    deudor: Deudor
    estado: EstadoProcedimiento
    fecha_inicio: date
    fecha_resolucion: Optional[date] = None
    liquidador: Optional[str] = None
    tribunal: Optional[str] = None
    rol_causa: Optional[str] = None
    creditos: List[Credito] = field(default_factory=list)
    activos: List[ActivoLiquidacion] = field(default_factory=list)
    resultado: Optional[ResultadoLiquidacion] = None

# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================

class LiquidacionConcursalService:
    """
    Servicio de Liquidación Concursal según Ley 20.720.
    
    Implementa:
    - Gestión de procedimientos concursales
    - Verificación de créditos
    - Inventario y realización de activos
    - Distribución según prelación legal
    - Generación de informes para Superintendencia
    """
    
    def __init__(self):
        self.procedimientos: Dict[str, ProcedimientoConcursal] = {}
        self.version = "3.0.0"
    
    # ========================================================================
    # GESTIÓN DE PROCEDIMIENTOS
    # ========================================================================
    
    def iniciar_procedimiento(
        self,
        tipo: TipoProcedimiento,
        deudor: Deudor,
        liquidador: str,
        tribunal: str,
        rol_causa: str
    ) -> ProcedimientoConcursal:
        """
        Inicia un nuevo procedimiento concursal.
        
        Args:
            tipo: Tipo de procedimiento según Ley 20.720
            deudor: Información del deudor
            liquidador: Nombre del liquidador designado
            tribunal: Tribunal competente
            rol_causa: Rol de la causa
        
        Returns:
            Procedimiento concursal creado
        """
        procedimiento_id = str(uuid.uuid4())[:8].upper()
        
        procedimiento = ProcedimientoConcursal(
            id=procedimiento_id,
            tipo=tipo,
            deudor=deudor,
            estado=EstadoProcedimiento.INICIADO,
            fecha_inicio=date.today(),
            liquidador=liquidador,
            tribunal=tribunal,
            rol_causa=rol_causa
        )
        
        self.procedimientos[procedimiento_id] = procedimiento
        
        logger.info(f"Procedimiento {procedimiento_id} iniciado: {tipo.value}")
        
        return procedimiento
    
    def cambiar_estado(
        self,
        procedimiento_id: str,
        nuevo_estado: EstadoProcedimiento
    ) -> ProcedimientoConcursal:
        """Cambia el estado de un procedimiento."""
        proc = self._get_procedimiento(procedimiento_id)
        proc.estado = nuevo_estado
        
        if nuevo_estado == EstadoProcedimiento.TERMINADO:
            proc.fecha_resolucion = date.today()
        
        logger.info(f"Procedimiento {procedimiento_id}: {nuevo_estado.value}")
        return proc
    
    # ========================================================================
    # VERIFICACIÓN DE CRÉDITOS
    # ========================================================================
    
    def verificar_credito(
        self,
        procedimiento_id: str,
        acreedor_rut: str,
        acreedor_nombre: str,
        monto: float,
        clase: ClaseCredito,
        garantia: Optional[str] = None,
        bien_afecto: Optional[str] = None,
        documentos: List[str] = None
    ) -> Credito:
        """
        Verifica un crédito en el procedimiento (Art. 170-179).
        
        Args:
            procedimiento_id: ID del procedimiento
            acreedor_rut: RUT del acreedor
            acreedor_nombre: Nombre del acreedor
            monto: Monto del crédito
            clase: Clase de crédito según prelación
            garantia: Tipo de garantía si aplica
            bien_afecto: Bien afecto a la garantía
            documentos: Documentos de respaldo
        
        Returns:
            Crédito verificado
        """
        proc = self._get_procedimiento(procedimiento_id)
        
        credito = Credito(
            id=str(uuid.uuid4())[:8].upper(),
            acreedor_rut=acreedor_rut,
            acreedor_nombre=acreedor_nombre,
            monto_original=monto,
            monto_verificado=monto,
            clase=clase,
            garantia=garantia,
            bien_afecto=bien_afecto,
            documentos=documentos or [],
            estado="verificado"
        )
        
        proc.creditos.append(credito)
        
        logger.info(
            f"Crédito verificado: {acreedor_nombre} - "
            f"${monto:,.0f} ({clase.value})"
        )
        
        return credito
    
    def impugnar_credito(
        self,
        procedimiento_id: str,
        credito_id: str,
        motivo: str,
        monto_propuesto: Optional[float] = None
    ) -> Credito:
        """
        Impugna un crédito verificado (Art. 174-176).
        """
        proc = self._get_procedimiento(procedimiento_id)
        credito = self._get_credito(proc, credito_id)
        
        credito.estado = "impugnado"
        if monto_propuesto is not None:
            credito.monto_verificado = monto_propuesto
        
        logger.info(f"Crédito {credito_id} impugnado: {motivo}")
        return credito
    
    def obtener_nomina_creditos(
        self,
        procedimiento_id: str
    ) -> Dict[ClaseCredito, List[Credito]]:
        """
        Obtiene nómina de créditos agrupada por clase.
        """
        proc = self._get_procedimiento(procedimiento_id)
        
        nomina = {clase: [] for clase in ClaseCredito}
        for credito in proc.creditos:
            if credito.estado == "verificado":
                nomina[credito.clase].append(credito)
        
        # Ordenar por monto dentro de cada clase
        for clase in nomina:
            nomina[clase].sort(key=lambda c: c.monto_verificado, reverse=True)
        
        return nomina
    
    def calcular_total_creditos(
        self,
        procedimiento_id: str
    ) -> Dict[str, float]:
        """
        Calcula totales de créditos por clase.
        """
        nomina = self.obtener_nomina_creditos(procedimiento_id)
        
        totales = {
            "primera_clase": sum(c.monto_verificado for c in nomina[ClaseCredito.PRIMERA_CLASE]),
            "segunda_clase": sum(c.monto_verificado for c in nomina[ClaseCredito.SEGUNDA_CLASE]),
            "tercera_clase": sum(c.monto_verificado for c in nomina[ClaseCredito.TERCERA_CLASE]),
            "cuarta_clase": sum(c.monto_verificado for c in nomina[ClaseCredito.CUARTA_CLASE]),
            "quinta_clase": sum(c.monto_verificado for c in nomina[ClaseCredito.QUINTA_CLASE]),
        }
        totales["total"] = sum(totales.values())
        totales["preferentes"] = totales["total"] - totales["quinta_clase"]
        
        return totales
    
    # ========================================================================
    # INVENTARIO Y REALIZACIÓN DE ACTIVOS
    # ========================================================================
    
    def agregar_activo(
        self,
        procedimiento_id: str,
        tipo: TipoActivo,
        descripcion: str,
        valor_libro: float,
        ubicacion: Optional[str] = None,
        gravamenes: List[str] = None
    ) -> ActivoLiquidacion:
        """
        Agrega un activo al inventario del procedimiento.
        """
        proc = self._get_procedimiento(procedimiento_id)
        
        activo = ActivoLiquidacion(
            id=str(uuid.uuid4())[:8].upper(),
            tipo=tipo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            valor_libro=valor_libro,
            gravamenes=gravamenes or []
        )
        
        proc.activos.append(activo)
        
        logger.info(f"Activo agregado: {descripcion} - ${valor_libro:,.0f}")
        return activo
    
    def tasar_activo(
        self,
        procedimiento_id: str,
        activo_id: str,
        valor_tasacion: float,
        tasador: str
    ) -> ActivoLiquidacion:
        """
        Registra tasación de un activo.
        """
        proc = self._get_procedimiento(procedimiento_id)
        activo = self._get_activo(proc, activo_id)
        
        activo.valor_tasacion = valor_tasacion
        activo.estado = "tasado"
        
        logger.info(f"Activo {activo_id} tasado: ${valor_tasacion:,.0f} por {tasador}")
        return activo
    
    def realizar_activo(
        self,
        procedimiento_id: str,
        activo_id: str,
        metodo: MetodoRealizacion,
        valor_realizacion: float,
        comprador: str
    ) -> ActivoLiquidacion:
        """
        Registra la realización (venta) de un activo (Art. 203+).
        """
        proc = self._get_procedimiento(procedimiento_id)
        activo = self._get_activo(proc, activo_id)
        
        activo.metodo_realizacion = metodo
        activo.valor_realizacion = valor_realizacion
        activo.comprador = comprador
        activo.fecha_realizacion = date.today()
        activo.estado = "realizado"
        
        logger.info(
            f"Activo {activo_id} realizado: ${valor_realizacion:,.0f} - "
            f"{metodo.value} a {comprador}"
        )
        return activo
    
    def calcular_total_activos(
        self,
        procedimiento_id: str
    ) -> Dict[str, float]:
        """
        Calcula totales de activos del procedimiento.
        """
        proc = self._get_procedimiento(procedimiento_id)
        
        return {
            "valor_libro": sum(a.valor_libro for a in proc.activos),
            "valor_tasacion": sum(a.valor_tasacion for a in proc.activos if a.valor_tasacion),
            "valor_realizado": sum(a.valor_realizacion for a in proc.activos if a.valor_realizacion),
            "pendientes_realizar": sum(
                a.valor_tasacion or a.valor_libro 
                for a in proc.activos 
                if a.estado != "realizado"
            ),
            "cantidad_activos": len(proc.activos),
            "cantidad_realizados": sum(1 for a in proc.activos if a.estado == "realizado")
        }
    
    # ========================================================================
    # DISTRIBUCIÓN DE FONDOS
    # ========================================================================
    
    def calcular_distribucion(
        self,
        procedimiento_id: str
    ) -> ResultadoLiquidacion:
        """
        Calcula la distribución de fondos según prelación legal.
        
        Orden de prelación (Art. 2470+ Código Civil):
        1. Primera clase: Laborales, previsionales (Art. 2472)
        2. Segunda clase: Prenda, posadero (Art. 2474)
        3. Tercera clase: Hipotecarios (Art. 2477)
        4. Cuarta clase: Fisco, administradores (Art. 2481)
        5. Quinta clase: Valistas/quirografarios (Art. 2489)
        """
        proc = self._get_procedimiento(procedimiento_id)
        
        # Total realizado
        total_activos = sum(
            a.valor_realizacion for a in proc.activos 
            if a.estado == "realizado"
        )
        
        # Costos del procedimiento (Art. 39)
        costos = self._calcular_costos_procedimiento(total_activos)
        
        # Fondos disponibles para distribución
        fondos_disponibles = total_activos - costos
        
        # Totales por clase
        totales_creditos = self.calcular_total_creditos(procedimiento_id)
        
        # Distribución según prelación
        pagos = {
            "primera": 0.0,
            "segunda": 0.0,
            "tercera": 0.0,
            "cuarta": 0.0,
            "quinta": 0.0
        }
        
        remanente = fondos_disponibles
        
        # Primera clase: 100% si hay fondos
        if remanente > 0:
            pago = min(remanente, totales_creditos["primera_clase"])
            pagos["primera"] = pago
            remanente -= pago
        
        # Segunda clase: según bien afecto
        if remanente > 0:
            pago = min(remanente, totales_creditos["segunda_clase"])
            pagos["segunda"] = pago
            remanente -= pago
        
        # Tercera clase: según inmueble hipotecado
        if remanente > 0:
            pago = min(remanente, totales_creditos["tercera_clase"])
            pagos["tercera"] = pago
            remanente -= pago
        
        # Cuarta clase
        if remanente > 0:
            pago = min(remanente, totales_creditos["cuarta_clase"])
            pagos["cuarta"] = pago
            remanente -= pago
        
        # Quinta clase: a prorrata
        if remanente > 0:
            pago = min(remanente, totales_creditos["quinta_clase"])
            pagos["quinta"] = pago
            remanente -= pago
        
        # Porcentaje de recuperación para valistas
        if totales_creditos["quinta_clase"] > 0:
            pct_valistas = (pagos["quinta"] / totales_creditos["quinta_clase"]) * 100
        else:
            pct_valistas = 0
        
        resultado = ResultadoLiquidacion(
            procedimiento_id=procedimiento_id,
            total_activos_realizados=total_activos,
            total_costos_procedimiento=costos,
            total_creditos_verificados=totales_creditos["total"],
            total_pagado_primera_clase=pagos["primera"],
            total_pagado_segunda_clase=pagos["segunda"],
            total_pagado_tercera_clase=pagos["tercera"],
            total_pagado_cuarta_clase=pagos["cuarta"],
            total_pagado_quinta_clase=pagos["quinta"],
            porcentaje_recuperacion_valistas=round(pct_valistas, 2),
            remanente=remanente
        )
        
        proc.resultado = resultado
        
        logger.info(
            f"Distribución calculada: Total ${total_activos:,.0f}, "
            f"Pagado ${resultado.total_pagado:,.0f}, "
            f"Valistas {pct_valistas:.1f}%"
        )
        
        return resultado
    
    def _calcular_costos_procedimiento(self, total_realizado: float) -> float:
        """Calcula costos del procedimiento según Art. 39."""
        # Honorarios liquidador (2-5% del total)
        honorarios = total_realizado * COSTOS_PROCEDIMIENTO["honorarios_liquidador_base"]
        
        # Gastos de administración (3% estimado)
        gastos = total_realizado * COSTOS_PROCEDIMIENTO["gastos_administracion"]
        
        # Publicaciones e inscripciones
        otros = (
            COSTOS_PROCEDIMIENTO["publicaciones"] * 5 +  # ~5 publicaciones
            COSTOS_PROCEDIMIENTO["inscripciones"] * 3    # ~3 inscripciones
        )
        
        return honorarios + gastos + otros
    
    def generar_proyecto_reparto(
        self,
        procedimiento_id: str
    ) -> Dict[str, Any]:
        """
        Genera proyecto de reparto para aprobación judicial.
        """
        proc = self._get_procedimiento(procedimiento_id)
        resultado = proc.resultado or self.calcular_distribucion(procedimiento_id)
        nomina = self.obtener_nomina_creditos(procedimiento_id)
        
        reparto = {
            "procedimiento_id": procedimiento_id,
            "fecha_proyecto": date.today().isoformat(),
            "deudor": {
                "rut": proc.deudor.rut,
                "nombre": proc.deudor.nombre
            },
            "resumen": {
                "total_activos_realizados": resultado.total_activos_realizados,
                "total_costos": resultado.total_costos_procedimiento,
                "fondos_distribuibles": resultado.total_activos_realizados - resultado.total_costos_procedimiento,
                "total_creditos": resultado.total_creditos_verificados
            },
            "distribucion_por_clase": [],
            "detalle_acreedores": []
        }
        
        # Distribución por clase
        clases = [
            ("Primera Clase (Laborales)", ClaseCredito.PRIMERA_CLASE, resultado.total_pagado_primera_clase),
            ("Segunda Clase (Prenda)", ClaseCredito.SEGUNDA_CLASE, resultado.total_pagado_segunda_clase),
            ("Tercera Clase (Hipotecarios)", ClaseCredito.TERCERA_CLASE, resultado.total_pagado_tercera_clase),
            ("Cuarta Clase (Fisco)", ClaseCredito.CUARTA_CLASE, resultado.total_pagado_cuarta_clase),
            ("Quinta Clase (Valistas)", ClaseCredito.QUINTA_CLASE, resultado.total_pagado_quinta_clase),
        ]
        
        for nombre, clase, total_pagado in clases:
            creditos_clase = nomina.get(clase, [])
            total_creditos = sum(c.monto_verificado for c in creditos_clase)
            
            if total_creditos > 0:
                pct_pago = (total_pagado / total_creditos) * 100
            else:
                pct_pago = 0
            
            reparto["distribucion_por_clase"].append({
                "clase": nombre,
                "total_creditos": total_creditos,
                "total_a_pagar": total_pagado,
                "porcentaje_pago": round(pct_pago, 2),
                "cantidad_acreedores": len(creditos_clase)
            })
            
            # Detalle por acreedor
            for credito in creditos_clase:
                if total_creditos > 0:
                    pago_individual = (credito.monto_verificado / total_creditos) * total_pagado
                else:
                    pago_individual = 0
                
                reparto["detalle_acreedores"].append({
                    "clase": nombre,
                    "acreedor_rut": credito.acreedor_rut,
                    "acreedor_nombre": credito.acreedor_nombre,
                    "credito_verificado": credito.monto_verificado,
                    "monto_a_pagar": round(pago_individual, 0),
                    "porcentaje_recuperacion": round(
                        (pago_individual / credito.monto_verificado * 100) if credito.monto_verificado > 0 else 0, 2
                    )
                })
        
        return reparto
    
    # ========================================================================
    # INFORMES Y REPORTES
    # ========================================================================
    
    def generar_informe_superintendencia(
        self,
        procedimiento_id: str
    ) -> Dict[str, Any]:
        """
        Genera informe para Superintendencia de Insolvencia y Reemprendimiento.
        """
        proc = self._get_procedimiento(procedimiento_id)
        totales_activos = self.calcular_total_activos(procedimiento_id)
        totales_creditos = self.calcular_total_creditos(procedimiento_id)
        
        return {
            "encabezado": {
                "tipo_informe": "Informe Periódico Liquidador",
                "procedimiento_id": proc.id,
                "tipo_procedimiento": proc.tipo.value,
                "tribunal": proc.tribunal,
                "rol_causa": proc.rol_causa,
                "liquidador": proc.liquidador,
                "fecha_informe": date.today().isoformat()
            },
            "deudor": {
                "rut": proc.deudor.rut,
                "nombre": proc.deudor.nombre,
                "tipo": proc.deudor.tipo,
                "actividad": proc.deudor.actividad_economica
            },
            "estado_procedimiento": {
                "estado_actual": proc.estado.value,
                "fecha_inicio": proc.fecha_inicio.isoformat(),
                "dias_transcurridos": (date.today() - proc.fecha_inicio).days
            },
            "activos": {
                "total_inventariados": totales_activos["cantidad_activos"],
                "total_realizados": totales_activos["cantidad_realizados"],
                "valor_libro": totales_activos["valor_libro"],
                "valor_tasacion": totales_activos["valor_tasacion"],
                "valor_realizado": totales_activos["valor_realizado"],
                "pendientes": totales_activos["pendientes_realizar"]
            },
            "creditos": {
                "total_verificados": len([c for c in proc.creditos if c.estado == "verificado"]),
                "monto_primera_clase": totales_creditos["primera_clase"],
                "monto_segunda_clase": totales_creditos["segunda_clase"],
                "monto_tercera_clase": totales_creditos["tercera_clase"],
                "monto_cuarta_clase": totales_creditos["cuarta_clase"],
                "monto_quinta_clase": totales_creditos["quinta_clase"],
                "monto_total": totales_creditos["total"]
            },
            "proyeccion": {
                "recuperacion_estimada_valistas": self._estimar_recuperacion_valistas(proc)
            }
        }
    
    def _estimar_recuperacion_valistas(self, proc: ProcedimientoConcursal) -> float:
        """Estima porcentaje de recuperación para acreedores valistas."""
        totales_activos = self.calcular_total_activos(proc.id)
        totales_creditos = self.calcular_total_creditos(proc.id)
        
        # Valor estimado a realizar
        valor_estimado = totales_activos["valor_tasacion"] or totales_activos["valor_libro"]
        
        # Costos estimados
        costos = self._calcular_costos_procedimiento(valor_estimado)
        
        # Fondos disponibles
        fondos = valor_estimado - costos
        
        # Pagar preferentes primero
        fondos -= totales_creditos["preferentes"]
        
        # Lo que queda para valistas
        if fondos > 0 and totales_creditos["quinta_clase"] > 0:
            return min(100, (fondos / totales_creditos["quinta_clase"]) * 100)
        return 0
    
    def generar_cuenta_final(
        self,
        procedimiento_id: str
    ) -> Dict[str, Any]:
        """
        Genera cuenta final del liquidador (Art. 49-51).
        """
        proc = self._get_procedimiento(procedimiento_id)
        resultado = proc.resultado or self.calcular_distribucion(procedimiento_id)
        
        return {
            "titulo": "CUENTA FINAL DE ADMINISTRACIÓN",
            "procedimiento": {
                "id": proc.id,
                "tipo": proc.tipo.value,
                "deudor": proc.deudor.nombre,
                "tribunal": proc.tribunal,
                "rol": proc.rol_causa
            },
            "periodo": {
                "fecha_inicio": proc.fecha_inicio.isoformat(),
                "fecha_termino": date.today().isoformat(),
                "dias_totales": (date.today() - proc.fecha_inicio).days
            },
            "resumen_activos": {
                "inventariados": len(proc.activos),
                "realizados": sum(1 for a in proc.activos if a.estado == "realizado"),
                "valor_total_realizado": resultado.total_activos_realizados
            },
            "resumen_pasivos": {
                "creditos_verificados": len([c for c in proc.creditos if c.estado == "verificado"]),
                "monto_total_creditos": resultado.total_creditos_verificados
            },
            "distribucion_efectuada": {
                "primera_clase": resultado.total_pagado_primera_clase,
                "segunda_clase": resultado.total_pagado_segunda_clase,
                "tercera_clase": resultado.total_pagado_tercera_clase,
                "cuarta_clase": resultado.total_pagado_cuarta_clase,
                "quinta_clase": resultado.total_pagado_quinta_clase,
                "total_distribuido": resultado.total_pagado
            },
            "costos_procedimiento": resultado.total_costos_procedimiento,
            "remanente": resultado.remanente,
            "porcentaje_recuperacion_valistas": resultado.porcentaje_recuperacion_valistas,
            "observaciones": self._generar_observaciones_cuenta(proc, resultado),
            "fecha_cuenta": date.today().isoformat(),
            "liquidador": proc.liquidador
        }
    
    def _generar_observaciones_cuenta(
        self,
        proc: ProcedimientoConcursal,
        resultado: ResultadoLiquidacion
    ) -> List[str]:
        """Genera observaciones para la cuenta final."""
        obs = []
        
        # Recuperación valistas
        if resultado.porcentaje_recuperacion_valistas < 10:
            obs.append(
                f"Baja recuperación para acreedores valistas ({resultado.porcentaje_recuperacion_valistas}%). "
                "El pasivo superó significativamente el activo realizado."
            )
        elif resultado.porcentaje_recuperacion_valistas >= 50:
            obs.append(
                f"Recuperación favorable para valistas ({resultado.porcentaje_recuperacion_valistas}%)."
            )
        
        # Remanente
        if resultado.remanente > 0:
            obs.append(
                f"Existe remanente de ${resultado.remanente:,.0f} a devolver al deudor "
                "tras el pago íntegro de todos los créditos."
            )
        
        # Primera clase
        if resultado.total_pagado_primera_clase < self.calcular_total_creditos(proc.id)["primera_clase"]:
            obs.append(
                "Los créditos de primera clase (laborales/previsionales) no fueron pagados íntegramente."
            )
        
        return obs
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def _get_procedimiento(self, procedimiento_id: str) -> ProcedimientoConcursal:
        """Obtiene un procedimiento por ID."""
        if procedimiento_id not in self.procedimientos:
            raise ValueError(f"Procedimiento {procedimiento_id} no encontrado")
        return self.procedimientos[procedimiento_id]
    
    def _get_credito(self, proc: ProcedimientoConcursal, credito_id: str) -> Credito:
        """Obtiene un crédito por ID."""
        for credito in proc.creditos:
            if credito.id == credito_id:
                return credito
        raise ValueError(f"Crédito {credito_id} no encontrado")
    
    def _get_activo(self, proc: ProcedimientoConcursal, activo_id: str) -> ActivoLiquidacion:
        """Obtiene un activo por ID."""
        for activo in proc.activos:
            if activo.id == activo_id:
                return activo
        raise ValueError(f"Activo {activo_id} no encontrado")
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna información del módulo."""
        return {
            "modulo": "M07 - Liquidación Concursal",
            "version": self.version,
            "normativa": "Ley 20.720",
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
            "clases_creditos": list(ClaseCredito),
            "tipos_procedimiento": list(TipoProcedimiento),
            "plazos_legales": PLAZOS_LEY_20720
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

def ejemplo_liquidacion():
    """Ejemplo completo de uso del módulo de liquidación."""
    servicio = LiquidacionConcursalService()
    
    # Crear deudor
    deudor = Deudor(
        id="D001",
        rut="76.123.456-7",
        nombre="Constructora XYZ Ltda.",
        tipo="persona_juridica",
        domicilio="Av. Providencia 1234, Santiago",
        actividad_economica="Construcción",
        capital_social=500_000_000
    )
    
    # Iniciar procedimiento
    proc = servicio.iniciar_procedimiento(
        tipo=TipoProcedimiento.LIQUIDACION_VOLUNTARIA,
        deudor=deudor,
        liquidador="Juan Pérez González",
        tribunal="1° Juzgado Civil de Santiago",
        rol_causa="C-1234-2026"
    )
    
    print(f"Procedimiento iniciado: {proc.id}")
    
    # Agregar activos
    servicio.agregar_activo(
        proc.id,
        TipoActivo.INMUEBLE,
        "Oficina comercial 150m2",
        valor_libro=180_000_000,
        ubicacion="Las Condes",
        gravamenes=["Hipoteca Banco Estado"]
    )
    
    servicio.agregar_activo(
        proc.id,
        TipoActivo.VEHICULO,
        "Camioneta Toyota Hilux 2022",
        valor_libro=25_000_000
    )
    
    servicio.agregar_activo(
        proc.id,
        TipoActivo.MAQUINARIA,
        "Grúa torre Liebherr",
        valor_libro=80_000_000
    )
    
    # Tasar activos
    servicio.tasar_activo(proc.id, proc.activos[0].id, 150_000_000, "Tasador Autorizado")
    servicio.tasar_activo(proc.id, proc.activos[1].id, 22_000_000, "Tasador Autorizado")
    servicio.tasar_activo(proc.id, proc.activos[2].id, 60_000_000, "Tasador Autorizado")
    
    # Realizar activos
    servicio.realizar_activo(
        proc.id, proc.activos[0].id,
        MetodoRealizacion.SUBASTA_PUBLICA,
        145_000_000, "Inversiones ABC"
    )
    servicio.realizar_activo(
        proc.id, proc.activos[1].id,
        MetodoRealizacion.VENTA_DIRECTA,
        20_000_000, "Juan Martínez"
    )
    servicio.realizar_activo(
        proc.id, proc.activos[2].id,
        MetodoRealizacion.LICITACION_PRIVADA,
        55_000_000, "Constructora DEF"
    )
    
    # Verificar créditos
    servicio.verificar_credito(
        proc.id, "12.345.678-9", "Pedro Trabajador",
        15_000_000, ClaseCredito.PRIMERA_CLASE
    )
    servicio.verificar_credito(
        proc.id, "98.765.432-1", "María Obrera",
        8_000_000, ClaseCredito.PRIMERA_CLASE
    )
    servicio.verificar_credito(
        proc.id, "97.020.000-5", "Banco Estado",
        120_000_000, ClaseCredito.TERCERA_CLASE,
        garantia="Hipoteca", bien_afecto="Oficina comercial"
    )
    servicio.verificar_credito(
        proc.id, "60.910.000-1", "Tesorería General",
        12_000_000, ClaseCredito.CUARTA_CLASE
    )
    servicio.verificar_credito(
        proc.id, "76.100.200-3", "Proveedor Materiales SA",
        45_000_000, ClaseCredito.QUINTA_CLASE
    )
    servicio.verificar_credito(
        proc.id, "76.200.300-4", "Subcontratista Eléctrico",
        30_000_000, ClaseCredito.QUINTA_CLASE
    )
    
    # Calcular distribución
    resultado = servicio.calcular_distribucion(proc.id)
    
    print(f"\n=== RESULTADO LIQUIDACIÓN ===")
    print(f"Total activos realizados: ${resultado.total_activos_realizados:,.0f}")
    print(f"Costos procedimiento: ${resultado.total_costos_procedimiento:,.0f}")
    print(f"Total créditos: ${resultado.total_creditos_verificados:,.0f}")
    print(f"Recuperación valistas: {resultado.porcentaje_recuperacion_valistas}%")
    
    # Generar proyecto de reparto
    reparto = servicio.generar_proyecto_reparto(proc.id)
    print(f"\n=== PROYECTO DE REPARTO ===")
    for clase in reparto["distribucion_por_clase"]:
        print(f"{clase['clase']}: ${clase['total_a_pagar']:,.0f} ({clase['porcentaje_pago']}%)")
    
    return servicio


if __name__ == "__main__":
    ejemplo_liquidacion()
