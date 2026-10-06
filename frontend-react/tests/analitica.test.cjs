const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { transformSync } = require('esbuild');
const mxn = value => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(value ?? 0);

function cargar(valores = [], solicitar = async () => ({ ok: true, json: async () => [] })) {
  let cursor = 0;
  const cambios = [], efectos = [];
  const react = {
    useState: () => { const i = cursor++; return [valores[i], v => cambios.push([i, v])]; },
    useEffect: (fn, deps) => efectos.push({ fn, deps }),
    createElement: (type, props, ...children) => ({ type, props, children }),
  };
  const module = { exports: {} };
  const code = transformSync(fs.readFileSync('src/Analitica.jsx', 'utf8'), { loader: 'jsx', format: 'cjs', jsxFactory: 'React.createElement' }).code;
  vm.runInNewContext(code, { module, exports: module.exports, React: react, AbortController, require: name => name === 'recharts' ? Object.fromEntries(['ResponsiveContainer', 'LineChart', 'CartesianGrid', 'XAxis', 'YAxis', 'Tooltip', 'Line'].map(name => [name, name])) : name === 'react' ? react : name === './formatoAnalitica' ? { mxn } : { apiFetch: solicitar } });
  return { ...module.exports, cambios, efectos };
}
function nodos(tree) {
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...tree.children.flat(Infinity).flatMap(nodos)];
}
function texto(tree) {
  if (tree == null) return '';
  if (typeof tree !== 'object') return String(tree);
  return tree.children.flat(Infinity).map(texto).join(' ');
}
const resumen = { cartera_vencida: 1234, monto_recuperado_total: 200, porcentaje_recuperacion: 25,
  clientes_alto_riesgo: 2, clientes_con_estrategia_ia: 3, monto_recuperado_post_ia: 100,
  clientes_contactados_ia: 2, clientes_con_pago_post_ia: 1, tasa_pago_post_ia: 50,
  ventana_ia_dias: 7, ultima_actualizacion: '2026-10-05T12:00:00Z', deudores_activos: 2 };

test('KPIs, MXN y precisión observacional', () => {
  const { PanelAnalitica } = cargar();
  const tree = PanelAnalitica({ datos: { resumen, evolucion: [], canales: [] } });
  assert.equal(nodos(tree).filter(n => n.props?.className === 'tarjeta-metrica').length, 6);
  assert.match(texto(tree), /Recuperación asociada a IA/);
  assert.match(texto(tree), /No representa causalidad demostrada/);
  assert.match(texto(tree), /25%/);
  assert.equal(mxn(1234), new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(1234));
});
test('loading, error y ausencia de datos', () => {
  const { PanelAnalitica, Serie } = cargar();
  assert.equal(PanelAnalitica({ cargando: true }).props.role, 'status');
  assert.equal(PanelAnalitica({ error: true }).props.role, 'alert');
  assert.match(texto(PanelAnalitica({})), /Sin datos/);
  assert.match(texto(Serie({ titulo: 'Prueba', datos: [] })), /recopilación comienza/);
  assert.match(texto(PanelAnalitica({ datos: { resumen: { ...resumen, deudores_activos: 0, monto_recuperado_total: 0 }, evolucion: [], canales: [] } })), /Sin cartera activa/);
});
test('periodos, actualizar y llamadas con periodo seleccionado', async () => {
  const rutas = [];
  const modulo = cargar([90, 0, null, false, false], async ruta => {
    rutas.push(ruta); return { ok: true, json: async () => ruta.includes('resumen') ? resumen : [] };
  });
  const tree = modulo.default({});
  const select = nodos(tree).find(n => n.type === 'select');
  assert.deepEqual(nodos(select).filter(n => n.type === 'option').map(n => n.props.value), [30, 90, 180, 365]);
  select.props.onChange({ target: { value: '180' } });
  assert.deepEqual(modulo.cambios[0], [0, 180]);
  nodos(tree).find(n => n.type === 'button').props.onClick();
  assert.equal(modulo.cambios[1][1](0), 1);
  const cleanup = modulo.efectos[0].fn();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(rutas.length, 3);
  assert.ok(rutas.every(r => r.endsWith('?dias=90')));
  assert.ok(modulo.cambios.some(([i, v]) => i === 2 && v.resumen));
  cleanup();
});
test('error de API visible y fin de carga', async () => {
  const modulo = cargar([30, 0, null, true, false], async () => ({ ok: false }));
  modulo.default({}); modulo.efectos[0].fn();
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(modulo.cambios.some(([i, v]) => i === 4 && v === true));
  assert.ok(modulo.cambios.some(([i, v]) => i === 3 && v === false));
});
test('navegación y vínculo de estrategia en ficha', () => {
  const nav = fs.readFileSync('src/useNavegacionSecciones.js', 'utf8');
  assert.match(nav, /id: 'analitica', titulo: 'Analítica IA'/);
  assert.match(fs.readFileSync('src/App.jsx', 'utf8'), /seccionesRef.current.analitica = node/);
  assert.match(fs.readFileSync('src/FichaCliente.jsx', 'utf8'), /estrategiaId: detalle.sin_deuda_activa \? null : detalle.ultima_estrategia\?\.id/);
  assert.match(fs.readFileSync('src/Comunicacion.jsx', 'utf8'), /estrategia_id: resultado.estrategiaId \?\? null/);
});

test('series con cero, uno o dos puntos y fechas en orden temporal', () => {
  const { Serie } = cargar();
  assert.match(texto(Serie({ titulo: 'Prueba', datos: [] })), /Sin datos suficientes para graficar/);
  for (const cantidad of [1, 2]) {
    const datos = [{ fecha: '2026-10-06', saldo: '200' }, { fecha: '2026-10-01', saldo: 0 }].slice(0, cantidad);
    const tree = Serie({ titulo: 'Prueba', datos, campo: 'saldo' });
    const chart = nodos(tree).find(n => n.type === 'LineChart');
    assert.equal(chart.props.data.length, cantidad);
    assert.ok(chart.props.data.every(d => Number.isFinite(d.monto)));
    if (cantidad === 2) assert.ok(chart.props.data[0].instante < chart.props.data[1].instante);
    const line = nodos(tree).find(n => n.type === 'Line');
    assert.equal(line.props.type, 'linear');
    assert.ok(line.props.dot.r > 0);
    const tooltip = nodos(tree).find(n => n.type === 'Tooltip');
    assert.equal(tooltip.props.formatter(200)[0], mxn(200));
    assert.match(nodos(tree).find(n => n.type === 'YAxis').props.tickFormatter(200), /200/);
  }
  assert.match(texto(Serie({ titulo: 'Prueba', campo: 'saldo', datos: [{ fecha: '2026-10-06', saldo: null }] })), /Sin datos suficientes/);
});
