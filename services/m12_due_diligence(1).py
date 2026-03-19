"""
DATAPOLIS v3.0 - M12 Due Diligence Service
===========================================
Servicio de Due Diligence inmobiliario con evaluación integral automatizada.

Características:
- 150+ checks en 6 dimensiones
- Integración SII, Conservador, DOM, SAG, SERNAGEOMIN
- Scoring por área y global
- Validación humana opcional (HITL)
- Generación de reportes automatizada

Autor: DATAPOLIS SpA
Versión: 3.0.0
Licencia: Propietaria
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
import hashlib

import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERACIONES Y CONSTANTES
# =============================================================================

class AreaDueDiligence(str, Enum):
    """Áreas de evaluación Due Diligence."""
    LEGAL = "legal"
    FINANCIERO = "financiero"
    TECNICO = "tecnico"
    AMBIENTAL = "ambiental"
    URBANISTICO = "urbanistico"
    COMERCIAL = "comercial"


class EstadoCheck(str, Enum):
    """Estados posibles de un check."""
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    OBSERVADO = "observado"
    NO_APLICA = "no_aplica"
    ERROR = "error"


class CriticidadCheck(str, Enum):
    """Nivel de criticidad del check."""
    CRITICO = "critico"      # Deal breaker
    ALTO = "alto"            # Riesgo significativo
    MEDIO = "medio"          # Requiere atención
    BAJO = "bajo"            # Informativo
    INFORMATIVO = "info"     # Solo información


class TipoValidacion(str, Enum):
    """Tipo de validación requerida."""
    AUTOMATICA = "automatica"        # 100% automático
    SEMI_AUTOMATICA = "semi_auto"    # Auto + revisión humana
    MANUAL = "manual"                # Requiere humano
    EXTERNA = "externa"              # Fuente externa


# Ponderaciones por área
PONDERACIONES_AREA = {
    AreaDueDiligence.LEGAL: 0.25,
    AreaDueDiligence.FINANCIERO: 0.20,
    AreaDueDiligence.TECNICO: 0.15,
    AreaDueDiligence.AMBIENTAL: 0.15,
    AreaDueDiligence.URBANISTICO: 0.15,
    AreaDueDiligence.COMERCIAL: 0.10,
}


# =============================================================================
# DEFINICIÓN DE CHECKS - 150+ CHECKS ORGANIZADOS POR ÁREA
# =============================================================================

CHECKS_DUE_DILIGENCE = {
    # =========================================================================
    # ÁREA LEGAL (40 checks)
    # =========================================================================
    AreaDueDiligence.LEGAL: [
        # Títulos de dominio (10)
        {"codigo": "LEG-001", "nombre": "Vigencia inscripción CBR", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-002", "nombre": "Cadena de dominio últimos 10 años", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-003", "nombre": "Verificación deslindes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "LEG-004", "nombre": "Coincidencia planos/escritura", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-005", "nombre": "Servidumbres activas", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-006", "nombre": "Usufructos vigentes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-007", "nombre": "Verificación cabida", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-008", "nombre": "Estado subdivisión/fusión", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-009", "nombre": "Declaración de bien familiar", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-010", "nombre": "Verificación comunidad/copropiedad", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        
        # Gravámenes e hipotecas (10)
        {"codigo": "LEG-011", "nombre": "Hipotecas vigentes", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-012", "nombre": "Prohibiciones de enajenar", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-013", "nombre": "Embargos activos", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-014", "nombre": "Medidas precautorias", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-015", "nombre": "Derechos de agua inscritos", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-016", "nombre": "Concesiones mineras", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-017", "nombre": "Gravámenes ambientales", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-018", "nombre": "Afectaciones de utilidad pública", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-019", "nombre": "Reservas de dominio", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-020", "nombre": "Condiciones resolutorias pendientes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.MANUAL},
        
        # Litigios y juicios (10)
        {"codigo": "LEG-021", "nombre": "Juicios civiles activos", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-022", "nombre": "Juicios ejecutivos", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-023", "nombre": "Juicios laborales (empresa)", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-024", "nombre": "Procesos de quiebra/liquidación", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-025", "nombre": "Juicios ambientales", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-026", "nombre": "Reclamos municipales pendientes", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-027", "nombre": "Arbitrajes en curso", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "LEG-028", "nombre": "Prescripciones en trámite", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-029", "nombre": "Acciones reivindicatorias", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "LEG-030", "nombre": "Nulidades de inscripción", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        
        # Contratos y arriendos (10)
        {"codigo": "LEG-031", "nombre": "Contratos de arriendo vigentes", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-032", "nombre": "Cláusulas especiales arriendo", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "LEG-033", "nombre": "Garantías y boletas vigentes", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-034", "nombre": "Promesas de compraventa", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-035", "nombre": "Opciones de compra otorgadas", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "LEG-036", "nombre": "Contratos de administración", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-037", "nombre": "Poderes vigentes sobre propiedad", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "LEG-038", "nombre": "Cesiones de derechos", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "LEG-039", "nombre": "Contratos de leasing", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "LEG-040", "nombre": "Pactos de retroventa", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
    ],
    
    # =========================================================================
    # ÁREA FINANCIERA (30 checks)
    # =========================================================================
    AreaDueDiligence.FINANCIERO: [
        # Tributario (10)
        {"codigo": "FIN-001", "nombre": "Contribuciones al día", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-002", "nombre": "Avalúo fiscal SII", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-003", "nombre": "Situación tributaria propietario", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "FIN-004", "nombre": "IVA crédito fiscal (si aplica)", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "FIN-005", "nombre": "Impuesto herencia pendiente", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "FIN-006", "nombre": "Ganancia capital estimada", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-007", "nombre": "Depreciación acumulada", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-008", "nombre": "Beneficios DFL2 vigentes", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-009", "nombre": "Deudas municipales", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-010", "nombre": "Retenciones de arriendo", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        
        # Valoración (10)
        {"codigo": "FIN-011", "nombre": "Tasación comercial actualizada", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "FIN-012", "nombre": "Comparables de mercado", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-013", "nombre": "Análisis precio/m2 zona", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-014", "nombre": "Proyección flujos (DCF)", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-015", "nombre": "Cap rate vs mercado", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-016", "nombre": "Valor de liquidación", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-017", "nombre": "Costo de reposición", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-018", "nombre": "Tendencia plusvalía histórica", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-019", "nombre": "Sensibilidad a tasas", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-020", "nombre": "Análisis de inversión alternativa", "criticidad": CriticidadCheck.INFORMATIVO, "tipo": TipoValidacion.AUTOMATICA},
        
        # Operacional (10)
        {"codigo": "FIN-021", "nombre": "Ingresos históricos 24 meses", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "FIN-022", "nombre": "Gastos operacionales detallados", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "FIN-023", "nombre": "NOI vs mercado", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-024", "nombre": "Vacancia histórica", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-025", "nombre": "Morosidad arrendatarios", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-026", "nombre": "Contratos por vencer 12 meses", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-027", "nombre": "CAPEX proyectado", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "FIN-028", "nombre": "Fondo de reserva (copropiedad)", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-029", "nombre": "Seguros vigentes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "FIN-030", "nombre": "Contingencias financieras", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.MANUAL},
    ],
    
    # =========================================================================
    # ÁREA TÉCNICA (25 checks)
    # =========================================================================
    AreaDueDiligence.TECNICO: [
        # Estructura (10)
        {"codigo": "TEC-001", "nombre": "Inspección estructural", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-002", "nombre": "Certificado NCh 433 (sismo)", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-003", "nombre": "Estado fundaciones", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-004", "nombre": "Grietas estructurales", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-005", "nombre": "Asentamientos diferenciales", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-006", "nombre": "Estado techumbres", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-007", "nombre": "Humedad y filtraciones", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-008", "nombre": "Estado fachadas", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-009", "nombre": "Vida útil remanente", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "TEC-010", "nombre": "Historial de reparaciones", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        
        # Instalaciones (10)
        {"codigo": "TEC-011", "nombre": "Certificación eléctrica SEC", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-012", "nombre": "Certificación gas SEC", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-013", "nombre": "Estado instalación sanitaria", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-014", "nombre": "Sistema agua caliente", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-015", "nombre": "Sistema climatización", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-016", "nombre": "Ascensores (certificación)", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-017", "nombre": "Sistema contra incendio", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "TEC-018", "nombre": "Red de datos/comunicaciones", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-019", "nombre": "Sistema de seguridad", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-020", "nombre": "Estanques y bombas", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        
        # Terminaciones (5)
        {"codigo": "TEC-021", "nombre": "Estado terminaciones interiores", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-022", "nombre": "Carpintería y ventanas", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-023", "nombre": "Pisos y revestimientos", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-024", "nombre": "Áreas comunes (copropiedad)", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "TEC-025", "nombre": "Eficiencia energética", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
    ],
    
    # =========================================================================
    # ÁREA AMBIENTAL (20 checks)
    # =========================================================================
    AreaDueDiligence.AMBIENTAL: [
        # Contaminación (8)
        {"codigo": "AMB-001", "nombre": "Estudio de suelo (contaminación)", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-002", "nombre": "Pasivos ambientales históricos", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-003", "nombre": "Presencia de asbesto", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-004", "nombre": "Tanques subterráneos", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-005", "nombre": "Manejo de residuos", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "AMB-006", "nombre": "Emisiones atmosféricas", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-007", "nombre": "Ruido ambiental", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "AMB-008", "nombre": "Olores molestos", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        
        # Permisos ambientales (6)
        {"codigo": "AMB-009", "nombre": "RCA (Resolución Calificación Ambiental)", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-010", "nombre": "Permisos sectoriales vigentes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-011", "nombre": "Plan de manejo ambiental", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "AMB-012", "nombre": "Certificaciones ambientales", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-013", "nombre": "Compromisos ambientales pendientes", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "AMB-014", "nombre": "Fiscalizaciones SMA", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        
        # Riesgos naturales (6)
        {"codigo": "AMB-015", "nombre": "Zona de riesgo sísmico", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-016", "nombre": "Zona de inundación", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-017", "nombre": "Zona de tsunami", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-018", "nombre": "Riesgo de remoción en masa", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-019", "nombre": "Riesgo de incendios forestales", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "AMB-020", "nombre": "Riesgo volcánico", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
    ],
    
    # =========================================================================
    # ÁREA URBANÍSTICA (20 checks)
    # =========================================================================
    AreaDueDiligence.URBANISTICO: [
        # Permisos municipales (10)
        {"codigo": "URB-001", "nombre": "Permiso de edificación", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-002", "nombre": "Recepción final municipal", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-003", "nombre": "Certificado de informaciones previas", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-004", "nombre": "Patente comercial (si aplica)", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-005", "nombre": "Permiso de ampliación", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "URB-006", "nombre": "Regularización Ley 20.898", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "URB-007", "nombre": "Cambio de destino aprobado", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "URB-008", "nombre": "Resolución sanitaria (si aplica)", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.EXTERNA},
        {"codigo": "URB-009", "nombre": "Informe de riesgos municipal", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "URB-010", "nombre": "Declaración de utilidad pública", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        
        # Normativa (10)
        {"codigo": "URB-011", "nombre": "Uso de suelo permitido", "criticidad": CriticidadCheck.CRITICO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-012", "nombre": "Coeficiente constructibilidad", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-013", "nombre": "Coeficiente ocupación suelo", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-014", "nombre": "Altura máxima permitida", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-015", "nombre": "Rasantes y distanciamientos", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "URB-016", "nombre": "Densidad habitacional", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-017", "nombre": "Estacionamientos normativos", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-018", "nombre": "Áreas verdes requeridas", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-019", "nombre": "Zona de conservación histórica", "criticidad": CriticidadCheck.ALTO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "URB-020", "nombre": "Modificaciones PRC en trámite", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
    ],
    
    # =========================================================================
    # ÁREA COMERCIAL (15 checks)
    # =========================================================================
    AreaDueDiligence.COMERCIAL: [
        # Mercado (8)
        {"codigo": "COM-001", "nombre": "Análisis de mercado zona", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-002", "nombre": "Competencia directa", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-003", "nombre": "Demanda proyectada", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-004", "nombre": "Proyectos futuros en zona", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-005", "nombre": "Tendencias demográficas", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-006", "nombre": "Infraestructura proyectada", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "COM-007", "nombre": "Planes de desarrollo comunal", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "COM-008", "nombre": "Índice de liquidez mercado", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        
        # Operacional (7)
        {"codigo": "COM-009", "nombre": "Perfil arrendatarios actuales", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "COM-010", "nombre": "Mix de arrendatarios", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-011", "nombre": "Rotación histórica", "criticidad": CriticidadCheck.MEDIO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-012", "nombre": "Satisfacción arrendatarios", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.MANUAL},
        {"codigo": "COM-013", "nombre": "Potencial de mejora NOI", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.AUTOMATICA},
        {"codigo": "COM-014", "nombre": "Oportunidades de desarrollo", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.SEMI_AUTOMATICA},
        {"codigo": "COM-015", "nombre": "Reputación del activo", "criticidad": CriticidadCheck.BAJO, "tipo": TipoValidacion.MANUAL},
    ],
}


# =============================================================================
# DATACLASSES PARA RESULTADOS
# =============================================================================

@dataclass
class ResultadoCheck:
    """Resultado de un check individual."""
    codigo: str
    nombre: str
    area: AreaDueDiligence
    criticidad: CriticidadCheck
    tipo_validacion: TipoValidacion
    estado: EstadoCheck
    score: float  # 0-100
    hallazgos: List[str] = field(default_factory=list)
    observaciones: str = ""
    documentos_soporte: List[str] = field(default_factory=list)
    ejecutado_por_ia: bool = True
    validado_por_humano: bool = False
    validador_humano: Optional[str] = None
    fecha_ejecucion: datetime = field(default_factory=datetime.now)
    fecha_validacion: Optional[datetime] = None
    tiempo_ejecucion_ms: float = 0.0
    fuente_datos: Optional[str] = None
    confianza: float = 0.0  # 0-100%


@dataclass
class ResultadoArea:
    """Resultado agregado por área."""
    area: AreaDueDiligence
    checks_total: int
    checks_aprobados: int
    checks_rechazados: int
    checks_observados: int
    checks_pendientes: int
    score: float  # 0-100
    score_ponderado: float
    riesgos_criticos: int
    riesgos_altos: int
    completitud: float  # 0-100%
    checks: List[ResultadoCheck] = field(default_factory=list)


@dataclass
class ResultadoDueDiligence:
    """Resultado completo del Due Diligence."""
    # Identificación
    id_due_diligence: str
    propiedad_id: str
    rol_sii: Optional[str]
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    
    # Estado general
    estado: str  # en_proceso, completado, con_observaciones, rechazado
    
    # Scores
    score_global: float  # 0-100
    categoria: str  # A, B, C, D, F
    
    # Resultados por área
    areas: Dict[AreaDueDiligence, ResultadoArea]
    
    # Resumen de riesgos
    total_checks: int
    checks_ejecutados: int
    checks_aprobados: int
    checks_rechazados: int
    checks_observados: int
    
    riesgos_criticos: List[ResultadoCheck]
    riesgos_altos: List[ResultadoCheck]
    
    # Deal breakers
    tiene_deal_breakers: bool
    deal_breakers: List[str]
    
    # Recomendaciones
    recomendaciones: List[str]
    condiciones_cierre: List[str]
    
    # Validación
    requiere_validacion_humana: bool
    validadores_requeridos: List[str]
    
    # Metadata
    version: str = "3.0.0"
    hash_documento: str = ""
    tiempo_total_ms: float = 0.0


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class DueDiligenceService:
    """
    Servicio de Due Diligence Inmobiliario.
    
    Ejecuta evaluación integral con 150+ checks en 6 áreas:
    1. Legal: Títulos, gravámenes, litigios
    2. Financiero: Tributario, valoración, operacional
    3. Técnico: Estructura, instalaciones, terminaciones
    4. Ambiental: Contaminación, permisos, riesgos naturales
    5. Urbanístico: Permisos municipales, normativa
    6. Comercial: Mercado, operacional
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._validadores_externos: Dict[str, Callable] = {}
        self._cache_resultados: Dict[str, Any] = {}
    
    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================
    
    async def ejecutar(
        self,
        propiedad_id: str,
        datos_propiedad: Dict[str, Any],
        areas: Optional[List[AreaDueDiligence]] = None,
        nivel_profundidad: str = "completo",  # basico, estandar, completo
        incluir_validacion_humana: bool = True,
        timeout_por_check_ms: int = 30000,
    ) -> ResultadoDueDiligence:
        """
        Ejecuta Due Diligence completo.
        
        Args:
            propiedad_id: ID único de la propiedad
            datos_propiedad: Datos para evaluación
            areas: Áreas a evaluar (None = todas)
            nivel_profundidad: Nivel de detalle
            incluir_validacion_humana: Si marcar checks para HITL
            timeout_por_check_ms: Timeout por check
            
        Returns:
            ResultadoDueDiligence con evaluación completa
        """
        inicio = datetime.now()
        
        # Generar ID único
        id_dd = f"DD-{propiedad_id}-{inicio.strftime('%Y%m%d%H%M%S')}"
        
        # Determinar áreas a evaluar
        areas_evaluar = areas or list(AreaDueDiligence)
        
        # Filtrar checks según nivel de profundidad
        checks_filtrados = self._filtrar_checks_por_nivel(
            areas_evaluar, nivel_profundidad
        )
        
        # Ejecutar checks por área
        resultados_areas: Dict[AreaDueDiligence, ResultadoArea] = {}
        todos_checks: List[ResultadoCheck] = []
        
        for area in areas_evaluar:
            checks_area = checks_filtrados.get(area, [])
            resultado_area = await self._ejecutar_area(
                area=area,
                checks=checks_area,
                datos=datos_propiedad,
                timeout_ms=timeout_por_check_ms,
            )
            resultados_areas[area] = resultado_area
            todos_checks.extend(resultado_area.checks)
        
        # Calcular métricas globales
        score_global = self._calcular_score_global(resultados_areas)
        categoria = self._determinar_categoria(score_global, todos_checks)
        
        # Identificar riesgos críticos y altos
        riesgos_criticos = [
            c for c in todos_checks
            if c.criticidad == CriticidadCheck.CRITICO
            and c.estado in [EstadoCheck.RECHAZADO, EstadoCheck.OBSERVADO]
        ]
        riesgos_altos = [
            c for c in todos_checks
            if c.criticidad == CriticidadCheck.ALTO
            and c.estado in [EstadoCheck.RECHAZADO, EstadoCheck.OBSERVADO]
        ]
        
        # Identificar deal breakers
        deal_breakers = self._identificar_deal_breakers(todos_checks)
        
        # Generar recomendaciones
        recomendaciones = self._generar_recomendaciones(
            todos_checks, resultados_areas, score_global
        )
        
        # Condiciones para cierre
        condiciones = self._generar_condiciones_cierre(
            riesgos_criticos, riesgos_altos
        )
        
        # Determinar si requiere validación humana
        requiere_hitl = incluir_validacion_humana and any(
            c.tipo_validacion in [TipoValidacion.SEMI_AUTOMATICA, TipoValidacion.MANUAL]
            and not c.validado_por_humano
            for c in todos_checks
        )
        
        # Validadores requeridos
        validadores = self._determinar_validadores(todos_checks)
        
        fin = datetime.now()
        tiempo_total = (fin - inicio).total_seconds() * 1000
        
        # Generar hash del documento
        hash_doc = self._generar_hash(todos_checks)
        
        # Determinar estado
        if any(c.estado == EstadoCheck.ERROR for c in todos_checks):
            estado = "con_errores"
        elif deal_breakers:
            estado = "rechazado"
        elif riesgos_criticos or riesgos_altos:
            estado = "con_observaciones"
        elif all(c.estado == EstadoCheck.APROBADO for c in todos_checks if c.estado != EstadoCheck.NO_APLICA):
            estado = "completado"
        else:
            estado = "en_proceso"
        
        return ResultadoDueDiligence(
            id_due_diligence=id_dd,
            propiedad_id=propiedad_id,
            rol_sii=datos_propiedad.get("rol_sii"),
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=estado,
            score_global=score_global,
            categoria=categoria,
            areas=resultados_areas,
            total_checks=len(todos_checks),
            checks_ejecutados=sum(1 for c in todos_checks if c.estado != EstadoCheck.PENDIENTE),
            checks_aprobados=sum(1 for c in todos_checks if c.estado == EstadoCheck.APROBADO),
            checks_rechazados=sum(1 for c in todos_checks if c.estado == EstadoCheck.RECHAZADO),
            checks_observados=sum(1 for c in todos_checks if c.estado == EstadoCheck.OBSERVADO),
            riesgos_criticos=riesgos_criticos,
            riesgos_altos=riesgos_altos,
            tiene_deal_breakers=bool(deal_breakers),
            deal_breakers=deal_breakers,
            recomendaciones=recomendaciones,
            condiciones_cierre=condiciones,
            requiere_validacion_humana=requiere_hitl,
            validadores_requeridos=validadores,
            hash_documento=hash_doc,
            tiempo_total_ms=tiempo_total,
        )
    
    # =========================================================================
    # EJECUCIÓN POR ÁREA
    # =========================================================================
    
    async def _ejecutar_area(
        self,
        area: AreaDueDiligence,
        checks: List[Dict[str, Any]],
        datos: Dict[str, Any],
        timeout_ms: int,
    ) -> ResultadoArea:
        """Ejecuta todos los checks de un área."""
        resultados_checks: List[ResultadoCheck] = []
        
        for check_def in checks:
            resultado = await self._ejecutar_check(
                check_def=check_def,
                area=area,
                datos=datos,
                timeout_ms=timeout_ms,
            )
            resultados_checks.append(resultado)
        
        # Calcular métricas del área
        aprobados = sum(1 for c in resultados_checks if c.estado == EstadoCheck.APROBADO)
        rechazados = sum(1 for c in resultados_checks if c.estado == EstadoCheck.RECHAZADO)
        observados = sum(1 for c in resultados_checks if c.estado == EstadoCheck.OBSERVADO)
        pendientes = sum(1 for c in resultados_checks if c.estado == EstadoCheck.PENDIENTE)
        
        # Score del área (promedio ponderado por criticidad)
        score_area = self._calcular_score_area(resultados_checks)
        
        # Completitud
        ejecutados = len(checks) - pendientes
        completitud = (ejecutados / len(checks) * 100) if checks else 0
        
        return ResultadoArea(
            area=area,
            checks_total=len(checks),
            checks_aprobados=aprobados,
            checks_rechazados=rechazados,
            checks_observados=observados,
            checks_pendientes=pendientes,
            score=score_area,
            score_ponderado=score_area * PONDERACIONES_AREA[area],
            riesgos_criticos=sum(
                1 for c in resultados_checks
                if c.criticidad == CriticidadCheck.CRITICO
                and c.estado in [EstadoCheck.RECHAZADO, EstadoCheck.OBSERVADO]
            ),
            riesgos_altos=sum(
                1 for c in resultados_checks
                if c.criticidad == CriticidadCheck.ALTO
                and c.estado in [EstadoCheck.RECHAZADO, EstadoCheck.OBSERVADO]
            ),
            completitud=completitud,
            checks=resultados_checks,
        )
    
    async def _ejecutar_check(
        self,
        check_def: Dict[str, Any],
        area: AreaDueDiligence,
        datos: Dict[str, Any],
        timeout_ms: int,
    ) -> ResultadoCheck:
        """Ejecuta un check individual."""
        inicio = datetime.now()
        codigo = check_def["codigo"]
        
        try:
            # Determinar método de ejecución según código
            handler = self._get_check_handler(codigo)
            
            if handler:
                estado, score, hallazgos, observaciones, fuente = await asyncio.wait_for(
                    handler(datos),
                    timeout=timeout_ms / 1000
                )
            else:
                # Check sin handler específico - marcar como pendiente
                estado = EstadoCheck.PENDIENTE
                score = 0.0
                hallazgos = []
                observaciones = "Check pendiente de implementación"
                fuente = None
            
            tiempo_ms = (datetime.now() - inicio).total_seconds() * 1000
            
            # Determinar confianza basada en tipo de validación
            confianza = self._calcular_confianza_check(
                check_def["tipo"], estado, hallazgos
            )
            
            return ResultadoCheck(
                codigo=codigo,
                nombre=check_def["nombre"],
                area=area,
                criticidad=check_def["criticidad"],
                tipo_validacion=check_def["tipo"],
                estado=estado,
                score=score,
                hallazgos=hallazgos,
                observaciones=observaciones,
                ejecutado_por_ia=check_def["tipo"] == TipoValidacion.AUTOMATICA,
                validado_por_humano=False,
                fecha_ejecucion=datetime.now(),
                tiempo_ejecucion_ms=tiempo_ms,
                fuente_datos=fuente,
                confianza=confianza,
            )
            
        except asyncio.TimeoutError:
            return ResultadoCheck(
                codigo=codigo,
                nombre=check_def["nombre"],
                area=area,
                criticidad=check_def["criticidad"],
                tipo_validacion=check_def["tipo"],
                estado=EstadoCheck.ERROR,
                score=0.0,
                hallazgos=[],
                observaciones=f"Timeout después de {timeout_ms}ms",
                tiempo_ejecucion_ms=timeout_ms,
                confianza=0.0,
            )
        except Exception as e:
            logger.error(f"Error ejecutando check {codigo}: {e}")
            return ResultadoCheck(
                codigo=codigo,
                nombre=check_def["nombre"],
                area=area,
                criticidad=check_def["criticidad"],
                tipo_validacion=check_def["tipo"],
                estado=EstadoCheck.ERROR,
                score=0.0,
                hallazgos=[],
                observaciones=f"Error: {str(e)}",
                confianza=0.0,
            )
    
    # =========================================================================
    # HANDLERS DE CHECKS ESPECÍFICOS
    # =========================================================================
    
    def _get_check_handler(self, codigo: str) -> Optional[Callable]:
        """Retorna el handler para un código de check."""
        handlers = {
            # LEGAL
            "LEG-001": self._check_inscripcion_cbr,
            "LEG-011": self._check_hipotecas,
            "LEG-012": self._check_prohibiciones,
            "LEG-013": self._check_embargos,
            
            # FINANCIERO
            "FIN-001": self._check_contribuciones,
            "FIN-002": self._check_avaluo_sii,
            "FIN-012": self._check_comparables,
            
            # URBANISTICO
            "URB-001": self._check_permiso_edificacion,
            "URB-002": self._check_recepcion_final,
            "URB-011": self._check_uso_suelo,
            
            # AMBIENTAL
            "AMB-015": self._check_zona_sismica,
            "AMB-016": self._check_zona_inundacion,
            "AMB-017": self._check_zona_tsunami,
            
            # TECNICO
            "TEC-009": self._check_vida_util,
            "TEC-025": self._check_eficiencia_energetica,
            
            # COMERCIAL
            "COM-001": self._check_mercado_zona,
            "COM-008": self._check_liquidez_mercado,
        }
        return handlers.get(codigo)
    
    # --- Checks Legales ---
    
    async def _check_inscripcion_cbr(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """LEG-001: Verifica vigencia de inscripción en CBR."""
        inscripcion = datos.get("legal", {}).get("inscripcion_cbr", {})
        
        if not inscripcion:
            return (
                EstadoCheck.PENDIENTE,
                0.0,
                [],
                "Datos de inscripción no disponibles",
                None
            )
        
        vigente = inscripcion.get("vigente", False)
        foja = inscripcion.get("foja")
        numero = inscripcion.get("numero")
        año = inscripcion.get("año")
        
        if vigente and foja and numero and año:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [f"Inscripción vigente: Foja {foja}, N° {numero}, Año {año}"],
                "Inscripción verificada",
                "Conservador de Bienes Raíces"
            )
        else:
            return (
                EstadoCheck.RECHAZADO,
                0.0,
                ["Inscripción no vigente o incompleta"],
                "Requiere regularización de inscripción",
                "Conservador de Bienes Raíces"
            )
    
    async def _check_hipotecas(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """LEG-011: Verifica hipotecas vigentes."""
        hipotecas = datos.get("legal", {}).get("hipotecas", [])
        
        if not hipotecas:
            return (
                EstadoCheck.APROBADO,
                100.0,
                ["Sin hipotecas registradas"],
                "Propiedad libre de hipotecas",
                "Conservador de Bienes Raíces"
            )
        
        hipotecas_vigentes = [h for h in hipotecas if h.get("vigente", True)]
        
        if hipotecas_vigentes:
            hallazgos = []
            monto_total = 0
            for h in hipotecas_vigentes:
                monto = h.get("monto_uf", 0)
                monto_total += monto
                acreedor = h.get("acreedor", "Desconocido")
                hallazgos.append(f"Hipoteca: {monto:,.0f} UF - {acreedor}")
            
            valor_propiedad = datos.get("financiero", {}).get("valor_uf", 0)
            ltv = (monto_total / valor_propiedad * 100) if valor_propiedad else 0
            
            if ltv > 80:
                return (
                    EstadoCheck.OBSERVADO,
                    30.0,
                    hallazgos + [f"LTV: {ltv:.1f}%"],
                    "Hipoteca con LTV elevado - verificar capacidad de alzamiento",
                    "Conservador de Bienes Raíces"
                )
            else:
                return (
                    EstadoCheck.OBSERVADO,
                    60.0,
                    hallazgos + [f"LTV: {ltv:.1f}%"],
                    "Hipotecas vigentes - considerar en negociación",
                    "Conservador de Bienes Raíces"
                )
        
        return (
            EstadoCheck.APROBADO,
            100.0,
            ["Sin hipotecas vigentes"],
            "Hipotecas alzadas",
            "Conservador de Bienes Raíces"
        )
    
    async def _check_prohibiciones(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """LEG-012: Verifica prohibiciones de enajenar."""
        prohibiciones = datos.get("legal", {}).get("prohibiciones", [])
        
        if not prohibiciones:
            return (
                EstadoCheck.APROBADO,
                100.0,
                ["Sin prohibiciones registradas"],
                "Propiedad sin restricciones de enajenación",
                "Conservador de Bienes Raíces"
            )
        
        prohibiciones_vigentes = [p for p in prohibiciones if p.get("vigente", True)]
        
        if prohibiciones_vigentes:
            hallazgos = [
                f"Prohibición: {p.get('tipo', 'N/A')} - {p.get('beneficiario', 'N/A')}"
                for p in prohibiciones_vigentes
            ]
            return (
                EstadoCheck.RECHAZADO,
                0.0,
                hallazgos,
                "DEAL BREAKER: Prohibición de enajenar vigente",
                "Conservador de Bienes Raíces"
            )
        
        return (
            EstadoCheck.APROBADO,
            100.0,
            ["Prohibiciones alzadas"],
            "Sin prohibiciones vigentes",
            "Conservador de Bienes Raíces"
        )
    
    async def _check_embargos(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """LEG-013: Verifica embargos activos."""
        embargos = datos.get("legal", {}).get("embargos", [])
        
        if not embargos:
            return (
                EstadoCheck.APROBADO,
                100.0,
                ["Sin embargos registrados"],
                "Propiedad libre de embargos",
                "Conservador de Bienes Raíces"
            )
        
        embargos_activos = [e for e in embargos if e.get("activo", True)]
        
        if embargos_activos:
            hallazgos = [
                f"Embargo: {e.get('causa', 'N/A')} - {e.get('tribunal', 'N/A')}"
                for e in embargos_activos
            ]
            return (
                EstadoCheck.RECHAZADO,
                0.0,
                hallazgos,
                "DEAL BREAKER: Embargo activo sobre la propiedad",
                "Poder Judicial / CBR"
            )
        
        return (
            EstadoCheck.APROBADO,
            100.0,
            ["Embargos alzados"],
            "Sin embargos activos",
            "Conservador de Bienes Raíces"
        )
    
    # --- Checks Financieros ---
    
    async def _check_contribuciones(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """FIN-001: Verifica contribuciones al día."""
        contribuciones = datos.get("financiero", {}).get("contribuciones", {})
        
        al_dia = contribuciones.get("al_dia", None)
        deuda = contribuciones.get("deuda_uf", 0)
        
        if al_dia is None:
            return (
                EstadoCheck.PENDIENTE,
                0.0,
                [],
                "Verificar estado de contribuciones en TGR",
                None
            )
        
        if al_dia:
            return (
                EstadoCheck.APROBADO,
                100.0,
                ["Contribuciones pagadas al día"],
                "Sin deuda de contribuciones",
                "SII / TGR"
            )
        else:
            return (
                EstadoCheck.OBSERVADO,
                50.0,
                [f"Deuda de contribuciones: {deuda:,.2f} UF"],
                "Deuda debe ser pagada previo a transferencia",
                "SII / TGR"
            )
    
    async def _check_avaluo_sii(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """FIN-002: Obtiene avalúo fiscal SII."""
        sii = datos.get("financiero", {}).get("sii", {})
        
        avaluo = sii.get("avaluo_fiscal_uf", 0)
        año_avaluo = sii.get("año_avaluo", 0)
        
        if avaluo > 0:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [f"Avalúo fiscal: {avaluo:,.0f} UF (año {año_avaluo})"],
                "Información de avalúo obtenida",
                "SII"
            )
        else:
            return (
                EstadoCheck.PENDIENTE,
                0.0,
                [],
                "Avalúo fiscal no disponible",
                None
            )
    
    async def _check_comparables(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """FIN-012: Analiza comparables de mercado."""
        comparables = datos.get("financiero", {}).get("comparables", [])
        
        if len(comparables) >= 3:
            precios = [c.get("precio_uf_m2", 0) for c in comparables]
            precio_prom = np.mean(precios)
            precio_med = np.median(precios)
            
            return (
                EstadoCheck.APROBADO,
                100.0,
                [
                    f"Comparables analizados: {len(comparables)}",
                    f"Precio promedio: {precio_prom:,.0f} UF/m²",
                    f"Precio mediana: {precio_med:,.0f} UF/m²"
                ],
                "Base de comparables suficiente",
                "Mercado inmobiliario"
            )
        elif len(comparables) > 0:
            return (
                EstadoCheck.OBSERVADO,
                60.0,
                [f"Solo {len(comparables)} comparable(s) disponible(s)"],
                "Base de comparables limitada",
                "Mercado inmobiliario"
            )
        else:
            return (
                EstadoCheck.PENDIENTE,
                0.0,
                [],
                "Sin comparables disponibles",
                None
            )
    
    # --- Checks Urbanísticos ---
    
    async def _check_permiso_edificacion(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """URB-001: Verifica permiso de edificación."""
        permisos = datos.get("urbanistico", {}).get("permisos", {})
        
        tiene_permiso = permisos.get("permiso_edificacion", False)
        numero_permiso = permisos.get("numero_permiso", "")
        fecha_permiso = permisos.get("fecha_permiso", "")
        
        if tiene_permiso:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [f"Permiso N° {numero_permiso} de fecha {fecha_permiso}"],
                "Permiso de edificación vigente",
                "DOM Municipal"
            )
        else:
            return (
                EstadoCheck.RECHAZADO,
                0.0,
                ["Sin permiso de edificación"],
                "CRÍTICO: Construcción sin permiso municipal",
                "DOM Municipal"
            )
    
    async def _check_recepcion_final(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """URB-002: Verifica recepción final municipal."""
        permisos = datos.get("urbanistico", {}).get("permisos", {})
        
        tiene_recepcion = permisos.get("recepcion_final", False)
        fecha_recepcion = permisos.get("fecha_recepcion", "")
        
        if tiene_recepcion:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [f"Recepción final de fecha {fecha_recepcion}"],
                "Obra recepcionada por municipio",
                "DOM Municipal"
            )
        else:
            # Verificar si tiene permiso pero no recepción
            tiene_permiso = permisos.get("permiso_edificacion", False)
            if tiene_permiso:
                return (
                    EstadoCheck.OBSERVADO,
                    40.0,
                    ["Con permiso, sin recepción final"],
                    "Gestionar recepción final",
                    "DOM Municipal"
                )
            else:
                return (
                    EstadoCheck.RECHAZADO,
                    0.0,
                    ["Sin recepción final"],
                    "CRÍTICO: Obra no recepcionada",
                    "DOM Municipal"
                )
    
    async def _check_uso_suelo(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """URB-011: Verifica uso de suelo permitido."""
        urbanistico = datos.get("urbanistico", {})
        
        uso_actual = urbanistico.get("uso_actual", "")
        uso_permitido = urbanistico.get("uso_permitido", [])
        zona = urbanistico.get("zona_prc", "")
        
        if not uso_actual or not uso_permitido:
            return (
                EstadoCheck.PENDIENTE,
                0.0,
                [],
                "Verificar uso de suelo en CIP municipal",
                None
            )
        
        if uso_actual in uso_permitido:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [
                    f"Uso actual: {uso_actual}",
                    f"Zona PRC: {zona}",
                    f"Usos permitidos: {', '.join(uso_permitido)}"
                ],
                "Uso de suelo compatible con normativa",
                "PRC Municipal"
            )
        else:
            return (
                EstadoCheck.RECHAZADO,
                0.0,
                [
                    f"Uso actual: {uso_actual}",
                    f"Usos permitidos: {', '.join(uso_permitido)}"
                ],
                "DEAL BREAKER: Uso de suelo no permitido",
                "PRC Municipal"
            )
    
    # --- Checks Ambientales ---
    
    async def _check_zona_sismica(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """AMB-015: Evalúa zona de riesgo sísmico."""
        riesgos = datos.get("ambiental", {}).get("riesgos", {})
        
        zona_sismica = riesgos.get("zona_sismica", "2")  # Chile: zonas 1, 2, 3
        aceleracion = riesgos.get("aceleracion_suelo", 0.3)
        
        if zona_sismica == "1":
            return (
                EstadoCheck.APROBADO,
                100.0,
                [f"Zona sísmica 1 (menor riesgo)", f"Aceleración: {aceleracion}g"],
                "Zona de menor riesgo sísmico",
                "NCh 433 / SHOA"
            )
        elif zona_sismica == "2":
            return (
                EstadoCheck.APROBADO,
                80.0,
                [f"Zona sísmica 2 (riesgo medio)", f"Aceleración: {aceleracion}g"],
                "Verificar cumplimiento NCh 433",
                "NCh 433 / SHOA"
            )
        else:
            return (
                EstadoCheck.OBSERVADO,
                60.0,
                [f"Zona sísmica 3 (mayor riesgo)", f"Aceleración: {aceleracion}g"],
                "Zona de mayor riesgo - verificar diseño estructural",
                "NCh 433 / SHOA"
            )
    
    async def _check_zona_inundacion(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """AMB-016: Evalúa zona de inundación."""
        riesgos = datos.get("ambiental", {}).get("riesgos", {})
        
        zona_inundacion = riesgos.get("zona_inundacion", False)
        periodo_retorno = riesgos.get("periodo_retorno_inundacion", 0)
        
        if not zona_inundacion:
            return (
                EstadoCheck.APROBADO,
                100.0,
                ["Fuera de zona de inundación"],
                "Sin riesgo de inundación identificado",
                "SENAPRED / MOP"
            )
        else:
            if periodo_retorno <= 10:
                return (
                    EstadoCheck.RECHAZADO,
                    0.0,
                    [f"Zona de inundación recurrente (T={periodo_retorno} años)"],
                    "DEAL BREAKER: Alto riesgo de inundación",
                    "SENAPRED / MOP"
                )
            elif periodo_retorno <= 50:
                return (
                    EstadoCheck.OBSERVADO,
                    40.0,
                    [f"Zona de inundación (T={periodo_retorno} años)"],
                    "Riesgo medio de inundación - verificar seguros",
                    "SENAPRED / MOP"
                )
            else:
                return (
                    EstadoCheck.OBSERVADO,
                    70.0,
                    [f"Zona de inundación baja (T={periodo_retorno} años)"],
                    "Bajo riesgo de inundación",
                    "SENAPRED / MOP"
                )
    
    async def _check_zona_tsunami(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """AMB-017: Evalúa zona de tsunami."""
        riesgos = datos.get("ambiental", {}).get("riesgos", {})
        
        zona_tsunami = riesgos.get("zona_tsunami", False)
        cota_msnm = riesgos.get("cota_msnm", 100)
        distancia_costa_m = riesgos.get("distancia_costa_m", 10000)
        
        if not zona_tsunami or distancia_costa_m > 5000 or cota_msnm > 30:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [
                    f"Cota: {cota_msnm} msnm",
                    f"Distancia costa: {distancia_costa_m/1000:.1f} km"
                ],
                "Fuera de zona de riesgo de tsunami",
                "SHOA"
            )
        else:
            if cota_msnm < 10 and distancia_costa_m < 500:
                return (
                    EstadoCheck.RECHAZADO,
                    0.0,
                    [
                        f"Cota: {cota_msnm} msnm",
                        f"Distancia costa: {distancia_costa_m} m"
                    ],
                    "DEAL BREAKER: Alto riesgo de tsunami",
                    "SHOA"
                )
            else:
                return (
                    EstadoCheck.OBSERVADO,
                    50.0,
                    [
                        f"Cota: {cota_msnm} msnm",
                        f"Distancia costa: {distancia_costa_m} m"
                    ],
                    "En zona de riesgo de tsunami - verificar vías de evacuación",
                    "SHOA"
                )
    
    # --- Checks Técnicos ---
    
    async def _check_vida_util(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """TEC-009: Calcula vida útil remanente."""
        tecnico = datos.get("tecnico", {})
        
        año_construccion = datos.get("basico", {}).get("año_construccion", 2000)
        tipo_construccion = tecnico.get("tipo_construccion", "hormigon")
        estado = tecnico.get("estado_conservacion", "regular")
        
        vidas_utiles = {
            "hormigon": 80,
            "albanileria": 60,
            "madera": 40,
            "metalica": 50,
        }
        
        factores_estado = {
            "excelente": 1.2,
            "muy_bueno": 1.1,
            "bueno": 1.0,
            "regular": 0.9,
            "malo": 0.7,
            "muy_malo": 0.5,
        }
        
        vida_base = vidas_utiles.get(tipo_construccion, 60)
        factor = factores_estado.get(estado, 0.9)
        vida_ajustada = vida_base * factor
        
        antiguedad = datetime.now().year - año_construccion
        vida_remanente = max(0, vida_ajustada - antiguedad)
        pct_remanente = (vida_remanente / vida_ajustada * 100) if vida_ajustada else 0
        
        score = min(100, pct_remanente)
        
        if pct_remanente >= 50:
            return (
                EstadoCheck.APROBADO,
                score,
                [
                    f"Antigüedad: {antiguedad} años",
                    f"Vida útil remanente: {vida_remanente:.0f} años ({pct_remanente:.0f}%)"
                ],
                "Vida útil adecuada",
                "Cálculo técnico"
            )
        elif pct_remanente >= 25:
            return (
                EstadoCheck.OBSERVADO,
                score,
                [
                    f"Antigüedad: {antiguedad} años",
                    f"Vida útil remanente: {vida_remanente:.0f} años ({pct_remanente:.0f}%)"
                ],
                "Considerar renovaciones mayores",
                "Cálculo técnico"
            )
        else:
            return (
                EstadoCheck.OBSERVADO,
                score,
                [
                    f"Antigüedad: {antiguedad} años",
                    f"Vida útil remanente: {vida_remanente:.0f} años ({pct_remanente:.0f}%)"
                ],
                "Vida útil crítica - evaluar demolición/reconstrucción",
                "Cálculo técnico"
            )
    
    async def _check_eficiencia_energetica(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """TEC-025: Evalúa eficiencia energética."""
        tecnico = datos.get("tecnico", {})
        
        certificacion = tecnico.get("certificacion_energetica", "")
        consumo_kwh_m2 = tecnico.get("consumo_energia_kwh_m2_año", 0)
        
        scores_cert = {
            "A+": 100, "A": 95, "B": 85, "C": 75,
            "D": 60, "E": 45, "F": 30, "G": 15
        }
        
        if certificacion:
            score = scores_cert.get(certificacion, 50)
            if certificacion in ["A+", "A", "B"]:
                return (
                    EstadoCheck.APROBADO,
                    score,
                    [
                        f"Certificación energética: {certificacion}",
                        f"Consumo: {consumo_kwh_m2} kWh/m²/año" if consumo_kwh_m2 else ""
                    ],
                    "Buena eficiencia energética",
                    "MINVU / Certificador"
                )
            elif certificacion in ["C", "D"]:
                return (
                    EstadoCheck.APROBADO,
                    score,
                    [f"Certificación energética: {certificacion}"],
                    "Eficiencia energética media",
                    "MINVU / Certificador"
                )
            else:
                return (
                    EstadoCheck.OBSERVADO,
                    score,
                    [f"Certificación energética: {certificacion}"],
                    "Baja eficiencia energética - potencial de mejora",
                    "MINVU / Certificador"
                )
        else:
            return (
                EstadoCheck.APROBADO,
                50.0,
                ["Sin certificación energética"],
                "Certificación no requerida o no disponible",
                None
            )
    
    # --- Checks Comerciales ---
    
    async def _check_mercado_zona(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """COM-001: Análisis de mercado de la zona."""
        comercial = datos.get("comercial", {})
        
        indice_demanda = comercial.get("indice_demanda", 50)
        tendencia = comercial.get("tendencia_precios_12m_pct", 0)
        absorcion = comercial.get("tasa_absorcion_pct", 0)
        
        score = (indice_demanda * 0.5) + (min(100, max(0, tendencia * 5 + 50)) * 0.3) + (absorcion * 0.2)
        
        hallazgos = [
            f"Índice de demanda: {indice_demanda}/100",
            f"Tendencia precios 12m: {tendencia:+.1f}%",
            f"Tasa de absorción: {absorcion:.1f}%"
        ]
        
        if score >= 70:
            return (
                EstadoCheck.APROBADO,
                score,
                hallazgos,
                "Mercado dinámico y favorable",
                "Análisis de mercado"
            )
        elif score >= 50:
            return (
                EstadoCheck.APROBADO,
                score,
                hallazgos,
                "Mercado estable",
                "Análisis de mercado"
            )
        else:
            return (
                EstadoCheck.OBSERVADO,
                score,
                hallazgos,
                "Mercado débil - considerar estrategia de salida",
                "Análisis de mercado"
            )
    
    async def _check_liquidez_mercado(
        self, datos: Dict[str, Any]
    ) -> Tuple[EstadoCheck, float, List[str], str, Optional[str]]:
        """COM-008: Evalúa liquidez del mercado."""
        comercial = datos.get("comercial", {})
        
        dias_mercado = comercial.get("dias_mercado_promedio", 90)
        transacciones_12m = comercial.get("transacciones_zona_12m", 0)
        
        score = max(0, 100 - (dias_mercado - 30))  # Base 30 días
        
        if dias_mercado <= 30:
            return (
                EstadoCheck.APROBADO,
                100.0,
                [
                    f"Tiempo promedio en mercado: {dias_mercado} días",
                    f"Transacciones últimos 12m: {transacciones_12m}"
                ],
                "Alta liquidez",
                "Análisis de mercado"
            )
        elif dias_mercado <= 60:
            return (
                EstadoCheck.APROBADO,
                score,
                [f"Tiempo promedio en mercado: {dias_mercado} días"],
                "Liquidez normal",
                "Análisis de mercado"
            )
        elif dias_mercado <= 120:
            return (
                EstadoCheck.OBSERVADO,
                score,
                [f"Tiempo promedio en mercado: {dias_mercado} días"],
                "Liquidez moderada - considerar pricing competitivo",
                "Análisis de mercado"
            )
        else:
            return (
                EstadoCheck.OBSERVADO,
                max(0, score),
                [f"Tiempo promedio en mercado: {dias_mercado} días"],
                "Baja liquidez - mercado lento",
                "Análisis de mercado"
            )
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def _filtrar_checks_por_nivel(
        self,
        areas: List[AreaDueDiligence],
        nivel: str,
    ) -> Dict[AreaDueDiligence, List[Dict]]:
        """Filtra checks según nivel de profundidad."""
        resultado = {}
        
        for area in areas:
            checks_area = CHECKS_DUE_DILIGENCE.get(area, [])
            
            if nivel == "basico":
                # Solo críticos y altos
                checks_filtrados = [
                    c for c in checks_area
                    if c["criticidad"] in [CriticidadCheck.CRITICO, CriticidadCheck.ALTO]
                ]
            elif nivel == "estandar":
                # Críticos, altos y medios
                checks_filtrados = [
                    c for c in checks_area
                    if c["criticidad"] in [
                        CriticidadCheck.CRITICO,
                        CriticidadCheck.ALTO,
                        CriticidadCheck.MEDIO
                    ]
                ]
            else:  # completo
                checks_filtrados = checks_area
            
            resultado[area] = checks_filtrados
        
        return resultado
    
    def _calcular_score_area(self, checks: List[ResultadoCheck]) -> float:
        """Calcula score de un área basado en checks."""
        if not checks:
            return 0.0
        
        # Ponderación por criticidad
        pesos = {
            CriticidadCheck.CRITICO: 4.0,
            CriticidadCheck.ALTO: 3.0,
            CriticidadCheck.MEDIO: 2.0,
            CriticidadCheck.BAJO: 1.0,
            CriticidadCheck.INFORMATIVO: 0.5,
        }
        
        total_ponderado = 0.0
        total_pesos = 0.0
        
        for check in checks:
            if check.estado == EstadoCheck.NO_APLICA:
                continue
            peso = pesos.get(check.criticidad, 1.0)
            total_ponderado += check.score * peso
            total_pesos += peso
        
        return (total_ponderado / total_pesos) if total_pesos > 0 else 0.0
    
    def _calcular_score_global(
        self,
        areas: Dict[AreaDueDiligence, ResultadoArea],
    ) -> float:
        """Calcula score global ponderado por área."""
        total = sum(area.score_ponderado for area in areas.values())
        return round(total, 1)
    
    def _determinar_categoria(
        self,
        score: float,
        checks: List[ResultadoCheck],
    ) -> str:
        """Determina categoría del due diligence."""
        # Verificar deal breakers
        criticos_rechazados = sum(
            1 for c in checks
            if c.criticidad == CriticidadCheck.CRITICO
            and c.estado == EstadoCheck.RECHAZADO
        )
        
        if criticos_rechazados > 0:
            return "F"  # Fail
        
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
    
    def _identificar_deal_breakers(
        self,
        checks: List[ResultadoCheck],
    ) -> List[str]:
        """Identifica deal breakers en los checks."""
        deal_breakers = []
        
        for check in checks:
            if (check.criticidad == CriticidadCheck.CRITICO
                and check.estado == EstadoCheck.RECHAZADO):
                deal_breakers.append(f"{check.codigo}: {check.nombre}")
        
        return deal_breakers
    
    def _generar_recomendaciones(
        self,
        checks: List[ResultadoCheck],
        areas: Dict[AreaDueDiligence, ResultadoArea],
        score: float,
    ) -> List[str]:
        """Genera recomendaciones basadas en resultados."""
        recomendaciones = []
        
        # Por score global
        if score < 50:
            recomendaciones.append(
                "⚠️ Score global bajo - Se recomienda revisión profunda antes de proceder"
            )
        
        # Por área débil
        for area_enum, area in areas.items():
            if area.score < 50:
                recomendaciones.append(
                    f"📋 Área {area_enum.value}: Requiere atención especial (score: {area.score:.0f})"
                )
        
        # Por checks críticos observados
        criticos_obs = [
            c for c in checks
            if c.criticidad == CriticidadCheck.CRITICO
            and c.estado == EstadoCheck.OBSERVADO
        ]
        for check in criticos_obs[:3]:  # Max 3
            recomendaciones.append(f"🔴 Resolver: {check.nombre}")
        
        # Por checks que requieren validación
        requieren_validacion = sum(
            1 for c in checks
            if c.tipo_validacion in [TipoValidacion.SEMI_AUTOMATICA, TipoValidacion.MANUAL]
            and not c.validado_por_humano
        )
        if requieren_validacion > 0:
            recomendaciones.append(
                f"👤 {requieren_validacion} check(s) requieren validación humana"
            )
        
        return recomendaciones[:8]
    
    def _generar_condiciones_cierre(
        self,
        riesgos_criticos: List[ResultadoCheck],
        riesgos_altos: List[ResultadoCheck],
    ) -> List[str]:
        """Genera condiciones para cierre de transacción."""
        condiciones = []
        
        for riesgo in riesgos_criticos:
            condiciones.append(
                f"CRÍTICO: Resolver {riesgo.nombre} antes de cierre"
            )
        
        for riesgo in riesgos_altos[:5]:
            condiciones.append(
                f"IMPORTANTE: {riesgo.nombre}"
            )
        
        return condiciones
    
    def _determinar_validadores(
        self,
        checks: List[ResultadoCheck],
    ) -> List[str]:
        """Determina validadores requeridos según checks."""
        validadores = set()
        
        for check in checks:
            if check.tipo_validacion == TipoValidacion.MANUAL:
                if check.area == AreaDueDiligence.LEGAL:
                    validadores.add("Abogado inmobiliario")
                elif check.area == AreaDueDiligence.TECNICO:
                    validadores.add("Ingeniero estructural")
                elif check.area == AreaDueDiligence.AMBIENTAL:
                    validadores.add("Consultor ambiental")
                elif check.area == AreaDueDiligence.FINANCIERO:
                    validadores.add("Analista financiero")
            elif check.tipo_validacion == TipoValidacion.EXTERNA:
                if "SEC" in check.nombre:
                    validadores.add("Certificador SEC")
                elif "estructural" in check.nombre.lower():
                    validadores.add("Ingeniero civil")
        
        return list(validadores)
    
    def _calcular_confianza_check(
        self,
        tipo: TipoValidacion,
        estado: EstadoCheck,
        hallazgos: List[str],
    ) -> float:
        """Calcula confianza del check."""
        base = {
            TipoValidacion.AUTOMATICA: 85.0,
            TipoValidacion.SEMI_AUTOMATICA: 70.0,
            TipoValidacion.MANUAL: 95.0,  # Manual validado tiene alta confianza
            TipoValidacion.EXTERNA: 90.0,
        }.get(tipo, 50.0)
        
        # Ajustar por estado
        if estado == EstadoCheck.ERROR:
            return 0.0
        elif estado == EstadoCheck.PENDIENTE:
            return 0.0
        
        # Bonus por hallazgos documentados
        if hallazgos:
            base = min(100, base + len(hallazgos) * 2)
        
        return base
    
    def _generar_hash(self, checks: List[ResultadoCheck]) -> str:
        """Genera hash del documento para integridad."""
        contenido = json.dumps(
            [
                {
                    "codigo": c.codigo,
                    "estado": c.estado.value,
                    "score": c.score,
                    "fecha": c.fecha_ejecucion.isoformat(),
                }
                for c in checks
            ],
            sort_keys=True
        )
        return hashlib.sha256(contenido.encode()).hexdigest()[:16]


# =============================================================================
# FUNCIONES AUXILIARES PARA API
# =============================================================================

async def ejecutar_due_diligence(
    db: AsyncSession,
    propiedad_id: str,
    datos: Dict[str, Any],
    **kwargs,
) -> ResultadoDueDiligence:
    """
    Función wrapper para ejecutar Due Diligence.
    
    Uso:
        resultado = await ejecutar_due_diligence(
            db=session,
            propiedad_id="PROP-12345",
            datos={
                "basico": {...},
                "legal": {...},
                "financiero": {...},
                ...
            },
        )
    """
    service = DueDiligenceService(db)
    return await service.ejecutar(
        propiedad_id=propiedad_id,
        datos_propiedad=datos,
        **kwargs,
    )


def due_diligence_to_dict(resultado: ResultadoDueDiligence) -> Dict[str, Any]:
    """Convierte resultado a diccionario serializable."""
    return {
        "id": resultado.id_due_diligence,
        "propiedad_id": resultado.propiedad_id,
        "rol_sii": resultado.rol_sii,
        "fecha_inicio": resultado.fecha_inicio.isoformat(),
        "fecha_fin": resultado.fecha_fin.isoformat() if resultado.fecha_fin else None,
        "estado": resultado.estado,
        "score_global": resultado.score_global,
        "categoria": resultado.categoria,
        "resumen": {
            "total_checks": resultado.total_checks,
            "ejecutados": resultado.checks_ejecutados,
            "aprobados": resultado.checks_aprobados,
            "rechazados": resultado.checks_rechazados,
            "observados": resultado.checks_observados,
        },
        "areas": {
            area.value: {
                "score": data.score,
                "score_ponderado": data.score_ponderado,
                "checks_total": data.checks_total,
                "aprobados": data.checks_aprobados,
                "rechazados": data.checks_rechazados,
                "completitud": data.completitud,
            }
            for area, data in resultado.areas.items()
        },
        "deal_breakers": resultado.deal_breakers,
        "riesgos_criticos": [
            {"codigo": r.codigo, "nombre": r.nombre, "observaciones": r.observaciones}
            for r in resultado.riesgos_criticos
        ],
        "riesgos_altos": [
            {"codigo": r.codigo, "nombre": r.nombre, "observaciones": r.observaciones}
            for r in resultado.riesgos_altos
        ],
        "recomendaciones": resultado.recomendaciones,
        "condiciones_cierre": resultado.condiciones_cierre,
        "requiere_validacion": resultado.requiere_validacion_humana,
        "validadores": resultado.validadores_requeridos,
        "hash": resultado.hash_documento,
        "tiempo_ms": resultado.tiempo_total_ms,
    }
