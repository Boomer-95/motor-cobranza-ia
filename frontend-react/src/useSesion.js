import { useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import { apiFetch, setManejadorSesionExpirada } from './api';
import { bloquearSesion, cuentaActiva } from './auth/msalConfig';

export default function useSesion() {
  const { instance, inProgress, accounts } = useMsal();
  const [sesion, setSesion] = useState({ estado: 'validando', admin: null, errorSesion: '' });
  const revision = useRef(0);
  const pendiente = useRef(null);
  const invalidar = useCallback(() => {
    revision.current += 1;
    pendiente.current?.abort();
    pendiente.current = null;
  }, []);
  const denegar = useCallback(() => {
    invalidar();
    bloquearSesion();
    setSesion({ estado: 'no-autenticado', admin: null,
      errorSesion: 'No se pudo autorizar el acceso. Comprueba tu cuenta y la configuración Entra.' });
  }, [invalidar]);
  const cerrar = useCallback(async () => {
    const account = cuentaActiva();
    invalidar(); bloquearSesion();
    setSesion({ estado: 'no-autenticado', admin: null, errorSesion: '' });
    try { await instance.logoutRedirect({ account }); }
    catch {
      setSesion({ estado: 'no-autenticado', admin: null,
        errorSesion: 'No se pudo completar el cierre en Microsoft. Recarga y vuelve a cerrar sesión.' });
    }
  }, [instance, invalidar]);
  const validar = useCallback(async () => {
    invalidar();
    setSesion({ estado: 'validando', admin: null, errorSesion: '' });
    if (inProgress !== InteractionStatus.None) return;
    const account = cuentaActiva();
    if (!account) {
      setSesion({ estado: 'no-autenticado', admin: null, errorSesion: '' });
      return;
    }
    const actual = revision.current;
    const controller = new AbortController();
    pendiente.current = controller;
    try {
      const response = await apiFetch('/auth/me', { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error();
      const admin = await response.json();
      if (typeof admin.id !== 'string' || !admin.id) throw new Error();
      if (actual !== revision.current || cuentaActiva()?.homeAccountId !== account.homeAccountId) return;
      pendiente.current = null;
      setSesion({ estado: 'autenticado', admin, errorSesion: '' });
    } catch {
      if (actual === revision.current) denegar();
    }
  }, [inProgress, invalidar, denegar]);

  useEffect(() => {
    setManejadorSesionExpirada(denegar);
    void validar();
    const restaurar = () => flushSync(() => { void validar(); });
    const ocultar = () => flushSync(() => {
      invalidar(); setSesion({ estado: 'validando', admin: null, errorSesion: '' });
    });
    const visibilidad = () => { if (document.visibilityState === 'visible') restaurar(); };
    window.addEventListener('pageshow', restaurar);
    window.addEventListener('popstate', restaurar);
    window.addEventListener('pagehide', ocultar);
    document.addEventListener('visibilitychange', visibilidad);
    return () => {
      invalidar(); setManejadorSesionExpirada(null);
      window.removeEventListener('pageshow', restaurar);
      window.removeEventListener('popstate', restaurar);
      window.removeEventListener('pagehide', ocultar);
      document.removeEventListener('visibilitychange', visibilidad);
    };
  }, [accounts, denegar, invalidar, validar]);

  // Nunca renderizar un dashboard antiguo durante inicialización/redirect/logout.
  return { ...sesion, estado: inProgress !== InteractionStatus.None ? 'validando'
    : sesion.estado === 'autenticado' && !cuentaActiva() ? 'no-autenticado' : sesion.estado, cerrar };
}
