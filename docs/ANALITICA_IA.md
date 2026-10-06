# Analítica IA · Impacto de Cobranza

El módulo complementa el dashboard existente. Conserva Entra, Groq y proveedores. Todos los endpoints requieren el token Entra habitual. Las consultas calculan el estado actual desde la base; el botón **Actualizar datos** vuelve a consultarlas. No usa WebSockets ni refresco automático.

## Activación y migración

Antes de iniciar el backend actualizado, ejecutar `python -m app.migrate` con la configuración habitual del entorno. Es una migración aditiva e idempotente: añade `comunicaciones.estrategia_id INTEGER NULL REFERENCES historial_mensajes(id)` y su índice; crea `metricas_snapshots`, con importes `NUMERIC(18,2)`, contadores enteros y fecha única. No rellena comunicaciones antiguas ni crea historia previa. No ejecuta seeds ni cambia credenciales.

La ficha envía el identificador de la estrategia utilizada, incluso si se adapta su texto al canal o se edita. La API verifica que la estrategia pertenezca al cliente. Mensajes sin estrategia conservan un identificador nulo.

`GET /api/analitica/evolucion` crea o actualiza el snapshot de hoy. PostgreSQL usa bloqueo transaccional y upsert sobre fecha única; las consultas concurrentes no generan duplicados. El snapshot del día puede cambiar, los anteriores se conservan. El primer snapshot determina la fecha real de inicio, consultable en `resumen.inicio_historico`. No hay una fecha de inicio preestablecida ni se inventan snapshots pasados. Esta estrategia registra **días con consultas**, no garantiza registros en días sin actividad. Para recopilación diaria continua, un proceso programado autenticado puede consultar evolución cada día.

## Periodos y fórmulas

Las tres rutas `/api/analitica/resumen`, `/api/analitica/evolucion` y `/api/analitica/canales` aceptan `dias=30|90|180|365` (30 por defecto); otros valores devuelven 422. El periodo incluye hoy y los `dias-1` días anteriores. Se excluyen pagos futuros, pagos sin fecha, montos no positivos y registros con `se_recuperó != true`.

| Métrica | Definición |
| --- | --- |
| Saldo pendiente | Suma actual de saldos de deudas; comparte cálculo con `/api/metricas`. |
| Saldo / cartera vencida | Suma actual de saldos positivos con estatus En Mora o vencimiento anterior a hoy, igual al dashboard existente. |
| Monto recuperado total | Suma de pagos válidos registrados en el periodo; no se infiere restando saldo al monto original. |
| Porcentaje de recuperación | 100 × pagos del periodo / (pagos del periodo + saldo pendiente actual); cero si el denominador es cero. Es un indicador operativo, no una tasa sobre una cohorte de cartera inicial. El dashboard mantiene su fórmula original. |
| Deudores activos | Clientes distintos con al menos una deuda de saldo positivo actualmente. |
| Clientes de alto riesgo | Deudores activos con `score_riesgo >= 0.66`; no recalcula el modelo. |
| Clientes con estrategia IA | Clientes distintos con estrategia generada durante el periodo. Los snapshots guardan el total histórico disponible. |
| Clientes contactados IA | Clientes distintos con envío válido ligado explícitamente a una estrategia durante el periodo. |
| Clientes con pago post IA | Clientes distintos con al menos un pago del periodo asociado temporalmente a una estrategia. El contacto puede preceder el inicio del periodo hasta la ventana configurada. |
| Recuperación asociada a IA | Suma de esos pagos, cada pago una sola vez. |
| Tasa de pago post IA | 100 × clientes con pago asociado a un contacto del periodo / clientes contactados IA del periodo; cero sin contactos. |
| Recuperación acumulada en evolución | Suma de todos los pagos válidos hasta la fecha de cada snapshot, capturada en ese momento; incluye pagos históricos reales existentes, no snapshots históricos inventados. |

## Asociación temporal y canales

Un candidato requiere el mismo cliente y `estrategia_id IS NOT NULL`, canal Email, SMS o WhatsApp, envío exitoso, modo distinto de simulado y sin estado de fallo. La aceptación del proveedor no prueba entrega. Se excluyen pendientes, fallidos y simulados; los simulados se muestran por separado. Un registro legacy exitoso puede participar si tiene vínculo explícito; ninguno se rellena automáticamente.

La ventana inicial es **7 días**, configurable con `ANALITICA_VENTANA_IA_DIAS` (entero de 1 a 365; valores enteros fuera de rango se limitan a esos extremos). El pago debe ocurrir entre 1 y 7 días después del envío. Dado que `fecha_envio` y `fecha_pago` son DATE, se excluye el mismo día: no se puede demostrar su orden. Entre varios contactos elegibles se elige el más reciente, desempate por id mayor. Cada pago pertenece como máximo a un contacto y un canal; las sumas por canal coinciden con el total asociado.

Por canal se cuentan envíos aceptados del periodo, entregas con `provider_status=delivered|read`, fallos con estado Fallido o status failed/undelivered/bounced/dropped, simulaciones, clientes únicos y pagos asociados. Los pagos se filtran por su fecha, aunque el contacto elegido pueda ser anterior al periodo. No se presenta Llamada como proveedor implementado.

Esto es **recuperación asociada temporalmente a una estrategia IA**, no causalidad demostrada. No hay grupo de control, experimento ni ajuste por factores externos. Los clientes con estrategia, contactados y con pagos no siempre forman una misma cohorte; las gráficas muestran sus definiciones y la tasa usa la cohorte contactada.

## Verificación

1. Ejecutar la migración antes del despliegue (no se ha aplicado automáticamente a la base operativa).
2. Entrar con Microsoft Entra y abrir **Analítica IA** en el menú. Cambiar entre 30/90/180 días y 1 año; pulsar **Actualizar datos**.
3. Verificar estado vacío en una base de pruebas sin registros, un snapshot de hoy tras consultar y fechas reales cuando se acumule historia.
4. En un entorno de pruebas con `COMMUNICATIONS_REAL_ENABLED=false`, enviar desde la ficha y comprobar `estrategia_id`. El registro simulado no incrementa recuperación asociada ni contactos reales. No activar proveedores para esta validación.
5. Ejecutar `python -m pytest`, `python -m compileall app`; en `frontend-react`, `npm test -- --run`, `npm run lint`, `npm run build`; desde raíz `docker compose config --quiet`.

Los tests bloquean la red y utilizan SQLite aislado. La concurrencia PostgreSQL se protege por bloqueo y unicidad pero requiere validación de integración sobre PostgreSQL antes de producción. Los importes fuente siguen siendo Float por compatibilidad: se redondean los pagos a centavos y los snapshots usan Numeric. En carteras grandes la asociación carga pagos y comunicaciones del periodo en memoria; conviene evaluar volumen antes de ampliar el MVP. En SendGrid no existe aquí un callback nuevo: sin estado disponible, entrega permanece sin confirmar. La estrategia histórica puede tener origen no verificable y se conserva la advertencia existente en la ficha.
