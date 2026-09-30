# Mantenimiento

## Respaldos

Con Compose: `docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > respaldo.sql`. El archivo contiene datos de clientes: protegerlo, no subirlo a Git y probar restauración en una base separada. Respaldar también el modelo joblib antes de entrenar. No ejecutar `docker compose down -v` si se necesitan los datos.

## Dependencias

Usar un entorno virtual y `npm ci` para respetar el lockfile frontend. Revisar actualizaciones en rama, ejecutar pytest y build antes de actualizar producción. Se conservó el inventario Python original para reducir cambios; incluye paquetes transitivos que deberán revisarse con un lock reproducible en una mejora posterior. La autenticación ya no depende de passlib/bcrypt ni python-jose; PyJWT valida tokens Microsoft.

## Modelo y datos

Los seeds son para demostración, no para poblar producción. Reentrenar con `python -m app.ml.train_model`, revisar métricas y reiniciar backend; conservar versión anterior para reversión. Hoy los datos son sintéticos; no atribuir precisión real al reporte. Cambios de esquema requieren migración explícita: create_all no altera columnas.

## Claves y logs

La sesión se administra en Microsoft Entra ID. No existen claves JWT propias ni contraseñas locales activas; seed_admin es un comando retirado que no modifica datos. Rotar GROQ_API_KEY y las claves de comunicaciones desde sus proveedores si se utilizan.

Consultar `docker compose logs --tail=100 backend`. No registrar tokens, cuerpos de login, claves ni respuestas completas del proveedor. Evitar compartir logs con datos personales. Revisar espacio del volumen PostgreSQL y respaldos.

## Próximas mejoras

Migraciones, paginación, auditoría, limitación de login, montos Numeric, versiones reproducibles del modelo y evaluación real. Groq es obligatorio para generar estrategias; el cálculo ML funciona sin Groq.

## Aplicar esta actualización sin perder datos

Primero respaldar con el comando anterior. No cambiar el nombre del proyecto Compose ni el volumen existente. Con PostgreSQL iniciado:

```bash
docker compose config --quiet
docker compose build backend frontend
docker compose stop backend
docker compose run --rm --no-deps backend python -m app.migrate
docker compose up -d
```

Si la migración falla, no iniciar el backend actualizado hasta resolverla. Es idempotente: se puede volver a ejecutar. En local: `python -m app.migrate` antes de uvicorn. Agrega deuda_id anulable/FK/índice en pagos, probabilidad_pago_a_tiempo anulable en clientes y contexto_hash anulable en historial_mensajes. No reconstruye tablas ni asocia pagos antiguos arbitrariamente. En PostgreSQL todos los cambios ocurren en una transacción. Las columnas nuevas se pueden conservar si se revierte al código anterior.

La clave GROQ_API_KEY sigue viniendo del entorno y Compose usa `${GROQ_API_KEY:-}`. No es necesaria para iniciar ni registrar pagos; sí para generar estrategias. Reiniciar backend después de cambiar el entorno. El despliegue no ejecuta seeds automáticamente.

Opcional, solo en demo: ejecutar `docker compose exec backend python -m app.seed` y luego `docker compose exec backend python -m app.ml.seed_historial`. Son idempotentes por cliente y preservan clientes/deudas/pagos previos. El historial es simulado y no altera saldos. No ejecutar seeds en paralelo.

## Actualización de comunicaciones y CI

Esta actualización agrega a comunicaciones: modo VARCHAR(16), estado VARCHAR(16), provider VARCHAR(16), external_id VARCHAR(255) y error_tecnico VARCHAR(64), todas anulables. Aplicar `python -m app.migrate` antes de iniciar el backend actualizado; en Docker usar el procedimiento anterior. Es aditiva e idempotente y conserva valores históricos. No se ha ejecutado contra la base del usuario durante el desarrollo.

Mantener `COMMUNICATIONS_REAL_ENABLED=false` en demo. Para habilitar un canal, configurar variables de `.env.example` manualmente, verificar remitentes/capacidades en el proveedor y finalmente activar `true`. Reiniciar backend; con Compose recrearlo para recoger el entorno. Desactivar el interruptor vuelve a simulación incluso si quedan credenciales. Rotar claves desde el proveedor sin pegarlas en logs ni Git. Revisar Pendiente/Fallido y el panel del proveedor antes de reintentar; un timeout no garantiza que no hubo envío.

SDK directos: twilio 9.11.2 y sendgrid 6.12.5 sobre Python 3.12. No se rehízo el inventario heredado. CI instala requirements y requirements-dev, usa SQLite aislada sin secretos, ejecuta pytest/compileall/pip check, lint/build React y construye ambas imágenes sin push. Para reproducir localmente usar el venv, `pytest`, `python -m compileall -q app tests`, `python -m pip check`, `npm run lint --prefix frontend-react`, `npm run build --prefix frontend-react` y ambos `docker build` del workflow. Los builds no usan `.env` ni ejecutan envíos.

## Despliegue de autenticación Entra

No requiere migración de base ni borrar administradores. Agregar las siete variables Entra indicadas en README; CLIENT_ID debe coincidir en SPA y API. Eliminar manualmente del entorno JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD y ADMIN_NOMBRE si ya no se usan fuera del proyecto. No se modificó el .env del usuario.

Después de configurar, ejecutar `docker compose config --quiet`, `docker compose build backend frontend` y `docker compose up -d backend frontend`. VITE_* se incorpora en compilación: reiniciar el contenedor frontend sin reconstruir no actualiza esos valores. No ejecutar seed_admin ni eliminar volúmenes. Mantener el interruptor de comunicaciones en false para las pruebas de login.

MSAL se inicializa una sola vez mediante MsalProvider, que procesa el redirect. Si faltan variables frontend se muestra “Microsoft Entra ID no está configurado.”; el build de CI sigue funcionando sin IDs. Revisar issuer/audience/scope y versión v2 desde la configuración Entra sin copiar tokens a logs o herramientas públicas. Para una prueba completa se requiere acceso interactivo del usuario a Microsoft; pytest utiliza claves RSA efímeras y discovery/JWKS mockeados.
