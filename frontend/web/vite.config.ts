import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/SparkLabs/Editor/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@components': path.resolve(__dirname, 'components'),
      '@hooks': path.resolve(__dirname, 'hooks'),
      '@utils': path.resolve(__dirname, 'utils'),
      '@types': path.resolve(__dirname, 'types'),
      '@store': path.resolve(__dirname, 'store'),
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
        { from: /^\/SparkLabs\/Editor$/, to: '/SparkLabs/Editor/index.html' },
        { from: /^\/SparkLabs\/Editor\/.*$/, to: '/SparkLabs/Editor/index.html' },
      ],
    },
  },
});
