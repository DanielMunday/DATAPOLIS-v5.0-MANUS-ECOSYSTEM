"""
DATAPOLIS v3.0 - Configuración Central
PropTech/FinTech/RegTech Platform for Chilean Real Estate Market
Author: DATAPOLIS SpA
Version: 3.0.0
License: Proprietary
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Configuración centralizada de DATAPOLIS v3.0"""
    
    # =====================================================
    # APLICACIÓN
    # =====================================================
    APP_NAME: str = "DATAPOLIS"
    APP_VERSION: str = "3.0.0"
    APP_DESCRIPTION: str = "Plataforma PropTech/FinTech/RegTech para el mercado inmobiliario chileno"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # =====================================================
    # API
    # =====================================================
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://datapolis.cl", "https://app.datapolis.cl"]
    
    # =====================================================
    # BASE DE DATOS POSTGRESQL/POSTGIS
    # =====================================================
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: str = Field(default="datapolis_v3", env="DB_NAME")
    DB_USER: str = Field(default="datapolis", env="DB_USER")
    DB_PASSWORD: str = Field(default="", env="DB_PASSWORD")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # =====================================================
    # TIMESCALEDB (Series Temporales)
    # =====================================================
    TIMESCALE_ENABLED: bool = Field(default=True, env="TIMESCALE_ENABLED")
    TIMESCALE_RETENTION_DAYS: int = Field(default=3650, env="TIMESCALE_RETENTION_DAYS")  # 10 años
    
    # =====================================================
    # REDIS (Cache + Sessions)
    # =====================================================
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hora
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # =====================================================
    # AUTENTICACIÓN JWT
    # =====================================================
    JWT_SECRET_KEY: str = Field(default="CHANGE-THIS-SECRET-KEY-IN-PRODUCTION", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # =====================================================
    # OAUTH 2.0 (Google, Microsoft)
    # =====================================================
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_SECRET")
    
    # =====================================================
    # INTEGRACIONES CHILENAS - FUENTES OFICIALES
    # =====================================================
    
    # Banco Central de Chile
    BCCH_API_URL: str = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    BCCH_API_USER: Optional[str] = Field(default=None, env="BCCH_API_USER")
    BCCH_API_PASSWORD: Optional[str] = Field(default=None, env="BCCH_API_PASSWORD")
    
    # Servicio de Impuestos Internos
    SII_API_URL: str = "https://api.sii.cl"
    SII_RUT_EMPRESA: Optional[str] = Field(default=None, env="SII_RUT_EMPRESA")
    SII_CLAVE_TRIBUTARIA: Optional[str] = Field(default=None, env="SII_CLAVE_TRIBUTARIA")
    
    # Comisión para el Mercado Financiero
    CMF_API_URL: str = "https://www.cmfchile.cl/api"
    
    # Conservador de Bienes Raíces (vía web scraping autorizado)
    CBR_SCRAPING_ENABLED: bool = Field(default=False, env="CBR_SCRAPING_ENABLED")
    
    # SHOA - Servicio Hidrográfico y Oceanográfico
    SHOA_API_URL: str = "http://www.shoa.cl/servicios"
    
    # SENAPRED - Gestión del Riesgo de Desastres
    SENAPRED_API_URL: str = "https://www.senapred.cl/api"
    
    # IDE Chile - Infraestructura de Datos Espaciales
    IDE_CHILE_WMS_URL: str = "https://www.ide.cl/geoserver/wms"
    IDE_CHILE_WFS_URL: str = "https://www.ide.cl/geoserver/wfs"
    
    # Ministerio de Vivienda y Urbanismo
    MINVU_API_URL: str = "https://www.minvu.cl/api"
    
    # =====================================================
    # GEOSPATIAL - ESRI ARCGIS
    # =====================================================
    ARCGIS_API_KEY: Optional[str] = Field(default=None, env="ARCGIS_API_KEY")
    ARCGIS_CLIENT_ID: Optional[str] = Field(default=None, env="ARCGIS_CLIENT_ID")
    ARCGIS_CLIENT_SECRET: Optional[str] = Field(default=None, env="ARCGIS_CLIENT_SECRET")
    ARCGIS_PORTAL_URL: str = Field(default="https://www.arcgis.com", env="ARCGIS_PORTAL_URL")
    
    # =====================================================
    # LLM - INTELIGENCIA ARTIFICIAL
    # =====================================================
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field(default="claude-sonnet-4-20250514", env="CLAUDE_MODEL")
    CLAUDE_MAX_TOKENS: int = Field(default=4096, env="CLAUDE_MAX_TOKENS")
    
    # OpenAI (Fallback)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo", env="OPENAI_MODEL")
    
    # Local LLM (Ollama/Llama)
    LOCAL_LLM_ENABLED: bool = Field(default=False, env="LOCAL_LLM_ENABLED")
    LOCAL_LLM_URL: str = Field(default="http://localhost:11434", env="LOCAL_LLM_URL")
    LOCAL_LLM_MODEL: str = Field(default="llama3:70b", env="LOCAL_LLM_MODEL")
    
    # =====================================================
    # MACHINE LEARNING
    # =====================================================
    ML_MODELS_PATH: str = Field(default="/app/ml_models", env="ML_MODELS_PATH")
    ML_TRAINING_DATA_PATH: str = Field(default="/app/training_data", env="ML_TRAINING_DATA_PATH")
    
    # Configuración XGBoost
    XGBOOST_N_ESTIMATORS: int = 100
    XGBOOST_MAX_DEPTH: int = 6
    XGBOOST_LEARNING_RATE: float = 0.1
    
    # Configuración ARIMA
    ARIMA_ORDER: tuple = (5, 1, 0)
    ARIMA_SEASONAL_ORDER: tuple = (1, 1, 1, 12)
    
    # =====================================================
    # BLOCKCHAIN - HYPERLEDGER FABRIC
    # =====================================================
    BLOCKCHAIN_ENABLED: bool = Field(default=False, env="BLOCKCHAIN_ENABLED")
    HYPERLEDGER_PEER_URL: str = Field(default="grpc://localhost:7051", env="HYPERLEDGER_PEER_URL")
    HYPERLEDGER_ORDERER_URL: str = Field(default="grpc://localhost:7050", env="HYPERLEDGER_ORDERER_URL")
    HYPERLEDGER_CHANNEL: str = Field(default="datapolis-channel", env="HYPERLEDGER_CHANNEL")
    
    # =====================================================
    # ALMACENAMIENTO
    # =====================================================
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")  # local, s3, gcs
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    AWS_REGION: str = Field(default="sa-east-1", env="AWS_REGION")  # São Paulo (closest to Chile)
    
    # Local Storage
    LOCAL_STORAGE_PATH: str = Field(default="/app/storage", env="LOCAL_STORAGE_PATH")
    
    # =====================================================
    # EMAIL (Notificaciones)
    # =====================================================
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field(default="noreply@datapolis.cl", env="EMAIL_FROM")
    
    # =====================================================
    # COMPLIANCE Y REGULATORIO
    # =====================================================
    
    # Ley 21.442 - Copropiedad Inmobiliaria
    LEY_21442_ENABLED: bool = True
    LEY_21442_VIGENCIA: str = "2022-04-01"
    
    # Ley 21.713 - Cumplimiento Tributario
    LEY_21713_ENABLED: bool = True
    LEY_21713_VIGENCIA: str = "2024-10-24"
    
    # Ley 21.719 - Protección de Datos
    LEY_21719_ENABLED: bool = True
    LEY_21719_VIGENCIA: str = "2024-12-01"
    
    # NCG CMF (Normas de Carácter General)
    CMF_NCG_AUTO_UPDATE: bool = Field(default=True, env="CMF_NCG_AUTO_UPDATE")
    
    # =====================================================
    # INDICADORES ECONÓMICOS - DEFAULTS
    # =====================================================
    DEFAULT_UF_VALUE: float = 38500.0  # Valor referencial
    DEFAULT_UTM_VALUE: float = 67000.0  # Valor referencial
    DEFAULT_IPC_ANUAL: float = 0.04  # 4% inflación
    DEFAULT_TASA_POLITICA_MONETARIA: float = 0.0475  # 4.75%
    
    # =====================================================
    # LÍMITES Y RATE LIMITING
    # =====================================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    MAX_EXPEDIENTE_DOCUMENTS: int = Field(default=1000, env="MAX_EXPEDIENTE_DOCUMENTS")
    
    # =====================================================
    # LOGGING
    # =====================================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_PATH: str = Field(default="/app/logs/datapolis.log", env="LOG_FILE_PATH")
    
    # =====================================================
    # MONITORING
    # =====================================================
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración cacheada (singleton)"""
    return Settings()


# Instancia global de settings
settings = get_settings()


# =====================================================
# CONSTANTES CHILENAS
# =====================================================

# Regiones de Chile (código - nombre)
REGIONES_CHILE = {
    "XV": "Arica y Parinacota",
    "I": "Tarapacá",
    "II": "Antofagasta",
    "III": "Atacama",
    "IV": "Coquimbo",
    "V": "Valparaíso",
    "RM": "Metropolitana de Santiago",
    "VI": "O'Higgins",
    "VII": "Maule",
    "VIII": "Biobío",
    "IX": "La Araucanía",
    "XIV": "Los Ríos",
    "X": "Los Lagos",
    "XI": "Aysén",
    "XII": "Magallanes",
    "XVI": "Ñuble"
}

# Tipos de propiedad según SII
TIPOS_PROPIEDAD_SII = {
    "A": "Agrícola",
    "B": "No Agrícola - Habitacional",
    "C": "No Agrícola - Comercial",
    "D": "No Agrícola - Industrial",
    "E": "No Agrícola - Otros",
    "F": "Sitio Eriazo",
    "G": "Bien Común"
}

# Series Banco Central
SERIES_BCCH = {
    "UF": "F073.UFF.PRE.Z.D",
    "UTM": "F073.UTM.PRE.Z.M",
    "IPC": "F074.IPC.VAR.Z.Z.C.M",
    "DOLAR_OBSERVADO": "F073.TCO.PRE.Z.D",
    "TASA_POLITICA_MONETARIA": "F022.TPM.TIN.D.Z.EP",
    "IMACEC": "F032.IMC.IND.N.7.C.M"
}

# Tasas de impuestos
TASAS_IMPUESTOS_CHILE = {
    "CONTRIBUCIONES_TASA_BASE": 0.0098,  # 0.98%
    "IVA": 0.19,  # 19%
    "IMPUESTO_GANANCIAS_CAPITAL_HABITUAL": 0.0,  # Exento habitacional habitual
    "IMPUESTO_GANANCIAS_CAPITAL_NO_HABITUAL": 0.10,  # 10% hasta 8000 UF
    "IMPUESTO_GANANCIAS_CAPITAL_EXCESO": 0.20,  # Tasa marginal sobre 8000 UF
    "SOBRETASA_CONTRIBUCIONES": {
        "673_UTA_851_UTA": 0.0005,
        "851_UTA_1071_UTA": 0.0010,
        "1071_UTA_MAS": 0.0015
    }
}

# Zonas de riesgo sísmico
ZONAS_SISMICAS_CHILE = {
    1: "Zona sísmica 1 (menor riesgo)",
    2: "Zona sísmica 2",
    3: "Zona sísmica 3 (mayor riesgo)"
}

# Normativa urbanística - Usos de suelo PRMS
USOS_SUELO_PRMS = [
    "ZH - Zona Habitacional",
    "ZHM - Zona Habitacional Mixta",
    "ZC - Zona Comercial",
    "ZI - Zona Industrial",
    "ZEU - Zona de Extensión Urbana",
    "ZODUC - Zona de Desarrollo Urbano Condicionado",
    "AUDP - Área de Desarrollo Prioritario",
    "ZUDC - Zona Urbana de Desarrollo Condicionado",
    "AV - Área Verde",
    "ZP - Zona de Protección"
]
