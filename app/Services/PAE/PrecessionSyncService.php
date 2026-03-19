<?php

declare(strict_types=1);

namespace App\Services\PAE;

use App\Events\PAE\IntegrationEvents;
use App\Models\PAE\PrecessionAlert;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Event;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Queue;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION SYNC SERVICE
 * Servicio de Sincronización con ÁGORA v4.0
 * =========================================================================
 *
 * Gestiona la sincronización bidireccional entre DATAPOLIS PAE y ÁGORA:
 * - Intercambio de ontología (grafos de relaciones precesionales)
 * - Alertas cross-platform (afectación territorial)
 * - Feedback loop para calibración de modelos
 *
 * EVENTOS:
 * - pae.ontology.updated: Publicar ontología actualizada
 * - pae.agora.ontology.updated: Recibir ontología de ÁGORA
 * - pae.datapolis.alert.cross_platform: Publicar alerta cross-platform
 * - pae.agora.alert.cross_platform: Recibir alerta de ÁGORA
 * - pae.feedback.prediction_result: Reportar accuracy de predicciones
 *
 * @package App\Services\PAE
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionSyncService
{
    /**
     * Eventos de sincronización
     */
    public const EVENT_ONTOLOGY_UPDATED = 'pae.ontology.updated';
    public const EVENT_AGORA_ONTOLOGY = 'pae.agora.ontology.updated';
    public const EVENT_CROSS_ALERT_OUT = 'pae.datapolis.alert.cross_platform';
    public const EVENT_CROSS_ALERT_IN = 'pae.agora.alert.cross_platform';
    public const EVENT_FEEDBACK = 'pae.feedback.prediction_result';

    /**
     * Umbrales para alertas cross-platform
     */
    protected const CROSS_ALERT_THRESHOLDS = [
        'cluster_morosidad' => 20,          // % de morosidad en cluster
        'cambio_valorizacion' => 15,        // % cambio en valorización
        'ola_regularizaciones' => 5,        // cantidad de regularizaciones
        'cambio_uso_suelo' => true,         // cualquier cambio
        'nueva_infraestructura' => true,    // cualquier infraestructura
    ];

    /**
     * Configuración
     * @var array
     */
    protected array $config;

    /**
     * Graph Engine
     * @var PrecessionGraphEngine
     */
    protected PrecessionGraphEngine $graphEngine;

    /**
     * Alert Engine
     * @var PrecessionAlertEngine
     */
    protected PrecessionAlertEngine $alertEngine;

    /**
     * Constructor
     *
     * @param PrecessionGraphEngine $graphEngine
     * @param PrecessionAlertEngine $alertEngine
     */
    public function __construct(
        PrecessionGraphEngine $graphEngine,
        PrecessionAlertEngine $alertEngine
    ) {
        $this->graphEngine = $graphEngine;
        $this->alertEngine = $alertEngine;

        $this->config = config('datapolis.pae.sync', [
            'enabled' => env('PAE_SYNC_ENABLED', true),
            'ontology_sync_cron' => '0 2 * * *',
            'event_bus_driver' => env('PAE_EVENT_BUS', 'redis'),
            'agora_api_url' => env('AGORA_API_URL'),
        ]);
    }

    // =========================================================================
    // SINCRONIZACIÓN DE ONTOLOGÍA
    // =========================================================================

    /**
     * Sincronizar ontología hacia ÁGORA
     *
     * Publica la ontología actual del PAE al Event Bus para que
     * ÁGORA pueda integrarla en su sistema de inteligencia territorial.
     *
     * @return void
     */
    public function syncOntologyToAgora(): void
    {
        if (!$this->config['enabled']) {
            Log::debug('PrecessionSyncService: Sync deshabilitado');
            return;
        }

        try {
            // Exportar ontología del Graph Engine
            $ontology = $this->graphEngine->exportOntology();

            // Agregar metadatos de sincronización
            $payload = [
                'source' => 'DATAPOLIS_PAE',
                'version' => $ontology['version'],
                'timestamp' => now()->toISOString(),
                'ontology' => $ontology,
                'stats' => $this->graphEngine->getStats(),
                'sync_type' => 'full',
            ];

            // Publicar evento
            $this->publishEvent(self::EVENT_ONTOLOGY_UPDATED, $payload);

            // Actualizar cache de última sincronización
            Cache::put('pae:sync:ontology:last', now()->toISOString(), now()->addDays(7));

            Log::info('PrecessionSyncService: Ontología sincronizada a ÁGORA', [
                'nodes' => $ontology['metadata']['total_nodes'],
                'edges' => $ontology['metadata']['total_edges'],
            ]);

        } catch (\Exception $e) {
            Log::error('PrecessionSyncService: Error sincronizando ontología', [
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Recibir ontología desde ÁGORA
     *
     * Suscribe a eventos de ontología de ÁGORA y realiza merge
     * inteligente con la ontología local.
     *
     * @param array $ontology Ontología recibida
     * @return void
     */
    public function receiveOntologyFromAgora(array $ontology): void
    {
        if (!$this->config['enabled']) {
            return;
        }

        try {
            $source = $ontology['source'] ?? 'AGORA';
            
            // Validar ontología
            if (!$this->validateOntology($ontology)) {
                Log::warning('PrecessionSyncService: Ontología inválida recibida', [
                    'source' => $source,
                ]);
                return;
            }

            // Merge inteligente: mantener nodos locales + incorporar nuevos de ÁGORA
            $this->graphEngine->importOntology($ontology['ontology'] ?? $ontology, true);

            // Registrar recepción
            Cache::put('pae:sync:agora:last', now()->toISOString(), now()->addDays(7));

            Log::info('PrecessionSyncService: Ontología recibida de ÁGORA', [
                'source' => $source,
                'nodes_received' => count($ontology['ontology']['nodes'] ?? []),
            ]);

        } catch (\Exception $e) {
            Log::error('PrecessionSyncService: Error recibiendo ontología', [
                'error' => $e->getMessage(),
            ]);
        }
    }

    // =========================================================================
    // ALERTAS CROSS-PLATFORM
    // =========================================================================

    /**
     * Publicar alerta cross-platform
     *
     * Cuando una alerta de DATAPOLIS afecta zona territorial,
     * se notifica a ÁGORA para análisis a nivel macro.
     *
     * @param PrecessionAlert $alert
     * @return void
     */
    public function publishCrossAlert(PrecessionAlert $alert): void
    {
        if (!$this->config['enabled']) {
            return;
        }

        // Determinar si la alerta amerita notificación cross-platform
        if (!$this->shouldPublishCrossAlert($alert)) {
            return;
        }

        try {
            // Obtener datos de la copropiedad y zona
            $copropiedad = $alert->copropiedad;
            if (!$copropiedad) {
                return;
            }

            $payload = [
                'source' => 'DATAPOLIS_PAE',
                'timestamp' => now()->toISOString(),
                'alert' => [
                    'id' => $alert->id,
                    'type' => $alert->alert_type,
                    'severity' => $alert->severity,
                    'title' => $alert->title,
                    'description' => $alert->description,
                    'precession_angle' => $alert->precession_angle,
                ],
                'location' => [
                    'copropiedad_id' => $copropiedad->id,
                    'comuna' => $copropiedad->comuna,
                    'region' => $copropiedad->region,
                    'latitud' => $copropiedad->latitud,
                    'longitud' => $copropiedad->longitud,
                ],
                'impact' => [
                    'potential_uf' => $alert->potential_impact_uf,
                    'probability' => $alert->probability,
                    'expected_months' => $alert->expected_months,
                ],
                'cross_platform_type' => $this->determineCrossPlatformType($alert),
            ];

            $this->publishEvent(self::EVENT_CROSS_ALERT_OUT, $payload);

            // Marcar alerta como sincronizada
            $alert->update(['synced_to_agora' => true, 'synced_at' => now()]);

            Log::info('PrecessionSyncService: Alerta cross-platform publicada', [
                'alert_id' => $alert->id,
                'type' => $alert->alert_type,
                'comuna' => $copropiedad->comuna,
            ]);

        } catch (\Exception $e) {
            Log::error('PrecessionSyncService: Error publicando alerta cross-platform', [
                'alert_id' => $alert->id,
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Recibir alerta cross-platform desde ÁGORA
     *
     * Cuando ÁGORA detecta un evento territorial relevante,
     * crea alertas locales para las copropiedades afectadas.
     *
     * @param array $alertData Datos de la alerta
     * @return void
     */
    public function receiveCrossAlert(array $alertData): void
    {
        if (!$this->config['enabled']) {
            return;
        }

        try {
            $source = $alertData['source'] ?? 'AGORA';
            $location = $alertData['location'] ?? [];
            $alertInfo = $alertData['alert'] ?? [];

            // Buscar copropiedades en la zona afectada
            $affectedCopropiedades = $this->findAffectedCopropiedades($location);

            if ($affectedCopropiedades->isEmpty()) {
                Log::debug('PrecessionSyncService: Sin copropiedades afectadas', [
                    'location' => $location,
                ]);
                return;
            }

            // Crear alertas locales para cada copropiedad afectada
            foreach ($affectedCopropiedades as $copropiedad) {
                $localAlert = $this->alertEngine->generateAlert(
                    $this->mapAgoraAlertType($alertData['cross_platform_type'] ?? 'generic'),
                    $this->mapAgoraSeverity($alertInfo['severity'] ?? 'info'),
                    [
                        'title' => "[ÁGORA] " . ($alertInfo['title'] ?? 'Alerta Territorial'),
                        'description' => ($alertInfo['description'] ?? 'Evento territorial detectado por ÁGORA.') .
                            " Afecta zona de " . ($location['comuna'] ?? 'la comuna') . ".",
                        'copropiedad_id' => $copropiedad->id,
                        'tenant_id' => $copropiedad->tenant_id,
                        'data' => [
                            'agora_alert_id' => $alertInfo['id'] ?? null,
                            'source' => $source,
                            'original_data' => $alertData,
                        ],
                        'analysis' => [],
                    ]
                );
            }

            Log::info('PrecessionSyncService: Alerta de ÁGORA procesada', [
                'source' => $source,
                'affected_copropiedades' => $affectedCopropiedades->count(),
                'type' => $alertData['cross_platform_type'] ?? 'generic',
            ]);

        } catch (\Exception $e) {
            Log::error('PrecessionSyncService: Error recibiendo alerta de ÁGORA', [
                'error' => $e->getMessage(),
            ]);
        }
    }

    // =========================================================================
    // FEEDBACK LOOP
    // =========================================================================

    /**
     * Sincronizar feedback de predicciones
     *
     * Reporta el accuracy de las predicciones al Event Bus
     * para permitir calibración cruzada de modelos.
     *
     * @param array $predictionResult Resultado de predicción con valores reales
     * @return void
     */
    public function syncFeedback(array $predictionResult): void
    {
        if (!$this->config['enabled']) {
            return;
        }

        try {
            // Calcular métricas de accuracy
            $metrics = $this->calculatePredictionMetrics($predictionResult);

            $payload = [
                'source' => 'DATAPOLIS_PAE',
                'timestamp' => now()->toISOString(),
                'prediction' => [
                    'id' => $predictionResult['prediction_id'] ?? null,
                    'type' => $predictionResult['type'] ?? 'precession',
                    'horizon_months' => $predictionResult['horizon_months'] ?? 12,
                ],
                'accuracy' => $metrics,
                'context' => [
                    'copropiedad_id' => $predictionResult['copropiedad_id'] ?? null,
                    'comuna' => $predictionResult['comuna'] ?? null,
                    'sample_size' => $predictionResult['sample_size'] ?? 1,
                ],
            ];

            $this->publishEvent(self::EVENT_FEEDBACK, $payload);

            // Almacenar para análisis interno
            Cache::put(
                "pae:feedback:{$predictionResult['prediction_id']}",
                $payload,
                now()->addDays(90)
            );

            Log::debug('PrecessionSyncService: Feedback sincronizado', [
                'prediction_id' => $predictionResult['prediction_id'] ?? 'N/A',
                'mae' => $metrics['mae'] ?? 0,
            ]);

        } catch (\Exception $e) {
            Log::error('PrecessionSyncService: Error sincronizando feedback', [
                'error' => $e->getMessage(),
            ]);
        }
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    /**
     * Publicar evento al Event Bus
     *
     * @param string $eventName
     * @param array $payload
     * @return void
     */
    protected function publishEvent(string $eventName, array $payload): void
    {
        $driver = $this->config['event_bus_driver'];

        switch ($driver) {
            case 'redis':
                $this->publishToRedis($eventName, $payload);
                break;

            case 'database':
                $this->publishToDatabase($eventName, $payload);
                break;

            case 'queue':
                $this->publishToQueue($eventName, $payload);
                break;

            default:
                // Local event dispatch
                Event::dispatch($eventName, $payload);
        }
    }

    /**
     * Publicar a Redis
     *
     * @param string $eventName
     * @param array $payload
     * @return void
     */
    protected function publishToRedis(string $eventName, array $payload): void
    {
        try {
            $redis = app('redis');
            $redis->publish($eventName, json_encode($payload));
        } catch (\Exception $e) {
            Log::warning('PrecessionSyncService: Error publicando a Redis', [
                'event' => $eventName,
                'error' => $e->getMessage(),
            ]);
            // Fallback to local event
            Event::dispatch($eventName, $payload);
        }
    }

    /**
     * Publicar a base de datos
     *
     * @param string $eventName
     * @param array $payload
     * @return void
     */
    protected function publishToDatabase(string $eventName, array $payload): void
    {
        try {
            \DB::table('pae_event_bus')->insert([
                'event_name' => $eventName,
                'payload' => json_encode($payload),
                'status' => 'pending',
                'created_at' => now(),
            ]);
        } catch (\Exception $e) {
            Log::warning('PrecessionSyncService: Error publicando a DB', [
                'event' => $eventName,
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Publicar a cola
     *
     * @param string $eventName
     * @param array $payload
     * @return void
     */
    protected function publishToQueue(string $eventName, array $payload): void
    {
        Queue::push(function () use ($eventName, $payload) {
            Event::dispatch($eventName, $payload);
        });
    }

    /**
     * Validar ontología recibida
     *
     * @param array $ontology
     * @return bool
     */
    protected function validateOntology(array $ontology): bool
    {
        // Validación básica de estructura
        $data = $ontology['ontology'] ?? $ontology;
        
        if (!isset($data['nodes']) || !is_array($data['nodes'])) {
            return false;
        }

        if (!isset($data['edges']) || !is_array($data['edges'])) {
            return false;
        }

        return true;
    }

    /**
     * Determinar si publicar alerta cross-platform
     *
     * @param PrecessionAlert $alert
     * @return bool
     */
    protected function shouldPublishCrossAlert(PrecessionAlert $alert): bool
    {
        // Solo alertas críticas o de alto impacto
        if (!in_array($alert->severity, ['critical', 'high'])) {
            return false;
        }

        // Casos específicos
        $data = $alert->data ?? [];

        // Cluster de morosidad alta
        if (($data['morosidad_cluster'] ?? 0) >= self::CROSS_ALERT_THRESHOLDS['cluster_morosidad']) {
            return true;
        }

        // Cambio significativo en valorización
        if (abs($data['cambio_valorizacion'] ?? 0) >= self::CROSS_ALERT_THRESHOLDS['cambio_valorizacion']) {
            return true;
        }

        // Ola de regularizaciones compliance
        if (($data['regularizaciones_count'] ?? 0) >= self::CROSS_ALERT_THRESHOLDS['ola_regularizaciones']) {
            return true;
        }

        // Alertas de tipo regulatorio siempre se publican
        if ($alert->alert_type === 'regulatory_impact') {
            return true;
        }

        return false;
    }

    /**
     * Determinar tipo de alerta cross-platform
     *
     * @param PrecessionAlert $alert
     * @return string
     */
    protected function determineCrossPlatformType(PrecessionAlert $alert): string
    {
        $data = $alert->data ?? [];

        if (($data['morosidad_cluster'] ?? 0) >= self::CROSS_ALERT_THRESHOLDS['cluster_morosidad']) {
            return 'cluster_morosidad';
        }

        if (abs($data['cambio_valorizacion'] ?? 0) >= self::CROSS_ALERT_THRESHOLDS['cambio_valorizacion']) {
            return 'cambio_valorizacion';
        }

        if ($alert->alert_type === 'regulatory_impact') {
            return 'impacto_regulatorio';
        }

        return 'general';
    }

    /**
     * Buscar copropiedades afectadas por ubicación
     *
     * @param array $location
     * @return \Illuminate\Support\Collection
     */
    protected function findAffectedCopropiedades(array $location): \Illuminate\Support\Collection
    {
        $query = \App\Models\Copropiedad::query();

        // Filtrar por comuna si está disponible
        if (isset($location['comuna'])) {
            $query->where('comuna', $location['comuna']);
        }

        // Filtrar por proximidad geográfica si hay coordenadas
        if (isset($location['latitud'], $location['longitud'])) {
            $lat = $location['latitud'];
            $lng = $location['longitud'];
            $radius = $location['radius_km'] ?? 2; // 2km por defecto

            // Aproximación simple sin PostGIS
            $query->whereRaw("
                (6371 * acos(
                    cos(radians(?)) * cos(radians(latitud)) * 
                    cos(radians(longitud) - radians(?)) + 
                    sin(radians(?)) * sin(radians(latitud))
                )) <= ?
            ", [$lat, $lng, $lat, $radius]);
        }

        return $query->where('activa', true)->get();
    }

    /**
     * Mapear tipo de alerta de ÁGORA a tipo local
     *
     * @param string $agoraType
     * @return string
     */
    protected function mapAgoraAlertType(string $agoraType): string
    {
        return match ($agoraType) {
            'cambio_uso_suelo' => PrecessionAlertEngine::TYPE_REGULATORY,
            'nueva_infraestructura' => PrecessionAlertEngine::TYPE_MARKET,
            'presion_prc' => PrecessionAlertEngine::TYPE_REGULATORY,
            'cambio_valorizacion' => PrecessionAlertEngine::TYPE_MARKET,
            'cluster_morosidad' => PrecessionAlertEngine::TYPE_RISK_THRESHOLD,
            default => PrecessionAlertEngine::TYPE_TREND_CHANGE,
        };
    }

    /**
     * Mapear severidad de ÁGORA a local
     *
     * @param string $agoraSeverity
     * @return string
     */
    protected function mapAgoraSeverity(string $agoraSeverity): string
    {
        return match ($agoraSeverity) {
            'critico', 'critical' => PrecessionAlertEngine::SEVERITY_CRITICAL,
            'alto', 'high' => PrecessionAlertEngine::SEVERITY_HIGH,
            'medio', 'warning', 'medium' => PrecessionAlertEngine::SEVERITY_WARNING,
            default => PrecessionAlertEngine::SEVERITY_INFO,
        };
    }

    /**
     * Calcular métricas de predicción
     *
     * @param array $predictionResult
     * @return array
     */
    protected function calculatePredictionMetrics(array $predictionResult): array
    {
        $predicted = $predictionResult['predicted_value'] ?? 0;
        $actual = $predictionResult['actual_value'] ?? 0;

        if ($actual == 0 && $predicted == 0) {
            return ['mae' => 0, 'mape' => 0, 'accuracy' => 1];
        }

        // Mean Absolute Error
        $mae = abs($predicted - $actual);

        // Mean Absolute Percentage Error
        $mape = $actual != 0 ? abs(($actual - $predicted) / $actual) : 0;

        // Accuracy (1 - MAPE, bounded)
        $accuracy = max(0, min(1, 1 - $mape));

        return [
            'mae' => round($mae, 4),
            'mape' => round($mape, 4),
            'accuracy' => round($accuracy, 4),
            'predicted' => $predicted,
            'actual' => $actual,
        ];
    }

    /**
     * Obtener estado de sincronización
     *
     * @return array
     */
    public function getSyncStatus(): array
    {
        return [
            'enabled' => $this->config['enabled'],
            'last_ontology_sync' => Cache::get('pae:sync:ontology:last'),
            'last_agora_receive' => Cache::get('pae:sync:agora:last'),
            'event_bus_driver' => $this->config['event_bus_driver'],
            'ontology_stats' => $this->graphEngine->getStats(),
        ];
    }
}
