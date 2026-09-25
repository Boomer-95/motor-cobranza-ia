import { useState, useEffect, useCallback } from 'react';
import './App.css';
import Login from './Login';
import { apiFetch, getToken, borrarToken, setManejadorSesionExpirada } from './api';

const SEGMENTO_INFO = {
  'Alto riesgo': { color: 'var(--danger)', label: 'Alto riesgo' },
  'Riesgo medio': { color: 'var(--warning)', label: 'Riesgo medio' },
  'Bajo riesgo': { color: 'var(--success)', label: 'Bajo riesgo' },
  'No definido': { color: 'var(--text-muted)', label: 'Sin calcular' },
};

function BadgeSegmento({ segmento }) {
  const info = SEGMENTO_INFO[segmento] || SEGMENTO_INFO['No definido'];
  return (
    <span className="badge-segmento" style={{ backgroundColor: info.color }}>
      {info.label}
    </span>
  );
}

function App() {
  const [autenticado, setAutenticado] = useState(!!getToken());
  const [nombreAdmin, setNombreAdmin] = useState('');

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

  // Si el backend responde 401 en cualquier momento (token vencido),
  // regresamos a la pantalla de login automáticamente.
  useEffect(() => {
    setManejadorSesionExpirada(() => {
      setAutenticado(false);
      setResultado(null);
      setCartera([]);
    });
  }, []);

  const cargarMetricas = useCallback(async () => {
    try {
      const response = await apiFetch('/api/metricas');
      if (response.ok) {
        const data = await response.json();
        setMetricas({
          deudoresActivos: data.deudores_activos,
          carteraVencida: `$${data.cartera_vencida.toLocaleString('es-MX')}`,
          estrategiasIA: data.estrategias_ia,
          recuperacion: `${data.porcentaje_recuperacion}%`,
        });
      }
    } catch (error) {
      console.error('Error al cargar métricas', error);
    }
  }, []);

  const cargarCartera = useCallback(async () => {
    setCargandoCartera(true);
    setErrorCartera('');
    try {
      const response = await apiFetch('/api/cartera-priorizada');
      if (response.ok) {
        const data = await response.json();
        setCartera(data);
      } else if (response.status !== 401) {
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
    if (autenticado) {
      cargarMetricas();
      cargarCartera();
    }
  }, [autenticado, cargarMetricas, cargarCartera]);

  const generarMensaje = async () => {
    if (!clienteId) return;

    setCargando(true);
    setErrorStatus('');
    setResultado(null);

    try {
      const resMensaje = await apiFetch(`/ia/analizar-riesgo/${clienteId}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });

      if (resMensaje.status === 404) {
        setErrorStatus('Cliente no encontrado.');
        return;
      }
      if (!resMensaje.ok) {
        if (resMensaje.status !== 401) {
          setErrorStatus(`Error del servidor: ${resMensaje.status}`);
        }
        return;
      }
      const dataMensaje = await resMensaje.json();

      let scoreRiesgo = null;
      let segmento = 'No definido';
      let probabilidadPago = null;

      const resRiesgo = await apiFetch(`/ia/calcular-riesgo/${clienteId}`, {
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
        monto: `$${dataMensaje.monto_pendiente.toLocaleString('es-MX')} MXN`,
        mensaje: dataMensaje.mensaje_empatico,
        scoreRiesgo,
        segmento,
        probabilidadPago,
      });

      cargarMetricas();
      cargarCartera();
    } catch (error) {
      console.error('Error:', error);
      setErrorStatus('Error de conexión. ¿FastAPI está corriendo?');
    } finally {
      setCargando(false);
    }
  };

  const handleLogout = () => {
    borrarToken();
    setAutenticado(false);
    setResultado(null);
    setCartera([]);
  };

  if (!autenticado) {
    return (
      <Login
        onLoginExitoso={(nombre) => {
          setNombreAdmin(nombre);
          setAutenticado(true);
        }}
      />
    );
  }

  return (
    <div className="dashboard">
      <div className="barra-superior">
        <h1 style={{ margin: 0, border: 'none', padding: 0 }}>Motor Inteligente de Cobranza</h1>
        <div className="sesion-admin">
          <span>👤 {nombreAdmin || 'Administrador'}</span>
          <button className="btn-secundario" onClick={handleLogout}>Cerrar sesión</button>
        </div>
      </div>

      <div className="header-dashboard">
        <p className="eyebrow">Vista General</p>
        <h2>Tu cartera, en perspectiva.</h2>
        <p style={{ color: 'var(--text-muted)' }}>
          Consulta el estado de la deuda y organiza tu siguiente estrategia de contacto.
        </p>

        <div className="grid-metricas">
          <div className="tarjeta-metrica">
            <h4>Deudores Activos</h4>
            <div className="valor">{metricas.deudoresActivos}</div>
          </div>
          <div className="tarjeta-metrica">
            <h4>Cartera Vencida</h4>
            <div className="valor">{metricas.carteraVencida}</div>
          </div>
          <div className="tarjeta-metrica">
            <h4>Estrategias IA</h4>
            <div className="valor">{metricas.estrategiasIA}</div>
          </div>
          <div className="tarjeta-metrica">
            <h4>Recuperación</h4>
            <div className="valor" style={{ color: 'var(--primary)' }}>
              {metricas.recuperacion}
            </div>
          </div>
        </div>
      </div>

      <h3 style={{ marginBottom: '20px' }}>Operación de Cobranza</h3>

      <div className="grid-operacion">
        <div className="panel-grid">
          <h3 style={{ marginTop: 0 }}>Generar Estrategia de Contacto</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Ingresa el ID del deudor para analizar su perfil con IA y calcular su riesgo.
          </p>

          <div className="input-group">
            <input
              type="number"
              value={clienteId}
              onChange={(e) => setClienteId(e.target.value)}
              min="1"
            />
            <button onClick={generarMensaje} disabled={cargando}>
              {cargando ? 'Procesando...' : 'Procesar con IA'}
            </button>
          </div>
          {errorStatus && <div className="mensaje-error">{errorStatus}</div>}
        </div>

        {resultado && (
          <div className="panel-grid">
            <div className="encabezado-resultado">
              <h3 style={{ margin: 0, color: 'var(--primary)' }}>Estrategia Guardada en DB</h3>
              <BadgeSegmento segmento={resultado.segmento} />
            </div>

            <div className="datos-cliente">
              <div className="metrica">
                <small>Cliente</small>
                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{resultado.nombre}</div>
              </div>
              <div className="metrica monto">
                <small>Monto</small>
                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{resultado.monto}</div>
              </div>
              {resultado.scoreRiesgo !== null && (
                <div className="metrica riesgo">
                  <small>Prob. de pago a tiempo</small>
                  <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                    {Math.round(resultado.probabilidadPago * 100)}%
                  </div>
                </div>
              )}
            </div>

            <textarea readOnly style={{ height: '110px' }} value={resultado.mensaje}></textarea>
          </div>
        )}
      </div>

      <div className="panel-grid panel-cartera">
        <div className="encabezado-cartera">
          <div>
            <h3 style={{ marginTop: 0 }}>Cartera Priorizada</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0 }}>
              Ordenada por riesgo financiero (score de riesgo × monto pendiente).
            </p>
          </div>
          <button className="btn-secundario" onClick={cargarCartera} disabled={cargandoCartera}>
            {cargandoCartera ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>

        {errorCartera && <div className="mensaje-error">{errorCartera}</div>}

        {!errorCartera && cartera.length === 0 && !cargandoCartera && (
          <p style={{ color: 'var(--text-muted)' }}>
            No hay deuda pendiente registrada, o el modelo aún no ha calculado ningún score.
          </p>
        )}

        {cartera.length > 0 && (
          <div className="tabla-wrapper">
            <table className="tabla-cartera">
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
                    <td>{c.cliente_nombre}</td>
                    <td>${c.monto_pendiente.toLocaleString('es-MX')}</td>
                    <td>
                      <BadgeSegmento segmento={c.segmento} />
                    </td>
                    <td>{c.prioridad.toLocaleString('es-MX')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
