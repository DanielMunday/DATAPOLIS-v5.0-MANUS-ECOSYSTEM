"""
DATAPOLIS v3.0 - Routers API COMPLETO
=====================================
Registro centralizado de todos los routers de la aplicación.

Módulos Core:
- auth: Autenticación JWT/OAuth2, 2FA, sesiones (20 endpoints)
- usuarios: Gestión de usuarios, roles, permisos, equipos (23 endpoints)
- expediente: M00 Expediente Universal - Gestión documental (26 endpoints)
- ficha_propiedad: M01 Ficha Propiedad - Datos técnicos inmobiliarios (20 endpoints)
- copropiedad: M02 Copropiedad - Gestión condominios Ley 21.442 (32 endpoints)
- arriendos: M05 Arriendos - Gestión arriendos Ley 18.101/21.461 (22 endpoints)
- mantenciones: M06 Mantenciones - Gestión mantenciones NCh 3562 (26 endpoints)
- analisis_inversion: M07 Análisis Inversión - ROI/TIR/VAN/Monte Carlo (28 endpoints)
- plusvalia: M06B Plusvalía - Ganancias capital Ley 21.210/21.713 (22 endpoints)

Módulos Negocio:
- indicadores: UF, IPC, tasas BCCh, tipo cambio (15 endpoints)
- valorizacion: Valorización IVS 2022, comparables, ML (17 endpoints)
- credit_score: Scoring 5 dimensiones, SHAP, riesgos (16 endpoints)
- due_diligence: 150+ checks, 6 áreas, HITL (25 endpoints)

Módulos FinTech NCG 514:
- open_finance: Open Finance NCG 514 CMF - AIS/PIS/OAuth2/FAPI (45 endpoints)
- fintech_avanzado: TNFD/Basel IV/SCF ESG (35 endpoints)

Integraciones:
- gires: Integración ESRI/ArcGIS (M17) (24 endpoints)
- mercado_suelo: Análisis mercado de suelo (MS) (14 endpoints)

TOTAL: 410+ endpoints | 17 routers | 70,000+ líneas Python

Autor: DATAPOLIS SpA
Versión: 3.0.0
Deadline NCG 514: Abril 2026
"""

from fastapi import APIRouter

# Importar todos los routers existentes
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.expediente import router as expediente_router
from app.routers.ficha_propiedad import router as ficha_propiedad_router
from app.routers.indicadores import router as indicadores_router
from app.routers.valorizacion import router as valorizacion_router
from app.routers.credit_score import router as credit_score_router
from app.routers.due_diligence import router as due_diligence_router
from app.routers.gires import router as gires_router
from app.routers.mercado_suelo import router as mercado_suelo_router
from app.routers.copropiedad import router as copropiedad_router
from app.routers.arriendos import router as arriendos_router
from app.routers.mantenciones import router as mantenciones_router
from app.routers.analisis_inversion import router as analisis_inversion_router
from app.routers.plusvalia import router as plusvalia_router

# Importar NUEVOS routers FinTech NCG 514
from app.routers.open_finance import router as open_finance_router
from app.routers.fintech_avanzado import router as fintech_avanzado_router

# Router principal que agrupa todos los módulos
api_router = APIRouter(prefix="/api/v1")

# =============================================================================
# REGISTRO DE ROUTERS
# =============================================================================

# Autenticación y usuarios (sin prefix adicional, ya tienen el suyo)
api_router.include_router(auth_router)
api_router.include_router(users_router)

# Módulos Core DATAPOLIS
api_router.include_router(expediente_router)
api_router.include_router(ficha_propiedad_router)
api_router.include_router(copropiedad_router)
api_router.include_router(arriendos_router)
api_router.include_router(mantenciones_router)
api_router.include_router(analisis_inversion_router)
api_router.include_router(plusvalia_router)

# Módulos de negocio core
api_router.include_router(indicadores_router)
api_router.include_router(valorizacion_router)
api_router.include_router(credit_score_router)
api_router.include_router(due_diligence_router)

# Integraciones externas
api_router.include_router(gires_router)
api_router.include_router(mercado_suelo_router)

# ============================================================================
# MÓDULOS FINTECH NCG 514 - OPEN FINANCE (NUEVO)
# ============================================================================
api_router.include_router(open_finance_router)
api_router.include_router(fintech_avanzado_router)

# =============================================================================
# EXPORTACIONES
# =============================================================================

__all__ = [
    # Router principal
    "api_router",
    # Routers individuales - Auth & Users
    "auth_router",
    "users_router",
    # Routers individuales - Core
    "expediente_router",
    "ficha_propiedad_router",
    "copropiedad_router",
    "arriendos_router",
    "mantenciones_router",
    "analisis_inversion_router",
    "plusvalia_router",
    # Routers individuales - Negocio
    "indicadores_router",
    "valorizacion_router", 
    "credit_score_router",
    "due_diligence_router",
    # Routers individuales - Integraciones
    "gires_router",
    "mercado_suelo_router",
    # Routers individuales - FinTech NCG 514 (NUEVO)
    "open_finance_router",
    "fintech_avanzado_router",
    # Metadata
    "ROUTERS_METADATA"
]

# =============================================================================
# METADATA DE ROUTERS
# =============================================================================

