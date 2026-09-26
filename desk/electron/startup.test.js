const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { buildBackendEnv } = require('./backendHost');
const { isAllowedSecureKey } = require('./secureStorePolicy');

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

// Régression : le store sécurisé refusait les clés d'auth ('erp.auth.*' et
// legacy), aucun token n'était persisté -> pas de header Authorization ->
// 401 -> 'auth:logout' -> retour immédiat au login après une connexion
// pourtant réussie dans l'exe packagé.
test('le store sécurisé accepte toutes les clés d’authentification', () => {
  const authKeys = [
    'access_token',
    'refresh_token',
    'user',
    'tenant',
    'subscription',
    'erp.auth.access_token',
    'erp.auth.refresh_token',
    'erp.auth.user',
    'erp.auth.tenant',
    'erp.auth.subscription',
    'erp.desk.preferences.42:7.theme',
  ];

  for (const key of authKeys) {
    assert.equal(isAllowedSecureKey(key), true, `clé rejetée: ${key}`);
  }
});

test('le store sécurisé refuse les clés hors politique', () => {
  const rejected = ['password', 'erp.authx.user', 'erp.desk', 'session', '', null, undefined, 42];

  for (const key of rejected) {
    assert.equal(isAllowedSecureKey(key), false, `clé acceptée: ${String(key)}`);
  }
});

test('les clés écrites par les stores d’auth sont couvertes par la politique', () => {
  const KEY_PATTERN = /'((?:erp\.[a-z.]+)|(?:access_token|refresh_token|user|tenant|subscription))'/g;
  const stores = [
    ['shared', 'storage', 'authStorage.js'],
    ['shared', 'storage', 'tokenStore.js'],
    ['desk', 'shared', 'storage', 'authStorage.js'],
    ['desk', 'shared', 'storage', 'tokenStore.js'],
  ].map((parts) => path.join(__dirname, '..', '..', ...parts));

  let found = 0;
  for (const store of stores) {
    const content = fs.readFileSync(store, 'utf8');
    for (const match of content.matchAll(KEY_PATTERN)) {
      found += 1;
      assert.equal(
        isAllowedSecureKey(match[1]),
        true,
        `${path.relative(path.join(__dirname, '..', '..'), store)}: clé rejetée ${match[1]}`,
      );
    }
  }

  assert.ok(found >= 10, `clés d'auth détectées: ${found}`);
});

test('le Desk utilise le central en ligne et le local uniquement en repli', () => {
  const api = fs.readFileSync(
    path.join(__dirname, '..', '..', 'shared', 'services', 'api.js'),
    'utf8',
  );

  assert.match(api, /resolveDesktopRoute\(\{[\s\S]*?forceLocal/);
  assert.match(api, /markDesktopCentralUnavailable\(\)/);
  assert.match(api, /_desktopTarget === 'central'/);
  assert.match(api, /tokenStore\.getCentralAccessToken\(\)/);
  assert.match(api, /tokenStore\.getOfflineAccessToken\(\)/);
  assert.match(api, /api\.post\('\/auth\/login'.*_forceLocal/);
});

test('le backend local expose le cycle de synchronisation immédiat', () => {
  const host = fs.readFileSync(
    path.join(__dirname, 'backendHost.js'),
    'utf8',
  );
  const syncApi = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'local_sync.py'),
    'utf8',
  );

  assert.match(host, /getCentralApiBaseUrl/);
  assert.match(host, /syncNow/);
  assert.match(syncApi, /\/local-run/);
});

test('les contrats IA critiques existent côté backend', () => {
  const ai = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'ai.py'),
    'utf8',
  );
  assert.match(ai, /@ns\.route\('\/analytics\/stock'\)/);
  assert.match(ai, /@ns\.route\('\/analytics\/sales'\)/);
});

