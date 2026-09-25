# Motor Inteligente de Cobranza para PluriOne

MVP universitario para administrar una cartera, priorizar clientes y preparar estrategias de contacto. Se amplía el proyecto existente con historial visible y comunicaciones simuladas, conservando FastAPI, React, PostgreSQL, JWT, Groq y Random Forest.

## Objetivo y alcance

Ayudar al administrador a decidir a quién contactar y preparar un mensaje empático. El proyecto se puede desarrollar y demostrar con presupuesto de **$0 MXN**, usando software local y sujeto a las cuotas de la cuenta de Groq. Azure fue sustituido por soluciones gratuitas debido al presupuesto $0 del MVP. No se requieren Twilio, SendGrid ni servicios de pago.

Incluye login privado, métricas, segmentación Alto/Medio/Bajo, prioridad por riesgo × saldo, generación y almacenamiento de estrategias, historial por cliente, registro simulado de Email/SMS/WhatsApp/Llamada y cierre de sesión.

## Arquitectura y tecnologías

```text
React + Vite -> api.js -> FastAPI -> SQLAlchemy -> PostgreSQL
                            |-> JWT / passlib + bcrypt
                            |-> RandomForestClassifier (joblib local)
                            |-> Groq para estrategias personalizadas
Docker: navegador -> Nginx -> /backend -> FastAPI -> PostgreSQL
```

Python 3.12, Node 20, React 18, Vite, FastAPI, SQLAlchemy, PostgreSQL 16, scikit-learn, pandas, NumPy, SDK compatible OpenAI para Groq, python-jose, pytest, Docker Compose y Nginx. Git/GitHub para control de versiones.

```text
app/
  main.py                 API y operaciones de cobranza
  auth.py, database.py     JWT y sesiones SQLAlchemy
  models.py               Cliente, Deuda, Pago, Administrador, historial y comunicación
  seed_admin.py, seed.py   Inicialización local
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
| JWT_SECRET_KEY | Clave aleatoria privada para firmar JWT |
| ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_NOMBRE | Administrador creado por script |
| GROQ_API_KEY / GROQ_MODEL | Credencial necesaria para estrategias y modelo de Groq |
| CORS_ORIGINS | Orígenes permitidos separados por coma; sin comodín |
| POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB | Inicialización de PostgreSQL en Compose |
| DB_HOST | Compose lo fija a `db`; construye la URL de forma segura y tiene prioridad sobre DATABASE_URL |
| VITE_API_URL | URL pública del backend; nunca debe contener secretos |

Los JWT duran 60 minutos. Solo `python -m app.seed_admin` crea administradores; no existe registro público. Contraseñas con bcrypt. El frontend valida `/auth/me` y elimina el token al recibir 401.

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

Edita `.env` localmente. Completa `DATABASE_URL` con estructura `postgresql+psycopg2://USUARIO:CONTRASENA@localhost:5432/BASE`, `JWT_SECRET_KEY` y las variables del administrador. Usa una contraseña de hasta 72 bytes (límite bcrypt) y una clave JWT aleatoria, por ejemplo generada localmente con `python -c "import secrets; print(secrets.token_hex(32))"`. No compartas esos valores.

```bash
python -m app.migrate
python -m app.seed_admin
python -m app.seed
python -m app.ml.seed_historial
# Opcional: reemplaza el modelo existente; respáldalo antes.
python -m app.ml.train_model
uvicorn app.main:app --reload
```

Los scripts crean tablas faltantes y evitan repetir sus datos cuando ya existen. `seed_admin` no cambia contraseñas existentes. Los seeds son exclusivamente para una base de demostración. `create_all` no migra tablas existentes.

En otra terminal:

```bash
cd frontend-react
npm ci
npm run dev
```

Abre http://localhost:5173. La API local predeterminada es http://127.0.0.1:8000. Para cambiarla: `VITE_API_URL=http://localhost:8000 npm run dev`. Vite no lee automáticamente el `.env` de la raíz desde su subcarpeta. Documentación interactiva: http://127.0.0.1:8000/docs.

## Docker

Con PostgreSQL ya iniciado (`docker compose up -d db` si es una instalación nueva), completa en tu entorno o `.env` las variables `POSTGRES_*`, `JWT_SECRET_KEY` y `ADMIN_*`. Compose exige los secretos y no incluye valores predeterminados para ellos. No copies `.env` en las imágenes.

