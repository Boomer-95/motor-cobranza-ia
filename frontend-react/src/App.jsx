import { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

const SEGMENTO_INFO = {
  'Alto riesgo': { className: 'badge badge-alto', label: 'Alto riesgo' },
  'Riesgo medio': { className: 'badge badge-medio', label: 'Riesgo medio' },
  'Bajo riesgo': { className: 'badge badge-bajo', label: 'Bajo riesgo' },
  'No definido': { className: 'badge badge-neutro', label: 'Sin calcular' },
};

function BadgeSegmento({ segmento }) {
  const info = SEGMENTO_INFO[segmento] || SEGMENTO_INFO['No definido'];
  return <span className={info.className}>{info.label}</span>;
}

function MetricCard({ title, value, subtitle, accent = 'purple' }) {
  return (
    <article className={`metric-card accent-${accent}`}>
      <div className="metric-card-top">
        <span className="metric-label">{title}</span>
        <span className="metric-dot" />
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-subtitle">{subtitle}</span>
    </article>
  );
}

function App() {
  const [metricas, setMetricas] = useState({
    deudoresActivos: '-',
    carteraVencida: '$-',
    estrategiasIA: '-',
    recuperacion: '-%',
  });

  const [clienteId, setClienteId] = useState(1);
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [errorStatus, setErrorStatus] = useState('');

  const [cartera, setCartera] = useState([]);
  const [cargandoCartera, setCargandoCartera] = useState(false);
  const [errorCartera, setErrorCartera] = useState('');

  const cargarMetricas = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/metricas`);
      if (!response.ok) return;

      const data = await response.json();
      setMetricas({
        deudoresActivos: data.deudores_activos,
        carteraVencida: `$${Number(data.cartera_vencida).toLocaleString('es-MX')}`,
        estrategiasIA: data.estrategias_ia,
        recuperacion: `${data.porcentaje_recuperacion}%`,
      });
    } catch (error) {
      console.error('Error al cargar métricas', error);
    }
  }, []);

  const cargarCartera = useCallback(async () => {
    setCargandoCartera(true);
    setErrorCartera('');

    try {
      const response = await fetch(`${API_BASE}/api/cartera-priorizada`);
      if (response.ok) {
        const data = await response.json();
        setCartera(data);
      } else {
        setErrorCartera('No se pudo cargar la cartera priorizada.');
      }
    } catch (error) {
      console.error('Error al cargar cartera priorizada', error);
      setErrorCartera('Error de conexión al cargar la cartera.');
    } finally {
      setCargandoCartera(false);
    }
  }, []);

  useEffect(() => {
    cargarMetricas();
    cargarCartera();
  }, [cargarMetricas, cargarCartera]);

  const generarMensaje = async () => {
    if (!clienteId) return;

    setCargando(true);
    setErrorStatus('');
    setResultado(null);

    try {
      const resMensaje = await fetch(`${API_BASE}/ia/analizar-riesgo/${clienteId}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });

      if (resMensaje.status === 404) {
        setErrorStatus('Cliente no encontrado.');
        return;
      }

      if (!resMensaje.ok) {
        setErrorStatus(`Error del servidor: ${resMensaje.status}`);
        return;
      }

      const dataMensaje = await resMensaje.json();

      let scoreRiesgo = null;
      let segmento = 'No definido';
      let probabilidadPago = null;

      const resRiesgo = await fetch(`${API_BASE}/ia/calcular-riesgo/${clienteId}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });

      if (resRiesgo.ok) {
        const dataRiesgo = await resRiesgo.json();
        scoreRiesgo = dataRiesgo.score_riesgo;
        segmento = dataRiesgo.segmento;
        probabilidadPago = dataRiesgo.probabilidad_pago_a_tiempo;
      }

      setResultado({
        nombre: dataMensaje.cliente_nombre,
        monto: `$${Number(dataMensaje.monto_pendiente).toLocaleString('es-MX')} MXN`,
        mensaje: dataMensaje.mensaje_empatico,
        scoreRiesgo,
        segmento,
        probabilidadPago,
      });

      cargarMetricas();
      cargarCartera();
    } catch (error) {
      console.error('Error:', error);
      setErrorStatus('Error de conexión. Verifica que FastAPI esté corriendo.');
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">MC</div>
          <div>
            <strong>Motor Cobranza</strong>
            <span>PluriOne</span>
          </div>
        </div>

        <nav className="nav-menu">
          <button className="nav-item active">Resumen</button>
          <button className="nav-item">Cartera</button>
          <button className="nav-item">Estrategias IA</button>
          <button className="nav-item">Historial</button>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          API local conectada
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Motor Inteligente de Cobranza</p>
            <h1>Panel de gestión</h1>
            <p className="page-description">
              Analiza riesgo, prioriza cartera y genera estrategias de contacto con IA.
            </p>
          </div>

          <button
            className="btn btn-secondary"
            onClick={() => {
              cargarMetricas();
              cargarCartera();
            }}
          >
            Actualizar datos
          </button>
        </header>

        <section className="metrics-grid">
          <MetricCard title="Deudores activos" value={metricas.deudoresActivos} subtitle="Clientes registrados" accent="purple" />
          <MetricCard title="Cartera vencida" value={metricas.carteraVencida} subtitle="Saldo pendiente" accent="red" />
          <MetricCard title="Estrategias IA" value={metricas.estrategiasIA} subtitle="Mensajes generados" accent="blue" />
          <MetricCard title="Recuperación" value={metricas.recuperacion} subtitle="Sobre monto original" accent="green" />
        </section>

        <section className="workspace-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Operación</p>
                <h2>Generar estrategia de contacto</h2>
              </div>
            </div>

            <p className="muted">
              Ingresa el ID del cliente para generar un mensaje empático y calcular su nivel de riesgo.
            </p>

            <div className="action-row">
              <div className="field">
                <label htmlFor="cliente-id">ID del cliente</label>
                <input
                  id="cliente-id"
                  type="number"
                  value={clienteId}
                  onChange={(e) => setClienteId(e.target.value)}
                  min="1"
                />
              </div>

              <button className="btn btn-primary" onClick={generarMensaje} disabled={cargando}>
                {cargando ? 'Procesando...' : 'Procesar con IA'}
              </button>
            </div>

            {errorStatus && <div className="alert alert-error">{errorStatus}</div>}
          </article>

          <article className="panel result-panel">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Resultado</p>
                <h2>Estrategia generada</h2>
              </div>
              {resultado && <BadgeSegmento segmento={resultado.segmento} />}
            </div>

            {!resultado ? (
              <div className="empty-state">
                <div className="empty-icon">IA</div>
                <p>Procesa un cliente para visualizar aquí su estrategia y evaluación de riesgo.</p>
              </div>
            ) : (
              <>
                <div className="result-stats">
                  <div className="result-stat">
                    <span>Cliente</span>
                    <strong>{resultado.nombre}</strong>
                  </div>
                  <div className="result-stat">
                    <span>Monto pendiente</span>
                    <strong>{resultado.monto}</strong>
                  </div>
                  <div className="result-stat">
                    <span>Prob. pago a tiempo</span>
                    <strong>
                      {resultado.probabilidadPago !== null
                        ? `${Math.round(resultado.probabilidadPago * 100)}%`
                        : 'No disponible'}
                    </strong>
                  </div>
                </div>

                <div className="message-box">
                  <span className="message-label">Mensaje recomendado</span>
                  <p>{resultado.mensaje}</p>
                </div>
              </>
            )}
          </article>
        </section>

        <section className="panel portfolio-panel">
          <div className="panel-heading portfolio-heading">
            <div>
              <p className="section-kicker">Priorización</p>
              <h2>Cartera priorizada</h2>
              <p className="muted">
                Ordenada por riesgo financiero multiplicado por monto pendiente.
              </p>
            </div>

            <button className="btn btn-secondary" onClick={cargarCartera} disabled={cargandoCartera}>
              {cargandoCartera ? 'Actualizando...' : 'Actualizar'}
            </button>
          </div>

          {errorCartera && <div className="alert alert-error">{errorCartera}</div>}

          {!errorCartera && cartera.length === 0 && !cargandoCartera ? (
            <div className="empty-state compact">
              <p>No hay deuda pendiente registrada o el modelo aún no ha calculado scores.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Monto pendiente</th>
                    <th>Segmento</th>
                    <th>Prioridad</th>
                  </tr>
                </thead>
                <tbody>
                  {cartera.map((c) => (
                    <tr key={c.cliente_id}>
                      <td>
                        <div className="client-cell">
                          <div className="avatar">{c.cliente_nombre?.charAt(0) || '?'}</div>
                          <span>{c.cliente_nombre}</span>
                        </div>
                      </td>
                      <td>${Number(c.monto_pendiente).toLocaleString('es-MX')}</td>
                      <td><BadgeSegmento segmento={c.segmento} /></td>
                      <td>
                        <strong>{Number(c.prioridad).toLocaleString('es-MX')}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;