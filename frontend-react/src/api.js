import { getAccessToken } from './auth/getAccessToken';
import { cuentaActiva } from './auth/msalConfig';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
let manejadorSesionExpirada = null;
export function setManejadorSesionExpirada(fn) { manejadorSesionExpirada = fn; }

export async function apiFetch(path, options = {}) {
  const accountId = cuentaActiva()?.homeAccountId;
  const token = await getAccessToken();
  if (options.signal?.aborted || cuentaActiva()?.homeAccountId !== accountId) {
    throw new Error('La sesión cambió.');
  }
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if ((response.status === 401 || response.status === 403) && !options.signal?.aborted
      && cuentaActiva()?.homeAccountId === accountId) manejadorSesionExpirada?.();
  return response;
}
