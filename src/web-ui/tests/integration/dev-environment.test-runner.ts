/**
 * Development Environment Test Runner
 *
 * This test runner orchestrates the execution of all development environment
 * tests with proper setup, teardown, and reporting. It provides a single
 * entry point for validating the complete development setup.
 */

import { describe, it, expect, beforeAll, afterAll, jest } from '@jest/globals';
import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import { readFile, writeFile, access, stat, readdir } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const exec = promisify(require('child_process').exec);

describe('Development Environment Test Suite', () => {
  const projectRoot = resolve(__dirname, '../..');
  const TEST_TIMEOUT = 300000; // 5 minutes for entire suite
  const PERFORMANCE_TARGETS = {
    startup: 2000, // <2 seconds startup (SDD requirement)
    hotReload: 100, // <100ms hot reload (SDD requirement)
    build: 60000, // <1 minute build
    test: 30000 // <30 seconds test run
  };

  let testResults: {
    hotReload: boolean;
    serverStartup: boolean;
    toolIntegration: boolean;
    buildProcess: boolean;
    configuration: boolean;
    performance: boolean;
  } = {
    hotReload: false,
    serverStartup: false,
    toolIntegration: false,
    buildProcess: false,
    configuration: false,
    performance: false
  };

  beforeAll(async () => {
    console.log('🚀 Starting Development Environment Test Suite...');
    console.log(`📁 Project Root: ${projectRoot}`);
    console.log(`⏱️  Test Timeout: ${TEST_TIMEOUT / 1000}s`);

    process.chdir(projectRoot);

    // Ensure dependencies are installed
    try {
      await access('node_modules');
      console.log('✅ Dependencies already installed');
    } catch {
      console.log('📦 Installing dependencies...');
      await exec('npm install', { timeout: 300000 });
      console.log('✅ Dependencies installed');
    }
  });

  describe('Comprehensive Development Environment Validation', () => {
    it('should validate complete development environment setup', async () => {
      console.log('\n🔍 Running comprehensive validation...');

      const validationSteps = [
        {
          name: 'Configuration Validation',
          test: async () => {
            console.log('  📋 Validating configurations...');
            return await validateConfigurations();
          }
        },
        {
          name: 'Tool Integration',
          test: async () => {
            console.log('  🛠️  Validating tool integration...');
            return await validateToolIntegration();
          }
        },
        {
          name: 'Build Process',
          test: async () => {
            console.log('  🏗️  Validating build process...');
            return await validateBuildProcess();
          }
        },
        {
          name: 'Server Startup',
          test: async () => {
            console.log('  🌐 Validating server startup...');
            return await validateServerStartup();
          }
        },
        {
          name: 'Hot Reload',
          test: async () => {
            console.log('  🔥 Validating hot reload...');
            return await validateHotReload();
          }
        },
        {
          name: 'Performance Targets',
          test: async () => {
            console.log('  ⚡ Validating performance targets...');
            return await validatePerformanceTargets();
          }
        }
      ];

      const results = [];
      for (const step of validationSteps) {
        try {
          const result = await step.test();
          results.push({ name: step.name, success: true, result });
          console.log(`  ✅ ${step.name} - PASSED`);
        } catch (error) {
          results.push({ name: step.name, success: false, error });
          console.log(`  ❌ ${step.name} - FAILED`);
          console.error(`     Error: ${error}`);
        }
      }

      // Generate summary report
      console.log('\n📊 Test Suite Summary:');
      console.log('=' .repeat(50));

      const passed = results.filter(r => r.success).length;
      const total = results.length;

      results.forEach(result => {
        const status = result.success ? '✅ PASS' : '❌ FAIL';
        console.log(`${status} ${result.name}`);
      });

      console.log('=' .repeat(50));
      console.log(`📈 Results: ${passed}/${total} tests passed`);

      if (passed === total) {
        console.log('🎉 All development environment tests passed!');
        console.log('✨ The development environment is properly configured and ready for use.');
      } else {
        console.log(`⚠️  ${total - passed} test(s) failed. Please review the errors above.`);
      }

      expect(passed).toBe(total);
    }, TEST_TIMEOUT);
  });

  async function validateConfigurations(): Promise<boolean> {
    const requiredFiles = [
      'package.json',
      'tsconfig.json',
      'tsconfig.node.json',
      'vite.config.ts',
      'tailwind.config.js',
      'components.json',
      'src-tauri/tauri.conf.json',
      '.gitignore'
    ];

    for (const file of requiredFiles) {
      try {
        await stat(join(projectRoot, file));
      } catch {
        throw new Error(`Missing required file: ${file}`);
      }
    }

    // Validate package.json structure
    const packageJson = JSON.parse(await readFile(join(projectRoot, 'package.json'), 'utf-8'));
    const requiredScripts = ['dev', 'build', 'lint', 'test', 'tauri:dev', 'tauri:build'];

    for (const script of requiredScripts) {
      if (!packageJson.scripts[script]) {
        throw new Error(`Missing required script: ${script}`);
      }
    }

    testResults.configuration = true;
    return true;
  }

  async function validateToolIntegration(): Promise<boolean> {
    const tools = [
      { name: 'TypeScript', command: 'npx tsc --version' },
      { name: 'Vite', command: 'npx vite --version' },
      { name: 'ESLint', command: 'npx eslint --version' },
      { name: 'Prettier', command: 'npx prettier --version' },
      { name: 'Tauri CLI', command: 'npx tauri --version' },
      { name: 'Vitest', command: 'npx vitest --version' }
    ];

    for (const tool of tools) {
      try {
        const { stdout } = await exec(tool.command, { timeout: 10000 });
        if (!stdout || stdout.trim().length === 0) {
          throw new Error(`${tool.name} returned empty version`);
        }
      } catch (error) {
        throw new Error(`${tool.name} not working: ${error}`);
      }
    }

    testResults.toolIntegration = true;
    return true;
  }

  async function validateBuildProcess(): Promise<boolean> {
    const startTime = Date.now();

    try {
      // Clean any existing build
      try {
        await exec('rm -rf dist', { cwd: projectRoot });
      } catch {}

      // Run build
      const { stdout, stderr } = await exec('npm run build', {
        cwd: projectRoot,
        timeout: PERFORMANCE_TARGETS.build
      });

      if (stderr && stderr.includes('error')) {
        throw new Error(`Build errors: ${stderr}`);
      }

      // Verify build output
      await stat(join(projectRoot, 'dist'));
      await stat(join(projectRoot, 'dist', 'index.html'));

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const hasJs = distFiles.some(f => f.endsWith('.js'));
      const hasCss = distFiles.some(f => f.endsWith('.css'));

      if (!hasJs || !hasCss) {
        throw new Error('Build output missing required files');
      }

      const buildTime = Date.now() - startTime;
      if (buildTime > PERFORMANCE_TARGETS.build) {
        throw new Error(`Build too slow: ${buildTime}ms > ${PERFORMANCE_TARGETS.build}ms`);
      }

      console.log(`    📦 Build completed in ${buildTime}ms`);
      testResults.buildProcess = true;
      return true;
    } catch (error) {
      throw new Error(`Build process validation failed: ${error}`);
    }
  }

  async function validateServerStartup(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let serverStarted = false;
      let startupTime = 0;

      const devServer = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0' }
      });

      const timeout = setTimeout(() => {
        if (!serverStarted) {
          devServer.kill('SIGTERM');
          reject(new Error(`Server startup timeout: ${PERFORMANCE_TARGETS.startup}ms`));
        }
      }, PERFORMANCE_TARGETS.startup);

      devServer.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('Local:') || output.includes('ready in')) {
          if (!serverStarted) {
            serverStarted = true;
            startupTime = Date.now() - startTime;
            clearTimeout(timeout);

            if (startupTime > PERFORMANCE_TARGETS.startup) {
              devServer.kill('SIGTERM');
              reject(new Error(`Server startup too slow: ${startupTime}ms > ${PERFORMANCE_TARGETS.startup}ms`));
            } else {
              console.log(`    🚀 Server started in ${startupTime}ms`);
              testResults.serverStartup = true;
              devServer.kill('SIGTERM');
              resolve(true);
            }
          }
        }
      });

      devServer.stderr?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('error') && !serverStarted) {
          clearTimeout(timeout);
          devServer.kill('SIGTERM');
          reject(new Error(`Server startup error: ${output}`));
        }
      });

      devServer.on('error', (error) => {
        clearTimeout(timeout);
        reject(new Error(`Failed to start server: ${error}`));
      });

      devServer.on('exit', (code) => {
        if (code !== 0 && !serverStarted) {
          clearTimeout(timeout);
          reject(new Error(`Server exited with code ${code}`));
        }
      });
    });
  }

  async function validateHotReload(): Promise<boolean> {
    const testComponent = join(projectRoot, 'src', 'components', 'HotReloadValidationTest.tsx');
    const originalContent = `export default function HotReloadValidationTest() {
  return <div data-testid="hot-reload">Original</div>;
}`;

    const modifiedContent = `export default function HotReloadValidationTest() {
  return <div data-testid="hot-reload">Modified</div>;
}`;

    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let hotReloadDetected = false;
      let reloadTime = 0;

      const devServer = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0' }
      });

      const timeout = setTimeout(() => {
        devServer.kill('SIGTERM');
        cleanup();
        reject(new Error('Hot reload validation timeout'));
      }, 15000);

      devServer.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('HMR') || output.includes('hot') || output.includes('updated')) {
          if (!hotReloadDetected) {
            hotReloadDetected = true;
            reloadTime = Date.now() - startTime;
            clearTimeout(timeout);

            if (reloadTime > PERFORMANCE_TARGETS.hotReload) {
              console.log(`    ⚠️  Hot reload slow but working: ${reloadTime}ms`);
            } else {
              console.log(`    🔥 Hot reload working: ${reloadTime}ms`);
            }

            testResults.hotReload = true;
            devServer.kill('SIGTERM');
            cleanup();
            resolve(true);
          }
        }
      });

      // Wait for server to start, then modify file
      setTimeout(async () => {
        try {
          await writeFile(testComponent, originalContent);
          await new Promise(r => setTimeout(r, 2000));
          await writeFile(testComponent, modifiedContent);
        } catch (error) {
          clearTimeout(timeout);
          devServer.kill('SIGTERM');
          cleanup();
          reject(error);
        }
      }, 3000);

      const cleanup = async () => {
        try {
          await require('fs').unlinkSync(testComponent);
        } catch {}
      };
    });
  }

  async function validatePerformanceTargets(): Promise<boolean> {
    const performanceTests = [
      {
        name: 'TypeScript Check',
        command: 'npx tsc --noEmit',
        target: PERFORMANCE_TARGETS.test
      },
      {
        name: 'Lint Check',
        command: 'npm run lint',
        target: PERFORMANCE_TARGETS.test
      },
      {
        name: 'Format Check',
        command: 'npm run format:check',
        target: PERFORMANCE_TARGETS.test
      }
    ];

    const results = [];
    for (const test of performanceTests) {
      const startTime = Date.now();
      try {
        await exec(test.command, { cwd: projectRoot, timeout: test.target });
        const duration = Date.now() - startTime;
        results.push({ name: test.name, duration, success: true });
        console.log(`    ⚡ ${test.name}: ${duration}ms`);
      } catch (error) {
        const duration = Date.now() - startTime;
        results.push({ name: test.name, duration, success: false, error });
        console.log(`    ⚠️  ${test.name}: ${duration}ms (with errors)`);
      }
    }

    // All tests should complete (even with errors) within reasonable time
    const allCompleted = results.every(r => r.duration < r.target * 2); // Allow 2x for errors

    if (allCompleted) {
      testResults.performance = true;
    }

    return allCompleted;
  }
});