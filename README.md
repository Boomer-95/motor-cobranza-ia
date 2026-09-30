# Motor Inteligente de Cobranza para PluriOne

MVP universitario para administrar una cartera, priorizar clientes y preparar estrategias de contacto. Se amplía el proyecto existente con historial visible y comunicaciones externas opcionales, conservando FastAPI, React, PostgreSQL, Microsoft Entra ID, Groq y Random Forest.

## Objetivo y alcance

Ayudar al administrador a decidir a quién contactar y preparar un mensaje empático. El proyecto se puede desarrollar y demostrar con presupuesto de **$0 MXN**, usando software local y sujeto a las cuotas de la cuenta de Groq. No se requieren Twilio, SendGrid ni servicios de pago.

Incluye login privado, métricas, segmentación Alto/Medio/Bajo, prioridad por riesgo × saldo, generación y almacenamiento de estrategias, historial por cliente, registro de Email/SMS/WhatsApp con envío opcional y Llamada simulada y cierre de sesión.

## Arquitectura y tecnologías

```text
React + Vite -> api.js -> FastAPI -> SQLAlchemy -> PostgreSQL
                            |-> Microsoft Entra ID / MSAL / validación RS256
                            |-> RandomForestClassifier (joblib local)
                            |-> Groq para estrategias personalizadas
Docker: navegador -> Nginx -> /backend -> FastAPI -> PostgreSQL
```

Python 3.12, Node 20, React 18, Vite, FastAPI, SQLAlchemy, PostgreSQL 16, scikit-learn, pandas, NumPy, SDK compatible OpenAI para Groq, PyJWT, MSAL, pytest, Docker Compose y Nginx. Git/GitHub para control de versiones.

```text
app/
  main.py                 API y operaciones de cobranza
  auth.py, database.py     Entra ID y sesiones SQLAlchemy
  models.py               Cliente, Deuda, Pago, Administrador, historial y comunicación
  seed.py                 Datos demo (seed_admin retirado)
  ml/                     Features, entrenamiento, historial sintético y risk_model.joblib
frontend-react/
  src/                    Dashboard, Login, Historial, Comunicacion y api.js
  Dockerfile, nginx.conf
tests/                   Pruebas aisladas (sin servicios externos)
docs/                     Arquitectura, QA, ML, seguridad y mantenimiento
Dockerfile, docker-compose.yml, .env.example
```

La carpeta residual `app/app/ml` contiene un `__init__.py` vacío y caché; no se usa en los imports revisados. Se conserva por prudencia. El modelo existente no se elimina ni se reentrena automáticamente.

## IA generativa y ML predictivo

Groq es obligatorio para generar estrategias: configura `GROQ_API_KEY` en el entorno y opcionalmente `GROQ_MODEL` (por defecto `llama-3.1-8b-instant`). La aplicación inicia sin esa clave, pero analizar devuelve 503 “Servicio de IA no configurado.”. Si el proveedor falla o devuelve texto vacío/incompleto se devuelve 502 sin guardar mensaje. No existe plantilla local ni sustitución de errores por mensajes predeterminados.

Seleccionar un cliente solo consulta su detalle y estrategia almacenada. “Procesar cliente” calcula riesgo y genera con Groq cuando tiene deuda activa y aún no tiene estrategia. Si ya hay estrategia, conserva la última; “Regenerar estrategia con IA” es la acción explícita para pedir otra. Sin deuda activa no se ejecuta ML ni Groq: probabilidad y score no aplican y el segmento es Sin deuda. Los registros históricos se conservan, identificando los de origen no verificado.

Random Forest combina 200 árboles de decisión para estimar pago a tiempo a partir de seis características de pagos y deuda. El riesgo es `1 - P(pago a tiempo)`; desde 0.66 es alto, desde 0.33 medio y por debajo bajo. El entrenamiento genera 2,000 observaciones sintéticas para demostrar el flujo sin exponer datos personales. Sus métricas **no demuestran precisión sobre clientes reales**. Consulta [MODELO_ML.md](docs/MODELO_ML.md).

## Variables de entorno

Usa [.env.example](.env.example) como referencia. No contiene secretos. No sobrescribas un `.env` existente.

