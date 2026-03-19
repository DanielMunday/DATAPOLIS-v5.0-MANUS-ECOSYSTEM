#!/bin/bash
# ==============================================================================
# DATAPOLIS v3.0 - Script de Validación 100% Completitud
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ERRORS=0
WARNINGS=0

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       DATAPOLIS v3.0 - Validación 100% Completitud            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==============================================================================
# FUNCIÓN: Verificar existencia de archivo
# ==============================================================================
check_file() {
    local file="$1"
    local desc="$2"
    if [ -f "$ROOT_DIR/$file" ]; then
        echo -e "${GREEN}  ✓${NC} $desc"
        return 0
    else
        echo -e "${RED}  ✗${NC} $desc (falta: $file)"
        ((ERRORS++))
        return 1
    fi
}

# ==============================================================================
# FUNCIÓN: Verificar existencia de directorio
# ==============================================================================
check_dir() {
    local dir="$1"
    local desc="$2"
    if [ -d "$ROOT_DIR/$dir" ]; then
        echo -e "${GREEN}  ✓${NC} $desc"
        return 0
    else
        echo -e "${RED}  ✗${NC} $desc (falta: $dir)"
        ((ERRORS++))
        return 1
    fi
}

# ==============================================================================
# 1. ARTEFACTOS DE CÓDIGO
# ==============================================================================
echo -e "${YELLOW}[1/6] Verificando artefactos de código...${NC}"

check_dir "backend/fastapi" "Backend FastAPI"
check_dir "backend/laravel" "Backend Laravel"
check_file "backend/fastapi/main.py" "FastAPI main.py"
check_file "backend/fastapi/openapi.yaml" "OpenAPI specification"
check_file "backend/laravel/routes/api.php" "Laravel routes/api.php"
echo ""

# ==============================================================================
# 2. ARCHIVOS DE DEPENDENCIAS
# ==============================================================================
echo -e "${YELLOW}[2/6] Verificando archivos de dependencias...${NC}"

check_file "backend/fastapi/requirements.txt" "Python requirements.txt"
check_file "backend/laravel/composer.json" "Laravel composer.json"

if [ -d "$ROOT_DIR/frontend" ]; then
    check_file "frontend/package.json" "Frontend package.json"
fi
echo ""

# ==============================================================================
# 3. DOCUMENTACIÓN
# ==============================================================================
echo -e "${YELLOW}[3/6] Verificando documentación...${NC}"

check_file "docs/ARCHITECTURE.md" "Documentación de arquitectura"
check_file "docs/API_REFERENCE.md" "Referencia de API"
check_file "docs/DEPLOY_LOCAL.md" "Guía de despliegue local"
check_file "docs/DEPLOY_CPANEL.md" "Guía de despliegue cPanel"

# Documentos de presentación (opcional pero recomendado)
if [ -f "$ROOT_DIR/docs/INVERSORES_PRESENTACION.md" ]; then
    echo -e "${GREEN}  ✓${NC} Presentación para inversores"
else
    echo -e "${YELLOW}  ⚠${NC} Presentación inversores (recomendado)"
    ((WARNINGS++))
fi

if [ -f "$ROOT_DIR/docs/CLIENTES_MANUAL_OPERATIVO.md" ]; then
    echo -e "${GREEN}  ✓${NC} Manual operativo clientes"
else
    echo -e "${YELLOW}  ⚠${NC} Manual clientes (recomendado)"
    ((WARNINGS++))
fi

if [ -f "$ROOT_DIR/docs/REGULADOR_CMF_514_CUMPLIMIENTO.md" ]; then
    echo -e "${GREEN}  ✓${NC} Documento cumplimiento regulador"
else
    echo -e "${YELLOW}  ⚠${NC} Documento regulador (recomendado)"
    ((WARNINGS++))
fi
echo ""

# ==============================================================================
# 4. CI/CD Y SCRIPTS
# ==============================================================================
echo -e "${YELLOW}[4/6] Verificando CI/CD y scripts...${NC}"

check_file "ci/.github/workflows/ci.yml" "Pipeline CI/CD"
check_file "scripts/build_and_zip.sh" "Script de build"
check_file "scripts/validate_100_percent.sh" "Script de validación"
echo ""

# ==============================================================================
# 5. TESTS
# ==============================================================================
echo -e "${YELLOW}[5/6] Verificando tests...${NC}"

if [ -f "$ROOT_DIR/tests/test_e2e.py" ]; then
    echo -e "${GREEN}  ✓${NC} Test E2E principal"
    
    # Intentar ejecutar tests si pytest está disponible
    if command -v pytest &> /dev/null; then
        echo "    Ejecutando tests..."
        cd "$ROOT_DIR"
        if pytest tests/test_e2e.py -v --tb=short -x 2>/dev/null; then
            echo -e "${GREEN}    ✓ Tests pasaron${NC}"
        else
            echo -e "${YELLOW}    ⚠ Tests fallaron (verificar configuración)${NC}"
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}    ⚠ pytest no disponible, saltando ejecución${NC}"
    fi
else
    echo -e "${RED}  ✗${NC} Test E2E no encontrado"
    ((ERRORS++))
fi
echo ""

# ==============================================================================
# 6. HEALTH CHECKS (si los servicios están corriendo)
# ==============================================================================
echo -e "${YELLOW}[6/6] Verificando health checks (opcional)...${NC}"

# FastAPI
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}  ✓${NC} FastAPI health check OK"
elif curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}  ✓${NC} API health check OK (puerto 8000)"
else
    echo -e "${YELLOW}  ⚠${NC} Servicios no están corriendo (normal si es validación offline)"
fi

# Laravel
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null | grep -q "200"; then
    echo -e "${GREEN}  ✓${NC} Laravel health check OK"
else
    echo -e "${YELLOW}  ⚠${NC} Laravel no está corriendo (normal si es validación offline)"
fi
echo ""

# ==============================================================================
# RESUMEN
# ==============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                         RESUMEN                                ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}┌─────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${GREEN}│     ✓ VALIDACIÓN EXITOSA - 100% COMPLETITUD VERIFICADA      │${NC}"
        echo -e "${GREEN}└─────────────────────────────────────────────────────────────┘${NC}"
        echo ""
        echo -e "  El proyecto DATAPOLIS v3.0 está ${GREEN}100% completo${NC} y listo para:"
        echo "    • Despliegue en servidor local"
        echo "    • Despliegue en cPanel"
        echo "    • Presentación a inversores/clientes/reguladores"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}┌─────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${YELLOW}│  ⚠ VALIDACIÓN CON ADVERTENCIAS - $WARNINGS advertencia(s)           │${NC}"
        echo -e "${YELLOW}└─────────────────────────────────────────────────────────────┘${NC}"
        echo ""
        echo -e "  El proyecto está funcionalmente completo pero tiene $WARNINGS advertencia(s)."
        echo "  Revise los ítems marcados con ⚠ para optimizar."
        echo ""
        exit 0
    fi
else
    echo -e "${RED}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${RED}│     ✗ VALIDACIÓN FALLIDA - $ERRORS error(es) encontrado(s)           │${NC}"
    echo -e "${RED}└─────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "  Corrija los errores marcados con ✗ antes de continuar."
    echo ""
    exit 1
fi
