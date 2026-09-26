// desk/electron/main.js
// Processus principal Electron pour l'application desktop ERP Pro.
const { app, BrowserWindow, Menu, ipcMain, Notification, dialog, safeStorage } = require('electron');
const backendHost = require('./backendHost');
const path = require('path');
const fs = require('fs');

const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;

const DEV_URL = 'http://localhost:3001';

// Icône de l'application (fenêtre, barre des tâches, notifications).
// Le PNG vit dans electron/ pour être inclus dans le package final.
const ICON_PATH = path.join(__dirname, 'icon.png');

let win = null;

// ==== Store sécurisé (audit P1-2) ====
// Le chiffrement vit DANS le processus principal (safeStorage n'existe pas
// dans un preload sandboxé). Le renderer n'accède jamais au disque ni à la
// clé : les opérations passent par IPC à canal strict. Si le chiffrement OS
// est indisponible, on échoue en "fail-closed" (renvoie null) au lieu de
// stocker les tokens en clair.
const { isAllowedSecureKey } = require('./secureStorePolicy');
const SECURE_STORE_MAX_VALUE_LEN = 64 * 1024;
let secureStoreCache = null;

function secureStorePath() {
  return path.join(app.getPath('userData'), 'secure-store.json');
}

function loadSecureStore() {
  if (secureStoreCache) return secureStoreCache;
  try {
    secureStoreCache = JSON.parse(fs.readFileSync(secureStorePath(), 'utf8'));
  } catch {
    secureStoreCache = {};
  }
  return secureStoreCache;
}

function persistSecureStore(cache) {
  try {
    fs.writeFileSync(secureStorePath(), JSON.stringify(cache));
  } catch {
    /* disque indisponible : on garde en mémoire */
  }
}

function _isAllowedSecureKey(key) {
  return isAllowedSecureKey(key);
}

function registerSecureStoreHandlers() {
  // Lecteurs synchrones (sendSync) pour rester compatible avec l'interface
  // synchrone de storageAdapter.
  ipcMain.on('secure-store:get', (event, key) => {
    if (!_isAllowedSecureKey(key) || !safeStorage.isEncryptionAvailable()) {
      event.returnValue = null;
      return;
    }
    const cache = loadSecureStore();
    const raw = cache[key];
    if (raw == null) {
      event.returnValue = null;
      return;
    }
    try {
      event.returnValue = safeStorage.decryptString(Buffer.from(raw, 'base64'));
    } catch {
      // Clé OS changée, donnée corrompue, ou valeur écrite en clair par une
      // ancienne version : on purge l'entrée et on force une reconnexion.
      delete cache[key];
      persistSecureStore(cache);
      event.returnValue = null;
    }
  });

  ipcMain.on('secure-store:set', (event, key, value) => {
    if (!_isAllowedSecureKey(key) || !safeStorage.isEncryptionAvailable()) {
      event.returnValue = false;
      return;
    }
    const str = value == null ? '' : String(value);
    if (str.length > SECURE_STORE_MAX_VALUE_LEN) {
      event.returnValue = false;
      return;
    }
    try {
      const cache = loadSecureStore();
      cache[key] = safeStorage.encryptString(str).toString('base64');
      persistSecureStore(cache);
      event.returnValue = true;
    } catch {
      // fail-closed : jamais de fallback en clair côté disque
      event.returnValue = false;
    }
  });

  ipcMain.on('secure-store:remove', (event, key) => {
    if (!_isAllowedSecureKey(key)) {
      event.returnValue = false;
      return;
    }
    const cache = loadSecureStore();
    if (Object.prototype.hasOwnProperty.call(cache, key)) {
      delete cache[key];
      persistSecureStore(cache);
    }
    event.returnValue = true;
  });
}

function buildMenu() {
  const template = [
    {
      label: 'Fichier',
      submenu: [
        { label: 'Imprimer', accelerator: 'CmdOrCtrl+P', click: () => win?.webContents.print({}, () => {}) },
        { type: 'separator' },
        { label: 'Quitter', accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Alt+F4', click: () => app.quit() },
      ],
    },
    {
      label: 'Édition',
      submenu: [
        { label: 'Annuler', accelerator: 'CmdOrCtrl+Z', role: 'undo' },
        { label: 'Rétablir', accelerator: 'Shift+CmdOrCtrl+Z', role: 'redo' },
        { type: 'separator' },
        { label: 'Couper', accelerator: 'CmdOrCtrl+X', role: 'cut' },
        { label: 'Copier', accelerator: 'CmdOrCtrl+C', role: 'copy' },
        { label: 'Coller', accelerator: 'CmdOrCtrl+V', role: 'paste' },
        { label: 'Tout sélectionner', accelerator: 'CmdOrCtrl+A', role: 'selectAll' },
      ],
    },
    {
      label: 'Affichage',
      submenu: [
        { label: 'Recharger', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: 'Forcer le rechargement', accelerator: 'Shift+CmdOrCtrl+R', role: 'forceReload' },
        { label: 'Outils de développement', accelerator: 'F12', role: 'toggleDevTools' },
        { type: 'separator' },
        { label: 'Plein écran', accelerator: 'F11', role: 'togglefullscreen' },
        { label: 'Zoom avant', accelerator: 'CmdOrCtrl+Plus', role: 'zoomIn' },
        { label: 'Zoom arrière', accelerator: 'CmdOrCtrl+-', role: 'zoomOut' },
        { label: 'Zoom normal', accelerator: 'CmdOrCtrl+0', role: 'resetZoom' },
      ],
    },
    {
      label: 'Aide',
      submenu: [
        {
          label: 'À propos de ERP Pro',
          click: () => {
            dialog.showMessageBox(win, {
              type: 'info',
              title: 'À propos',
              message: 'MIHAJA ERP Pro',
              detail: `Version ${app.getVersion()}\nElectron ${process.versions.electron}\nNode ${process.versions.node}`,
            });
          },
        },
      ],
    },
  ];

  // Sur macOS, ajouter le menu d'application standard
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    });
  }

  return Menu.buildFromTemplate(template);
}