| Variable | Uso |
|---|---|
| DATABASE_URL | URL PostgreSQL local; usuario y contraseña propios, con caracteres especiales codificados en URL |
| ENTRA_CLIENT_ID / ENTRA_TENANT_ID / ENTRA_REQUIRED_SCOPE | Validación del access token de la API |
| VITE_ENTRA_CLIENT_ID / VITE_ENTRA_TENANT_ID / VITE_ENTRA_API_SCOPE / VITE_ENTRA_REDIRECT_URI | MSAL en React; mismo registro que la API |
| GROQ_API_KEY / GROQ_MODEL | Credencial necesaria para estrategias y modelo de Groq |
| CORS_ORIGINS | Orígenes permitidos separados por coma; sin comodín |
| POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB | Inicialización de PostgreSQL en Compose |
| DB_HOST | Compose lo fija a `db`; construye la URL de forma segura y tiene prioridad sobre DATABASE_URL |
| VITE_API_URL | URL pública del backend; nunca debe contener secretos |

Microsoft Entra ID es el único acceso. MSAL administra la sesión; FastAPI valida el access token y React confirma `/auth/me` antes de mostrar el dashboard. No se crean usuarios locales.

## Instalación local en Linux Mint

Instala Python 3.12 con venv, PostgreSQL y Node 20 con npm usando los paquetes apropiados para tu versión de Linux Mint. Verifica `python3 --version`, `node --version` y `npm --version`. Para PostgreSQL local:

```bash
sudo apt update
sudo apt install python3-venv postgresql postgresql-contrib
sudo systemctl enable --now postgresql
sudo -u postgres createuser --pwprompt plurione_app
sudo -u postgres createdb --owner=plurione_app plurione_demo
```

`createuser` solicita tu contraseña de forma interactiva. Si ya existen usuario y base, reutilízalos; estos nombres son ejemplos, no credenciales. Desde la raíz:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements-dev.txt
# Solo si todavía no existe .env:
test -e .env || cp .env.example .env
```

Edita `.env` localmente sin sobrescribir valores existentes. Completa `DATABASE_URL` y las variables Entra descritas abajo. Nunca compartas contraseñas de PostgreSQL ni claves de proveedores.

```bash
python -m app.migrate
python -m app.seed
python -m app.ml.seed_historial
# Opcional: reemplaza el modelo existente; respáldalo antes.
python -m app.ml.train_model
uvicorn app.main:app --reload
```

Los scripts crean tablas faltantes y evitan repetir sus datos cuando ya existen. Los seeds son exclusivamente para una base de demostración. `create_all` no migra tablas existentes.

En otra terminal:

```bash
cd frontend-react
npm ci
npm run dev
```

Abre http://localhost:5173. La API local predeterminada es http://127.0.0.1:8000. Para cambiarla: `VITE_API_URL=http://localhost:8000 npm run dev`. Vite no lee automáticamente el `.env` de la raíz desde su subcarpeta. Documentación interactiva: http://127.0.0.1:8000/docs.

## Docker

Con PostgreSQL ya iniciado (`docker compose up -d db` si es una instalación nueva), completa en tu entorno o `.env` las variables `POSTGRES_*` y las variables Entra. Compose exige los secretos y no incluye valores predeterminados para ellos. No copies `.env` en las imágenes.

```bash
docker compose build backend frontend
docker compose stop backend
docker compose run --rm --no-deps backend python -m app.migrate
docker compose up -d
docker compose exec backend python -m app.seed
docker compose exec backend python -m app.ml.seed_historial
```

Abre http://localhost:8080. Nginx sirve React y envía `/backend/` a FastAPI; `VITE_API_URL` se fija al construir el frontend. PostgreSQL persiste en un volumen y no expone su puerto. Los puertos web se limitan a localhost. `docker compose down` conserva el volumen; **no uses `down -v` si necesitas los datos**.

Para reentrenar el modelo persistente, ejecuta el entrenamiento local y reconstruye el backend. El entrenamiento dentro del contenedor escribe en su capa temporal y se pierde al recrearlo.

## Demostración

