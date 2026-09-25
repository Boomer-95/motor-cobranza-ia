# Arquitectura

React/Vite conserva sidebar, tablas y paneles empresariales. FastAPI autentica cada endpoint con JWT y SQLAlchemy accede a PostgreSQL. Se conservan login, comunicación simulada, historial y cartera priorizada.

Flujo: PostgreSQL (deudas + pagos) → features → Random Forest → probabilidad, score y segmento → contexto mínimo → Groq → HistorialMensaje. El modelo no escribe mensajes; Groq no calcula scores.

GET /api/clientes permite query por nombre (sin distinguir mayúsculas), ID y folio CL-000001, segmento, analizado, estatus_deuda y orden (prioridad/saldo/atraso/vencimiento/nombre). Los folios se derivan del ID, no requieren columna. Las deudas activas tienen saldo positivo. La cartera muestra el vencimiento activo más antiguo, para priorizar vencidas; los días se calculan desde la fecha actual del servidor. El detalle devuelve todas las deudas, pagos, la última estrategia y las comunicaciones del cliente, ordenadas por fecha e ID descendentes. Cada comunicación incluye canal, fecha, mensaje y estado. Los registros históricos marcados exitosos se conservan sin afirmar entrega verificada.

POST /api/deudas/{id}/pagos valida monto decimal positivo de hasta dos decimales, saldo y estado. La fecha es el día del servidor; no se aceptan fechas retroactivas. Bloquea primero Cliente y después Deuda con SELECT FOR UPDATE, registra Pago, actualiza saldo/estatus, hace flush y recalcula ML antes de commit. Todos los pagos de un cliente se serializan en PostgreSQL, aunque correspondan a distintas deudas. Cualquier error hace rollback. No hay reintento automático de pagos; ante una respuesta perdida consultar el historial antes de volver a enviar.

POST /ia/analizar-riesgo/{id} primero comprueba saldo. Sin deuda limpia score/probabilidad a NULL y segmento a Sin deuda, sin ejecutar Random Forest ni Groq. Con deuda y estrategia previa devuelve la última guardada; solamente regenerar=true pide una nueva versión. Sin estrategia calcula ML y solicita Groq (timeout 20 segundos, sin reintentos, temperature 0.5). La huella del contexto se conserva como referencia de generación; ya no dispara regeneraciones automáticas. Errores del proveedor devuelven 502 sin guardar mensajes; si una generación requiere clave y falta, devuelve 503. No hay plantilla local.

Toda la fila selecciona al cliente, llena el ID y desplaza a #operacion. El panel Resultado del análisis consulta únicamente GET /api/clientes/{id}; no calcula ML ni llama Groq. Muestra resumen financiero, fechas, riesgo y estrategia guardada; deudas/pagos/comunicaciones quedan en subsecciones compactas desplegables del mismo panel. No hay ficha debajo de cartera. Los clientes sin estrategia muestran No generada y Sin calcular donde corresponde. Sin deuda se muestra No aplica — sin deuda activa y no hay botones de generación.

GET de detalle expone sin_deuda_activa, tiene_estrategia y fecha_ultima_estrategia. En consultas, los clientes sin saldo muestran score/probabilidad nulos aunque tengan valores históricos; GET no modifica la base. Al procesarlos explícitamente o liquidar su última deuda se persiste la limpieza. Si quedan otras deudas positivas, el pago sigue recalculando ML con las seis features. La columna score_riesgo ya era nullable; este ajuste no requiere migración adicional.

La tabla de cobranza usa GET /api/clientes?solo_con_deuda=true más sus filtros. GET /api/clientes sin ese parámetro sigue siendo un listado general. Clientes liquidados se pueden consultar por ID en Operación de Cobranza.


Métricas: saldo vencido positivo por fecha o estatus; clientes con estrategia mediante COUNT DISTINCT; sin evaluar por segmento; deudores activos por saldo. Las claves anteriores se conservan y se agregan total_clientes, clientes_sin_evaluar y saldo_pendiente.

app.migrate agrega columnas anulables sin eliminar registros. Se ejecuta explícitamente antes de desplegar; create_all no sustituye la migración. PostgreSQL usa bloqueo asesor transaccional para evitar dos migraciones simultáneas. Docker conserva el volumen postgres_data; Nginx sirve React y hace proxy /backend.
