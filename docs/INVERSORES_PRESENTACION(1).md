# DATAPOLIS v3.0 - Presentación para Inversores

## Plataforma PropTech/FinTech/RegTech Líder en Chile

---

## Resumen Ejecutivo

### El Problema

El mercado inmobiliario chileno enfrenta desafíos críticos:

- **Fragmentación de datos**: Información dispersa entre SII, CMF, BCCH, DOM, notarías
- **Cumplimiento regulatorio complejo**: NCG 514, Ley 21.713, Basel IV, Ley 21.442
- **Gestión ineficiente de copropiedades**: 2.5 millones de unidades sin herramientas adecuadas
- **Falta de análisis de riesgo**: Decisiones de inversión sin data confiable
- **Open Finance incipiente**: Chile aún sin ecosistema maduro

### La Solución: DATAPOLIS v3.0

Plataforma integral que unifica **PropTech + FinTech + RegTech + GovTech** en un solo ecosistema:

- **23 módulos funcionales** cubriendo todo el ciclo inmobiliario
- **450+ endpoints API** listos para integración
- **Compliance nativo** con regulación chilena vigente
- **Machine Learning** para valorización y scoring crediticio
- **Open Finance NCG 514** implementado con FAPI 2.0

---

## Diferenciadores Competitivos

| Factor | Competencia | DATAPOLIS |
|--------|-------------|-----------|
| Cobertura | Solo gestión básica | Ecosistema completo |
| Regulación | Manual / parcial | Automatizado / 100% |
| ML/AI | No | Valorización + Scoring |
| Open Finance | No | FAPI 2.0 ready |
| Análisis de riesgo | Básico | PAE Engine propietario |
| GIS / Territorial | No | ÁGORA GeoViewer integrado |

### Barreras de Entrada

1. **Complejidad técnica**: 150,000+ líneas de código especializado
2. **Conocimiento regulatorio**: 18 años de experiencia en urbanismo y finanzas
3. **Datos propietarios**: Ontología PAE y modelos ML entrenados
4. **Certificaciones**: En proceso de certificación CMF para Open Finance
5. **First-mover advantage**: Único en combinar todos los verticales

---