1. Inicia sesión y busca por nombre parcial, ID o folio `CL-000001`. Los nombres pueden repetirse.
2. Filtra por riesgo, estado del análisis y estado de deuda; ordena por prioridad, saldo, atraso, vencimiento o nombre.
3. Selecciona la fila o activa el botón de folio con teclado: llena automáticamente el ID y muestra el detalle en Resultado del análisis, dentro de Operación de Cobranza.
4. Revisa todas las deudas, vencimientos, pagos, score, última estrategia y comunicaciones.
5. “Procesar cliente” genera la primera estrategia si hay deuda activa. Una estrategia existente solo se reemplaza mediante Regenerar.
6. En una deuda activa ingresa un monto y pulsa “Registrar pago”. El saldo, historial, riesgo, cartera y métricas se actualizan sin recargar la página.
7. Desde Resultado del análisis puedes procesar o regenerar si hay deuda activa y abrir subsecciones de pagos y comunicaciones. Revisa o edita el mensaje antes de registrarlo; el historial muestra canal, fecha, mensaje y estado. Por defecto no hay envío externo; consulta Comunicaciones externas.

“Saldo vencido” suma saldos positivos con estatus `En Mora` o fecha anterior a hoy. Es dinero que los clientes deben a PluriOne. `cartera_vencida` conserva su clave API. “Clientes con estrategia IA” usa `COUNT(DISTINCT cliente_id)` sobre el historial conservado; regenerar no aumenta el conteo del mismo cliente. Los registros anteriores se conservan, incluso si su origen no está verificado. “Clientes sin evaluar” usa segmento `No definido` o nulo, nunca score cero. Deudores activos cuenta clientes con saldo positivo; `total_clientes` cuenta todos. Recuperación sigue siendo (monto original − saldo) / monto original, no una suma del historial sintético.

## Endpoints principales

Todos los endpoints de esta tabla requieren `Authorization: Bearer TOKEN`.

| Método | Ruta | Función |
|---|---|---|
| GET | /auth/me | Identidad Microsoft: id (oid), nombre y email opcional |
| GET | /api/metricas | Resumen de cartera |
| GET | /api/clientes | query, segmento, analizado, estatus_deuda, orden |
| GET | /api/clientes/{cliente_id} | Ficha financiera, deudas, pagos y estrategia |
| POST | /api/deudas/{deuda_id}/pagos | JSON `{"monto": 3000}`; registra pago y recalcula ML |
| GET | /api/cartera-priorizada | Orden descendente por riesgo × saldo |
| POST | /ia/analizar-riesgo/{cliente_id} | Calcula ML y genera/reutiliza mensaje; `?regenerar=true` fuerza Groq |
| POST | /ia/calcular-riesgo/{cliente_id} | Calcula y guarda score/segmento |
| GET | /ia/historial/{cliente_id} | Historial más reciente primero; 404 si vacío |
| POST | /api/comunicaciones | JSON: cliente_id, canal y mensaje; respuesta 201 con modo y estado |

En comunicaciones `exitoso=false` identifica simulación o envío no confirmado; consultar `modo` y `estado`. `fecha_envio` conserva el tipo Date y representa el día del registro. GET /api/integraciones/estado requiere autenticación y devuelve disponibilidad efectiva por canal.

## Pruebas y compilación

```bash
source venv/bin/activate
pytest
python -m compileall -q app tests
python -m pip check
npm run lint --prefix frontend-react
npm run build --prefix frontend-react
```

Las pruebas no usan PostgreSQL real, `.env` ni APIs externas. Ver [QA.md](docs/QA.md).

## Limitaciones y mejoras futuras

No hay registro local, migraciones automáticas ni auditoría completa. MSAL administra los tokens en sessionStorage; sigue siendo necesario prevenir XSS. La política de acceso administrativo se configura en Entra. El saldo usa Float heredado; migrar a Numeric con planificación. Groq recibe nombre, deudas activas, features, riesgo y hasta ocho pagos recientes: usar únicamente clientes ficticios durante la demo. El modelo sintético requiere validación real, calibración y análisis de sesgo antes de decisiones operativas. Se requiere HTTPS para cualquier despliegue fuera de localhost.

