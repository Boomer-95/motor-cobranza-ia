const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { transformSync } = require('esbuild');

function api({ token = async () => 'token-ficticio', account = () => ({ homeAccountId: 'cuenta-fixture' }),
  fetch = async () => ({ status: 200 }) } = {}) {
  const filename = path.join(__dirname, '../src/api.js');
  const code = transformSync(fs.readFileSync(filename, 'utf8'), {
    format: 'cjs', define: { 'import.meta.env.VITE_API_URL': '"https://api.example.invalid"' },
  }).code;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, Headers, fetch,
    require(name) {
      if (name === './auth/getAccessToken') return { getAccessToken: token };
      if (name === './auth/msalConfig') return { cuentaActiva: account };
      throw new Error(`Import inesperado: ${name}`);
    },
  }, { filename });
  return module.exports;
}

test('API adquiere token por solicitud y preserva opciones y cabeceras', async () => {
  let tokens = 0;
  const calls = [];
  const real = api({ token: async () => `fixture-${++tokens}`,
    fetch: async (url, options) => { calls.push({ url, options }); return { status: 200 }; } });
  await real.apiFetch('/api/metricas', { headers: { 'X-Fixture': 'conservada' } });
  await real.apiFetch('/api/clientes', { method: 'GET' });
  assert.equal(tokens, 2);
  assert.equal(calls[0].url, 'https://api.example.invalid/api/metricas');
  assert.equal(calls[0].options.headers.get('Authorization'), 'Bearer fixture-1');
  assert.equal(calls[0].options.headers.get('X-Fixture'), 'conservada');
  assert.equal(calls[1].options.headers.get('Authorization'), 'Bearer fixture-2');
});

for (const status of [401, 403, 200, 500]) {
  test(`API invalida sesión solo ante rechazo de autenticación: ${status}`, async () => {
    let invalidaciones = 0;
    const real = api({ fetch: async () => ({ status }) });
    real.setManejadorSesionExpirada(() => invalidaciones++);
    assert.equal((await real.apiFetch('/auth/me')).status, status);
    assert.equal(invalidaciones, [401, 403].includes(status) ? 1 : 0);
  });
}

for (const caso of ['token rechazado', 'cuenta cambiada', 'solicitud cancelada']) {
  test(`API evita transmitir con ${caso}`, async () => {
    let cuenta = 'cuenta-fixture';
    let llamadas = 0;
    const real = api({ account: () => ({ homeAccountId: cuenta }),
      token: async () => {
        if (caso === 'token rechazado') throw new Error('Reautenticar');
        if (caso === 'cuenta cambiada') cuenta = 'otra-fixture';
        return 'token-ficticio';
      }, fetch: async () => { llamadas++; return { status: 200 }; } });
    await assert.rejects(real.apiFetch('/api/clientes', {
      signal: { aborted: caso === 'solicitud cancelada' },
    }));
    assert.equal(llamadas, 0);
  });
}

test('rechazo tardío de otra cuenta no invalida la sesión actual', async () => {
  let cuenta = 'cuenta-fixture';
  let invalidaciones = 0;
  const real = api({ account: () => ({ homeAccountId: cuenta }),
    fetch: async () => { cuenta = 'otra-fixture'; return { status: 401 }; } });
  real.setManejadorSesionExpirada(() => invalidaciones++);
  await real.apiFetch('/api/clientes');
  assert.equal(invalidaciones, 0);
});
