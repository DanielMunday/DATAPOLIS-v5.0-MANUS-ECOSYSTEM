<?php

/**
 * =========================================================================
 * PAE M11-DP - CONFIGURACIÓN
 * Precession Analytics Engine - Arquitectura Nativa PHP/Laravel
 * =========================================================================
 *
 * Configuración del módulo PAE con engines nativos.
 * NO contiene pae_api_url ni pae_api_key (eliminados).
 *
 * @package Config
 * @version 2.0.0
 * @author DATAPOLIS SpA
 */

return [

    /*
    |--------------------------------------------------------------------------
    | Configuración del Graph Engine
    |--------------------------------------------------------------------------
    |
    | Parámetros para el motor de grafo precesional nativo.
    |
    */
    'graph' => [
        // Profundidad máxima de exploración BFS
        'max_depth' => env('PAE_GRAPH_MAX_DEPTH', 4),

        // Horizonte temporal por defecto (meses)
        'default_time_horizon' => env('PAE_GRAPH_TIME_HORIZON', 60),

        // Factor de decay por nivel de profundidad
        'decay_factor' => env('PAE_GRAPH_DECAY_FACTOR', 0.85),

        // Umbral mínimo de peso para considerar efecto
        'min_weight_threshold' => 0.01,

        // Umbral mínimo de confianza
        'min_confidence_threshold' => 0.1,
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración del Scoring Engine
    |--------------------------------------------------------------------------
    |
    | Pesos y parámetros para cálculo de scores.
    |
    */
    'scoring' => [
        // Pesos para Investment Score compuesto
        'weights' => [
            'precession' => (float) env('PAE_WEIGHT_PRECESSION', 0.40),
            'financial' => (float) env('PAE_WEIGHT_FINANCIAL', 0.30),
            'compliance' => (float) env('PAE_WEIGHT_COMPLIANCE', 0.20),
            'location' => (float) env('PAE_WEIGHT_LOCATION', 0.10),
        ],

        // Pesos por ángulo precesional (Teoría Fuller)
        'angle_weights' => [
            'direct_0' => 1.0,      // Efecto directo
            'induced_45' => 1.2,    // Efectos inducidos
            'precession_90' => 1.5, // Core Fuller - máximo valor
            'systemic_135' => 1.3,  // Efectos sistémicos
            'counter_180' => 0.8,   // Retroalimentación
        ],

        // Normalización
        'normalization' => [
            'sigmoid_center' => 50,
            'sigmoid_steepness' => 20,
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración del ML Connector
    |--------------------------------------------------------------------------
    |
    | Parámetros para conexión con Ollama y fallback estadístico.
    |
    */
    'ml' => [
        // URL de Ollama local
        'ollama_url' => env('OLLAMA_URL', 'http://localhost:11434'),

        // Modelo para análisis
        'ollama_model_analysis' => env('OLLAMA_MODEL_ANALYSIS', 'qwen2.5:7b'),

        // Modelo para narrativas
        'ollama_model_narrative' => env('OLLAMA_MODEL_NARRATIVE', 'llama3.2:8b'),

        // Habilitar fallback cuando Ollama no está disponible
        'fallback_enabled' => env('PAE_ML_FALLBACK_ENABLED', true),

        // Timeout para requests a Ollama (segundos)
        'timeout' => env('PAE_ML_TIMEOUT', 30),

        // Cache de health check (segundos)
        'health_check_ttl' => 60,

        // Parámetros de generación
        'generation' => [
            'temperature' => 0.7,
            'top_p' => 0.9,
            'max_tokens' => 500,
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración del Alert Engine
    |--------------------------------------------------------------------------
    |
    | Umbrales y parámetros para generación de alertas.
    |
    */
    'alerts' => [
        // Umbrales de severidad por risk_score
        'critical_threshold' => (float) env('PAE_ALERT_CRITICAL', 0.8),
        'high_threshold' => (float) env('PAE_ALERT_HIGH', 0.6),
        'warning_threshold' => (float) env('PAE_ALERT_WARNING', 0.5),

        // Umbral de cambio porcentual para alertas
        'change_threshold_percent' => (float) env('PAE_ALERT_CHANGE_PCT', 20),

        // Confianza mínima para efecto negativo crítico
        'negative_effect_confidence_critical' => 0.85,

        // Umbral para detectar oportunidades
        'opportunity_threshold' => 0.7,

        // Tiempo de expiración de alertas (días)
        'expiration_days' => 90,

        // Prevenir duplicados en ventana de tiempo (horas)
        'duplicate_window_hours' => 24,
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración de Sincronización con ÁGORA
    |--------------------------------------------------------------------------
    |
    | Parámetros para sincronización bidireccional con ÁGORA v4.0.
    |
    */
    'sync' => [
        // Habilitar sincronización
        'enabled' => env('PAE_SYNC_ENABLED', true),

        // Driver del Event Bus (redis, database, queue)
        'event_bus_driver' => env('PAE_EVENT_BUS', 'redis'),

        // URL de API de ÁGORA (opcional, para HTTP directo)
        'agora_api_url' => env('AGORA_API_URL'),

        // Cron para sincronización de ontología (2am diario)
        'ontology_sync_cron' => '0 2 * * *',

        // Cargar ontología cacheada al iniciar
        'load_cached_ontology' => env('PAE_LOAD_CACHED_ONTOLOGY', false),

        // Umbrales para alertas cross-platform
        'cross_alert_thresholds' => [
            'cluster_morosidad' => 20,      // % de morosidad en cluster
            'cambio_valorizacion' => 15,    // % cambio en valorización
            'ola_regularizaciones' => 5,    // cantidad de regularizaciones
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración de Cache
    |--------------------------------------------------------------------------
    |
    | TTL y parámetros de caché para análisis.
    |
    */
    'cache' => [
        // TTL para análisis (segundos)
        'analysis_ttl' => env('PAE_CACHE_ANALYSIS_TTL', 3600),

        // TTL para scoring (segundos)
        'scoring_ttl' => env('PAE_CACHE_SCORING_TTL', 86400),

        // TTL para dashboard (segundos)
        'dashboard_ttl' => env('PAE_CACHE_DASHBOARD_TTL', 1800),

        // Prefijo de claves
        'prefix' => 'pae:',
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración de Logging
    |--------------------------------------------------------------------------
    |
    | Nivel y canal de logging para PAE.
    |
    */
    'logging' => [
        // Canal de logs
        'channel' => env('PAE_LOG_CHANNEL', 'daily'),

        // Nivel mínimo de log
        'level' => env('PAE_LOG_LEVEL', 'debug'),

        // Log de análisis completados
        'log_analyses' => env('PAE_LOG_ANALYSES', true),

        // Log de alertas generadas
        'log_alerts' => env('PAE_LOG_ALERTS', true),
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración de Reportes
    |--------------------------------------------------------------------------
    |
    | Parámetros para generación de reportes de inversor.
    |
    */
    'reports' => [
        // Formato por defecto (json, pdf)
        'default_format' => 'json',

        // Incluir secciones
        'sections' => [
            'executive_summary' => true,
            'property_info' => true,
            'precession_analysis' => true,
            'ml_predictions' => true,
            'metrics_integration' => true,
            'recommendations' => true,
            'disclaimer' => true,
        ],

        // Branding
        'branding' => [
            'company_name' => 'DATAPOLIS SpA',
            'product_name' => 'Precession Analytics Engine',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Configuración de Ontología
    |--------------------------------------------------------------------------
    |
    | Nodos y aristas base del grafo precesional.
    | Se cargan automáticamente al iniciar el GraphEngine.
    |
    */
    'ontology' => [
        // Fuentes de datos reconocidas
        'sources' => [
            'DOM' => 'Dirección de Obras Municipales',
            'SII' => 'Servicio de Impuestos Internos',
            'INE' => 'Instituto Nacional de Estadísticas',
            'MINVU' => 'Ministerio de Vivienda y Urbanismo',
            'DATAPOLIS' => 'DATAPOLIS SpA (interno)',
        ],

        // Tipos de nodos
        'node_types' => [
            'urban_metric',
            'valuation',
            'demographic',
            'financial',
            'compliance',
            'building',
            'occupancy',
            'rental',
            'tax',
        ],

        // Versión de la ontología
        'version' => '1.0.0',
    ],

];