Futuro: migraciones Alembic, paginación, roles, auditoría, pruebas PostgreSQL y E2E, auditoría de pagos y reentrenamiento validado. Las integraciones conservan las responsabilidades existentes; la autenticación utiliza exclusivamente Entra ID.

## Migración compatible

`python -m app.migrate` agrega tres columnas anulables: `pagos.deuda_id` (FK a deudas, con índice), `clientes.probabilidad_pago_a_tiempo` y `historial_mensajes.contexto_hash`. Es aditiva e idempotente y funciona también sobre una base nueva. `create_all` por sí solo no modifica tablas existentes. Ejecuta la migración antes de iniciar el backend actualizado. No intenta asociar pagos históricos a deudas por inferencia. No borra tablas, datos ni volúmenes. Consulta [MANTENIMIENTO.md](docs/MANTENIMIENTO.md) para respaldo y despliegue.

Los seeds agregan aproximadamente 15 clientes ficticios con emails `example.invalid`, reconocen los tres emails heredados y no modifican sus datos. Cada cliente nuevo y sus deudas se crean juntos; los clientes existentes se omiten para no reponer deudas pagadas. El historial sintético usa semilla por cliente y fechas fijas; omite clientes con pagos previos y nunca puebla clientes ajenos al catálogo demo.

## Comunicaciones externas

El modo predeterminado es simulación gratuita. `COMMUNICATIONS_REAL_ENABLED=false` (o ausente) impide todo envío, incluso con credenciales. Solo el valor `true` habilita envíos y cada canal necesita configuración completa. El endpoint protegido `GET /api/integraciones/estado` devuelve booleanos de disponibilidad efectiva, sin consultar proveedores ni revelar valores; no comprueba autenticación ni entrega.

