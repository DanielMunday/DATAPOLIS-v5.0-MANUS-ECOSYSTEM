<?php

declare(strict_types=1);

namespace App\Services\PAE;

use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;

/**
 * =========================================================================
 * PAE M11-DP - PRECESSION GRAPH ENGINE
 * Motor de Grafo Precesional Nativo PHP/Laravel
 * =========================================================================
 *
 * Implementación nativa del motor de análisis precesional basado en
 * la teoría de R. Buckminster Fuller. Grafo dirigido ponderado con
 * ontología territorial para análisis de efectos indirectos.
 *
 * ARQUITECTURA:
 * - Nodos: Variables urbanas/inmobiliarias (array asociativo)
 * - Aristas: Relaciones precesionales con ángulo, peso, lag, confianza
 * - Análisis: BFS desde intervención con clasificación por ángulo
 *
 * @package App\Services\PAE
 * @version 1.0.0
 * @author DATAPOLIS SpA
 */
class PrecessionGraphEngine
{
    /**
     * Nodos del grafo (array asociativo)
     * @var array<string, array>
     */
    protected array $nodes = [];

    /**
     * Aristas del grafo (lista de adyacencia)
     * @var array<string, array<array>>
     */
    protected array $edges = [];

    /**
     * Configuración del engine
     * @var array
     */
    protected array $config;

    /**
     * Ángulos precesionales de Fuller
     */
    public const ANGLE_DIRECT = 0;      // Efecto directo causa-efecto
    public const ANGLE_INDUCED = 45;    // Efectos inducidos correlacionados
    public const ANGLE_PRECESSION = 90; // Efecto perpendicular (core Fuller)
    public const ANGLE_SYSTEMIC = 135;  // Efectos sistémicos segundo orden
    public const ANGLE_COUNTER = 180;   // Retroalimentación inversa

    /**
     * Rangos de ángulos para clasificación
     */
    protected const ANGLE_RANGES = [
        self::ANGLE_DIRECT => [0, 22.5],
        self::ANGLE_INDUCED => [22.5, 67.5],
        self::ANGLE_PRECESSION => [67.5, 112.5],
        self::ANGLE_SYSTEMIC => [112.5, 157.5],
        self::ANGLE_COUNTER => [157.5, 180],
    ];

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->config = config('datapolis.pae.graph', [
            'max_depth' => 4,
            'default_time_horizon' => 60,
            'decay_factor' => 0.85,
        ]);

