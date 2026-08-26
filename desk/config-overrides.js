// desk/config-overrides.js
// Permet au build CRA (react-app-rewired) d'importer la bibliothèque partagée
// située hors de src (../shared) et de transpiler le JSX qu'elle contient.
const path = require('path');
const { override, removeModuleScopePlugin, addWebpackAlias } = require('customize-cra');

const sharedDir = path.resolve(__dirname, '../shared');

function addSharedToBabelInclude() {
  return (config) => {
    const jsRule = config.module.rules.find((rule) => Array.isArray(rule.oneOf));
    if (jsRule && jsRule.oneOf) {
      const babelRule = jsRule.oneOf.find(
        (rule) => rule.test && /\.(js|mjs|jsx|ts|tsx)$/.test(rule.test.toString())
      );
      if (babelRule) {
        babelRule.include = [].concat(babelRule.include || [], sharedDir);
      } else {
        const candidate = jsRule.oneOf[3];
        if (candidate && candidate.test) {
          candidate.include = [].concat(candidate.include || [], sharedDir);
        }
      }
    }
    return config;
  };
}

module.exports = override(
  removeModuleScopePlugin(),
  addSharedToBabelInclude(),
  addWebpackAlias({ '@shared': sharedDir })
);
