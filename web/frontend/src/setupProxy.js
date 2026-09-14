// web/frontend/src/setupProxy.js
// Proxy de développement CRA : redirige les appels backend vers Flask.
// Sans ce fichier, `proxy: 127.0.0.1:5000` (package.json) ne couvre que
// /api + /health de façon implicite et laisse /docs + /socket.io passer par
// le dev-server CRA (et donc par le tunnel) -> ERR_CONNECTION_CLOSED côté
// tunnel quand le navigateur retente la navigation. Ce proxy explicite
// garantit qu'un seul tunnel (:3000) sert frontend + backend.
//
// NOTE : create-react-app charge automatiquement src/setupProxy.js au boot.

const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:5000';

const common = {
  target: BACKEND,
  changeOrigin: true,
  logLevel: 'warn',
  timeout: 30000,
  proxyTimeout: 30000,
  onError(err, _req, res) {
    if (res && !res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
    }
    if (res) {
      res.end(JSON.stringify({ message: 'Backend indisponible (proxy dev)' }));
    }
  },
};

module.exports = function (app) {
  app.use('/api', createProxyMiddleware({ ...common }));
  app.use('/public', createProxyMiddleware({ ...common }));
  app.use('/health', createProxyMiddleware({ ...common }));
  app.use('/ready', createProxyMiddleware({ ...common }));
  app.use('/docs', createProxyMiddleware({ ...common }));
  app.use('/socket.io', createProxyMiddleware({ ...common, ws: true }));
};
