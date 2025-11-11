import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React libraries
          'vendor-react': ['react', 'react-dom', 'react-redux'],
          // Redux toolkit
          'vendor-redux': ['@reduxjs/toolkit'],
          // Large visualization library
          'vendor-plotly': ['plotly.js', 'react-plotly.js'],
          // UI framework
          'vendor-antd': ['antd', '@ant-design/icons'],
          // Form libraries
          'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
          // Flow diagram
          'vendor-flow': ['reactflow', '@dnd-kit/core', '@dnd-kit/sortable'],
          // Utilities
          'vendor-utils': ['axios']
        }
      }
    },
    chunkSizeWarningLimit: 1000,
    // Enable source maps for production debugging (optional)
    sourcemap: false,
    // Optimize minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true
      }
    }
  }
})
