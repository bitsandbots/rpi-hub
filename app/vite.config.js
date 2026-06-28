import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  build: {
    outDir: '../www/portal/app',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: 'index.html',
        branded: 'index-branded.html',
      },
    },
  },
});
