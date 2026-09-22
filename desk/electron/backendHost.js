// desk/electron/backendHost.js
// Démarre et supervise le backend Flask local embarqué.
// Dev  : spawn `python run.py` avec env local-embedded.
// Prod : spawn l'exécutable PyInstaller packagé (resources/backend/).
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const { app, BrowserWindow } = require('electron');

let backendProc = null;
let currentPort = null;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, '127.0.0.1', () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
    srv.on('error', reject);
  });
}

function emitStatus(status) {
  BrowserWindow.getAllWindows().forEach((w) =>
    w.webContents.send('backend:status', status));
}

function readUserConfig() {
  const cfgPath = path.join(app.getPath('userData'), 'local-backend.json');
  try {
    return JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  } catch {
    return {};
  }
}

async function startLocalBackend() {
  const port = await getFreePort();
  currentPort = port; // fix : conserver le port (signalé dans le plan)
  const dbDir = path.join(app.getPath('userData'), 'local-db');
  fs.mkdirSync(dbDir, { recursive: true });
  const cfg = readUserConfig();
  const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;
  const backendRoot = isDev
    ? path.join(__dirname, '..', '..', 'web', 'backend')
    : path.join(process.resourcesPath, 'backend');

  const env = {
    ...process.env,
    FLASK_ENV: 'local-embedded',
    LOCAL_DB_PATH: path.join(dbDir, 'erp-local.db'),
    LOCAL_API_PORT: String(port),
    REPLICATION_URL: cfg.replicationUrl || process.env.REPLICATION_URL || 'https://erp.mihaja.mg',
    SECRET_KEY: cfg.secretKey || 'local-embedded-secret-a-remplacer',
    JWT_SECRET_KEY: cfg.jwtSecretKey || 'local-embedded-jwt-a-remplacer',
  };

  backendProc = isDev
    ? spawn('python', ['run.py'], { cwd: backendRoot, env, shell: true })
    : spawn(path.join(backendRoot, 'mihaja-backend.exe'), [], { env });

  emitStatus('starting');
  backendProc.on('exit', () => {
    backendProc = null;
    emitStatus('stopped');
  });

  // Health-check : /health doit répondre avant de déclarer 'ready'
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/health`);
      if (r.ok) {
        emitStatus('ready');
        return { port, pid: backendProc ? backendProc.pid : null };
      }
    } catch {
      /* pas encore prêt */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  emitStatus('error');
  throw new Error("Le serveur local n'a pas démarré dans les 20 secondes.");
}

function stopLocalBackend() {
  if (backendProc) {
    backendProc.kill();
    backendProc = null;
  }
}

function getPort() {
  return currentPort;
}

module.exports = { startLocalBackend, stopLocalBackend, getPort };
