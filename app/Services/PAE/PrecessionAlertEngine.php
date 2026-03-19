<?php

declare(strict_types=1);

namespace App\Services\PAE;

use App\Models\PAE\PrecessionAlert;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION ALERT ENGINE
 * Motor de Alertas Precesionales Nativo PHP/Laravel
 * =========================================================================
 *
 * Motor de detección y gestión de alertas precesionales.
 * Evalúa umbrales configurables y genera alertas sin dependencia externa.
 *
 * NIVELES DE SEVERIDAD:
 * - CRITICAL: risk_score > 0.8 OR efecto negativo confianza > 0.85
 * - HIGH: risk_score > 0.6 OR múltiples efectos negativos
 * - WARNING: risk_score > 0.5 OR cambio score > 20% en 30 días
 * - INFO: nuevo efecto precesional detectado
 *
 * @package App\Services\PAE
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionAlertEngine
{
    /**
     * Tipos de alerta
     */
    public const TYPE_RISK_THRESHOLD = 'risk_threshold';
    public const TYPE_OPPORTUNITY = 'opportunity_detected';
    public const TYPE_TREND_CHANGE = 'trend_change';
    public const TYPE_ANOMALY = 'anomaly_detected';
    public const TYPE_DEADLINE = 'deadline_approaching';
    public const TYPE_REGULATORY = 'regulatory_impact';
    public const TYPE_MARKET = 'market_shift';

    /**
     * Severidades
     */
    public const SEVERITY_CRITICAL = 'critical';
    public const SEVERITY_HIGH = 'high';
    public const SEVERITY_WARNING = 'warning';
    public const SEVERITY_INFO = 'info';

    /**
     * Configuración de umbrales
     * @var array
     */
    protected array $thresholds;

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->thresholds = config('datapolis.pae.alerts', [
            'critical_threshold' => 0.8,
            'high_threshold' => 0.6,
            'warning_threshold' => 0.5,
            'change_threshold_percent' => 20,
            'negative_effect_confidence_critical' => 0.85,
            'opportunity_threshold' => 0.7,
        ]);
    }

    // =========================================================================
    // EVALUACIÓN DE UMBRALES
    // =========================================================================

    /**
     * Evaluar umbrales y generar alertas
     *
     * @param array $analysis Resultado del análisis precesional
     * @param int|null $copropiedadId ID de la copropiedad
     * @param int|null $tenantId ID del tenant
     * @return array Lista de alertas generadas
     */
    public function evaluateThresholds(
        array $analysis,
        ?int $copropiedadId = null,
        ?int $tenantId = null
    ): array {
        $alerts = [];
        $effects = $analysis['effects'] ?? [];
        $metrics = $analysis['metrics'] ?? [];

        // Calcular scores si no vienen en el análisis
        $scoringEngine = app(PrecessionScoringEngine::class);
        $riskScore = $analysis['risk_score'] ?? $scoringEngine->calculateRiskScore($effects);
        $opportunityScore = $analysis['opportunity_score'] ?? $scoringEngine->calculateOpportunityScore($effects);
        $precessionScore = $analysis['precession_score'] ?? $scoringEngine->calculatePrecessionScore($effects);

        // 1. Evaluar umbral de riesgo crítico
        if ($riskScore >= $this->thresholds['critical_threshold']) {
            $alerts[] = $this->createAlertData(
                self::TYPE_RISK_THRESHOLD,
                self::SEVERITY_CRITICAL,
                'Riesgo Crítico Detectado',
                "El índice de riesgo precesional ({$this->formatPercent($riskScore)}) supera el umbral crítico. " .
                "Se requiere acción inmediata para mitigar los efectos negativos identificados.",
                [
                    'risk_score' => $riskScore,
                    'threshold' => $this->thresholds['critical_threshold'],
                    'negative_effects' => $metrics['negative_effects'] ?? 0,
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        } elseif ($riskScore >= $this->thresholds['high_threshold']) {
            $alerts[] = $this->createAlertData(
                self::TYPE_RISK_THRESHOLD,
                self::SEVERITY_HIGH,
                'Riesgo Alto Detectado',
                "El índice de riesgo ({$this->formatPercent($riskScore)}) requiere atención. " .
                "Revisar los factores de riesgo para prevenir deterioro.",
                [
                    'risk_score' => $riskScore,
                    'threshold' => $this->thresholds['high_threshold'],
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        } elseif ($riskScore >= $this->thresholds['warning_threshold']) {
            $alerts[] = $this->createAlertData(
                self::TYPE_RISK_THRESHOLD,
                self::SEVERITY_WARNING,
                'Riesgo Moderado',
                "Se detecta riesgo moderado ({$this->formatPercent($riskScore)}). " .
                "Monitorear evolución de indicadores.",
                [
                    'risk_score' => $riskScore,
                    'threshold' => $this->thresholds['warning_threshold'],
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        // 2. Evaluar efectos negativos de alta confianza
        $criticalNegativeEffects = array_filter($effects, function ($effect) {
            return ($effect['weight'] ?? 0) < 0 &&
                   ($effect['confidence'] ?? 0) >= $this->thresholds['negative_effect_confidence_critical'];
        });

        if (!empty($criticalNegativeEffects)) {
            $topNegative = array_slice($criticalNegativeEffects, 0, 3);
            $effectDescriptions = array_map(
                fn($e) => "{$e['target_name']} (confianza: {$this->formatPercent($e['confidence'])})",
                $topNegative
            );

            $alerts[] = $this->createAlertData(
                self::TYPE_ANOMALY,
                self::SEVERITY_CRITICAL,
                'Efectos Negativos de Alta Certeza',
                "Se detectaron " . count($criticalNegativeEffects) . " efectos negativos con alta confianza: " .
                implode(', ', $effectDescriptions),
                [
                    'critical_effects' => $criticalNegativeEffects,
                    'count' => count($criticalNegativeEffects),
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        // 3. Evaluar oportunidades
        if ($opportunityScore >= $this->thresholds['opportunity_threshold']) {
            $alerts[] = $this->createAlertData(
                self::TYPE_OPPORTUNITY,
                self::SEVERITY_INFO,
                'Oportunidad de Inversión Detectada',
                "El análisis precesional identifica potencial de oportunidad ({$this->formatPercent($opportunityScore)}). " .
                "Considerar estrategias de capitalización.",
                [
                    'opportunity_score' => $opportunityScore,
                    'positive_effects' => $metrics['positive_effects'] ?? 0,
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        // 4. Evaluar cambios significativos (comparar con análisis anterior)
        $changeAlert = $this->evaluateScoreChange($copropiedadId, $precessionScore);
        if ($changeAlert) {
            $alerts[] = $changeAlert;
        }

        // 5. Evaluar efectos por horizonte temporal (deadlines)
        $shortTermEffects = array_filter($effects, fn($e) => ($e['lag_months'] ?? 12) <= 6);
        $criticalShortTerm = array_filter($shortTermEffects, fn($e) => ($e['weight'] ?? 0) < -0.3);

        if (!empty($criticalShortTerm)) {
            $alerts[] = $this->createAlertData(
                self::TYPE_DEADLINE,
                self::SEVERITY_HIGH,
                'Efectos Negativos a Corto Plazo',
                "Se identifican " . count($criticalShortTerm) . " efectos negativos significativos " .
                "en los próximos 6 meses. Requiere atención prioritaria.",
                [
                    'effects' => $criticalShortTerm,
                    'horizon' => '6 meses',
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        // 6. Evaluar impactos regulatorios (si hay datos de compliance)
        if (isset($analysis['context']['compliance'])) {
            $complianceAlert = $this->evaluateComplianceImpact($analysis['context']['compliance'], $copropiedadId, $tenantId, $analysis);
            if ($complianceAlert) {
                $alerts[] = $complianceAlert;
            }
        }

        Log::info('PrecessionAlertEngine: Evaluación completada', [
            'copropiedad_id' => $copropiedadId,
            'alerts_generated' => count($alerts),
            'risk_score' => $riskScore,
        ]);

        return $alerts;
    }

    /**
     * Evaluar cambio de score respecto a análisis anterior
     *
     * @param int|null $copropiedadId
     * @param float $currentScore
     * @return array|null
     */
    protected function evaluateScoreChange(?int $copropiedadId, float $currentScore): ?array
    {
        if (!$copropiedadId) {
            return null;
        }

        // Buscar análisis anterior (últimos 30 días)
        $cacheKey = "pae:last_score:{$copropiedadId}";
        $lastScore = Cache::get($cacheKey);

        // Guardar score actual para próxima comparación
        Cache::put($cacheKey, $currentScore, now()->addDays(30));

        if ($lastScore === null) {
            return null;
        }

        $changePercent = $lastScore > 0 
            ? (($currentScore - $lastScore) / $lastScore) * 100 
            : 0;

        if (abs($changePercent) >= $this->thresholds['change_threshold_percent']) {
            $direction = $changePercent > 0 ? 'incremento' : 'decremento';
            $severity = abs($changePercent) >= 30 ? self::SEVERITY_HIGH : self::SEVERITY_WARNING;

            return $this->createAlertData(
                self::TYPE_TREND_CHANGE,
                $severity,
                "Cambio Significativo en Score Precesional",
                "Se detectó un {$direction} del {$this->formatPercent(abs($changePercent)/100)} en el score precesional " .
                "respecto al último análisis (de {$lastScore} a {$currentScore}).",
                [
                    'previous_score' => $lastScore,
                    'current_score' => $currentScore,
                    'change_percent' => $changePercent,
                ],
                $copropiedadId,
                null,
                []
            );
        }

        return null;
    }

    /**
     * Evaluar impacto de compliance
     *
     * @param array $complianceData
     * @param int|null $copropiedadId
     * @param int|null $tenantId
     * @param array $analysis
     * @return array|null
     */
    protected function evaluateComplianceImpact(
        array $complianceData,
        ?int $copropiedadId,
        ?int $tenantId,
        array $analysis
    ): ?array {
        $scoreGlobal = $complianceData['score_global'] ?? 100;
        $brechasCriticas = $complianceData['brechas']['criticas'] ?? [];

        // Alerta por score bajo de compliance
        if ($scoreGlobal < 50) {
            return $this->createAlertData(
                self::TYPE_REGULATORY,
                self::SEVERITY_HIGH,
                'Bajo Score de Compliance',
                "El score de compliance ({$scoreGlobal}/100) está por debajo del mínimo aceptable. " .
                "Esto puede generar efectos precesionales negativos en valorización y riesgo.",
                [
                    'compliance_score' => $scoreGlobal,
                    'critical_gaps' => count($brechasCriticas),
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        // Alerta por brechas críticas
        if (!empty($brechasCriticas)) {
            return $this->createAlertData(
                self::TYPE_REGULATORY,
                self::SEVERITY_WARNING,
                'Brechas Normativas Críticas',
                "Se identifican " . count($brechasCriticas) . " brechas normativas críticas " .
                "que pueden impactar la valorización y cumplimiento regulatorio.",
                [
                    'critical_gaps' => $brechasCriticas,
                ],
                $copropiedadId,
                $tenantId,
                $analysis
            );
        }

        return null;
    }

    // =========================================================================
    // GENERACIÓN DE ALERTAS
    // =========================================================================

    /**
     * Crear datos de alerta
     *
     * @param string $type
     * @param string $severity
     * @param string $title
     * @param string $description
     * @param array $data
     * @param int|null $copropiedadId
     * @param int|null $tenantId
     * @param array $analysis
     * @return array
     */
    protected function createAlertData(
        string $type,
        string $severity,
        string $title,
        string $description,
        array $data,
        ?int $copropiedadId,
        ?int $tenantId,
        array $analysis
    ): array {
        // Determinar ángulo precesional predominante
        $predominantAngle = $this->determinePredominantAngle($analysis);

        // Calcular impacto potencial
        $potentialImpact = $this->calculatePotentialImpact($data, $severity);

        // Calcular probabilidad
        $probability = $this->calculateProbability($data, $analysis);

        // Determinar horizonte esperado
        $expectedMonths = $this->determineExpectedHorizon($analysis, $type);

        // Generar recomendación
        $recommendation = $this->generateRecommendation($type, $severity, $data);

        return [
            'tenant_id' => $tenantId ?? auth()->id() ?? 1,
            'copropiedad_id' => $copropiedadId,
            'analysis_id' => $analysis['id'] ?? null,
            'alert_type' => $type,
            'severity' => $severity,
            'precession_angle' => $predominantAngle,
            'status' => 'active',
            'title' => $title,
            'description' => $description,
            'recommendation' => $recommendation,
            'probability' => $probability,
            'potential_impact_uf' => $potentialImpact,
            'expected_months' => $expectedMonths,
            'data' => $data,
            'expires_at' => now()->addMonths(3),
            'created_at' => now(),
        ];
    }

    /**
     * Generar alerta (persistir en BD)
     *
     * @param string $type
     * @param string $severity
     * @param array $data
     * @return PrecessionAlert
     */
    public function generateAlert(string $type, string $severity, array $data): PrecessionAlert
    {
        $alertData = $this->createAlertData(
            $type,
            $severity,
            $data['title'] ?? 'Alerta Precesional',
            $data['description'] ?? '',
            $data['data'] ?? [],
            $data['copropiedad_id'] ?? null,
            $data['tenant_id'] ?? null,
            $data['analysis'] ?? []
        );

        return PrecessionAlert::create($alertData);
    }

    /**
     * Persistir múltiples alertas
     *
     * @param array $alertsData
     * @return Collection
     */
    public function persistAlerts(array $alertsData): Collection
    {
        $alerts = collect();

        foreach ($alertsData as $alertData) {
            try {
                // Verificar si ya existe alerta similar activa
                $exists = PrecessionAlert::where('copropiedad_id', $alertData['copropiedad_id'])
                    ->where('alert_type', $alertData['alert_type'])
                    ->where('severity', $alertData['severity'])
                    ->where('status', 'active')
                    ->where('created_at', '>', now()->subHours(24))
                    ->exists();

                if (!$exists) {
                    $alert = PrecessionAlert::create($alertData);
                    $alerts->push($alert);
                }
            } catch (\Exception $e) {
                Log::error('PrecessionAlertEngine: Error persistiendo alerta', [
                    'error' => $e->getMessage(),
                    'alert_data' => $alertData,
                ]);
            }
        }

        return $alerts;
    }

    // =========================================================================
    // GESTIÓN DE ALERTAS
    // =========================================================================

    /**
     * Obtener alertas activas
     *
     * @param int|null $copropiedadId
     * @param int|null $tenantId
     * @return Collection
     */
    public function getActiveAlerts(?int $copropiedadId = null, ?int $tenantId = null): Collection
    {
        $query = PrecessionAlert::where('status', 'active')
            ->where('expires_at', '>', now())
            ->orderByRaw("CASE severity 
                WHEN 'critical' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'warning' THEN 3 
                WHEN 'info' THEN 4 
                ELSE 5 END")
            ->orderBy('created_at', 'desc');

        if ($copropiedadId) {
            $query->where('copropiedad_id', $copropiedadId);
        }

        if ($tenantId) {
            $query->where('tenant_id', $tenantId);
        }

        return $query->get();
    }

    /**
     * Marcar alerta como leída/reconocida
     *
     * @param int $alertId
     * @return bool
     */
    public function acknowledgeAlert(int $alertId): bool
    {
        return PrecessionAlert::where('id', $alertId)
            ->update([
                'status' => 'acknowledged',
                'acknowledged_at' => now(),
                'acknowledged_by' => auth()->id(),
            ]) > 0;
    }

    /**
     * Resolver alerta
     *
     * @param int $alertId
     * @param string|null $notes
     * @return bool
     */
    public function resolveAlert(int $alertId, ?string $notes = null): bool
    {
        return PrecessionAlert::where('id', $alertId)
            ->update([
                'status' => 'resolved',
                'resolved_at' => now(),
                'resolved_by' => auth()->id(),
                'resolution_notes' => $notes,
            ]) > 0;
    }

    /**
     * Marcar alerta como leída (alias)
     *
     * @param int $alertId
     * @return void
     */
    public function markAsRead(int $alertId): void
    {
        $this->acknowledgeAlert($alertId);
    }

    /**
     * Configurar umbrales personalizados
     *
     * @param array $thresholds
     * @return void
     */
    public function configureThresholds(array $thresholds): void
    {
        $this->thresholds = array_merge($this->thresholds, $thresholds);
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    /**
     * Determinar ángulo precesional predominante
     *
     * @param array $analysis
     * @return string
     */
    protected function determinePredominantAngle(array $analysis): string
    {
        $effectsByAngle = $analysis['effects_by_angle'] ?? [];
        
        $maxCount = 0;
        $predominant = 'precession_90';

        foreach ($effectsByAngle as $angle => $effects) {
            if (count($effects) > $maxCount) {
                $maxCount = count($effects);
                $predominant = $angle;
            }
        }

        return $predominant;
    }

    /**
     * Calcular impacto potencial en UF
     *
     * @param array $data
     * @param string $severity
     * @return float
     */
    protected function calculatePotentialImpact(array $data, string $severity): float
    {
        // Base por severidad
        $baseImpact = match ($severity) {
            self::SEVERITY_CRITICAL => 1000,
            self::SEVERITY_HIGH => 500,
            self::SEVERITY_WARNING => 200,
            default => 50,
        };

        // Ajustar por datos disponibles
        $riskScore = $data['risk_score'] ?? 0.5;
        $multiplier = 1 + $riskScore;

        return round($baseImpact * $multiplier, 2);
    }

    /**
     * Calcular probabilidad
     *
     * @param array $data
     * @param array $analysis
     * @return float
     */
    protected function calculateProbability(array $data, array $analysis): float
    {
        $avgConfidence = $analysis['metrics']['avg_confidence'] ?? 0.7;
        $riskScore = $data['risk_score'] ?? 0.5;

        // Probabilidad = promedio ponderado de confianza y riesgo
        $probability = ($avgConfidence * 0.6 + $riskScore * 0.4);

        return round(min(1, max(0, $probability)), 4);
    }

    /**
     * Determinar horizonte esperado
     *
     * @param array $analysis
     * @param string $type
     * @return int
     */
    protected function determineExpectedHorizon(array $analysis, string $type): int
    {
        // Horizonte base por tipo
        $baseHorizon = match ($type) {
            self::TYPE_DEADLINE => 6,
            self::TYPE_RISK_THRESHOLD => 12,
            self::TYPE_OPPORTUNITY => 18,
            self::TYPE_REGULATORY => 12,
            default => 12,
        };

        // Ajustar por análisis
        $effects = $analysis['effects'] ?? [];
        if (!empty($effects)) {
            $avgLag = array_sum(array_column($effects, 'lag_months')) / count($effects);
            $baseHorizon = (int) round(($baseHorizon + $avgLag) / 2);
        }

        return max(3, min(60, $baseHorizon));
    }

    /**
     * Generar recomendación
     *
     * @param string $type
     * @param string $severity
     * @param array $data
     * @return string
     */
    protected function generateRecommendation(string $type, string $severity, array $data): string
    {
        return match ($type) {
            self::TYPE_RISK_THRESHOLD => match ($severity) {
                self::SEVERITY_CRITICAL => 'Convocar reunión urgente de comité. Revisar todos los factores de riesgo y definir plan de mitigación inmediato.',
                self::SEVERITY_HIGH => 'Programar revisión de indicadores críticos. Implementar medidas preventivas.',
                default => 'Monitorear evolución semanal de indicadores de riesgo.',
            },
            self::TYPE_OPPORTUNITY => 'Evaluar estrategias de capitalización. Considerar inversión adicional en mejoras.',
            self::TYPE_TREND_CHANGE => 'Analizar causas del cambio. Ajustar proyecciones financieras.',
            self::TYPE_DEADLINE => 'Priorizar acciones de corto plazo. Revisar calendario de intervenciones.',
            self::TYPE_REGULATORY => 'Iniciar proceso de regularización. Consultar con asesoría legal.',
            self::TYPE_MARKET => 'Actualizar análisis de mercado. Revisar estrategia de precios.',
            default => 'Revisar análisis detallado y tomar acciones según contexto.',
        };
    }

    /**
     * Formatear porcentaje
     *
     * @param float $value
     * @return string
     */
    protected function formatPercent(float $value): string
    {
        return number_format($value * 100, 1) . '%';
    }

    /**
     * Obtener estadísticas de alertas
     *
     * @param int|null $copropiedadId
     * @param int $days
     * @return array
     */
    public function getAlertStats(?int $copropiedadId = null, int $days = 30): array
    {
        $query = PrecessionAlert::where('created_at', '>=', now()->subDays($days));

        if ($copropiedadId) {
            $query->where('copropiedad_id', $copropiedadId);
        }

        $alerts = $query->get();

        return [
            'total' => $alerts->count(),
            'by_severity' => $alerts->groupBy('severity')->map->count(),
            'by_type' => $alerts->groupBy('alert_type')->map->count(),
            'by_status' => $alerts->groupBy('status')->map->count(),
            'critical_active' => $alerts->where('severity', 'critical')->where('status', 'active')->count(),
            'resolved_rate' => $alerts->count() > 0 
                ? round($alerts->where('status', 'resolved')->count() / $alerts->count() * 100, 1) 
                : 0,
        ];
    }
}
