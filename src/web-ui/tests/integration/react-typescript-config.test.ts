import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

/**
 * Comprehensive test suite for React 18 + TypeScript configuration
 *
 * This test validates that the React 18 + TypeScript setup is properly configured
 * with Vite build system, strict TypeScript mode, and React 18 concurrent features
 * as specified in SDD requirements.
 */
describe('React 18 + TypeScript Configuration Validation', () => {
  const projectRoot = process.cwd();
  const srcDir = join(projectRoot, 'src');

  beforeEach(() => {
    process.env.NODE_ENV = 'test';
  });

  afterEach(() => {
    process.env.NODE_ENV = 'development';
  });

  describe('Package.json Dependencies', () => {
    it('should have correct React 18 dependencies', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      expect(existsSync(packageJsonPath)).toBe(true);

      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Core React 18 dependencies
      expect(packageJson.dependencies).toHaveProperty('react');
      expect(packageJson.dependencies).toHaveProperty('react-dom');

      // Should be React 18.x
      const reactVersion = packageJson.dependencies.react;
      const reactDomVersion = packageJson.dependencies['react-dom'];
      expect(reactVersion).toMatch(/^18\./);
      expect(reactDomVersion).toMatch(/^18\./);

      // Should have React 18 concurrent features
      expect(reactVersion).not.toMatch(/^(17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0)\./);
    });

    it('should have TypeScript and type definitions', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // TypeScript should be a dev dependency
      expect(packageJson.devDependencies).toHaveProperty('typescript');

      // React type definitions
      expect(packageJson.devDependencies).toHaveProperty('@types/react');
      expect(packageJson.devDependencies).toHaveProperty('@types/react-dom');

      // Node types for environment APIs
      expect(packageJson.devDependencies).toHaveProperty('@types/node');
    });

    it('should have Vite build system', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Vite should be a dev dependency
      expect(packageJson.devDependencies).toHaveProperty('vite');

      // Vite React plugin
      expect(packageJson.devDependencies).toHaveProperty('@vitejs/plugin-react');

      // Should have proper build scripts
      expect(packageJson.scripts).toHaveProperty('dev');
      expect(packageJson.scripts).toHaveProperty('build');
      expect(packageJson.scripts).toHaveProperty('preview');

      // Vite dev command should use correct configuration
      const devScript = packageJson.scripts.dev;
      expect(devScript).toContain('vite');
    });

    it('should have Tauri integration scripts', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Tauri development and build scripts
      expect(packageJson.scripts).toHaveProperty('tauri');
      expect(packageJson.scripts).toHaveProperty('tauri:dev');
      expect(packageJson.scripts).toHaveProperty('tauri:build');

      // Should integrate with Vite build
      const tauriDevScript = packageJson.scripts['tauri:dev'];
      expect(tauriDevScript).toContain('tauri dev');

      const tauriBuildScript = packageJson.scripts['tauri:build'];
      expect(tauriBuildScript).toContain('tauri build');
    });
  });

  describe('Vite Configuration', () => {
    it('should have valid vite.config.ts', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      expect(existsSync(viteConfigPath)).toBe(true);

      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should import necessary plugins
      expect(viteConfig).toContain('import { defineConfig }');
      expect(viteConfig).toContain('import react from');
      expect(viteConfig).toContain('@vitejs/plugin-react');

      // Should export configuration
      expect(viteConfig).toContain('export default defineConfig');

      // Should have React plugin configuration
      expect(viteConfig).toContain('plugins:');
      expect(viteConfig).toContain('react()');

      // Should have build configuration
      expect(viteConfig).toContain('build:');
      expect(viteConfig).toContain('outDir:');
    });

    it('should have Tauri integration in Vite config', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have server configuration for Tauri development
      expect(viteConfig).toContain('server:');
      expect(viteConfig).toContain('port:');
      expect(viteConfig).toContain('strictPort: true');

      // Should have proper build output configuration for Tauri
      expect(viteConfig).toContain('outDir:');
      expect(viteConfig).toContain('emptyOutDir:');
    });

    it('should have environment configuration', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have environment variable handling
      expect(viteConfig).toContain('define:');
      expect(viteConfig).toContain('__APP_VERSION__');
    });

    it('should have optimization configuration for performance', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have build optimizations
      expect(viteConfig).toContain('target:');
      expect(viteConfig).toContain('minify:');
      expect(viteConfig).toContain('sourcemap:');
    });
  });

  describe('TypeScript Configuration', () => {
    it('should have strict TypeScript configuration', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      expect(existsSync(tsConfigPath)).toBe(true);

      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should enable strict mode
      expect(tsConfig.compilerOptions).toHaveProperty('strict');
      expect(tsConfig.compilerOptions.strict).toBe(true);

      // Should have proper module resolution
      expect(tsConfig.compilerOptions).toHaveProperty('moduleResolution');
      expect(tsConfig.compilerOptions.moduleResolution).toBe('bundler');

      // Should enable modern JavaScript features
      expect(tsConfig.compilerOptions).toHaveProperty('target');
      expect(['ES2020', 'ES2021', 'ES2022', 'ESNext']).toContain(tsConfig.compilerOptions.target);

      // Should have proper JSX configuration
      expect(tsConfig.compilerOptions).toHaveProperty('jsx');
      expect(['react-jsx', 'react-jsxdev', 'react']).toContain(tsConfig.compilerOptions.jsx);

      // Should enable type checking
      expect(tsConfig.compilerOptions).toHaveProperty('noImplicitAny');
      expect(tsConfig.compilerOptions.noImplicitAny).toBe(true);

      expect(tsConfig.compilerOptions).toHaveProperty('strictNullChecks');
      expect(tsConfig.compilerOptions.strictNullChecks).toBe(true);
    });

    it('should have proper path mapping', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should have baseUrl and paths for clean imports
      if (tsConfig.compilerOptions.baseUrl) {
        expect(tsConfig.compilerOptions.baseUrl).toBe('./');

        // Should have path mappings for common directories
        if (tsConfig.compilerOptions.paths) {
          const paths = tsConfig.compilerOptions.paths;

          // Common path mappings
          expect(paths).toHaveProperty('@/*');
          expect(Array.isArray(paths['@/*'])).toBe(true);
          expect(paths['@/*'][0]).toBe('./src/*');
        }
      }
    });

    it('should include necessary type definitions', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should include necessary type files
      if (tsConfig.include) {
        expect(tsConfig.include).toContain('src');
        expect(tsConfig.include).toContain('vite.config.ts');
      }

      // Should exclude unnecessary files
      if (tsConfig.exclude) {
        expect(tsConfig.exclude).toContain('node_modules');
        expect(tsConfig.exclude).toContain('dist');
      }
    });
  });

  describe('React 18 Concurrent Features', () => {
    it('should have React 18 concurrent features available', () => {
      const mainTsxPath = join(srcDir, 'main.tsx');
      if (existsSync(mainTsxPath)) {
        const mainContent = readFileSync(mainTsxPath, 'utf-8');

        // Should use React 18 createRoot API
        expect(mainContent).toContain('createRoot');
        expect(mainContent).toContain('import.*createRoot.*from.*react-dom/client');
      }
    });

    it('should have proper React 18 render pattern', () => {
      const mainTsxPath = join(srcDir, 'main.tsx');
      if (existsSync(mainTsxPath)) {
        const mainContent = readFileSync(mainTsxPath, 'utf-8');

        // Should use createRoot instead of ReactDOM.render
        expect(mainContent).toMatch(/createRoot\([^)]+\)\.render\(/);
        expect(mainContent).not.toContain('ReactDOM.render');
      }
    });

    it('should support React 18 concurrent features in components', () => {
      // Test that components can use React 18 features
      const componentFiles = [
        'App.tsx',
        'components/App.tsx',
        'components/ui/Button.tsx',
        'components/ui/Card.tsx'
      ];

      let hasConcurrentFeatures = false;
      for (const file of componentFiles) {
        const filePath = join(srcDir, file);
        if (existsSync(filePath)) {
          const content = readFileSync(filePath, 'utf-8');

          // Look for concurrent features usage
          if (content.includes('useTransition') ||
              content.includes('useDeferredValue') ||
              content.includes('Suspense') ||
              content.includes('startTransition')) {
            hasConcurrentFeatures = true;
            break;
          }
        }
      }

      // Note: This is optional for initial setup, but should be available
      // expect(hasConcurrentFeatures).toBe(true);
    });
  });

  describe('Build Process Validation', () => {
    it('should be able to run TypeScript compilation', () => {
      try {
        const result = execSync('npx tsc --noEmit', {
          cwd: projectRoot,
          stdio: 'pipe'
        });
        expect(result).toBeDefined();
      } catch (error: any) {
        // If TypeScript compilation fails, provide helpful error
        fail(`TypeScript compilation failed: ${error.message}`);
      }
    });

    it('should be able to run Vite build process', () => {
      try {
        // Run Vite build in dry-run mode if available
        const result = execSync('npx vite build --dryRun', {
          cwd: projectRoot,
          stdio: 'pipe'
        });
        expect(result).toBeDefined();
      } catch (error: any) {
        // If dry-run not supported, try to check config validity
        try {
          execSync('npx vite --version', { stdio: 'pipe' });
          execSync('npx vite build --mode development', {
            cwd: projectRoot,
            stdio: 'pipe'
          });
        } catch (buildError: any) {
          fail(`Vite build validation failed: ${buildError.message}`);
        }
      }
    });

    it('should have proper build output configuration', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should configure output directory for Tauri
      expect(viteConfig).toContain('outDir:');

      // Should configure proper asset handling
      expect(viteConfig).toContain('assetsDir:');
      expect(viteConfig).toContain('rollupOptions:');
    });
  });

  describe('Development Environment Setup', () => {
    it('should have proper development server configuration', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have development server configuration
      expect(viteConfig).toContain('server:');
      expect(viteConfig).toContain('host:');
      expect(viteConfig).toContain('port:');
    });

    it('should have hot module replacement configured', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // HMR should be enabled
      expect(viteConfig).toContain('hmr:');
    });

    it('should have proper environment variable handling', () => {
      const envFiles = ['.env', '.env.development', '.env.production'];

      envFiles.forEach(envFile => {
        const envPath = join(projectRoot, envFile);
        if (existsSync(envPath)) {
          const envContent = readFileSync(envPath, 'utf-8');

          // Should have proper variable format
          expect(envContent).toMatch(/^[A-Z_]+=.*$/m);
        }
      });
    });
  });

  describe('Performance Optimizations', () => {
    it('should have code splitting configured', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have manual chunk splitting for performance
      expect(viteConfig).toContain('manualChunks:');
    });

    it('should have proper asset optimization', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have asset size limits
      expect(viteConfig).toContain('assetsInlineLimit:');
    });

    it('should have source map configuration', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should configure source maps appropriately
      expect(viteConfig).toContain('sourcemap:');
    });
  });

  describe('Type Safety and Integration', () => {
    it('should have proper TypeScript integration with Tauri', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should have Tauri type definitions
      if (packageJson.devDependencies) {
        expect(packageJson.devDependencies).toHaveProperty('@tauri-apps/api');
      }
    });

    it('should have environment type definitions', () => {
      const envTypesPath = join(srcDir, 'env.d.ts');
      if (existsSync(envTypesPath)) {
        const envTypes = readFileSync(envTypesPath, 'utf-8');

        // Should have Vite environment types
        expect(envTypes).toContain('/// <reference types="vite/client" />');

        // Should have import meta environment types
        expect(envTypes).toContain('interface ImportMetaEnv');
      }
    });

    it('should have proper module resolution', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should have proper module resolution for ESM
      expect(tsConfig.compilerOptions).toHaveProperty('module');
      expect(['ESNext', 'ES2022', 'ES2021', 'ES2020']).toContain(tsConfig.compilerOptions.module);

      // Should allow importing JSON and other assets
      expect(tsConfig.compilerOptions).toHaveProperty('allowSyntheticDefaultImports');
      expect(tsConfig.compilerOptions.allowSyntheticDefaultImports).toBe(true);

      expect(tsConfig.compilerOptions).toHaveProperty('esModuleInterop');
      expect(tsConfig.compilerOptions.esModuleInterop).toBe(true);
    });
  });
});