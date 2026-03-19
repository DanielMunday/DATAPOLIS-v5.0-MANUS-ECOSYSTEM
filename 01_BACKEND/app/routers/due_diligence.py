"""
DATAPOLIS v3.0 - Router API Due Diligence Inmobiliario
Endpoints REST para M12_DueDiligence (150+ checks, 6 áreas, HITL)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import io

from app.schemas.due_diligence import (
    DueDiligenceRequest, DueDiligenceResponse, DueDiligenceRapidoRequest,
    CheckResultResponse, AreaResultResponse, ValidacionHITLRequest,
    InformeDDRequest, HistorialDDResponse, CheckDefinitionResponse
)
from app.schemas.base import ResponseWrapper, PaginatedResponse, ErrorResponse
from app.services.m12_due_diligence import ServicioDueDiligence
from app.config import get_settings

router = APIRouter(
    prefix="/due-diligence",
    tags=["Due Diligence Inmobiliario"],
    responses={
        400: {"model": ErrorResponse, "description": "Request inválido"},
        404: {"model": ErrorResponse, "description": "Due diligence no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno"}
    }
)

settings = get_settings()
_servicio_dd: Optional[ServicioDueDiligence] = None

async def get_servicio() -> ServicioDueDiligence:
    """Dependency injection para servicio due diligence"""
    global _servicio_dd
    if _servicio_dd is None:
        _servicio_dd = ServicioDueDiligence()
    return _servicio_dd


class NivelProfundidad(str, Enum):
    """Niveles de profundidad del due diligence"""
    BASICO = "basico"       # Solo checks críticos y altos
    ESTANDAR = "estandar"   # + checks medios
    COMPLETO = "completo"   # Todos los checks


class AreaDD(str, Enum):
    """Áreas de due diligence"""
    LEGAL = "legal"
    FINANCIERO = "financiero"
    TECNICO = "tecnico"
    AMBIENTAL = "ambiental"
    URBANISTICO = "urbanistico"
    COMERCIAL = "comercial"


# ============================================================================
# EJECUTAR DUE DILIGENCE
# ============================================================================

@router.post(
    "/ejecutar",
    response_model=ResponseWrapper[DueDiligenceResponse],
    summary="Ejecutar Due Diligence completo",
    description="Proceso de due diligence con 150+ verificaciones automáticas"
)
async def ejecutar_due_diligence(
    request: DueDiligenceRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Ejecuta Due Diligence inmobiliario integral.
    
    **6 Áreas de verificación**:
    1. **Legal** (40 checks): Títulos, gravámenes, litigios, contratos
    2. **Financiero** (30 checks): Tributario, valoración, operacional
    3. **Técnico** (25 checks): Estructura, instalaciones, terminaciones
    4. **Ambiental** (20 checks): Contaminación, permisos, riesgos naturales
    5. **Urbanístico** (20 checks): Permisos municipales, normativa
    6. **Comercial** (15 checks): Mercado, operacional
    
    **Niveles de profundidad**:
    - básico: Solo checks críticos y altos (~30 checks)
    - estándar: + checks medios (~80 checks)
    - completo: Todos los 150+ checks
    
    **Tiempo estimado**: 30 segundos - 5 minutos según nivel
    """
    try:
        resultado = await servicio.ejecutar(
            datos_propiedad=request.datos_propiedad,
            datos_adicionales=request.datos_adicionales,
            nivel_profundidad=request.nivel_profundidad or "estandar",
            areas_incluidas=request.areas_incluidas,
            timeout_check_ms=request.timeout_check_ms or 30000
        )
        
        # Log asíncrono
        background_tasks.add_task(
            _log_due_diligence,
            resultado.id_due_diligence,
            request.datos_propiedad.get("rol_sii")
        )
        
        return ResponseWrapper(
            success=True,
            data=resultado,
            message=f"Due Diligence completado - Score: {resultado.score_global} ({resultado.categoria})"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en due diligence: {str(e)}")


@router.post(
    "/rapido",
    response_model=ResponseWrapper[dict],
    summary="Due Diligence rápido",
    description="Verificación express de puntos críticos"
)
async def ejecutar_dd_rapido(
    request: DueDiligenceRapidoRequest,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Due Diligence express con verificaciones críticas mínimas.
    
    **Checks incluidos** (~15):
    - Inscripción CBR vigente
    - Prohibiciones de enajenar
    - Embargos activos
    - Hipotecas (LTV)
    - Litigios críticos
    - Permiso edificación
    - Recepción final
    - Uso de suelo
    - Contribuciones al día
    
    **Tiempo**: < 30 segundos
    """
    try:
        resultado = await servicio.ejecutar_rapido(
            rol_sii=request.rol_sii,
            direccion=request.direccion,
            comuna=request.comuna,
            tipo_propiedad=request.tipo_propiedad
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "estado": resultado["estado"],
                "deal_breakers": resultado["deal_breakers"],
                "alertas_criticas": resultado["alertas_criticas"],
                "score_preliminar": resultado["score"],
                "checks_aprobados": resultado["aprobados"],
                "checks_rechazados": resultado["rechazados"],
                "checks_pendientes": resultado["pendientes"],
                "recomendacion": resultado["recomendacion"],
                "requiere_dd_completo": resultado["requiere_completo"],
                "nota": "Verificación express. Para análisis completo, ejecute DD estándar."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ejecutar/{rol_sii}",
    response_model=ResponseWrapper[DueDiligenceResponse],
    summary="DD por ROL SII"
)
async def ejecutar_por_rol(
    rol_sii: str,
    nivel: NivelProfundidad = Query(NivelProfundidad.ESTANDAR),
    areas: Optional[str] = Query(None, description="Áreas separadas por coma"),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Ejecuta Due Diligence consultando datos automáticamente por ROL SII.
    """
    try:
        areas_lista = [a.strip() for a in areas.split(",")] if areas else None
        
        resultado = await servicio.ejecutar_por_rol(
            rol_sii=rol_sii,
            nivel_profundidad=nivel.value,
            areas_incluidas=areas_lista
        )
        
        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró información para ROL {rol_sii}"
            )
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHECKS Y ÁREAS
# ============================================================================

@router.get(
    "/checks",
    response_model=ResponseWrapper[List[CheckDefinitionResponse]],
    summary="Catálogo de checks disponibles"
)
async def listar_checks(
    area: Optional[AreaDD] = Query(None),
    criticidad: Optional[str] = Query(None, regex="^(critico|alto|medio|bajo|informativo)$"),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Lista todos los checks disponibles con filtros opcionales.
    
    **Total**: 150+ checks organizados por área y criticidad
    """
    try:
        checks = await servicio.listar_checks(
            area=area.value if area else None,
            criticidad=criticidad
        )
        
        return ResponseWrapper(
            success=True,
            data=checks,
            message=f"Total checks: {len(checks)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/checks/{codigo}",
    response_model=ResponseWrapper[CheckDefinitionResponse],
    summary="Detalle de check específico"
)
async def get_check_detalle(
    codigo: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Obtiene detalle completo de un check específico.
    
    **Formato código**: AREA-NNN (ej: LEG-001, FIN-012, TEC-025)
    """
    try:
        check = await servicio.detalle_check(codigo.upper())
        
        if check is None:
            raise HTTPException(status_code=404, detail=f"Check no encontrado: {codigo}")
        
        return ResponseWrapper(success=True, data=check)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/areas",
    response_model=ResponseWrapper[List[dict]],
    summary="Áreas de due diligence"
)
async def listar_areas():
    """
    Lista las 6 áreas de due diligence con descripción y pesos.
    """
    areas = [
        {
            "codigo": "legal",
            "nombre": "Legal",
            "descripcion": "Verificación de títulos, gravámenes, litigios y contratos",
            "peso_score": 0.25,
            "total_checks": 40,
            "subcategorias": [
                "Títulos de dominio",
                "Gravámenes e hipotecas",
                "Litigios activos",
                "Contratos y arriendos"
            ],
            "fuentes_principales": ["CBR", "Poder Judicial", "SII"]
        },
        {
            "codigo": "financiero",
            "nombre": "Financiero",
            "descripcion": "Análisis tributario, valoración y operacional",
            "peso_score": 0.20,
            "total_checks": 30,
            "subcategorias": [
                "Situación tributaria",
                "Valoración de mercado",
                "Operacional"
            ],
            "fuentes_principales": ["SII", "TGR", "Portales inmobiliarios"]
        },
        {
            "codigo": "tecnico",
            "nombre": "Técnico",
            "descripcion": "Estado físico, estructura e instalaciones",
            "peso_score": 0.15,
            "total_checks": 25,
            "subcategorias": [
                "Estructura",
                "Instalaciones",
                "Terminaciones"
            ],
            "fuentes_principales": ["Inspección", "SEC", "MINVU"]
        },
        {
            "codigo": "ambiental",
            "nombre": "Ambiental",
            "descripcion": "Contaminación, permisos ambientales y riesgos naturales",
            "peso_score": 0.15,
            "total_checks": 20,
            "subcategorias": [
                "Contaminación",
                "Permisos ambientales",
                "Riesgos naturales"
            ],
            "fuentes_principales": ["SMA", "SHOA", "SENAPRED", "SEA"]
        },
        {
            "codigo": "urbanistico",
            "nombre": "Urbanístico",
            "descripcion": "Permisos municipales y cumplimiento normativo",
            "peso_score": 0.15,
            "total_checks": 20,
            "subcategorias": [
                "Permisos municipales",
                "Normativa urbana"
            ],
            "fuentes_principales": ["DOM Municipal", "MINVU", "PRC"]
        },
        {
            "codigo": "comercial",
            "nombre": "Comercial",
            "descripcion": "Análisis de mercado y situación operacional",
            "peso_score": 0.10,
            "total_checks": 15,
            "subcategorias": [
                "Análisis de mercado",
                "Operacional"
            ],
            "fuentes_principales": ["Portales", "INE", "BCCh"]
        }
    ]
    
    return ResponseWrapper(success=True, data=areas)


@router.get(
    "/{id_dd}/area/{area}",
    response_model=ResponseWrapper[AreaResultResponse],
    summary="Resultado por área"
)
async def get_resultado_area(
    id_dd: str,
    area: AreaDD,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Obtiene resultado detallado de un área específica del due diligence.
    """
    try:
        resultado = await servicio.resultado_area(id_dd, area.value)
        
        if resultado is None:
            raise HTTPException(status_code=404, detail="Due diligence o área no encontrada")
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VALIDACIÓN HUMANA (HITL)
# ============================================================================

@router.get(
    "/{id_dd}/pendientes-validacion",
    response_model=ResponseWrapper[List[dict]],
    summary="Checks pendientes de validación humana"
)
async def get_pendientes_validacion(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Lista checks que requieren validación humana (HITL).
    
    **Tipos**:
    - SEMI_AUTOMATICA: IA + revisión humana recomendada
    - MANUAL: Requiere inspección/verificación humana
    - EXTERNA: Requiere validación de fuente externa
    """
    try:
        pendientes = await servicio.checks_pendientes_validacion(id_dd)
        
        if pendientes is None:
            raise HTTPException(status_code=404, detail="Due diligence no encontrado")
        
        return ResponseWrapper(
            success=True,
            data=pendientes,
            message=f"Total pendientes: {len(pendientes)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{id_dd}/validar",
    response_model=ResponseWrapper[dict],
    summary="Registrar validación humana"
)
async def validar_check(
    id_dd: str,
    request: ValidacionHITLRequest,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Registra validación humana de un check específico.
    
    **Validadores requeridos** (según check):
    - Abogado inmobiliario
    - Ingeniero estructural
    - Consultor ambiental
    - Certificador SEC
    - Tasador autorizado
    """
    try:
        resultado = await servicio.registrar_validacion(
            id_dd=id_dd,
            codigo_check=request.codigo_check,
            validado=request.validado,
            validador_nombre=request.validador_nombre,
            validador_rut=request.validador_rut,
            validador_profesion=request.validador_profesion,
            observaciones=request.observaciones,
            documentos_soporte=request.documentos_soporte
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "check_validado": request.codigo_check,
                "estado_check": resultado["nuevo_estado"],
                "validador": request.validador_nombre,
                "fecha_validacion": datetime.now().isoformat(),
                "dd_actualizado": resultado["dd_recalculado"]
            },
            message="Validación registrada correctamente"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/validadores-requeridos",
    response_model=ResponseWrapper[List[dict]],
    summary="Validadores profesionales requeridos"
)
async def get_validadores_requeridos(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Lista profesionales requeridos para completar validaciones HITL.
    """
    try:
        validadores = await servicio.validadores_requeridos(id_dd)
        
        return ResponseWrapper(
            success=True,
            data=validadores
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEAL BREAKERS Y RIESGOS
# ============================================================================

@router.get(
    "/{id_dd}/deal-breakers",
    response_model=ResponseWrapper[List[dict]],
    summary="Deal breakers identificados"
)
async def get_deal_breakers(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Lista deal breakers que bloquean la transacción.
    
    **Ejemplos de deal breakers**:
    - Prohibición de enajenar vigente
    - Embargo activo
    - Uso de suelo incompatible
    - Alto riesgo tsunami/inundación
    - Litigio crítico sobre dominio
    """
    try:
        deal_breakers = await servicio.obtener_deal_breakers(id_dd)
        
        if deal_breakers is None:
            raise HTTPException(status_code=404, detail="Due diligence no encontrado")
        
        return ResponseWrapper(
            success=True,
            data=deal_breakers,
            message=f"Deal breakers: {len(deal_breakers)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/riesgos",
    response_model=ResponseWrapper[dict],
    summary="Resumen de riesgos"
)
async def get_riesgos(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Resumen de riesgos identificados por criticidad.
    """
    try:
        riesgos = await servicio.resumen_riesgos(id_dd)
        
        if riesgos is None:
            raise HTTPException(status_code=404, detail="Due diligence no encontrado")
        
        return ResponseWrapper(
            success=True,
            data={
                "total_riesgos": riesgos["total"],
                "criticos": riesgos["criticos"],
                "altos": riesgos["altos"],
                "medios": riesgos["medios"],
                "bajos": riesgos["bajos"],
                "detalle_criticos": riesgos["detalle_criticos"],
                "detalle_altos": riesgos["detalle_altos"],
                "matriz_riesgo": riesgos["matriz"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/condiciones-cierre",
    response_model=ResponseWrapper[List[dict]],
    summary="Condiciones para cierre"
)
async def get_condiciones_cierre(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Lista condiciones que deben cumplirse antes del cierre de transacción.
    """
    try:
        condiciones = await servicio.condiciones_cierre(id_dd)
        
        return ResponseWrapper(
            success=True,
            data=condiciones
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INFORMES Y EXPORTACIÓN
# ============================================================================

@router.post(
    "/{id_dd}/informe",
    response_model=ResponseWrapper[dict],
    summary="Generar informe Due Diligence"
)
async def generar_informe(
    id_dd: str,
    request: InformeDDRequest,
    background_tasks: BackgroundTasks,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Genera informe profesional de Due Diligence.
    
    **Formatos**: PDF, DOCX, HTML
    
    **Contenido**:
    - Resumen ejecutivo
    - Resultado por área
    - Deal breakers y alertas
    - Checks detallados
    - Recomendaciones
    - Anexos documentales
    """
    try:
        resultado = await servicio.generar_informe(
            id_dd=id_dd,
            formato=request.formato or "pdf",
            incluir_anexos=request.incluir_anexos,
            idioma=request.idioma or "es",
            nivel_detalle=request.nivel_detalle or "completo"
        )
        
        return ResponseWrapper(
            success=True,
            data={
                "informe_id": resultado["informe_id"],
                "url_descarga": resultado["url"],
                "formato": request.formato or "pdf",
                "paginas_estimadas": resultado["paginas"],
                "generado_at": datetime.now().isoformat(),
                "expira_at": resultado["expira_at"],
                "hash_integridad": resultado["hash"]
            },
            message="Informe generado correctamente"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/informe/{informe_id}/descargar",
    summary="Descargar informe"
)
async def descargar_informe(
    id_dd: str,
    informe_id: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """Descarga informe de Due Diligence generado"""
    try:
        contenido, filename, media_type = await servicio.obtener_informe(informe_id)
        
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Informe no encontrado o expirado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/exportar/checklist",
    summary="Exportar checklist"
)
async def exportar_checklist(
    id_dd: str,
    formato: str = Query("xlsx", regex="^(xlsx|csv|pdf)$"),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Exporta checklist de verificaciones en formato tabular.
    """
    try:
        contenido, filename, media_type = await servicio.exportar_checklist(id_dd, formato)
        
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HISTORIAL Y TRACKING
# ============================================================================

@router.get(
    "/historial/{rol_sii}",
    response_model=ResponseWrapper[HistorialDDResponse],
    summary="Historial de due diligence"
)
async def get_historial(
    rol_sii: str,
    limite: int = Query(10, ge=1, le=50),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Historial de due diligence para una propiedad.
    """
    try:
        resultado = await servicio.historial_dd(rol_sii, limite)
        
        return ResponseWrapper(
            success=True,
            data=HistorialDDResponse(
                rol_sii=rol_sii,
                total_procesos=resultado["total"],
                procesos=resultado["procesos"],
                tendencia_score=resultado["tendencia"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}",
    response_model=ResponseWrapper[DueDiligenceResponse],
    summary="Obtener DD por ID"
)
async def get_due_diligence(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """Recupera due diligence existente por ID"""
    try:
        resultado = await servicio.obtener_dd(id_dd)
        
        if resultado is None:
            raise HTTPException(status_code=404, detail="Due diligence no encontrado")
        
        return ResponseWrapper(success=True, data=resultado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{id_dd}/verificar-integridad",
    response_model=ResponseWrapper[dict],
    summary="Verificar integridad"
)
async def verificar_integridad(
    id_dd: str,
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Verifica integridad del due diligence mediante hash SHA-256.
    """
    try:
        resultado = await servicio.verificar_integridad(id_dd)
        
        return ResponseWrapper(
            success=True,
            data={
                "id_dd": id_dd,
                "hash_original": resultado["hash_original"],
                "hash_actual": resultado["hash_actual"],
                "integro": resultado["integro"],
                "verificado_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPARATIVOS Y ESTADÍSTICAS
# ============================================================================

@router.get(
    "/estadisticas/generales",
    response_model=ResponseWrapper[dict],
    summary="Estadísticas generales DD"
)
async def get_estadisticas_generales(
    periodo_meses: int = Query(12, ge=1, le=60),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Estadísticas generales de procesos de due diligence.
    """
    try:
        stats = await servicio.estadisticas_generales(periodo_meses)
        
        return ResponseWrapper(
            success=True,
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/estadisticas/deal-breakers",
    response_model=ResponseWrapper[List[dict]],
    summary="Deal breakers más frecuentes"
)
async def get_estadisticas_deal_breakers(
    top: int = Query(10, ge=1, le=50),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Ranking de deal breakers más frecuentes en procesos DD.
    """
    try:
        ranking = await servicio.ranking_deal_breakers(top)
        return ResponseWrapper(success=True, data=ranking)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/estadisticas/checks-fallidos",
    response_model=ResponseWrapper[List[dict]],
    summary="Checks con mayor tasa de fallo"
)
async def get_checks_mayor_fallo(
    top: int = Query(20, ge=1, le=100),
    area: Optional[AreaDD] = Query(None),
    servicio: ServicioDueDiligence = Depends(get_servicio)
):
    """
    Ranking de checks con mayor tasa de rechazo/observaciones.
    """
    try:
        ranking = await servicio.checks_mayor_fallo(top, area.value if area else None)
        return ResponseWrapper(success=True, data=ranking)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILIDADES
# ============================================================================

@router.get(
    "/categorias",
    response_model=ResponseWrapper[List[dict]],
    summary="Categorías de clasificación DD"
)
async def listar_categorias():
    """Categorías de resultado del due diligence"""
    categorias = [
        {"categoria": "A", "rango": "≥85", "descripcion": "Excelente - Sin observaciones críticas", "color": "#22c55e"},
        {"categoria": "B", "rango": "70-84", "descripcion": "Bueno - Observaciones menores", "color": "#84cc16"},
        {"categoria": "C", "rango": "55-69", "descripcion": "Aceptable - Requiere atención", "color": "#eab308"},
        {"categoria": "D", "rango": "40-54", "descripcion": "Riesgoso - Observaciones significativas", "color": "#f97316"},
        {"categoria": "F", "rango": "<40", "descripcion": "No recomendado - Deal breakers o riesgos críticos", "color": "#ef4444"}
    ]
    
    return ResponseWrapper(success=True, data=categorias)


@router.get(
    "/criticidades",
    response_model=ResponseWrapper[List[dict]],
    summary="Niveles de criticidad"
)
async def listar_criticidades():
    """Niveles de criticidad de los checks"""
    criticidades = [
        {
            "nivel": "critico",
            "descripcion": "Deal breaker - Bloquea transacción",
            "peso": 4,
            "ejemplo": "Prohibición de enajenar vigente"
        },
        {
            "nivel": "alto",
            "descripcion": "Riesgo significativo - Requiere resolución",
            "peso": 3,
            "ejemplo": "Hipoteca con LTV > 80%"
        },
        {
            "nivel": "medio",
            "descripcion": "Requiere atención - Puede mitigarse",
            "peso": 2,
            "ejemplo": "Contribuciones atrasadas"
        },
        {
            "nivel": "bajo",
            "descripcion": "Observación menor - Bajo impacto",
            "peso": 1,
            "ejemplo": "Terminaciones con desgaste normal"
        },
        {
            "nivel": "informativo",
            "descripcion": "Solo información - Sin riesgo",
            "peso": 0.5,
            "ejemplo": "Antigüedad de la propiedad"
        }
    ]
    
    return ResponseWrapper(success=True, data=criticidades)


async def _log_due_diligence(id_dd: str, rol_sii: Optional[str]):
    """Log asíncrono para auditoría"""
    pass


@router.get("/health", include_in_schema=False)
async def health_check():
    return {
        "status": "healthy",
        "service": "due_diligence",
        "timestamp": datetime.now().isoformat()
    }
