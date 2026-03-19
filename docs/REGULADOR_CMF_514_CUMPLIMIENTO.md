# DATAPOLIS v3.0 - Documento de Cumplimiento Regulatorio

## NCG 514, Ley 21.713, Basel IV

---

## Índice

1. [Introducción](#1-introducción)
2. [NCG 514 - Open Finance](#2-ncg-514---open-finance)
3. [Ley 21.713 - Plusvalías Urbanas](#3-ley-21713---plusvalías-urbanas)
4. [Basel IV - Framework Regulatorio](#4-basel-iv---framework-regulatorio)
5. [Mapa de Evidencia](#5-mapa-de-evidencia)
6. [Auditoría y Trazabilidad](#6-auditoría-y-trazabilidad)

---

## 1. Introducción

### Propósito del Documento

Este documento detalla cómo DATAPOLIS v3.0 cumple con los requisitos regulatorios aplicables al mercado financiero e inmobiliario chileno, específicamente:

- **NCG 514 CMF**: Norma de Sistema de Finanzas Abiertas (Open Finance)
- **Ley 21.713**: Impuesto a las Plusvalías de Bienes Raíces
- **Basel IV**: Marco regulatorio para riesgo crediticio y capital

### Alcance

| Regulación | Módulos Relacionados | Estado |
|------------|---------------------|--------|
| NCG 514 | M01-OF (Open Finance) | ✅ Implementado |
| Ley 21.713 | GT-PV (Plusvalías) | ✅ Implementado |
| Basel IV | M03, M04, M13, M16 | ✅ Implementado |

---

## 2. NCG 514 - Open Finance

### 2.1 Resumen de la Norma

La NCG 514 de la CMF establece el marco para el Sistema de Finanzas Abiertas en Chile, permitiendo el intercambio seguro de información financiera entre instituciones autorizadas.

### 2.2 Requisitos y Cumplimiento

#### 2.2.1 Interfaces de Programación (APIs)

| Requisito NCG 514 | Implementación DATAPOLIS | Evidencia |
|-------------------|-------------------------|-----------|
| APIs RESTful estandarizadas | OpenAPI 3.0 specification | `backend/fastapi/openapi.yaml` |
| Versionamiento de APIs | `/api/v1/` prefix | `backend/*/routes/` |
| Documentación técnica | Swagger/OpenAPI | `/api/docs` endpoint |
| Códigos de respuesta HTTP | Estándares REST | Ver schemas en openapi.yaml |

#### 2.2.2 Seguridad (FAPI 2.0)

| Requisito | Implementación | Archivo/Carpeta |
|-----------|----------------|-----------------|
| **OAuth 2.0** | Authorization Code Flow con PKCE | `fintech_ncg514/ncg514_fapi_security.py` |
| **mTLS** | Mutual TLS obligatorio para producción | Kong Gateway config |
| **JWT** | Tokens firmados con RS256 | `app/Services/AuthService.php` |
| **Consentimiento** | Gestión completa de lifecycle | `/open-finance/consent/*` endpoints |
| **Token binding** | Certificate-bound tokens | FAPI 2.0 compliant |

**Código de referencia - FAPI Security:**

```python
# backend/fastapi/fintech_ncg514/ncg514_fapi_security.py

class FAPI2SecurityProvider:
    """
    Implementación de FAPI 2.0 Security Profile según NCG 514
    """
    
    def validate_mtls(self, certificate: X509Certificate) -> bool:
        """Valida certificado cliente mTLS"""
        # Verifica cadena de confianza
        # Verifica vigencia
        # Verifica CN/SAN contra directorio CMF
        pass
    
    def create_access_token(self, client_id: str, scope: List[str]) -> str:
        """Genera token de acceso certificate-bound"""
        # Token vinculado al certificado cliente
        # Tiempo de vida máximo 15 minutos
        pass
    
    def validate_consent(self, consent_id: str) -> ConsentStatus:
        """Valida estado de consentimiento"""
        # Verifica expiración
        # Verifica permisos otorgados
        # Verifica revocación
        pass
```

#### 2.2.3 Endpoints Implementados

| Endpoint | Método | Descripción | Permisos Requeridos |
|----------|--------|-------------|---------------------|
| `/open-finance/consent` | POST | Crear consentimiento | N/A (inicio de flujo) |
| `/open-finance/consent/{id}` | GET | Estado de consentimiento | accounts:read |
| `/open-finance/consent/{id}` | DELETE | Revocar consentimiento | accounts:read |
| `/open-finance/accounts` | GET | Listar cuentas | accounts:read |
| `/open-finance/accounts/{id}/balances` | GET | Saldos de cuenta | balances:read |
| `/open-finance/accounts/{id}/transactions` | GET | Transacciones | transactions:read |
| `/open-finance/payments` | POST | Iniciar pago (PIS) | payments:write |
| `/open-finance/directorio` | GET | Participantes | N/A |

#### 2.2.4 Logging y Auditoría

```python
# Estructura de log de auditoría NCG 514
{
    "timestamp": "2026-02-07T12:00:00Z",
    "event_type": "CONSENT_CREATED",
    "consent_id": "consent_abc123",
    "client_id": "fintech_xyz",
    "user_id": "user_123",
    "permissions": ["accounts:read", "balances:read"],
    "ip_address": "192.168.1.100",
    "certificate_thumbprint": "SHA256:abc...",
    "result": "SUCCESS"
}
```

**Retención**: Logs conservados por 5 años según requisito CMF.

**Ubicación**: `backend/fastapi/logs/openfinance_audit.log`

#### 2.2.5 Directorio de Participantes

```python
# backend/fastapi/fintech_ncg514/ncg514_directorio_participantes.py

class DirectorioParticipantes:
    """
    Consulta al directorio centralizado de participantes CMF
    """
    
    def get_participant(self, org_id: str) -> Participant:
        """Obtiene datos de participante registrado"""
        pass
    
    def validate_participant(self, certificate: X509Certificate) -> bool:
        """Valida que certificado pertenece a participante autorizado"""
        pass
    
    def get_api_endpoints(self, org_id: str, api_type: str) -> List[str]:
        """Obtiene endpoints publicados por participante"""
        pass
```

### 2.3 Proceso de Certificación

| Fase | Estado | Fecha Estimada |
|------|--------|---------------|
| Desarrollo APIs | ✅ Completado | - |
| Sandbox testing | 🔄 En proceso | Q1 2026 |
| Auditoría externa | ⏳ Pendiente | Q2 2026 |
| Certificación CMF | ⏳ Pendiente | Q2 2026 |
| Producción | ⏳ Pendiente | Q3 2026 |

---

## 3. Ley 21.713 - Plusvalías Urbanas

### 3.1 Resumen de la Ley

La Ley 21.713 establece un impuesto sobre el mayor valor (plusvalía) que experimentan los bienes raíces producto de obras públicas o modificaciones al plan regulador.

### 3.2 Requisitos y Cumplimiento

#### 3.2.1 Cálculo de Plusvalía

```python
# backend/fastapi/services/m06_plusvalia.py

class PlusvaliaCalculator:
    """
    Cálculo de plusvalía según Ley 21.713
    """
    
    def calculate(self, propiedad_id: int, params: PlusvaliaParams) -> PlusvaliaResult:
        """
        Calcula plusvalía considerando:
        - Valor de adquisición original (UF)
        - Valor actual (avalúo ML o fiscal)
        - Mejoras realizadas (deducibles)
        - Inflación (ajuste IPC)
        - Exenciones aplicables
        """
        
        # 1. Obtener valores
        valor_adquisicion = self.get_valor_adquisicion(propiedad_id, params.fecha_adquisicion)
        valor_actual = self.get_valor_actual(propiedad_id)
        mejoras = self.get_mejoras_deducibles(propiedad_id)
        
        # 2. Ajustar por inflación
        valor_adquisicion_ajustado = self.ajustar_ipc(valor_adquisicion, params.fecha_adquisicion)
        
        # 3. Calcular plusvalía bruta
        plusvalia_bruta = valor_actual - valor_adquisicion_ajustado - mejoras
        
        # 4. Verificar exenciones
        exencion = self.verificar_exenciones(propiedad_id, plusvalia_bruta)
        
        # 5. Calcular impuesto
        if exencion.aplicable:
            impuesto = 0
        else:
            tasa = self.get_tasa_vigente()
            impuesto = plusvalia_bruta * tasa
        
        return PlusvaliaResult(
            plusvalia_uf=plusvalia_bruta,
            impuesto_uf=impuesto,
            tasa_aplicada=tasa,
            exento=exencion.aplicable,
            motivo_exencion=exencion.motivo
        )
```

#### 3.2.2 Exenciones Implementadas

| Exención | Código | Validación |
|----------|--------|------------|
| Vivienda única habitada por propietario | EX-001 | Cruce con SII |
| Plusvalía < 100 UTM | EX-002 | Cálculo automático |
| Herencia en línea directa | EX-003 | Documento notarial |
| Propiedad DFL-2 | EX-004 | Consulta Conservador |

#### 3.2.3 Integración con SII

```python
# Flujo de declaración y pago

1. Usuario calcula plusvalía en DATAPOLIS
2. Sistema genera borrador de declaración
3. Usuario revisa y confirma
4. Sistema envía a SII vía API (cuando disponible)
   O genera PDF para presentación manual
5. Sistema registra número de declaración
6. Sistema hace seguimiento de pago
```

#### 3.2.4 Auditoría de Cálculos

Cada cálculo de plusvalía genera un registro auditable:

```json
{
    "calculo_id": "PV-2026-00001",
    "propiedad_id": 12345,
    "usuario_id": 67890,
    "timestamp": "2026-02-07T12:00:00Z",
    "parametros_entrada": {
        "fecha_adquisicion": "2020-01-15",
        "valor_adquisicion_uf": 3500,
        "mejoras_uf": 200
    },
    "resultado": {
        "plusvalia_uf": 1200,
        "impuesto_uf": 120,
        "tasa": 0.10,
        "exento": false
    },
    "version_algoritmo": "1.0.3",
    "hash_integridad": "sha256:abc123..."
}
```

### 3.3 Endpoints Plusvalía

| Endpoint | Descripción |
|----------|-------------|
| `POST /plusvalias/calcular` | Calcular plusvalía |
| `GET /plusvalias/{id}` | Detalle de cálculo |
| `POST /plusvalias/simular` | Simular escenarios |
| `POST /plusvalias/declaracion` | Generar declaración |
| `GET /plusvalias/zonas-afectas` | Zonas con plusvalía activa |
| `GET /plusvalias/obras-publicas` | Obras que generan plusvalía |

---

## 4. Basel IV - Framework Regulatorio

### 4.1 Resumen del Marco

Basel IV establece requisitos de capital y gestión de riesgo para instituciones financieras. DATAPOLIS implementa componentes clave para análisis de riesgo inmobiliario.

### 4.2 Componentes Implementados

#### 4.2.1 Credit Scoring (M03)

```python
# backend/fastapi/services/m03_credit_score.py

class BaselIVCreditScoring:
    """
    Scoring crediticio conforme a Basel IV
    """
    
    def calculate_pd(self, entity_id: int) -> float:
        """
        Probability of Default
        - Modelo: XGBoost + Logistic Regression ensemble
        - Variables: historial pago, ratio deuda/ingreso, antigüedad
        - Calibración: datos históricos Chile 2015-2025
        """
        pass
    
    def calculate_lgd(self, entity_id: int, garantia_id: int) -> float:
        """
        Loss Given Default
        - Considera tipo y valor de garantía
        - Haircuts según categoría de activo
        - LTV (Loan-to-Value)
        """
        pass
    
    def calculate_ead(self, exposure_id: int) -> float:
        """
        Exposure at Default
        - Monto comprometido
        - Factor de conversión crediticia
        """
        pass
    
    def calculate_rwa(self, pd: float, lgd: float, ead: float) -> float:
        """
        Risk Weighted Assets según CR-SA
        - Fórmula estándar Basel IV
        - Output floor aplicado
        """
        k = self.capital_requirement(pd, lgd)
        rwa = k * 12.5 * ead
        return rwa
```

#### 4.2.2 Valorización (M04)

| Método | Uso | Modelo |
|--------|-----|--------|
| ML Ensemble | Valoración rápida | XGBoost + LightGBM + RF |
| Hedónico | Análisis de variables | Regresión multivariada |
| Comparables | Validación | K-nearest neighbors |
| Costo | Propiedades nuevas | Depreciación + terreno |

```python
# backend/fastapi/services/m04_valorizacion.py

class ValorizacionBaselIV:
    """
    Valorización de activos para colateral Basel IV
    """
    
    def avaluo_ml(self, propiedad_id: int) -> AvaluoResult:
        """
        Avalúo con modelo ML ensemble
        - Intervalo de confianza 95%
        - Variables: ubicación, superficie, antigüedad, estado
        - Actualización: mensual con datos de mercado
        """
        pass
    
    def haircut_calculation(self, tipo_activo: str, ltv: float) -> float:
        """
        Cálculo de haircut según tipo de activo
        - Residencial: 20-35%
        - Comercial: 30-50%
        - Terreno: 40-60%
        """
        pass
```

#### 4.2.3 Motor Regulatorio Basel IV (M16)

```python
# backend/fastapi/routers/basel.py

@router.post("/basel/validate")
async def validate_basel_iv(request: BaselValidationRequest) -> BaselValidationResult:
    """
    Validación completa de cumplimiento Basel IV
    
    Incluye:
    - CR-SA (Credit Risk Standardised Approach)
    - Output floor (72.5% a 2028)
    - Requerimientos de capital
    - Buffers de conservación
    """
    
    # 1. Calcular RWA por CR-SA
    rwa_crsa = calculate_crsa_rwa(request)
    
    # 2. Aplicar output floor
    rwa_final = max(rwa_crsa, rwa_irb * 0.725)
    
    # 3. Calcular capital requerido
    capital_required = rwa_final * 0.08  # Mínimo 8%
    
    # 4. Agregar buffers
    capital_with_buffers = capital_required * 1.025  # Conservation buffer
    
    # 5. Verificar cumplimiento
    compliant = available_capital >= capital_with_buffers
    
    return BaselValidationResult(
        rwa=rwa_final,
        capital_required=capital_with_buffers,
        compliant=compliant
    )
```

#### 4.2.4 Garantías (M13)

| Tipo Garantía | LGD Estándar | Haircut |
|---------------|--------------|---------|
| Hipoteca residencial | 25% | 20% |
| Hipoteca comercial | 35% | 30% |
| Prenda sobre vehículo | 45% | 40% |
| Fianza personal | 75% | N/A |

### 4.3 Articulación de Módulos

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO BASEL IV EN DATAPOLIS                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  M01 Propiedad ──► M04 Valorización ──► Valor Colateral        │
│        │                   │                    │               │
│        │                   ▼                    │               │
│        │          ┌─────────────────┐           │               │
│        │          │   Haircut       │           │               │
│        │          │   Aplicado      │           │               │
│        │          └────────┬────────┘           │               │
│        │                   │                    │               │
│        ▼                   ▼                    ▼               │
│  M03 Credit Score ──► M13 Garantía ──► M16 Basel IV            │
│        │                   │                    │               │
│    PD, LGD, EAD      LTV calculado         RWA final           │
│                                            Capital req.         │
│                                            Compliance ✓/✗       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Mapa de Evidencia

### 5.1 Archivos por Regulación

#### NCG 514 (Open Finance)

| Requisito | Archivo/Carpeta |
|-----------|-----------------|
| APIs FAPI 2.0 | `backend/fastapi/fintech_ncg514/` |
| Seguridad OAuth2 | `fintech_ncg514/ncg514_fapi_security.py` |
| Consentimiento | `routers/open_finance.py` |
| Directorio | `fintech_ncg514/ncg514_directorio_participantes.py` |
| ISO 20022 | `fintech_ncg514/ncg514_iso20022_messaging.py` |
| OpenAPI spec | `backend/fastapi/openapi.yaml` |
| Logs auditoría | `logs/openfinance_audit.log` |

#### Ley 21.713 (Plusvalías)

| Requisito | Archivo/Carpeta |
|-----------|-----------------|
| Cálculo plusvalía | `services/m06_plusvalia.py` |
| Router endpoints | `routers/plusvalia.py` |
| Exenciones | `services/m06_plusvalia.py:ExencionValidator` |
| Declaración | `services/m06_plusvalia.py:DeclaracionGenerator` |
| Zonas afectas | Integración con ÁGORA (M22) |

#### Basel IV

| Requisito | Archivo/Carpeta |
|-----------|-----------------|
| Credit Scoring | `services/m03_credit_score.py` |
| Valorización | `services/m04_valorizacion.py` |
| Garantías | Modelo `Garantia` en Laravel |
| Motor Basel IV | `routers/basel.py` |
| CR-SA | `services/m03_credit_score.py:CRSA` |

### 5.2 Tests de Cumplimiento

```bash
# Ejecutar tests específicos de cumplimiento
pytest tests/compliance/ -v

# Tests incluidos:
# - test_ncg514_consent_lifecycle.py
# - test_ncg514_fapi_security.py
# - test_plusvalia_calculation.py
# - test_plusvalia_exenciones.py
# - test_basel_iv_scoring.py
# - test_basel_iv_rwa.py
```

---

## 6. Auditoría y Trazabilidad

### 6.1 Logs de Auditoría

Todos los eventos sensibles generan logs estructurados:

```python
# Estructura estándar de log
{
    "timestamp": "ISO8601",
    "event_id": "UUID",
    "event_type": "ENUM",
    "user_id": "integer",
    "tenant_id": "integer",
    "ip_address": "string",
    "resource_type": "string",
    "resource_id": "string",
    "action": "string",
    "result": "SUCCESS|FAILURE",
    "details": "object",
    "hash_integridad": "SHA256"
}
```

### 6.2 Retención de Datos

| Tipo de Dato | Retención | Regulación |
|--------------|-----------|------------|
| Logs Open Finance | 5 años | NCG 514 |
| Cálculos plusvalía | 10 años | Ley 21.713 + SII |
| Scoring crediticio | 5 años | Basel IV |
| Transacciones | 6 años | Código Comercio |

### 6.3 Reportes para Regulador

| Reporte | Periodicidad | Destinatario |
|---------|--------------|--------------|
| Transacciones Open Finance | Mensual | CMF |
| Consentimientos activos | Trimestral | CMF |
| Incidentes de seguridad | Inmediato | CMF + CSIRT |
| Capital y RWA | Trimestral | CMF/SBIF |
| Plusvalías calculadas | Anual | SII |

---

## Certificación de Cumplimiento

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   DATAPOLIS v3.0 - DECLARACIÓN DE CUMPLIMIENTO               ║
║                                                               ║
║   Este documento certifica que la plataforma DATAPOLIS v3.0  ║
║   ha sido diseñada e implementada para cumplir con:          ║
║                                                               ║
║   ✅ NCG 514 CMF - Sistema de Finanzas Abiertas              ║
║   ✅ Ley 21.713 - Impuesto a las Plusvalías                  ║
║   ✅ Basel IV - Marco de Riesgo Crediticio                   ║
║                                                               ║
║   Versión: 3.0.0                                             ║
║   Fecha: 07 de Febrero de 2026                               ║
║                                                               ║
║   La certificación final requiere auditoría externa y        ║
║   aprobación de la CMF para producción Open Finance.         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Contacto Regulatorio

Para consultas de cumplimiento:

**DATAPOLIS SpA**
- Oficial de Cumplimiento: compliance@datapolis.cl
- Seguridad: security@datapolis.cl
- Legal: legal@datapolis.cl

---

**DATAPOLIS v3.0** | Documento de Cumplimiento Regulatorio | Febrero 2026
