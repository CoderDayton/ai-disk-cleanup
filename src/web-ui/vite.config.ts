import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    TanStackRouterVite({
      autoCodeSplitting: true,
      generatedRouteTree: './src/routes/routeTree.gen.ts',
      routesDirectory: './src/routes',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/stores': path.resolve(__dirname, './src/stores'),
      '@/services': path.resolve(__dirname, './src/services'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/styles': path.resolve(__dirname, './src/styles'),
    },
  },
  server: {
    port: 1420,
    strictPort: true,
    host: false,
  },
  build: {
    // Tauri expects the final build to be in the `dist` directory
    outDir: 'dist',
    // Tauri supports es2021
    target: 'es2021',
    // Optimize for Tauri's smaller bundle size
    minify: 'esbuild',
    sourcemap: true,
    // Don't inline assets that are larger than this size
    assetsInlineLimit: 4096,
  },
  optimizeDeps: {
    // Pre-bundle these dependencies for faster development
    include: [
      'react',
      'react-dom',
      '@tanstack/react-router',
      '@tanstack/react-query',
      'zustand',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-progress',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-select',
      '@radix-ui/react-separator',
      '@radix-ui/react-slot',
      '@radix-ui/react-switch',
      '@radix-ui/react-tabs',
      '@radix-ui/react-toast',
      'class-variance-authority',
      'clsx',
      'lucide-react',
      'tailwind-merge',
    ],
  },
  clearScreen: false,
  envPrefix: ['VITE_', 'TAURI_'],
})