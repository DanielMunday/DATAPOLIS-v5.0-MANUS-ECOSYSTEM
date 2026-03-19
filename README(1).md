# DATAPOLIS v3.0

## Plataforma PropTech/FinTech/RegTech/GovTech

### Inicio Rápido

```bash
# 1. Validar completitud
bash scripts/validate_100_percent.sh

# 2. Desplegar localmente
# Ver docs/DEPLOY_LOCAL.md

# 3. Desplegar en cPanel
# Ver docs/DEPLOY_CPANEL.md
```

### Estructura

```
DATAPOLIS_100/
├── backend/
│   ├── fastapi/          # API ML/Analytics (Python)
│   │   ├── openapi.yaml  # Especificación OpenAPI 3.0
│   │   ├── requirements.txt
│   │   └── routers/      # 29 módulos
│   └── laravel/          # API CRUD/PAE (PHP)
│       └── composer.json
├── frontend/             # Vue.js 3 + Leaflet
├── docs/                 # Documentación completa
├── scripts/              # Build y validación
├── tests/                # Tests E2E
└── ci/                   # GitHub Actions
```

### Documentación

| Documento | Descripción |
|-----------|-------------|
| `docs/ARCHITECTURE.md` | Arquitectura técnica |
| `docs/API_REFERENCE.md` | Referencia de 450+ endpoints |
| `docs/DEPLOY_LOCAL.md` | Guía de instalación local |
| `docs/DEPLOY_CPANEL.md` | Guía para cPanel |
| `docs/INVERSORES_PRESENTACION.md` | Pitch para inversores |
| `docs/CLIENTES_MANUAL_OPERATIVO.md` | Manual de usuario |
| `docs/REGULADOR_CMF_514_CUMPLIMIENTO.md` | Cumplimiento normativo |

### Licencia

Proprietary - DATAPOLIS SpA © 2026
