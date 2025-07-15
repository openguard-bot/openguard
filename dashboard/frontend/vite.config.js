import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';
import autoprefixer from 'autoprefixer';
import path from "path"

// https://vitejs.dev/config/
export default defineConfig({
  base: '/dashboard/',
  plugins: [react(), tailwindcss(), autoprefixer()],
    resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.jsx',
  },
})
