<?php

declare(strict_types=1);

namespace App\Providers;

use App\Services\PAE\PrecessionGraphEngine;
use App\Services\PAE\PrecessionScoringEngine;
use App\Services\PAE\PrecessionMLConnector;
use App\Services\PAE\PrecessionAlertEngine;
use App\Services\PAE\PrecessionSyncService;
use App\Services\PrecessionService;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Event;
use Illuminate\Support\Facades\Log;

/**
 * =========================================================================
 * PAE M11-DP - SERVICE PROVIDER
 * Registro y Configuración de Engines Nativos PHP/Laravel
 * =========================================================================
 *
 * Este provider registra todos los componentes del Precession Analytics
 * Engine como singletons, asegurando una única instancia durante el
 * ciclo de vida de la aplicación.
 *
 * ENGINES REGISTRADOS:
 * - PrecessionGraphEngine: Motor de grafo precesional
 * - PrecessionScoringEngine: Motor de scoring
 * - PrecessionMLConnector: Conector ML con fallback
 * - PrecessionAlertEngine: Motor de alertas
 * - PrecessionSyncService: Sincronización con ÁGORA
 * - PrecessionService: Orquestador principal
 *
 * @package App\Providers
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PAEServiceProvider extends ServiceProvider
{
    /**
     * Indica si el provider debe ser diferido
     *
     * @var bool
     */
    protected $defer = false;

    /**
     * Registrar servicios en el contenedor
     *
     * @return void
     */
    public function register(): void
    {
        // Merge configuración
        $this->mergeConfigFrom(
            __DIR__ . '/../../config/pae.php',
            'datapolis.pae'
        );

        // =====================================================================
        // REGISTRO DE ENGINES COMO SINGLETONS
        // =====================================================================

        // Graph Engine - Motor de grafo precesional
        $this->app->singleton(PrecessionGraphEngine::class, function ($app) {
            return new PrecessionGraphEngine();
        });

        // Scoring Engine - Motor de scoring
        $this->app->singleton(PrecessionScoringEngine::class, function ($app) {
            return new PrecessionScoringEngine();
        });

        // ML Connector - Conector ML con fallback
        $this->app->singleton(PrecessionMLConnector::class, function ($app) {
            return new PrecessionMLConnector();
        });

        // Alert Engine - Motor de alertas
        $this->app->singleton(PrecessionAlertEngine::class, function ($app) {
            return new PrecessionAlertEngine();
        });

        // Sync Service - Sincronización con ÁGORA
        $this->app->singleton(PrecessionSyncService::class, function ($app) {
            return new PrecessionSyncService(
                $app->make(PrecessionGraphEngine::class),
                $app->make(PrecessionAlertEngine::class)
            );
        });

        // Precession Service - Orquestador principal
        $this->app->singleton(PrecessionService::class, function ($app) {
            return new PrecessionService(
                $app->make(PrecessionGraphEngine::class),
                $app->make(PrecessionScoringEngine::class),
                $app->make(PrecessionMLConnector::class),
                $app->make(PrecessionAlertEngine::class),
                $app->make(PrecessionSyncService::class)
            );
        });

        // =====================================================================
        // ALIASES
        // =====================================================================

        $this->app->alias(PrecessionService::class, 'pae');
        $this->app->alias(PrecessionGraphEngine::class, 'pae.graph');
        $this->app->alias(PrecessionScoringEngine::class, 'pae.scoring');
        $this->app->alias(PrecessionMLConnector::class, 'pae.ml');
        $this->app->alias(PrecessionAlertEngine::class, 'pae.alerts');
        $this->app->alias(PrecessionSyncService::class, 'pae.sync');
    }

    /**
     * Bootstrap de servicios
     *
     * @return void
     */
    public function boot(): void
    {
        // Publicar configuración
        $this->publishes([
            __DIR__ . '/../../config/pae.php' => config_path('pae.php'),
        ], 'pae-config');

        // Publicar migraciones
        $this->publishes([
            __DIR__ . '/../../database/migrations/pae' => database_path('migrations'),
        ], 'pae-migrations');

        // =====================================================================
        // INICIALIZAR ONTOLOGÍA BASE
        // =====================================================================
        $this->initializeOntology();

        // =====================================================================
        // REGISTRAR EVENT LISTENERS PARA SINCRONIZACIÓN
        // =====================================================================
        $this->registerEventListeners();

        // =====================================================================
        // REGISTRAR COMANDOS ARTISAN
        // =====================================================================
        if ($this->app->runningInConsole()) {
            $this->commands([
                \App\Console\Commands\PAE\PAEAnalyzeCommand::class,
                \App\Console\Commands\PAE\PAESyncCommand::class,
                \App\Console\Commands\PAE\PAEAlertsCommand::class,
            ]);
        }

        Log::debug('PAEServiceProvider: Booted successfully');
    }

    /**
     * Inicializar ontología base del Graph Engine
     *
     * @return void
     */
    protected function initializeOntology(): void
    {
        // La ontología se inicializa en el constructor del GraphEngine
        // Aquí podemos cargar ontologías adicionales si existen

        try {
            if (config('datapolis.pae.sync.load_cached_ontology', false)) {
                $cachedOntology = \Cache::get('pae:ontology:cached');
                if ($cachedOntology) {
                    $graphEngine = $this->app->make(PrecessionGraphEngine::class);
                    $graphEngine->importOntology($cachedOntology, true);
                    Log::debug('PAEServiceProvider: Ontología cacheada cargada');
                }
            }
        } catch (\Exception $e) {
            Log::warning('PAEServiceProvider: Error cargando ontología cacheada', [
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Registrar event listeners para sincronización
     *
     * @return void
     */
    protected function registerEventListeners(): void
    {
        // Listener para recibir ontología de ÁGORA
        Event::listen('pae.agora.ontology.updated', function ($payload) {
            try {
                $syncService = $this->app->make(PrecessionSyncService::class);
                $syncService->receiveOntologyFromAgora($payload);
            } catch (\Exception $e) {
                Log::error('PAEServiceProvider: Error procesando ontología de ÁGORA', [
                    'error' => $e->getMessage(),
                ]);
            }
        });

        // Listener para recibir alertas cross-platform de ÁGORA
        Event::listen('pae.agora.alert.cross_platform', function ($payload) {
            try {
                $syncService = $this->app->make(PrecessionSyncService::class);
                $syncService->receiveCrossAlert($payload);
            } catch (\Exception $e) {
                Log::error('PAEServiceProvider: Error procesando alerta de ÁGORA', [
                    'error' => $e->getMessage(),
                ]);
            }
        });

        // Listener para feedback de predicciones
        Event::listen('pae.feedback.prediction_result', function ($payload) {
            try {
                // Almacenar feedback para análisis
                \Cache::put(
                    "pae:feedback:{$payload['prediction']['id']}",
                    $payload,
                    now()->addDays(90)
                );
            } catch (\Exception $e) {
                Log::warning('PAEServiceProvider: Error almacenando feedback', [
                    'error' => $e->getMessage(),
                ]);
            }
        });

        // Listener para análisis completado
        Event::listen(\App\Events\PAE\PrecessionAnalysisCompleted::class, function ($event) {
            try {
                // Evaluar si publicar alerta cross-platform
                $syncService = $this->app->make(PrecessionSyncService::class);
                
                foreach ($event->alerts as $alertData) {
                    if (isset($alertData['id'])) {
                        $alert = \App\Models\PAE\PrecessionAlert::find($alertData['id']);
                        if ($alert) {
                            $syncService->publishCrossAlert($alert);
                        }
                    }
                }
            } catch (\Exception $e) {
                Log::warning('PAEServiceProvider: Error en post-análisis', [
                    'error' => $e->getMessage(),
                ]);
            }
        });
    }

    /**
     * Obtener servicios provistos
     *
     * @return array
     */
    public function provides(): array
    {
        return [
            PrecessionGraphEngine::class,
            PrecessionScoringEngine::class,
            PrecessionMLConnector::class,
            PrecessionAlertEngine::class,
            PrecessionSyncService::class,
            PrecessionService::class,
            'pae',
            'pae.graph',
            'pae.scoring',
            'pae.ml',
            'pae.alerts',
            'pae.sync',
        ];
    }
}
