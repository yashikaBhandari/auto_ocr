import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Local dev proxy so relative fetch('/process') hits backend on 8000.
// If VITE_API_BASE is defined, UploadForm uses that instead.
const backendPort = process.env.BACKEND_PORT || '8000';
const backendTarget = `http://127.0.0.1:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/process': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/health': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/metrics': {
        target: backendTarget,
        changeOrigin: true,
      }
    }
  }
});
