# Frontend de cobranza

Usar un solo frontend durante cada ejecución y prueba de sesión:

- Docker/Nginx: http://localhost:8080
- Desarrollo Vite: http://localhost:5173

Son orígenes diferentes: cada puerto tiene su propio `localStorage`. No se
comparte ni se borra la sesión entre puertos. No utilizarlos simultáneamente
para probar la misma sesión.

## Sesión e historial

La aplicación comienza validando. Sin token muestra Login; con token consulta
`/auth/me` sin caché y solo monta el dashboard después de un 200 con usuario
válido. Cualquier fallo de validación elimina el token y vuelve al Login.
El login guarda el JWT y pasa por esta misma validación.

`pageshow` (incluido `persisted=true` desde BFCache), `popstate` y volver a una
pestaña visible comprueban nuevamente la sesión, sin recargar la aplicación.
`pagehide` desmonta el dashboard antes de guardar la página en BFCache.
Los cambios de token en otras pestañas del mismo origen también se detectan.
El historial guarda secciones, nunca autorización.

Cerrar sesión elimina el JWT y el administrador y desmonta el dashboard con
toda su cartera, selección, métricas, resultados e historial. Las respuestas
de validaciones y logins cancelados no pueden restaurar una sesión antigua.
`apiFetch` conserva `Authorization: Bearer` y cierra la sesión ante un 401 de
la sesión actual; un 401 tardío de un token anterior no cierra una sesión nueva.

## Verificación manual

Preparar entradas de historial navegando entre secciones del dashboard.
En DevTools, usar la pestaña Network para comprobar `/auth/me` y ralentizar la
red para verificar que aparece «Validando sesión...» sin mostrar el dashboard.

| Caso | Pasos | Resultado esperado |
| --- | --- | --- |
| A | Login → Dashboard → Cerrar sesión → Atrás | Login |
| B | Login → Dashboard → Atrás → Cerrar sesión → Adelante | Login |
| C | Login → Dashboard → eliminar `token` en Application/Local Storage → Atrás/Adelante | Login |
| D | Con un token expirado, volver al dashboard desde historial | `/auth/me` rechaza el token; se elimina y aparece Login |
| E | Con token válido, recargar | Validando sesión → `/auth/me` 200 → Dashboard |

Para BFCache, salir a otra página en la misma pestaña y volver con Atrás;
comprobar también con la herramienta Back/forward cache del navegador que la
restauración es real. Repetir tras cerrar sesión desde otra pestaña del mismo
origen. Verificar fallos 401, 403 y de conexión en `/auth/me`, así como un 401
en cualquier endpoint protegido. Ninguno debe dejar visible el dashboard.

Validaciones de código: `npm run lint` y `npm run build`.

## Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh
