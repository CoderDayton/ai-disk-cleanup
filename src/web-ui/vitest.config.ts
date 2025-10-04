import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import { TanStackRouterVite } from '@tanstack/router-vite-plugin';
import path from 'path';

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
  test: {
    // Test environment
    environment: 'jsdom',
    setupFiles: ['./tests/setup/tests-setup.ts'],

    // Test files
    include: [
      'tests/**/*.{test,spec}.{js,ts,tsx}',
      'src/**/__tests__/**/*.{test,spec}.{js,ts,tsx}',
      'src/**/*.{test,spec}.{js,ts,tsx}',
    ],
    exclude: [
      'node_modules',
      'dist',
      'build',
      '.git',
      'coverage',
    ],

    // Coverage
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules',
        'dist',
        'build',
        '.git',
        'coverage',
        'tests/**',
        '**/*.d.ts',
        '**/*.config.*',
        '**/stories/**',
        'src/**/index.ts',
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70,
        },
      },
    },

    // Performance
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        maxThreads: 4,
        minThreads: 1,
      },
    },

    // Test settings
    globals: true,
    testTimeout: 10000,
    hookTimeout: 10000,
    isolate: true,
    passWithNoTests: false,

    // Reporting
    reporter: ['default', 'junit'],
    outputFile: {
      junit: './coverage/junit.xml',
    },

    // Watch mode
    watch: false,
    watchExclude: [
      'node_modules',
      'dist',
      'build',
      'coverage',
    ],

    // Global settings
    clearScreen: false,
    envPrefix: ['VITE_', 'TAURI_'],
  },

  // Optimize dependencies for testing
  optimizeDeps: {
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
      '@testing-library/react',
      '@testing-library/jest-dom',
      '@testing-library/user-event',
    ],
  },
});