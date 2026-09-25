# Mantenimiento

## Respaldos

Con Compose: `docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > respaldo.sql`. El archivo contiene datos de clientes: protegerlo, no subirlo a Git y probar restauración en una base separada. Respaldar también el modelo joblib antes de entrenar. No ejecutar `docker compose down -v` si se necesitan los datos.

## Dependencias

Usar un entorno virtual y `npm ci` para respetar el lockfile frontend. Revisar actualizaciones en rama, ejecutar pytest y build antes de actualizar producción. Se conservó el inventario Python original para reducir cambios; incluye paquetes transitivos que deberán revisarse con un lock reproducible en una mejora posterior. passlib/bcrypt deben actualizarse conjuntamente con pruebas de hashes existentes.

## Modelo y datos

Los seeds son para demostración, no para poblar producción. Reentrenar con `python -m app.ml.train_model`, revisar métricas y reiniciar backend; conservar versión anterior para reversión. Hoy los datos son sintéticos; no atribuir precisión real al reporte. Cambios de esquema requieren migración explícita: create_all no altera columnas.

## Claves y logs

Rotar JWT_SECRET_KEY mediante el gestor local de entorno y reiniciar backend; invalida los tokens previos. Rotar GROQ_API_KEY desde la cuenta del proveedor si se utiliza. seed_admin no cambia contraseñas existentes: cualquier rotación de administrador requiere actualización controlada del hash, nunca guardar texto plano en DB.

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
