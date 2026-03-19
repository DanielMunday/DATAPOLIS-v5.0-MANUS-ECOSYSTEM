"""
DATAPOLIS v3.0 - Router M05: Arriendos
======================================
API REST para gestión integral de arriendos inmobiliarios.

Endpoints:
- Gestión de contratos (CRUD)
- Cobros y pagos mensuales
- Proceso Ley 21.461
- Garantías
- Análisis de rentabilidad
- Reportes y estadísticas

Autor: DATAPOLIS SpA
Versión: 3.0.0
"""

from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime
from enum import Enum

from app.services.m05_arriendos import (
    get_arriendos_service,
    ArriendosService,
    TipoContrato,
    EstadoContrato,
    TipoReajuste,
    TipoGarantia,
    EstadoPago,
    MotivoTermino,
    EtapaLey21461,
    PersonaArriendo,
    PropiedadArriendo,
    ConfiguracionReajuste,
    ContratoArriendo,
    CobroArriendo,
    Garantia,
    ProcesoLey21461,
    AnalisisRentabilidad
)

router = APIRouter(
    prefix="/arriendos",
    tags=["M05 - Arriendos"],
    responses={
        404: {"description": "No encontrado"},
        400: {"description": "Datos inválidos"},
        500: {"description": "Error interno"}
    }
)


# =============================================================================
# SCHEMAS DE REQUEST
# =============================================================================

class PersonaInput(BaseModel):
    """Datos de persona (arrendador/arrendatario)"""
    rut: str = Field(..., description="RUT con formato XX.XXX.XXX-X")
    nombre_completo: str = Field(..., min_length=3, max_length=200)
    email: str = Field(..., description="Email de contacto")
    telefono: str = Field(..., description="Teléfono de contacto")
    direccion: str = Field(..., description="Dirección particular")
    comuna: str = Field(..., description="Comuna de residencia")
    nacionalidad: str = Field(default="Chilena")
    estado_civil: Optional[str] = None
    profesion: Optional[str] = None
    empleador: Optional[str] = None
    renta_mensual: Optional[Decimal] = Field(None, description="Renta mensual en pesos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rut": "12.345.678-9",
                "nombre_completo": "Juan Pérez González",
                "email": "juan.perez@email.com",
                "telefono": "+56912345678",
                "direccion": "Av. Providencia 1234, Depto 501",
                "comuna": "Providencia",
                "nacionalidad": "Chilena",
                "estado_civil": "Soltero",
                "profesion": "Ingeniero",
                "empleador": "Empresa ABC",
                "renta_mensual": 2500000
            }
        }


class PropiedadInput(BaseModel):
    """Datos de la propiedad"""
    expediente_id: Optional[str] = Field(None, description="ID Expediente M00")
    ficha_propiedad_id: Optional[str] = Field(None, description="ID Ficha M01")
    rol_sii: str = Field(..., description="Rol SII de la propiedad")
    direccion_completa: str = Field(..., description="Dirección completa")
    numero: str = Field(..., description="Número")
    departamento: Optional[str] = Field(None, description="Número departamento")
    comuna: str = Field(..., description="Comuna")
    region: str = Field(default="Metropolitana")
    tipo: str = Field(..., description="Tipo: departamento, casa, oficina, etc.")
    superficie_util_m2: Decimal = Field(..., gt=0)
    dormitorios: int = Field(default=0, ge=0)
    banos: int = Field(default=0, ge=0)
    estacionamientos: int = Field(default=0, ge=0)
    bodega: bool = Field(default=False)
    bodega_m2: Decimal = Field(default=Decimal("0"), ge=0)
    piso: Optional[int] = None
    orientacion: Optional[str] = None
    amoblado: bool = Field(default=False)
    estado_conservacion: str = Field(default="bueno")
    gasto_comun_uf: Decimal = Field(default=Decimal("0"), ge=0)
    valor_comercial_uf: Optional[Decimal] = Field(None, gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "rol_sii": "1234-5678",
                "direccion_completa": "Av. Providencia 1234",
                "numero": "1234",
                "departamento": "501",
                "comuna": "Providencia",
                "region": "Metropolitana",
                "tipo": "departamento",
                "superficie_util_m2": 75.5,
                "dormitorios": 2,
                "banos": 2,
                "estacionamientos": 1,
                "bodega": True,
                "bodega_m2": 4.5,
                "piso": 5,
                "orientacion": "Norte",
                "amoblado": False,
                "estado_conservacion": "bueno",
                "gasto_comun_uf": 4.5,
                "valor_comercial_uf": 5500
            }
        }


class ReajusteInput(BaseModel):
    """Configuración de reajuste"""
    tipo: TipoReajuste = Field(default=TipoReajuste.IPC)
    periodicidad_meses: int = Field(default=12, ge=1, le=24)
    porcentaje_fijo_anual: Optional[Decimal] = Field(None, ge=0, le=20)
    tope_reajuste_anual: Optional[Decimal] = Field(None, ge=0, le=20)
    piso_reajuste_anual: Optional[Decimal] = Field(None, ge=0, le=20)


