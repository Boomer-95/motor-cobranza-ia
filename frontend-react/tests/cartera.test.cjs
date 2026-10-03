const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { transformSync } = require('esbuild');

for (const errorConexion of [false, true]) {
  test(`una consulta de cartera antigua fallida no sobrescribe la última: conexión=${errorConexion}`, async () => {
    const slots = [];
    let cursor = 0;
    let callbacks = [];
    let completarAntigua;
    let rechazarAntigua;
    let solicitudes = 0;
    const antigua = new Promise((resolve, reject) => {
      completarAntigua = resolve; rechazarAntigua = reject;
    });
    const react = {
      createElement: (type, props, ...children) => ({ type, props, children }),
      useState(initial) {
        const index = cursor++;
        if (!(index in slots)) slots[index] = initial;
        return [slots[index], value => { slots[index] = value; }];
      },
      useRef(initial) {
        const index = cursor++;
        if (!(index in slots)) slots[index] = { current: initial };
        return slots[index];
      },
      useEffect() {},
      useCallback(fn) { callbacks.push(fn); return fn; },
    };
    const filename = path.join(__dirname, '../src/App.jsx');
    const code = transformSync(fs.readFileSync(filename, 'utf8') + '\nexport { Dashboard };', {
      loader: 'jsx', format: 'cjs', jsxFactory: 'React.createElement',
    }).code;
    const module = { exports: {} };
    vm.runInNewContext(code, { module, exports: module.exports, React: react, URLSearchParams,
      console: { error() {} }, require(name) {
        if (name === 'react') return react;
        if (name === './api') return { apiFetch: async () => ++solicitudes === 1
          ? antigua : { ok: true, json: async () => [] } };
        if (name === './useNavegacionSecciones') return { __esModule: true, SECCIONES: [], default: () => ({
          seccionesRef: { current: {} }, inicioRef: {}, navegar() {},
        }) };
        return { default: () => null };
      },
    }, { filename });
    function render() {
      cursor = 0; callbacks = [];
      return module.exports.Dashboard({ nombreAdmin: 'Fixture', handleLogout() {} });
    }
    render();
    const cargar = callbacks[1];
    const anterior = cargar();
    await cargar();
    if (errorConexion) rechazarAntigua(new Error('Fallo antiguo'));
    else completarAntigua({ ok: false, status: 500 });
    await anterior;
    const tree = render();
    assert.ok(!JSON.stringify(tree).includes('No se pudo cargar la cartera priorizada.'));
    assert.ok(!JSON.stringify(tree).includes('Error de conexión al cargar la cartera.'));
    assert.equal(solicitudes, 2);
  });
}
