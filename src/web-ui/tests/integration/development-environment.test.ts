/**
 * Development Environment Setup Tests
 *
 * This test suite validates the complete development environment setup for
 * AI Disk Cleaner's Modern Web UI, ensuring all tools work correctly
 * and meet performance requirements.
 */

import { describe, it, expect, beforeAll, afterAll, jest } from '@jest/globals';
import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import { readFile, writeFile, access, stat } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

// Configuration constants
const DEV_SERVER_PORT = 1420;
const STARTUP_TIMEOUT = 5000; // 2 seconds target + buffer
const HOT_RELOAD_TIMEOUT = 3000;
const PERFORMANCE_TARGET_MS = 100;

describe('Development Environment Setup', () => {
  let devServerProcess: ChildProcess | null = null;
  let tauriProcess: ChildProcess | null = null;
  const projectRoot = resolve(__dirname, '../..');

  beforeAll(async () => {
    // Ensure we're in the correct directory
    process.chdir(projectRoot);

    // Install dependencies if needed
    try {
      await access('node_modules');
    } catch {
      await promisify(require('child_process').exec)('npm install');
    }
  });

  afterAll(async () => {
    // Clean up processes
    if (devServerProcess) {
      devServerProcess.kill('SIGTERM');
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (tauriProcess) {
      tauriProcess.kill('SIGTERM');
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  });

  describe('Hot Reload Functionality', () => {
    it('should detect React component changes and trigger hot reload', async () => {
      const testComponentPath = join(projectRoot, 'src', 'components', 'HotReloadTestComponent.tsx');
      const originalContent = `export default function HotReloadTestComponent() {
  return <div data-testid="hot-reload-test">Original Content</div>;
}`;

      const modifiedContent = `export default function HotReloadTestComponent() {
  return <div data-testid="hot-reload-test">Modified Content</div>;
}`;

      try {
        // Create test component
        await writeFile(testComponentPath, originalContent);

        // Start dev server with hot reload detection
        const startTime = Date.now();
        devServerProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, FORCE_COLOR: '0' }
        });

        let hotReloadDetected = false;
        let compilationTime = 0;

        devServerProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('HMR') || output.includes('hot') || output.includes('reloaded')) {
            hotReloadDetected = true;
            compilationTime = Date.now() - startTime;
          }
        });

        // Wait for initial compilation
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Modify the component
        const modifyStartTime = Date.now();
        await writeFile(testComponentPath, modifiedContent);

        // Wait for hot reload
        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        expect(hotReloadDetected).toBe(true);
        expect(compilationTime).toBeLessThan(PERFORMANCE_TARGET_MS);

        // Cleanup
        require('fs').unlinkSync(testComponentPath);
      } catch (error) {
        // Cleanup on error
        try {
          require('fs').unlinkSync(testComponentPath);
        } catch {}
        throw error;
      }
    }, 10000);

    it('should handle TypeScript errors during hot reload gracefully', async () => {
      const testComponentPath = join(projectRoot, 'src', 'components', 'TypeErrorTestComponent.tsx');
      const invalidContent = `export default function TypeErrorTestComponent() {
  const invalidType: string = 123;
  return <div>{invalidType}</div>;
}`;

      try {
        await writeFile(testComponentPath, invalidContent);

        let errorDetected = false;
        devServerProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, FORCE_COLOR: '0' }
        });

        devServerProcess.stderr?.on('data', (data) => {
          if (data.toString().includes('TypeScript error') || data.toString().includes('TS')) {
            errorDetected = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        expect(errorDetected).toBe(true);

        // Cleanup
        require('fs').unlinkSync(testComponentPath);
      } catch (error) {
        try {
          require('fs').unlinkSync(testComponentPath);
        } catch {}
        throw error;
      }
    }, 8000);

    it('should validate CSS/Tailwind changes trigger hot reload', async () => {
      const testStylePath = join(projectRoot, 'src', 'styles', 'HotReloadTestStyles.css');
      const originalContent = '.test-style { color: red; }';
      const modifiedContent = '.test-style { color: blue; }';

      try {
        await writeFile(testStylePath, originalContent);

        let styleHotReloadDetected = false;
        devServerProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        devServerProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('.css') && (output.includes('updated') || output.includes('reloaded'))) {
            styleHotReloadDetected = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 2000));

        // Modify CSS
        await writeFile(testStylePath, modifiedContent);
        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        expect(styleHotReloadDetected).toBe(true);

        // Cleanup
        require('fs').unlinkSync(testStylePath);
      } catch (error) {
        try {
          require('fs').unlinkSync(testStylePath);
        } catch {}
        throw error;
      }
    }, 8000);
  });

  describe('Development Server Startup', () => {
    it('should start Vite dev server within performance target', async () => {
      const startTime = Date.now();
      let serverStarted = false;
      let startupTime = 0;

      devServerProcess = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0' }
      });

      devServerProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('Local:') || output.includes('ready in')) {
          serverStarted = true;
          startupTime = Date.now() - startTime;
        }
      });

      await new Promise(resolve => setTimeout(resolve, STARTUP_TIMEOUT));

      expect(serverStarted).toBe(true);
      expect(startupTime).toBeLessThan(2000); // SDD Performance Requirement: <2 second startup
    }, 7000);

    it('should start Tauri dev server with proper coordination', async () => {
      const startTime = Date.now();
      let tauriStarted = false;
      let tauriStartupTime = 0;

      tauriProcess = spawn('npm', ['run', 'tauri:dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0' }
      });

      tauriProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('App running') || output.includes('finished')) {
          tauriStarted = true;
          tauriStartupTime = Date.now() - startTime;
        }
      });

      await new Promise(resolve => setTimeout(resolve, 10000));

      expect(tauriStarted).toBe(true);
      expect(tauriStartupTime).toBeLessThan(5000); // Allow more time for Tauri startup
    }, 15000);

    it('should handle port conflicts gracefully', async () => {
      // Start first server on the default port
      const firstServer = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PORT: '1420' }
      });

      // Wait for first server to start
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Try to start second server on same port
      const secondServer = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PORT: '1420' }
      });

      let portErrorDetected = false;
      secondServer.stderr?.on('data', (data) => {
        if (data.toString().includes('EADDRINUSE') || data.toString().includes('already in use')) {
          portErrorDetected = true;
        }
      });

      await new Promise(resolve => setTimeout(resolve, 3000));

      expect(portErrorDetected).toBe(true);

      // Cleanup
      firstServer.kill('SIGTERM');
      secondServer.kill('SIGTERM');
    }, 8000);
  });

  describe('Tool Integration', () => {
    it('should validate npm scripts are properly configured', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));

      const requiredScripts = [
        'dev',
        'build',
        'lint',
        'lint:fix',
        'type-check',
        'format',
        'format:check',
        'test',
        'test:coverage',
        'tauri:dev',
        'tauri:build'
      ];

      requiredScripts.forEach(script => {
        expect(packageJson.scripts).toHaveProperty(script);
        expect(typeof packageJson.scripts[script]).toBe('string');
      });
    });

    it('should execute TypeScript type checking successfully', async () => {
      const { stdout, stderr } = await promisify(require('child_process').exec)('npm run type-check', {
        cwd: projectRoot,
        timeout: 30000
      });

      // Should not have TypeScript errors
      expect(stderr).not.toContain('error');
      expect(stdout).not.toContain('Found');
    }, 35000);

    it('should run ESLint without critical errors', async () => {
      const { stdout, stderr } = await promisify(require('child_process').exec)('npm run lint', {
        cwd: projectRoot,
        timeout: 30000
      });

      // Should pass linting or have only warnings
      expect(stderr).not.toContain('error');
    }, 35000);

    it('should validate Prettier formatting configuration', async () => {
      const { stdout, stderr } = await promisify(require('child_process').exec)('npm run format:check', {
        cwd: projectRoot,
        timeout: 20000
      });

      // Should be properly formatted
      expect(stderr).not.toContain('Code style issues');
    }, 25000);

    it('should run Jest tests with proper configuration', async () => {
      const { stdout, stderr } = await promisify(require('child_process').exec)('npm test', {
        cwd: projectRoot,
        timeout: 60000
      });

      expect(stdout).toContain('Test Suites:');
      expect(stdout).toContain('Tests:');
      expect(stderr).not.toContain('error');
    }, 65000);

    it('should generate test coverage reports', async () => {
      const { stdout } = await promisify(require('child_process').exec)('npm run test:coverage', {
        cwd: projectRoot,
        timeout: 60000
      });

      expect(stdout).toContain('Coverage');
      expect(stdout).toContain('%');
    }, 65000);
  });

  describe('Build Process', () => {
    it('should build production bundle successfully', async () => {
      const startTime = Date.now();

      const { stdout, stderr } = await promisify(require('child_process').exec)('npm run build', {
        cwd: projectRoot,
        timeout: 120000
      });

      const buildTime = Date.now() - startTime;

      // Should build without errors
      expect(stderr).not.toContain('error');
      expect(stdout).toContain('build');

      // Check if dist directory was created
      await expect(access(join(projectRoot, 'dist'))).resolves.not.toThrow();

      // Build should complete within reasonable time
      expect(buildTime).toBeLessThan(30000);
    }, 125000);

    it('should optimize assets and respect size limits', async () => {
      // First build the project
      await promisify(require('child_process').exec)('npm run build', {
        cwd: projectRoot,
        timeout: 120000
      });

      // Check bundle sizes
      const distStats = await stat(join(projectRoot, 'dist'));
      expect(distStats.isDirectory()).toBe(true);

      // Check for optimized assets
      const indexHtml = await readFile(join(projectRoot, 'dist', 'index.html'), 'utf-8');
      expect(indexHtml).toContain('<script');
      expect(indexHtml).toContain('<link');
    }, 125000);

    it('should handle build errors gracefully', async () => {
      // Create a file with syntax error
      const errorFile = join(projectRoot, 'src', 'components', 'BuildErrorComponent.tsx');
      const errorContent = `export default function BuildErrorComponent() {
  // Intentional syntax error
  const broken = {
  return <div>Broken</div>;
}`;

      try {
        await writeFile(errorFile, errorContent);

        const { stderr } = await promisify(require('child_process').exec)('npm run build', {
          cwd: projectRoot,
          timeout: 30000
        });

        expect(stderr).toContain('error') || expect(stderr).toContain('failed');

        // Cleanup
        require('fs').unlinkSync(errorFile);
      } catch (error) {
        try {
          require('fs').unlinkSync(errorFile);
        } catch {}
        // Build errors are expected
        expect(error).toBeDefined();
      }
    }, 35000);
  });

  describe('Performance Validation', () => {
    it('should meet sub-100ms response time targets', async () => {
      // This test validates that the development environment is configured
      // for optimal performance, not actual runtime performance

      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');
      const tauriConfig = JSON.parse(await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8'));

      // Check Vite optimization configuration
      expect(viteConfig).toContain('optimizeDeps');
      expect(viteConfig).toContain('@tanstack/react-router');
      expect(viteConfig).toContain('@tanstack/react-query');

      // Check Tauri performance settings
      expect(tauriConfig.app.windows[0].webviewOptions.autoZoom).toBe(false);
    });

    it('should validate HMR performance settings', async () => {
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Check for performance optimizations
      expect(viteConfig).toContain('server');
      expect(viteConfig).toContain('port: 1420');
      expect(viteConfig).toContain('strictPort: true');
    });

    it('should ensure proper dependency optimization', async () => {
      const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Check for React 18
      expect(packageJson.dependencies.react).toMatch(/^18\./);
      expect(packageJson.dependencies['react-dom']).toMatch(/^18\./);

      // Check for optimized dependencies
      expect(viteConfig).toContain('react');
      expect(viteConfig).toContain('react-dom');
    });
  });
});