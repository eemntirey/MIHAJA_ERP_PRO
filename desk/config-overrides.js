// desk/config-overrides.js
// Permet au build CRA (react-app-rewired) d'importer la bibliothèque partagée
// située hors de src (../shared) et de transpiler le JSX qu'elle contient.
const path = require('path');
const { override, removeModuleScopePlugin, addWebpackAlias } = require('customize-cra');

const sharedDir = path.resolve(__dirname, '../shared');
const deskSharedDir = path.resolve(__dirname, 'shared');

function addSharedToBabelInclude() {
  return (config) => {
    const jsRule = config.module.rules.find((rule) => Array.isArray(rule.oneOf));
    if (jsRule && jsRule.oneOf) {
      const babelRule = jsRule.oneOf.find(
        (rule) => rule.test instanceof RegExp && rule.test.test('foo.jsx')
      );
      if (babelRule) {
        babelRule.include = [].concat(babelRule.include || [], sharedDir, deskSharedDir);
      } else {
        const candidate = jsRule.oneOf[3];
        if (candidate && candidate.test) {
          candidate.include = [].concat(candidate.include || [], sharedDir, deskSharedDir);
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
