import { useState } from 'react';
import { API_BASE, guardarToken } from './api';

function Login({ onLoginExitoso }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setCargando(true);

    try {
      // El endpoint /auth/login espera form-data (estándar OAuth2), no JSON.
      const body = new URLSearchParams();
      body.append('username', username);
      body.append('password', password);

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });

      if (response.ok) {
        const data = await response.json();
        guardarToken(data.access_token);
        onLoginExitoso(data.nombre || username);
      } else if (response.status === 401) {
        setError('Usuario o contraseña incorrectos.');
      } else {
        setError(`Error del servidor: ${response.status}`);
      }
    } catch (err) {
      console.error('Error de login:', err);
      setError('Error de conexión. ¿La API está corriendo?');
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="login-card" onSubmit={handleSubmit}>
        <p className="eyebrow">Motor Inteligente de Cobranza</p>
        <h2>Acceso administrador</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '20px' }}>
          Esta información es confidencial. Solo personal autorizado puede continuar.
        </p>

        <input
          type="text"
          placeholder="Usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div className="mensaje-error">{error}</div>}

        <button type="submit" disabled={cargando} style={{ width: '100%', marginTop: '10px' }}>
          {cargando ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>
    </div>
  );
}

export default Login;
