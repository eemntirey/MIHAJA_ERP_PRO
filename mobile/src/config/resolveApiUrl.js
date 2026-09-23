// mobile/src/config/resolveApiUrl.js
// Résolution de l'URL du backend — logique PURE (sans React Native) pour être
// réutilisable et testable, consommée par config/env.js.
//
// Règle de priorité :
//   1. EXPO_PUBLIC_API_URL pointant vers un hôte NON local (IP LAN, tunnel
//      HTTPS, domaine de production) est utilisée telle quelle : appareil
//      physique, recette, production.
//   2. Sinon (variable absente ou hôte local), l'URL est dérivée de la
//      plateforme d'exécution — cas du développement local :
//        - android (émulateur) → http://10.0.2.2:<port>/api/v1
//          (10.0.2.2 = alias du localhost de la machine hôte)
//        - web (npx expo start --web, port 8081) → http://<hôte de la page>:<port>/api/v1
//          (localhost:8081 → localhost, 192.168.x.y:8081 → 192.168.x.y)
//        - ios (simulateur) / autre → http://localhost:<port>/api/v1
//
// Sans cette résolution, une valeur 10.0.2.2 dans mobile/.env rendait l'API
// injoignable depuis le navigateur ouvert sur http://localhost:8081
// (« Impossible de joindre le serveur. »).

export const DEFAULT_API_PORT = 5000;
export const API_PATH = '/api/v1';

// Hôtes « locaux » : leur valeur dépend de la plateforme, ils doivent donc
// être ré-écrits selon la plateforme courante.
const LOCAL_HOSTS = ['localhost', '127.0.0.1', '::1', '0.0.0.0', '10.0.2.2', '10.0.3.2'];

// Alias d'émulateur Android : à ne jamais dériver depuis le serveur de dev.
const EMULATOR_HOSTS = ['10.0.2.2', '10.0.3.2'];

// Extrait l'hôte d'une URL ('' si l'URL est absente/invalide).
export function extractHost(url) {
  if (typeof url !== 'string') return '';
  const match = /^[a-z][a-z0-9+.-]*:\/\/(\[[^\]]+\]|[^/?#:]+)/i.exec(url.trim());
  if (!match) return '';
  return match[1].replace(/^\[|\]$/g, '').toLowerCase();
}

// Vrai si l'URL cible un hôte local (donc spécifique à une plateforme).
export function isLocalApiUrl(url) {
  const host = extractHost(url);
  return host === '' || LOCAL_HOSTS.includes(host);
}

// Vrai si l'hôte est une IP LAN privée (192.168.x, 10.x, 172.16-31.x) ou un
// nom « .local ». Sert à savoir si un appareil physique peut joindre cet hôte.
export function isPrivateLanHost(host) {
  if (typeof host !== 'string' || !host.trim()) return false;
  const value = host.trim().toLowerCase();
  if (EMULATOR_HOSTS.includes(value)) return false;

  const ipv4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(value);
  if (ipv4) {
    const a = Number(ipv4[1]);
    const b = Number(ipv4[2]);
    if (a === 192 && b === 168) return true;
    if (a === 10) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    return false;
  }

  return value.endsWith('.local');
}

// Extrait l'hôte d'un « hostUri » Expo (ex. '192.168.89.120:8081').
export function hostFromHostUri(hostUri) {
  if (typeof hostUri !== 'string') return '';
  const value = hostUri.trim();
  if (!value) return '';
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) return extractHost(value);
  return extractHost(`http://${value}`);
}

// URL de l'API déduite de l'hôte du serveur de dev Expo : c'est l'adresse que
// le téléphone sait déjà joindre (il vient d'y télécharger le bundle), on
// remplace simplement le port Metro par celui du backend.
export function apiUrlFromDevServerHost(devServerHost, port = DEFAULT_API_PORT) {
  const host = typeof devServerHost === 'string' ? devServerHost.trim().toLowerCase() : '';
  if (!isPrivateLanHost(host)) return '';
  return `http://${host}:${port}${API_PATH}`;
}

// URL de repli (appareil physique) : '' si elle est inutile (hôte non LAN ou
// identique à l'URL principale).
export function resolveFallbackApiBaseUrl(primaryUrl, devServerHost, port = DEFAULT_API_PORT) {
  const fallback = apiUrlFromDevServerHost(devServerHost, port);
  if (!fallback) return '';
  const primary = typeof primaryUrl === 'string' ? primaryUrl.replace(/\/+$/, '') : '';
  return fallback === primary ? '' : fallback;
}

// Construit l'URL de développement local adaptée à la plateforme.
export function buildLocalApiUrl(platform, hostname, port = DEFAULT_API_PORT) {
  if (platform === 'android') return `http://10.0.2.2:${port}${API_PATH}`;
  if (platform === 'web') {
    const host =
      typeof hostname === 'string' && hostname.trim() ? hostname.trim() : 'localhost';
    return `http://${host}:${port}${API_PATH}`;
  }
  return `http://localhost:${port}${API_PATH}`;
}

// URL finale du backend, sans slash final.
export function resolveApiBaseUrl(configuredUrl, platform, hostname, port = DEFAULT_API_PORT) {
  const explicit =
    typeof configuredUrl === 'string' ? configuredUrl.trim().replace(/\/+$/, '') : '';
  if (explicit && !isLocalApiUrl(explicit)) return explicit;
  return buildLocalApiUrl(platform, hostname, port);
}

// Valide un port fourni par l'environnement (retombe sur 5000 si invalide).
export function resolveApiPort(rawPort, fallback = DEFAULT_API_PORT) {
  const parsed = Number.parseInt(rawPort, 10);
  return Number.isInteger(parsed) && parsed > 0 && parsed < 65536 ? parsed : fallback;
}

export default resolveApiBaseUrl;