class CrearContratoRequest(BaseModel):
    """Request para crear contrato"""
    tipo: TipoContrato = Field(..., description="Tipo de contrato")
    arrendador: PersonaInput
    arrendatario: PersonaInput
    codeudor: Optional[PersonaInput] = None
    propiedad: PropiedadInput
    renta_mensual_uf: Decimal = Field(..., gt=0, description="Renta mensual en UF")
    fecha_inicio: date = Field(..., description="Fecha inicio arriendo")
    duracion_meses: Optional[int] = Field(12, ge=1, le=120, description="Duración en meses")
    reajuste: Optional[ReajusteInput] = None
    garantia_meses: int = Field(default=1, ge=0, le=3, description="Meses de garantía")
    tipo_garantia: TipoGarantia = Field(default=TipoGarantia.DEPOSITO_EFECTIVO)
    dia_pago: int = Field(default=5, ge=1, le=28, description="Día del mes para pago")
    gastos_comunes_incluidos: bool = Field(default=False)
    servicios_incluidos: List[str] = Field(default_factory=list)
    permite_mascotas: bool = Field(default=False)
    permite_subarriendo: bool = Field(default=False)
    uso_exclusivo: str = Field(default="habitacional")
    clausulas_adicionales: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "plazo_fijo",
                "arrendador": {
                    "rut": "11.111.111-1",
                    "nombre_completo": "Propietario Ejemplo",
                    "email": "propietario@email.com",
                    "telefono": "+56911111111",
                    "direccion": "Dirección propietario",
                    "comuna": "Las Condes"
                },
                "arrendatario": {
                    "rut": "22.222.222-2",
                    "nombre_completo": "Arrendatario Ejemplo",
                    "email": "arrendatario@email.com",
                    "telefono": "+56922222222",
                    "direccion": "Dirección arrendatario",
                    "comuna": "Providencia"
                },
                "propiedad": {
                    "rol_sii": "1234-5678",
                    "direccion_completa": "Av. Providencia 1234",
                    "numero": "1234",
                    "departamento": "501",
                    "comuna": "Providencia",
                    "tipo": "departamento",
                    "superficie_util_m2": 75.5,
                    "dormitorios": 2,
                    "banos": 2
                },
                "renta_mensual_uf": 25.0,
                "fecha_inicio": "2025-02-01",
                "duracion_meses": 12,
                "garantia_meses": 1,
                "dia_pago": 5
            }
        }


class ActualizarContratoRequest(BaseModel):
    """Request para actualizar contrato"""
    renta_mensual_uf: Optional[Decimal] = Field(None, gt=0)
    dia_pago: Optional[int] = Field(None, ge=1, le=28)
    gastos_comunes_incluidos: Optional[bool] = None
    gasto_comun_mensual_uf: Optional[Decimal] = Field(None, ge=0)
    servicios_incluidos: Optional[List[str]] = None
    permite_mascotas: Optional[bool] = None
    clausulas_adicionales: Optional[str] = None


class TerminarContratoRequest(BaseModel):
    """Request para terminar contrato"""
    motivo: MotivoTermino
    fecha_termino: date
    observaciones: Optional[str] = None


class EmitirCobroRequest(BaseModel):
    """Request para emitir cobro mensual"""
    periodo: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Período YYYY-MM")
    cobros_adicionales: Optional[Dict[str, Decimal]] = Field(
        None, 
        description="Cobros extras {concepto: monto}"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "periodo": "2025-02",
                "cobros_adicionales": {
                    "reparacion_calefont": 50000,
                    "limpieza_alfombras": 30000
                }
            }
        }


class RegistrarPagoRequest(BaseModel):
    """Request para registrar pago"""
    cobro_id: str = Field(..., description="ID del cobro a pagar")
    monto: Decimal = Field(..., gt=0, description="Monto pagado en pesos")
    fecha_pago: date
    medio_pago: str = Field(..., description="transferencia, efectivo, cheque, webpay")
    comprobante: Optional[str] = Field(None, description="Número de comprobante")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cobro_id": "cobro-uuid",
                "monto": 962500,
                "fecha_pago": "2025-02-05",
                "medio_pago": "transferencia",
                "comprobante": "TRF-123456"
            }
        }


class DevolverGarantiaRequest(BaseModel):
    """Request para devolver garantía"""
    descuentos: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Lista de descuentos [{concepto, monto}]"
    )
    observaciones: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "descuentos": [
                    {"concepto": "Pintura paredes", "monto": 150000},
                    {"concepto": "Limpieza profunda", "monto": 80000}
                ],
                "observaciones": "Departamento entregado con daños menores"
            }
        }


class IniciarLey21461Request(BaseModel):
    """Request para iniciar proceso Ley 21.461"""
    confirmar: bool = Field(..., description="Confirmar inicio del proceso")
    abogado_patrocinante: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "confirmar": True,
                "abogado_patrocinante": "Juan Abogado - Estudio Jurídico ABC"
            }
        }


class ActualizarLey21461Request(BaseModel):
    """Request para actualizar proceso Ley 21.461"""
    nueva_etapa: EtapaLey21461
    datos: Dict[str, Any] = Field(..., description="Datos específicos de la etapa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nueva_etapa": "requerimiento",
                "datos": {
                    "tribunal": "1er Juzgado Civil de Santiago",
                    "rol_causa": "C-1234-2025",
                    "fecha_presentacion": "2025-02-01",
                    "fecha_notificacion": "2025-02-05"
                }
            }
        }


class CalcularRentabilidadRequest(BaseModel):
    """Request para calcular rentabilidad"""
    propiedad_id: str = Field(..., description="ID de la propiedad")
    renta_mensual_uf: Decimal = Field(..., gt=0)
    valor_propiedad_uf: Decimal = Field(..., gt=0)
    gastos_anuales: Optional[Dict[str, Decimal]] = Field(
        None,
        description="Gastos desglosados: contribuciones, seguros, mantenciones, etc."
    )
    vacancia_pct: Decimal = Field(default=Decimal("5"), ge=0, le=50)
    plusvalia_anual_pct: Decimal = Field(default=Decimal("3"), ge=-10, le=20)
    
    class Config:
        json_schema_extra = {
            "example": {
                "propiedad_id": "prop-uuid",
                "renta_mensual_uf": 25.0,
                "valor_propiedad_uf": 5500,
                "gastos_anuales": {
                    "contribuciones": 66,
                    "seguros": 11,
                    "mantenciones": 55,
                    "administracion": 24
                },
                "vacancia_pct": 5,
                "plusvalia_anual_pct": 3
            }
        }


# =============================================================================
# SCHEMAS DE RESPONSE
# =============================================================================

class ContratoResumenResponse(BaseModel):
    """Resumen de contrato para listados"""
    id: str
    codigo: str
    tipo: str
    estado: str
    arrendador_nombre: str
    arrendador_rut: str
    arrendatario_nombre: str
    arrendatario_rut: str
    propiedad_direccion: str
    propiedad_comuna: str
    renta_mensual_uf: str
    fecha_inicio: date
    fecha_termino: Optional[date]
    meses_mora: int
    saldo_deuda: str


