import { useState, useEffect, useCallback } from 'react';
import './App.css';
import useNavegacionSecciones, { SECCIONES } from './useNavegacionSecciones';
import Login from './Login';
import Historial from './Historial';
import Comunicacion from './Comunicacion';
import { apiFetch, getToken, borrarToken, setManejadorSesionExpirada } from './api';

const SEGMENTO_INFO = {
  'Alto riesgo': { clase: 'riesgo-alto', label: 'Alto riesgo' },
  'Riesgo medio': { clase: 'riesgo-medio', label: 'Riesgo medio' },
  'Bajo riesgo': { clase: 'riesgo-bajo', label: 'Bajo riesgo' },
  'No definido': { clase: 'riesgo-indefinido', label: 'Sin calcular' },
};

function BadgeSegmento({ segmento }) {
  const info = SEGMENTO_INFO[segmento] || SEGMENTO_INFO['No definido'];
  return (
    <span className={`badge-segmento ${info.clase}`}>
      {info.label}
    </span>
  );
}

function App() {
  const [autenticado, setAutenticado] = useState(!!getToken());
  const [nombreAdmin, setNombreAdmin] = useState('');
  const { seccionesRef, inicioRef, seccionActiva, navegar } = useNavegacionSecciones(autenticado);
  const [errorMetricas, setErrorMetricas] = useState('');

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
    setErrorMetricas('');
    try {
      const response = await apiFetch('/api/metricas');
      if (!response.ok) throw new Error('Métricas no disponibles');
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
      setErrorMetricas('No se pudieron cargar las métricas.');
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
      apiFetch('/auth/me').then(async (res) => {
        if (res.ok) {
          const admin = await res.json();
          setNombreAdmin(admin.nombre || admin.username);
        }
      }).catch(() => setErrorMetricas('No se pudo verificar la sesión.'));
      cargarMetricas();
      cargarCartera();
    }
  }, [autenticado, cargarMetricas, cargarCartera]);

  const generarMensaje = async () => {
    if (!Number.isInteger(Number(clienteId)) || Number(clienteId) < 1) {
      setErrorStatus('Ingresa un ID de cliente válido.');
      return;
    }

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
      } else {
        setErrorStatus('Estrategia guardada; no se pudo calcular el riesgo. Verifica que el modelo esté entrenado.');
      }

      setResultado({
        clienteId: dataMensaje.cliente_id,
        modo: dataMensaje.modo_generacion,
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
    <div ref={inicioRef} className="dashboard">
      <aside className="sidebar">
        <div className="marca">PluriOne<span>Gestión de cartera</span></div>
        <nav aria-label="Navegación principal">
          {SECCIONES.map(({ id, titulo }) => (
            <a key={id} className={`nav-item${seccionActiva === id ? ' active' : ''}`}
              href={`#${id}`} aria-current={seccionActiva === id ? 'location' : undefined}
              onClick={(event) => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                navegar(id, true, true);
              }}>
              {titulo}
            </a>
          ))}
        </nav>
        <div className="sesion-admin">
          <small>Usuario autenticado</small>
          <span>{nombreAdmin || 'Administrador'}</span>
          <button className="btn-secundario" onClick={handleLogout}>Cerrar sesión</button>
        </div>
      </aside>

      <main className="contenido-principal">
        <header className="barra-superior">
          <h1>Motor Inteligente de Cobranza</h1>
          <p>Administración y seguimiento de cartera · PluriOne</p>
        </header>

        <section ref={node => { seccionesRef.current.resumen = node; }} tabIndex={-1} id="resumen" className="header-dashboard" aria-labelledby="titulo-resumen">
          <h2 id="titulo-resumen">Resumen de cartera</h2>
          {errorMetricas && <p role="alert" className="mensaje-error">{errorMetricas}</p>}
          <div className="grid-metricas">
            <div className="tarjeta-metrica"><h3>Deudores activos</h3><div className="valor">{metricas.deudoresActivos}</div></div>
            <div className="tarjeta-metrica"><h3>Cartera vencida</h3><div className="valor">{metricas.carteraVencida}</div></div>
            <div className="tarjeta-metrica"><h3>Estrategias IA</h3><div className="valor">{metricas.estrategiasIA}</div></div>
            <div className="tarjeta-metrica"><h3>Recuperación</h3><div className="valor">{metricas.recuperacion}</div></div>
          </div>
        </section>

        <section ref={node => { seccionesRef.current.operacion = node; }} tabIndex={-1} id="operacion" aria-labelledby="titulo-operacion">
          <h2 id="titulo-operacion">Operación de Cobranza</h2>
          <div className="grid-operacion">
            <div className="panel-grid">
              <h3>Generar estrategia de contacto</h3>
              <p className="texto-secundario">Selecciona un cliente para generar su estrategia y calcular el riesgo.</p>
              <label htmlFor="cliente-operacion">ID del cliente</label>
              <div className="input-group">
                <input id="cliente-operacion" aria-label="ID del cliente" type="number" value={clienteId} onChange={(e) => setClienteId(e.target.value)} min="1" />
                <button onClick={generarMensaje} disabled={cargando}>{cargando ? 'Procesando...' : 'Procesar con IA'}</button>
              </div>
              {errorStatus && <div className="mensaje-error">{errorStatus}</div>}
            </div>

            {resultado ? (
              <div className="panel-grid">
                <div className="encabezado-resultado">
                  <h3>Estrategia guardada</h3>
                  <BadgeSegmento segmento={resultado.segmento} />
                </div>
                <dl className="datos-cliente">
                  <div><dt>Cliente</dt><dd>{resultado.nombre}</dd></div>
                  <div><dt>Monto pendiente</dt><dd>{resultado.monto}</dd></div>
                  {resultado.scoreRiesgo !== null && (
                    <div><dt>Probabilidad de pago a tiempo</dt><dd>{Math.round(resultado.probabilidadPago * 100)}%</dd></div>
                  )}
                  <div><dt>Score de riesgo</dt><dd>{resultado.scoreRiesgo ?? 'No disponible'}</dd></div>
                </dl>
                <p className="origen-mensaje">{resultado.modo === 'local' ? 'Plantilla local de demostración' : 'Generado con Groq'}</p>
                <label htmlFor="mensaje-generado">Mensaje generado</label>
                <textarea id="mensaje-generado" aria-label="Mensaje generado" readOnly value={resultado.mensaje} />
                <Comunicacion key={resultado.mensaje} resultado={resultado} />
              </div>
            ) : (
              <div className="panel-grid resultado-vacio">
                <h3>Resultado del análisis</h3>
                <p className="texto-secundario">El cliente, el score de riesgo y la estrategia aparecerán aquí al procesar un ID.</p>
              </div>
            )}
          </div>
        </section>

        <section ref={node => { seccionesRef.current.cartera = node; }} tabIndex={-1} id="cartera" className="panel-grid panel-cartera" aria-labelledby="titulo-cartera">
          <div className="encabezado-cartera">
            <div>
              <h2 id="titulo-cartera">Cartera priorizada</h2>
              <p className="texto-secundario">Ordenada por riesgo financiero (score de riesgo × monto pendiente).</p>
            </div>
            <button className="btn-secundario" onClick={cargarCartera} disabled={cargandoCartera}>{cargandoCartera ? 'Actualizando...' : 'Actualizar'}</button>
          </div>
          {errorCartera && <div className="mensaje-error">{errorCartera}</div>}
          {!errorCartera && cartera.length === 0 && !cargandoCartera && <p className="texto-secundario">No hay deuda pendiente registrada.</p>}
          {cartera.length > 0 && (
            <div className="tabla-wrapper" tabIndex="0" role="region" aria-label="Cartera priorizada">
              <table className="tabla-cartera">
                <thead><tr><th scope="col">Cliente</th><th scope="col" className="numero">Monto pendiente</th><th scope="col">Segmento</th><th scope="col" className="numero">Prioridad</th></tr></thead>
                <tbody>
                  {cartera.map((c) => (
                    <tr key={c.cliente_id}>
                      <td><button className="btn-id" aria-label={`Seleccionar cliente ${c.cliente_id}`} onClick={() => setClienteId(c.cliente_id)}>{c.cliente_id}</button> {c.cliente_nombre}</td>
                      <td className="numero">${c.monto_pendiente.toLocaleString('es-MX')}</td>
                      <td><BadgeSegmento segmento={c.segmento} /></td>
                      <td className="numero">{c.prioridad.toLocaleString('es-MX')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <Historial referenciaSeccion={node => { seccionesRef.current.historial = node; }} />
      </main>
    </div>
  );
}

export default App;
