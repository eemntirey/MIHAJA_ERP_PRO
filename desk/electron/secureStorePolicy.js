// desk/electron/secureStorePolicy.js
// Politique de clés du store sécurisé (audit P1-2), extraite de main.js pour
// être testable sans charger Electron.
//
// Le renderer écrit deux familles de clés :
//  - les préférences scopées par storageAdapter.buildKey -> 'erp.desk.*'
//  - la session d'authentification (authStorage/tokenStore) -> 'erp.auth.*'
//    et les clés legacy 'access_token' / 'refresh_token' / 'user' /
//    'tenant' / 'subscription'.
//
// BUG CORRIGÉ : n'accepter que 'erp.desk.' faisait échouer silencieusement
// chaque écriture de token (secure-store:set -> false ignoré par
// storageAdapter). Aucun Authorization n'était ensuite envoyé -> 401 ->
// 'auth:logout' -> retour immédiat au login dans l'exe packagé.

const SECURE_STORE_ALLOWED_PREFIXES = ['erp.desk.', 'erp.auth.'];

const SECURE_STORE_ALLOWED_KEYS = [
  'access_token',
  'refresh_token',
  'user',
  'tenant',
  'subscription',
];

function isAllowedSecureKey(key) {
  if (typeof key !== 'string' || key.length === 0) return false;
  if (SECURE_STORE_ALLOWED_KEYS.includes(key)) return true;
  return SECURE_STORE_ALLOWED_PREFIXES.some((prefix) => key.startsWith(prefix));
}

module.exports = {
  SECURE_STORE_ALLOWED_PREFIXES,
  SECURE_STORE_ALLOWED_KEYS,
  isAllowedSecureKey,
};