class ContratoDetalleResponse(BaseModel):
    """Detalle completo de contrato"""
    id: str
    codigo: str
    tipo: str
    estado: str
    arrendador: Dict[str, Any]
    arrendatario: Dict[str, Any]
    codeudor: Optional[Dict[str, Any]]
    propiedad: Dict[str, Any]
    fechas: Dict[str, Any]
    renta: Dict[str, Any]
    reajuste: Dict[str, Any]
    garantia: Optional[Dict[str, Any]]
    condiciones: Dict[str, Any]
    estado_cuenta: Dict[str, Any]
    proceso_legal: Optional[Dict[str, Any]]
    documentos: Dict[str, Any]
    auditoria: Dict[str, Any]


class ListaContratosResponse(BaseModel):
    """Respuesta de listado de contratos"""
    contratos: List[ContratoResumenResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


class CobroResponse(BaseModel):
    """Respuesta de cobro"""
    id: str
    contrato_codigo: str
    periodo: str
    fecha_emision: date
    fecha_vencimiento: date
    renta_base_uf: str
    renta_base_pesos: str
    gasto_comun_pesos: str
    otros_cobros: str
    iva_monto: str
    total_cobro: str
    estado: str
    fecha_pago: Optional[date]
    monto_pagado: str
    dias_mora: int
    interes_mora: str


class GarantiaResponse(BaseModel):
    """Respuesta de garantía"""
    id: str
    tipo: str
    monto_uf: str
    monto_pesos: str
    fecha_constitucion: date
    estado: str
    fecha_devolucion: Optional[date]
    monto_devuelto: str
    descuentos_aplicados: List[Dict[str, Any]]


class ProcesoLey21461Response(BaseModel):
    """Respuesta de proceso Ley 21.461"""
    id: str
    etapa: str
    fecha_inicio: Optional[date]
    meses_mora: int
    monto_adeudado_uf: str
    monto_adeudado_pesos: str
    tribunal: str
    rol_causa: str
    fechas: Dict[str, Any]
    estado_actual: str
    proximos_pasos: List[str]


class RentabilidadResponse(BaseModel):
    """Respuesta de análisis de rentabilidad"""
    propiedad_id: str
    fecha_calculo: date
    valores_base: Dict[str, str]
    ingresos: Dict[str, str]
    gastos: Dict[str, str]
    rentabilidades: Dict[str, str]
    proyeccion_5_anos: List[Dict[str, Any]]
    indicadores_inversion: Dict[str, str]
    comparacion_mercado: Dict[str, str]
    recomendacion: str


class ReporteCarteraResponse(BaseModel):
    """Respuesta de reporte de cartera"""
    fecha_corte: str
    resumen: Dict[str, Any]
    financiero: Dict[str, str]
    distribucion_tipo: Dict[str, Any]
    distribucion_comuna: Dict[str, Any]
    alertas: Dict[str, int]


class EstadisticasMercadoResponse(BaseModel):
    """Respuesta de estadísticas de mercado"""
    comuna: str
    tipo_propiedad: str
    fecha_actualizacion: str
    indicadores: Dict[str, str]
    rangos_renta: Dict[str, Dict[str, str]]
    cap_rate_zona: Dict[str, str]


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_service() -> ArriendosService:
    """Obtener servicio de arriendos"""
    return get_arriendos_service()


def persona_input_to_dataclass(p: PersonaInput) -> PersonaArriendo:
    """Convertir PersonaInput a PersonaArriendo"""
    return PersonaArriendo(
        rut=p.rut,
        nombre_completo=p.nombre_completo,
        email=p.email,
        telefono=p.telefono,
        direccion=p.direccion,
        comuna=p.comuna,
        nacionalidad=p.nacionalidad,
        estado_civil=p.estado_civil or "",
        profesion=p.profesion or "",
        empleador=p.empleador or "",
        renta_mensual=p.renta_mensual
    )


def propiedad_input_to_dataclass(p: PropiedadInput) -> PropiedadArriendo:
    """Convertir PropiedadInput a PropiedadArriendo"""
    return PropiedadArriendo(
        expediente_id=p.expediente_id,
        ficha_propiedad_id=p.ficha_propiedad_id,
        rol_sii=p.rol_sii,
        direccion_completa=p.direccion_completa,
        numero=p.numero,
        departamento=p.departamento,
        comuna=p.comuna,
        region=p.region,
        tipo=p.tipo,
        superficie_util_m2=p.superficie_util_m2,
        dormitorios=p.dormitorios,
        banos=p.banos,
        estacionamientos=p.estacionamientos,
        bodega=p.bodega,
        bodega_m2=p.bodega_m2,
        piso=p.piso,
        orientacion=p.orientacion or "",
        amoblado=p.amoblado,
        estado_conservacion=p.estado_conservacion,
        gasto_comun_uf=p.gasto_comun_uf,
        valor_comercial_uf=p.valor_comercial_uf or Decimal("0")
    )


def contrato_to_resumen(c: ContratoArriendo) -> ContratoResumenResponse:
    """Convertir contrato a resumen"""
    return ContratoResumenResponse(
        id=c.id,
        codigo=c.codigo,
        tipo=c.tipo.value,
        estado=c.estado.value,
        arrendador_nombre=c.arrendador.nombre_completo,
        arrendador_rut=c.arrendador.rut,
        arrendatario_nombre=c.arrendatario.nombre_completo,
        arrendatario_rut=c.arrendatario.rut,
        propiedad_direccion=f"{c.propiedad.direccion_completa} {c.propiedad.departamento or ''}".strip(),
        propiedad_comuna=c.propiedad.comuna,
        renta_mensual_uf=str(c.renta_mensual_uf),
        fecha_inicio=c.fecha_inicio,
        fecha_termino=c.fecha_termino,
        meses_mora=c.meses_mora,
        saldo_deuda=str(c.saldo_deuda)
    )


def contrato_to_detalle(c: ContratoArriendo) -> ContratoDetalleResponse:
    """Convertir contrato a detalle completo"""
    return ContratoDetalleResponse(
        id=c.id,
        codigo=c.codigo,
        tipo=c.tipo.value,
        estado=c.estado.value,
        arrendador={
            "id": c.arrendador.id,
            "rut": c.arrendador.rut,
            "nombre": c.arrendador.nombre_completo,
            "email": c.arrendador.email,
            "telefono": c.arrendador.telefono,
            "direccion": c.arrendador.direccion,
            "comuna": c.arrendador.comuna
        },
        arrendatario={
            "id": c.arrendatario.id,
            "rut": c.arrendatario.rut,
            "nombre": c.arrendatario.nombre_completo,
            "email": c.arrendatario.email,
            "telefono": c.arrendatario.telefono,
            "direccion": c.arrendatario.direccion,
            "comuna": c.arrendatario.comuna,
            "profesion": c.arrendatario.profesion,
            "empleador": c.arrendatario.empleador
        },
        codeudor={
            "rut": c.codeudor.rut,
            "nombre": c.codeudor.nombre_completo,
            "email": c.codeudor.email,
            "telefono": c.codeudor.telefono
        } if c.codeudor else None,
        propiedad={
            "id": c.propiedad.id,
            "rol_sii": c.propiedad.rol_sii,
            "direccion": c.propiedad.direccion_completa,
            "numero": c.propiedad.numero,
            "departamento": c.propiedad.departamento,
            "comuna": c.propiedad.comuna,
            "tipo": c.propiedad.tipo,
            "superficie_m2": str(c.propiedad.superficie_util_m2),
            "dormitorios": c.propiedad.dormitorios,
            "banos": c.propiedad.banos,
            "estacionamientos": c.propiedad.estacionamientos,
            "amoblado": c.propiedad.amoblado
        },
        fechas={
            "firma": c.fecha_firma.isoformat() if c.fecha_firma else None,
            "inicio": c.fecha_inicio.isoformat(),
            "termino": c.fecha_termino.isoformat() if c.fecha_termino else None,
            "duracion_meses": c.duracion_meses,
            "renovacion_automatica": c.renovacion_automatica,
            "preaviso_dias": c.preaviso_dias
        },
        renta={
            "mensual_uf": str(c.renta_mensual_uf),
            "mensual_pesos": str(c.renta_mensual_pesos),
            "dia_pago": c.dia_pago,
            "afecto_iva": c.afecto_iva,
            "gastos_comunes_incluidos": c.gastos_comunes_incluidos,
            "gasto_comun_uf": str(c.gasto_comun_mensual_uf)
        },
        reajuste={
            "tipo": c.reajuste.tipo.value,
            "periodicidad_meses": c.reajuste.periodicidad_meses,
            "porcentaje_fijo": str(c.reajuste.porcentaje_fijo_anual) if c.reajuste.porcentaje_fijo_anual else None,
            "ultimo_reajuste": c.reajuste.fecha_ultimo_reajuste.isoformat() if c.reajuste.fecha_ultimo_reajuste else None
        },
        garantia={
            "id": c.garantia.id,
            "tipo": c.garantia.tipo.value,
            "monto_uf": str(c.garantia.monto_uf),
            "monto_pesos": str(c.garantia.monto_pesos),
            "estado": c.garantia.estado.value,
            "fecha_constitucion": c.garantia.fecha_constitucion.isoformat()
        } if c.garantia else None,
        condiciones={
            "uso_exclusivo": c.uso_exclusivo,
            "permite_mascotas": c.permite_mascotas,
            "permite_subarriendo": c.permite_subarriendo,
            "servicios_incluidos": c.servicios_incluidos,
            "restricciones": c.restricciones
        },
        estado_cuenta={
            "saldo_favor": str(c.saldo_favor),
            "saldo_deuda": str(c.saldo_deuda),
            "meses_mora": c.meses_mora,
            "total_cobros": len(c.cobros),
            "cobros_pendientes": len([cb for cb in c.cobros if cb.estado in [EstadoPago.PENDIENTE, EstadoPago.VENCIDO]])
        },
        proceso_legal={
            "activo": c.proceso_ley21461 is not None and c.proceso_ley21461.etapa != EtapaLey21461.NO_APLICA,
            "etapa": c.proceso_ley21461.etapa.value if c.proceso_ley21461 else None,
            "monto_adeudado": str(c.proceso_ley21461.monto_adeudado_pesos) if c.proceso_ley21461 else None
        } if c.proceso_ley21461 else None,
        documentos={
            "contrato_pdf": c.contrato_pdf_url,
            "inventario": c.inventario_url,
            "acta_entrega": c.acta_entrega_url,
            "anexos": c.anexos_urls
        },
        auditoria={
            "creado_en": c.creado_en.isoformat(),
            "actualizado_en": c.actualizado_en.isoformat(),
            "creado_por": c.creado_por,
            "version": c.version
        }
    )


# =============================================================================
# ENDPOINTS - GESTIÓN DE CONTRATOS
# =============================================================================

@router.post(
    "/contratos",
    response_model=ContratoDetalleResponse,
    status_code=201,
    summary="Crear contrato de arriendo",
    description="Crea un nuevo contrato de arriendo con todos sus datos"
)
async def crear_contrato(
    request: CrearContratoRequest,
    service: ArriendosService = Depends(get_service)
):
    """
    Crear nuevo contrato de arriendo.
    
    Valida datos y crea contrato con:
    - Partes (arrendador, arrendatario, codeudor opcional)
    - Propiedad
    - Condiciones de renta y reajuste
    - Garantía
    """
    try:
        # Convertir inputs
        arrendador = persona_input_to_dataclass(request.arrendador)
        arrendatario = persona_input_to_dataclass(request.arrendatario)
        propiedad = propiedad_input_to_dataclass(request.propiedad)
        
        # Configurar reajuste
        reajuste = None
        if request.reajuste:
            reajuste = ConfiguracionReajuste(
                tipo=request.reajuste.tipo,
                periodicidad_meses=request.reajuste.periodicidad_meses,
                porcentaje_fijo_anual=request.reajuste.porcentaje_fijo_anual or Decimal("0"),
                tope_reajuste_anual=request.reajuste.tope_reajuste_anual,
                piso_reajuste_anual=request.reajuste.piso_reajuste_anual
            )
        
        # Crear contrato
        contrato = await service.crear_contrato(
            tipo=request.tipo,
            arrendador=arrendador,
            arrendatario=arrendatario,
            propiedad=propiedad,
            renta_mensual_uf=request.renta_mensual_uf,
            fecha_inicio=request.fecha_inicio,
            duracion_meses=request.duracion_meses,
            reajuste=reajuste,
            garantia_meses=request.garantia_meses,
            tipo_garantia=request.tipo_garantia,
            dia_pago=request.dia_pago
        )
        
        # Configurar condiciones adicionales
        contrato.gastos_comunes_incluidos = request.gastos_comunes_incluidos
        contrato.servicios_incluidos = request.servicios_incluidos
        contrato.permite_mascotas = request.permite_mascotas
        contrato.permite_subarriendo = request.permite_subarriendo
        contrato.uso_exclusivo = request.uso_exclusivo
        contrato.clausulas_adicionales = request.clausulas_adicionales or ""
        
        if request.codeudor:
            contrato.codeudor = persona_input_to_dataclass(request.codeudor)
        
        return contrato_to_detalle(contrato)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/contratos/{contrato_id}",
    response_model=ContratoDetalleResponse,
    summary="Obtener contrato",
    description="Obtiene detalle completo de un contrato por ID o código"
)
async def obtener_contrato(
    contrato_id: str = Path(..., description="ID o código del contrato"),
    service: ArriendosService = Depends(get_service)
):
    """Obtener detalle de contrato"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return contrato_to_detalle(contrato)


@router.get(
    "/contratos",
    response_model=ListaContratosResponse,
    summary="Listar contratos",
    description="Lista contratos con filtros y paginación"
)
async def listar_contratos(
    arrendador_rut: Optional[str] = Query(None, description="Filtrar por RUT arrendador"),
    arrendatario_rut: Optional[str] = Query(None, description="Filtrar por RUT arrendatario"),
    estado: Optional[EstadoContrato] = Query(None, description="Filtrar por estado"),
    comuna: Optional[str] = Query(None, description="Filtrar por comuna"),
    tipo: Optional[TipoContrato] = Query(None, description="Filtrar por tipo"),
    solo_morosos: bool = Query(False, description="Solo contratos morosos"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    service: ArriendosService = Depends(get_service)
):
    """Listar contratos con filtros"""
    contratos, total = await service.listar_contratos(
        arrendador_rut=arrendador_rut,
        arrendatario_rut=arrendatario_rut,
        estado=estado,
        comuna=comuna,
        tipo=tipo,
        solo_morosos=solo_morosos,
        pagina=pagina,
        por_pagina=por_pagina
    )
    
    return ListaContratosResponse(
        contratos=[contrato_to_resumen(c) for c in contratos],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=(total + por_pagina - 1) // por_pagina
    )


@router.put(
    "/contratos/{contrato_id}",
    response_model=ContratoDetalleResponse,
    summary="Actualizar contrato",
    description="Actualiza datos modificables del contrato"
)
async def actualizar_contrato(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: ActualizarContratoRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Actualizar datos del contrato"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    # Actualizar campos
    if request.renta_mensual_uf is not None:
        contrato.renta_mensual_uf = request.renta_mensual_uf
    if request.dia_pago is not None:
        contrato.dia_pago = request.dia_pago
    if request.gastos_comunes_incluidos is not None:
        contrato.gastos_comunes_incluidos = request.gastos_comunes_incluidos
    if request.gasto_comun_mensual_uf is not None:
        contrato.gasto_comun_mensual_uf = request.gasto_comun_mensual_uf
    if request.servicios_incluidos is not None:
        contrato.servicios_incluidos = request.servicios_incluidos
    if request.permite_mascotas is not None:
        contrato.permite_mascotas = request.permite_mascotas
    if request.clausulas_adicionales is not None:
        contrato.clausulas_adicionales = request.clausulas_adicionales
    
    contrato.actualizado_en = datetime.now()
    contrato.version += 1
    
    return contrato_to_detalle(contrato)


@router.post(
    "/contratos/{contrato_id}/activar",
    response_model=ContratoDetalleResponse,
    summary="Activar contrato",
    description="Cambia estado del contrato a vigente (firmado)"
)
async def activar_contrato(
    contrato_id: str = Path(..., description="ID del contrato"),
    fecha_firma: date = Body(..., embed=True),
    service: ArriendosService = Depends(get_service)
):
    """Activar contrato (cambiar a vigente)"""
    contrato = await service.actualizar_estado_contrato(
        contrato_id=contrato_id,
        nuevo_estado=EstadoContrato.VIGENTE
    )
    contrato.fecha_firma = fecha_firma
    return contrato_to_detalle(contrato)


@router.post(
    "/contratos/{contrato_id}/terminar",
    response_model=ContratoDetalleResponse,
    summary="Terminar contrato",
    description="Termina el contrato por el motivo especificado"
)
async def terminar_contrato(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: TerminarContratoRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Terminar contrato de arriendo"""
    contrato = await service.terminar_contrato(
        contrato_id=contrato_id,
        motivo=request.motivo,
        fecha_termino=request.fecha_termino,
        observaciones=request.observaciones or ""
    )
    return contrato_to_detalle(contrato)


