<?php

declare(strict_types=1);

namespace App\Services\PAE;

use Illuminate\Support\Facades\Log;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION SCORING ENGINE
 * Motor de Scoring Precesional Nativo PHP/Laravel
 * =========================================================================
 *
 * Implementación nativa de algoritmos de scoring para análisis precesional.
 * Calcula scores de precesión, riesgo, oportunidad e inversión sin
 * dependencias externas.
 *
 * PONDERACIONES POR ÁNGULO (Teoría Fuller):
 * - 0° (Directo): 1.0 - Efecto lineal esperado
 * - 45° (Inducido): 1.2 - Efectos secundarios valiosos
 * - 90° (Precesión): 1.5 - Core de Fuller, máximo valor
 * - 135° (Sistémico): 1.3 - Efectos de segundo orden
 * - 180° (Contra): 0.8 - Retroalimentación, menor peso
 *
 * @package App\Services\PAE
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionScoringEngine
{
    /**
     * Pesos por ángulo precesional
     * @var array<string, float>
     */
    protected const ANGLE_WEIGHTS = [
        'direct_0' => 1.0,
        'induced_45' => 1.2,
        'precession_90' => 1.5,
        'systemic_135' => 1.3,
        'counter_180' => 0.8,
    ];

    /**
     * Configuración del engine
     * @var array
     */
    protected array $config;

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->config = config('datapolis.pae.scoring', [
            'weights' => [
                'precession' => 0.40,
                'financial' => 0.30,
                'compliance' => 0.20,
                'location' => 0.10,
            ],
        ]);
    }

    // =========================================================================
    // SCORING PRINCIPAL
    // =========================================================================

    /**
     * Calcular Precession Score
     *
     * Score compuesto que mide el valor total de efectos precesionales,
     * ponderado por ángulo y confianza.
     *
     * @param array $effects Lista de efectos del análisis
     * @return float Score 0-100
     */
    public function calculatePrecessionScore(array $effects): float
    {
        if (empty($effects)) {
            return 0.0;
        }

        $weightedSum = 0.0;
        $totalWeight = 0.0;

        foreach ($effects as $effect) {
            $angleClass = $effect['angle_class'] ?? 'precession_90';
            $angleWeight = self::ANGLE_WEIGHTS[$angleClass] ?? 1.0;
            $effectWeight = abs($effect['weight'] ?? 0);
            $confidence = $effect['confidence'] ?? 0.7;

            // Ponderación: peso del efecto × peso del ángulo × confianza
            $contribution = $effectWeight * $angleWeight * $confidence;
            
            // Bonus por efectos positivos, penalización por negativos
            if (($effect['weight'] ?? 0) > 0) {
                $contribution *= 1.1;
            } else {
                $contribution *= 0.9;
            }

            $weightedSum += $contribution;
            $totalWeight += $angleWeight * $confidence;
        }

        // Normalizar a escala 0-100
        if ($totalWeight == 0) {
            return 0.0;
        }

        // Aplicar función sigmoide para distribución natural
        $rawScore = ($weightedSum / $totalWeight) * 100;
        $normalizedScore = $this->sigmoidNormalize($rawScore, 50, 20);

        return round(min(100, max(0, $normalizedScore)), 2);
    }

    /**
     * Calcular Risk Score
     *
     * Evalúa el nivel de riesgo basado en efectos negativos,
     * ponderados por confianza y horizonte temporal.
     *
     * @param array $effects Lista de efectos
     * @return float Score 0-1 (mayor = más riesgo)
     */
    public function calculateRiskScore(array $effects): float
    {
        if (empty($effects)) {
            return 0.0;
        }

        // Filtrar efectos negativos
        $negativeEffects = array_filter($effects, fn($e) => ($e['weight'] ?? 0) < 0);

        if (empty($negativeEffects)) {
            return 0.0;
        }

        $riskScore = 0.0;
        $maxPossibleRisk = 0.0;

        foreach ($negativeEffects as $effect) {
            $weight = abs($effect['weight']);
            $confidence = $effect['confidence'] ?? 0.7;
            $lagMonths = $effect['lag_months'] ?? 12;

            // Mayor riesgo para efectos de corto plazo y alta confianza
            $timeDecay = $this->calculateTimeDecay($lagMonths);
            $riskContribution = $weight * $confidence * $timeDecay;

            $riskScore += $riskContribution;
            $maxPossibleRisk += $weight; // Máximo teórico sin decay
        }

        // Normalizar
        if ($maxPossibleRisk == 0) {
            return 0.0;
        }

        $normalizedRisk = $riskScore / $maxPossibleRisk;

        // Ajustar por cantidad de efectos negativos (más efectos = más riesgo)
        $countFactor = min(1.0, count($negativeEffects) / 5);
        $finalRisk = $normalizedRisk * (0.7 + 0.3 * $countFactor);

        return round(min(1.0, max(0.0, $finalRisk)), 4);
    }

    /**
     * Calcular Opportunity Score
     *
     * Evalúa el potencial de oportunidad basado en efectos positivos,
     * ponderados por magnitud y ventana temporal.
     *
     * @param array $effects Lista de efectos
     * @return float Score 0-1 (mayor = más oportunidad)
     */
    public function calculateOpportunityScore(array $effects): float
    {
        if (empty($effects)) {
            return 0.0;
        }

        // Filtrar efectos positivos
        $positiveEffects = array_filter($effects, fn($e) => ($e['weight'] ?? 0) > 0);

        if (empty($positiveEffects)) {
            return 0.0;
        }

        $opportunityScore = 0.0;
        $maxPossibleOpportunity = 0.0;

        foreach ($positiveEffects as $effect) {
            $weight = $effect['weight'];
            $confidence = $effect['confidence'] ?? 0.7;
            $angleClass = $effect['angle_class'] ?? 'precession_90';
            $angleWeight = self::ANGLE_WEIGHTS[$angleClass] ?? 1.0;

            // Los efectos a 90° (precesión pura) tienen mayor valor de oportunidad
            $precessionBonus = $angleClass === 'precession_90' ? 1.3 : 1.0;

            $opportunityContribution = $weight * $confidence * $angleWeight * $precessionBonus;

            $opportunityScore += $opportunityContribution;
            $maxPossibleOpportunity += $weight * self::ANGLE_WEIGHTS['precession_90'] * 1.3;
        }

        // Normalizar
        if ($maxPossibleOpportunity == 0) {
            return 0.0;
        }

        $normalizedOpportunity = $opportunityScore / $maxPossibleOpportunity;

        return round(min(1.0, max(0.0, $normalizedOpportunity)), 4);
    }

    // =========================================================================
    // INVESTMENT SCORE
    // =========================================================================

    /**
     * Calcular Investment Score compuesto
     *
     * Score integral para evaluación de inversión que combina:
     * - Precession Score (40%)
     * - Financial Score (30%)
     * - Compliance Score (20%)
     * - Location Score (10%)
     *
     * @param array $copropiedadData Datos de la copropiedad
     * @param array $precessionAnalysis Resultado del análisis precesional
     * @return array [score, nivel_riesgo, recomendacion, horizonte, breakdown]
     */
    public function calculateInvestmentScore(
        array $copropiedadData,
        array $precessionAnalysis
    ): array {
        // Obtener pesos de configuración
        $weights = $this->config['weights'] ?? [
            'precession' => 0.40,
            'financial' => 0.30,
            'compliance' => 0.20,
            'location' => 0.10,
        ];

        // Calcular componentes
        $precessionScore = $this->calculatePrecessionScore(
            $precessionAnalysis['effects'] ?? []
        );

        $financialScore = $this->calculateFinancialScore($copropiedadData);
        $complianceScore = $this->extractComplianceScore($copropiedadData);
        $locationScore = $this->calculateLocationScore($copropiedadData);

        // Score compuesto
        $compositeScore = 
            ($precessionScore / 100) * $weights['precession'] +
            ($financialScore / 100) * $weights['financial'] +
            ($complianceScore / 100) * $weights['compliance'] +
            ($locationScore / 100) * $weights['location'];

        $compositeScore = round($compositeScore * 100, 2);

        // Determinar nivel de riesgo
        $riskScore = $this->calculateRiskScore($precessionAnalysis['effects'] ?? []);
        $riskLevel = $this->determineRiskLevel($riskScore, $compositeScore);

        // Generar recomendación
        $recommendation = $this->generateRecommendation(
            $compositeScore,
            $riskLevel,
            $precessionAnalysis
        );

        // Determinar horizonte óptimo
        $horizon = $this->determineOptimalHorizon($precessionAnalysis);

        return [
            'score' => $compositeScore,
            'nivel_riesgo' => $riskLevel,
            'recomendacion' => $recommendation,
            'horizonte_meses' => $horizon,
            'breakdown' => [
                'precession' => [
                    'score' => $precessionScore,
                    'weight' => $weights['precession'],
                    'contribution' => round($precessionScore * $weights['precession'] / 100, 2),
                ],
                'financial' => [
                    'score' => $financialScore,
                    'weight' => $weights['financial'],
                    'contribution' => round($financialScore * $weights['financial'] / 100, 2),
                ],
                'compliance' => [
                    'score' => $complianceScore,
                    'weight' => $weights['compliance'],
                    'contribution' => round($complianceScore * $weights['compliance'] / 100, 2),
                ],
                'location' => [
                    'score' => $locationScore,
                    'weight' => $weights['location'],
                    'contribution' => round($locationScore * $weights['location'] / 100, 2),
                ],
            ],
            'risk_score' => $riskScore,
            'opportunity_score' => $this->calculateOpportunityScore(
                $precessionAnalysis['effects'] ?? []
            ),
        ];
    }

    /**
     * Calcular Financial Score
     *
     * @param array $data Datos de la copropiedad
     * @return float Score 0-100
     */
    protected function calculateFinancialScore(array $data): float
    {
        $score = 50.0; // Base

        // Morosidad (inverso)
        $morosidad = $data['indice_morosidad'] ?? $data['morosidad'] ?? 0;
        if ($morosidad <= 5) {
            $score += 20;
        } elseif ($morosidad <= 15) {
            $score += 10;
        } elseif ($morosidad > 30) {
            $score -= 20;
        }

        // Gasto común vs promedio zona
        $gastoComun = $data['gasto_comun_promedio'] ?? 0;
        $gastoZona = $data['gasto_zona_promedio'] ?? $gastoComun;
        if ($gastoZona > 0) {
            $ratio = $gastoComun / $gastoZona;
            if ($ratio < 0.9) {
                $score += 15; // Más eficiente
            } elseif ($ratio > 1.2) {
                $score -= 10; // Menos eficiente
            }
        }

        // Vacancia
        $vacancia = $data['tasa_vacancia'] ?? 0;
        if ($vacancia <= 5) {
            $score += 15;
        } elseif ($vacancia <= 10) {
            $score += 5;
        } elseif ($vacancia > 20) {
            $score -= 15;
        }

        // Yield (si disponible)
        $yield = $data['gross_yield'] ?? $data['yield'] ?? null;
        if ($yield !== null) {
            if ($yield >= 6) {
                $score += 10;
            } elseif ($yield >= 4) {
                $score += 5;
            } elseif ($yield < 3) {
                $score -= 5;
            }
        }

        return min(100, max(0, $score));
    }

    /**
     * Extraer Compliance Score
     *
     * @param array $data Datos de la copropiedad
     * @return float Score 0-100
     */
    protected function extractComplianceScore(array $data): float
    {
        // Si ya viene calculado
        if (isset($data['compliance_score'])) {
            return (float) $data['compliance_score'];
        }

        // Calcular desde componentes
        $score = 50.0;

        // DS7-2025
        $ds7Score = $data['ds7_score'] ?? $data['ds7_2025_score'] ?? null;
        if ($ds7Score !== null) {
            $score = ($score + $ds7Score) / 2;
        }

        // Ley 21.442
        $ley21442Status = $data['ley_21442_status'] ?? $data['ley21442_status'] ?? null;
        if ($ley21442Status === 'cumple') {
            $score += 20;
        } elseif ($ley21442Status === 'parcial') {
            $score += 5;
        } elseif ($ley21442Status === 'incumple') {
            $score -= 20;
        }

        // Brechas críticas
        $brechasCriticas = $data['critical_gaps'] ?? $data['brechas_criticas'] ?? 0;
        $score -= $brechasCriticas * 5;

        return min(100, max(0, $score));
    }

    /**
     * Calcular Location Score
     *
     * @param array $data Datos de la copropiedad
     * @return float Score 0-100
     */
    protected function calculateLocationScore(array $data): float
    {
        $score = 50.0;

        // Valor del suelo relativo a zona
        $valorM2 = $data['valor_suelo_m2'] ?? $data['valor_m2'] ?? 0;
        $valorZona = $data['valor_zona_m2'] ?? $valorM2;
        if ($valorZona > 0) {
            $ratio = $valorM2 / $valorZona;
            if ($ratio >= 0.9 && $ratio <= 1.1) {
                $score += 15; // Precio justo
            } elseif ($ratio < 0.8) {
                $score += 20; // Subvalorado (oportunidad)
            } elseif ($ratio > 1.3) {
                $score -= 10; // Sobrevalorado
            }
        }

        // Cobertura de equipamiento
        $equipamiento = $data['cobertura_equipamiento'] ?? $data['equipamiento_score'] ?? 50;
        if ($equipamiento >= 80) {
            $score += 15;
        } elseif ($equipamiento >= 60) {
            $score += 5;
        } elseif ($equipamiento < 40) {
            $score -= 10;
        }

        // Tendencia de permisos de edificación (proxy de desarrollo)
        $permisosVar = $data['variacion_permisos'] ?? $data['trend_permisos'] ?? 0;
        if ($permisosVar > 10) {
            $score += 10; // Zona en desarrollo
        } elseif ($permisosVar < -10) {
            $score -= 5; // Zona estancada
        }

        // Densidad poblacional
        $densidad = $data['densidad_poblacional'] ?? null;
        if ($densidad !== null) {
            if ($densidad >= 5000 && $densidad <= 15000) {
                $score += 5; // Densidad óptima
            }
        }

        return min(100, max(0, $score));
    }

    // =========================================================================
    // COMPARACIÓN
    // =========================================================================

    /**
     * Comparar copropiedades por scores precesionales
     *
     * @param array $copropiedadesData Array de [id => [data, analysis]]
     * @return array Rankings y análisis diferencial
     */
    public function compareCopropiedades(array $copropiedadesData): array
    {
        $scores = [];
        $rankings = [];

        foreach ($copropiedadesData as $id => $item) {
            $data = $item['data'] ?? [];
            $analysis = $item['analysis'] ?? [];

            $investmentScore = $this->calculateInvestmentScore($data, $analysis);

            $scores[$id] = [
                'copropiedad_id' => $id,
                'nombre' => $data['nombre'] ?? "Copropiedad $id",
                'precession_score' => $this->calculatePrecessionScore($analysis['effects'] ?? []),
                'risk_score' => $investmentScore['risk_score'],
                'opportunity_score' => $investmentScore['opportunity_score'],
                'investment_score' => $investmentScore['score'],
                'nivel_riesgo' => $investmentScore['nivel_riesgo'],
                'recomendacion' => $investmentScore['recomendacion'],
                'breakdown' => $investmentScore['breakdown'],
            ];
        }

        // Generar rankings
        $rankings['by_investment'] = $this->rankBy($scores, 'investment_score', 'desc');
        $rankings['by_precession'] = $this->rankBy($scores, 'precession_score', 'desc');
        $rankings['by_risk'] = $this->rankBy($scores, 'risk_score', 'asc');
        $rankings['by_opportunity'] = $this->rankBy($scores, 'opportunity_score', 'desc');

        // Análisis diferencial
        $differential = $this->calculateDifferential($scores);

        return [
            'scores' => $scores,
            'rankings' => $rankings,
            'differential' => $differential,
            'summary' => [
                'best_investment' => $rankings['by_investment'][0] ?? null,
                'lowest_risk' => $rankings['by_risk'][0] ?? null,
                'highest_opportunity' => $rankings['by_opportunity'][0] ?? null,
                'avg_investment_score' => $this->average(array_column($scores, 'investment_score')),
                'avg_risk_score' => $this->average(array_column($scores, 'risk_score')),
            ],
        ];
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    /**
     * Normalización sigmoide
     *
     * @param float $value
     * @param float $center
     * @param float $steepness
     * @return float
     */
    protected function sigmoidNormalize(float $value, float $center, float $steepness): float
    {
        return 100 / (1 + exp(-($value - $center) / $steepness));
    }

    /**
     * Calcular decay temporal
     *
     * @param int $lagMonths
     * @return float
     */
    protected function calculateTimeDecay(int $lagMonths): float
    {
        // Efectos a corto plazo tienen más peso en riesgo
        // decay = 1 / (1 + lag/12)
        return 1 / (1 + $lagMonths / 12);
    }

    /**
     * Determinar nivel de riesgo
     *
     * @param float $riskScore
     * @param float $compositeScore
     * @return string
     */
    protected function determineRiskLevel(float $riskScore, float $compositeScore): string
    {
        if ($riskScore >= 0.7) {
            return 'muy_alto';
        }
        if ($riskScore >= 0.5) {
            return 'alto';
        }
        if ($riskScore >= 0.3) {
            if ($compositeScore < 50) {
                return 'alto';
            }
            return 'moderado';
        }
        if ($riskScore >= 0.15) {
            return 'bajo';
        }
        return 'muy_bajo';
    }

    /**
     * Generar recomendación
     *
     * @param float $score
     * @param string $riskLevel
     * @param array $analysis
     * @return string
     */
    protected function generateRecommendation(
        float $score,
        string $riskLevel,
        array $analysis
    ): string {
        $opportunityScore = $this->calculateOpportunityScore($analysis['effects'] ?? []);

        if ($score >= 75 && in_array($riskLevel, ['muy_bajo', 'bajo'])) {
            return 'Inversión recomendada con alto potencial precesional';
        }

        if ($score >= 60 && $opportunityScore >= 0.6) {
            return 'Inversión atractiva con oportunidades de valorización';
        }

        if ($score >= 50 && $riskLevel === 'moderado') {
            return 'Inversión viable con monitoreo de factores de riesgo';
        }

        if ($riskLevel === 'alto' || $riskLevel === 'muy_alto') {
            return 'Precaución: alto riesgo identificado, requiere análisis profundo';
        }

        if ($score < 40) {
            return 'No recomendado: bajo potencial y/o riesgos elevados';
        }

        return 'Evaluación neutral: considerar factores adicionales';
    }

    /**
     * Determinar horizonte óptimo de inversión
     *
     * @param array $analysis
     * @return int Meses
     */
    protected function determineOptimalHorizon(array $analysis): int
    {
        $effects = $analysis['effects'] ?? [];
        
        if (empty($effects)) {
            return 24; // Default
        }

        // Encontrar el punto donde se maximizan los efectos positivos
        $positiveEffects = array_filter($effects, fn($e) => ($e['weight'] ?? 0) > 0);
        
        if (empty($positiveEffects)) {
            return 12; // Corto plazo si no hay efectos positivos
        }

        // Ponderar por peso y lag
        $weightedSum = 0;
        $totalWeight = 0;

        foreach ($positiveEffects as $effect) {
            $weight = $effect['weight'];
            $lag = $effect['total_lag_months'] ?? $effect['lag_months'] ?? 12;
            $weightedSum += $lag * $weight;
            $totalWeight += $weight;
        }

        $optimalHorizon = $totalWeight > 0 
            ? (int) round($weightedSum / $totalWeight)
            : 24;

        // Redondear a múltiplos de 6 meses
        return max(6, min(60, round($optimalHorizon / 6) * 6));
    }

    /**
     * Rankear por campo
     *
     * @param array $scores
     * @param string $field
     * @param string $order 'asc' o 'desc'
     * @return array
     */
    protected function rankBy(array $scores, string $field, string $order = 'desc'): array
    {
        $sorted = $scores;
        usort($sorted, function ($a, $b) use ($field, $order) {
            $comparison = $a[$field] <=> $b[$field];
            return $order === 'desc' ? -$comparison : $comparison;
        });

        return array_map(fn($s) => $s['copropiedad_id'], $sorted);
    }

    /**
     * Calcular diferencial entre copropiedades
     *
     * @param array $scores
     * @return array
     */
    protected function calculateDifferential(array $scores): array
    {
        if (count($scores) < 2) {
            return [];
        }

        $ids = array_keys($scores);
        $differential = [];

        for ($i = 0; $i < count($ids); $i++) {
            for ($j = $i + 1; $j < count($ids); $j++) {
                $id1 = $ids[$i];
                $id2 = $ids[$j];

                $differential["{$id1}_vs_{$id2}"] = [
                    'investment_diff' => round(
                        $scores[$id1]['investment_score'] - $scores[$id2]['investment_score'],
                        2
                    ),
                    'risk_diff' => round(
                        $scores[$id1]['risk_score'] - $scores[$id2]['risk_score'],
                        4
                    ),
                    'opportunity_diff' => round(
                        $scores[$id1]['opportunity_score'] - $scores[$id2]['opportunity_score'],
                        4
                    ),
                    'better_investment' => $scores[$id1]['investment_score'] > $scores[$id2]['investment_score']
                        ? $id1 : $id2,
                    'lower_risk' => $scores[$id1]['risk_score'] < $scores[$id2]['risk_score']
                        ? $id1 : $id2,
                ];
            }
        }

        return $differential;
    }

    /**
     * Calcular promedio
     *
     * @param array $values
     * @return float
     */
    protected function average(array $values): float
    {
        if (empty($values)) {
            return 0.0;
        }
        return round(array_sum($values) / count($values), 2);
    }
}
