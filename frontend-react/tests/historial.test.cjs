const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { transformSync } = require('esbuild');

test('historial conserva una fecha nula sin inventar el año 1970', async () => {
  const fechas = await import('../src/fechas.js');
  let cursor = 0;
  const valores = ['1', [{ id: 1, cliente_id: 1, fecha_creacion: null,
    monto_al_momento: 100, mensaje_generado: 'Histórico' }], '', false];
  const react = {
    useState() { const valor = valores[cursor++]; return [valor, () => {}]; },
    createElement: (type, props, ...children) => ({ type, props, children }),
  };
  const filename = path.join(__dirname, '../src/Historial.jsx');
  const code = transformSync(fs.readFileSync(filename, 'utf8'), {
    loader: 'jsx', format: 'cjs', jsxFactory: 'React.createElement',
  }).code;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, React: react,
    require(name) {
      if (name === 'react') return react;
      if (name === './api') return { apiFetch: () => { throw new Error('Red prohibida'); } };
      if (name === './fechas') return fechas;
      throw new Error(`Import inesperado: ${name}`);
    },
  }, { filename });
  const tree = module.exports.default({});
  function buscarFecha(node) {
    if (!node || typeof node !== 'object') return undefined;
    if (node.type === 'td' && node.props?.className === 'fecha') return node.children[0];
    return node.children?.flat(Infinity).map(buscarFecha).find(value => value !== undefined);
  }
  assert.equal(buscarFecha(tree), '—');
});

for (const fecha of [null, undefined, '', 'fecha inválida']) {
  test(`fecha ausente o inválida: ${String(fecha)}`, async () => {
    const { fechaHoraVisible } = await import('../src/fechas.js');
    assert.equal(fechaHoraVisible(fecha), '—');
  });
}

test('la fecha válida conserva el formato local existente', async () => {
  const { fechaHoraVisible } = await import('../src/fechas.js');
  const fecha = '2026-10-02T12:30:00';
  assert.equal(fechaHoraVisible(fecha), new Date(fecha).toLocaleString('es-MX'));
});
