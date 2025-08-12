import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      external: [],
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.woff2')) {
            return 'webfonts/[name][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        }
      }
    }
  }
})
