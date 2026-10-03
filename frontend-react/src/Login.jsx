import { useRef, useState } from 'react';
import { loginRequest, msalInstance } from './auth/msalConfig';
import './App.css';

export default function Login({ configurado = true, errorSesion = '' }) {
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const pendiente = useRef(false);
  async function iniciar() {
    if (pendiente.current || !configurado) return;
    pendiente.current = true;
    setCargando(true); setError('');
    try { await msalInstance.loginRedirect(loginRequest); }
    catch {
      pendiente.current = false;
      setCargando(false);
      setError('No se pudo iniciar sesión con Microsoft. Intenta nuevamente.');
    }
  }
  return <div className="login-wrapper"><div className="login-card">
    <p className="login-marca">PluriOne</p>
    <h1>Motor Inteligente de Cobranza</h1>
    <h2>Acceso administrativo</h2>
    <p className="confidencialidad">Esta información es confidencial. Solo personal autorizado puede continuar.</p>
    {!configurado && <p role="alert">Microsoft Entra ID no está configurado.</p>}
    {(error || errorSesion) && <p role="alert" className="mensaje-error">{error || errorSesion}</p>}
    <button type="button" onClick={iniciar} disabled={!configurado || cargando} className="btn-login">
      <span className="microsoft-mark" aria-hidden="true"><i /><i /><i /><i /></span>
      {cargando ? 'Conectando con Microsoft...' : 'Iniciar sesión con Microsoft'}
    </button>
  </div></div>;
}
