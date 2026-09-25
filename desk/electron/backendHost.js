// desk/electron/backendHost.js
// Démarre et supervise le backend Flask local embarqué.
// Dev  : spawn `run.py` avec env local-embedded, après avoir résolu un
//        interpréteur Python disposant des dépendances (cf. incident
//        2026-09-22 : `python` du PATH pointait vers un venv sans Flask ->
//        "Impossible de démarrer le serveur local").
// Prod : spawn l'exécutable PyInstaller packagé (resources/backend/).
const { spawn, execFile } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const { app, BrowserWindow } = require('electron');

let backendProc = null;
let currentPort = null;
let ready = false;
let resolvedPython = null;

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

// Candidats interpréteurs, par priorité :
//  - MIHAJA_PYTHON : chemin explicite choisi par l'utilisateur ;
//  - `python` du PATH (souvent correct, mais peut être un venv incomplet) ;
//  - launcher Windows `py` avec les versions compatibles du projet.
function pythonCandidates() {
  const candidates = [];
  if (process.env.MIHAJA_PYTHON) {
    candidates.push([process.env.MIHAJA_PYTHON]);
  }
  candidates.push(['python'], ['py', '-3.11'], ['py', '-3.12'], ['py', '-3'], ['python3']);
  return candidates;
}

// Sonde : `import app` valide d'un coup l'interpréteur ET toutes les
// dépendances du backend (flask, flask_restx, sqlalchemy, ...).
function probePython(candidate, backendRoot) {
  return new Promise((resolve) => {
    const args = [...candidate.slice(1), '-c', 'import app'];
    execFile(candidate[0], args, {
      cwd: backendRoot,
      timeout: 30000,
      windowsHide: true,
    }, (err) => resolve(!err));
  });
}

async function resolvePython(backendRoot) {
  if (resolvedPython) return resolvedPython;
  const candidates = pythonCandidates();
  const results = await Promise.all(
    candidates.map((c) => probePython(c, backendRoot).then((ok) => ({ c, ok })))
  );
  const winner = results.find((r) => r.ok);
  if (winner) {
    resolvedPython = winner.c;
    console.log('[backend-local] Interpréteur Python retenu :',
      winner.c.join(' '));
  }
  return resolvedPython;
}

function buildBackendEnv({ cfg, dbDir, port, processEnv = process.env }) {
  return {
    ...processEnv,
    FLASK_ENV: 'local-embedded',
    LOCAL_DB_PATH: path.join(dbDir, 'erp-local.db'),
    LOCAL_API_PORT: String(port),
    // Le central est distinct du backend Flask local. Ne jamais utiliser 127.0.0.1 ici.
    REPLICATION_URL: cfg.replicationUrl || processEnv.REPLICATION_URL || 'https://mihaja-erp-pro.onrender.com',
    SECRET_KEY: cfg.secretKey || 'local-embedded-secret-a-remplacer',
    JWT_SECRET_KEY: cfg.jwtSecretKey || 'local-embedded-jwt-a-remplacer',
  };
}

async function startLocalBackend() {
  // Déjà démarré : ne pas lancer un second processus.
  if (backendProc) {
    return { port: currentPort, pid: backendProc.pid };
  }
  const port = await getFreePort();
  currentPort = port; // fix : conserver le port (signalé dans le plan)
  ready = false;
  const dbDir = path.join(app.getPath('userData'), 'local-db');
  fs.mkdirSync(dbDir, { recursive: true });
  const cfg = readUserConfig();
  const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;
  const backendRoot = isDev
    ? path.join(__dirname, '..', '..', 'web', 'backend')
    : path.join(process.resourcesPath, 'backend');

  const env = buildBackendEnv({ cfg, dbDir, port });
  if (!cfg.secretKey || !cfg.jwtSecretKey) {
    console.warn(
      '[backend-local] SECRET_KEY ou JWT_SECRET_KEY non configuré : '
      + 'valeur par défaut local-embedded-*-a-remplacer utilisée '
      + '(réservée à la démo locale, à remplacer avant toute mise en service).'
    );
  }

  if (isDev) {
    const pythonCmd = await resolvePython(backendRoot);
    if (!pythonCmd) {
      throw new Error(
        'Aucun interpréteur Python avec les dépendances du backend n’a été '
        + 'trouvé sur ce poste.\n\n'
        + 'Correction (depuis la racine du projet) :\n'
        + '  py -3.11 -m pip install -r web/requirements.txt\n\n'
        + 'Ou désignez explicitement l’interpréteur via la variable '
        + 'd’environnement MIHAJA_PYTHON.'
      );
    }
    // Sans `shell: true` : kill() termine bien le processus Python lui-même
    // (avec cmd.exe intermédiaire, le kill libérait cmd mais pas python).
    backendProc = spawn(
      pythonCmd[0], [...pythonCmd.slice(1), 'run.py'],
      { cwd: backendRoot, env, windowsHide: true }
    );
  } else {
    backendProc = spawn(path.join(backendRoot, 'mihaja-backend.exe'), [], { env });
  }
  emitStatus('starting');

  // Journal circulaire : les 40 dernières lignes servent au diagnostic
  // affiché dans le dialogue d'erreur.
  const logTail = [];
  const pushLog = (chunk, stream) => {
    for (const line of chunk.toString().split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      logTail.push(`[${stream}] ${trimmed}`);
      if (logTail.length > 40) logTail.shift();
      console.log(`[backend-local] ${trimmed}`);
    }
  };
  backendProc.stdout?.on('data', (chunk) => pushLog(chunk, 'out'));
  backendProc.stderr?.on('data', (chunk) => pushLog(chunk, 'err'));

  let exitInfo = null;
  backendProc.on('error', (err) => {
    exitInfo = `échec du lancement : ${err.message}`;
  });
  backendProc.on('exit', (code, signal) => {
    backendProc = null;
    exitInfo = signal
      ? `interrompu (${signal})`
      : `terminé avec le code ${code}`;
    // Ne pas écraser un 'error' déjà émis pendant le démarrage.
    emitStatus(ready ? 'stopped' : 'error');
  });

  const failureDetail = () => {
    const lines = exitInfo ? [`Le processus backend : ${exitInfo}.`] : [];
    if (logTail.length) {
      lines.push('Dernières sorties du backend :', ...logTail);
    }
    return lines.join('\n');
  };

  // Health-check : /health doit répondre avant de déclarer 'ready'
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (!backendProc) {
      emitStatus('error');
      throw new Error(
        'Le serveur local s’est arrêté avant de répondre.\n' + failureDetail()
      );
    }
    try {
      const r = await fetch(`http://127.0.0.1:${port}/health`);
      if (r.ok) {
        ready = true;
        emitStatus('ready');
        return { port, pid: backendProc ? backendProc.pid : null };
      }
    } catch {
      /* pas encore prêt */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  emitStatus('error');
  throw new Error(
    "Le serveur local n'a pas démarré dans les 20 secondes.\n" + failureDetail()
  );
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

module.exports = { buildBackendEnv, startLocalBackend, stopLocalBackend, getPort };
