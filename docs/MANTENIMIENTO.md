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

Migraciones, paginación, auditoría, limitación de login, montos Numeric, versiones reproducibles del modelo y evaluación real. Mantener el modo local para demostraciones sin red ni gasto.
