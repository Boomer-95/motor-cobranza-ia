# QA

Desde la raíz: `source venv/bin/activate`, `python -m pip install -r requirements-dev.txt` y `pytest`.

Las fixtures establecen variables temporales antes de importar la app, deshabilitan dotenv, generan una clave JWT aleatoria y reemplazan la dependencia DB por SQLite en memoria. No se conecta a PostgreSQL real. Groq se desactiva o se reemplaza con AsyncMock; no se realizan llamadas externas.

Se validan: login incorrecto y correcto; rutas protegidas sin token; `/auth/me`; token vencido y malformado; cartera vencida con fechas pasadas/futuras/hoy y saldo cero; recuperación independiente de vencimiento; orden de cartera; segmentos alto/medio/bajo y persistencia; modelo ausente; historial vacío y guardado; fallback local y Groq simulado; los cuatro canales y validación de cliente/canal/mensaje.

Comprobaciones adicionales: `python -m compileall -q app tests`, `python -m pip check`, `npm run build --prefix frontend-react`. Docker debe verificarse con `docker compose build` en un equipo con daemon disponible. No imprimir `docker compose config` con el entorno real porque expande secretos.

Prueba manual: crear administrador/datos, entrar, revisar métricas, procesar cliente, comprobar score y plantilla, consultar historial, registrar comunicación en cada canal y cerrar sesión. Repetir con ID inexistente, backend detenido, token expirado y pantalla móvil. SQLite no sustituye una prueba de integración PostgreSQL, y el build no sustituye una prueba de navegador.

La auditoría `npm audit` identificó dos avisos heredados en Vite/esbuild (uno alto y uno moderado). Se documentan en SEGURIDAD.md; no se aplicó `npm audit fix --force`, que cambia la versión mayor de Vite.

## Resultado de esta revisión

24 pruebas aprobadas, incluyendo inferencia con el artefacto ML existente, cuentas desactivadas y límite bcrypt. Compilación Python, pip check, lint React y build Vite correctos. Se observaron dos avisos de deprecación en dependencias (Starlette/AnyIO y passlib/crypt); no impiden ejecutar Python 3.12. La suite se ejecutó fuera del sandbox porque este bloqueaba el portal de hilos de TestClient. Compose validado con variables temporales, sin leer el .env del usuario.