| Canal | Proveedor | Variables necesarias además del interruptor |
|---|---|---|
| Email | SendGrid | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`; nombre opcional `SENDGRID_FROM_NAME=PluriOne` |
| SMS | Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` |
| WhatsApp | Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` |
| Llamada | Simulada | Voice no está habilitado |

Configura manualmente el entorno del backend, verifica el remitente SendGrid y utiliza números habilitados en Twilio. Los teléfonos requieren formato internacional E.164 (`+`, código de país y número), sin inventar prefijos. WhatsApp acepta remitente con o sin `whatsapp:`; requiere remitente aprobado o Sandbox y destinatarios habilitados. Tener teléfono no demuestra que tenga WhatsApp. Las restricciones de Sandbox, ventanas de conversación y plantillas las aplica el proveedor; los rechazos quedan como Fallido. Esta implementación envía texto libre y no gestiona plantillas.

Referencias: [SDK oficial SendGrid](https://github.com/sendgrid/sendgrid-python), [WhatsApp en Twilio](https://www.twilio.com/docs/whatsapp/quickstart). La demo no necesita cuentas externas. Los envíos reales pueden generar cargos: conservar el interruptor en `false` para desarrollo de presupuesto $0.

`POST /api/comunicaciones` conserva `{cliente_id, canal, mensaje}`. El backend decide el modo, valida contacto para envío real y devuelve `modo`, `estado`, `provider`, `exitoso` y `simulada`. No permite que el payload habilite servicios. Sin configuración suficiente registra `simulado / Simulado / exitoso=false`, incluso en clientes demo sin contacto utilizable. En real valida email o teléfono y rechaza datos inválidos con 422 antes de contactar al proveedor. Canal inválido/mensaje vacío dan 422 y cliente inexistente 404.

Se guarda Pendiente antes del envío; aceptación del proveedor produce Enviado y guarda external_id cuando existe. Enviado significa aceptación, **no entrega confirmada**. Un error produce Fallido con código técnico seguro, sin excepción ni respuesta del proveedor en el frontend. No hay reintentos automáticos. Ante timeout o conexión perdida, revisar el historial y el proveedor antes de reenviar: pudo haberse aceptado el mensaje. El botón bloquea doble clic mientras está en curso; no es idempotencia entre pestañas o peticiones independientes.

Flujo demo: React → FastAPI → PostgreSQL (simulado). Flujo real: revisión del administrador → FastAPI → Twilio/SendGrid → resultado en PostgreSQL. Random Forest calcula riesgo, Groq genera el texto y los proveedores solo lo envían. Llamada mantiene una función reservada para Voice; faltan habilitación explícita, número con capacidad Voice y un diseño de TwiML/instrucciones de llamada antes de implementarlo.

Antes de arrancar esta versión sobre una base existente, respaldar y ejecutar `python -m app.migrate` (en Docker, seguir Mantenimiento). Añade cinco columnas anulables sin borrar datos ni reinterpretar entregas históricas.

## Integración continua

`.github/workflows/ci.yml` ejecuta en push y pull_request hacia main tres jobs: backend (Python 3.12, requirements y requirements-dev, pytest, compileall y pip check), frontend (Node 22, npm ci, lint y build) y construcción de ambas imágenes Docker sin publicarlas. No necesita PostgreSQL ni secretos: pytest usa SQLite, proveedores mockeados, bloqueo de conexiones de red y desactiva dotenv. Si en el futuro se precisan secretos de CI, configurarlos en GitHub Actions Secrets, nunca en YAML. No se añade badge hasta verificar la ruta pública del repositorio.

## Microsoft Entra ID: único método de acceso

Se reutiliza **el único App Registration existente**, tanto para SPA como para API. No se necesita client secret. POST /auth/login desaparece; GET /auth/me devuelve `{id, nombre, email}` y puede devolver email nulo. La tabla administradores se conserva sin uso para autenticación; seed_admin queda retirado y no modifica datos.

Agregar manualmente estas variables al entorno o al `.env` existente (sustituir los marcadores; no son valores reales):

```dotenv
ENTRA_CLIENT_ID=<CLIENT_ID>
ENTRA_TENANT_ID=<TENANT_ID>
ENTRA_REQUIRED_SCOPE=access_as_user
VITE_ENTRA_CLIENT_ID=<EL_MISMO_CLIENT_ID>
VITE_ENTRA_TENANT_ID=<EL_MISMO_TENANT_ID>
VITE_ENTRA_API_SCOPE=api://<CLIENT_ID>/access_as_user
VITE_ENTRA_REDIRECT_URI=http://localhost:8080/
```

Puedes retirar manualmente JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD y ADMIN_NOMBRE. No se usan. Las variables Entra son identificadores públicos, no secretos; ninguna clave Microsoft se incluye en React.

1. En el registro existente, conservar plataforma SPA y redirect exacto `http://localhost:8080/`, Application ID URI `api://<CLIENT_ID>` y scope habilitado `access_as_user`.
2. Verificar en el manifiesto del mismo registro `api.requestedAccessTokenVersion: 2`. FastAPI exige audience CLIENT_ID e issuer `https://login.microsoftonline.com/<TENANT_ID>/v2.0`; también valida firma RS256, exp, nbf cuando exista, tid, ver y scp. No acepta tokens v1 ni Graph. [Documentación Microsoft sobre versiones y validación](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens).
3. Configurar consentimiento para el scope delegado según las políticas del tenant. User.Read puede permanecer configurado, pero esta aplicación no solicita Graph. Para acceso administrativo restringido, habilitar asignación requerida y asignar los usuarios/grupos permitidos en la aplicación empresarial correspondiente; el scope por sí solo no es un rol administrativo.
4. Mantener `COMMUNICATIONS_REAL_ENABLED=false` durante las pruebas. Ejecutar:

```bash
docker compose config --quiet
docker compose build backend frontend
docker compose up -d backend frontend
```

