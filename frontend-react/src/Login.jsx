import { useEffect, useRef, useState } from 'react';
import { apiFetch, getToken, guardarToken } from './api';

function Login({ onLoginExitoso }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const solicitud = useRef(null);
  useEffect(() => () => { solicitud.current?.abort(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (solicitud.current) return;
    const controller = new AbortController();
    solicitud.current = controller;
    const tokenInicial = getToken();
    setError('');
    setCargando(true);

    try {
      // El endpoint /auth/login espera form-data (estándar OAuth2), no JSON.
      const body = new URLSearchParams();
      body.append('username', username);
      body.append('password', password);

      const response = await apiFetch('/auth/login', {
        publico: true,
        signal: controller.signal,
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });

      if (response.ok) {
        const data = await response.json();
        if (controller.signal.aborted) return;
        if (getToken() !== tokenInicial) {
          onLoginExitoso();
          return;
        }
        if (typeof data.access_token !== 'string' || !data.access_token) {
          throw new Error('Respuesta de autenticación no válida');
        }
        guardarToken(data.access_token);
        onLoginExitoso();
      } else if (response.status === 401) {
        setError('Usuario o contraseña incorrectos.');
      } else {
        setError(`Error del servidor: ${response.status}`);
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error('Error de login:', err);
      setError('Error de conexión. ¿La API está corriendo?');
    } finally {
      solicitud.current = null;
      if (!controller.signal.aborted) setCargando(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Motor Inteligente de Cobranza</h1>
        <p className="login-marca">PluriOne</p>
        <h2>Acceso administrador</h2>
        <p className="confidencialidad">
          Esta información es confidencial. Solo personal autorizado puede continuar.
        </p>

        <label htmlFor="usuario">Usuario</label>
        <input
          id="usuario"
          type="text"
          placeholder="Usuario"
          aria-label="Usuario" required autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <label htmlFor="contrasena">Contraseña</label>
        <input
          id="contrasena"
          type="password"
          placeholder="Contraseña"
          aria-label="Contraseña" required autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div className="mensaje-error">{error}</div>}

        <button type="submit" disabled={cargando} className="btn-login">
          {cargando ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>
    </div>
  );
}

export default Login;
