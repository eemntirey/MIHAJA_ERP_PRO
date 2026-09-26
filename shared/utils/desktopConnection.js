// shared/utils/desktopConnection.js
// Routage Desk : serveur central en priorité, backend SQLite uniquement
// lorsque le central est réellement indisponible.
// Le test porte sur /health du serveur central, pas sur navigator.onLine.

const PROBE_TTL_MS = 10000;
const PROBE_TIMEOUT_MS = 5000;

let mode = 'unknown';
let checkedAt = 0;
let centralBasePromise = null;

const isElectron = () => (
  typeof window !== 'undefined'
  && !!window.electron
  && !!window.electron.backend
);

const normalize = (value) => {
  if (!value) return '';
  return String(value).replace(/\/+$/, '');
};

const localBase = async () => {
  if (!isElectron()) return '';
  const port = await window.electron.backend.getPort();
  return port ? `http://127.0.0.1:${port}/api/v1` : '';
};

const centralBase = async () => {
  if (!isElectron()) return '';
  if (!centralBasePromise) {
    centralBasePromise = window.electron.backend
      .getCentralApiBaseUrl()
      .then((url) => {
        const base = normalize(url);
        return base ? `${base}/api/v1` : '';
      })
      .catch(() => '');
  }
  return centralBasePromise;
};

const probe = async (base) => {
  if (!base || typeof fetch !== 'function') return false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(`${base.replace(/\/api\/v1$/, '')}/health`, {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
};

const notifyMode = (next) => {
  if (mode === next) return;
  const previous = mode;
  mode = next;
  if (typeof window === 'undefined') return;

  window.dispatchEvent(new CustomEvent('desktop:connection-change', {
    detail: { mode: next, previous },
  }));

  // Au retour du central, lancer immédiatement un cycle push/pull sur le
  // backend local. Ce cycle utilise son jeton de service déjà cache apres le
  // dernier login en ligne.
  if (next === 'central' && previous !== 'unknown') {
    try {
      window.electron?.backend?.syncNow?.();
    } catch {
      // Le routage central ne doit jamais dépendre de cette optimisation.
    }
  }
};

export const resolveDesktopRoute = async ({ forceLocal = false, target = null } = {}) => {
  if (!isElectron()) {
    return { target: 'web', baseURL: null };
  }

  if (target === 'local' || forceLocal) {
    const baseURL = await localBase();
    if (!baseURL) throw new Error('Backend local du Desk indisponible.');
    return { target: 'local', baseURL };
  }

  const now = Date.now();
  if (mode === 'central' && now - checkedAt < PROBE_TTL_MS) {
    return { target: 'central', baseURL: await centralBase() };
  }
  if (mode === 'local' && now - checkedAt < PROBE_TTL_MS) {
    return { target: 'local', baseURL: await localBase() };
  }

  const central = await centralBase();
  const ok = await probe(central);
  checkedAt = Date.now();
  notifyMode(ok ? 'central' : 'local');

  if (ok && central) return { target: 'central', baseURL: central };

  const local = await localBase();
  if (!local) throw new Error('Serveur central et backend local indisponibles.');
  return { target: 'local', baseURL: local };
};

export const markDesktopCentralUnavailable = () => {
  checkedAt = Date.now();
  notifyMode('local');
};

export const getDesktopCentralBase = centralBase;

export const resetDesktopConnectionProbe = () => {
  checkedAt = 0;
  mode = 'unknown';
};

export default resolveDesktopRoute;


if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    checkedAt = 0;
  });
}