## Arquitectura Técnica (Alto Nivel)

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATAPOLIS v3.0                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   PROPTECH          FINTECH           REGTECH          GOVTECH  │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐      ┌────────┐│
│  │Expedient│      │Open Fin │       │ Basel   │      │ GIRES  ││
│  │Copropied│      │Credit   │       │ PAE     │      │ ÁGORA  ││
│  │Arriendos│      │Valoriz. │       │ Comply  │      │Plusval.││
│  └─────────┘      └─────────┘       └─────────┘      └────────┘│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Backend: FastAPI + Laravel │ DB: PostgreSQL + PostGIS + Redis  │
│  ML: XGBoost + LSTM         │ Security: mTLS + OAuth2 + JWT     │
└─────────────────────────────────────────────────────────────────┘
```

### Stack Tecnológico

- **Backend**: Python FastAPI (ML) + PHP Laravel (CRUD)
- **Frontend**: Vue.js 3 + TailwindCSS + Leaflet
- **Database**: PostgreSQL 15 + PostGIS 3.3 + Redis 7
- **ML**: XGBoost, LightGBM, LSTM, Scikit-learn
- **Infraestructura**: Compatible Docker, cPanel, VPS, Cloud

---

## Mercado Objetivo

### TAM (Total Addressable Market)

| Segmento | Unidades/Entidades | Potencial Anual |
|----------|-------------------|-----------------|
| Copropiedades Chile | 65,000+ edificios | USD 195M |
| Administradores | 2,500+ empresas | USD 75M |
| Bancos/Financieras | 50+ instituciones | USD 50M |
| Inversores inmobiliarios | 10,000+ fondos | USD 100M |
| Municipalidades | 346 comunas | USD 50M |
| **Total Chile** | | **USD 470M** |

### SAM (Serviceable Available Market)

Enfoque inicial: Región Metropolitana + grandes ciudades
- 25,000 copropiedades
- 1,000 administradores
- Potencial: **USD 150M**

### SOM (Serviceable Obtainable Market)

Objetivo año 1-3: Capturar 5-10% del SAM
- **Año 1**: USD 5M ARR
- **Año 2**: USD 15M ARR
- **Año 3**: USD 30M ARR

---

## Modelo de Negocio

### Streams de Revenue

| Producto | Pricing | Target |
|----------|---------|--------|
| **SaaS Copropiedades** | USD 50-200/mes/edificio | Administradores |
| **API Access** | USD 0.01-0.10/call | Desarrolladores |
| **Enterprise License** | USD 50K-200K/año | Bancos, Fondos |
| **Certificados Tributarios** | USD 5/certificado | Contribuyentes |
| **Open Finance Fees** | 0.1-0.5% transacción | Fintech |
| **Consulting/Setup** | USD 10K-50K proyecto | Grandes clientes |

### Unit Economics (Proyectado)

| Métrica | Valor |
|---------|-------|
| CAC (Customer Acquisition Cost) | USD 500 |
| LTV (Lifetime Value) | USD 5,000 |
| LTV/CAC Ratio | 10x |
| Gross Margin | 80% |
| Net Revenue Retention | 120% |

---

## Tracción y Validación

### Desarrollo Completado

✅ **100% del MVP construido** (verificable)
- 23 módulos funcionales
- 450+ endpoints API
- 150,000+ líneas de código
- Tests E2E pasando
- Documentación completa

### Validación de Mercado

- Piloto con I.M. Pudahuel (convenio CEPAL-UN)
- Análisis de 345 soluciones habitacionales SERVIU
- Tercer lugar Bloomberg Philanthropies Mayor Challenge
- Consultoría valoración para empresas del rubro

### Propiedad Intelectual

- Código fuente propietario (copyright registrable)
- Modelo PAE (Precession Analysis Engine) propietario
- Ontología de riesgo inmobiliario única
- Marca DATAPOLIS en proceso de registro

---

## Roadmap

### 2026 Q1-Q2: Launch
- ✅ Completar desarrollo 100%
- Certificación CMF para Open Finance
- 10 clientes piloto pagados
- Primera ronda seed

### 2026 Q3-Q4: Growth
- 100 clientes activos
- Integración SII automatizada
- App móvil v1
- Expansión a regiones

### 2027: Scale
- 500+ clientes
- Expansión a Perú/Colombia
- Serie A
- Partnerships bancarios

### 2028+: Dominate
- Líder regional en PropTech/RegTech
- API estándar de facto
- M&A oportunístico

---

## El Equipo

### Fundador y CEO
**Daniel Leyton**
- 18 años experiencia en arquitectura y urbanismo
- Consultor CEPAL-UN
- CEO DATAPOLIS SpA
- Experiencia: SERVIU, I.M. Pudahuel, valorización inmobiliaria

### Capacidades del Equipo
- Desarrollo full-stack (Python, PHP, JavaScript)
- Machine Learning / Data Science
- Regulación financiera chilena
- Urbanismo y planificación territorial
- DevOps / Cloud infrastructure

---

## Financiamiento

### Uso de Fondos (Seed Round)

| Categoría | % | Monto |
|-----------|---|-------|
| Desarrollo producto | 40% | |
| Ventas y marketing | 30% | |
| Operaciones | 20% | |
| Legal/Compliance | 10% | |

### Hitos con Funding

1. **USD 500K**: Launch comercial + 50 clientes
2. **USD 1.5M**: 200 clientes + certificación CMF
3. **USD 5M**: Expansión regional + partnerships

---

## Por Qué Invertir en DATAPOLIS

1. **Producto 100% construido** – No es un PowerPoint, es software funcionando
2. **Mercado masivo** – Chile tiene 2.5M unidades en copropiedades
3. **Timing perfecto** – Open Finance Chile en implementación
4. **Equipo con track record** – CEPAL, Bloomberg, SERVIU
5. **Moat técnico** – 150K líneas de código especializado
6. **Capital efficient** – Desarrollo propio, bajo burn rate

---

## Contacto

**DATAPOLIS SpA**
- Email: inversores@datapolis.cl
- Web: https://datapolis.cl
- LinkedIn: /company/datapolis-chile

---

*"La plataforma inmobiliaria más completa de Latinoamérica, lista para escalar."*

---

**DATAPOLIS v3.0** | Presentación Inversores | Febrero 2026
