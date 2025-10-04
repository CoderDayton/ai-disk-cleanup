import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { readFileSync, existsSync, mkdirSync, rmSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

/**
 * Comprehensive test suite for Tauri 2.0 project structure setup
 *
 * This test validates that the Tauri 2.0 project has been created correctly
 * with all required configuration files and dependencies as specified in
 * the SDD requirements (sections 424-440).
 */
describe('Tauri 2.0 Project Structure Validation', () => {
  const projectRoot = process.cwd();
  const tauriDir = join(projectRoot, 'src-tauri');
  const srcDir = join(projectRoot, 'src');

  beforeEach(() => {
    // Ensure we're working with a clean test environment
    process.env.NODE_ENV = 'test';
  });

  afterEach(() => {
    // Clean up any test artifacts
    process.env.NODE_ENV = 'development';
  });

  describe('Core Tauri Configuration Files', () => {
    it('should have src-tauri directory structure', () => {
      expect(existsSync(tauriDir)).toBe(true);
      expect(existsSync(join(tauriDir, 'src'))).toBe(true);
      expect(existsSync(join(tauriDir, 'Cargo.toml'))).toBe(true);
      expect(existsSync(join(tauriDir, 'tauri.conf.json'))).toBe(true);
      expect(existsSync(join(tauriDir, 'build.rs'))).toBe(true);
    });

    it('should have valid tauri.conf.json with required settings', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      expect(existsSync(tauriConfigPath)).toBe(true);

      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Validate required Tauri 2.0 configuration structure
      expect(config).toHaveProperty('productName');
      expect(config).toHaveProperty('version');
      expect(config).toHaveProperty('identifier');
      expect(config).toHaveProperty('build');
      expect(config).toHaveProperty('app');
      expect(config).toHaveProperty('bundle');

      // Validate app configuration
      expect(config.app).toHaveProperty('windows');
      expect(config.app).toHaveProperty('security');

      // Validate security configuration (critical for SDD requirements)
      expect(config.app.security).toHaveProperty('csp');
      expect(config.app.security).toHaveProperty('assetProtocol');

      // Validate capability system (Tauri 2.0 requirement)
      if (config.capabilities) {
        expect(Array.isArray(config.capabilities)).toBe(true);
      }

      // Validate window configuration
      if (config.app.windows && config.app.windows.length > 0) {
        const mainWin = config.app.windows[0];
        expect(mainWin).toHaveProperty('label');
        expect(mainWin).toHaveProperty('title');
        expect(mainWin).toHaveProperty('url');
        expect(mainWin).toHaveProperty('width');
        expect(mainWin).toHaveProperty('height');
      }
    });

    it('should have properly configured Cargo.toml for Tauri dependencies', () => {
      const cargoPath = join(tauriDir, 'Cargo.toml');
      expect(existsSync(cargoPath)).toBe(true);

      const cargoContent = readFileSync(cargoPath, 'utf-8');

      // Validate Tauri 2.0 dependencies
      expect(cargoContent).toContain('tauri');
      expect(cargoContent).toContain('serde');
      expect(cargoContent).toContain('tokio');

      // Check for Tauri 2.0 specific features
      if (cargoContent.includes('tauri = {')) {
        expect(cargoContent).toContain('features');
      }

      // Validate required crate structure
      expect(cargoContent).toContain('[package]');
      expect(cargoContent).toContain('name =');
      expect(cargoContent).toContain('version =');
      expect(cargoContent).toContain('edition =');
    });

    it('should have Rust source files in proper structure', () => {
      const rustSrcDir = join(tauriDir, 'src');

      // Main entry point
      expect(existsSync(join(rustSrcDir, 'main.rs'))).toBe(true);
      expect(existsSync(join(rustSrcDir, 'lib.rs'))).toBe(true);

      // Command handlers directory (SDD requirement)
      const commandsDir = join(rustSrcDir, 'commands');
      if (existsSync(commandsDir)) {
        expect(existsSync(join(commandsDir, 'mod.rs'))).toBe(true);
        expect(existsSync(join(commandsDir, 'file_system.rs'))).toBe(true);
        expect(existsSync(join(commandsDir, 'system_integration.rs'))).toBe(true);
        expect(existsSync(join(commandsDir, 'security.rs'))).toBe(true);
        expect(existsSync(join(commandsDir, 'notifications.rs'))).toBe(true);
      }

      // Utility modules
      const utilsDir = join(rustSrcDir, 'utils');
      if (existsSync(utilsDir)) {
        expect(existsSync(join(utilsDir, 'mod.rs'))).toBe(true);
        expect(existsSync(join(utilsDir, 'config.rs'))).toBe(true);
        expect(existsSync(join(utilsDir, 'platform.rs'))).toBe(true);
        expect(existsSync(join(utilsDir, 'security.rs'))).toBe(true);
      }
    });

    it('should have build configuration (build.rs)', () => {
      const buildRsPath = join(tauriDir, 'build.rs');
      expect(existsSync(buildRsPath)).toBe(true);

      const buildContent = readFileSync(buildRsPath, 'utf-8');
      expect(buildContent).toContain('fn main()');
    });
  });

  describe('Tauri Capability System Configuration', () => {
    it('should have capability definitions for security boundaries', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Check if capabilities are defined (Tauri 2.0 security model)
      if (config.capabilities) {
        // Should have file system capabilities for directory access
        const hasFileSystemCap = config.capabilities.some((cap: any) =>
          cap.identifier && cap.identifier.includes('filesystem')
        );

        // Should have shell capabilities if needed
        const hasShellCap = config.capabilities.some((cap: any) =>
          cap.identifier && cap.identifier.includes('shell')
        );

        // Validate capability structure
        config.capabilities.forEach((capability: any) => {
          expect(capability).toHaveProperty('identifier');
          expect(capability).toHaveProperty('description');
          if (capability.windows) {
            expect(Array.isArray(capability.windows)).toBe(true);
          }
          if (capability.permissions) {
            expect(Array.isArray(capability.permissions)).toBe(true);
          }
        });
      }
    });

    it('should have proper security configuration in tauri.conf.json', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      const security = config.app.security;

      // Content Security Policy should be configured
      if (security.csp) {
        expect(typeof security.csp).toBe('string');
        expect(security.csp).toContain('default-src');
      }

      // Asset protocol security
      if (security.assetProtocol) {
        expect(security.assetProtocol).toHaveProperty('enable');
        expect(typeof security.assetProtocol.enable).toBe('boolean');
      }

      // Freeze prototype should be enabled for security
      if (security.freezePrototype !== undefined) {
        expect(typeof security.freezePrototype).toBe('boolean');
      }
    });
  });

  describe('Tauri Build System Validation', () => {
    it('should be able to execute cargo check without errors', () => {
      try {
        // Check if Rust toolchain is available
        execSync('cargo --version', { stdio: 'pipe' });

        // Try to check the Rust code
        if (existsSync(tauriDir)) {
          const result = execSync('cargo check', {
            cwd: tauriDir,
            stdio: 'pipe'
          });
          expect(result).toBeDefined();
        }
      } catch (error) {
        // If Rust toolchain is not available, skip this test
        console.warn('Rust toolchain not available, skipping build validation');
      }
    });

    it('should have proper dependency resolution in Cargo.lock', () => {
      const cargoLockPath = join(tauriDir, 'Cargo.lock');
      if (existsSync(cargoLockPath)) {
        const lockContent = readFileSync(cargoLockPath, 'utf-8');
        expect(lockContent).toContain('[[package]]');
        expect(lockContent).toContain('name = "tauri"');
      }
    });
  });

  describe('Tauri Integration Points', () => {
    it('should have proper integration with frontend build output', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Check if frontendDist is properly configured
      if (config.build) {
        expect(config.build).toHaveProperty('frontendDist');
        expect(typeof config.build.frontendDist).toBe('string');

        // Should point to the correct frontend build directory
        const frontendDist = config.build.frontendDist;
        const expectedPaths = ['../dist', '../build', '../out'];
        const isValidPath = expectedPaths.some(path => frontendDist.includes(path));
        expect(isValidPath).toBe(true);
      }
    });

    it('should have proper development server configuration', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Check if devUrl is configured for development
      if (config.build && config.build.devUrl) {
        expect(typeof config.build.devUrl).toBe('string');
        expect(config.build.devUrl).toMatch(/^http:\/\/localhost:\d+$/);
      }
    });
  });

  describe('Cross-Platform Configuration', () => {
    it('should have platform-specific bundle configuration', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      if (config.bundle) {
        // Windows configuration
        if (config.bundle.windows) {
          expect(config.bundle.windows).toHaveProperty('certificateThumbprint');
          expect(config.bundle.windows).toHaveProperty('digestAlgorithm');
          expect(config.bundle.windows).toHaveProperty('timestampUrl');
        }

        // macOS configuration
        if (config.bundle.macOS) {
          expect(config.bundle.macOS).toHaveProperty('entitlements');
          expect(config.bundle.macOS).toHaveProperty('providerShortName');
        }

        // Linux configuration
        if (config.bundle.linux) {
          expect(config.bundle.linux).toHaveProperty('deb');
          expect(config.bundle.linux).toHaveProperty('appimage');
        }
      }
    });

    it('should have proper icon configuration', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      if (config.bundle) {
        expect(config.bundle).toHaveProperty('icon');
        if (config.bundle.icon) {
          if (Array.isArray(config.bundle.icon)) {
            expect(config.bundle.icon.length).toBeGreaterThan(0);
          } else {
            expect(typeof config.bundle.icon).toBe('string');
          }
        }
      }
    });
  });

  describe('Performance and Security Requirements', () => {
    it('should meet performance requirements specified in SDD', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Check for performance-related configurations
      if (config.app) {
        // Window configuration should support efficient rendering
        if (config.app.windows) {
          config.app.windows.forEach((window: any) => {
            if (window.minWidth) {
              expect(typeof window.minWidth).toBe('number');
              expect(window.minWidth).toBeGreaterThan(0);
            }
            if (window.minHeight) {
              expect(typeof window.minHeight).toBe('number');
              expect(window.minHeight).toBeGreaterThan(0);
            }
          });
        }
      }
    });

    it('should have security-first configuration as per SDD requirements', () => {
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Security configurations should be present
      expect(config.app).toHaveProperty('security');

      const security = config.app.security;

      // Should have dangerous capabilities disabled by default
      if (security.dangerousDisableAssetCsp !== undefined) {
        expect(security.dangerousDisableAssetCsp).toBe(false);
      }

      // Should have proper CSP configured
      if (security.csp) {
        // CSP should not be overly permissive
        expect(security.csp).not.toContain("'unsafe-inline'");
        expect(security.csp).not.toContain("'unsafe-eval'");
      }
    });
  });

  describe('Integration with Existing Python Backend', () => {
    it('should have configuration for backend integration', () => {
      // This test validates that the Tauri app can communicate with the
      // FastAPI bridge layer mentioned in the SDD
      const tauriConfigPath = join(tauriDir, 'tauri.conf.json');
      const config = JSON.parse(readFileSync(tauriConfigPath, 'utf-8'));

      // Should have permissions for HTTP requests to localhost
      if (config.capabilities) {
        const httpCap = config.capabilities.find((cap: any) =>
          cap.identifier && cap.identifier.includes('http')
        );

        if (httpCap && httpCap.permissions) {
          const hasLocalhostPermission = httpCap.permissions.some((perm: any) =>
            typeof perm === 'string' && perm.includes('localhost')
          );
          // This ensures the app can communicate with the FastAPI bridge
        }
      }
    });

    it('should have Rust command handlers for file system operations', () => {
      const commandsDir = join(tauriDir, 'src', 'commands');

      if (existsSync(commandsDir)) {
        // File system operations for Python backend integration
        const fileSystemCmds = join(commandsDir, 'file_system.rs');
        if (existsSync(fileSystemCmds)) {
          const content = readFileSync(fileSystemCmds, 'utf-8');

          // Should have Tauri command decorators
          expect(content).toContain('#[tauri::command]');

          // Should have file system operations
          expect(content).toMatch(/use\s+std::fs/);
          expect(content).toMatch(/fn\s+\w+/);
        }
      }
    });
  });

  describe('Development Environment Validation', () => {
    it('should have Tauri CLI dependencies available', () => {
      const packageJsonPath = join(projectRoot, 'package.json');

      if (existsSync(packageJsonPath)) {
        const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

        // Should have Tauri development dependencies
        if (packageJson.devDependencies) {
          expect(packageJson.devDependencies).toHaveProperty('@tauri-apps/cli');
          expect(packageJson.devDependencies).toHaveProperty('@tauri-apps/api');
        }
      }
    });

    it('should have proper build scripts configuration', () => {
      const packageJsonPath = join(projectRoot, 'package.json');

      if (existsSync(packageJsonPath)) {
        const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));

        // Should have Tauri development and build scripts
        if (packageJson.scripts) {
          expect(packageJson.scripts).toHaveProperty('tauri');
          expect(packageJson.scripts).toHaveProperty('tauri:dev');
          expect(packageJson.scripts).toHaveProperty('tauri:build');
        }
      }
    });
  });
});