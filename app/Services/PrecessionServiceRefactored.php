<?php

declare(strict_types=1);

namespace App\Services;

use App\Events\PAE\PrecessionAnalysisCompleted;
use App\Models\Copropiedad;
use App\Models\PAE\PrecessionAnalysis;
use App\Models\PAE\PrecessionAlert;
use App\Services\PAE\PrecessionGraphEngine;
use App\Services\PAE\PrecessionScoringEngine;
use App\Services\PAE\PrecessionMLConnector;
use App\Services\PAE\PrecessionAlertEngine;
use App\Services\PAE\PrecessionSyncService;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION SERVICE (REFACTORIZADO)
 * Orquestador de Engines Nativos PHP/Laravel
 * =========================================================================
 *
 * Este servicio ha sido REFACTORIZADO para usar engines nativos PHP en lugar
 * de llamadas HTTP al PAE Core externo (FastAPI).
 *
 * ARQUITECTURA ANTERIOR (ELIMINADA):
 * - Llamadas HTTP POST al PAE Core externo
 * - Dependencia de pae_api_url y pae_api_key
 *
 * ARQUITECTURA NUEVA (IMPLEMENTADA):
 * - PrecessionGraphEngine: Motor de grafo nativo
 * - PrecessionScoringEngine: Motor de scoring nativo
 * - PrecessionMLConnector: Conexión ML con fallback
 * - PrecessionAlertEngine: Motor de alertas nativo
 * - PrecessionSyncService: Sincronización con ÁGORA
 *
 * @package App\Services
 * @version 2.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionService
{
    /**
     * Motor de grafo precesional
     * @var PrecessionGraphEngine
     */
    protected PrecessionGraphEngine $graphEngine;

    /**
     * Motor de scoring
     * @var PrecessionScoringEngine
     */
    protected PrecessionScoringEngine $scoringEngine;

    /**
     * Conector ML
     * @var PrecessionMLConnector
     */
    protected PrecessionMLConnector $mlConnector;

    /**
     * Motor de alertas
     * @var PrecessionAlertEngine
     */
    protected PrecessionAlertEngine $alertEngine;

    /**
     * Servicio de sincronización
     * @var PrecessionSyncService|null
     */
    protected ?PrecessionSyncService $syncService;

    /**
     * Configuración
     * @var array
     */
    protected array $config;

    /**
     * Constructor con inyección de dependencias
     *
     * @param PrecessionGraphEngine $graphEngine
     * @param PrecessionScoringEngine $scoringEngine
     * @param PrecessionMLConnector $mlConnector
     * @param PrecessionAlertEngine $alertEngine
     * @param PrecessionSyncService|null $syncService
     */
    public function __construct(
        PrecessionGraphEngine $graphEngine,
        PrecessionScoringEngine $scoringEngine,
        PrecessionMLConnector $mlConnector,
        PrecessionAlertEngine $alertEngine,
        ?PrecessionSyncService $syncService = null
    ) {
        $this->graphEngine = $graphEngine;
        $this->scoringEngine = $scoringEngine;
        $this->mlConnector = $mlConnector;
        $this->alertEngine = $alertEngine;
        $this->syncService = $syncService;

        $this->config = config('datapolis.pae', []);
    }

    // =========================================================================
    // ANÁLISIS PRINCIPAL
    // =========================================================================

    /**
     * Analizar copropiedad
     *
     * Ejecuta análisis precesional completo para una copropiedad.
     *
     * @param int $copropiedadId
     * @param array $options [horizon, radius, max_depth, include_ml, force_refresh]
     * @return PrecessionAnalysis
     */
    public function analyzeCopropiedad(int $copropiedadId, array $options = []): PrecessionAnalysis
    {
        $startTime = microtime(true);

        // Opciones con defaults
        $horizon = $options['horizon'] ?? 36;
        $radius = $options['radius'] ?? 1000;
        $maxDepth = $options['max_depth'] ?? 4;
        $includeML = $options['include_ml'] ?? true;
        $forceRefresh = $options['force_refresh'] ?? false;

        // Verificar caché si no es force refresh
        $cacheKey = "pae:analysis:{$copropiedadId}:{$horizon}:{$maxDepth}";
        if (!$forceRefresh) {
            $cached = Cache::get($cacheKey);
            if ($cached) {
                Log::debug('PrecessionService: Análisis desde caché', [
                    'copropiedad_id' => $copropiedadId,
                ]);
                return $cached;
            }
        }

        // Cargar copropiedad
        $copropiedad = Copropiedad::with(['unidades', 'gastos', 'compliance'])
            ->findOrFail($copropiedadId);

        // =====================================================================
        // PASO 1: Construir contexto desde módulos existentes
        // =====================================================================
        $context = $this->buildContext($copropiedad);

        // =====================================================================
        // PASO 2: Análisis precesional con Graph Engine NATIVO
        // (ANTES: HTTP POST al PAE Core externo)
        // (AHORA: llamada local in-process)
        // =====================================================================
        
        // Determinar nodo de intervención principal
        $interventionNode = $this->determineInterventionNode($context);
        
        $graphAnalysis = $this->graphEngine->analyzePrecession(
            $interventionNode,
            $maxDepth,
            $horizon
        );

        // =====================================================================
        // PASO 3: Calcular scores con Scoring Engine NATIVO
        // =====================================================================
        $precessionScore = $this->scoringEngine->calculatePrecessionScore(
            $graphAnalysis['effects']
        );
        
        $riskScore = $this->scoringEngine->calculateRiskScore(
            $graphAnalysis['effects']
        );
        
        $opportunityScore = $this->scoringEngine->calculateOpportunityScore(
            $graphAnalysis['effects']
        );

        $multiplier = $this->graphEngine->calculateMultiplier($graphAnalysis);

        // =====================================================================
        // PASO 4: Predicciones ML (con fallback)
        // =====================================================================
        $mlPredictions = null;
        if ($includeML) {
            $historical = $this->getHistoricalData($copropiedadId);
            $trendPrediction = $this->mlConnector->predictTrend($historical, $horizon);
            $morosidadPrediction = $this->mlConnector->predictMorosidad($context);
            $narrative = $this->mlConnector->generateNarrative($graphAnalysis);

            $mlPredictions = [
                'trend' => $trendPrediction,
                'morosidad' => $morosidadPrediction,
                'narrative' => $narrative,
                'model_version' => 'PAE-Native-1.0',
                'ollama_available' => $this->mlConnector->isOllamaAvailable(),
            ];
        }

        // =====================================================================
        // PASO 5: Evaluar umbrales y generar alertas
        // =====================================================================
        $analysisData = [
            'effects' => $graphAnalysis['effects'],
            'effects_by_angle' => $graphAnalysis['effects_by_angle'],
            'metrics' => $graphAnalysis['metrics'],
            'precession_score' => $precessionScore,
            'risk_score' => $riskScore,
            'opportunity_score' => $opportunityScore,
            'context' => $context,
        ];

        $alertsData = $this->alertEngine->evaluateThresholds(
            $analysisData,
            $copropiedadId,
            $copropiedad->tenant_id
        );

        // =====================================================================
        // PASO 6: Persistir análisis en BD
        // =====================================================================
        $analysis = $this->persistAnalysis(
            $copropiedad,
            $graphAnalysis,
            $precessionScore,
            $riskScore,
            $opportunityScore,
            $multiplier,
            $mlPredictions,
            $options
        );

        // Persistir alertas generadas
        if (!empty($alertsData)) {
            $this->alertEngine->persistAlerts($alertsData);
        }

        // Guardar en caché
        Cache::put($cacheKey, $analysis, now()->addHour());

        // =====================================================================
        // PASO 7: Publicar evento
        // =====================================================================
        event(new PrecessionAnalysisCompleted($analysis, $alertsData));

        // Log tiempo de ejecución
        $executionTime = round((microtime(true) - $startTime) * 1000, 2);
        Log::info('PrecessionService: Análisis completado', [
            'copropiedad_id' => $copropiedadId,
            'precession_score' => $precessionScore,
            'risk_score' => $riskScore,
            'effects_count' => count($graphAnalysis['effects']),
            'alerts_count' => count($alertsData),
            'execution_time_ms' => $executionTime,
        ]);

        return $analysis;
    }

    // =========================================================================
    // CONSTRUCCIÓN DE CONTEXTO
    // =========================================================================

    /**
     * Construir contexto desde módulos DATAPOLIS
     *
     * @param Copropiedad $copropiedad
     * @return array
     */
    public function buildContext(Copropiedad $copropiedad): array
    {
        return [
            'copropiedad' => $this->buildCopropiedadContext($copropiedad),
            'tributario' => $this->buildTributarioContext($copropiedad),
            'gastos' => $this->buildGastosContext($copropiedad),
            'compliance' => $this->buildComplianceContext($copropiedad),
            'alicuotas' => $this->buildAlicuotasContext($copropiedad),
            'valorizacion' => $this->buildValorizacionContext($copropiedad),
            'arriendos' => $this->buildArriendosContext($copropiedad),
        ];
    }

    /**
     * Contexto de copropiedad
     */
    protected function buildCopropiedadContext(Copropiedad $copropiedad): array
    {
        return [
            'id' => $copropiedad->id,
            'nombre' => $copropiedad->nombre,
            'direccion' => $copropiedad->direccion,
            'comuna' => $copropiedad->comuna,
            'region' => $copropiedad->region,
            'latitud' => $copropiedad->latitud,
            'longitud' => $copropiedad->longitud,
            'tipo' => $copropiedad->tipo,
            'unidades_count' => $copropiedad->unidades_count ?? $copropiedad->unidades()->count(),
            'superficie_total' => $copropiedad->superficie_total,
            'antiguedad_edificacion' => $copropiedad->ano_construccion 
                ? now()->year - $copropiedad->ano_construccion 
                : null,
        ];
    }

    /**
     * Contexto tributario (M04)
     */
    protected function buildTributarioContext(Copropiedad $copropiedad): array
    {
        try {
            // Intentar cargar desde módulo tributario si existe
            $tributario = $copropiedad->tributario ?? null;
            
            if ($tributario) {
                return [
                    'carga_tributaria' => $tributario->carga_anual_estimada ?? 0,
                    'riesgo_fiscalizacion' => $tributario->riesgo_fiscalizacion ?? 0,
                    'cumplimiento_global' => $tributario->cumplimiento_global ?? 0,
                    'ahorro_potencial' => $tributario->ahorro_potencial ?? 0,
                ];
            }

            return [
                'carga_tributaria' => 0,
                'riesgo_fiscalizacion' => 0,
                'cumplimiento_global' => 0,
                'ahorro_potencial' => 0,
            ];
        } catch (\Exception $e) {
            return ['error' => 'Módulo tributario no disponible'];
        }
    }

    /**
     * Contexto de gastos comunes (M05)
     */
    protected function buildGastosContext(Copropiedad $copropiedad): array
    {
        try {
            $gastos = $copropiedad->gastos()
                ->where('fecha', '>=', now()->subMonths(36))
                ->orderBy('fecha', 'desc')
                ->get();

            if ($gastos->isEmpty()) {
                return ['gasto_comun_promedio' => 0, 'tendencia' => 'indeterminada'];
            }

            $promedio = $gastos->avg('monto');
            $ultimo = $gastos->first()->monto ?? $promedio;
            $hace12m = $gastos->where('fecha', '>=', now()->subMonths(12))->avg('monto') ?? $promedio;

            $tendencia = 'estable';
            if ($hace12m > 0) {
                $cambio = (($ultimo - $hace12m) / $hace12m) * 100;
                if ($cambio > 5) $tendencia = 'creciente';
                elseif ($cambio < -5) $tendencia = 'decreciente';
            }

            return [
                'gasto_comun_promedio' => round($promedio, 2),
                'ultimo_gasto' => round($ultimo, 2),
                'tendencia' => $tendencia,
                'volatilidad' => $promedio > 0 ? round($gastos->std('monto') / $promedio, 4) : 0,
            ];
        } catch (\Exception $e) {
            return ['error' => 'Datos de gastos no disponibles'];
        }
    }

    /**
     * Contexto de compliance (M06)
     */
    protected function buildComplianceContext(Copropiedad $copropiedad): array
    {
        try {
            $compliance = $copropiedad->compliance ?? null;

            if ($compliance) {
                return [
                    'score_global' => $compliance->score_global ?? 0,
                    'ds7_score' => $compliance->ds7_score ?? 0,
                    'ley21442_status' => $compliance->ley21442_status ?? 'desconocido',
                    'brechas' => [
                        'cantidad' => $compliance->gaps_count ?? 0,
                        'criticas' => $compliance->critical_gaps ?? [],
                    ],
                ];
            }

            return [
                'score_global' => 50,
                'ds7_score' => 50,
                'ley21442_status' => 'desconocido',
                'brechas' => ['cantidad' => 0, 'criticas' => []],
            ];
        } catch (\Exception $e) {
            return ['error' => 'Datos de compliance no disponibles'];
        }
    }

    /**
     * Contexto de alícuotas (M07)
     */
    protected function buildAlicuotasContext(Copropiedad $copropiedad): array
    {
        try {
            $unidades = $copropiedad->unidades()->get();
            
            if ($unidades->isEmpty()) {
                return ['gini' => 0, 'dispersion' => 0];
            }

            $alicuotas = $unidades->pluck('alicuota_prorrateo')->filter()->values();
            
            if ($alicuotas->isEmpty()) {
                return ['gini' => 0, 'dispersion' => 0];
            }

            // Calcular Gini simplificado
            $mean = $alicuotas->avg();
            $gini = 0;
            if ($mean > 0) {
                $sum = 0;
                foreach ($alicuotas as $a) {
                    foreach ($alicuotas as $b) {
                        $sum += abs($a - $b);
                    }
                }
                $gini = $sum / (2 * count($alicuotas) * count($alicuotas) * $mean);
            }

            return [
                'gini' => round($gini, 4),
                'dispersion' => $mean > 0 ? round($alicuotas->std() / $mean, 4) : 0,
                'promedio' => round($mean, 4),
            ];
        } catch (\Exception $e) {
            return ['error' => 'Datos de alícuotas no disponibles'];
        }
    }

    /**
     * Contexto de valorización (M08)
     */
    protected function buildValorizacionContext(Copropiedad $copropiedad): array
    {
        try {
            $avaluo = $copropiedad->avaluo ?? null;
            
            return [
                'valor_suelo_m2' => $avaluo->valor_m2_uf ?? 0,
                'avaluo_fiscal' => $avaluo->valor_uf ?? 0,
                'fecha_avaluo' => $avaluo->fecha ?? null,
                'tendencia_zona' => $avaluo->tendencia_zona ?? 'estable',
            ];
        } catch (\Exception $e) {
            return ['error' => 'Datos de valorización no disponibles'];
        }
    }

    /**
     * Contexto de arriendos (M16)
     */
    protected function buildArriendosContext(Copropiedad $copropiedad): array
    {
        try {
            $unidades = $copropiedad->unidades()->get();
            $arrendadas = $unidades->where('estado', 'arrendada');
            $vacantes = $unidades->where('estado', 'vacante');

            $totalUnidades = $unidades->count();
            $tasaVacancia = $totalUnidades > 0 
                ? $vacantes->count() / $totalUnidades * 100 
                : 0;

            $arriendoPromedio = $arrendadas->avg('arriendo_mensual') ?? 0;

            return [
                'tasa_vacancia' => round($tasaVacancia, 2),
                'indice_arriendo_m2' => $arriendoPromedio,
                'unidades_arrendadas' => $arrendadas->count(),
                'unidades_vacantes' => $vacantes->count(),
            ];
        } catch (\Exception $e) {
            return ['error' => 'Datos de arriendos no disponibles'];
        }
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    /**
     * Determinar nodo de intervención principal
     *
     * @param array $context
     * @return array [node_id, magnitude, type]
     */
    protected function determineInterventionNode(array $context): array
    {
        // Priorizar según contexto disponible
        $interventions = [];

        // Valorización
        if (($context['valorizacion']['valor_suelo_m2'] ?? 0) > 0) {
            $interventions[] = [
                'node_id' => 'valor_suelo_m2',
                'magnitude' => $context['valorizacion']['valor_suelo_m2'],
                'type' => 'valuation',
                'priority' => 1,
            ];
        }

        // Morosidad/Gastos
        if (($context['gastos']['gasto_comun_promedio'] ?? 0) > 0) {
            $interventions[] = [
                'node_id' => 'gasto_comun_promedio',
                'magnitude' => $context['gastos']['gasto_comun_promedio'],
                'type' => 'expense',
                'priority' => 2,
            ];
        }

        // Compliance
        if (($context['compliance']['score_global'] ?? 0) > 0) {
            $interventions[] = [
                'node_id' => 'compliance_score',
                'magnitude' => $context['compliance']['score_global'] / 100,
                'type' => 'compliance',
                'priority' => 3,
            ];
        }

        // Vacancia
        if (($context['arriendos']['tasa_vacancia'] ?? 0) > 0) {
            $interventions[] = [
                'node_id' => 'tasa_vacancia',
                'magnitude' => $context['arriendos']['tasa_vacancia'] / 100,
                'type' => 'occupancy',
                'priority' => 4,
            ];
        }

        // Ordenar por prioridad y retornar el primero
        usort($interventions, fn($a, $b) => $a['priority'] <=> $b['priority']);

        return $interventions[0] ?? [
            'node_id' => 'valor_suelo_m2',
            'magnitude' => 1.0,
            'type' => 'generic',
        ];
    }

    /**
     * Obtener datos históricos para predicciones
     *
     * @param int $copropiedadId
     * @return array
     */
    protected function getHistoricalData(int $copropiedadId): array
    {
        try {
            // Obtener histórico de gastos como proxy
            $gastos = DB::table('gastos_comunes')
                ->where('copropiedad_id', $copropiedadId)
                ->where('fecha', '>=', now()->subMonths(36))
                ->orderBy('fecha')
                ->pluck('monto', 'fecha')
                ->toArray();

            return $gastos;
        } catch (\Exception $e) {
            return [];
        }
    }

    /**
     * Persistir análisis en BD
     *
     * @param Copropiedad $copropiedad
     * @param array $graphAnalysis
     * @param float $precessionScore
     * @param float $riskScore
     * @param float $opportunityScore
     * @param float $multiplier
     * @param array|null $mlPredictions
     * @param array $options
     * @return PrecessionAnalysis
     */
    protected function persistAnalysis(
        Copropiedad $copropiedad,
        array $graphAnalysis,
        float $precessionScore,
        float $riskScore,
        float $opportunityScore,
        float $multiplier,
        ?array $mlPredictions,
        array $options
    ): PrecessionAnalysis {
        // Calcular valores por ángulo
        $valuesByAngle = $this->calculateValuesByAngle($graphAnalysis);

        return PrecessionAnalysis::create([
            'id' => Str::uuid(),
            'copropiedad_id' => $copropiedad->id,
            'tenant_id' => $copropiedad->tenant_id,
            'analysis_type' => 'full',
            'status' => 'completed',
            
            // Scores
            'precession_score' => $precessionScore,
            'risk_score' => $riskScore,
            'opportunity_score' => $opportunityScore,
            'confidence' => $graphAnalysis['metrics']['avg_confidence'] ?? 0.7,
            
            // Valores por ángulo (UF)
            'total_precession_value_uf' => $valuesByAngle['total'],
            'direct_value_uf' => $valuesByAngle['direct_0'],
            'induced_value_uf' => $valuesByAngle['induced_45'],
            'precession_value_uf' => $valuesByAngle['precession_90'],
            'systemic_value_uf' => $valuesByAngle['systemic_135'],
            'counter_value_uf' => $valuesByAngle['counter_180'],
            
            // Efectos
            'effects_summary' => $graphAnalysis['metrics'],
            'effects_count' => $graphAnalysis['metrics']['total_effects'] ?? 0,
            
            // ML Predictions
            'ml_predictions' => $mlPredictions,
            
            // Parámetros
            'parameters' => [
                'horizon_months' => $options['horizon'] ?? 36,
                'radius_meters' => $options['radius'] ?? 1000,
                'max_depth' => $options['max_depth'] ?? 4,
                'include_ml' => $options['include_ml'] ?? true,
            ],
            
            // Metadatos
            'execution_time_ms' => $graphAnalysis['execution_time_ms'] ?? 0,
            'expires_at' => now()->addDays(7),
        ]);
    }

    /**
     * Calcular valores por ángulo
     *
     * @param array $graphAnalysis
     * @return array
     */
    protected function calculateValuesByAngle(array $graphAnalysis): array
    {
        $values = [
            'direct_0' => 0,
            'induced_45' => 0,
            'precession_90' => 0,
            'systemic_135' => 0,
            'counter_180' => 0,
            'total' => 0,
        ];

        // Factor de conversión a UF (simplificado)
        $ufFactor = 1000;

        foreach ($graphAnalysis['effects_by_angle'] as $angleClass => $effects) {
            $sum = array_sum(array_map(fn($e) => abs($e['weight']) * $ufFactor, $effects));
            $values[$angleClass] = round($sum, 2);
            $values['total'] += $sum;
        }

        $values['total'] = round($values['total'], 2);

        return $values;
    }

    // =========================================================================
    // MÉTODOS PÚBLICOS ADICIONALES
    // =========================================================================

    /**
     * Calcular Investment Score
     *
     * @param int $copropiedadId
     * @param array|null $precessionAnalysis
     * @return array
     */
    public function calculateInvestmentScore(int $copropiedadId, ?array $precessionAnalysis = null): array
    {
        $copropiedad = Copropiedad::findOrFail($copropiedadId);
        $context = $this->buildContext($copropiedad);

        if (!$precessionAnalysis) {
            $analysis = $this->analyzeCopropiedad($copropiedadId);
            $precessionAnalysis = [
                'effects' => [],
                'precession_score' => $analysis->precession_score,
                'risk_score' => $analysis->risk_score,
            ];
        }

        return $this->scoringEngine->calculateInvestmentScore($context, $precessionAnalysis);
    }

    /**
     * Comparar copropiedades
     *
     * @param array $copropiedadIds
     * @return array
     */
    public function comparePrecession(array $copropiedadIds): array
    {
        $data = [];

        foreach ($copropiedadIds as $id) {
            try {
                $copropiedad = Copropiedad::find($id);
                if (!$copropiedad) continue;

                $analysis = $this->analyzeCopropiedad($id, ['force_refresh' => false]);
                $context = $this->buildContext($copropiedad);

                $data[$id] = [
                    'data' => $context,
                    'analysis' => [
                        'effects' => [],
                        'precession_score' => $analysis->precession_score,
                        'risk_score' => $analysis->risk_score,
                        'opportunity_score' => $analysis->opportunity_score,
                    ],
                ];
            } catch (\Exception $e) {
                Log::warning("PrecessionService: Error comparando copropiedad {$id}", [
                    'error' => $e->getMessage(),
                ]);
            }
        }

        return $this->scoringEngine->compareCopropiedades($data);
    }

    /**
     * Generar alertas para una copropiedad
     *
     * @param int $copropiedadId
     * @return Collection
     */
    public function generateAlerts(int $copropiedadId): Collection
    {
        $analysis = $this->analyzeCopropiedad($copropiedadId);
        
        return $this->alertEngine->getActiveAlerts($copropiedadId);
    }

    /**
     * Obtener dashboard de una copropiedad
     *
     * @param int $copropiedadId
     * @return array
     */
    public function getDashboard(int $copropiedadId): array
    {
        $analysis = PrecessionAnalysis::where('copropiedad_id', $copropiedadId)
            ->where('status', 'completed')
            ->orderBy('created_at', 'desc')
            ->first();

        $alerts = $this->alertEngine->getActiveAlerts($copropiedadId);

        $copropiedad = Copropiedad::find($copropiedadId);
        $context = $copropiedad ? $this->buildContext($copropiedad) : [];

        return [
            'analysis' => $analysis,
            'alerts' => $alerts,
            'context' => $context,
            'metrics' => $analysis ? [
                'precession_score' => $analysis->precession_score,
                'risk_score' => $analysis->risk_score,
                'opportunity_score' => $analysis->opportunity_score,
            ] : null,
        ];
    }

    /**
     * Sincronizar con ÁGORA
     *
     * @return void
     */
    public function syncWithAgora(): void
    {
        if ($this->syncService) {
            $this->syncService->syncOntologyToAgora();
        }
    }
}
