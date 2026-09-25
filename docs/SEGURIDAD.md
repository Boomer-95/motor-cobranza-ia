# Seguridad

JWT HS256 con expiración de 60 minutos y clave en `JWT_SECRET_KEY`. Se valida firma, expiración, sujeto y administrador activo. `/auth/me` devuelve solo nombre y username. El frontend borra la sesión al recibir 401; el cierre de sesión elimina el token local, pero no revoca copias ya emitidas.

Contraseñas hasheadas con passlib/bcrypt. bcrypt se fija a una versión compatible con passlib; acepta hasta 72 bytes. Los administradores se crean únicamente por `python -m app.seed_admin` mediante variables de entorno, sin registro público.

Métricas, cartera, historial, generación, scoring y comunicación requieren JWT. CORS limita orígenes localhost configurables y excluye `*`; no es sustituto de autenticación. El registro simulado valida canales permitidos y mensajes no vacíos hasta 10,000 caracteres.

Nunca subir `.env`, tokens, contraseñas ni claves. Los contextos Docker excluyen archivos de entorno. VITE_API_URL es público porque se incorpora al JavaScript compilado. Las respuestas de error de Groq no exponen detalles del proveedor; no hay respuesta local de respaldo ni se imprime la excepción del proveedor.

Limitaciones: falta rate limiting, MFA, revocación centralizada y roles. localStorage es vulnerable si existe XSS; React muestra mensajes como texto sin HTML. Para producción se debe evaluar cookies HttpOnly/CSRF, TLS y controles de acceso adicionales. No compartir puertos fuera de localhost en la demo. Habilitar Groq envía datos del cliente al proveedor: usar datos ficticios y revisar consentimiento antes de datos reales.

La auditoría npm de esta revisión detectó dos vulnerabilidades en herramientas de desarrollo heredadas (Vite 5 / esbuild: una alta y una moderada). La corrección propuesta por npm requiere un salto mayor de Vite; se deja como actualización planificada para preservar compatibilidad. No publicar el servidor de desarrollo. El contenedor final sirve archivos estáticos con Nginx y no contiene el servidor Vite.

Búsqueda, ficha y registro de pagos también requieren administrador activo. Groq recibe únicamente contexto necesario: nombre, saldo/deudas/vencimientos, features y riesgo, y pagos recientes. No recibe email, teléfono, JWT, claves ni información del administrador. Las respuestas se renderizan como texto. Se instruye al proveedor a tratar el contexto como datos y a no inventar condiciones financieras; la salida generativa requiere revisión humana.

La aplicación inicia sin GROQ_API_KEY; generación devuelve 503. Los errores del proveedor devuelven 502 y no guardan estrategias. No existe plantilla local. Los pagos usan validación Decimal y bloqueo transaccional PostgreSQL; las columnas Float heredadas se conservan para evitar una conversión riesgosa. Se recomienda una futura migración planificada a Numeric y claves de idempotencia para reintentos de pagos.
