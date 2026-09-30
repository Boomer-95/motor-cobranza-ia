# QA

Ejecutar desde la raíz con el entorno virtual activado:

```bash
pytest
python -m compileall -q app tests
python -m pip check
cd frontend-react
npm run lint
npm run build
```

Las fixtures deshabilitan dotenv y usan SQLite en memoria, tokens Entra firmados con RSA efímera, discovery/JWKS y Groq mockeados. No leen .env, no acceden a PostgreSQL real ni hacen llamadas al proveedor. Se conserva cobertura de autenticación Entra, comunicación simulada y modelo existente.

Se prueban falta de configuración Groq (503), fallo/respuesta vacía (502, sin historial ni fallback), contexto mínimo, generación, reutilización, regeneración, invalidación tras pago y COUNT DISTINCT. Búsqueda por nombre/ID/folio, filtros, clientes sin evaluar, detalle y fechas pasadas/futuras. Pagos parciales/totales, sobrepago, montos inválidos, deuda inexistente, estatus, saldo, historial, features posteriores al pago, persistencia ML y rollback sin modelo. Migración aditiva repetida y seeds idempotentes, incluyendo cliente heredado.

Docker: `docker compose config --quiet` valida sin imprimir secretos expandidos; `docker compose build backend frontend` construye sin modificar volúmenes. No ejecutar comandos para eliminar volúmenes.

Prueba manual pendiente de navegador: iniciar sesión; buscar dos nombres iguales y distinguir por folio; abrir ficha con ratón/teclado; filtrar y ordenar; procesar/reutilizar/regenerar; registrar pago y verificar actualización de ficha, cartera, métricas y riesgo; comprobar errores visibles; probar móvil y expiración de sesión.

SQLite no reproduce SELECT FOR UPDATE de PostgreSQL. Antes de producción verificar migración sobre una copia del respaldo y pagos concurrentes en PostgreSQL. No se ejecutan pruebas sobre la base existente del usuario. Los builds no sustituyen pruebas E2E. Revisar las limitaciones de dependencias documentadas en SEGURIDAD.md.

## Validación de esta actualización

65 pruebas aprobadas (14.75 s), sin llamadas reales a Groq. Dos advertencias heredadas de deprecación: Starlette/AnyIO y passlib/crypt. La suite se ejecutó fuera del sandbox porque TestClient quedaba bloqueado dentro de él. compileall y pip check correctos; lint sin errores ni advertencias; build Vite correcto. Compose validado con config --quiet sin imprimir secretos. Imágenes backend y frontend construidas correctamente; Docker usó el builder clásico porque no está instalado buildx. No se aplicó la migración ni se ejecutaron seeds sobre la base existente y no se recrearon servicios ni volúmenes.

## Ampliación de ficha y comunicaciones

Se agregaron pruebas de búsqueda parcial por apellido con nombres duplicados y folios distintos; detalle sin comunicaciones; aislamiento de comunicaciones por cliente, orden de fecha/ID, estado simulado y conservación de registros históricos. La ficha contiene ahora acciones de procesar y regenerar, registro editable de comunicación y su historial. El clic en toda la fila o el botón de folio enfoca el detalle; confirmar esta interacción también en navegador.

Validación de la ampliación: 68 pruebas aprobadas en 14.77 s, con las mismas dos advertencias heredadas. Lint sin errores ni advertencias, build Vite, compileall, pip check y Compose config --quiet correctos. No se hizo prueba E2E de navegador ni se operó sobre los datos PostgreSQL existentes.

## Selección y liquidación

La selección consulta detalle sin llamar ML/Groq ni incrementar historial. Se prueban última estrategia, cliente sin estrategia, folios distintos, saldo cero con y sin servicios configurados, score/probabilidad nulos, limpieza al liquidar, exclusión de cartera y deudores activos. Las pruebas existentes de scoring ahora crean deuda positiva. La estrategia previa se conserva incluso después de un pago: una nueva requiere regenerar=true.

Validación manual de interfaz: seleccionar fila y verificar ID automático, desplazamiento a Operación y detalle superior; verificar los cuatro estados del panel y ausencia de ficha bajo cartera. Registrar pago desde la subsección compacta y comprobar que liquidar elimina la fila pero mantiene visible el cliente seleccionado como Sin deuda activa.

Validación del flujo corregido: 79 pruebas aprobadas en 17.94 s; dos advertencias heredadas de deprecación. Lint sin errores ni advertencias; build Vite, compileall y pip check correctos. Groq mockeado y SQLite aislado; sin cambios sobre PostgreSQL. La interacción visual de navegador permanece pendiente de revisión manual.

## Autenticación Microsoft Entra ID

