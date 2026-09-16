import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const sharedDir = path.resolve(__dirname, '../shared');
const deskSharedDir = path.resolve(__dirname, 'shared');

export default defineConfig({
  plugins: [react()],
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
  },
});
