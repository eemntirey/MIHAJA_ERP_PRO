import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const sharedDir = path.resolve(__dirname, '../../shared');

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@shared': sharedDir,
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    fs: {
      // Autoriser les imports depuis ../../shared (monorepo)
      allow: [sharedDir, __dirname],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/public': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/ready': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://127.0.0.1:5000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'build',
    sourcemap: false,
  },
  // Vite pré-bundle les dépendances automatiquement — pas besoin du trick
  // react/react-dom alias du config-overrides.js CRA.
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },
});