# =============================================================================
# ENDPOINTS - COBROS Y PAGOS
# =============================================================================

@router.post(
    "/contratos/{contrato_id}/cobros",
    response_model=CobroResponse,
    status_code=201,
    summary="Emitir cobro mensual",
    description="Emite cobro de arriendo para el período especificado"
)
async def emitir_cobro(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: EmitirCobroRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Emitir cobro mensual de arriendo"""
    try:
        cobro = await service.emitir_cobro_mensual(
            contrato_id=contrato_id,
            periodo=request.periodo,
            cobros_adicionales=request.cobros_adicionales
        )
        
        contrato = await service.obtener_contrato(contrato_id)
        
        return CobroResponse(
            id=cobro.id,
            contrato_codigo=contrato.codigo if contrato else "",
            periodo=cobro.periodo,
            fecha_emision=cobro.fecha_emision,
            fecha_vencimiento=cobro.fecha_vencimiento,
            renta_base_uf=str(cobro.renta_base_uf),
            renta_base_pesos=str(cobro.renta_base_pesos),
            gasto_comun_pesos=str(cobro.gasto_comun_pesos),
            otros_cobros=str(cobro.otros_cobros),
            iva_monto=str(cobro.iva_monto),
            total_cobro=str(cobro.total_cobro),
            estado=cobro.estado.value,
            fecha_pago=cobro.fecha_pago,
            monto_pagado=str(cobro.monto_pagado),
            dias_mora=cobro.dias_mora,
            interes_mora=str(cobro.interes_mora)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/contratos/{contrato_id}/cobros",
    response_model=List[CobroResponse],
    summary="Listar cobros",
    description="Lista todos los cobros del contrato"
)
async def listar_cobros(
    contrato_id: str = Path(..., description="ID del contrato"),
    estado: Optional[EstadoPago] = Query(None, description="Filtrar por estado"),
    service: ArriendosService = Depends(get_service)
):
    """Listar cobros del contrato"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    cobros = contrato.cobros
    if estado:
        cobros = [c for c in cobros if c.estado == estado]
    
    return [
        CobroResponse(
            id=c.id,
            contrato_codigo=contrato.codigo,
            periodo=c.periodo,
            fecha_emision=c.fecha_emision,
            fecha_vencimiento=c.fecha_vencimiento,
            renta_base_uf=str(c.renta_base_uf),
            renta_base_pesos=str(c.renta_base_pesos),
            gasto_comun_pesos=str(c.gasto_comun_pesos),
            otros_cobros=str(c.otros_cobros),
            iva_monto=str(c.iva_monto),
            total_cobro=str(c.total_cobro),
            estado=c.estado.value,
            fecha_pago=c.fecha_pago,
            monto_pagado=str(c.monto_pagado),
            dias_mora=c.dias_mora,
            interes_mora=str(c.interes_mora)
        )
        for c in cobros
    ]


@router.post(
    "/contratos/{contrato_id}/pagos",
    response_model=CobroResponse,
    summary="Registrar pago",
    description="Registra pago de arriendo"
)
async def registrar_pago(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: RegistrarPagoRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Registrar pago de arriendo"""
    try:
        cobro = await service.registrar_pago(
            contrato_id=contrato_id,
            cobro_id=request.cobro_id,
            monto=request.monto,
            fecha_pago=request.fecha_pago,
            medio_pago=request.medio_pago,
            comprobante=request.comprobante or ""
        )
        
        contrato = await service.obtener_contrato(contrato_id)
        
        return CobroResponse(
            id=cobro.id,
            contrato_codigo=contrato.codigo if contrato else "",
            periodo=cobro.periodo,
            fecha_emision=cobro.fecha_emision,
            fecha_vencimiento=cobro.fecha_vencimiento,
            renta_base_uf=str(cobro.renta_base_uf),
            renta_base_pesos=str(cobro.renta_base_pesos),
            gasto_comun_pesos=str(cobro.gasto_comun_pesos),
            otros_cobros=str(cobro.otros_cobros),
            iva_monto=str(cobro.iva_monto),
            total_cobro=str(cobro.total_cobro),
            estado=cobro.estado.value,
            fecha_pago=cobro.fecha_pago,
            monto_pagado=str(cobro.monto_pagado),
            dias_mora=cobro.dias_mora,
            interes_mora=str(cobro.interes_mora)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ENDPOINTS - GARANTÍAS
# =============================================================================

@router.get(
    "/contratos/{contrato_id}/garantia",
    response_model=GarantiaResponse,
    summary="Obtener garantía",
    description="Obtiene información de la garantía del contrato"
)
async def obtener_garantia(
    contrato_id: str = Path(..., description="ID del contrato"),
    service: ArriendosService = Depends(get_service)
):
    """Obtener información de garantía"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    if not contrato.garantia:
        raise HTTPException(status_code=404, detail="Contrato sin garantía registrada")
    
    g = contrato.garantia
    return GarantiaResponse(
        id=g.id,
        tipo=g.tipo.value,
        monto_uf=str(g.monto_uf),
        monto_pesos=str(g.monto_pesos),
        fecha_constitucion=g.fecha_constitucion,
        estado=g.estado.value,
        fecha_devolucion=g.fecha_devolucion,
        monto_devuelto=str(g.monto_devuelto),
        descuentos_aplicados=g.descuentos_aplicados
    )


@router.post(
    "/contratos/{contrato_id}/garantia/devolver",
    response_model=GarantiaResponse,
    summary="Devolver garantía",
    description="Procesa devolución de garantía al término del contrato"
)
async def devolver_garantia(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: DevolverGarantiaRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Procesar devolución de garantía"""
    try:
        garantia = await service.devolver_garantia(
            contrato_id=contrato_id,
            descuentos=request.descuentos,
            observaciones=request.observaciones or ""
        )
        
        return GarantiaResponse(
            id=garantia.id,
            tipo=garantia.tipo.value,
            monto_uf=str(garantia.monto_uf),
            monto_pesos=str(garantia.monto_pesos),
            fecha_constitucion=garantia.fecha_constitucion,
            estado=garantia.estado.value,
            fecha_devolucion=garantia.fecha_devolucion,
            monto_devuelto=str(garantia.monto_devuelto),
            descuentos_aplicados=garantia.descuentos_aplicados
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ENDPOINTS - PROCESO LEY 21.461
# =============================================================================

@router.post(
    "/contratos/{contrato_id}/ley21461/iniciar",
    response_model=ProcesoLey21461Response,
    summary="Iniciar proceso Ley 21.461",
    description="Inicia procedimiento monitorio 'Devuélveme Mi Casa'"
)
async def iniciar_proceso_ley21461(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: IniciarLey21461Request = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Iniciar proceso Ley 21.461"""
    if not request.confirmar:
        raise HTTPException(
            status_code=400, 
            detail="Debe confirmar el inicio del proceso legal"
        )
    
    try:
        proceso = await service.iniciar_proceso_ley21461(contrato_id)
        
        return ProcesoLey21461Response(
            id=proceso.id,
            etapa=proceso.etapa.value,
            fecha_inicio=proceso.fecha_inicio,
            meses_mora=proceso.meses_mora,
            monto_adeudado_uf=str(proceso.monto_adeudado_uf),
            monto_adeudado_pesos=str(proceso.monto_adeudado_pesos),
            tribunal=proceso.tribunal,
            rol_causa=proceso.rol_causa,
            fechas={
                "inicio": proceso.fecha_inicio.isoformat() if proceso.fecha_inicio else None,
                "presentacion": proceso.fecha_presentacion.isoformat() if proceso.fecha_presentacion else None,
                "notificacion": proceso.fecha_notificacion.isoformat() if proceso.fecha_notificacion else None,
                "plazo_vence": proceso.plazo_vence.isoformat() if proceso.plazo_vence else None
            },
            estado_actual="Preparación de antecedentes",
            proximos_pasos=[
                "Reunir documentación requerida",
                "Presentar requerimiento en tribunal",
                "Esperar notificación al arrendatario"
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/contratos/{contrato_id}/ley21461",
    response_model=ProcesoLey21461Response,
    summary="Actualizar proceso Ley 21.461",
    description="Actualiza etapa del procedimiento monitorio"
)
async def actualizar_proceso_ley21461(
    contrato_id: str = Path(..., description="ID del contrato"),
    request: ActualizarLey21461Request = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Actualizar proceso Ley 21.461"""
    try:
        proceso = await service.actualizar_proceso_ley21461(
            contrato_id=contrato_id,
            nueva_etapa=request.nueva_etapa,
            datos=request.datos
        )
        
        # Determinar próximos pasos según etapa
        proximos_pasos = []
        estado_actual = ""
        
        if proceso.etapa == EtapaLey21461.REQUERIMIENTO:
            estado_actual = "Requerimiento presentado"
            proximos_pasos = [
                f"Plazo para pago/oposición vence: {proceso.plazo_vence}",
                "Monitorear respuesta del arrendatario"
            ]
        elif proceso.etapa == EtapaLey21461.OPOSICION:
            estado_actual = "Arrendatario se opuso"
            proximos_pasos = [
                "Esperar audiencia de conciliación",
                "Preparar alegatos"
            ]
        elif proceso.etapa == EtapaLey21461.SENTENCIA:
            estado_actual = "Sentencia dictada"
            if proceso.sentencia_favorable:
                proximos_pasos = [
                    "Solicitar orden de lanzamiento",
                    "Coordinar con receptor judicial"
                ]
            else:
                proximos_pasos = ["Evaluar apelación"]
        elif proceso.etapa == EtapaLey21461.LANZAMIENTO:
            estado_actual = "Lanzamiento programado"
            proximos_pasos = [
                f"Fecha lanzamiento: {proceso.fecha_lanzamiento_programada}",
                "Coordinar con Carabineros si es necesario"
            ]
        
        return ProcesoLey21461Response(
            id=proceso.id,
            etapa=proceso.etapa.value,
            fecha_inicio=proceso.fecha_inicio,
            meses_mora=proceso.meses_mora,
            monto_adeudado_uf=str(proceso.monto_adeudado_uf),
            monto_adeudado_pesos=str(proceso.monto_adeudado_pesos),
            tribunal=proceso.tribunal,
            rol_causa=proceso.rol_causa,
            fechas={
                "inicio": proceso.fecha_inicio.isoformat() if proceso.fecha_inicio else None,
                "presentacion": proceso.fecha_presentacion.isoformat() if proceso.fecha_presentacion else None,
                "notificacion": proceso.fecha_notificacion.isoformat() if proceso.fecha_notificacion else None,
                "plazo_vence": proceso.plazo_vence.isoformat() if proceso.plazo_vence else None,
                "sentencia": proceso.fecha_sentencia.isoformat() if proceso.fecha_sentencia else None,
                "lanzamiento_programado": proceso.fecha_lanzamiento_programada.isoformat() if proceso.fecha_lanzamiento_programada else None
            },
            estado_actual=estado_actual,
            proximos_pasos=proximos_pasos
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/contratos/{contrato_id}/ley21461",
    response_model=ProcesoLey21461Response,
    summary="Obtener proceso Ley 21.461",
    description="Obtiene estado actual del procedimiento monitorio"
)
async def obtener_proceso_ley21461(
    contrato_id: str = Path(..., description="ID del contrato"),
    service: ArriendosService = Depends(get_service)
):
    """Obtener estado del proceso Ley 21.461"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    if not contrato.proceso_ley21461:
        raise HTTPException(
            status_code=404, 
            detail="No hay proceso Ley 21.461 activo para este contrato"
        )
    
    p = contrato.proceso_ley21461
    return ProcesoLey21461Response(
        id=p.id,
        etapa=p.etapa.value,
        fecha_inicio=p.fecha_inicio,
        meses_mora=p.meses_mora,
        monto_adeudado_uf=str(p.monto_adeudado_uf),
        monto_adeudado_pesos=str(p.monto_adeudado_pesos),
        tribunal=p.tribunal,
        rol_causa=p.rol_causa,
        fechas={
            "inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
            "presentacion": p.fecha_presentacion.isoformat() if p.fecha_presentacion else None,
            "notificacion": p.fecha_notificacion.isoformat() if p.fecha_notificacion else None,
            "plazo_vence": p.plazo_vence.isoformat() if p.plazo_vence else None,
            "oposicion": p.fecha_oposicion.isoformat() if p.fecha_oposicion else None,
            "sentencia": p.fecha_sentencia.isoformat() if p.fecha_sentencia else None,
            "lanzamiento_programado": p.fecha_lanzamiento_programada.isoformat() if p.fecha_lanzamiento_programada else None,
            "lanzamiento_ejecutado": p.fecha_lanzamiento_ejecutada.isoformat() if p.fecha_lanzamiento_ejecutada else None
        },
        estado_actual=p.etapa.value.replace("_", " ").title(),
        proximos_pasos=[]
    )


# =============================================================================
# ENDPOINTS - ANÁLISIS DE RENTABILIDAD
# =============================================================================

@router.post(
    "/rentabilidad/calcular",
    response_model=RentabilidadResponse,
    summary="Calcular rentabilidad",
    description="Calcula análisis completo de rentabilidad de arriendo"
)
async def calcular_rentabilidad(
    request: CalcularRentabilidadRequest = Body(...),
    service: ArriendosService = Depends(get_service)
):
    """Calcular rentabilidad de arriendo"""
    analisis = await service.calcular_rentabilidad(
        propiedad_id=request.propiedad_id,
        renta_mensual_uf=request.renta_mensual_uf,
        valor_propiedad_uf=request.valor_propiedad_uf,
        gastos_anuales=request.gastos_anuales,
        vacancia_pct=request.vacancia_pct,
        plusvalia_anual_pct=request.plusvalia_anual_pct
    )
    
    return RentabilidadResponse(
        propiedad_id=analisis.propiedad_id,
        fecha_calculo=analisis.fecha_calculo,
        valores_base={
            "valor_propiedad_uf": str(analisis.valor_propiedad_uf),
            "renta_mensual_uf": str(analisis.renta_mensual_uf)
        },
        ingresos={
            "bruto_anual_uf": str(analisis.ingreso_bruto_anual_uf),
            "vacancia_pct": str(analisis.vacancia_estimada_pct),
            "efectivo_anual_uf": str(analisis.ingreso_efectivo_anual_uf)
        },
        gastos={
            "contribuciones_uf": str(analisis.contribuciones_uf),
            "seguros_uf": str(analisis.seguros_uf),
            "mantenciones_uf": str(analisis.mantenciones_uf),
            "administracion_uf": str(analisis.administracion_uf),
            "gastos_comunes_uf": str(analisis.gastos_comunes_uf),
            "otros_uf": str(analisis.otros_gastos_uf),
            "total_uf": str(analisis.total_gastos_uf)
        },
        rentabilidades={
            "ingreso_neto_anual_uf": str(analisis.ingreso_neto_anual_uf),
            "cap_rate_bruto_pct": str(analisis.cap_rate_bruto),
            "cap_rate_neto_pct": str(analisis.cap_rate_neto)
        },
        proyeccion_5_anos=analisis.proyeccion_5_anos,
        indicadores_inversion={
            "tir_estimada_pct": str(analisis.tir_estimada),
            "payback_anos": str(analisis.payback_anos)
        },
        comparacion_mercado={
            "cap_rate_mercado_pct": str(analisis.cap_rate_mercado_zona),
            "diferencial_pct": str(analisis.diferencial_mercado)
        },
        recomendacion=analisis.recomendacion
    )


# =============================================================================
# ENDPOINTS - REPORTES Y ESTADÍSTICAS
# =============================================================================

@router.get(
    "/reportes/cartera",
    response_model=ReporteCarteraResponse,
    summary="Reporte de cartera",
    description="Genera reporte consolidado de cartera de arriendos"
)
async def generar_reporte_cartera(
    arrendador_rut: Optional[str] = Query(None, description="Filtrar por arrendador"),
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    service: ArriendosService = Depends(get_service)
):
    """Generar reporte de cartera"""
    reporte = await service.generar_reporte_cartera(
        arrendador_rut=arrendador_rut,
        fecha_corte=fecha_corte
    )
    
    return ReporteCarteraResponse(**reporte)


@router.get(
    "/estadisticas/mercado",
    response_model=EstadisticasMercadoResponse,
    summary="Estadísticas de mercado",
    description="Obtiene estadísticas del mercado de arriendos"
)
async def obtener_estadisticas_mercado(
    comuna: str = Query(..., description="Comuna a consultar"),
    tipo_propiedad: Optional[str] = Query(None, description="Tipo de propiedad"),
    service: ArriendosService = Depends(get_service)
):
    """Obtener estadísticas de mercado de arriendos"""
    stats = await service.obtener_estadisticas_mercado(
        comuna=comuna,
        tipo_propiedad=tipo_propiedad
    )
    
    return EstadisticasMercadoResponse(**stats)


@router.get(
    "/contratos/{contrato_id}/historial",
    response_model=List[Dict[str, Any]],
    summary="Historial del contrato",
    description="Obtiene historial de eventos del contrato"
)
async def obtener_historial_contrato(
    contrato_id: str = Path(..., description="ID del contrato"),
    service: ArriendosService = Depends(get_service)
):
    """Obtener historial de eventos del contrato"""
    contrato = await service.obtener_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "tipo_evento": h.tipo_evento,
            "descripcion": h.descripcion,
            "usuario": h.usuario,
            "datos_adicionales": h.datos_adicionales
        }
        for h in contrato.historial
    ]


# =============================================================================
# ENDPOINTS - UTILIDADES
# =============================================================================

@router.get(
    "/tipos-contrato",
    response_model=List[Dict[str, str]],
    summary="Tipos de contrato",
    description="Lista tipos de contrato disponibles"
)
async def listar_tipos_contrato():
    """Listar tipos de contrato"""
    return [
        {"valor": t.value, "descripcion": t.name.replace("_", " ").title()}
        for t in TipoContrato
    ]


@router.get(
    "/estados-contrato",
    response_model=List[Dict[str, str]],
    summary="Estados de contrato",
    description="Lista estados posibles del contrato"
)
async def listar_estados_contrato():
    """Listar estados de contrato"""
    return [
        {"valor": e.value, "descripcion": e.name.replace("_", " ").title()}
        for e in EstadoContrato
    ]


@router.get(
    "/motivos-termino",
    response_model=List[Dict[str, str]],
    summary="Motivos de término",
    description="Lista motivos de término de contrato"
)
async def listar_motivos_termino():
    """Listar motivos de término"""
    return [
        {"valor": m.value, "descripcion": m.name.replace("_", " ").title()}
        for m in MotivoTermino
    ]


@router.get(
    "/tipos-garantia",
    response_model=List[Dict[str, str]],
    summary="Tipos de garantía",
    description="Lista tipos de garantía aceptados"
)
async def listar_tipos_garantia():
    """Listar tipos de garantía"""
    return [
        {"valor": t.value, "descripcion": t.name.replace("_", " ").title()}
        for t in TipoGarantia
    ]
