<?php

declare(strict_types=1);

namespace App\Services\PAE;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION ML CONNECTOR
 * Conector ML con Ollama y Fallback PHP Nativo
 * =========================================================================
 *
 * Proporciona capacidades de predicción ML para el análisis precesional:
 * - Conexión HTTP a Ollama local para predicciones narrativas
 * - Predicciones estadísticas básicas en PHP (regresión lineal,
 *   medias móviles, tendencias) como fallback
 * - NO reemplaza modelos ML pesados (XGBoost, Prophet, LSTM) pero
 *   provee funcionalidad autónoma cuando Ollama no está disponible
 *
 * @package App\Services\PAE
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionMLConnector
{
    /**
     * Configuración del conector
     * @var array
     */
    protected array $config;

    /**
     * Cache key para disponibilidad de Ollama
     */
    protected const OLLAMA_HEALTH_CACHE_KEY = 'pae:ollama:health';
    protected const OLLAMA_HEALTH_TTL = 60; // segundos

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->config = config('datapolis.pae.ml', [
            'ollama_url' => env('OLLAMA_URL', 'http://localhost:11434'),
            'ollama_model_analysis' => env('OLLAMA_MODEL', 'qwen2.5:7b'),
            'ollama_model_narrative' => 'llama3.2:8b',
            'fallback_enabled' => true,
            'timeout' => 30,
        ]);
    }

    // =========================================================================
    // OLLAMA PREDICTIONS
    // =========================================================================

    /**
     * Generar predicción con Ollama
     *
     * @param string $prompt Prompt para el modelo
     * @param array $context Contexto adicional
     * @param string|null $model Modelo específico a usar
     * @return string|null Respuesta del modelo o null si falla
     */
    public function predictWithOllama(
        string $prompt,
        array $context = [],
        ?string $model = null
    ): ?string {
        if (!$this->isOllamaAvailable()) {
            Log::debug('PrecessionMLConnector: Ollama no disponible');
            return null;
        }

        $model = $model ?? $this->config['ollama_model_analysis'];
        $url = rtrim($this->config['ollama_url'], '/') . '/api/generate';

        // Construir prompt con contexto
        $fullPrompt = $this->buildPromptWithContext($prompt, $context);

        try {
            $response = Http::timeout($this->config['timeout'])
                ->post($url, [
                    'model' => $model,
                    'prompt' => $fullPrompt,
                    'stream' => false,
                    'options' => [
                        'temperature' => 0.7,
                        'top_p' => 0.9,
                        'num_predict' => 500,
                    ],
                ]);

            if ($response->successful()) {
                $data = $response->json();
                return $data['response'] ?? null;
            }

            Log::warning('PrecessionMLConnector: Ollama response error', [
                'status' => $response->status(),
                'body' => $response->body(),
            ]);

            return null;

        } catch (\Exception $e) {
            Log::error('PrecessionMLConnector: Ollama request failed', [
                'error' => $e->getMessage(),
            ]);
            return null;
        }
    }

    /**
     * Verificar disponibilidad de Ollama
     *
     * @return bool
     */
    public function isOllamaAvailable(): bool
    {
        return Cache::remember(
            self::OLLAMA_HEALTH_CACHE_KEY,
            self::OLLAMA_HEALTH_TTL,
            function () {
                try {
                    $url = rtrim($this->config['ollama_url'], '/') . '/api/tags';
                    $response = Http::timeout(5)->get($url);
                    return $response->successful();
                } catch (\Exception $e) {
                    return false;
                }
            }
        );
    }

    /**
     * Construir prompt con contexto
     *
     * @param string $prompt
     * @param array $context
     * @return string
     */
    protected function buildPromptWithContext(string $prompt, array $context): string
    {
        if (empty($context)) {
            return $prompt;
        }

        $contextStr = "Contexto:\n";
        foreach ($context as $key => $value) {
            if (is_array($value)) {
                $value = json_encode($value, JSON_UNESCAPED_UNICODE);
            }
            $contextStr .= "- {$key}: {$value}\n";
        }

        return $contextStr . "\n" . $prompt;
    }

    // =========================================================================
    // PREDICCIONES ESTADÍSTICAS (FALLBACK PHP)
    // =========================================================================

    /**
     * Predecir tendencia usando estadísticas básicas
     *
     * Implementa regresión lineal simple y media móvil exponencial
     * como fallback cuando Ollama no está disponible.
     *
     * @param array $historicalData Array de valores históricos [fecha => valor]
     * @param int $horizonMonths Meses a predecir
     * @return array [valor_predicho, intervalo_confianza, tendencia, metodo]
     */
    public function predictTrend(array $historicalData, int $horizonMonths = 12): array
    {
        if (empty($historicalData) || count($historicalData) < 3) {
            return $this->emptyPrediction();
        }

        // Convertir a array numérico indexado
        $values = array_values($historicalData);
        $n = count($values);

        // Calcular regresión lineal
        $regression = $this->linearRegression($values);

        // Calcular media móvil exponencial
        $ema = $this->exponentialMovingAverage($values, min(6, $n));

        // Predecir valor futuro
        $predictedValue = $regression['intercept'] + $regression['slope'] * ($n + $horizonMonths);

        // Ajustar con EMA (blend)
        $blendedPrediction = 0.7 * $predictedValue + 0.3 * $ema;

        // Calcular intervalo de confianza (basado en error estándar)
        $stdError = $this->calculateStdError($values, $regression);
        $confidenceMargin = 1.96 * $stdError * sqrt(1 + 1/$n + pow($horizonMonths, 2) / $regression['ss_x']);

        // Determinar tendencia
        $trend = $this->determineTrend($regression['slope'], $values);

        return [
            'valor_predicho' => round($blendedPrediction, 2),
            'intervalo_confianza' => [
                'inferior' => round($blendedPrediction - $confidenceMargin, 2),
                'superior' => round($blendedPrediction + $confidenceMargin, 2),
            ],
            'tendencia' => $trend,
            'confianza' => $this->calculateConfidence($regression['r_squared'], $n),
            'metodo' => 'linear_regression_ema_blend',
            'parametros' => [
                'slope' => round($regression['slope'], 6),
                'intercept' => round($regression['intercept'], 2),
                'r_squared' => round($regression['r_squared'], 4),
                'n_observaciones' => $n,
                'horizonte_meses' => $horizonMonths,
            ],
        ];
    }

    /**
     * Predecir morosidad usando heurísticas
     *
     * @param array $copropiedadData Datos de la copropiedad
     * @return array [prediccion, factores, riesgo, confianza]
     */
    public function predictMorosidad(array $copropiedadData): array
    {
        // Extraer variables relevantes
        $valorSuelo = $copropiedadData['valor_suelo_m2'] ?? 0;
        $gastoComun = $copropiedadData['gasto_comun_promedio'] ?? 0;
        $complianceScore = $copropiedadData['compliance_score'] ?? 50;
        $antiguedad = $copropiedadData['antiguedad_edificacion'] ?? 10;
        $morosidadActual = $copropiedadData['indice_morosidad'] ?? 10;
        $vacancia = $copropiedadData['tasa_vacancia'] ?? 5;

        // Heurísticas del dominio
        $factores = [];
        $riskScore = 0.0;

        // Regla 1: valor_suelo ↑ + gasto_comun ↑ = morosidad ↑
        if ($valorSuelo > 50 && $gastoComun > 3) { // UF/m² y UF/mes
            $riskScore += 0.2;
            $factores[] = 'Alto valor de suelo con gastos comunes elevados';
        }

        // Regla 2: compliance_score ↑ = morosidad ↓
        if ($complianceScore >= 80) {
            $riskScore -= 0.15;
            $factores[] = 'Alto compliance reduce riesgo de morosidad';
        } elseif ($complianceScore < 50) {
            $riskScore += 0.15;
            $factores[] = 'Bajo compliance aumenta riesgo de morosidad';
        }

        // Regla 3: antiguedad ↑ + sin_mantenimiento = morosidad ↑
        if ($antiguedad > 20) {
            $riskScore += 0.1;
            $factores[] = 'Edificio antiguo con potencial de mayores gastos';
        }

        // Regla 4: vacancia alta correlaciona con morosidad
        if ($vacancia > 15) {
            $riskScore += 0.2;
            $factores[] = 'Alta vacancia indica posible deterioro';
        }

        // Regla 5: morosidad actual como predictor
        if ($morosidadActual > 20) {
            $riskScore += 0.25;
            $factores[] = 'Morosidad histórica alta';
        } elseif ($morosidadActual < 5) {
            $riskScore -= 0.1;
            $factores[] = 'Historial de baja morosidad';
        }

        // Normalizar riskScore
        $riskScore = max(0, min(1, 0.3 + $riskScore)); // Base 30%

        // Predecir morosidad futura
        $prediccionMorosidad = $morosidadActual * (1 + $riskScore * 0.3);
        $prediccionMorosidad = min(50, max(0, $prediccionMorosidad));

        return [
            'prediccion_morosidad_12m' => round($prediccionMorosidad, 2),
            'riesgo_incremento' => round($riskScore, 4),
            'factores' => $factores,
            'confianza' => 0.65, // Heurísticas tienen confianza moderada
            'recomendaciones' => $this->generateMorosidadRecommendations($riskScore, $factores),
        ];
    }

    /**
     * Generar narrativa del análisis
     *
     * @param array $analysis Resultado del análisis precesional
     * @return string Narrativa en español
     */
    public function generateNarrative(array $analysis): string
    {
        // Intentar con Ollama primero
        if ($this->isOllamaAvailable()) {
            $prompt = $this->buildNarrativePrompt($analysis);
            $narrative = $this->predictWithOllama(
                $prompt,
                [],
                $this->config['ollama_model_narrative']
            );

            if ($narrative) {
                return $narrative;
            }
        }

        // Fallback: generar narrativa basada en templates
        return $this->generateTemplateNarrative($analysis);
    }

    // =========================================================================
    // HELPERS ESTADÍSTICOS
    // =========================================================================

    /**
     * Regresión lineal simple
     *
     * @param array $values
     * @return array [slope, intercept, r_squared, ss_x]
     */
    protected function linearRegression(array $values): array
    {
        $n = count($values);
        if ($n < 2) {
            return ['slope' => 0, 'intercept' => $values[0] ?? 0, 'r_squared' => 0, 'ss_x' => 1];
        }

        // X = índice (0, 1, 2, ..., n-1)
        $sumX = 0;
        $sumY = 0;
        $sumXY = 0;
        $sumX2 = 0;
        $sumY2 = 0;

        for ($i = 0; $i < $n; $i++) {
            $x = $i;
            $y = $values[$i];
            $sumX += $x;
            $sumY += $y;
            $sumXY += $x * $y;
            $sumX2 += $x * $x;
            $sumY2 += $y * $y;
        }

        $meanX = $sumX / $n;
        $meanY = $sumY / $n;

        $ss_xy = $sumXY - $n * $meanX * $meanY;
        $ss_x = $sumX2 - $n * $meanX * $meanX;
        $ss_y = $sumY2 - $n * $meanY * $meanY;

        if ($ss_x == 0) {
            return ['slope' => 0, 'intercept' => $meanY, 'r_squared' => 0, 'ss_x' => 1];
        }

        $slope = $ss_xy / $ss_x;
        $intercept = $meanY - $slope * $meanX;

        // R-squared
        $ss_res = 0;
        $ss_tot = 0;
        for ($i = 0; $i < $n; $i++) {
            $predicted = $intercept + $slope * $i;
            $ss_res += pow($values[$i] - $predicted, 2);
            $ss_tot += pow($values[$i] - $meanY, 2);
        }
        $r_squared = $ss_tot > 0 ? 1 - ($ss_res / $ss_tot) : 0;

        return [
            'slope' => $slope,
            'intercept' => $intercept,
            'r_squared' => max(0, $r_squared),
            'ss_x' => $ss_x > 0 ? $ss_x : 1,
        ];
    }

    /**
     * Media móvil exponencial
     *
     * @param array $values
     * @param int $period
     * @return float
     */
    protected function exponentialMovingAverage(array $values, int $period): float
    {
        if (empty($values)) {
            return 0;
        }

        $alpha = 2 / ($period + 1);
        $ema = $values[0];

        for ($i = 1; $i < count($values); $i++) {
            $ema = $alpha * $values[$i] + (1 - $alpha) * $ema;
        }

        return $ema;
    }

    /**
     * Calcular error estándar de la regresión
     *
     * @param array $values
     * @param array $regression
     * @return float
     */
    protected function calculateStdError(array $values, array $regression): float
    {
        $n = count($values);
        if ($n <= 2) {
            return 0;
        }

        $sumSquaredErrors = 0;
        for ($i = 0; $i < $n; $i++) {
            $predicted = $regression['intercept'] + $regression['slope'] * $i;
            $sumSquaredErrors += pow($values[$i] - $predicted, 2);
        }

        return sqrt($sumSquaredErrors / ($n - 2));
    }

    /**
     * Determinar tendencia
     *
     * @param float $slope
     * @param array $values
     * @return string
     */
    protected function determineTrend(float $slope, array $values): string
    {
        if (empty($values)) {
            return 'indeterminada';
        }

        $mean = array_sum($values) / count($values);
        $percentChange = $mean > 0 ? ($slope * 12 / $mean) * 100 : 0;

        if ($percentChange > 5) {
            return 'creciente';
        }
        if ($percentChange < -5) {
            return 'decreciente';
        }
        return 'estable';
    }

    /**
     * Calcular confianza de la predicción
     *
     * @param float $rSquared
     * @param int $n
     * @return float
     */
    protected function calculateConfidence(float $rSquared, int $n): float
    {
        // Ajustar R² por tamaño de muestra
        $adjustedR = $rSquared * (1 - 1 / max(1, $n - 2));
        
        // Penalizar muestras pequeñas
        $sizeFactor = min(1, $n / 12);
        
        return round($adjustedR * $sizeFactor, 4);
    }

    // =========================================================================
    // NARRATIVA
    // =========================================================================

    /**
     * Construir prompt para narrativa
     *
     * @param array $analysis
     * @return string
     */
    protected function buildNarrativePrompt(array $analysis): string
    {
        $intervention = $analysis['intervention'] ?? [];
        $metrics = $analysis['metrics'] ?? [];
        
        return "Genera un análisis precesional conciso en español para una copropiedad. 
        
Intervención: {$intervention['node_name']} con magnitud {$intervention['magnitude']}.
Efectos totales: {$metrics['total_effects']}, positivos: {$metrics['positive_effects']}, negativos: {$metrics['negative_effects']}.
Confianza promedio: {$metrics['avg_confidence']}.

Escribe 2-3 párrafos explicando los efectos precesionales principales, usando la teoría de Fuller 
(efectos perpendiculares a la causa). Menciona los horizontes temporales relevantes.";
    }

    /**
     * Generar narrativa basada en templates
     *
     * @param array $analysis
     * @return string
     */
    protected function generateTemplateNarrative(array $analysis): string
    {
        $intervention = $analysis['intervention'] ?? [];
        $metrics = $analysis['metrics'] ?? [];
        $effectsByAngle = $analysis['effects_by_angle'] ?? [];

        $nodeName = $intervention['node_name'] ?? 'la variable';
        $totalEffects = $metrics['total_effects'] ?? 0;
        $positiveEffects = $metrics['positive_effects'] ?? 0;
        $negativeEffects = $metrics['negative_effects'] ?? 0;

        // Contar efectos por ángulo
        $precessionCount = count($effectsByAngle['precession_90'] ?? []);
        $inducedCount = count($effectsByAngle['induced_45'] ?? []);

        $narrative = "El análisis precesional de {$nodeName} revela un total de {$totalEffects} efectos proyectados. ";

        if ($positiveEffects > $negativeEffects) {
            $narrative .= "La intervención presenta un balance favorable con {$positiveEffects} efectos positivos frente a {$negativeEffects} negativos. ";
        } elseif ($negativeEffects > $positiveEffects) {
            $narrative .= "Se identifican {$negativeEffects} efectos negativos que requieren atención, superando los {$positiveEffects} positivos. ";
        } else {
            $narrative .= "El balance entre efectos positivos ({$positiveEffects}) y negativos ({$negativeEffects}) es equilibrado. ";
        }

        if ($precessionCount > 0) {
            $narrative .= "Siguiendo la teoría de Fuller, se detectaron {$precessionCount} efectos precesionales puros (90°), ";
            $narrative .= "que representan impactos perpendiculares a la causa original. ";
        }

        if ($inducedCount > 0) {
            $narrative .= "Adicionalmente, {$inducedCount} efectos inducidos (45°) complementan el análisis. ";
        }

        $avgConfidence = $metrics['avg_confidence'] ?? 0;
        if ($avgConfidence >= 0.7) {
            $narrative .= "El nivel de confianza promedio es alto ({$avgConfidence}), indicando robustez en las proyecciones.";
        } else {
            $narrative .= "La confianza promedio ({$avgConfidence}) sugiere monitorear la evolución de los indicadores.";
        }

        return $narrative;
    }

    /**
     * Generar recomendaciones para morosidad
     *
     * @param float $riskScore
     * @param array $factores
     * @return array
     */
    protected function generateMorosidadRecommendations(float $riskScore, array $factores): array
    {
        $recommendations = [];

        if ($riskScore >= 0.6) {
            $recommendations[] = 'Implementar plan de cobranza preventiva';
            $recommendations[] = 'Revisar estructura de gastos comunes';
        }

        if ($riskScore >= 0.4) {
            $recommendations[] = 'Fortalecer comunicación con copropietarios';
            $recommendations[] = 'Evaluar opciones de pago diferido';
        }

        if (in_array('Bajo compliance aumenta riesgo de morosidad', $factores)) {
            $recommendations[] = 'Priorizar regularización normativa (DS7-2025, Ley 21.442)';
        }

        if (in_array('Edificio antiguo con potencial de mayores gastos', $factores)) {
            $recommendations[] = 'Establecer fondo de reserva para mantención mayor';
        }

        if (empty($recommendations)) {
            $recommendations[] = 'Mantener políticas actuales de gestión';
        }

        return $recommendations;
    }

    /**
     * Predicción vacía
     *
     * @return array
     */
    protected function emptyPrediction(): array
    {
        return [
            'valor_predicho' => null,
            'intervalo_confianza' => ['inferior' => null, 'superior' => null],
            'tendencia' => 'indeterminada',
            'confianza' => 0,
            'metodo' => 'insufficient_data',
            'parametros' => [],
        ];
    }

    /**
     * Forzar refresh del health check de Ollama
     *
     * @return bool
     */
    public function refreshOllamaHealth(): bool
    {
        Cache::forget(self::OLLAMA_HEALTH_CACHE_KEY);
        return $this->isOllamaAvailable();
    }
}