        $this->initializeBaseOntology();
    }

    // =========================================================================
    // GESTIÓN DE NODOS
    // =========================================================================

    /**
     * Agregar nodo al grafo
     *
     * @param string $id Identificador único del nodo
     * @param array $data Datos del nodo [name, type, source, description, unit, ...]
     * @return void
     */
    public function addNode(string $id, array $data): void
    {
        $this->nodes[$id] = array_merge([
            'id' => $id,
            'name' => $data['name'] ?? $id,
            'type' => $data['type'] ?? 'generic',
            'source' => $data['source'] ?? 'DATAPOLIS',
            'description' => $data['description'] ?? '',
            'unit' => $data['unit'] ?? null,
            'current_value' => $data['current_value'] ?? null,
            'created_at' => now()->toISOString(),
        ], $data);
    }

    /**
     * Obtener nodo por ID
     *
     * @param string $id
     * @return array|null
     */
    public function getNode(string $id): ?array
    {
        return $this->nodes[$id] ?? null;
    }

    /**
     * Verificar si existe nodo
     *
     * @param string $id
     * @return bool
     */
    public function hasNode(string $id): bool
    {
        return isset($this->nodes[$id]);
    }

    /**
     * Obtener todos los nodos
     *
     * @return array
     */
    public function getAllNodes(): array
    {
        return $this->nodes;
    }

    /**
     * Actualizar valor actual de un nodo
     *
     * @param string $id
     * @param mixed $value
     * @return void
     */
    public function updateNodeValue(string $id, mixed $value): void
    {
        if (isset($this->nodes[$id])) {
            $this->nodes[$id]['current_value'] = $value;
            $this->nodes[$id]['updated_at'] = now()->toISOString();
        }
    }

    // =========================================================================
    // GESTIÓN DE ARISTAS
    // =========================================================================

    /**
     * Agregar arista al grafo
     *
     * @param string $source Nodo origen
     * @param string $target Nodo destino
     * @param array $data [angle, weight, lag_months, confidence, description]
     * @return void
     */
    public function addEdge(string $source, string $target, array $data): void
    {
        if (!isset($this->edges[$source])) {
            $this->edges[$source] = [];
        }

        $this->edges[$source][] = [
            'source' => $source,
            'target' => $target,
            'angle' => $data['angle'] ?? self::ANGLE_PRECESSION,
            'weight' => $data['weight'] ?? 0.5,
            'lag_months' => $data['lag_months'] ?? 12,
            'confidence' => $data['confidence'] ?? 0.7,
            'description' => $data['description'] ?? '',
            'bidirectional' => $data['bidirectional'] ?? false,
        ];

        // Si es bidireccional, agregar arista inversa con ángulo complementario
        if ($data['bidirectional'] ?? false) {
            $inverseAngle = $this->calculateInverseAngle($data['angle'] ?? 90);
            if (!isset($this->edges[$target])) {
                $this->edges[$target] = [];
            }
            $this->edges[$target][] = [
                'source' => $target,
                'target' => $source,
                'angle' => $inverseAngle,
                'weight' => ($data['weight'] ?? 0.5) * 0.7, // Peso reducido en inversa
                'lag_months' => $data['lag_months'] ?? 12,
                'confidence' => ($data['confidence'] ?? 0.7) * 0.8,
                'description' => "Inverso: " . ($data['description'] ?? ''),
                'bidirectional' => false,
            ];
        }
    }

    /**
     * Obtener aristas salientes de un nodo
     *
     * @param string $nodeId
     * @return array
     */
    public function getOutgoingEdges(string $nodeId): array
    {
        return $this->edges[$nodeId] ?? [];
    }

    /**
     * Obtener aristas entrantes a un nodo
     *
     * @param string $nodeId
     * @return array
     */
    public function getIncomingEdges(string $nodeId): array
    {
        $incoming = [];
        foreach ($this->edges as $source => $edges) {
            foreach ($edges as $edge) {
                if ($edge['target'] === $nodeId) {
                    $incoming[] = $edge;
                }
            }
        }
        return $incoming;
    }

    // =========================================================================
    // ANÁLISIS PRECESIONAL
    // =========================================================================

    /**
     * Analizar efectos precesionales desde una intervención
     *
     * Implementa BFS desde el nodo de intervención, clasificando efectos
     * por ángulo precesional y calculando pesos acumulados con decay.
     *
     * @param array $intervention [node_id, magnitude, type]
     * @param int $maxDepth Profundidad máxima de exploración
     * @param int $timeHorizonMonths Horizonte temporal en meses
     * @return array Resultados estructurados por tipo de efecto
     */
    public function analyzePrecession(
        array $intervention,
        int $maxDepth = 4,
        int $timeHorizonMonths = 60
    ): array {
        $startTime = microtime(true);
        
        $nodeId = $intervention['node_id'] ?? null;
        $magnitude = $intervention['magnitude'] ?? 1.0;
        $interventionType = $intervention['type'] ?? 'generic';

        if (!$nodeId || !$this->hasNode($nodeId)) {
            return $this->emptyAnalysisResult();
        }

        $maxDepth = min($maxDepth, $this->config['max_depth']);
        $decayFactor = $this->config['decay_factor'];

        // Estructuras para BFS
        $visited = [];
        $effects = [];
        $queue = new \SplQueue();

        // Iniciar BFS desde el nodo de intervención
        $queue->enqueue([
            'node_id' => $nodeId,
            'depth' => 0,
            'accumulated_weight' => $magnitude,
            'accumulated_confidence' => 1.0,
            'path' => [$nodeId],
            'total_lag' => 0,
            'angle_chain' => [],
        ]);

        while (!$queue->isEmpty()) {
            $current = $queue->dequeue();
            $currentNodeId = $current['node_id'];
            $currentDepth = $current['depth'];

            // Control de profundidad
            if ($currentDepth >= $maxDepth) {
                continue;
            }

            // Control de visitas (permitir múltiples paths pero limitar)
            $visitKey = $currentNodeId . '_' . $currentDepth;
            if (isset($visited[$visitKey])) {
                continue;
            }
            $visited[$visitKey] = true;

            // Explorar aristas salientes
            $outgoingEdges = $this->getOutgoingEdges($currentNodeId);
            
            foreach ($outgoingEdges as $edge) {
                $targetId = $edge['target'];
                $lagMonths = $edge['lag_months'];

                // Filtrar por horizonte temporal
                $newTotalLag = $current['total_lag'] + $lagMonths;
                if ($newTotalLag > $timeHorizonMonths) {
                    continue;
                }

                // Calcular peso acumulado con decay
                $depthDecay = pow($decayFactor, $currentDepth + 1);
                $newWeight = $current['accumulated_weight'] * $edge['weight'] * $depthDecay;
                $newConfidence = $current['accumulated_confidence'] * $edge['confidence'];

                // Evitar efectos insignificantes
                if (abs($newWeight) < 0.01 || $newConfidence < 0.1) {
                    continue;
                }

                // Clasificar por ángulo
                $angleClass = $this->classifyAngle($edge['angle']);

                // Registrar efecto
                $effects[] = [
                    'source_node' => $currentNodeId,
                    'target_node' => $targetId,
                    'source_name' => $this->nodes[$currentNodeId]['name'] ?? $currentNodeId,
                    'target_name' => $this->nodes[$targetId]['name'] ?? $targetId,
                    'angle' => $edge['angle'],
                    'angle_class' => $angleClass,
                    'weight' => $newWeight,
                    'confidence' => $newConfidence,
                    'depth' => $currentDepth + 1,
                    'lag_months' => $lagMonths,
                    'total_lag_months' => $newTotalLag,
                    'path' => array_merge($current['path'], [$targetId]),
                    'description' => $edge['description'],
                    'effect_type' => $newWeight >= 0 ? 'positive' : 'negative',
                ];

                // Encolar para continuar BFS
                $queue->enqueue([
                    'node_id' => $targetId,
                    'depth' => $currentDepth + 1,
                    'accumulated_weight' => $newWeight,
                    'accumulated_confidence' => $newConfidence,
                    'path' => array_merge($current['path'], [$targetId]),
                    'total_lag' => $newTotalLag,
                    'angle_chain' => array_merge($current['angle_chain'], [$edge['angle']]),
                ]);
            }
        }

        // Agrupar efectos por ángulo
        $effectsByAngle = $this->groupEffectsByAngle($effects);

        // Calcular métricas agregadas
        $metrics = $this->calculateAggregateMetrics($effects, $effectsByAngle);

        $executionTime = (microtime(true) - $startTime) * 1000;

        return [
            'intervention' => [
                'node_id' => $nodeId,
                'node_name' => $this->nodes[$nodeId]['name'] ?? $nodeId,
                'magnitude' => $magnitude,
                'type' => $interventionType,
            ],
            'parameters' => [
                'max_depth' => $maxDepth,
                'time_horizon_months' => $timeHorizonMonths,
                'decay_factor' => $decayFactor,
            ],
            'effects' => $effects,
            'effects_by_angle' => $effectsByAngle,
            'metrics' => $metrics,
            'execution_time_ms' => round($executionTime, 2),
            'analyzed_at' => now()->toISOString(),
        ];
    }

    /**
     * Clasificar ángulo en categoría precesional
     *
     * @param float $angle
     * @return string
     */
    protected function classifyAngle(float $angle): string
    {
        $normalizedAngle = fmod($angle, 180);
        if ($normalizedAngle < 0) {
            $normalizedAngle += 180;
        }

        foreach (self::ANGLE_RANGES as $class => $range) {
            if ($normalizedAngle >= $range[0] && $normalizedAngle < $range[1]) {
                return $this->getAngleClassName($class);
            }
        }

        // Edge case para 180°
        if ($normalizedAngle >= 157.5) {
            return 'counter_180';
        }

        return 'precession_90';
    }

    /**
     * Obtener nombre de clase de ángulo
     *
     * @param int $angleClass
     * @return string
     */
    protected function getAngleClassName(int $angleClass): string
    {
        return match ($angleClass) {
            self::ANGLE_DIRECT => 'direct_0',
            self::ANGLE_INDUCED => 'induced_45',
            self::ANGLE_PRECESSION => 'precession_90',
            self::ANGLE_SYSTEMIC => 'systemic_135',
            self::ANGLE_COUNTER => 'counter_180',
            default => 'precession_90',
        };
    }

    /**
     * Agrupar efectos por ángulo
     *
     * @param array $effects
     * @return array
     */
    protected function groupEffectsByAngle(array $effects): array
    {
        $grouped = [
            'direct_0' => [],
            'induced_45' => [],
            'precession_90' => [],
            'systemic_135' => [],
            'counter_180' => [],
        ];

        foreach ($effects as $effect) {
            $angleClass = $effect['angle_class'];
            if (isset($grouped[$angleClass])) {
                $grouped[$angleClass][] = $effect;
            }
        }

        // Ordenar cada grupo por peso absoluto descendente
        foreach ($grouped as $angleClass => &$angleEffects) {
            usort($angleEffects, fn($a, $b) => abs($b['weight']) <=> abs($a['weight']));
        }

        return $grouped;
    }

    /**
     * Calcular métricas agregadas del análisis
     *
     * @param array $effects
     * @param array $effectsByAngle
     * @return array
     */
    protected function calculateAggregateMetrics(array $effects, array $effectsByAngle): array
    {
        if (empty($effects)) {
            return [
                'total_effects' => 0,
                'positive_effects' => 0,
                'negative_effects' => 0,
                'avg_confidence' => 0,
                'max_depth_reached' => 0,
                'effects_by_angle_count' => [],
                'total_weight_by_angle' => [],
            ];
        }

        $positiveCount = count(array_filter($effects, fn($e) => $e['weight'] >= 0));
        $negativeCount = count($effects) - $positiveCount;
        $avgConfidence = array_sum(array_column($effects, 'confidence')) / count($effects);
        $maxDepth = max(array_column($effects, 'depth'));

        $countByAngle = [];
        $weightByAngle = [];
        foreach ($effectsByAngle as $angleClass => $angleEffects) {
            $countByAngle[$angleClass] = count($angleEffects);
            $weightByAngle[$angleClass] = array_sum(array_column($angleEffects, 'weight'));
        }

        return [
            'total_effects' => count($effects),
            'positive_effects' => $positiveCount,
            'negative_effects' => $negativeCount,
            'avg_confidence' => round($avgConfidence, 4),
            'max_depth_reached' => $maxDepth,
            'effects_by_angle_count' => $countByAngle,
            'total_weight_by_angle' => $weightByAngle,
        ];
    }

    /**
     * Calcular multiplicador precesional
     *
     * El multiplicador representa el factor de amplificación total
     * de los efectos precesionales respecto a la intervención original.
     *
     * @param array $analysisResults
     * @return float
     */
    public function calculateMultiplier(array $analysisResults): float
    {
        if (empty($analysisResults['effects'])) {
            return 1.0;
        }

        $intervention = $analysisResults['intervention']['magnitude'] ?? 1.0;
        if ($intervention == 0) {
            return 1.0;
        }

        // Sumar pesos absolutos de todos los efectos
        $totalWeight = array_sum(array_map(
            fn($e) => abs($e['weight']),
            $analysisResults['effects']
        ));

        // Multiplicador = total efectos / intervención original
        // Ponderado por confianza promedio
        $avgConfidence = $analysisResults['metrics']['avg_confidence'] ?? 0.7;
        $multiplier = ($totalWeight / abs($intervention)) * $avgConfidence;

        return round(max(1.0, $multiplier), 4);
    }

    /**
     * Obtener nodos afectados por un nodo dado
     *
     * @param string $nodeId
     * @param int $depth
     * @return array
     */
    public function getAffectedNodes(string $nodeId, int $depth = 2): array
    {
        $affected = [];
        $visited = [];
        $queue = new \SplQueue();

        $queue->enqueue(['node' => $nodeId, 'depth' => 0]);

        while (!$queue->isEmpty()) {
            $current = $queue->dequeue();
            
            if ($current['depth'] >= $depth) {
                continue;
            }

            $edges = $this->getOutgoingEdges($current['node']);
            foreach ($edges as $edge) {
                $target = $edge['target'];
                if (!isset($visited[$target])) {
                    $visited[$target] = true;
                    $affected[] = [
                        'node_id' => $target,
                        'node_name' => $this->nodes[$target]['name'] ?? $target,
                        'depth' => $current['depth'] + 1,
                        'angle' => $edge['angle'],
                        'weight' => $edge['weight'],
                    ];
                    $queue->enqueue(['node' => $target, 'depth' => $current['depth'] + 1]);
                }
            }
        }

        return $affected;
    }

    // =========================================================================
    // ONTOLOGÍA
    // =========================================================================

    /**
     * Inicializar ontología base
     *
     * Carga los nodos y aristas predefinidos para el análisis
     * precesional urbano/inmobiliario.
     *
     * @return void
     */
    protected function initializeBaseOntology(): void
    {
        // =====================================================================
        // NODOS BASE (Variables territoriales e inmobiliarias)
        // =====================================================================

        // Fuentes externas (DOM, SII, INE, MINVU)
        $this->addNode('permisos_edificacion', [
            'name' => 'Permisos de Edificación',
            'type' => 'urban_metric',
            'source' => 'DOM',
            'description' => 'Permisos de edificación otorgados en la zona',
            'unit' => 'unidades/año',
        ]);

        $this->addNode('valor_suelo_m2', [
            'name' => 'Valor del Suelo',
            'type' => 'valuation',
            'source' => 'SII',
            'description' => 'Valor de mercado del suelo por metro cuadrado',
            'unit' => 'UF/m²',
        ]);

        $this->addNode('densidad_poblacional', [
            'name' => 'Densidad Poblacional',
            'type' => 'demographic',
            'source' => 'INE',
            'description' => 'Densidad de población en la zona',
            'unit' => 'hab/km²',
        ]);

        $this->addNode('cobertura_equipamiento', [
            'name' => 'Cobertura de Equipamiento',
            'type' => 'urban_metric',
            'source' => 'MINVU',
            'description' => 'Índice de cobertura de equipamiento urbano',
            'unit' => 'índice 0-100',
        ]);

        $this->addNode('antiguedad_edificacion', [
            'name' => 'Antigüedad de Edificación',
            'type' => 'building',
            'source' => 'DOM',
            'description' => 'Años desde la construcción del edificio',
            'unit' => 'años',
        ]);

        $this->addNode('calidad_construccion', [
            'name' => 'Calidad de Construcción',
            'type' => 'building',
            'source' => 'MINVU',
            'description' => 'Índice de calidad constructiva',
            'unit' => 'índice 1-5',
        ]);

        // Fuentes internas DATAPOLIS
        $this->addNode('indice_morosidad', [
            'name' => 'Índice de Morosidad',
            'type' => 'financial',
            'source' => 'DATAPOLIS',
            'description' => 'Tasa de morosidad en gastos comunes',
            'unit' => 'porcentaje',
        ]);

        $this->addNode('compliance_score', [
            'name' => 'Score de Compliance',
            'type' => 'compliance',
            'source' => 'DATAPOLIS',
            'description' => 'Puntaje de cumplimiento normativo (DS7, Ley 21.442)',
            'unit' => 'índice 0-100',
        ]);

        $this->addNode('gasto_comun_promedio', [
            'name' => 'Gasto Común Promedio',
            'type' => 'financial',
            'source' => 'DATAPOLIS',
            'description' => 'Gasto común mensual promedio por unidad',
            'unit' => 'UF/mes',
        ]);

        $this->addNode('tasa_vacancia', [
            'name' => 'Tasa de Vacancia',
            'type' => 'occupancy',
            'source' => 'DATAPOLIS',
            'description' => 'Porcentaje de unidades desocupadas',
            'unit' => 'porcentaje',
        ]);

        $this->addNode('indice_arriendo_m2', [
            'name' => 'Índice de Arriendo',
            'type' => 'rental',
            'source' => 'DATAPOLIS',
            'description' => 'Valor de arriendo promedio por m²',
            'unit' => 'UF/m²/mes',
        ]);

        $this->addNode('carga_tributaria', [
            'name' => 'Carga Tributaria',
            'type' => 'tax',
            'source' => 'SII/DATAPOLIS',
            'description' => 'Carga tributaria anual estimada',
            'unit' => 'UF/año',
        ]);

        // =====================================================================
        // ARISTAS BASE (Relaciones precesionales)
        // =====================================================================

        // permisos_edificacion → valor_suelo_m2 (45°, positivo)
        $this->addEdge('permisos_edificacion', 'valor_suelo_m2', [
            'angle' => 45,
            'weight' => 0.72,
            'lag_months' => 12,
            'confidence' => 0.85,
            'description' => 'Nuevos permisos aumentan expectativa de valor del suelo',
        ]);

        // permisos_edificacion → densidad_poblacional (90°, positivo)
        $this->addEdge('permisos_edificacion', 'densidad_poblacional', [
            'angle' => 90,
            'weight' => 0.65,
            'lag_months' => 24,
            'confidence' => 0.78,
            'description' => 'Construcción nueva aumenta densidad a mediano plazo',
        ]);

        // densidad_poblacional → cobertura_equipamiento (90°, positivo)
        $this->addEdge('densidad_poblacional', 'cobertura_equipamiento', [
            'angle' => 90,
            'weight' => 0.58,
            'lag_months' => 36,
            'confidence' => 0.72,
            'description' => 'Mayor densidad genera demanda de equipamiento',
        ]);

        // valor_suelo_m2 → indice_morosidad (180°, negativo)
        $this->addEdge('valor_suelo_m2', 'indice_morosidad', [
            'angle' => 180,
            'weight' => -0.45,
            'lag_months' => 18,
            'confidence' => 0.68,
            'description' => 'Mayor valor suelo correlaciona con menor morosidad (efecto inverso)',
        ]);

        // valor_suelo_m2 → indice_arriendo_m2 (45°, positivo)
        $this->addEdge('valor_suelo_m2', 'indice_arriendo_m2', [
            'angle' => 45,
            'weight' => 0.78,
            'lag_months' => 6,
            'confidence' => 0.82,
            'description' => 'Mayor valor suelo impulsa arriendos',
        ]);

        // valor_suelo_m2 → gasto_comun_promedio (90°, positivo)
        $this->addEdge('valor_suelo_m2', 'gasto_comun_promedio', [
            'angle' => 90,
            'weight' => 0.42,
            'lag_months' => 12,
            'confidence' => 0.65,
            'description' => 'Valorización genera mayor gasto en mantención',
        ]);

        // compliance_score → valor_suelo_m2 (90°, positivo)
        $this->addEdge('compliance_score', 'valor_suelo_m2', [
            'angle' => 90,
            'weight' => 0.35,
            'lag_months' => 18,
            'confidence' => 0.60,
            'description' => 'Mayor compliance aumenta valor percibido',
        ]);

        // carga_tributaria → indice_morosidad (45°, positivo)
        $this->addEdge('carga_tributaria', 'indice_morosidad', [
            'angle' => 45,
            'weight' => 0.55,
            'lag_months' => 6,
            'confidence' => 0.75,
            'description' => 'Mayor carga tributaria aumenta morosidad',
        ]);

        // antiguedad_edificacion → gasto_comun_promedio (45°, positivo)
        $this->addEdge('antiguedad_edificacion', 'gasto_comun_promedio', [
            'angle' => 45,
            'weight' => 0.48,
            'lag_months' => 12,
            'confidence' => 0.70,
            'description' => 'Edificios más antiguos requieren más mantención',
        ]);

        // tasa_vacancia → valor_suelo_m2 (180°, negativo)
        $this->addEdge('tasa_vacancia', 'valor_suelo_m2', [
            'angle' => 180,
            'weight' => -0.52,
            'lag_months' => 12,
            'confidence' => 0.72,
            'description' => 'Alta vacancia presiona valor a la baja',
        ]);

        // indice_morosidad → compliance_score (135°, negativo)
        $this->addEdge('indice_morosidad', 'compliance_score', [
            'angle' => 135,
            'weight' => -0.38,
            'lag_months' => 6,
            'confidence' => 0.65,
            'description' => 'Morosidad afecta capacidad de cumplimiento',
        ]);

        // gasto_comun_promedio → indice_morosidad (45°, positivo)
        $this->addEdge('gasto_comun_promedio', 'indice_morosidad', [
            'angle' => 45,
            'weight' => 0.40,
            'lag_months' => 3,
            'confidence' => 0.72,
            'description' => 'Gastos altos aumentan morosidad',
        ]);

        // cobertura_equipamiento → valor_suelo_m2 (45°, positivo)
        $this->addEdge('cobertura_equipamiento', 'valor_suelo_m2', [
            'angle' => 45,
            'weight' => 0.55,
            'lag_months' => 24,
            'confidence' => 0.68,
            'description' => 'Mejor equipamiento valoriza la zona',
        ]);

        // calidad_construccion → gasto_comun_promedio (180°, negativo)
        $this->addEdge('calidad_construccion', 'gasto_comun_promedio', [
            'angle' => 180,
            'weight' => -0.35,
            'lag_months' => 12,
            'confidence' => 0.62,
            'description' => 'Mejor calidad reduce gastos de mantención',
        ]);

        // calidad_construccion → valor_suelo_m2 (45°, positivo)
        $this->addEdge('calidad_construccion', 'valor_suelo_m2', [
            'angle' => 45,
            'weight' => 0.45,
            'lag_months' => 6,
            'confidence' => 0.75,
            'description' => 'Calidad constructiva aumenta valor',
        ]);

        Log::debug('PrecessionGraphEngine: Ontología base inicializada', [
            'nodes' => count($this->nodes),
            'edges' => array_sum(array_map('count', $this->edges)),
        ]);
    }

    /**
     * Exportar ontología para sincronización
     *
     * @return array
     */
    public function exportOntology(): array
    {
        return [
            'version' => '1.0.0',
            'source' => 'DATAPOLIS_PAE',
            'exported_at' => now()->toISOString(),
            'nodes' => $this->nodes,
            'edges' => $this->edges,
            'metadata' => [
                'total_nodes' => count($this->nodes),
                'total_edges' => array_sum(array_map('count', $this->edges)),
            ],
        ];
    }

    /**
     * Importar ontología desde fuente externa (e.g., ÁGORA)
     *
     * @param array $ontology
     * @param bool $merge Si true, combina con ontología existente
     * @return void
     */
    public function importOntology(array $ontology, bool $merge = true): void
    {
        if (!$merge) {
            $this->nodes = [];
            $this->edges = [];
        }

        // Importar nodos
        if (isset($ontology['nodes'])) {
            foreach ($ontology['nodes'] as $id => $data) {
                if (!isset($this->nodes[$id])) {
                    $this->nodes[$id] = array_merge($data, [
                        'imported_from' => $ontology['source'] ?? 'unknown',
                        'imported_at' => now()->toISOString(),
                    ]);
                }
            }
        }

        // Importar aristas
        if (isset($ontology['edges'])) {
            foreach ($ontology['edges'] as $source => $edges) {
                foreach ($edges as $edge) {
                    // Verificar que los nodos existan
                    if (isset($this->nodes[$source]) && isset($this->nodes[$edge['target']])) {
                        $this->addEdge($source, $edge['target'], $edge);
                    }
                }
            }
        }

        Log::info('PrecessionGraphEngine: Ontología importada', [
            'source' => $ontology['source'] ?? 'unknown',
            'nodes_imported' => count($ontology['nodes'] ?? []),
            'total_nodes' => count($this->nodes),
        ]);
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    /**
     * Calcular ángulo inverso
     *
     * @param float $angle
     * @return float
     */
    protected function calculateInverseAngle(float $angle): float
    {
        $inverse = 180 - $angle;
        return $inverse < 0 ? $inverse + 180 : $inverse;
    }

    /**
     * Resultado de análisis vacío
     *
     * @return array
     */
    protected function emptyAnalysisResult(): array
    {
        return [
            'intervention' => null,
            'parameters' => [],
            'effects' => [],
            'effects_by_angle' => [
                'direct_0' => [],
                'induced_45' => [],
                'precession_90' => [],
                'systemic_135' => [],
                'counter_180' => [],
            ],
            'metrics' => [
                'total_effects' => 0,
                'positive_effects' => 0,
                'negative_effects' => 0,
                'avg_confidence' => 0,
                'max_depth_reached' => 0,
                'effects_by_angle_count' => [],
                'total_weight_by_angle' => [],
            ],
            'execution_time_ms' => 0,
            'analyzed_at' => now()->toISOString(),
        ];
    }

    /**
     * Limpiar grafo
     *
     * @return void
     */
    public function clear(): void
    {
        $this->nodes = [];
        $this->edges = [];
    }

    /**
     * Recargar ontología base
     *
     * @return void
     */
    public function reload(): void
    {
        $this->clear();
        $this->initializeBaseOntology();
    }

    /**
     * Obtener estadísticas del grafo
     *
     * @return array
     */
    public function getStats(): array
    {
        $edgeCount = array_sum(array_map('count', $this->edges));
        $avgDegree = count($this->nodes) > 0 
            ? $edgeCount / count($this->nodes) 
            : 0;

        return [
            'total_nodes' => count($this->nodes),
            'total_edges' => $edgeCount,
            'average_degree' => round($avgDegree, 2),
            'sources' => array_unique(array_column($this->nodes, 'source')),
        ];
    }
}
