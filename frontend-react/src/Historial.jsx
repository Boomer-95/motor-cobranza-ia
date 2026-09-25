import { useState } from 'react';
import { apiFetch } from './api';

export default function Historial({ referenciaSeccion }) {
  const [id, setId] = useState('1');
  const [registros, setRegistros] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  async function consultar(event) {
    event.preventDefault();
    setCargando(true); setError(''); setRegistros(null);
    try {
      const res = await apiFetch(`/ia/historial/${id}`);
      if (res.status === 404) setRegistros([]);
      else if (!res.ok) throw new Error('No se pudo consultar el historial.');
      else setRegistros(await res.json());
    } catch { setError('No se pudo consultar el historial. Verifica la conexión.'); }
    finally { setCargando(false); }
  }
  return <section ref={referenciaSeccion} tabIndex={-1} id="historial" className="panel-grid panel-cartera" aria-labelledby="titulo-historial">
    <h2 id="titulo-historial">Historial de estrategias</h2>
    <form className="input-group" onSubmit={consultar}>
      <label>ID del cliente <input aria-label="ID para historial" type="number" min="1" step="1" required value={id} onChange={e => setId(e.target.value)} /></label>
      <button disabled={cargando}>{cargando ? 'Consultando...' : 'Consultar historial'}</button>
    </form>
    {error && <p className="mensaje-error" role="alert">{error}</p>}
    {registros?.length === 0 && <p>No existe historial para este ID de cliente.</p>}
    {registros && registros.length > 0 && <div className="tabla-wrapper" tabIndex="0" role="region" aria-label="Historial de estrategias">
      <table className="tabla-historial">
        <thead><tr><th scope="col">Folio</th><th scope="col">Fecha</th><th scope="col" className="numero">Monto</th><th scope="col">Mensaje</th></tr></thead>
        <tbody>{registros.map(item => <tr key={item.id}>
          <td>CL-{String(item.cliente_id).padStart(6, '0')}</td>
          <td className="fecha">{new Date(item.fecha_creacion).toLocaleString('es-MX')}</td>
          <td className="numero">${item.monto_al_momento.toLocaleString('es-MX')} MXN</td>
          <td className="texto-mensaje">{item.mensaje_generado}</td>
        </tr>)}</tbody>
      </table>
    </div>}
  </section>;
}
