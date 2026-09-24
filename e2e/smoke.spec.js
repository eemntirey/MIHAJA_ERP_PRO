const fs = require('fs');
const http = require('http');
const pathLib = require('path');
const { test, expect } = require('@playwright/test');

// Smoke E2E sur le vrai build React de production.
// Le backend est mocké : ce test valide le runtime React, le routing SPA,
// les chunks lazy et le rendu des pages sans dépendre de Render/Postgres.
//
// Localement, sans build, on conserve un serveur factice minimal.
// Pour tester une vraie app déjà démarrée :
// E2E_BASE_URL=http://localhost:3000 npx playwright test

const LIVE = process.env.E2E_BASE_URL;
const BUILD_DIR = pathLib.resolve(__dirname, '../web/frontend/build');

let server;
let baseUrl;

function startStaticSpaServer() {
  server = http.createServer((req, res) => {
    const requestPath = decodeURIComponent((req.url || '/').split('?')[0]);
    const relativePath = requestPath.replace(/^\/+/, '');
    let filePath = pathLib.join(BUILD_DIR, relativePath);

    if (!filePath.startsWith(BUILD_DIR)) {
      res.writeHead(400);
      res.end('Bad request');
      return;
    }

    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = pathLib.join(BUILD_DIR, 'index.html');
    }

    try {
      const body = fs.readFileSync(filePath);
      const ext = pathLib.extname(filePath);
      const contentTypes = {
        '.html': 'text/html; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.ico': 'image/x-icon',
      };
      res.writeHead(200, {
        'Content-Type': contentTypes[ext] || 'application/octet-stream',
        'Cache-Control': 'no-store',
      });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
  });

  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve(`http://127.0.0.1:${address.port}`);
    });
  });
}

test.beforeAll(async () => {
  if (LIVE) {
    baseUrl = LIVE;
    return;
  }

  if (fs.existsSync(pathLib.join(BUILD_DIR, 'index.html'))) {
    baseUrl = await startStaticSpaServer();
    return;
  }

  // Fallback historique si aucun build n'est disponible.
  server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(
      '<!DOCTYPE html><html lang="fr"><head><title>ERP Smoke</title></head>' +
      '<body><h1>MIHAJA ERP PRO</h1><p>smoke ok</p></body></html>'
    );
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.afterAll(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
});

async function mockApi(page) {
  await page.route('**/api/**', async (route) => {
    const url = route.request().url();
    const json = (body) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });

    if (url.includes('/dashboard/overview')) {
      return json({
        overview: {
          total_produits: 0,
          clients_actifs: 0,
          ventes_aujourdhui: 0,
          ca_aujourdhui: null,
          ca_mois: 0,
          benefice_mois: 0,
          alertes_stock: 0,
          alertes_stock_critiques: 0,
          evolution: [],
          previous_period_total: null,
          current_period_has_sales: false,
          top_products: [],
          recent_sales: [],
          receivables_count: 0,
          receivables_total: 0,
        },
      });
    }

    if (url.includes('/abonnements/mon-abonnement')) {
      return json({
        abonnement: {
          statut: 'ACTIF',
          plan: 'Pro',
          date_fin: '2030-01-01T00:00:00Z',
          montant: 15000,
        },
        subscription_active: true,
      });
    }

    if (url.includes('/public/produits')) return json({ produits: [] });
    if (url.includes('/ventes/summary')) return json({ count: 0 });
    if (url.includes('/stocks/alerts')) return json({ alertes_stock: [] });
    if (url.includes('/factures')) return json([]);
    if (url.includes('/notifications')) return json({ notifications: [] });
    if (url.includes('/dashboard')) return json({ stats: {} });

    return json({});
  });
}

test('le build React rend les routes principales sans erreur runtime', async ({ page }) => {
  if (!LIVE && !fs.existsSync(pathLib.join(BUILD_DIR, 'index.html'))) {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('h1')).toHaveText('MIHAJA ERP PRO');
    return;
  }

  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await mockApi(page);

  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).toContainText('ERP Pro');

  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#login-email')).toBeVisible();

  await page.addInitScript(() => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      role: 'admin',
      tenant_id: 'tenant-test',
      prenom: 'Test',
      nom: 'Admin',
      permissions: ['*'],
    }));
    localStorage.setItem('subscription', JSON.stringify({
      statut: 'ACTIF',
      plan: 'Pro',
      modules: [],
      date_fin: '2030-01-01T00:00:00Z',
      montant: 15000,
    }));
  });

  await page.goto(`${baseUrl}/dashboard`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Tableau de bord' })).toBeVisible({ timeout: 10000 });
  expect(pageErrors, pageErrors.join('\\n')).toEqual([]);
});
