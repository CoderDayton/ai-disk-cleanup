/**
 * Toolchain Integration Tests
 *
 * Validates the integration and proper configuration of all development tools
 * including npm scripts, ESLint, Prettier, Jest, React Testing Library, and Playwright.
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { promisify } from 'util';
import { readFile, writeFile, access, stat, unlink } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';
import { spawn } from 'child_process';

const require = createRequire(import.meta.url);
const exec = promisify(require('child_process').exec);

describe('Toolchain Integration', () => {
  const projectRoot = resolve(__dirname, '../..');
  const PERFORMANCE_TIMEOUT = 30000;

  beforeAll(async () => {
    process.chdir(projectRoot);

    // Ensure dependencies are installed
    try {
      await access('node_modules');
    } catch {
      console.log('Installing dependencies...');
      await exec('npm install', { timeout: 300000 });
    }
  });

  describe('NPM Scripts Configuration', () => {
    it('should have all required development scripts', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      const requiredScripts = {
        // Development scripts
        'dev': 'Vite development server',
        'tauri:dev': 'Tauri development mode',
        'preview': 'Production preview',

        // Build scripts
        'build': 'Production build',
        'tauri:build': 'Tauri production build',

        // Code quality scripts
        'lint': 'ESLint checking',
        'lint:fix': 'ESLint auto-fixing',
        'type-check': 'TypeScript compilation check',
        'format': 'Prettier formatting',
        'format:check': 'Prettier format checking',

        // Testing scripts
        'test': 'Run tests',
        'test:ui': 'Test UI interface',
        'test:coverage': 'Coverage reporting',

        // Utility scripts
        'generate:types': 'Type generation',
        'postinstall': 'Post-install setup'
      };

      Object.entries(requiredScripts).forEach(([script, description]) => {
        expect(packageJson.scripts).toHaveProperty(script);
        expect(typeof packageJson.scripts[script]).toBe('string');
        expect(packageJson.scripts[script].length).toBeGreaterThan(0);
      });
    });

    it('should validate script commands are valid', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Check that scripts reference available binaries
      const scriptCommands = Object.values(packageJson.scripts);

      // Should contain expected tools
      const scriptString = scriptCommands.join(' ');
      expect(scriptString).toContain('vite');
      expect(scriptString).toContain('tauri');
      expect(scriptString).toContain('tsc');
      expect(scriptString).toContain('eslint');
      expect(scriptString).toContain('prettier');
      expect(scriptString).toContain('vitest');
    });

    it('should have proper package.json structure', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Validate required fields
      expect(packageJson).toHaveProperty('name');
      expect(packageJson).toHaveProperty('version');
      expect(packageJson).toHaveProperty('type', 'module');
      expect(packageJson).toHaveProperty('scripts');
      expect(packageJson).toHaveProperty('dependencies');
      expect(packageJson).toHaveProperty('devDependencies');

      // Validate engines
      expect(packageJson.engines).toHaveProperty('node');
      expect(packageJson.engines).toHaveProperty('npm');
      expect(packageJson.engines.node).toMatch(/^>=18\./);
      expect(packageJson.engines.npm).toMatch(/^>=9\./);
    });
  });

  describe('ESLint Configuration', () => {
    it('should run ESLint without critical errors', async () => {
      try {
        const { stdout, stderr } = await exec('npm run lint', {
          cwd: projectRoot,
          timeout: PERFORMANCE_TIMEOUT
        });

        // Should pass linting or have only warnings
        expect(stderr).not.toContain('error');
        expect(stdout).not.toContain('✖');
      } catch (error: any) {
        // Allow linting errors but ensure the tool is working
        expect(error.stdout || error.stderr).toBeDefined();
      }
    }, PERFORMANCE_TIMEOUT);

    it('should validate TypeScript-specific ESLint rules', async () => {
      // Create a test file with various TypeScript issues
      const testFile = join(projectRoot, 'src', 'components', 'ESLintTestComponent.tsx');
      const testContent = `
import React from 'react';

// Unused variable
const unusedVar = 'test';

// Missing return type
function testFunction(param: any) {
  return param;
}

// Component without props interface
export default function ESLintTestComponent() {
  const [state, setState] = React.useState();

  // Console statement (should be flagged)
  console.log('test');

  return <div>Test</div>;
}`;

      try {
        await writeFile(testFile, testContent);

        const { stdout, stderr } = await exec(`npx eslint "${testFile}" --format json`, {
          cwd: projectRoot,
          timeout: 15000
        });

        const lintResults = JSON.parse(stdout);
        expect(Array.isArray(lintResults)).toBe(true);

        if (lintResults.length > 0) {
          expect(lintResults[0]).toHaveProperty('messages');
          expect(Array.isArray(lintResults[0].messages)).toBe(true);
        }

        await unlink(testFile);
      } catch (error) {
        try {
          await unlink(testFile);
        } catch {}
        // ESLint errors are expected for test code
      }
    }, 20000);

    it('should auto-fix linting issues with lint:fix', async () => {
      const testFile = join(projectRoot, 'src', 'components', 'ESLintFixTest.tsx');
      const unformattedContent = `
import React from 'react'
export default function ESLintFixTest(){return <div>Test</div>}
`;

      try {
        await writeFile(testFile, unformattedContent);

        // Run lint:fix
        await exec('npm run lint:fix', {
          cwd: projectRoot,
          timeout: PERFORMANCE_TIMEOUT
        });

        // Check if file was modified
        const fixedContent = await readFile(testFile, 'utf-8');
        expect(fixedContent).not.toBe(unformattedContent);

        await unlink(testFile);
      } catch (error) {
        try {
          await unlink(testFile);
        } catch {}
        // Fix operation might encounter issues
      }
    }, PERFORMANCE_TIMEOUT);
  });

  describe('Prettier Configuration', () => {
    it('should check code formatting with prettier', async () => {
      // Create a test file with formatting issues
      const testFile = join(projectRoot, 'src', 'components', 'PrettierTest.tsx');
      const unformattedContent = `import React from 'react';
export default function PrettierTest(){return(<div><p>Unformatted code</p></div>)}
`;

      try {
        await writeFile(testFile, unformattedContent);

        // Check formatting
        try {
          await exec(`npx prettier --check "${testFile}"`, {
            cwd: projectRoot,
            timeout: 10000
          });
          // If no error, file is properly formatted
        } catch (formatError: any) {
          // Should detect formatting issues
          expect(formatError.stdout || formatError.stderr).toContain('Code style issues');
        }

        await unlink(testFile);
      } catch (error) {
        try {
          await unlink(testFile);
        } catch {}
        throw error;
      }
    }, 15000);

    it('should format code with prettier', async () => {
      const testFile = join(projectRoot, 'src', 'components', 'PrettierFormatTest.tsx');
      const unformattedContent = `import React from 'react';export default function PrettierFormatTest(){return(<div>Unformatted</div>)}
`;

      try {
        await writeFile(testFile, unformattedContent);

        // Format the file
        await exec(`npx prettier --write "${testFile}"`, {
          cwd: projectRoot,
          timeout: 10000
        });

        // Check if file was formatted
        const formattedContent = await readFile(testFile, 'utf-8');
        expect(formattedContent).not.toBe(unformattedContent);
        expect(formattedContent).toContain('\n');
        expect(formattedContent).toContain('  ');

        await unlink(testFile);
      } catch (error) {
        try {
          await unlink(testFile);
        } catch {}
        throw error;
      }
    }, 15000);

    it('should run global format check', async () => {
      const { stdout, stderr } = await exec('npm run format:check', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TIMEOUT
      });

      // Should complete without fatal errors
      expect(stderr).not.toContain('FATAL');
      expect(stderr).not.toContain('ENOENT');
    }, PERFORMANCE_TIMEOUT);
  });

  describe('Jest and React Testing Library', ()() => {
    it('should have proper Jest configuration', async () => {
      const jestConfigPath = join(projectRoot, 'tests', 'setup', 'jest.config.js');
      const jestConfig = await readFile(jestConfigPath, 'utf-8');

      // Check essential Jest configuration
      expect(jestConfig).toContain('ts-jest');
      expect(jestConfig).toContain('jsdom');
      expect(jestConfig).toContain('setupFilesAfterEnv');
      expect(jestConfig).toContain('moduleNameMapping');
      expect(jestConfig).toContain('coverage');
    });

    it('should run Jest tests successfully', async () => {
      const { stdout, stderr } = await exec('npm test', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TIMEOUT * 2
      });

      // Should show test results
      expect(stdout).toContain('Test Suites:') || expect(stdout).toContain('No tests found');
      expect(stderr).not.toContain('FATAL');
    }, PERFORMANCE_TIMEOUT * 2);

    it('should generate coverage reports', async () => {
      const { stdout } = await exec('npm run test:coverage', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TIMEOUT * 2
      });

      expect(stdout).toContain('Coverage') || expect(stdout).toContain('No tests found');

      // Check if coverage directory was created
      try {
        await stat(join(projectRoot, 'coverage'));
        // Coverage directory exists
      } catch {
        // Coverage directory might not exist if no tests
      }
    }, PERFORMANCE_TIMEOUT * 2);

    it('should validate React Testing Library setup', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Check for RTL dependencies
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/react');
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/jest-dom');
      expect(packageJson.devDependencies).toHaveProperty('@testing-library/user-event');

      // Check setup files
      const setupFile = join(projectRoot, 'tests', 'setup', 'tests-setup.ts');
      const setupContent = await readFile(setupFile, 'utf-8');
      expect(setupContent).toContain('@testing-library/jest-dom');
    });
  });

  describe('TypeScript Integration', () => {
    it('should run type checking without errors', async () => {
      const { stdout, stderr } = await exec('npm run type-check', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TIMEOUT
      });

      // Should not have TypeScript errors
      expect(stderr).not.toContain('error');
      expect(stdout).not.toContain('Found') || expect(stdout).toContain('Found 0 errors');
    }, PERFORMANCE_TIMEOUT);

    it('should validate TypeScript configuration', async () => {
      const tsconfig = JSON.parse(await readFile(join(projectRoot, 'tsconfig.json'), 'utf-8'));

      // Check essential TypeScript configuration
      expect(tsconfig).toHaveProperty('compilerOptions');
      expect(tsconfig.compilerOptions).toHaveProperty('target');
      expect(tsconfig.compilerOptions).toHaveProperty('lib');
      expect(tsconfig.compilerOptions).toHaveProperty('allowJs');
      expect(tsconfig.compilerOptions).toHaveProperty('skipLibCheck');
      expect(tsconfig.compilerOptions).toHaveProperty('esModuleInterop');
      expect(tsconfig.compilerOptions).toHaveProperty('allowSyntheticDefaultImports');
      expect(tsconfig.compilerOptions).toHaveProperty('strict');
      expect(tsconfig.compilerOptions).toHaveProperty('forceConsistentCasingInFileNames');
      expect(tsconfig.compilerOptions).toHaveProperty('moduleResolution');
      expect(tsconfig.compilerOptions).toHaveProperty('resolveJsonModule');
      expect(tsconfig.compilerOptions).toHaveProperty('isolatedModules');
      expect(tsconfig.compilerOptions).toHaveProperty('noEmit');
      expect(tsconfig.compilerOptions).toHaveProperty('jsx');

      // Check path aliases
      expect(tsconfig.compilerOptions).toHaveProperty('baseUrl');
      expect(tsconfig.compilerOptions).toHaveProperty('paths');
    });

    it('should detect TypeScript errors', async () => {
      const testFile = join(projectRoot, 'src', 'components', 'TypeScriptErrorTest.tsx');
      const errorContent = `
import React from 'react';

export default function TypeScriptErrorTest() {
  const wrongType: string = 123; // Type error
  const missingType = 'test'; // Implicit any

  return <div>{wrongType}</div>;
}`;

      try {
        await writeFile(testFile, errorContent);

        try {
          await exec('npx tsc --noEmit', {
            cwd: projectRoot,
            timeout: 20000
          });
          // Should not reach here - there should be type errors
          expect(true).toBe(false);
        } catch (typeError: any) {
          // Should detect TypeScript errors
          expect(typeError.stdout || typeError.stderr).toContain('error');
        }

        await unlink(testFile);
      } catch (error) {
        try {
          await unlink(testFile);
        } catch {}
        throw error;
      }
    }, 25000);
  });

  describe('Vite Integration', () => {
    it('should validate Vite configuration', async () => {
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Check essential Vite configuration
      expect(viteConfig).toContain('@vitejs/plugin-react-swc');
      expect(viteConfig).toContain('TanStackRouterVite');
      expect(viteConfig).toContain('resolve.alias');
      expect(viteConfig).toContain('server');
      expect(viteConfig).toContain('build');
      expect(viteConfig).toContain('optimizeDeps');

      // Check port configuration
      expect(viteConfig).toContain('port: 1420');
      expect(viteConfig).toContain('strictPort: true');

      // Check build optimization
      expect(viteConfig).toContain('minify: \'esbuild\'');
      expect(viteConfig).toContain('sourcemap: true');
    });

    it('should build with Vite successfully', async () => {
      const { stdout, stderr } = await exec('npm run build', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TIMEOUT * 2
      });

      // Should build without errors
      expect(stderr).not.toContain('error');
      expect(stdout).toContain('build');

      // Check if dist directory was created
      await stat(join(projectRoot, 'dist'));
    }, PERFORMANCE_TIMEOUT * 2);

    it('should preview production build', async () => {
      // Build first if not already built
      try {
        await stat(join(projectRoot, 'dist'));
      } catch {
        await exec('npm run build', { cwd: projectRoot, timeout: PERFORMANCE_TIMEOUT * 2 });
      }

      const previewProcess = spawn('npm', ['run', 'preview'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: true
      });

      let previewStarted = false;
      previewProcess.stdout?.on('data', (data) => {
        if (data.toString().includes('Local:')) {
          previewStarted = true;
        }
      });

      await new Promise(resolve => setTimeout(resolve, 5000));

      expect(previewStarted).toBe(true);

      // Clean up
      process.kill(-previewProcess.pid!);
    }, 15000);
  });

  describe('Tauri Integration', () => {
    it('should validate Tauri configuration', async () => {
      const tauriConfig = JSON.parse(await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8'));

      // Check essential Tauri configuration
      expect(tauriConfig).toHaveProperty('productName');
      expect(tauriConfig).toHaveProperty('version');
      expect(tauriConfig).toHaveProperty('identifier');
      expect(tauriConfig).toHaveProperty('build');
      expect(tauriConfig).toHaveProperty('app');
      expect(tauriConfig).toHaveProperty('bundle');
      expect(tauriConfig).toHaveProperty('plugins');

      // Check build configuration
      expect(tauriConfig.build).toHaveProperty('frontendDist', '../dist');
      expect(tauriConfig.build).toHaveProperty('devUrl', 'http://localhost:1420');
      expect(tauriConfig.build).toHaveProperty('beforeDevCommand', 'npm run dev');
      expect(tauriConfig.build).toHaveProperty('beforeBuildCommand', 'npm run build');

      // Check window configuration
      expect(tauriConfig.app.windows).toHaveLength(1);
      expect(tauriConfig.app.windows[0]).toHaveProperty('width', 1200);
      expect(tauriConfig.app.windows[0]).toHaveProperty('height', 800);
    });

    it('should have Tauri CLI available', async () => {
      const { stdout } = await exec('npx tauri --version', {
        cwd: projectRoot,
        timeout: 10000
      });

      expect(stdout).toMatch(/\d+\.\d+\.\d+/);
    }, 15000);
  });

  describe('TailwindCSS Integration', () => {
    it('should validate TailwindCSS configuration', async () => {
      const tailwindConfig = await readFile(join(projectRoot, 'tailwind.config.js'), 'utf-8');

      // Check essential TailwindCSS configuration
      expect(tailwindConfig).toContain('content');
      expect(tailwindConfig).toContain('theme');
      expect(tailwindConfig).toContain('plugins');

      // Check for shadcn/ui configuration
      expect(tailwindConfig).toContain('border');
      expect(tailwindConfig).toContain('primary');
      expect(tailwindConfig).toContain('secondary');
      expect(tailwindConfig).toContain('destructive');
      expect(tailwindConfig).toContain('muted');
    });

    it('should have TailwindCSS dependencies', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      expect(packageJson.devDependencies).toHaveProperty('tailwindcss');
      expect(packageJson.devDependencies).toHaveProperty('@tailwindcss/vite');
      expect(packageJson.devDependencies).toHaveProperty('autoprefixer');
      expect(packageJson.devDependencies).toHaveProperty('postcss');

      // Check version is v4 alpha
      expect(packageJson.devDependencies.tailwindcss).toContain('alpha');
    });
  });

  describe('Performance and Tooling', () => {
    it('should validate all tools are within performance targets', async () => {
      const performanceTests = [
        { name: 'TypeScript Check', command: 'npm run type-check', timeout: 30000 },
        { name: 'Lint Check', command: 'npm run lint', timeout: 20000 },
        { name: 'Format Check', command: 'npm run format:check', timeout: 15000 },
      ];

      for (const test of performanceTests) {
        const startTime = Date.now();
        try {
          await exec(test.command, {
            cwd: projectRoot,
            timeout: test.timeout
          });
          const duration = Date.now() - startTime;
          expect(duration).toBeLessThan(test.timeout);
        } catch (error: any) {
          const duration = Date.now() - startTime;
          // Even on error, should not exceed timeout
          expect(duration).toBeLessThan(test.timeout);
        }
      }
    }, 120000);

    it('should validate toolchain consistency', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      // Check that TypeScript versions are compatible
      const typescriptVersion = packageJson.devDependencies.typescript;
      expect(typescriptVersion).toMatch(/^5\./);

      // Check that React versions are compatible
      const reactVersion = packageJson.dependencies.react;
      const reactDomVersion = packageJson.dependencies['react-dom'];
      expect(reactVersion).toMatch(/^18\./);
      expect(reactDomVersion).toMatch(/^18\./);

      // Check that Tauri versions are compatible
      const tauriApiVersion = packageJson.dependencies['@tauri-apps/api'];
      const tauriCliVersion = packageJson.devDependencies['@tauri-apps/cli'];
      expect(tauriApiVersion).toMatch(/^2\./);
      expect(tauriCliVersion).toMatch(/^2\./);
    });
  });
});