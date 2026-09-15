// scripts/smoke-tunnel-3000.cjs
// Smoke test : vérifie que TOUS les accès passent par le tunnel unique
// https://bj470sl0-3000.inc1.devtunnels.ms/ (le tunnel :5000 est mort -> 404).
// Le frontend CRA (:3000) proxifie /api, /health, /docs, /monitor vers le backend :5000.
// Endpoint /monitor (audit P0) ajouté pour visibilité et monitoring.
//
// Usage : node scripts/smoke-tunnel-3000.cjs
// Sortie : code 0 si tout OK, 1 sinon.

const BASE = 'https://bj470sl0-3000.inc1.devtunnels.ms';

const checks = [
  { name: 'root frontend', method: 'GET', path: '/', expect: [200] },
  { name: 'health backend (via proxy)', method: 'GET', path: '/health', expect: [200] },
  { name: 'monitor backend (via proxy)', method: 'GET', path: '/monitor', expect: [200] },
  // POST login avec identifiants bidons -> 400 ou 401 selon le garde actif
  // = le backend répond (preuve que /api passe par le tunnel).
  { name: 'login joignable (400/401 attendu)', method: 'POST', path: '/api/v1/auth/login', body: { username: 'x', password: 'y' }, expect: [400, 401] },
  // Route protégée sans token -> 401 = middleware auth OK.
  { name: 'produits sans token (401 attendu)', method: 'GET', path: '/api/v1/produits', expect: [401] },
  { name: 'dashboard sans token (401 attendu)', method: 'GET', path: '/api/v1/dashboard', expect: [401] },
  { name: 'swagger docs', method: 'GET', path: '/docs/', expect: [200] },
  { name: 'preflight CORS', method: 'OPTIONS', path: '/api/v1/produits', expect: [200, 204] },
];

(async () => {
  let failed = 0;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function fetchRetry(url, options, retries = 3) {
    let lastErr;
    for (let attempt = 1; attempt <= retries; attempt += 1) {
      try {
        return await fetch(url, options);
      } catch (e) {
        lastErr = e;
        console.log(`... retry ${attempt}/${retries} ${options.method} ${url} -> ${e.message}`);
        await sleep(2000 * attempt);
      }
    }
    throw lastErr;
  }

  for (const c of checks) {
    const url = BASE + c.path;
    try {
      const res = await fetchRetry(url, {
        method: c.method,
        headers: {
          'Content-Type': 'application/json',
          Origin: BASE,
          ...(c.method === 'OPTIONS'
            ? { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'Content-Type, Authorization' }
            : {}),
        },
        ...(c.body ? { body: JSON.stringify(c.body) } : {}),
      }, 3);
      // Toujours consommer le body pour libérer le socket (évite l'assertion UV_HANDLE_CLOSING sous Windows).
      await res.arrayBuffer().catch(() => null);
      const ok = c.expect.includes(res.status);
      console.log(`${ok ? 'PASS' : 'FAIL'} [${res.status}] ${c.name} ${c.method} ${c.path} (attendu: ${c.expect.join('/')})`);
      if (!ok) failed += 1;
    } catch (e) {
      failed += 1;
      console.log(`FAIL [ERR] ${c.name} ${c.method} ${c.path} -> ${e.message}`);
    }
    await sleep(500);
  }
  console.log(failed === 0 ? '\nTOUT EST ACCESSIBLE via ' + BASE : `\n${failed} CHECK(S) EN ECHEC`);
  process.exit(failed === 0 ? 0 : 1);
})();
