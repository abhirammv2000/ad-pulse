import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  build: {
    // The Dockerfile copies this folder into nginx.
    outDir: 'build',
  },
  test: {
    environment: 'jsdom',
    // describe, test, expect and vi are available without importing them.
    globals: true,
    setupFiles: './src/setupTests.js',
    // The first render in a file compiles a lot of MUI. A slow machine should not fail a test for that.
    testTimeout: 20000,
  },
});
