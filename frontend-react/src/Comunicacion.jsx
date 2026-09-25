import { useState } from 'react';
import { apiFetch } from './api';

// El cliente procede de la estrategia guardada, no del campo editable del dashboard.
export default function Comunicacion({ resultado, alRegistrar, permitirEdicion = false }) {
  const [mensaje, setMensaje] = useState(resultado.mensaje || '');
  const [canal, setCanal] = useState('Email');
  const [cargando, setCargando] = useState(false);
  const [estado, setEstado] = useState('');
  async function registrar() {
    setCargando(true); setEstado('');
    try {
      const res = await apiFetch('/api/comunicaciones', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cliente_id: resultado.clienteId, canal, mensaje: permitirEdicion ? mensaje.trim() : resultado.mensaje }),
      });
      if (!res.ok) throw new Error();
      setEstado('Comunicación simulada registrada correctamente.');
      alRegistrar?.();
    } catch { setEstado('No se pudo registrar la comunicación.'); }
    finally { setCargando(false); }
  }
  return <div className="comunicacion-form">
    <h4>Registro de comunicación</h4>
    <p className="aviso-demo">Modo demostración: la comunicación se registra pero no se envía externamente.</p>
    {permitirEdicion && <label>Mensaje de la comunicación
      <textarea value={mensaje} maxLength={10000} onChange={e => setMensaje(e.target.value)} />
    </label>}
    <div className="input-group">
      <label>Canal de comunicación
      <select aria-label="Canal de comunicación" value={canal} onChange={e => setCanal(e.target.value)}>
        {['Email', 'SMS', 'WhatsApp', 'Llamada'].map(c => <option key={c}>{c}</option>)}
      </select>
      </label>
      <button onClick={registrar} disabled={cargando || (permitirEdicion && !mensaje.trim())}>{cargando ? 'Registrando...' : 'Registrar comunicación'}</button>
    </div>
    <p role="status">{estado}</p>
  </div>;
}
