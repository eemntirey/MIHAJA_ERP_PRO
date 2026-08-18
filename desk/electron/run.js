// desk/electron/run.js
// Lance le processus principal Electron en supprimant ELECTRON_RUN_AS_NODE
// (variable d'environnement qui, si elle est définie, force Electron à se
// comporter comme Node simple et empêche require('electron') de fonctionner).
const { spawn } = require('child_process');
const path = require('path');

delete process.env.ELECTRON_RUN_AS_NODE;

const electron = require('electron'); // chemin vers l'exécutable Electron
const main = path.join(__dirname, 'main.js');
const child = spawn(electron, [main, ...process.argv.slice(2)], {
  stdio: 'inherit',
  env: process.env,
});

child.on('exit', (code) => process.exit(code === null ? 1 : code));
