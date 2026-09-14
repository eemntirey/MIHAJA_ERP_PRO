// web/frontend/config-overrides.js
// Permet au build CRA (react-app-rewired) d'importer la bibliothèque partagée
// située hors de src (../../shared) et de transpiler le JSX qu'elle contient.
//
// IMPORTANT — pourquoi les alias `react` / `react-dom` sont nécessaires :
// les modules de ../../shared (ex. shared/contexts/AuthContext.jsx) résolvent
// `import React from 'react'` depuis le node_modules RACINE du monorepo
// (webpack de CRA place 'node_modules' devant web/frontend/node_modules), ce qui
// charge une DEUXIÈME instance de React dans le bundle. ReactDOM et le code de
// web/frontend/src/ utilisent la copie locale de web/frontend/node_modules.
// Résultat : "Invalid hook call" / "Cannot read properties of null (reading
// 'useState')" dans AuthProvider. Ces alias forcent UNE seule copie partout.
const path = require('path');
const { override, addWebpackAlias } = require('customize-cra');

const sharedDir = path.resolve(__dirname, '../../shared');
const appNodeModules = path.resolve(__dirname, 'node_modules');
const reactRoot = path.join(appNodeModules, 'react');
const reactDomRoot = path.join(appNodeModules, 'react-dom');

function addBabelInclude(include) {
  return (config) => {
    const jsRule = config.module.rules.find((rule) => Array.isArray(rule.oneOf));
    if (jsRule && jsRule.oneOf) {
      const babelLoader = jsRule.oneOf.find(
        (rule) => rule.loader && rule.loader.includes('babel-loader')
      );
      if (babelLoader) {
        babelLoader.include = [].concat(babelLoader.include || [], include);
      }
    }
    return config;
  };
}

function removeModuleScopePlugin(config) {
  if (!config || !config.resolve) {
    return config;
  }
  config.resolve.plugins = (config.resolve.plugins || []).filter(
    (plugin) => plugin.constructor.name !== 'ModuleScopePlugin'
  );
  return config;
}

function makeCacheSeeConfigOverrides(config) {
  // Le cache filesystem de webpack 5 (activé par CRA5) n'invalide PAS lorsque
  // config-overrides.js change (react-app-rewired modifie la config après coup,
  // hors des buildDependencies de CRA). Sans cette ligne, un changement
  // d'alias est ignoré et le bundle reste l'ancien, depuis le cache.
  if (config.cache && config.cache.buildDependencies && Array.isArray(config.cache.buildDependencies.defaultConfig)) {
    config.cache.buildDependencies.defaultConfig.push(__filename);
  }
  return config;
}

module.exports = override(
  removeModuleScopePlugin,
  makeCacheSeeConfigOverrides,
  addBabelInclude([sharedDir]),
  addWebpackAlias({
    '@shared': sharedDir,
    // Forcer UNE seule copie de React et de ReactDOM dans le bundle.
    react: reactRoot,
    'react-dom': reactDomRoot,
  })
);
