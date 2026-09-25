import { useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { apiFetch, borrarToken, getToken, setManejadorSesionExpirada } from './api';

export default function useSesion() {
  const [sesion, setSesion] = useState({ estado: 'validando', admin: null });
  const revision = useRef(0);
  const pendiente = useRef(null);

  const invalidar = useCallback(() => {
    revision.current += 1;
    pendiente.current?.abort();
    pendiente.current = null;
  }, []);

  const cerrar = useCallback(() => {
    invalidar();
    borrarToken();
    setSesion({ estado: 'no-autenticado', admin: null });
  }, [invalidar]);

  const validar = useCallback(async () => {
    invalidar();
    const actual = revision.current;
    const token = getToken();
    if (!token) {
      setSesion({ estado: 'no-autenticado', admin: null });
      return;
    }
    setSesion({ estado: 'validando', admin: null });
    const controller = new AbortController();
    pendiente.current = controller;
    try {
      const response = await apiFetch('/auth/me', { signal: controller.signal, cache: 'no-store' });
      if (response.status !== 200) throw new Error('Sesión no válida');
      const admin = await response.json();
      if (!admin || typeof admin.username !== 'string' || !admin.username) {
        throw new Error('Usuario no válido');
      }
      if (actual !== revision.current) return;
      if (getToken() !== token) return validar();
      pendiente.current = null;
      setSesion({ estado: 'autenticado', admin });
    } catch {
      if (actual !== revision.current) return;
      if (getToken() !== token) return validar();
      cerrar();
    }
  }, [cerrar, invalidar]);

  useEffect(() => {
    setManejadorSesionExpirada(cerrar);
    validar();
    // Confirmar también en pageshow normal; persisted (BFCache) nunca reutiliza
    // la autorización anterior. flushSync retira el dashboard antes del repintado.
    const restaurar = () => flushSync(() => { void validar(); });
    const ocultar = () => flushSync(() => {
      invalidar();
      setSesion({ estado: 'validando', admin: null });
    });
    const visibilidad = () => {
      if (document.visibilityState === 'visible') restaurar();
    };
    const almacenamiento = (event) => {
      if (event.key === 'token' || event.key === null) restaurar();
    };
    window.addEventListener('pageshow', restaurar);
    window.addEventListener('popstate', restaurar);
    // Guardar en BFCache una pantalla sin datos sensibles.
    window.addEventListener('pagehide', ocultar);
    window.addEventListener('storage', almacenamiento);
    document.addEventListener('visibilitychange', visibilidad);
    return () => {
      invalidar();
      setManejadorSesionExpirada(null);
      window.removeEventListener('pageshow', restaurar);
      window.removeEventListener('popstate', restaurar);
      window.removeEventListener('pagehide', ocultar);
      window.removeEventListener('storage', almacenamiento);
      document.removeEventListener('visibilitychange', visibilidad);
    };
  }, [cerrar, invalidar, validar]);

  return { ...sesion, validar, cerrar };
}
