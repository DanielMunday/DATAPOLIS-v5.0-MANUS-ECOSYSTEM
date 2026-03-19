# DATAPOLIS v3.0 - Manual Operativo para Clientes

## Guía de Uso del Sistema

---

## Índice

1. [Introducción](#1-introducción)
2. [Acceso al Sistema](#2-acceso-al-sistema)
3. [Flujos de Uso Principal](#3-flujos-de-uso-principal)
4. [Módulos y Funcionalidades](#4-módulos-y-funcionalidades)
5. [Roles y Permisos](#5-roles-y-permisos)
6. [Buenas Prácticas](#6-buenas-prácticas)
7. [Soporte y FAQ](#7-soporte-y-faq)

---

## 1. Introducción

DATAPOLIS v3.0 es una plataforma integral para la gestión inmobiliaria que incluye:

- Gestión de expedientes y propiedades
- Administración de copropiedades
- Análisis de plusvalías y riesgos
- Credit scoring y valorización
- Inteligencia territorial (ÁGORA)
- Open Finance (consulta de cuentas bancarias)

### Requisitos del Sistema

| Requisito | Especificación |
|-----------|---------------|
| Navegador | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| Conexión | Internet estable (mínimo 5 Mbps) |
| Pantalla | Resolución mínima 1280x720 |

---

## 2. Acceso al Sistema

### 2.1 Primer Acceso

1. Reciba sus credenciales por email del administrador
2. Acceda a: `https://app.datapolis.cl`
3. Ingrese email y contraseña temporal
4. Cambie su contraseña en el primer login

### 2.2 Login Regular

```
URL: https://app.datapolis.cl
Email: su_email@empresa.cl
Contraseña: su_contraseña
```

### 2.3 Recuperar Contraseña

1. Click en "¿Olvidó su contraseña?"
2. Ingrese su email registrado
3. Revise su bandeja de entrada
4. Siga el enlace para crear nueva contraseña

### 2.4 Autenticación de Dos Factores (2FA)

Si su organización tiene 2FA habilitado:
1. Después del login, ingrese el código de su app authenticator
2. Marque "Recordar este dispositivo" si es de confianza

---

## 3. Flujos de Uso Principal

### 3.1 Flujo: Alta de Expediente Inmobiliario

```
Paso 1: Dashboard → "Nuevo Expediente"
Paso 2: Completar formulario básico
        - Título del expediente
        - Tipo (compraventa, arriendo, hipoteca, due diligence)
        - Descripción
Paso 3: Guardar expediente
Paso 4: Vincular propiedad existente o crear nueva
Paso 5: Agregar documentos de respaldo
Paso 6: Asignar participantes (vendedor, comprador, etc.)
```

**Campos obligatorios**: Título, Tipo

**Resultado**: Expediente creado con número único para seguimiento

### 3.2 Flujo: Registro de Propiedad

```
Paso 1: Expediente → "Vincular Propiedad" → "Nueva Propiedad"
Paso 2: Datos básicos
        - ROL (ej: 123-456)
        - Dirección completa
        - Comuna y región
        - Tipo (casa, departamento, terreno, local)
Paso 3: Datos técnicos
        - Superficie total y útil
        - Dormitorios, baños
        - Año construcción
        - Estado de conservación
Paso 4: Ubicación geográfica (mapa)
Paso 5: Guardar propiedad
```

**Resultado**: Propiedad registrada y vinculada al expediente

### 3.3 Flujo: Análisis de Plusvalía (Ley 21.713)

```
Paso 1: Propiedad → "Análisis de Plusvalía"
Paso 2: Ingresar datos de adquisición
        - Fecha de compra original
        - Valor de compra (UF)
        - Mejoras realizadas (si aplica)
Paso 3: Sistema calcula automáticamente:
        - Plusvalía generada
        - Tasa aplicable
        - Impuesto estimado
        - Posibles exenciones
Paso 4: Revisar resultado
Paso 5: Generar declaración (PDF)
Paso 6: Descargar o enviar a SII
```

**Resultado**: Cálculo de plusvalía con informe descargable

### 3.4 Flujo: Consulta de Riesgos (GIRES)

```
Paso 1: Propiedad → "Análisis de Riesgos"
Paso 2: Sistema consulta automáticamente:
        - Riesgo sísmico (zonificación)
        - Riesgo de tsunami
        - Riesgo de inundación
        - Riesgo de incendio
        - Riesgo de remoción en masa
Paso 3: Visualizar mapa de riesgos
Paso 4: Ver score global y recomendaciones
Paso 5: Descargar informe técnico
```

**Resultado**: Informe de riesgos naturales georreferenciado

### 3.5 Flujo: Uso de ÁGORA (Inteligencia Territorial)

```
Paso 1: Menú → "ÁGORA GeoViewer"
Paso 2: Buscar ubicación por:
        - Dirección
        - ROL
        - Coordenadas
        - Click en mapa
Paso 3: Activar capas de información:
        - Plan Regulador Comunal
        - Zonificación
        - Normativa urbana
        - Obras públicas
        - Riesgos naturales
Paso 4: Hacer consulta espacial (dibujar área)
Paso 5: Ver indicadores del territorio
Paso 6: Generar reporte territorial
```

**Resultado**: Análisis territorial completo con normativa aplicable

### 3.6 Flujo: Open Finance (Consulta Bancaria)

```
Paso 1: Menú → "Open Finance"
Paso 2: Seleccionar institución financiera
Paso 3: Autorizar consentimiento
        - Permisos solicitados (lectura cuentas, saldos, movimientos)
        - Duración del consentimiento
Paso 4: Autenticarse en el banco (redirect)
Paso 5: Regresar a DATAPOLIS
Paso 6: Ver cuentas y saldos sincronizados
Paso 7: Consultar movimientos históricos
```

**Nota**: Requiere tener cuentas en bancos que soporten NCG 514

---

## 4. Módulos y Funcionalidades

### Módulos Principales

| Módulo | Descripción | Acceso desde |
|--------|-------------|--------------|
| **Expedientes** (M00) | Gestión de casos inmobiliarios | Dashboard → Expedientes |
| **Propiedades** (M01) | Fichas de propiedad detalladas | Expedientes → Propiedades |
| **Copropiedades** (M02) | Gestión Ley 21.442 | Dashboard → Copropiedades |
| **Credit Scoring** (M03) | Evaluación crediticia Basel IV | Propiedad → Credit Score |
| **Valorización** (M04) | Avalúo automático ML | Propiedad → Valorizar |
| **PAE** (M11) | Análisis precesional | Copropiedad → PAE |
| **Garantías** (M13) | Registro de colaterales | Expediente → Garantías |
| **GIRES** (M17) | Riesgos naturales | Propiedad → Riesgos |
| **ÁGORA** (M22) | Inteligencia territorial | Menú → ÁGORA |
| **Plusvalías** (GT-PV) | Ley 21.713 | Propiedad → Plusvalía |
| **Open Finance** | NCG 514 | Menú → Open Finance |

### Funcionalidades por Módulo

#### Expedientes
- Crear, editar, cerrar expedientes
- Timeline de eventos
- Documentos adjuntos
- Participantes
- Estados y prioridades

#### Copropiedades
- Dashboard con KPIs
- Gestión de unidades
- Contratos de antenas
- Gastos comunes
- Morosidad y cobranza
- Fondo de reserva

#### Valorización
- Avalúo automático (ML ensemble)
- Método hedónico
- Comparables de mercado
- Historial de precios
- Informe descargable

---

## 5. Roles y Permisos

### Roles Disponibles

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| **Super Admin** | Administrador del sistema | Todos |
| **Admin** | Administrador de organización | CRUD completo en su tenant |
| **Manager** | Gerente / Supervisor | Gestión operativa, reportes |
| **Accountant** | Contador | Contabilidad, certificados, reportes financieros |
| **Operator** | Operador | Lectura + operaciones básicas |
| **Viewer** | Visualizador | Solo lectura |

### Matriz de Permisos

| Acción | Super Admin | Admin | Manager | Accountant | Operator | Viewer |
|--------|-------------|-------|---------|------------|----------|--------|
| Ver expedientes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Crear expedientes | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Editar expedientes | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Eliminar expedientes | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver contabilidad | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Generar certificados | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Configurar usuarios | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver auditoría | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 6. Buenas Prácticas

### Gestión de Expedientes

1. **Nombres descriptivos**: Use títulos claros como "Compraventa Depto 304 Edificio Los Robles"
2. **Documentación completa**: Adjunte todos los documentos relevantes desde el inicio
3. **Actualización constante**: Mantenga el estado del expediente actualizado
4. **Notas de seguimiento**: Agregue notas en cada hito importante

### Seguridad

1. **Contraseña robusta**: Mínimo 12 caracteres, incluya mayúsculas, números y símbolos
2. **No compartir credenciales**: Cada usuario debe tener su propia cuenta
3. **Cerrar sesión**: Siempre cierre sesión al terminar, especialmente en equipos compartidos
4. **Reportar incidentes**: Notifique cualquier actividad sospechosa

### Rendimiento

1. **Filtros**: Use filtros para buscar en lugar de navegar listas largas
2. **Exportaciones**: Exporte datos en horarios de baja demanda
3. **Navegador actualizado**: Mantenga su navegador en la última versión
4. **Caché**: Limpie caché del navegador si experimenta problemas

---

## 7. Soporte y FAQ

### Canales de Soporte

| Canal | Horario | Uso |
|-------|---------|-----|
| Email: soporte@datapolis.cl | 24/7 | Consultas generales |
| Chat en app | L-V 9:00-18:00 | Ayuda inmediata |
| Teléfono: +56 2 XXXX XXXX | L-V 9:00-18:00 | Urgencias |
| Base de conocimiento | 24/7 | Auto-servicio |

### FAQ

**P: ¿Cómo cambio mi contraseña?**
R: Perfil → Seguridad → Cambiar contraseña

**P: ¿Puedo exportar datos a Excel?**
R: Sí, la mayoría de las tablas tienen botón "Exportar" que genera XLSX

**P: ¿Qué pasa si se cae el sistema?**
R: Los datos se guardan automáticamente. Al volver, retome desde donde quedó.

**P: ¿Cómo agrego un nuevo usuario a mi organización?**
R: Requiere rol Admin. Vaya a Configuración → Usuarios → Nuevo Usuario

**P: ¿Los datos están seguros?**
R: Sí. Usamos encriptación AES-256, SSL/TLS, y cumplimos con estándares de seguridad bancaria.

**P: ¿Puedo acceder desde el celular?**
R: Sí, la plataforma es responsive. También hay app móvil en desarrollo.

**P: ¿Cómo vinculo mi cuenta bancaria para Open Finance?**
R: Menú → Open Finance → Agregar Institución → Seguir flujo de autorización

**P: ¿Cada cuánto se actualiza el valor UF?**
R: Diariamente, desde fuente oficial BCCH

---

## Glosario

| Término | Definición |
|---------|------------|
| **Expediente** | Caso o transacción inmobiliaria en seguimiento |
| **ROL** | Identificador único de propiedad en SII |
| **UF** | Unidad de Fomento, valor indexado a inflación |
| **PAE** | Precession Analysis Engine - motor de análisis de riesgos |
| **GIRES** | Sistema de gestión de riesgos naturales |
| **LTV** | Loan-to-Value - relación préstamo/valor |
| **PD** | Probability of Default - probabilidad de incumplimiento |
| **NCG 514** | Norma de Carácter General 514 CMF - Open Finance |

---

**DATAPOLIS v3.0** | Manual Operativo | Versión 3.0.0
