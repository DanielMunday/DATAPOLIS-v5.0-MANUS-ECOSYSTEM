"""
DATAPOLIS v3.0 - Aplicación Principal FastAPI
PropTech/FinTech/RegTech Platform for Chilean Real Estate Market
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Callable
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import settings
from .database import init_db, engine

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# =====================================================
# MÉTRICAS PROMETHEUS
# =====================================================

REQUEST_COUNT = Counter(
    'datapolis_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'datapolis_request_latency_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)


# =====================================================
# LIFECYCLE
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    # Startup
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Inicializar base de datos
    await init_db()
    logger.info("✅ Base de datos inicializada")
    
    # Inicializar Redis
    app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("✅ Redis conectado")
    
    # Cargar modelos ML
    # await load_ml_models()
    logger.info("✅ Modelos ML cargados")
    
    yield
    
    # Shutdown
    logger.info("🛑 Cerrando aplicación...")
    
    # Cerrar conexiones
    await app.state.redis.close()
    await engine.dispose()
    
    logger.info("👋 Aplicación cerrada correctamente")


# =====================================================
# APLICACIÓN FASTAPI
# =====================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)


# =====================================================
# MIDDLEWARE
# =====================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compresión GZip
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def logging_middleware(request: Request, call_next: Callable):
    """Middleware de logging y métricas"""
    start_time = time.time()
    
    # Procesar request
    response = await call_next(request)
    
    # Calcular duración
    duration = time.time() - start_time
    
    # Log
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Duration: {duration:.3f}s"
    )
    
    # Métricas Prometheus
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Header de tiempo de respuesta
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable):
    """Rate limiting por IP"""
    if not hasattr(app.state, 'redis'):
        return await call_next(request)
    
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}:{int(time.time() // 60)}"
    
    try:
        current = await app.state.redis.incr(key)
        if current == 1:
            await app.state.redis.expire(key, 60)
        
        if current > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."}
            )
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
    
    return await call_next(request)


# =====================================================
# EXCEPTION HANDLERS
# =====================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # En producción, no revelar detalles
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "status_code": 500
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": str(exc),
            "status_code": 500,
            "type": type(exc).__name__
        }
    )


# =====================================================
# ENDPOINTS RAÍZ
# =====================================================

@app.get("/")
async def root():
    """Health check y información básica"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.APP_ENV
    }


@app.get("/health")
async def health_check():
    """Health check detallado"""
    health = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "components": {}
    }
    
    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # Check Redis
    try:
        await app.state.redis.ping()
        health["components"]["redis"] = "healthy"
    except Exception as e:
        health["components"]["redis"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    return health


@app.get("/metrics")
async def metrics():
    """Endpoint de métricas Prometheus"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# =====================================================
# IMPORTAR Y REGISTRAR ROUTERS
# =====================================================

# Importar router principal (agrupa todos los módulos)
from app.routers import api_router

# Registrar router principal con todos los endpoints
app.include_router(api_router)

# Routers adicionales pendientes de implementación:
# - auth: Autenticación JWT/OAuth
# - users: Gestión de usuarios
# - ms_mercado_suelo: Análisis mercado suelo
# - m00_expediente: Expediente universal
# - m01_propiedad: Ficha propiedad
# - m02_copropiedad: Gestión condominios
# - m05_arriendos: Cartera arriendos
# - m17_gires: Gestión riesgos (Esri)
# - m22_agora: NLU geoespacial


# =====================================================
# DOCUMENTACIÓN DE API
# =====================================================

# Información adicional para OpenAPI
tags_metadata = [
    {
        "name": "Autenticación",
        "description": "Endpoints de autenticación JWT y OAuth 2.0"
    },
    {
        "name": "Usuarios",
        "description": "Gestión de usuarios y perfiles"
    },
    {
        "name": "IE - Indicadores Económicos",
        "description": "Indicadores BCCh (UF, UTM, IPC, Dólar) con predicciones ARIMA"
    },
    {
        "name": "MS - Mercado Suelo",
        "description": "Análisis de mercado de suelo con ML hedonic pricing"
    },
    {
        "name": "M00 - Expediente Universal",
        "description": "Expediente digital único por propiedad"
    },
    {
        "name": "M01 - Ficha Propiedad",
        "description": "Ficha maestra de propiedades inmobiliarias"
    },
    {
        "name": "M02 - Copropiedad",
        "description": "Gestión de condominios según Ley 21.442"
    },
    {
        "name": "M03 - Credit Score",
        "description": "Score crediticio inmobiliario con explicabilidad SHAP"
    },
    {
        "name": "M04 - Valorización",
        "description": "Valorización IVS 2022 (Comparación, Costo, DCF)"
    },
    {
        "name": "M05 - Arriendos",
        "description": "Gestión de cartera de arriendos"
    },
    {
        "name": "M12 - Due Diligence",
        "description": "Due Diligence automatizado (150+ checks)"
    },
    {
        "name": "M17 - GIRES",
        "description": "Gestión Integral de Riesgos (sísmico, tsunami, inundación)"
    },
    {
        "name": "M22 - ÁGORA GeoViewer",
        "description": "Consultas geoespaciales con NLU y ArcGIS"
    }
]

app.openapi_tags = tags_metadata


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=4 if not settings.DEBUG else 1
    )