ROUTERS_METADATA = {
    "auth": {
        "prefix": "/api/v1/auth",
        "tags": ["Autenticación"],
        "description": "JWT, OAuth2, 2FA, sesiones, recuperación de contraseña",
        "version": "1.0.0",
        "endpoints_count": 20
    },
    "usuarios": {
        "prefix": "/api/v1/usuarios",
        "tags": ["Usuarios"],
        "description": "Gestión de usuarios, perfiles, roles, permisos, equipos",
        "version": "1.0.0",
        "endpoints_count": 23
    },
    "expediente": {
        "prefix": "/api/v1/expediente",
        "tags": ["M00 - Expediente Universal"],
        "description": "Gestión documental centralizada, workflows, alertas, versionamiento",
        "version": "1.0.0",
        "endpoints_count": 26
    },
    "ficha_propiedad": {
        "prefix": "/api/v1/ficha-propiedad",
        "tags": ["M01 - Ficha Propiedad"],
        "description": "Datos técnicos inmobiliarios, SII, CBR, valorización, comparables",
        "version": "1.0.0",
        "endpoints_count": 20
    },
    "copropiedad": {
        "prefix": "/api/v1/copropiedad",
        "tags": ["M02 - Copropiedad"],
        "description": "Gestión integral condominios Ley 21.442, asambleas, gastos comunes, CMF",
        "version": "1.0.0",
        "endpoints_count": 32
    },
    "arriendos": {
        "prefix": "/api/v1/arriendos",
        "tags": ["M05 - Arriendos"],
        "description": "Gestión arriendos Ley 18.101/21.461, contratos, cobros, garantías, rentabilidad",
        "version": "1.0.0",
        "endpoints_count": 22
    },
    "mantenciones": {
        "prefix": "/api/v1/mantenciones",
        "tags": ["M06 - Mantenciones"],
        "description": "Gestión mantenciones preventivas/correctivas, planes, proveedores, KPIs NCh 3562",
        "version": "1.0.0",
        "endpoints_count": 26
    },
    "analisis_inversion": {
        "prefix": "/api/v1/analisis-inversion",
        "tags": ["M07 - Análisis de Inversión"],
        "description": "Análisis financiero inversiones: ROI, TIR, VAN, Monte Carlo, optimización portfolios",
        "version": "1.0.0",
        "endpoints_count": 28
    },
    "plusvalia": {
        "prefix": "/api/v1/plusvalia",
        "tags": ["M06B - Plusvalía y Ganancias de Capital"],
        "description": "Cálculo plusvalías, ganancias capital Ley 21.210/21.713, proyecciones, benchmarks",
        "version": "1.0.0",
        "endpoints_count": 22
    },
    "indicadores": {
        "prefix": "/api/v1/indicadores",
        "tags": ["Indicadores Económicos"],
        "description": "UF, IPC, tasas, tipo cambio BCCh, proyecciones ML",
        "version": "1.0.0",
        "endpoints_count": 15
    },
    "valorizacion": {
        "prefix": "/api/v1/valorizacion",
        "tags": ["Valorización Inmobiliaria"],
        "description": "Valorización IVS 2022, comparables, ajustes, informes",
        "version": "1.0.0",
        "endpoints_count": 17
    },
    "credit_score": {
        "prefix": "/api/v1/credit-score",
        "tags": ["Credit Score Inmobiliario"],
        "description": "Scoring 5 dimensiones, SHAP, simulaciones, benchmarks",
        "version": "1.0.0",
        "endpoints_count": 16
    },
    "due_diligence": {
        "prefix": "/api/v1/due-diligence",
        "tags": ["Due Diligence Inmobiliario"],
        "description": "150+ checks, 6 áreas, HITL, deal breakers",
        "version": "1.0.0",
        "endpoints_count": 25
    },
    "gires": {
        "prefix": "/api/v1/gires",
        "tags": ["GIRES - Integración Geoespacial"],
        "description": "ESRI/ArcGIS, capas territoriales, análisis espacial",
        "version": "1.0.0",
        "endpoints_count": 24
    },
    "mercado_suelo": {
        "prefix": "/api/v1/mercado",
        "tags": ["Mercado de Suelo"],
        "description": "Ofertas, clusters espaciales, modelo hedónico, oportunidades inversión",
        "version": "1.0.0",
        "endpoints_count": 14
    },
    "open_finance": {
        "prefix": "/api/v1/open-finance",
        "tags": ["Open Finance NCG 514"],
        "description": "Open Finance Chile: AIS, PIS, OAuth2+PKCE, FAPI 2.0, Directorio CMF, ISO 20022",
        "version": "3.0.0",
        "endpoints_count": 45,
        "normativas": ["NCG 514 CMF", "FAPI 2.0", "ISO 20022", "RFC 9126", "RFC 8705"],
        "deadline": "Abril 2026"
    },
    "fintech_avanzado": {
        "prefix": "/api/v1/fintech",
        "tags": ["FinTech Avanzado"],
        "description": "TNFD Nature Risk, Basel IV Capital, SCF ESG Supply Chain Finance",
        "version": "3.0.0",
        "endpoints_count": 35,
        "normativas": ["TNFD v1.0", "Basel IV CR-SA", "GHG Protocol Scope 3", "NIIF S1/S2"]
    }
}

# Estadísticas globales
TOTAL_ENDPOINTS = sum(r["endpoints_count"] for r in ROUTERS_METADATA.values())
TOTAL_MODULES = len(ROUTERS_METADATA)
