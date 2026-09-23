import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const sharedDir = path.resolve(__dirname, '../shared');
const deskSharedDir = path.resolve(__dirname, 'shared');

export default defineConfig({
  plugins: [react()],
  esbuild: {
    // Convention CRA conservée : le JSX vit dans des fichiers .js.
    // Sans cette option, esbuild refuse le JSX dans .js (« The JSX syntax
    // extension is not currently enabled »). Même approche que super-admin.
    // Le pattern couvre aussi le dossier racine ../shared (alias @shared),
    // en dehors de desk/src — sinon SyncContext.jsx & co. ne passent pas.
    loader: 'jsx',
    include: /(src|shared)[\\/].*\.[jt]sx?$/,
    exclude: [],
  },
  resolve: {
    alias: {
      '@shared': sharedDir,
      '@desk-shared': deskSharedDir,
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3001,
    strictPort: true,
    fs: {
      allow: [sharedDir, deskSharedDir, __dirname],
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
  optimizeDeps: {
    include: ['react', 'react-dom'],
    esbuildOptions: {
      loader: { '.js': 'jsx' },
    },
  },
});
