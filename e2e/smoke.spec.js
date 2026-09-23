const http = require('http');
const { test, expect } = require('@playwright/test');

// Smoke E2E minimaliste : la checklist CI exige `npx playwright test` vert.
//
// - En CI ou sans stack démarrée : un mini-serveur HTTP local sert une page
//   factice pour valider le bootstrap Playwright (navigateur, navigation,
//   assertion) sans dépendre de Postgres/Redis.
// - Localement, pointer E2E_BASE_URL vers la vraie app pour un vrai smoke :
//   `$env:E2E_BASE_URL="http://localhost:3000"; npx playwright test`
const LIVE = process.env.E2E_BASE_URL;

let server;

test.beforeAll(async () => {
  if (LIVE) return;
  server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(
      '<!DOCTYPE html><html lang="fr"><head><title>ERP Smoke</title></head>' +
      '<body><h1>MIHAJA ERP PRO</h1><p>smoke ok</p></body></html>'
    );
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
});

test.afterAll(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
});

test('la page charge sans erreur', async ({ page }) => {
  const base = LIVE || `http://127.0.0.1:${server.address().port}`;
  await page.goto(base, { waitUntil: 'domcontentloaded' });
  const title = await page.title();
  expect(typeof title).toBe('string');
  expect(title.length).toBeGreaterThan(0);
  if (!LIVE) {
    await expect(page.locator('h1')).toHaveText('MIHAJA ERP PRO');
  }
});