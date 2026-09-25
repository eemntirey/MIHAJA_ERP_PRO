const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { buildBackendEnv } = require('./backendHost');

test('le release reconstruit et teste le backend embarqué', () => {
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'),
  );

  assert.match(packageJson.scripts.release, /build:backend/);
  assert.match(packageJson.scripts.release, /test:startup/);
});

test('le backend embarqué reçoit une URL de réplication centrale', () => {
  const env = buildBackendEnv({
    cfg: {},
    dbDir: path.join('C:', 'local-db'),
    port: 4321,
    processEnv: { REPLICATION_URL: '' },
  });

  assert.equal(env.FLASK_ENV, 'local-embedded');
  assert.equal(env.LOCAL_API_PORT, '4321');
  assert.equal(env.REPLICATION_URL, 'https://mihaja-erp-pro.onrender.com');
});

test('la balise CSP n’utilise pas frame-ancestors', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

  assert.doesNotMatch(html, /frame-ancestors/);
});

test('le build Electron utilise des chemins d’assets relatifs', () => {
  const config = fs.readFileSync(
    path.join(__dirname, '..', 'vite.config.js'),
    'utf8',
  );

  assert.match(config, /base:\s*['"]\.\/['"]/);
});

test('Checkout n’importe aucun service public inexistant', () => {
  const checkout = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'pages', 'Checkout.jsx'),
    'utf8',
  );

  assert.doesNotMatch(checkout, /setPublicTenantContext/);
});

test('PyInstaller embarque les modules chargés par les migrations', () => {
  const spec = fs.readFileSync(
    path.join(__dirname, 'backend', 'mihaja-backend.spec'),
    'utf8',
  );

  assert.match(spec, /['"]engineio\.async_drivers\.threading['"]/);
  assert.match(spec, /['"]logging\.config['"]/);
});