5. Abrir `http://localhost:8080/` y pulsar **Iniciar sesión con Microsoft**. Seleccionar la cuenta autorizada y completar el consentimiento que corresponda. React solicita el access token del scope propio mediante acquireTokenSilent y recurre a acquireTokenRedirect cuando Microsoft requiere interacción. MSAL administra la caché/renovación; no se guardan tokens manualmente ni se utiliza idToken como Bearer. [Flujo MSAL React](https://learn.microsoft.com/en-us/entra/msal/javascript/react/faq).
6. Confirmar carga del dashboard y `/auth/me` sin copiar tokens. Cerrar sesión y probar Atrás/Adelante: la pantalla sensible debe permanecer oculta hasta volver a autenticar y validar. Logout usa logoutRedirect de Microsoft.

VITE_* se resuelve al construir la imagen: reconstruir frontend al cambiar IDs, scope o URI. Para Vite local, exportar las cuatro VITE_ENTRA_* en la terminal antes de `npm run dev`; Vite no lee el .env de la raíz. Si se usa localhost:5173, registrar también ese redirect SPA en **el mismo registro** y ajustar VITE_ENTRA_REDIRECT_URI; Docker mantiene localhost:8080.

Sin configuración frontend se muestra un aviso breve y no se permite login. El backend responde 503 seguro si falta configuración o no puede obtener claves; 401 por token inválido y 403 por scope insuficiente. La demo de comunicaciones sigue siendo gratuita/simulada, pero el acceso ahora requiere iniciar sesión en Microsoft; no hay login local de respaldo.

### Adaptación del mensaje por canal y prueba de un SMS

Email y WhatsApp conservan íntegro el mensaje recibido. SMS y Llamada necesitan Groq incluso en simulación: un fallo devuelve 502 (503 si no está configurado) antes de registrar o enviar. La adaptación no modifica `HistorialMensaje`. SMS pide una sola línea de 120–130 caracteres sin explicaciones ni formato, normaliza espacios, translitera acentos, elimina emojis y usa un subconjunto GSM-7 básico de un septeto por carácter. Si excede 150, conserva el prefijo de palabras completas que cabe, sin partir números ni URLs. Acepta contenido textual utilizable tanto con `finish_reason=stop` como con `length`; limpia adornos de formato y descarta razonamiento etiquetado. Si no queda texto utilizable, cancela el envío. El historial de comunicaciones guarda exactamente el texto enviado. Llamada genera texto breve y natural sin el límite SMS; Voice sigue deshabilitado.

Estados: `Pendiente` es la intención persistida antes del proveedor; `Enviado` significa aceptado, no entregado; `Fallido` significa rechazo o falta de confirmación (un timeout puede ocultar aceptación). `Entregado` se reserva para evidencia definitiva del proveedor y esta versión no lo asigna. El frontend explica la aceptación sin afirmar entrega. Para sincronizar estados posteriores se propone un status callback público HTTPS con validación de firma Twilio y actualización por `external_id`, sin reenviar mensajes. Esa infraestructura aún no está implementada. Mientras tanto, comprobar entrega/fallo en Twilio Console. Referencia: [estados y callbacks oficiales de Twilio](https://www.twilio.com/docs/messaging/guides/outbound-message-status-in-status-callbacks).

Para reconstruir, desde la raíz del repositorio:

```bash
docker compose build backend frontend
docker compose up -d db backend frontend
docker compose exec backend python -m app.migrate
```

Para **un solo SMS real**, configurar manualmente en `.env` `COMMUNICATIONS_REAL_ENABLED=true`, Groq y las tres variables Twilio SMS de la tabla anterior; no copiar credenciales al código. Usar un cliente cuyo teléfono E.164 sea el destinatario verificado de Trial. Recrear el backend tras cambiar `.env`:

```bash
docker compose up -d --force-recreate backend
```

Abrir `http://localhost:8080`, iniciar sesión Microsoft, seleccionar ese cliente y su estrategia, elegir **SMS**, confirmar que muestra **Real** y pulsar **Enviar comunicación una sola vez**. Comprobar en el historial el mensaje de hasta 150 caracteres y la aceptación; revisar el estado definitivo y segmentos en Twilio Console. Ante error o timeout no repetir el clic sin comprobar primero Twilio y el historial. Restaurar `COMMUNICATIONS_REAL_ENABLED=false` en `.env` y ejecutar de nuevo el último comando para volver a simulación. El interruptor habilita también otros proveedores que estén configurados: durante esta prueba usar únicamente SMS.

No hay reintentos automáticos ni idempotencia entre solicitudes independientes. La reducción de respaldo puede omitir información al final: revisar el texto registrado; el prompt no garantiza precisión semántica. Ninguna prueba automatizada envía mensajes ni llama a APIs externas.
