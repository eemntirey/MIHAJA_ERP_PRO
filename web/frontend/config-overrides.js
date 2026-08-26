// web/frontend/config-overrides.js
// Permet au build CRA (react-app-rewired) d'importer la bibliothèque partagée
// située hors de src (../../shared) et de transpiler le JSX qu'elle contient.
const path = require('path');
const { override, addWebpackAlias } = require('customize-cra');

const sharedDir = path.resolve(__dirname, '../../shared');

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

module.exports = override(
  removeModuleScopePlugin,
  addBabelInclude([sharedDir]),
  addWebpackAlias({ '@shared': sharedDir })
);
