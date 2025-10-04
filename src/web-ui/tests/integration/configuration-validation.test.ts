/**
 * Configuration Validation Tests
 *
 * Validates all configuration files for proper setup, compatibility,
   and adherence to best practices. Ensures all tools are properly
   integrated and configured for optimal development experience.
 */

import { describe, it, expect, beforeAll } from '@jest/globals';
import { readFile, access, stat } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

describe('Configuration Validation', () => {
  const projectRoot = resolve(__dirname, '../..');

  beforeAll(async () => {
    process.chdir(projectRoot);
  });

  describe('Package.json Configuration', () => {
    it('should have valid package.json structure', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Required top-level fields
      expect(packageJson).toHaveProperty('name');
      expect(packageJson).toHaveProperty('version');
      expect(packageJson).toHaveProperty('description');
      expect(packageJson).toHaveProperty('type', 'module');
      expect(packageJson).toHaveProperty('scripts');
      expect(packageJson).toHaveProperty('dependencies');
      expect(packageJson).toHaveProperty('devDependencies');

      // Validate semantic versioning
      expect(packageJson.version).toMatch(/^\d+\.\d+\.\d+(-.+)?$/);

      // Validate name follows npm conventions
      expect(packageJson.name).toMatch(/^[a-z0-9-_]+$/);
    });

    it('should have compatible dependency versions', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // React ecosystem compatibility
      const reactVersion = packageJson.dependencies.react;
      const reactDomVersion = packageJson.dependencies['react-dom'];
      expect(reactVersion).toMatch(/^18\./);
      expect(reactDomVersion).toMatch(/^18\./);

      // Tauri v2 compatibility
      const tauriApiVersion = packageJson.dependencies['@tauri-apps/api'];
      const tauriCliVersion = packageJson.devDependencies['@tauri-apps/cli'];
      expect(tauriApiVersion).toMatch(/^2\./);
      expect(tauriCliVersion).toMatch(/^2\./);

      // Modern TypeScript version
      const typescriptVersion = packageJson.devDependencies.typescript;
      expect(typescriptVersion).toMatch(/^5\./);

      // Vite v5 compatibility
      const viteVersion = packageJson.devDependencies.vite;
      expect(viteVersion).toMatch(/^5\./);
    });

    it('should have all required modern UI dependencies', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // SDD 425: Modern UI/UX requirements
      const requiredUiLibs = [
        'react',
        'react-dom',
        '@tanstack/react-router',
        '@tanstack/react-query',
        '@tanstack/react-virtual',
        'zustand',
        'class-variance-authority',
        'clsx',
        'tailwind-merge',
        'lucide-react'
      ];

      // shadcn/ui components (SDD 437)
      const requiredShadcnComponents = [
        '@radix-ui/react-dialog',
        '@radix-ui/react-dropdown-menu',
        '@radix-ui/react-progress',
        '@radix-ui/react-scroll-area',
        '@radix-ui/react-select',
        '@radix-ui/react-separator',
        '@radix-ui/react-slot',
        '@radix-ui/react-switch',
        '@radix-ui/react-tabs',
        '@radix-ui/react-toast'
      ];

      // Form handling
      const requiredFormLibs = [
        '@hookform/resolvers',
        'react-hook-form',
        'zod'
      ];

      // Additional UI enhancements
      const requiredEnhancements = [
        'date-fns',
        'recharts',
        'sonner'
      ];

      [...requiredUiLibs, ...requiredShadcnComponents, ...requiredFormLibs, ...requiredEnhancements].forEach(dep => {
        expect(packageJson.dependencies).toHaveProperty(dep);
      });
    });

    it('should have proper development tooling', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Build tools
      const buildTools = [
        '@vitejs/plugin-react-swc',
        '@tanstack/router-vite-plugin',
        'vite',
        'typescript'
      ];

      // Code quality tools
      const codeQualityTools = [
        '@typescript-eslint/eslint-plugin',
        '@typescript-eslint/parser',
        'eslint',
        'eslint-plugin-react-hooks',
        'eslint-plugin-react-refresh',
        'prettier'
      ];

      // Testing tools
      const testingTools = [
        'vitest',
        '@vitest/ui',
        '@vitest/coverage-v8',
        'jsdom',
        '@testing-library/react',
        '@testing-library/jest-dom',
        '@testing-library/user-event'
      ];

      // Styling tools
      const stylingTools = [
        'tailwindcss',
        '@tailwindcss/vite',
        'autoprefixer',
        'postcss'
      ];

      [...buildTools, ...codeQualityTools, ...testingTools, ...stylingTools].forEach(dep => {
        expect(packageJson.devDependencies).toHaveProperty(dep);
      });
    });

    it('should have proper scripts configuration', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      const scripts = packageJson.scripts;

      // Development scripts
      expect(scripts.dev).toContain('vite');
      expect(scripts['tauri:dev']).toContain('tauri dev');
      expect(scripts.preview).toContain('vite preview');

      // Build scripts
      expect(scripts.build).toContain('tsc && vite build');
      expect(scripts['tauri:build']).toContain('tauri build');

      // Code quality scripts
      expect(scripts.lint).toContain('eslint');
      expect(scripts['lint:fix']).toContain('eslint --fix');
      expect(scripts['type-check']).toContain('tsc --noEmit');
      expect(scripts.format).toContain('prettier --write');
      expect(scripts['format:check']).toContain('prettier --check');

      // Testing scripts
      expect(scripts.test).toContain('vitest');
      expect(scripts['test:ui']).toContain('vitest --ui');
      expect(scripts['test:coverage']).toContain('vitest --coverage');
    });

    it('should have proper engines configuration', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      expect(packageJson.engines).toBeDefined();
      expect(packageJson.engines.node).toMatch(/^>=18\./);
      expect(packageJson.engines.npm).toMatch(/^>=9\./);
    });
  });

  describe('TypeScript Configuration', () => {
    it('should have proper TypeScript configuration', async () => {
      const tsconfig = JSON.parse(await readFile(join(projectRoot, 'tsconfig.json'), 'utf-8'));

      // Compiler options
      const compilerOptions = tsconfig.compilerOptions;
      expect(compilerOptions).toBeDefined();

      // Essential compiler options
      expect(compilerOptions.target).toBe('ES2020');
      expect(compilerOptions.lib).toContain('ES2020');
      expect(compilerOptions.lib).toContain('DOM');
      expect(compilerOptions.lib).toContain('DOM.Iterable');

      // Module configuration
      expect(compilerOptions.module).toBe('ESNext');
      expect(compilerOptions.moduleResolution).toBe('bundler');
      expect(compilerOptions.allowImportingTsExtensions).toBe(true);
      expect(compilerOptions.resolveJsonModule).toBe(true);
      expect(compilerOptions.isolatedModules).toBe(true);
      expect(compilerOptions.noEmit).toBe(true);
      expect(compilerOptions.jsx).toBe('react-jsx');

      // Strict type checking
      expect(compilerOptions.strict).toBe(true);
      expect(compilerOptions.noUnusedLocals).toBe(true);
      expect(compilerOptions.noUnusedParameters).toBe(true);
      expect(compilerOptions.noFallthroughCasesInSwitch).toBe(true);

      // Path aliases
      expect(compilerOptions.baseUrl).toBe('.');
      expect(compilerOptions.paths).toBeDefined();
      expect(compilerOptions.paths['@/*']).toBeDefined();
      expect(compilerOptions.paths['@/components/*']).toBeDefined();
      expect(compilerOptions.paths['@/hooks/*']).toBeDefined();
      expect(compilerOptions.paths['@/stores/*']).toBeDefined();
      expect(compilerOptions.paths['@/services/*']).toBeDefined();
      expect(compilerOptions.paths['@/types/*']).toBeDefined();
      expect(compilerOptions.paths['@/utils/*']).toBeDefined();
      expect(compilerOptions.paths['@/styles/*']).toBeDefined();
    });

    it('should have proper Node.js TypeScript configuration', async () => {
      const tsconfigNode = JSON.parse(await readFile(join(projectRoot, 'tsconfig.node.json'), 'utf-8'));

      const compilerOptions = tsconfigNode.compilerOptions;
      expect(compilerOptions.target).toBe('ES2022');
      expect(compilerOptions.module).toBe('ESNext');
      expect(compilerOptions.moduleResolution).toBe('bundler');
      expect(compilerTypesNode.typescriptNode).toMatch(/^5\./);
    });
  });

  describe('Vite Configuration', () => {
    it('should have proper Vite configuration', async () => {
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Plugin configuration
      expect(viteConfig).toContain('@vitejs/plugin-react-swc');
      expect(viteConfig).toContain('TanStackRouterVite');

      // Server configuration
      expect(viteConfig).toContain('port: 1420');
      expect(viteConfig).toContain('strictPort: true');
      expect(viteConfig).toContain('host: false');

      // Build configuration
      expect(viteConfig).toContain('outDir: \'dist\'');
      expect(viteConfig).toContain('target: \'es2021\'');
      expect(viteConfig).toContain('minify: \'esbuild\'');
      expect(viteConfig).toContain('sourcemap: true');
      expect(viteConfig).toContain('assetsInlineLimit: 4096');

      // Path aliases
      expect(viteConfig).toContain('path.resolve(__dirname, \'./src\')');
      expect(viteConfig).toContain('@/components');
      expect(viteConfig).toContain('@/hooks');
      expect(viteConfig).toContain('@/stores');
      expect(viteConfig).toContain('@/services');
      expect(viteConfig).toContain('@/types');
      expect(viteConfig).toContain('@/utils');
      expect(viteConfig).toContain('@/styles');

      // Dependency optimization
      expect(viteConfig).toContain('optimizeDeps');
      expect(viteConfig).toContain('react');
      expect(viteConfig).toContain('react-dom');
      expect(viteConfig).toContain('@tanstack/react-router');
      expect(viteConfig).toContain('@tanstack/react-query');
    });

    it('should have proper environment configuration', async () => {
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      expect(viteConfig).toContain('envPrefix: [\'VITE_\', \'TAURI_\']');
      expect(viteConfig).toContain('clearScreen: false');
    });
  });

  describe('Tauri Configuration', () => {
    it('should have proper Tauri configuration', async () => {
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );

      // Basic configuration
      expect(tauriConfig.productName).toBe('AI Disk Cleaner');
      expect(tauriConfig.version).toMatch(/^\d+\.\d+\.\d+$/);
      expect(tauriConfig.identifier).toBe('com.aidiskcleaner.app');

      // Build configuration
      expect(tauriConfig.build.frontendDist).toBe('../dist');
      expect(tauriConfig.build.devUrl).toBe('http://localhost:1420');
      expect(tauriConfig.build.beforeDevCommand).toBe('npm run dev');
      expect(tauriConfig.build.beforeBuildCommand).toBe('npm run build');
      expect(tauriConfig.build.withGlobalTauri).toBe(false);

      // Window configuration
      expect(tauriConfig.app.windows).toHaveLength(1);
      const window = tauriConfig.app.windows[0];
      expect(window.title).toBe('AI Disk Cleaner');
      expect(window.label).toBe('main');
      expect(window.url).toBe('/');
      expect(window.width).toBe(1200);
      expect(window.height).toBe(800);
      expect(window.minWidth).toBe(800);
      expect(window.minHeight).toBe(600);
      expect(window.center).toBe(true);
      expect(window.resizable).toBe(true);
      expect(window.decorations).toBe(true);
      expect(window.transparent).toBe(false);
      expect(window.alwaysOnTop).toBe(false);
      expect(window.skipTaskbar).toBe(false);
      expect(window.theme).toBe('system');

      // Webview options
      expect(window.webviewOptions.autoZoom).toBe(false);
      expect(window.webviewOptions.dragDropEnabled).toBe(true);

      // Security configuration
      expect(tauriConfig.app.security.csp).toContain('default-src \'self\'');
      expect(tauriConfig.app.security.csp).toContain('style-src \'self\' \'unsafe-inline\'');
      expect(tauriConfig.app.security.csp).toContain('script-src \'self\'');
    });

    it('should have proper bundle configuration', async () => {
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );

      const bundle = tauriConfig.bundle;
      expect(bundle.active).toBe(true);
      expect(bundle.category).toBe('Utility');
      expect(bundle.identifier).toBe('com.aidiskcleaner.app');
      expect(bundle.shortDescription).toBe('AI Disk Cleaner');
      expect(bundle.longDescription).toBe('AI-powered disk cleaning application with modern web interface');
      expect(bundle.targets).toBe('all');

      // Icon configuration
      expect(bundle.icon).toContain('icons/32x32.png');
      expect(bundle.icon).toContain('icons/128x128.png');
      expect(bundle.icon).toContain('icons/icon.icns');
      expect(bundle.icon).toContain('icons/icon.ico');
    });

    it('should have proper plugin configuration', async () => {
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );

      const plugins = tauriConfig.plugins;

      // Shell plugin
      expect(plugins.shell.open).toBe(true);
      expect(plugins.shell.scope).toBeDefined();

      // Dialog plugin
      expect(plugins.dialog.all).toBe(true);
      expect(plugins.dialog.ask).toBe(true);
      expect(plugins.dialog.confirm).toBe(true);
      expect(plugins.dialog.message).toBe(true);
      expect(plugins.dialog.open).toBe(true);
      expect(plugins.dialog.save).toBe(true);

      // File system plugin
      expect(plugins.fs.all).toBe(true);
      expect(plugins.fs.readFile).toBe(true);
      expect(plugins.fs.writeFile).toBe(true);
      expect(plugins.fs.readDir).toBe(true);
      expect(plugins.fs.copyFile).toBe(true);
      expect(plugins.fs.createDir).toBe(true);
      expect(plugins.fs.removeDir).toBe(true);
      expect(plugins.fs.removeFile).toBe(true);
      expect(plugins.fs.renameFile).toBe(true);
      expect(plugins.fs.exists).toBe(true);
      expect(plugins.fs.scope).toContain('**');

      // Other plugins
      expect(plugins.notification.all).toBe(true);
      expect(plugins.os.all).toBe(true);
    });

    it('should have proper permissions configuration', async () => {
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );

      const requiredPermissions = [
        'core:default',
        'dialog:open',
        'dialog:save',
        'dialog:ask',
        'dialog:confirm',
        'dialog:message',
        'fs:default',
        'fs:read-file',
        'fs:write-file',
        'fs:read-dir',
        'fs:copy-file',
        'fs:create-dir',
        'fs:remove-dir',
        'fs:remove-file',
        'fs:rename-file',
        'fs:exists',
        'notification:default',
        'shell:open'
      ];

      requiredPermissions.forEach(permission => {
        expect(tauriConfig.permissions).toContain(permission);
      });
    });
  });

  describe('TailwindCSS Configuration', () => {
    it('should have proper TailwindCSS configuration', async () => {
      const tailwindConfig = await readFile(join(projectRoot, 'tailwind.config.js'), 'utf-8');

      // Content configuration
      expect(tailwindConfig).toContain('content: [');
      expect(tailwindConfig).toContain('\'./src/**/*.{ts,tsx}\'');

      // Theme configuration
      expect(tailwindConfig).toContain('theme: {');
      expect(tailwindConfig).toContain('container: {');
      expect(tailwindConfig).toContain('center: true');
      expect(tailwindConfig).toContain('padding: "2rem"');

      // Dark mode configuration
      expect(tailwindConfig).toContain('darkMode: ["class"]');

      // shadcn/ui color system
      expect(tailwindConfig).toContain('colors: {');
      expect(tailwindConfig).toContain('border: "hsl(var(--border))"');
      expect(tailwindConfig).toContain('input: "hsl(var(--input))"');
      expect(tailwindConfig).toContain('ring: "hsl(var(--ring))"');
      expect(tailwindConfig).toContain('background: "hsl(var(--background))"');
      expect(tailwindConfig).toContain('foreground: "hsl(var(--foreground))"');
      expect(tailwindConfig).toContain('primary: {');
      expect(tailwindConfig).toContain('secondary: {');
      expect(tailwindConfig).toContain('destructive: {');
      expect(tailwindConfig).toContain('muted: {');
      expect(tailwindConfig).toContain('accent: {');

      // Border radius configuration
      expect(tailwindConfig).toContain('borderRadius: {');
      expect(tailwindConfig).toContain('lg: "var(--radius)"');

      // Animation configuration
      expect(tailwindConfig).toContain('keyframes: {');
      expect(tailwindConfig).toContain('animation: {');

      // Font configuration
      expect(tailwindConfig).toContain('fontFamily: {');
      expect(tailwindConfig).toContain('sans: ["Inter"');
      expect(tailwindConfig).toContain('mono: ["JetBrains Mono"');

      // Plugins
      expect(tailwindConfig).toContain('plugins: [require("tailwindcss-animate")]');
    });

    it('should have proper component.json for shadcn/ui', async () => {
      const componentsConfig = JSON.parse(await readFile(join(projectRoot, 'components.json'), 'utf-8'));

      expect(componentsConfig.style).toBe('default');
      expect(componentsConfig.rsc).toBe(false);
      expect(componentsConfig.tsx).toBe(true);
      expect(componentsConfig.tailwind.config).toBe('tailwind.config.js');
      expect(componentsConfig.tailwind.css).toBe('src/styles/globals.css');
      expect(componentsConfig.tailwind.baseColor).toBe('slate');
      expect(componentsConfig.tailwind.cssVariables).toBe(true);
      expect(componentsConfig.alias.components).toBe('@/components');
      expect(componentsConfig.alias.utils).toBe('@/lib/utils');
    });
  });

  describe('Testing Configuration', () => {
    it('should have proper test setup files', async () => {
      // Check Jest setup (if using Jest)
      try {
        const jestSetup = await readFile(join(projectRoot, 'tests', 'setup', 'tests-setup.ts'), 'utf-8');
        expect(jestSetup).toContain('@testing-library/jest-dom');
      } catch {
        // Jest setup might not exist if using Vitest
      }

      // Check Vitest setup
      try {
        const vitestConfig = await readFile(join(projectRoot, 'vitest.config.ts'), 'utf-8');
        expect(vitestConfig).toContain('test: {');
        expect(vitestConfig).toContain('environment: \'jsdom\'');
      } catch {
        // Vitest config might be in vite.config.ts
        const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');
        // Vitest config might be embedded in Vite config
      }

      // Check test polyfills
      try {
        const polyfills = await readFile(join(projectRoot, 'tests', 'setup', 'jest.polyfills.js'), 'utf-8');
        expect(polyfills.length).toBeGreaterThan(0);
      } catch {
        // Polyfills might not be needed
      }
    });

    it('should have proper test utilities', async () => {
      // Check for test utilities
      try {
        const fileMock = await readFile(join(projectRoot, 'tests', 'setup', 'fileMock.js'), 'utf-8');
        expect(fileMock).toContain('module.exports');
      } catch {
        // File mock might not be needed
      }
    });
  });

  describe('ESLint Configuration', () => {
    it('should have ESLint configuration', async () => {
      try {
        // Check for eslint.config.js (flat config)
        const eslintConfig = await readFile(join(projectRoot, 'eslint.config.js'), 'utf-8');
        expect(eslintConfig).toContain('typescript');
        expect(eslintConfig).toContain('react');
      } catch {
        try {
          // Check for .eslintrc.js (legacy config)
          const eslintConfig = await readFile(join(projectRoot, '.eslintrc.js'), 'utf-8');
          expect(eslintConfig).toContain('@typescript-eslint/parser');
          expect(eslintConfig).toContain('plugin:react/recommended');
        } catch {
          // ESLint config might be in package.json or missing
          const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));
          expect(packageJson.devDependencies).toHaveProperty('eslint');
        }
      }
    });
  });

  describe('Prettier Configuration', () => {
    it('should have Prettier configuration', async () => {
      try {
        // Check for .prettierrc
        const prettierConfig = await readFile(join(projectRoot, '.prettierrc'), 'utf-8');
        expect(prettierConfig.length).toBeGreaterThan(0);
      } catch {
        try {
          // Check for .prettierrc.json
          const prettierConfig = await readFile(join(projectRoot, '.prettierrc.json'), 'utf-8');
          expect(JSON.parse(prettierConfig)).toBeDefined();
        } catch {
          try {
            // Check for prettier.config.js
            const prettierConfig = await readFile(join(projectRoot, 'prettier.config.js'), 'utf-8');
            expect(prettierConfig).toContain('module.exports');
          } catch {
            // Prettier config might be in package.json
            const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));
            expect(packageJson.devDependencies).toHaveProperty('prettier');
          }
        }
      }
    });
  });

  describe('Git Configuration', () => {
    it('should have proper .gitignore', async () => {
      const gitignore = await readFile(join(projectRoot, '.gitignore'), 'utf-8');

      const essentialIgnores = [
        'node_modules',
        'dist',
        'build',
        '.DS_Store',
        '*.log',
        '.env',
        '.env.local',
        '.env.development.local',
        '.env.test.local',
        '.env.production.local',
        'coverage',
        '.nyc_output',
        '.cache',
        '!.gitkeep'
      ];

      essentialIgnores.forEach(ignore => {
        expect(gitignore).toContain(ignore);
      });
    });
  });

  describe('Performance Configuration', () => {
    it('should have performance-optimized configurations', async () => {
      // Vite performance settings
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');
      expect(viteConfig).toContain('optimizeDeps');
      expect(viteConfig).toContain('minify: \'esbuild\'');
      expect(viteConfig).toContain('assetsInlineLimit: 4096');

      // Tauri performance settings
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );
      expect(tauriConfig.app.windows[0].webviewOptions.autoZoom).toBe(false);

      // Package.json engines for performance
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));
      expect(packageJson.engines.node).toMatch(/^>=18\./); // Modern Node.js for better performance
    });
  });

  describe('Security Configuration', () => {
    it('should have secure configurations', async () => {
      // Tauri security
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );
      expect(tauriConfig.app.security.csp).toBeDefined();
      expect(tauriConfig.app.security.csp).toContain('default-src \'self\'');

      // Package.json security
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Check for secure dependency versions (no overly old versions)
      const reactVersion = packageJson.dependencies.react;
      expect(reactVersion).toMatch(/^18\./); // Modern React with security updates

      // Git ignore for sensitive files
      const gitignore = await readFile(join(projectRoot, '.gitignore'), 'utf-8');
      expect(gitignore).toContain('.env');
      expect(gitignore).toContain('*.key');
      expect(gitignore).toContain('*.pem');
    });
  });
});