// desk/electron/preload.js
// Pont sécurisé entre le renderer et le processus principal (contexte isolé
// + sandbox). Audit P1-2 : ce preload n'utilise QUE contextBridge/ipcRenderer :
// safeStorage, fs et le disque sont exclusivement manipulés dans main.js.
const { contextBridge, ipcRenderer } = require('electron');

// Store sécurisé : délègue TOUTES les opérations au processus principal via
// IPC (canal strict, clés préfixées erp.desk.*, chiffré au repos par
// safeStorage). L'interface reste synchrone pour storageAdapter.
const secureStore = {
  get: (key) => {
    try {
      return ipcRenderer.sendSync('secure-store:get', key);
    } catch {
      return null;
    }
  },
  set: (key, value) => {
    try {
      return ipcRenderer.sendSync('secure-store:set', key, value);
    } catch {
      return false;
    }
  },
  remove: (key) => {
    try {
      return ipcRenderer.sendSync('secure-store:remove', key);
    } catch {
      return false;
    }
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
  // Renvoie une fonction de désabonnement : la barre de fenêtre est montée
  // successivement sur l'écran de connexion puis dans le layout applicatif,
  // ce qui évite d'accumuler des listeners dans le renderer.
  onMaximizeChanged: (callback) => {
    const listener = (_event, isMaximized) => callback(isMaximized);
    ipcRenderer.on('window:maximize-changed', listener);
    return () => ipcRenderer.removeListener('window:maximize-changed', listener);
  },
  // Déplacement de la fenêtre depuis une zone drag custom (barre de titre).
  startDragging: () => ipcRenderer.send('window:start-move'),

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