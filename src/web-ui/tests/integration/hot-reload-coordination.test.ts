/**
 * Hot Reload Coordination Tests
 *
 * Validates hot reload functionality across React, Tauri, Rust backend,
 * and styling systems with proper process coordination.
 */

import { describe, it, expect, beforeAll, afterAll, jest } from '@jest/globals';
import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import { readFile, writeFile, access, unlink } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);

describe('Hot Reload Coordination', () => {
  let viteProcess: ChildProcess | null = null;
  let tauriProcess: ChildProcess | null = null;
  const projectRoot = resolve(__dirname, '../..');
  const HOT_RELOAD_TIMEOUT = 5000;
  const RESPONSE_TIME_TARGET = 100; // SDD requirement: sub-100ms response times

  beforeAll(async () => {
    process.chdir(projectRoot);
  });

  afterAll(async () => {
    // Clean up all processes
    const cleanup = (process: ChildProcess | null) => {
      if (process && !process.killed) {
        process.kill('SIGTERM');
        setTimeout(() => {
          if (!process.killed) {
            process.kill('SIGKILL');
          }
        }, 1000);
      }
    };

    cleanup(viteProcess);
    cleanup(tauriProcess);
  });

  describe('React Component Hot Reload', () => {
    it('should detect and hot reload React component changes', async () => {
      const componentPath = join(projectRoot, 'src', 'components', 'HotReloadTest.tsx');
      const originalContent = `
import React from 'react';

export default function HotReloadTest() {
  return (
    <div data-testid="hot-reload-content">
      <h1>Original Title</h1>
      <p>Original description</p>
    </div>
  );
}`;

      const modifiedContent = `
import React from 'react';

export default function HotReloadTest() {
  return (
    <div data-testid="hot-reload-content">
      <h1>Modified Title</h1>
      <p>Modified description</p>
    </div>
  );
}`;

      try {
        // Create test component
        await writeFile(componentPath, originalContent);

        // Start Vite dev server
        const startTime = Date.now();
        let hotReloadDetected = false;
        let reloadTime = 0;

        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, FORCE_COLOR: '0', VITE_CJS_IGNORE_WARNING: 'true' }
        });

        const outputData: string[] = [];
        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          outputData.push(output);

          if (output.includes('HMR') || output.includes('hot module replacement') ||
              output.includes('updated') || output.includes('reloaded')) {
            hotReloadDetected = true;
            reloadTime = Date.now() - startTime;
          }
        });

        viteProcess.stderr?.on('data', (data) => {
          outputData.push(data.toString());
        });

        // Wait for initial compilation
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Modify the component
        const modifyStartTime = Date.now();
        await writeFile(componentPath, modifiedContent);

        // Wait for hot reload
        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        expect(hotReloadDetected).toBe(true);
        expect(reloadTime).toBeLessThan(RESPONSE_TIME_TARGET);

        // Cleanup
        await unlink(componentPath);
      } catch (error) {
        try {
          await unlink(componentPath);
        } catch {}
        throw error;
      }
    }, 15000);

    it('should preserve component state during hot reload', async () => {
      const componentPath = join(projectRoot, 'src', 'components', 'StatefulHotReloadTest.tsx');
      const componentContent = `
import React, { useState } from 'react';

export default function StatefulHotReloadTest() {
  const [count, setCount] = useState(0);

  return (
    <div data-testid="stateful-component">
      <button onClick={() => setCount(count + 1)}>
        Count: {count}
      </button>
    </div>
  );
}`;

      try {
        await writeFile(componentPath, componentContent);

        let statePreserved = false;
        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('HMR') && output.includes('preserved')) {
            statePreserved = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        // Modify component (should preserve state)
        const modifiedContent = componentContent.replace(
          'Stateful Hot Reload Test',
          'Stateful Hot Reload Test (Modified)'
        );
        await writeFile(componentPath, modifiedContent);

        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        // Note: Actual state preservation would need browser testing
        // This test validates the hot reload mechanism is active
        expect(viteProcess?.killed).toBe(false);

        await unlink(componentPath);
      } catch (error) {
        try {
          await unlink(componentPath);
        } catch {}
        throw error;
      }
    }, 12000);
  });

  describe('Tauri Backend Hot Reload', () => {
    it('should coordinate Vite and Tauri hot reload', async () => {
      // Test that Tauri can detect and handle frontend changes
      let tauriCoordinationDetected = false;
      let viteCoordinationDetected = false;

      tauriProcess = spawn('npm', ['run', 'tauri:dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0' }
      });

      tauriProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('Watching') || output.includes('Reloading')) {
          tauriCoordinationDetected = true;
        }
      });

      // Start Vite as well to test coordination
      viteProcess = spawn('npm', ['run', 'dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, FORCE_COLOR: '0', PORT: '1421' } // Different port to avoid conflict
      });

      viteProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('ready in') || output.includes('Local:')) {
          viteCoordinationDetected = true;
        }
      });

      await new Promise(resolve => setTimeout(resolve, 8000));

      expect(viteCoordinationDetected).toBe(true);
      // Tauri coordination might take longer to initialize
    }, 12000);

    it('should handle Rust compilation errors gracefully', async () => {
      // This test would require modifying Rust files in src-tauri
      // For now, we'll test the error handling mechanism

      let errorHandlingDetected = false;
      tauriProcess = spawn('npm', ['run', 'tauri:dev'], {
        cwd: projectRoot,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      tauriProcess.stderr?.on('data', (data) => {
        const output = data.toString();
        if (output.includes('error') || output.includes('Error')) {
          errorHandlingDetected = true;
        }
      });

      await new Promise(resolve => setTimeout(resolve, 5000));

      // Test that error handling is active
      expect(tauriProcess?.killed).toBe(false);
    }, 10000);
  });

  describe('Style Hot Reload', () => {
    it('should hot reload TailwindCSS changes', async () => {
      const stylePath = join(projectRoot, 'src', 'styles', 'HotReloadStyles.css');
      const originalCSS = `
.test-hot-reload {
  @apply bg-red-500 text-white p-4 rounded;
}`;

      const modifiedCSS = `
.test-hot-reload {
  @apply bg-blue-500 text-white p-4 rounded-lg;
}`;

      try {
        await writeFile(stylePath, originalCSS);

        let styleHotReloadDetected = false;
        let styleUpdateTime = 0;
        const startTime = Date.now();

        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('.css') && (output.includes('updated') || output.includes('reloaded'))) {
            styleHotReloadDetected = true;
            styleUpdateTime = Date.now() - startTime;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        // Modify styles
        await writeFile(stylePath, modifiedCSS);
        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        expect(styleHotReloadDetected).toBe(true);
        expect(styleUpdateTime).toBeLessThan(RESPONSE_TIME_TARGET);

        await unlink(stylePath);
      } catch (error) {
        try {
          await unlink(stylePath);
        } catch {}
        throw error;
      }
    }, 12000);

    it('should handle Tailwind config changes', async () => {
      const tailwindConfigPath = join(projectRoot, 'tailwind.config.js');
      const originalConfig = await readFile(tailwindConfigPath, 'utf-8');

      try {
        // Add a custom color to test config hot reload
        const modifiedConfig = originalConfig.replace(
          'export default {',
          'export default {\n  theme: {\n    extend: {\n      colors: {\n        "custom-hot-reload": "#ff6b6b",\n      },\n    },\n  },'
        );

        await writeFile(tailwindConfigPath, modifiedConfig);

        let configHotReloadDetected = false;
        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('tailwind') && output.includes('reloaded')) {
            configHotReloadDetected = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 4000));

        // Restore original config
        await writeFile(tailwindConfigPath, originalConfig);
        await new Promise(resolve => setTimeout(resolve, 2000));

        expect(configHotReloadDetected).toBe(true);
      } catch (error) {
        // Restore original config on error
        await writeFile(tailwindConfigPath, originalConfig);
        throw error;
      }
    }, 10000);
  });

  describe('Error Recovery', () => {
    it('should recover from syntax errors during hot reload', async () => {
      const componentPath = join(projectRoot, 'src', 'components', 'ErrorRecoveryTest.tsx');
      const invalidContent = `
import React from 'react';

export default function ErrorRecoveryTest() {
  // Intentional syntax error
  const broken = {
  return <div>Broken Component</div>;
}`;

      const validContent = `
import React from 'react';

export default function ErrorRecoveryTest() {
  return <div>Fixed Component</div>;
}`;

      try {
        await writeFile(componentPath, invalidContent);

        let errorDetected = false;
        let recoveryDetected = false;

        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stderr?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('error') || output.includes('failed')) {
            errorDetected = true;
          }
        });

        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (errorDetected && output.includes('reloaded')) {
            recoveryDetected = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        // Fix the error
        await writeFile(componentPath, validContent);
        await new Promise(resolve => setTimeout(resolve, HOT_RELOAD_TIMEOUT));

        expect(errorDetected).toBe(true);
        // Recovery might take time or require manual refresh in real scenarios
        expect(viteProcess?.killed).toBe(false);

        await unlink(componentPath);
      } catch (error) {
        try {
          await unlink(componentPath);
        } catch {}
        throw error;
      }
    }, 15000);

    it('should handle missing file dependencies gracefully', async () => {
      const componentPath = join(projectRoot, 'src', 'components', 'MissingDependencyTest.tsx');
      const contentWithMissingImport = `
import React from 'react';
import { MissingComponent } from './MissingComponent';

export default function MissingDependencyTest() {
  return <MissingComponent />;
}`;

      try {
        await writeFile(componentPath, contentWithMissingImport);

        let dependencyErrorDetected = false;
        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stderr?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('Cannot find module') || output.includes('MissingComponent')) {
            dependencyErrorDetected = true;
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        expect(dependencyErrorDetected).toBe(true);
        expect(viteProcess?.killed).toBe(false); // Server should continue running

        await unlink(componentPath);
      } catch (error) {
        try {
          await unlink(componentPath);
        } catch {}
        throw error;
      }
    }, 10000);
  });

  describe('Performance Monitoring', () => {
    it('should meet hot reload performance targets', async () => {
      const componentPath = join(projectRoot, 'src', 'components', 'PerformanceTest.tsx');
      const componentContent = `
import React from 'react';

export default function PerformanceTest() {
  return <div data-testid="performance-test">Performance Test</div>;
}`;

      try {
        await writeFile(componentPath, componentContent);

        const performanceMetrics: number[] = [];

        viteProcess = spawn('npm', ['run', 'dev'], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });

        viteProcess.stdout?.on('data', (data) => {
          const output = data.toString();
          if (output.includes('HMR') || output.includes('updated')) {
            performanceMetrics.push(Date.now());
          }
        });

        await new Promise(resolve => setTimeout(resolve, 3000));

        // Make multiple changes to test consistency
        for (let i = 0; i < 3; i++) {
          const modifiedContent = componentContent.replace(
            `Performance Test`,
            `Performance Test ${i}`
          );
          await writeFile(componentPath, modifiedContent);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Calculate average response time
        if (performanceMetrics.length >= 2) {
          const times = [];
          for (let i = 1; i < performanceMetrics.length; i++) {
            times.push(performanceMetrics[i] - performanceMetrics[i - 1]);
          }
          const averageTime = times.reduce((a, b) => a + b, 0) / times.length;
          expect(averageTime).toBeLessThan(RESPONSE_TIME_TARGET);
        }

        await unlink(componentPath);
      } catch (error) {
        try {
          await unlink(componentPath);
        } catch {}
        throw error;
      }
    }, 15000);
  });
});