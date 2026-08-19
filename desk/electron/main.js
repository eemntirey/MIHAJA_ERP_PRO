// desk/electron/main.js
// Processus principal Electron pour l'application desktop ERP Pro.
const { app, BrowserWindow, Menu, ipcMain, Notification, dialog } = require('electron');
const path = require('path');

const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;

const DEV_URL = 'http://localhost:3001';

let win = null;

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

function createWindow() {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1280,
    minHeight: 720,
    backgroundColor: '#111111',
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
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
      new Notification({ title, body }).show();
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

  if (isDev) {
    win.loadURL(DEV_URL);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    win.loadFile(path.join(__dirname, '..', 'build', 'index.html'));
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(buildMenu());
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