```bash
docker compose build backend frontend
docker compose stop backend
docker compose run --rm --no-deps backend python -m app.migrate
docker compose up -d
docker compose exec backend python -m app.seed_admin
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
7. Desde Resultado del análisis puedes procesar o regenerar si hay deuda activa y abrir subsecciones de pagos y comunicaciones. Revisa o edita el mensaje antes de registrarlo; el historial muestra canal, fecha, mensaje y estado simulado. No hay envío externo.

“Saldo vencido” suma saldos positivos con estatus `En Mora` o fecha anterior a hoy. Es dinero que los clientes deben a PluriOne. `cartera_vencida` conserva su clave API. “Clientes con estrategia IA” usa `COUNT(DISTINCT cliente_id)` sobre el historial conservado; regenerar no aumenta el conteo del mismo cliente. Los registros anteriores se conservan, incluso si su origen no está verificado. “Clientes sin evaluar” usa segmento `No definido` o nulo, nunca score cero. Deudores activos cuenta clientes con saldo positivo; `total_clientes` cuenta todos. Recuperación sigue siendo (monto original − saldo) / monto original, no una suma del historial sintético.

## Endpoints principales

Todos salvo login requieren `Authorization: Bearer TOKEN`.

| Método | Ruta | Función |
|---|---|---|
| POST | /auth/login | Formulario username/password |
| GET | /auth/me | Identidad del administrador |
| GET | /api/metricas | Resumen de cartera |
| GET | /api/clientes | query, segmento, analizado, estatus_deuda, orden |
| GET | /api/clientes/{cliente_id} | Ficha financiera, deudas, pagos y estrategia |
| POST | /api/deudas/{deuda_id}/pagos | JSON `{"monto": 3000}`; registra pago y recalcula ML |
| GET | /api/cartera-priorizada | Orden descendente por riesgo × saldo |
| POST | /ia/analizar-riesgo/{cliente_id} | Calcula ML y genera/reutiliza mensaje; `?regenerar=true` fuerza Groq |
| POST | /ia/calcular-riesgo/{cliente_id} | Calcula y guarda score/segmento |
| GET | /ia/historial/{cliente_id} | Historial más reciente primero; 404 si vacío |
| POST | /api/comunicaciones | JSON: cliente_id, canal y mensaje; respuesta 201 simulada |

En comunicaciones `exitoso=false` significa que no hubo entrega externa. La respuesta confirma `simulada=true`; `fecha_envio` conserva el tipo Date existente y representa el día de registro de la simulación.

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

No hay envíos reales, registro público, refresh tokens, limitación de intentos de login, migraciones automáticas ni auditoría completa. JWT en localStorage exige protegerse frente a XSS. El saldo usa Float heredado; migrar a Numeric con planificación. Groq recibe nombre, deudas activas, features, riesgo y hasta ocho pagos recientes: usar únicamente clientes ficticios durante la demo. El modelo sintético requiere validación real, calibración y análisis de sesgo antes de decisiones operativas. Se requiere HTTPS para cualquier despliegue fuera de localhost.

Futuro: migraciones Alembic, paginación, roles, auditoría, pruebas PostgreSQL y E2E, auditoría de pagos y reentrenamiento validado. No se agregaron dependencias cloud ni se hizo una limpieza agresiva del archivo de dependencias existente.

## Migración compatible

`python -m app.migrate` agrega tres columnas anulables: `pagos.deuda_id` (FK a deudas, con índice), `clientes.probabilidad_pago_a_tiempo` y `historial_mensajes.contexto_hash`. Es aditiva e idempotente y funciona también sobre una base nueva. `create_all` por sí solo no modifica tablas existentes. Ejecuta la migración antes de iniciar el backend actualizado. No intenta asociar pagos históricos a deudas por inferencia. No borra tablas, datos ni volúmenes. Consulta [MANTENIMIENTO.md](docs/MANTENIMIENTO.md) para respaldo y despliegue.

Los seeds agregan aproximadamente 15 clientes ficticios con emails `example.invalid`, reconocen los tres emails heredados y no modifican sus datos. Cada cliente nuevo y sus deudas se crean juntos; los clientes existentes se omiten para no reponer deudas pagadas. El historial sintético usa semilla por cliente y fechas fijas; omite clientes con pagos previos y nunca puebla clientes ajenos al catálogo demo.