Pruebas automatizadas: token ausente/malformado, firma inválida, exp/nbf, issuer/audience/tid/ver, scope exacto, identidad opcional sin email, rutas protegidas, /auth/login eliminado, configuración ausente, caché/rotación JWKS, discovery restringido y fallos seguros. Los tokens son sintéticos locales; no se consulta Microsoft. Se mantienen las pruebas de negocio y comunicaciones. Los resultados numéricos de secciones anteriores son históricos.

Prueba interactiva pendiente: configurar el único registro según README, iniciar con Microsoft en localhost:8080, aprobar consentimiento para el scope propio, entrar al dashboard y cerrar sesión. Probar atrás/adelante, recarga, cambio de pestaña y BFCache: no debe reaparecer información sin validar la cuenta. Probar selección con varias cuentas y recuperación tras expiración; nunca copiar ni imprimir tokens. Confirmar operaciones con COMMUNICATIONS_REAL_ENABLED=false. Los builds no sustituyen esta prueba interactiva del tenant.

Resultado de esta migración Entra: 142 pruebas aprobadas en 5.03 s; una advertencia heredada de Starlette/AnyIO. compileall, pip check, lint y builds React (sin configuración y con IDs ficticios) correctos. Compose config --quiet y build de backend/frontend correctos usando --env-file /dev/null y variables PostgreSQL ficticias, sin leer el .env real. No se iniciaron servicios ni se modificaron datos. Pendiente exclusivamente la prueba interactiva Microsoft con el tenant del usuario.

## Diagnóstico seguro de adaptación de comunicaciones

El 502 de adaptación ocurre antes de `comunicaciones.registrar()`: no registra comunicación ni contacta Twilio. Los logs posteriores confirmaron dos rechazos por `TokenLimitReached`: la validación exigía `stop` antes de evaluar si el contenido SMS era utilizable. El log no permite determinar qué texto o razonamiento agotó los tokens del proveedor.

Rutas identificadas y reproducidas con mocks:

- Error SDK/proveedor: `GroqGenerationFailed`, con razón fija para timeout, conexión, HTTP 400/401/403/404/429 y otros errores HTTP; una excepción inesperada del cliente se identifica por separado.
- Respuesta sin estructura esperada: `SmsAdaptationFailed reason=MalformedResponse`.
- Para Llamada, `finish_reason=length` mantiene `TokenLimitReached`. Para SMS se acepta `stop` o `length` con contenido utilizable; otros motivos mantienen `UnexpectedFinishReason`.
- Contenido nulo, no textual o vacío: `EmptyContent`.
- Normalización deja solo emojis/caracteres no permitidos, o la primera palabra excede 150 caracteres: `NoUsableSmsWords`.

Un SMS textual utilizable (`stop` o `length`) no se rechaza por el motivo de terminación ni por superar 150 caracteres: `adaptar_sms` extrae únicamente `message.content`, retira adornos Markdown, etiquetas SMS, comillas externas y bloques `<think>` completos o incompletos, normaliza a GSM-7 básico y conserva palabras completas hasta 150 caracteres. Nunca usa el campo separado de razonamiento. Si no queda texto alfanumérico utilizable, aborta antes de registrar. El prompt exige una sola línea de 120–130 caracteres sin razonamiento ni explicaciones. Se mantiene temperatura 0.2 y presupuesto fijo de 256 tokens; no se aumenta para resolver este caso. Llamada conserva su validación anterior, brevedad y simulación. No hay regeneración ni sustitución por mensajes hardcodeados cuando falla Groq.

Los logs contienen únicamente categorías, razones fijas y canal. No incluyen excepción, stack trace, cuerpo del proveedor, mensajes, destinatarios ni credenciales. Errores inesperados en código local ya no se convierten silenciosamente en un 502 de Groq. Para inspeccionar solo esas categorías tras desplegar (sin generar otro envío):

```bash
docker compose logs --no-color backend | rg 'GroqGenerationFailed|SmsAdaptationFailed|VoiceAdaptationFailed'
```

La regresión mantiene un SMS previo ID 6, provoca cada rechazo y verifica que no se agrega ningún registro ni se llama a proveedores. La suite bloquea conexiones de red y utiliza mocks de Groq, Twilio y SendGrid.

Validación de recuperación SMS con `length`: 207 pruebas aprobadas, con una advertencia heredada Starlette/AnyIO. Se prueba explícitamente entrega al servicio de comunicaciones mockeado, rechazo de contenido vacío/inutilizable sin registro, limpieza de formato/razonamiento y límite GSM-7; se mantienen las pruebas de proveedores, Email/WhatsApp, Voice simulada y fallos de Groq. `compileall app` y `git diff --check` correctos. Sin llamadas reales ni envíos.
