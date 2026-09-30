import { PublicClientApplication, EventType } from '@azure/msal-browser';

const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID?.trim();
const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID?.trim();
export const apiScope = import.meta.env.VITE_ENTRA_API_SCOPE?.trim();
const redirectUri = import.meta.env.VITE_ENTRA_REDIRECT_URI?.trim();
const guid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const entraConfigurado = Boolean(guid.test(clientId || '') && guid.test(tenantId || '')
  && apiScope === `api://${clientId}/access_as_user` && /^https?:\/\//.test(redirectUri || ''));

export const msalInstance = entraConfigurado ? new PublicClientApplication({
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri,
    postLogoutRedirectUri: redirectUri,
  },
  cache: { cacheLocation: 'sessionStorage' },
  system: { loggerOptions: { loggerCallback: () => {}, piiLoggingEnabled: false } },
}) : null;

let bloqueada = false;
export function bloquearSesion() { bloqueada = true; }
export function cuentaActiva() {
  if (!msalInstance || bloqueada) return null;
  const accounts = msalInstance.getAllAccounts();
  const active = msalInstance.getActiveAccount();
  if (active && accounts.some(a => a.homeAccountId === active.homeAccountId)) return active;
  if (accounts.length === 1) {
    msalInstance.setActiveAccount(accounts[0]);
    return accounts[0];
  }
  // Varias cuentas sin selección explícita: volver a selección Microsoft.
  return null;
}

msalInstance?.addEventCallback(event => {
  if (event.eventType === EventType.LOGIN_SUCCESS && event.payload?.account) {
    bloqueada = false;
    msalInstance.setActiveAccount(event.payload.account);
  }
});

export const loginRequest = { scopes: ['openid', 'profile'], prompt: 'select_account' };
