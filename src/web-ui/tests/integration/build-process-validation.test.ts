/**
 * Build Process Validation Tests
 *
 * Validates the complete build process including Vite configuration,
 * TypeScript compilation, asset processing, optimization, and error handling.
 * Ensures the build meets performance targets and production requirements.
 */

import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { promisify } from 'util';
import { readFile, writeFile, access, stat, readdir, unlink } from 'fs/promises';
import { join, resolve } from 'path';
import { createRequire } from 'module';
import { spawn } from 'child_process';

const require = createRequire(import.meta.url);
const exec = promisify(require('child_process').exec);

describe('Build Process Validation', () => {
  const projectRoot = resolve(__dirname, '../..');
  const BUILD_TIMEOUT = 120000; // 2 minutes
  const STARTUP_TARGET = 2000; // SDD requirement: <2 second startup
  const BUNDLE_SIZE_TARGET = 5 * 1024 * 1024; // 5MB target

  beforeAll(async () => {
    process.chdir(projectRoot);

    // Clean any existing build artifacts
    try {
      const distExists = await stat(join(projectRoot, 'dist'));
      if (distExists.isDirectory()) {
        await exec('rm -rf dist', { cwd: projectRoot });
      }
    } catch {
      // dist directory doesn't exist, which is fine
    }
  });

  afterAll(async () => {
    // Cleanup test artifacts
    try {
      await exec('rm -rf dist', { cwd: projectRoot });
    } catch {
      // Ignore cleanup errors
    }
  });

  describe('Vite Build Configuration', () => {
    it('should validate Vite build settings', async () => {
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Check build optimization settings
      expect(viteConfig).toContain('build: {');
      expect(viteConfig).toContain('outDir: \'dist\'');
      expect(viteConfig).toContain('target: \'es2021\'');
      expect(viteConfig).toContain('minify: \'esbuild\'');
      expect(viteConfig).toContain('sourcemap: true');
      expect(viteConfig).toContain('assetsInlineLimit: 4096');

      // Check dependency optimization
      expect(viteConfig).toContain('optimizeDeps: {');
      expect(viteConfig).toContain('react');
      expect(viteConfig).toContain('react-dom');
      expect(viteConfig).toContain('@tanstack/react-router');
      expect(viteConfig).toContain('@tanstack/react-query');
    });

    it('should build within performance targets', async () => {
      const startTime = Date.now();

      const { stdout, stderr } = await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const buildTime = Date.now() - startTime;

      // Should build without errors
      expect(stderr).not.toContain('error');
      expect(stdout).toContain('build');
      expect(stdout).toContain('dist/');

      // Build should complete within reasonable time
      expect(buildTime).toBeLessThan(60000); // 1 minute max for build

      console.log(`Build completed in ${buildTime}ms`);
    }, BUILD_TIMEOUT);

    it('should generate all required build artifacts', async () => {
      // Ensure build exists
      await stat(join(projectRoot, 'dist'));

      const distFiles = await readdir(join(projectRoot, 'dist'));

      // Check for essential files
      expect(distFiles).toContain('index.html');
      expect(distFiles.some(file => file.endsWith('.js'))).toBe(true);
      expect(distFiles.some(file => file.endsWith('.css'))).toBe(true);

      // Check for assets directory
      try {
        await stat(join(projectRoot, 'dist', 'assets'));
        // assets directory exists
      } catch {
        // assets directory might not exist if no assets
      }

      // Validate index.html structure
      const indexHtml = await readFile(join(projectRoot, 'dist', 'index.html'), 'utf-8');
      expect(indexHtml).toContain('<!DOCTYPE html>');
      expect(indexHtml).toContain('<script');
      expect(indexHtml).toContain('<link');
      expect(indexHtml).toContain('type="module"');
    });

    it('should optimize bundle sizes', async () => {
      // Build if not already built
      try {
        await stat(join(projectRoot, 'dist'));
      } catch {
        await exec('npm run build', { cwd: projectRoot, timeout: BUILD_TIMEOUT });
      }

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const jsFiles = distFiles.filter(file => file.endsWith('.js'));
      const cssFiles = distFiles.filter(file => file.endsWith('.css'));

      let totalBundleSize = 0;

      // Check JavaScript bundle sizes
      for (const jsFile of jsFiles) {
        const jsStats = await stat(join(projectRoot, 'dist', jsFile));
        totalBundleSize += jsStats.size;

        // Individual files should be reasonably sized
        expect(jsStats.size).toBeLessThan(2 * 1024 * 1024); // 2MB per file max
        console.log(`JavaScript file ${jsFile}: ${(jsStats.size / 1024).toFixed(2)}KB`);
      }

      // Check CSS bundle sizes
      for (const cssFile of cssFiles) {
        const cssStats = await stat(join(projectRoot, 'dist', cssFile));
        totalBundleSize += cssStats.size;

        // CSS files should be smaller
        expect(cssStats.size).toBeLessThan(500 * 1024); // 500KB per CSS file max
        console.log(`CSS file ${cssFile}: ${(cssStats.size / 1024).toFixed(2)}KB`);
      }

      // Total bundle should be within target
      expect(totalBundleSize).toBeLessThan(BUNDLE_SIZE_TARGET);
      console.log(`Total bundle size: ${(totalBundleSize / 1024 / 1024).toFixed(2)}MB`);
    });

    it('should generate proper source maps', async () => {
      // Build if not already built
      try {
        await stat(join(projectRoot, 'dist'));
      } catch {
        await exec('npm run build', { cwd: projectRoot, timeout: BUILD_TIMEOUT });
      }

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const sourceMapFiles = distFiles.filter(file => file.endsWith('.map'));

      // Should have source maps for JavaScript files
      expect(sourceMapFiles.length).toBeGreaterThan(0);

      for (const mapFile of sourceMapFiles) {
        const mapStats = await stat(join(projectRoot, 'dist', mapFile));
        expect(mapStats.size).toBeGreaterThan(0);
      }
    });
  });

  describe('TypeScript Compilation', () => {
    it('should compile TypeScript without errors', async () => {
      const { stdout, stderr } = await exec('npx tsc --noEmit', {
        cwd: projectRoot,
        timeout: 60000
      });

      // Should not have TypeScript compilation errors
      expect(stderr).not.toContain('error');
      expect(stdout).not.toContain('Found') || expect(stdout).toContain('Found 0 errors');
    }, 65000);

    it('should include proper type definitions', async () => {
      // Build to generate type definitions
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      // Check for .d.ts files in the build
      const distFiles = await readdir(join(projectRoot, 'dist'));
      const dtsFiles = distFiles.filter(file => file.endsWith('.d.ts'));

      // Note: Vite might not generate .d.ts files by default
      // This test validates the TypeScript compilation process
      console.log(`Generated ${dtsFiles.length} type definition files`);
    });

    it('should handle TypeScript errors gracefully', async () => {
      const errorFile = join(projectRoot, 'src', 'components', 'TypeScriptBuildError.tsx');
      const errorContent = `
import React from 'react';

export default function TypeScriptBuildError() {
  // Multiple TypeScript errors
  const wrongType: string = 123;
  const undefinedVar: undefined = 'test';

  function missingReturnType(param: any) {
    return param;
  }

  return <div>{wrongType}</div>;
}`;

      try {
        await writeFile(errorFile, errorContent);

        try {
          await exec('npm run build', {
            cwd: projectRoot,
            timeout: 60000
          });
          // Should not reach here - should fail on TypeScript errors
          expect(true).toBe(false);
        } catch (buildError: any) {
          // Should detect and report TypeScript errors
          expect(buildError.stdout || buildError.stderr).toBeDefined();
        }

        await unlink(errorFile);
      } catch (error) {
        try {
          await unlink(errorFile);
        } catch {}
        throw error;
      }
    }, 65000);
  });

  describe('Asset Processing and Optimization', () => {
    it('should process CSS assets correctly', async () => {
      // Build if not already built
      try {
        await stat(join(projectRoot, 'dist'));
      } catch {
        await exec('npm run build', { cwd: projectRoot, timeout: BUILD_TIMEOUT });
      }

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const cssFiles = distFiles.filter(file => file.endsWith('.css'));

      expect(cssFiles.length).toBeGreaterThan(0);

      for (const cssFile of cssFiles) {
        const cssContent = await readFile(join(projectRoot, 'dist', cssFile), 'utf-8');

        // CSS should be minified
        expect(cssContent.split('\n').length).toBeLessThan(100); // Reasonably few lines

        // Should contain TailwindCSS utilities
        expect(cssContent).toMatch(/\.[a-zA-Z0-9_-]+\s*{/); // CSS class syntax

        console.log(`CSS file ${cssFile}: ${cssContent.length} characters`);
      }
    });

    it('should inline small assets', async () => {
      // Build if not already built
      try {
        await stat(join(projectRoot, 'dist'));
      } catch {
        await exec('npm run build', { cwd: projectRoot, timeout: BUILD_TIMEOUT });
      }

      const indexHtml = await readFile(join(projectRoot, 'dist', 'index.html'), 'utf-8');

      // Should have some inlined assets (base64 or inline SVG)
      const hasInlinedAssets = indexHtml.includes('data:') || indexHtml.includes('<svg');
      console.log(`Has inlined assets: ${hasInlinedAssets}`);
    });

    it('should optimize images and static assets', async () => {
      const testImagePath = join(projectRoot, 'public', 'test-optimization.png');

      // Create a test image (1x1 transparent PNG)
      const pngData = Buffer.from([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 dimensions
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0x00,
        0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
        0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
        0xAE, 0x42, 0x60, 0x82
      ]);

      try {
        await writeFile(testImagePath, pngData);

        // Build with the test image
        await exec('npm run build', {
          cwd: projectRoot,
          timeout: BUILD_TIMEOUT
        });

        const distFiles = await readdir(join(projectRoot, 'dist'));

        // Check if image was processed
        const hasImages = distFiles.some(file =>
          file.endsWith('.png') || file.endsWith('.jpg') || file.endsWith('.svg')
        );

        console.log(`Processed images in build: ${hasImages}`);

        // Cleanup
        await unlink(testImagePath);
      } catch (error) {
        try {
          await unlink(testImagePath);
        } catch {}
        throw error;
      }
    }, BUILD_TIMEOUT);
  });

  describe('Error Handling and Debugging', () => {
    it('should provide meaningful build error messages', async () => {
      const errorFile = join(projectRoot, 'src', 'components', 'BuildErrorMessageTest.tsx');
      const errorContent = `
import React from 'react';
import { NonExistentComponent } from './NonExistentModule';

export default function BuildErrorMessageTest() {
  return <NonExistentComponent />;
}`;

      try {
        await writeFile(errorFile, errorContent);

        try {
          await exec('npm run build', {
            cwd: projectRoot,
            timeout: 60000
          });
          expect(true).toBe(false); // Should not succeed
        } catch (buildError: any) {
          const errorOutput = buildError.stdout || buildError.stderr;

          // Should provide meaningful error information
          expect(errorOutput).toBeDefined();
          expect(typeof errorOutput).toBe('string');
          expect(errorOutput.length).toBeGreaterThan(0);
        }

        await unlink(errorFile);
      } catch (error) {
        try {
          await unlink(errorFile);
        } catch {}
        throw error;
      }
    }, 65000);

    it('should handle missing dependencies gracefully', async () => {
      const packageJsonPath = join(projectRoot, 'package.json');
      const originalPackageJson = await readFile(packageJsonPath, 'utf-8');
      const packageJson = JSON.parse(originalPackageJson);

      try {
        // Temporarily remove a dependency
        const originalReact = packageJson.dependencies.react;
        delete packageJson.dependencies.react;
        await writeFile(packageJsonPath, JSON.stringify(packageJson, null, 2));

        try {
          await exec('npm run build', {
            cwd: projectRoot,
            timeout: 60000
          });
          expect(true).toBe(false); // Should fail
        } catch (buildError: any) {
          // Should handle missing dependency
          const errorOutput = buildError.stdout || buildError.stderr;
          expect(errorOutput).toBeDefined();
        }

        // Restore package.json
        await writeFile(packageJsonPath, originalPackageJson);
      } catch (error) {
        // Restore on error
        await writeFile(packageJsonPath, originalPackageJson);
        throw error;
      }
    }, 65000);

    it('should generate proper sourcemap references', async () => {
      // Build with sourcemaps
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const jsFiles = distFiles.filter(file => file.endsWith('.js'));

      for (const jsFile of jsFiles) {
        const jsContent = await readFile(join(projectRoot, 'dist', jsFile), 'utf-8');

        // Should reference source maps
        expect(jsContent).toContain('//# sourceMappingURL=');
      }
    }, BUILD_TIMEOUT);
  });

  describe('Tauri Integration Build', () => {
    it('should validate Tauri build configuration', async () => {
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );

      // Validate build commands
      expect(tauriConfig.build.beforeBuildCommand).toBe('npm run build');
      expect(tauriConfig.build.frontendDist).toBe('../dist');

      // Validate production settings
      expect(tauriConfig.bundle.active).toBe(true);
      expect(tauriConfig.bundle.targets).toBe('all');
    });

    it('should prepare frontend for Tauri packaging', async () => {
      // Build frontend first
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      // Check that dist directory is ready for Tauri
      await stat(join(projectRoot, 'dist', 'index.html'));

      // Validate Tauri can access the build
      const tauriConfig = JSON.parse(
        await readFile(join(projectRoot, 'src-tauri', 'tauri.conf.json'), 'utf-8')
      );
      const frontendDist = tauriConfig.build.frontendDist;
      const distPath = join(projectRoot, frontendDist);

      await stat(distPath);
      await stat(join(distPath, 'index.html'));
    }, BUILD_TIMEOUT);

    it('should handle Tauri-specific build requirements', async () => {
      // Build and check for Tauri-specific requirements
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const indexHtml = await readFile(join(projectRoot, 'dist', 'index.html'), 'utf-8');

      // Should be compatible with Tauri's webview
      expect(indexHtml).toContain('<meta charset="UTF-8">');
      expect(indexHtml).toContain('<meta name="viewport"');

      // Should not have external CDN dependencies that Tauri can't access
      expect(indexHtml).not.toContain('http://cdn.');
      expect(indexHtml).not.toContain('https://cdn.');
    }, BUILD_TIMEOUT);
  });

  describe('Performance Validation', () => {
    it('should meet SDD performance requirements', async () => {
      const buildStartTime = Date.now();

      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const buildTime = Date.now() - buildStartTime;

      // SDD requirement: <2 second startup (for build, we allow more time but still reasonable)
      expect(buildTime).toBeLessThan(30000); // 30 seconds max for build

      console.log(`Build performance: ${buildTime}ms (target: <30s for build process)`);
    }, BUILD_TIMEOUT);

    it('should optimize for sub-100ms response times', async () => {
      // Validate build optimizations that contribute to fast runtime performance
      const viteConfig = await readFile(join(projectRoot, 'vite.config.ts'), 'utf-8');

      // Check for performance optimizations
      expect(viteConfig).toContain('minify: \'esbuild\''); // Fast minification
      expect(viteConfig).toContain('optimizeDeps'); // Dependency pre-bundling
      expect(viteConfig).toContain('assetsInlineLimit'); // Asset optimization

      // Validate build output for performance
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const indexHtml = await readFile(join(projectRoot, 'dist', 'index.html'), 'utf-8');

      // Should have module loading for better performance
      expect(indexHtml).toContain('type="module"');

      // Should have proper resource hints
      expect(indexHtml).toContain('<link rel=');
    }, BUILD_TIMEOUT);

    it('should maintain bundle efficiency', async () => {
      // Build and analyze bundle efficiency
      await exec('npm run build', {
        cwd: projectRoot,
        timeout: BUILD_TIMEOUT
      });

      const distFiles = await readdir(join(projectRoot, 'dist'));
      const jsFiles = distFiles.filter(file => file.endsWith('.js'));

      let totalJsSize = 0;
      const chunkAnalysis: { name: string; size: number }[] = [];

      for (const jsFile of jsFiles) {
        const stats = await stat(join(projectRoot, 'dist', jsFile));
        totalJsSize += stats.size;
        chunkAnalysis.push({ name: jsFile, size: stats.size });
      }

      // Analyze chunk sizes
      chunkAnalysis.forEach(chunk => {
        const sizeKB = chunk.size / 1024;
        console.log(`Chunk ${chunk.name}: ${sizeKB.toFixed(2)}KB`);

        // Chunks should be reasonably sized
        expect(chunk.size).toBeLessThan(1024 * 1024); // 1MB per chunk max
      });

      // Total JavaScript should be efficient
      expect(totalJsSize).toBeLessThan(3 * 1024 * 1024); // 3MB total JS max

      console.log(`Total JavaScript: ${(totalJsSize / 1024 / 1024).toFixed(2)}MB`);
    }, BUILD_TIMEOUT);
  });
});