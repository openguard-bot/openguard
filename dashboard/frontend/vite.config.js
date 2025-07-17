import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';
import path from "path"

// https://vitejs.dev/config/
export default defineConfig({
  base: '/dashboard/',
  plugins: [react(), tailwindcss()],
    resolve: {
    alias: {
      // eslint-disable-next-line no-undef
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.tsx',
  },
})
