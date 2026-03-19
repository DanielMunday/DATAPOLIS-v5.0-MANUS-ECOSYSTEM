# DATAPOLIS v3.0 - Sección Final para DEPLOY_LOCAL.md

## Agregar al final del documento existente:

---

## Verificación Rápida de 100%

Después de completar la instalación, ejecute el script de validación para confirmar que todo está correctamente configurado:

```bash
# Desde el directorio raíz del proyecto
chmod +x scripts/validate_100_percent.sh
bash scripts/validate_100_percent.sh
```

El script verificará:
- ✅ Existencia de todos los archivos requeridos
- ✅ Archivos de dependencias (requirements.txt, composer.json, package.json)
- ✅ Especificación OpenAPI
- ✅ Documentación completa
- ✅ Pipeline CI/CD
- ✅ Tests disponibles
- ✅ Health checks de servicios (si están corriendo)

### Salida esperada:

```
╔═══════════════════════════════════════════════════════════════╗
║       DATAPOLIS v3.0 - Validación 100% Completitud            ║
╚═══════════════════════════════════════════════════════════════╝

[1/6] Verificando artefactos de código...
  ✓ Backend FastAPI
  ✓ Backend Laravel
  ...

┌─────────────────────────────────────────────────────────────┐
│     ✓ VALIDACIÓN EXITOSA - 100% COMPLETITUD VERIFICADA      │
└─────────────────────────────────────────────────────────────┘
```

---

## Empaquetado para Distribución o Backup

Para crear un paquete ZIP listo para distribución o backup:

```bash
# Desde el directorio raíz del proyecto
chmod +x scripts/build_and_zip.sh
bash scripts/build_and_zip.sh
```

Esto generará `DATAPOLIS_v3_Full.zip` con:
- Backend FastAPI completo (incluyendo openapi.yaml)
- Backend Laravel completo
- Frontend Vue.js
- Documentación
- CI/CD
- Scripts
- Tests

### Verificar contenido del ZIP:

```bash
unzip -l DATAPOLIS_v3_Full.zip | head -30
```

---

## Health Checks Post-Instalación

### Verificar todos los servicios:

```bash
# FastAPI
curl http://localhost:8001/health
# Esperado: {"status":"healthy","version":"3.0.0"}

# Laravel
curl http://localhost:8000/api/v1/health
# Esperado: {"status":"healthy","version":"3.0.0"}

# PostgreSQL
psql -U datapolis -d datapolis_db -c "SELECT 1"

# Redis
redis-cli ping
# Esperado: PONG
```

### Script de verificación completa:

```bash
#!/bin/bash
echo "=== Health Check DATAPOLIS v3.0 ==="

# FastAPI
echo -n "FastAPI: "
curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null || echo "ERROR"

# Laravel
echo -n "Laravel: "
curl -s http://localhost:8000/api/v1/health | jq -r '.status' 2>/dev/null || echo "ERROR"

# PostgreSQL
echo -n "PostgreSQL: "
psql -U datapolis -d datapolis_db -c "SELECT 'OK'" -t 2>/dev/null | tr -d ' ' || echo "ERROR"

# Redis
echo -n "Redis: "
redis-cli ping 2>/dev/null || echo "ERROR"

echo "=== Verificación completada ==="
```

---

## Solución de Problemas Post-Instalación

### Si validate_100_percent.sh reporta errores:

1. **Archivo faltante**: Verifique que el paquete se extrajo completamente
2. **Test falla**: Revise configuración de base de datos en `.env`
3. **Health check falla**: Verifique que los servicios están corriendo

### Comandos útiles de diagnóstico:

```bash
# Ver logs de Laravel
tail -f /var/www/datapolis/backend/laravel/storage/logs/laravel.log

# Ver logs de FastAPI
journalctl -u datapolis-fastapi -f

# Ver estado de servicios
sudo systemctl status nginx php8.2-fpm datapolis-fastapi datapolis-queue

# Reiniciar todos los servicios
sudo systemctl restart nginx php8.2-fpm datapolis-fastapi datapolis-queue
```

---

## Próximos Pasos Post-Instalación

1. **Crear usuario administrador inicial**:
   ```bash
   cd backend/laravel
   php artisan tinker
   >>> User::create(['name'=>'Admin', 'email'=>'admin@datapolis.cl', 'password'=>bcrypt('admin123')])
   ```

2. **Verificar flujo E2E**:
   ```bash
   pytest tests/test_e2e.py -v
   ```

3. **Revisar documentación para inversores/clientes**:
   - `docs/INVERSORES_PRESENTACION.md`
   - `docs/CLIENTES_MANUAL_OPERATIVO.md`

4. **Para auditoría regulatoria**:
   - `docs/REGULADOR_CMF_514_CUMPLIMIENTO.md`

---

**DATAPOLIS v3.0** | Instalación Local Completa
