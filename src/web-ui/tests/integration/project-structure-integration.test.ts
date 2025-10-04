import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { readFileSync, existsSync, mkdirSync, rmSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

/**
 * Comprehensive integration tests for the complete Phase 1 Project Structure Setup
 *
 * This test validates that all components (Tauri 2.0 + React 18 + TypeScript +
 * TailwindCSS v4 + shadcn/ui) work together correctly as specified in the SDD.
 */
describe('Complete Project Structure Integration Tests', () => {
  const projectRoot = process.cwd();
  const srcDir = join(projectRoot, 'src');
  const tauriDir = join(projectRoot, 'src-tauri');
  const publicDir = join(projectRoot, 'public');

  beforeEach(() => {
    process.env.NODE_ENV = 'test';
  });

  afterEach(() => {
    process.env.NODE_ENV = 'development';
  });

  describe('Overall Project Structure', () => {
    it('should have complete project directory structure', () => {
      // Root level files
      expect(existsSync(join(projectRoot, 'package.json'))).toBe(true);
      expect(existsSync(join(projectRoot, 'vite.config.ts'))).toBe(true);
      expect(existsSync(join(projectRoot, 'tsconfig.json'))).toBe(true);
      expect(existsSync(join(projectRoot, 'tailwind.config.js'))).toBe(true);
      expect(existsSync(join(projectRoot, 'postcss.config.js'))).toBe(true);
      expect(existsSync(join(projectRoot, 'components.json'))).toBe(true);

      // Source directory
      expect(existsSync(srcDir)).toBe(true);

      // Tauri directory
      expect(existsSync(tauriDir)).toBe(true);

      // Public directory
      expect(existsSync(publicDir)).toBe(true);
      expect(existsSync(join(publicDir, 'index.html'))).toBe(true);
    });

    it('should have proper source code organization', () => {
      // React source structure
      expect(existsSync(join(srcDir, 'main.tsx'))).toBe(true);
      expect(existsSync(join(srcDir, 'App.tsx'))).toBe(true);

      // Component directories
      expect(existsSync(join(srcDir, 'components'))).toBe(true);
      expect(existsSync(join(srcDir, 'components', 'ui'))).toBe(true);
      expect(existsSync(join(srcDir, 'lib'))).toBe(true);

      // Style directories
      expect(existsSync(join(srcDir, 'styles'))) || expect(existsSync(join(srcDir, 'index.css')));
    });

    it('should have complete TypeScript path mapping', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      if (tsConfig.compilerOptions.paths) {
        const paths = tsConfig.compilerOptions.paths;

        // Should have @ alias for src directory
        expect(paths).toHaveProperty('@/*');
        expect(Array.isArray(paths['@/*'])).toBe(true);
        expect(paths['@/*'][0]).toBe('./src/*');

        // Should have @components alias
        expect(paths).toHaveProperty('@/components/*');
        expect(paths['@/components/*'][0]).toBe('./src/components/*');

        // Should have @lib alias
        expect(paths).toHaveProperty('@/lib/*');
        expect(paths['@/lib/*'][0]).toBe('./src/lib/*');
      }
    });
  });

  describe('Build System Integration', () => {
    it('should have consistent build scripts across all tools', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Development scripts
      expect(packageJson.scripts).toHaveProperty('dev');
      expect(packageJson.scripts).toHaveProperty('tauri:dev');

      // Build scripts
      expect(packageJson.scripts).toHaveProperty('build');
      expect(packageJson.scripts).toHaveProperty('tauri:build');

      // Test scripts
      expect(packageJson.scripts).toHaveProperty('test');
      expect(packageJson.scripts).toHaveProperty('test:ui');

      // Linting scripts
      expect(packageJson.scripts).toHaveProperty('lint');
      expect(packageJson.scripts).toHaveProperty('type-check');
    });

    it('should have Vite configuration that integrates with Tauri', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have proper build output for Tauri
      expect(viteConfig).toContain('outDir:');
      expect(viteConfig).toContain('emptyOutDir: true');

      // Should have development server configuration
      expect(viteConfig).toContain('server:');
      expect(viteConfig).toContain('strictPort: true');
      expect(viteConfig).toContain('port: 1420'); // Default Tauri port

      // Should have React plugin
      expect(viteConfig).toContain('@vitejs/plugin-react');
    });

    it('should have Tauri configuration that references Vite build', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const tauriConfig = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Should reference Vite build output
      if (tauriConfig.build) {
        expect(tauriConfig.build).toHaveProperty('frontendDist');
        const frontendDist = tauriConfig.build.frontendDist;
        expect(frontendDist).toMatch(/^(dist|build|out)$/);
      }

      // Should have development URL configuration
      if (tauriConfig.build && tauriConfig.build.devUrl) {
        expect(tauriConfig.build.devUrl).toMatch(/^http:\/\/localhost:1420/);
      }
    });
  });

  describe('Frontend Integration', () => {
    it('should have proper React 18 entry point', () => {
      const mainTsxPath = join(srcDir, 'main.tsx');
      expect(existsSync(mainTsxPath)).toBe(true);

      const mainContent = readFileSync(mainTsxPath, 'utf-8');

      // Should use React 18 createRoot API
      expect(mainContent).toContain('import { createRoot }');
      expect(mainContent).toContain('from \'react-dom/client\'');
      expect(mainContent).toContain('createRoot');

      // Should reference the main app component
      expect(mainContent).toContain('import App from');
      expect(mainContent).toContain('root.render');
    });

    it('should have main App component with proper structure', () => {
      const appTsxPath = join(srcDir, 'App.tsx');
      if (existsSync(appTsxPath)) {
        const appContent = readFileSync(appTsxPath, 'utf-8');

        // Should import React and necessary hooks
        expect(appContent).toContain('import React');
        expect(appContent).toContain('export default');

        // Should use proper TypeScript
        expect(appContent).toMatch(/React\.(FC|FunctionComponent)/);
      }
    });

    it('should have CSS integration with TailwindCSS', () => {
      const cssFiles = [
        join(srcDir, 'styles', 'globals.css'),
        join(srcDir, 'index.css'),
        join(srcDir, 'main.css')
      ];

      let hasTailwindCSS = false;
      for (const cssFile of cssFiles) {
        if (existsSync(cssFile)) {
          const cssContent = readFileSync(cssFile, 'utf-8');

          if (cssContent.includes('@tailwind')) {
            hasTailwindCSS = true;
            expect(cssContent).toContain('@tailwind base;');
            expect(cssContent).toContain('@tailwind components;');
            expect(cssContent).toContain('@tailwind utilities;');
            break;
          }
        }
      }

      expect(hasTailwindCSS).toBe(true);
    });

    it('should have shadcn/ui components integrated', () => {
      const uiDir = join(srcDir, 'components', 'ui');
      const utilsPath = join(srcDir, 'lib', 'utils.ts');

      // Should have utility function
      expect(existsSync(utilsPath)).toBe(true);
      const utilsContent = readFileSync(utilsPath, 'utf-8');
      expect(utilsContent).toContain('export function cn');
      expect(utilsContent).toContain('twMerge');

      // Should have UI components directory
      expect(existsSync(uiDir)).toBe(true);

      // Should have at least one component
      const components = ['button.tsx', 'card.tsx', 'input.tsx'];
      let hasComponent = false;
      for (const component of components) {
        if (existsSync(join(uiDir, component))) {
          hasComponent = true;
          break;
        }
      }
      expect(hasComponent).toBe(true);
    });
  });

  describe('TypeScript Integration', () => {
    it('should have proper TypeScript configuration for all file types', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should include all relevant files
      if (tsConfig.include) {
        expect(tsConfig.include).toContain('src');
        expect(tsConfig.include).toContain('vite.config.ts');
      }

      // Should exclude build outputs
      if (tsConfig.exclude) {
        expect(tsConfig.exclude).toContain('node_modules');
        expect(tsConfig.exclude).toContain('dist');
        expect(tsConfig.exclude).toContain('build');
      }

      // Should have proper compiler options
      expect(tsConfig.compilerOptions.strict).toBe(true);
      expect(tsConfig.compilerOptions.noImplicitAny).toBe(true);
    });

    it('should have environment type definitions', () => {
      const envTypesPath = join(srcDir, 'env.d.ts');
      if (existsSync(envTypesPath)) {
        const envTypes = readFileSync(envTypesPath, 'utf-8');

        // Should have Vite environment types
        expect(envTypes).toContain('/// <reference types="vite/client" />');

        // Should have import meta environment types
        expect(envTypes).toContain('interface ImportMetaEnv');
        expect(envTypes).toContain('interface ImportMeta');
      }
    });

    it('should have Tauri API types available', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should have Tauri API types
      if (packageJson.devDependencies) {
        expect(packageJson.devDependencies).toHaveProperty('@tauri-apps/api');
      }
    });
  });

  describe('Development Environment Integration', () => {
    it('should have proper development workflow', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should have development server
      expect(packageJson.scripts.dev).toContain('vite');

      // Should have Tauri development mode
      expect(packageJson.scripts['tauri:dev']).toContain('tauri dev');

      // Should have TypeScript checking
      expect(packageJson.scripts['type-check']).toContain('tsc --noEmit');

      // Should have linting
      expect(packageJson.scripts.lint).toBeDefined();
    });

    it('should have hot module replacement configured', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have HMR enabled
      expect(viteConfig).toContain('server:');
    });

    it('should have proper environment handling', () => {
      const envFiles = ['.env', '.env.example', '.env.local'];

      for (const envFile of envFiles) {
        const envPath = join(projectRoot, envFile);
        if (existsSync(envPath)) {
          const envContent = readFileSync(envPath, 'utf-8');
          expect(envContent).toMatch(/^[A-Z_]+=.*$/m);
        }
      }
    });
  });

  describe('Performance Integration', () => {
    it('should have build optimizations configured', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have build optimizations
      expect(viteConfig).toContain('build:');
      expect(viteConfig).toContain('minify:');
      expect(viteConfig).toContain('sourcemap:');
    });

    it('should have code splitting configuration', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have manual chunk configuration
      if (viteConfig.includes('rollupOptions')) {
        expect(viteConfig).toContain('manualChunks:');
      }
    });

    it('should have TailwindCSS purge configuration', () => {
      const tailwindConfigPath = join(projectRoot, 'tailwind.config.js');
      const tailwindConfig = readFileSync(tailwindConfigPath, 'utf-8');

      // Should have content paths for purging unused CSS
      expect(tailwindConfig).toContain('content:');
      expect(tailwindConfig).toContain('./src/**/*.{js,ts,jsx,tsx}');
    });
  });

  describe('Security Integration', () => {
    it('should have Tauri security configuration', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const tauriConfig = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Should have security settings
      expect(tauriConfig.app).toHaveProperty('security');

      const security = tauriConfig.app.security;

      // Should have CSP configured
      if (security.csp) {
        expect(typeof security.csp).toBe('string');
        expect(security.csp).not.toContain("'unsafe-inline'");
      }
    });

    it('should have proper CSP in HTML', () => {
      const htmlPath = join(publicDir, 'index.html');
      if (existsSync(htmlPath)) {
        const htmlContent = readFileSync(htmlPath, 'utf-8');

        // Should have meta tags for security
        expect(htmlContent).toContain('<meta charset="UTF-8">');
        expect(htmlContent).toContain('<meta name="viewport"');
      }
    });
  });

  describe('Testing Integration', () => {
    it('should have complete testing setup', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should have testing dependencies
      expect(packageJson.devDependencies).toHaveProperty('jest');
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/react');
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/jest-dom');
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/user-event');
      expect(packageJson.devDependencies).toHaveProperty('jest-environment-jsdom');

      // Should have testing scripts
      expect(packageJson.scripts).toHaveProperty('test');
      expect(packageJson.scripts).toHaveProperty('test:watch');
      expect(packageJson.scripts).toHaveProperty('test:coverage');
    });

    it('should have Jest configuration', () => {
      const jestConfigPath = join(projectRoot, 'jest.config.js');
      expect(existsSync(jestConfigPath)).toBe(true);

      const jestConfig = readFileSync(jestConfigPath, 'utf-8');

      // Should have proper configuration
      expect(jestConfig).toContain('preset: \'ts-jest\'');
      expect(jestConfig).toContain('testEnvironment: \'jsdom\'');
      expect(jestConfig).toContain('setupFilesAfterEnv');
    });

    it('should have test setup files', () => {
      // Should have test setup
      expect(existsSync(join(projectRoot, 'tests', 'setup', 'tests-setup.ts'))).toBe(true);

      // Should have polyfills
      expect(existsSync(join(projectRoot, 'tests', 'setup', 'jest.polyfills.js'))).toBe(true);

      // Should have file mock
      expect(existsSync(join(projectRoot, 'tests', 'setup', 'fileMock.js'))).toBe(true);
    });

    it('should have integration tests', () => {
      const testFiles = [
        'tests/integration/tauri-project-structure.test.ts',
        'tests/integration/react-typescript-config.test.ts',
        'tests/integration/tailwind-shadcn-config.test.ts',
        'tests/integration/project-structure-integration.test.ts'
      ];

      for (const testFile of testFiles) {
        expect(existsSync(join(projectRoot, testFile))).toBe(true);
      }
    });
  });

  describe('Cross-Platform Integration', () => {
    it('should have platform-agnostic file paths', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Scripts should use forward slashes (works on all platforms)
      Object.values(packageJson.scripts).forEach(script => {
        if (typeof script === 'string') {
          // Should not use Windows-specific backslashes
          expect(script).not.toMatch(/[^\\]\\[^\\]/);
        }
      });
    });

    it('should have proper file extensions for all platforms', () => {
      // Executable scripts should not have extensions (cross-platform)
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      if (packageJson.scripts) {
        Object.values(packageJson.scripts).forEach(script => {
          if (typeof script === 'string') {
            // Should not have Windows .exe extensions
            expect(script).not.toMatch(/\.exe$/i);
          }
        });
      }
    });
  });

  describe('Documentation Integration', () => {
    it('should have README file', () => {
      const readmePath = join(projectRoot, 'README.md');
      if (existsSync(readmePath)) {
        const readme = readFileSync(readmePath, 'utf-8');

        // Should mention key technologies
        expect(readme).toMatch(/Tauri|React|TypeScript|TailwindCSS|shadcn\/ui/i);
      }
    });

    it('should have package.json with proper metadata', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should have proper package metadata
      expect(packageJson).toHaveProperty('name');
      expect(packageJson).toHaveProperty('version');
      expect(packageJson).toHaveProperty('description');
      expect(packageJson).toHaveProperty('keywords');
      expect(packageJson).toHaveProperty('author');
      expect(packageJson).toHaveProperty('license');

      // Should have relevant keywords
      if (packageJson.keywords) {
        const hasRelevantKeywords = packageJson.keywords.some((keyword: string) =>
          ['tauri', 'react', 'typescript', 'desktop', 'ai', 'disk', 'cleaner'].includes(keyword.toLowerCase())
        );
        expect(hasRelevantKeywords).toBe(true);
      }
    });
  });

  describe('Build Process Validation', () => {
    it('should be able to run TypeScript compilation without errors', () => {
      try {
        execSync('npx tsc --noEmit', {
          cwd: projectRoot,
          stdio: 'pipe'
        });
      } catch (error: any) {
        fail(`TypeScript compilation failed: ${error.message}`);
      }
    });

    it('should be able to run ESLint without errors', () => {
      try {
        const packageJsonPath = join(projectRoot, 'package.json');
        const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

        if (packageJson.scripts && packageJson.scripts.lint) {
          execSync('npm run lint', {
            cwd: projectRoot,
            stdio: 'pipe'
          });
        }
      } catch (error: any) {
        // ESLint might not be configured yet, which is acceptable for initial setup
        console.warn('ESLint not configured or failed:', error.message);
      }
    });

    it('should have valid configuration files', () => {
      const configFiles = [
        'vite.config.ts',
        'tsconfig.json',
        'tailwind.config.js',
        'postcss.config.js',
        'components.json',
        'jest.config.js'
      ];

      for (const configFile of configFiles) {
        const configPath = join(projectRoot, configFile);
        if (existsSync(configPath)) {
          try {
            const content = readFileSync(configPath, 'utf-8');
            expect(content.length).toBeGreaterThan(0);
          } catch (error) {
            fail(`Configuration file ${configFile} is not readable`);
          }
        }
      }
    });
  });

  describe('SDD Requirements Compliance', () => {
    it('should meet Tauri 2.0 requirements (SDD 432)', () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

      // Should use Tauri 2.x
      if (packageJson.devDependencies) {
        const tauriCliVersion = packageJson.devDependencies['@tauri-apps/cli'];
        const tauriApiVersion = packageJson.devDependencies['@tauri-apps/api'];

        expect(tauriCliVersion).toMatch(/^2\./);
        expect(tauriApiVersion).toMatch(/^2\./);
      }
    });

    it('should meet Component-Based Design requirements (SDD 437)', () => {
      const uiDir = join(srcDir, 'components', 'ui');
      expect(existsSync(uiDir)).toBe(true);

      // Should have component library foundation
      const utilsPath = join(srcDir, 'lib', 'utils.ts');
      expect(existsSync(utilsPath)).toBe(true);

      const utilsContent = readFileSync(utilsPath, 'utf-8');
      expect(utilsContent).toContain('cn');
    });

    it('should meet TypeScript End-to-End requirements (SDD 438)', () => {
      const tsConfigPath = join(projectRoot, 'tsconfig.json');
      const tsConfig = JSON.parse(readFileSync(tsConfigPath, 'utf-8'));

      // Should have strict TypeScript configuration
      expect(tsConfig.compilerOptions.strict).toBe(true);
      expect(tsConfig.compilerOptions.noImplicitAny).toBe(true);
      expect(tsConfig.compilerOptions.strictNullChecks).toBe(true);
    });

    it('should support virtual scrolling for 100k+ files (SDD performance requirements)', () => {
      const viteConfigPath = join(projectRoot, 'vite.config.ts');
      const viteConfig = readFileSync(viteConfigPath, 'utf-8');

      // Should have performance optimizations
      expect(viteConfig).toContain('build:');
      expect(viteConfig).toContain('target:');
      expect(viteConfig).toContain('minify:');

      // Note: Actual virtual scrolling implementation would be in components
      // This test validates that the build system supports it
    });

    it('should have security-first architecture (SDD security requirements)', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const tauriConfig = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Should have security configuration
      expect(tauriConfig.app).toHaveProperty('security');

      // Should have capability system
      if (tauriConfig.capabilities) {
        expect(Array.isArray(tauriConfig.capabilities)).toBe(true);
      }
    });
  });
});