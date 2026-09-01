// desk/electron/preload.js
// Pont sécurisé entre le renderer et le processus principal (contexte isolé).
const { contextBridge, ipcRenderer, safeStorage, app } = require('electron');
const fs = require('fs');
const path = require('path');

// Store sécurisé (chiffré au repos via safeStorage) pour le desktop.
// Le renderer y accède de façon synchrone via window.electron.secureStore.
const STORE_PATH = path.join(app.getPath('userData'), 'secure-store.json');
let _cache = {};
try {
  _cache = JSON.parse(fs.readFileSync(STORE_PATH, 'utf8'));
} catch {
  _cache = {};
}
const _persist = () => {
  try {
    fs.writeFileSync(STORE_PATH, JSON.stringify(_cache));
  } catch {
    /* disque indisponible : on garde en mémoire */
  }
};
const secureStore = {
  get: (key) => {
    const v = _cache[key];
    if (v == null) return null;
    try {
      return safeStorage.decryptString(Buffer.from(v, 'base64'));
    } catch {
      return v;
    }
  },
  set: (key, value) => {
    try {
      _cache[key] = safeStorage.encryptString(String(value)).toString('base64');
    } catch {
      _cache[key] = String(value);
    }
    _persist();
  },
  remove: (key) => {
    delete _cache[key];
    _persist();
  },
};

contextBridge.exposeInMainWorld('electron', {
  // === Contrôles de fenêtre ===
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  unmaximize: () => ipcRenderer.send('window:unmaximize'),
  close: () => ipcRenderer.send('window:close'),
  quit: () => ipcRenderer.send('window:quit'),
  isMaximized: () => ipcRenderer.invoke('window:is-maximized'),
  onMaximizeChanged: (callback) => {
    ipcRenderer.on('window:maximize-changed', (_event, isMaximized) => callback(isMaximized));
  },

  // === Impression ===
  print: (options) => ipcRenderer.invoke('print', options),

  // === Notifications système ===
  notify: (title, body) => ipcRenderer.invoke('notify', { title, body }),

  // === Dialogs fichiers ===
  openFileDialog: (options) => ipcRenderer.invoke('open-file-dialog', options),
  saveFileDialog: (options) => ipcRenderer.invoke('save-file-dialog', options),

  // === Utilitaires ===
  relaunch: () => ipcRenderer.invoke('relaunch'),
  setBadge: (count) => ipcRenderer.invoke('set-badge', count),

  // === Store sécurisé (tokens + préférences) ===
  secureStore,
});