test('le service tenant Super Admin utilise une route de suppression existante', () => {
  const api = fs.readFileSync(
    path.join(__dirname, '..', '..', 'shared', 'services', 'api.js'),
    'utf8',
  );
  assert.match(api, /delete: \(id\) =>\s*api\.delete\(\`\/super-admin\/tenants\/\$\{id\}\`\)/);
  assert.doesNotMatch(api, /\/super-admin\/tenants\/\$\{id\}\/delete/);
});

test('la matrice RBAC definit toutes les permissions utilisees par les roles', () => {
  const matrix = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'security', 'permission_matrix.py'),
    'utf8',
  );
  const definitionSection = matrix.split('WILDCARD_PERMISSION')[0];
  const roleSection = matrix.slice(
    matrix.indexOf('DEFAULT_PERMISSION_LISTS = {'),
    matrix.indexOf('# Alias historique conserve'),
  );
  const definitions = new Set(
    [...definitionSection.matchAll(/^\s*"([^"]+)":\s*\{/gm)].map((m) => m[1]),
  );
  const referenced = new Set(
    [...roleSection.matchAll(/"([a-z_]+\.[a-z_]+)"/g)].map((m) => m[1]),
  );
  for (const permission of referenced) {
    assert.equal(
      definitions.has(permission),
      true,
      `Permission non définie dans PERMISSION_DEFINITIONS: ${permission}`,
    );
  }
});

test('les filtres de dates comptables renvoient un 400 au lieu dun 500', () => {
  const compta = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'comptabilite.py'),
    'utf8',
  );
  assert.equal(
    (compta.match(/except \(ValueError, TypeError\):\s*\n\s*return \{'message': 'Format de date invalide/g) || []).length,
    3,
  );
});

test('les dépendances du module public sont importées avant usage', () => {
  const pub = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'public.py'),
    'utf8',
  );
  assert.match(pub, /from email\.utils import parseaddr/);
  assert.match(pub, /from os import getenv/);
  assert.match(pub, /import html as html_lib/);
  assert.match(pub, /from app\.config\.settings import Config/);
  assert.match(pub, /from app\.services\.email_service import send_email/);
});

test('ProduitService bloque les mises a jour directes du stock', () => {
  const service = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'services', 'produit_service.py'),
    'utf8',
  );
  assert.match(service, /'quantite_stock'/);
  assert.match(service, /instance\._calculer_prix_ttc\(\)/);
  assert.match(service, /instance\._calculer_volume\(\)/);
});

test('le webhook Papi convertit EN_ATTENTE/PENDING en PROCESSING', () => {
  const webhook = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'services', 'papi', 'webhook.py'),
    'utf8',
  );
  assert.match(webhook, /StatutPaiement\.EN_ATTENTE, StatutPaiement\.PENDING/);
  assert.match(webhook, /paiement\.statut = StatutPaiement\.PROCESSING/);
});

test('la création tenant Super Admin envoie les champs requis par le backend', () => {
  const page = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'frontend', 'src', 'pages', 'SuperAdmin.jsx'),
    'utf8',
  );
  assert.match(page, /slug: formData\.slug/);
  assert.match(page, /email_contact: formData\.email/);
  assert.match(page, /admin_email: formData\.admin_email \|\| formData\.email/);
  assert.match(page, /admin_password: formData\.admin_password/);
  assert.match(page, /plan: formData\.plan/);
});

test('les imports runtime critiques auth et vitrine sont présents', () => {
  const tenant = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'security', 'tenant.py'),
    'utf8',
  );
  const pub = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'public.py'),
    'utf8',
  );
  assert.match(tenant, /from datetime import datetime/);
  assert.match(pub, /^import re$/m);
});

test('les imports critiques stock et entrepôts sont présents', () => {
  const stocks = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'stocks.py'),
    'utf8',
  );
  const entrepots = fs.readFileSync(
    path.join(__dirname, '..', '..', 'web', 'backend', 'app', 'api', 'v1', 'entrepots.py'),
    'utf8',
  );
  assert.match(stocks, /from flask import request, current_app/);
  assert.match(entrepots, /from flask import request/);
});
