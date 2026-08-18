// desk/electron/main.js
// Processus principal Electron pour l'application desktop ERP Pro (Plan §11).
const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');

const isDev = process.env.ELECTRON_DEV === '1' || !app.isPackaged;

const DEV_URL = 'http://localhost:3001';

function createWindow() {
  const win = new BrowserWindow({
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
      // Préserve les raccourcis clavier globaux (CMD+K, etc.)
      spellcheck: false,
    },
  });

  // Contrôles de fenêtre exposés au renderer via IPC (barre de titre custom).
  ipcMain.on('window:minimize', () => win.minimize());
  ipcMain.on('window:maximize', () => win.maximize());
  ipcMain.on('window:unmaximize', () => win.unmaximize());
  ipcMain.on('window:close', () => win.close());
  ipcMain.on('window:quit', () => app.quit());
  ipcMain.handle('window:is-maximized', () => win.isMaximized());

  // Synchronise l'état maximisé/restauré vers la barre personnalisée.
  win.on('maximize', () => win.webContents.send('window:maximize-changed', true));
  win.on('unmaximize', () => win.webContents.send('window:maximize-changed', false));

  if (isDev) {
    win.loadURL(DEV_URL);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    // Build CRA servi en file:// (homepage: "." dans package.json).
    win.loadFile(path.join(__dirname, '..', 'build', 'index.html'));
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
