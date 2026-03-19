# DATAPOLIS v3.0 - Sección Final para DEPLOY_CPANEL.md

## Agregar al final del documento existente:

---

## Post-Deploy: Verificación Rápida

Después de completar el despliegue en cPanel, realice las siguientes verificaciones:

### 1. Verificar Endpoints desde Navegador

| Endpoint | URL | Respuesta Esperada |
|----------|-----|-------------------|
| Health Laravel | `https://api.sudominio.com/api/v1/health` | `{"status":"healthy"}` |
| Swagger/Docs | `https://api.sudominio.com/api/docs` | Página Swagger UI |
| Frontend | `https://app.sudominio.com` | Página de login |

### 2. Verificar desde Terminal SSH

```bash
# Conectar via SSH
ssh usuario@sudominio.com

# Health check Laravel
curl -s https://api.sudominio.com/api/v1/health | jq .

# Verificar artisan
cd ~/datapolis/backend/laravel
php artisan --version

# Verificar migraciones
php artisan migrate:status

# Verificar base de datos
php artisan tinker
>>> DB::connection()->getPdo()
>>> exit
```

### 3. Test de Login Funcional

```bash
# Desde terminal o Postman
curl -X POST https://api.sudominio.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@datapolis.cl","password":"admin123"}'

# Respuesta esperada:
# {"access_token":"...","token_type":"Bearer","user":{...}}
```

---

## Rutas de Salud por Servicio

### Laravel (API Principal)

```
GET https://api.sudominio.com/api/v1/health
```

Respuesta:
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2026-02-07T12:00:00Z",
  "services": {
    "database": "connected",
    "cache": "connected",
    "queue": "running"
  }
}
```

### FastAPI (ML/Analytics) - Si está configurado

Si tiene FastAPI detrás de un proxy o subdominio dedicado:

```
GET https://ml.sudominio.com/health
```

O a través de proxy en Laravel:

```
GET https://api.sudominio.com/api/v1/ml/health
```

---

## Checklist Post-Deploy cPanel

| # | Verificación | Comando/Acción | Estado |
|---|--------------|----------------|--------|
| 1 | SSL activo | Verificar candado en navegador | ☐ |
| 2 | Laravel responde | `curl https://api.sudominio.com/api/v1/health` | ☐ |
| 3 | Frontend carga | Abrir `https://app.sudominio.com` | ☐ |
| 4 | Login funciona | Probar POST `/auth/login` | ☐ |
| 5 | Base de datos conectada | `php artisan migrate:status` | ☐ |
| 6 | Cron jobs configurados | Verificar en cPanel → Cron Jobs | ☐ |
| 7 | Permisos de storage | `chmod -R 755 storage` | ☐ |
| 8 | .env configurado | Variables de producción | ☐ |

---

## Validación de OpenAPI en cPanel

Si desea verificar que la especificación OpenAPI está accesible:

### Opción A: Servir openapi.yaml estático

```bash
# Copiar openapi.yaml al directorio público
cp ~/datapolis/backend/fastapi/openapi.yaml ~/api.sudominio.com/public/openapi.yaml
```

Acceder en: `https://api.sudominio.com/openapi.yaml`

### Opción B: Usar Swagger UI

1. Descargar Swagger UI desde GitHub
2. Subir a `~/api.sudominio.com/public/swagger/`
3. Configurar para apuntar a `/openapi.yaml`
4. Acceder en: `https://api.sudominio.com/swagger/`

---

## Monitoreo en cPanel

### Configurar Alertas de Uptime

1. Ir a **Métricas** → **Uptime Robot** (si disponible)
2. Agregar monitores para:
   - `https://api.sudominio.com/api/v1/health`
   - `https://app.sudominio.com`

### Revisar Logs de Error

1. Ir a **Métricas** → **Errors**
2. O directamente:
   ```bash
   tail -f ~/logs/api.sudominio.com.error.log
   ```

---

## Comandos Útiles Post-Deploy

```bash
# Limpiar caché de Laravel
cd ~/datapolis/backend/laravel
php artisan cache:clear
php artisan config:clear
php artisan route:clear
php artisan view:clear

# Optimizar para producción
php artisan config:cache
php artisan route:cache
php artisan view:cache

# Verificar cola de trabajos
php artisan queue:work --once

# Ver versión instalada
cat ~/datapolis/VERSION

# Verificar permisos
ls -la storage/
ls -la bootstrap/cache/
```

---

## Solución de Problemas cPanel

### Error 500
```bash
# Verificar permisos
chmod -R 755 storage bootstrap/cache
chown -R usuario:usuario storage bootstrap/cache

# Verificar .env
cat .env | grep APP_KEY
# Si está vacío: php artisan key:generate

# Ver log de errores
tail -50 storage/logs/laravel.log
```

### Error de Base de Datos
```bash
# Verificar conexión
php artisan tinker
>>> DB::connection()->getPdo()

# Si falla, verificar credenciales en .env
cat .env | grep DB_
```

### CORS Errors en Frontend
```bash
# Verificar .htaccess incluye headers CORS
cat public/.htaccess | grep -i cors

# Verificar APP_URL en .env
cat .env | grep APP_URL
```

---

## Documentación Adicional

Para uso operativo y presentaciones, consulte:

| Documento | Propósito |
|-----------|-----------|
| `docs/CLIENTES_MANUAL_OPERATIVO.md` | Manual para usuarios finales |
| `docs/INVERSORES_PRESENTACION.md` | Pitch para inversores |
| `docs/REGULADOR_CMF_514_CUMPLIMIENTO.md` | Cumplimiento regulatorio |
| `docs/CHECKLIST_100_PERCENT.md` | Verificación de completitud |

---

**DATAPOLIS v3.0** | Despliegue cPanel Completo
