# Arquitectura

React consume FastAPI mediante `src/api.js`; SQLAlchemy consulta PostgreSQL. JWT HS256 autentica al administrador, y cada ruta sensible resuelve `get_admin_actual` para comprobar token y cuenta activa. No existe alta pública.

El dashboard obtiene métricas y cartera. Procesar cliente llama primero a generación, que guarda `HistorialMensaje`, y luego al cálculo ML, que guarda score y segmento en Cliente. Son operaciones independientes: si el modelo falta, la estrategia permanece guardada y la interfaz lo informa.

Groq se consume mediante AsyncOpenAI con timeout y sin reintentos. El modo local predeterminado y el fallback producen plantillas identificadas. Random Forest se carga desde `app/ml/risk_model.joblib`; no necesita conexión externa.

El historial se consulta por ID y se ordena por fecha e ID descendentes. Comunicación reutiliza el modelo existente: el backend valida canal/cliente/mensaje y registra una simulación con `exitoso=false`. No hay proveedores de mensajería.

Docker Compose arranca PostgreSQL con healthcheck, backend y Nginx. El proxy `/backend` permite usar el mismo origen del frontend. Las tablas faltantes se crean al iniciar FastAPI o ejecutar seeds; no sustituye un sistema de migraciones.
