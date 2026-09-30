import { InteractionRequiredAuthError } from '@azure/msal-browser';
import { apiScope, cuentaActiva, msalInstance } from './msalConfig';

let interaccionPendiente = false;
export async function getAccessToken() {
  const account = cuentaActiva();
  if (!account || interaccionPendiente) throw new Error('Inicia sesión con Microsoft.');
  const request = { scopes: [apiScope], account };
  try {
    const result = await msalInstance.acquireTokenSilent(request);
    if (cuentaActiva()?.homeAccountId !== account.homeAccountId) throw new Error('La sesión cambió.');
    return result.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError && !interaccionPendiente) {
      interaccionPendiente = true;
      try { await msalInstance.acquireTokenRedirect(request); }
      catch { interaccionPendiente = false; }
    }
    throw new Error('No se pudo validar la sesión Microsoft.');
  }
}
