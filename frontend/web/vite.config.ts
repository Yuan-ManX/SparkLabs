import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/sparklabs/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@components': path.resolve(__dirname, 'components'),
      '@hooks': path.resolve(__dirname, 'hooks'),
      '@utils': path.resolve(__dirname, 'utils'),
      '@types': path.resolve(__dirname, 'types'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
    historyApiFallback: {
      rewrites: [
        { from: /^\/sparklabs\/editor$/, to: '/sparklabs/index.html' },
        { from: /^\/sparklabs$/, to: '/sparklabs/index.html' },
      ],
    },
  },
});
