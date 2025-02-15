// vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    lib: {
      entry: fileURLToPath(new URL('./src/main.js', import.meta.url)),
      name: 'ChatWidget',
      fileName: 'chat-widget',
      formats: ['iife']
    },
    rollupOptions: {
      output: {
        entryFileNames: 'chat-widget.js',
        assetFileNames: 'chat-widget-assets/[name].[ext]'
      }
    },
    cssCodeSplit: false,
    assetsInlineLimit: 100000 // Inline assets up to 100kb
  }
});