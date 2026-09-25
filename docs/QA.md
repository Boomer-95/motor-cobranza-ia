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

Las fixtures deshabilitan dotenv y usan SQLite en memoria, JWT temporal y Groq mockeado. No leen .env, no acceden a PostgreSQL real ni hacen llamadas al proveedor. Se conserva cobertura de login, JWT, comunicación simulada y modelo existente.

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
