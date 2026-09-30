# Seguridad

Microsoft Entra ID es la única fuente de autenticación. React utiliza MSAL con Authorization Code + PKCE, sesión en sessionStorage y redirecciones de login/logout; el código no guarda tokens manualmente. FastAPI verifica RS256 con claves públicas obtenidas por discovery, exp, nbf cuando está presente, issuer v2, audience exacta (client ID), tid y scope delegado. Rechaza Graph, tokens v1 y JWT locales. Un ID token no contiene el scope delegado requerido y no autoriza la API.

POST /auth/login fue eliminado. GET /auth/me devuelve oid, nombre y email opcional, sin tokens. La tabla administradores y sus hashes se conservan por compatibilidad de datos, pero no autorizan acceso; seed_admin está retirado. Falta de configuración del backend o fallo de discovery devuelven 503 seguro; token ausente/inválido 401 y scope ausente 403.

Métricas, cartera, historial, generación, scoring y comunicación requieren access token Entra. CORS limita orígenes localhost configurables y excluye `*`; no es sustituto de autenticación. El registro simulado valida canales permitidos y mensajes no vacíos hasta 10,000 caracteres.

Nunca subir `.env`, tokens, contraseñas ni claves. Los contextos Docker excluyen archivos de entorno. VITE_API_URL es público porque se incorpora al JavaScript compilado. Las respuestas de error de Groq no exponen detalles del proveedor; no hay respuesta local de respaldo ni se imprime la excepción del proveedor.

Limitaciones: no hay roles locales ni rate limiting. Asignaciones de usuarios, MFA y acceso condicional se administran en Entra según la cuenta/licencia; sessionStorage es vulnerable si existe XSS; React muestra mensajes como texto sin HTML. Para producción se debe evaluar cookies HttpOnly/CSRF, TLS y controles de acceso adicionales. No compartir puertos fuera de localhost en la demo. Habilitar Groq envía datos del cliente al proveedor: usar datos ficticios y revisar consentimiento antes de datos reales.

La auditoría npm de esta revisión detectó dos vulnerabilidades en herramientas de desarrollo heredadas (Vite 5 / esbuild: una alta y una moderada). La corrección propuesta por npm requiere un salto mayor de Vite; se deja como actualización planificada para preservar compatibilidad. No publicar el servidor de desarrollo. El contenedor final sirve archivos estáticos con Nginx y no contiene el servidor Vite.

Búsqueda, ficha y registro de pagos también requieren scope delegado Entra válido. Groq recibe únicamente contexto necesario: nombre, saldo/deudas/vencimientos, features y riesgo, y pagos recientes. No recibe email, teléfono, JWT, claves ni información del administrador. Las respuestas se renderizan como texto. Se instruye al proveedor a tratar el contexto como datos y a no inventar condiciones financieras; la salida generativa requiere revisión humana.

La aplicación inicia sin GROQ_API_KEY; generación devuelve 503. Los errores del proveedor devuelven 502 y no guardan estrategias. No existe plantilla local. Los pagos usan validación Decimal y bloqueo transaccional PostgreSQL; las columnas Float heredadas se conservan para evitar una conversión riesgosa. Se recomienda una futura migración planificada a Numeric y claves de idempotencia para reintentos de pagos.

## Proveedores de comunicación opcionales

`COMMUNICATIONS_REAL_ENABLED` está deshabilitado por defecto y solo `true` permite envíos con configuración completa. También se verifica dentro de cada adaptador. El endpoint de estado exige autenticación Entra y expone exclusivamente disponibilidad booleana efectiva; no valida claves haciendo peticiones. Credenciales solo en el backend: nunca variables VITE, respuestas, logs ni imágenes.

Los errores se reducen al código fijo `ProviderRequestFailed`; no se registra el texto de excepciones, URLs, cabeceras, SID, JWT, contenido ni destinatarios. Se deshabilitan los loggers HTTP de Twilio y SendGrid que pueden incluir SID, cabeceras o payload. No habilitar trazas HTTP de dependencias en producción. `external_id` queda en base para conciliación y no se expone al frontend.

Los tests eliminan configuración heredada, impiden cargar `.env`, reemplazan clientes SDK por mocks y bloquean conexiones de sockets. Un fallo de proveedor no se convierte en simulación: queda real/Fallido para auditoría. No se reintenta automáticamente. El bloqueo del botón evita solicitudes simultáneas desde el componente, pero no sustituye idempotencia distribuida. Antes de habilitar envíos reales verificar destinatarios, permisos de contacto y presupuesto de la cuenta.

## Política de acceso Entra

Se utiliza un único App Registration para SPA y API, sin client secret. Todo usuario del tenant que obtenga access_as_user puede acceder a las operaciones administrativas: el rótulo de la pantalla no asigna un rol. Para limitarlo al personal autorizado, configurar asignación requerida y usuarios/grupos permitidos en la aplicación empresarial correspondiente, y consentimiento del scope según la política del tenant. La tabla legacy no se consulta.

Discovery/JWKS se consultan únicamente por HTTPS en login.microsoftonline.com, sin reenviar tokens ni seguir redirecciones. Caché por proceso de 1 hora y refresco por kid desconocido con intervalo mínimo de 60 segundos, también tras fallos, para limitar solicitudes. Durante ese intervalo una clave nueva puede devolver 401; no se aceptan claves caducadas tras fallo de refresco. No se registran tokens ni respuestas completas.

Logout oculta y desmonta los datos antes de logoutRedirect. pagehide guarda una pantalla sin datos para BFCache; pageshow/popstate y retorno de visibilidad revalidan cuenta y /auth/me. El logout de Microsoft no revoca instantáneamente todos los access tokens ya emitidos; la API sigue verificando su expiración. No existe refresh manual ni tokens en PostgreSQL.
