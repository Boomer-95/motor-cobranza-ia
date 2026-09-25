// Cambia esto si tu API corre en otra URL. En Docker local, sigue siendo
// localhost porque el navegador (no el contenedor) es quien hace la llamada.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

let manejadorSesionExpirada = null;

// App.jsx registra aquí qué hacer cuando el token ya no es válido (401).
export function setManejadorSesionExpirada(fn) {
  manejadorSesionExpirada = fn;
}

export function getToken() {
  return localStorage.getItem('token');
}

export function guardarToken(token) {
  localStorage.setItem('token', token);
}

export function borrarToken() {
  localStorage.removeItem('token');
}

/**
 * Wrapper de fetch que:
 * 1. Agrega el header Authorization con el JWT guardado.
 * 2. Si el servidor responde 401 (token vencido/ inválido), limpia la
 *    sesión y dispara el manejador para regresar al login.
 */
export async function apiFetch(path, options = {}) {
  const { publico = false, ...fetchOptions } = options;
  const token = publico ? null : getToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers });

  if (response.status === 401 && !publico) {
    borrarToken();
    if (manejadorSesionExpirada) manejadorSesionExpirada();
  }

  return response;
}