function createWindow(port) {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1280,
    minHeight: 720,
    backgroundColor: '#111111',
    frame: false,
    titleBarStyle: 'hidden',
    icon: ICON_PATH,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js'),
      spellcheck: false,
    },
  });

  // === Contrôles de fenêtre (barre de titre custom) ===
  ipcMain.on('window:minimize', () => win.minimize());
  ipcMain.on('window:maximize', () => win.maximize());
  ipcMain.on('window:unmaximize', () => win.unmaximize());
  ipcMain.on('window:close', () => win.close());
  ipcMain.on('window:quit', () => app.quit());
  ipcMain.handle('window:is-maximized', () => win.isMaximized());

  // Déplacement de fenêtre depuis une zone drag custom (topbar).
  // startDragging() bloque jusqu'au mouseup et reproduit le comportement
  // natif d'un drag de barre de titre (compatible Windows/Linux/macOS).
  ipcMain.on('window:start-move', () => {
    if (!win || win.isMaximized()) return;
    try {
      win.startDragging();
    } catch {
      /* startDragging indisponible (rare) */
    }
  });

  // Synchronise l'état maximisé/restauré vers la barre personnalisée.
  win.on('maximize', () => win.webContents.send('window:maximize-changed', true));
  win.on('unmaximize', () => win.webContents.send('window:maximize-changed', false));

  // === Impression ===
  ipcMain.handle('print', (_event, options = {}) => {
    return new Promise((resolve) => {
      win.webContents.print(
        { silent: false, printBackground: true, ...options },
        (success, errorType) => resolve({ success, errorType })
      );
    });
  });

  // === Notifications système ===
  ipcMain.handle('notify', (_event, { title = 'ERP Pro', body = '' } = {}) => {
    if (Notification.isSupported()) {
      new Notification({ title, body, icon: ICON_PATH }).show();
      return true;
    }
    return false;
  });

  // === Dialogs fichiers ===
  ipcMain.handle('open-file-dialog', (_event, options = {}) => {
    return dialog.showOpenDialog(win, {
      properties: ['openFile'],
      filters: [
        { name: 'Tous les fichiers', extensions: ['*'] },
        { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp'] },
        { name: 'Documents', extensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx'] },
      ],
      ...options,
    });
  });

  ipcMain.handle('save-file-dialog', (_event, options = {}) => {
    return dialog.showSaveDialog(win, {
      filters: [
        { name: 'PDF', extensions: ['pdf'] },
        { name: 'Excel', extensions: ['xlsx'] },
        { name: 'Tous les fichiers', extensions: ['*'] },
      ],
      ...options,
    });
  });

  // === Utilitaires ===
  ipcMain.handle('relaunch', () => {
    app.relaunch();
    app.exit(0);
  });

  // Badge (macOS/Linux)
  ipcMain.handle('set-badge', (_event, count) => {
    if (app.setBadgeCount) {
      app.setBadgeCount(typeof count === 'number' ? count : 0);
    }
  });

  // Backend local + serveur central (lecture de configuration).
  ipcMain.handle('backend:port', () => backendHost.getPort());
  ipcMain.handle('backend:central-api-base', () => backendHost.getCentralApiBaseUrl());
  ipcMain.handle('backend:sync-now', () => backendHost.syncNow());

  if (isDev) {
    const url = port ? `${DEV_URL}/?backendPort=${port}` : DEV_URL;
    win.loadURL(url);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    win.loadFile(path.join(__dirname, '..', 'build', 'index.html'), port ? { query: { backendPort: String(port) } } : {});
  }

  // === Electron Security (OWASP) ===
  // Empêche window.open() de créer des fenêtres non contrôlées.
  // Les liens externes sont ouverts dans le navigateur par défaut.
  const ALLOWED_NAVIGATION_HOSTS = isDev
    ? ['localhost', '127.0.0.1']
    : ['app.mihaja-erp.local'];

  win.webContents.setWindowOpenHandler(({ url }) => {
    // Ouvrir les liens externes dans le navigateur système
    const parsed = new URL(url);
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
      require('electron').shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  // Empêche la navigation vers des URLs non autorisées (clicks sur liens,
  // target="_blank", JavaScript). Seules les URLs du backend/api sont permises
  // en plus de l'URL de chargement initiale.
  win.webContents.on('will-navigate', (event, url) => {
    try {
      const parsed = new URL(url);
      const isSameOrigin = ALLOWED_NAVIGATION_HOSTS.includes(parsed.hostname);
      const isApiUrl = parsed.pathname.startsWith('/api/') || parsed.pathname.startsWith('/socket.io');
      if (!isSameOrigin && !isApiUrl) {
        event.preventDefault();
        require('electron').shell.openExternal(url);
      }
    } catch {
      event.preventDefault();
    }
  });
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(buildMenu());
  registerSecureStoreHandlers();
  let port = null;
  try {
    const started = await backendHost.startLocalBackend();
    port = started.port;
  } catch (err) {
    // La fenêtre s'ouvre quand même : écran d'erreur géré côté renderer.
    dialog.showErrorBox(
      'Erreur de démarrage',
      "Impossible de démarrer le serveur local.\n" + String(err));
  }
  createWindow(port);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow(port);
  });
});

app.on('before-quit', () => backendHost.stopLocalBackend());

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

