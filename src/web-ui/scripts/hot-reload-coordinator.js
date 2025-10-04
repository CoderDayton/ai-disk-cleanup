#!/usr/bin/env node

/**
 * Hot Reload Coordinator for AI Disk Cleaner
 * Coordinates hot reload between Vite dev server and Tauri development
 */

const { spawn } = require('child_process');
const { watch } = require('fs');
const { join, extname } = require('path');
const { EventEmitter } = require('events');

class HotReloadCoordinator extends EventEmitter {
  constructor(options = {}) {
    super();

    this.options = {
      vitePort: options.vitePort || 1420,
      tauriWatchDir: options.tauriWatchDir || 'src-tauri',
      sourceWatchDir: options.sourceWatchDir || 'src',
      debounceDelay: options.debounceDelay || 300,
      autoRestart: options.autoRestart !== false,
      ...options,
    };

    this.processes = {
      vite: null,
      tauri: null,
    };

    this.state = {
      viteReady: false,
      tauriReady: false,
      restarting: false,
    };

    this.pendingChanges = new Set();
    this.debounceTimer = null;

    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.on('vite-ready', () => {
      this.state.viteReady = true;
      console.log('✅ Vite dev server is ready');
      this.checkReadyState();
    });

    this.on('tauri-ready', () => {
      this.state.tauriReady = true;
      console.log('✅ Tauri development is ready');
      this.checkReadyState();
    });

    this.on('source-changed', (filePath) => {
      console.log(`📝 Source file changed: ${filePath}`);
      this.handleSourceChange(filePath);
    });

    this.on('rust-changed', (filePath) => {
      console.log(`🦀 Rust file changed: ${filePath}`);
      this.handleRustChange(filePath);
    });

    // Handle process exits
    process.on('SIGINT', () => this.shutdown());
    process.on('SIGTERM', () => this.shutdown());
    process.on('exit', () => this.shutdown());
  }

  async start() {
    console.log('🚀 Starting hot reload coordinator...\n');

    try {
      await this.startVite();
      await this.startTauri();
      await this.setupFileWatchers();

      console.log('🔄 Hot reload coordinator is running');
      console.log(`   - Vite server: http://localhost:${this.options.vitePort}`);
      console.log(`   - Watching: ${this.options.sourceWatchDir}, ${this.options.tauriWatchDir}`);
    } catch (error) {
      console.error('❌ Failed to start hot reload coordinator:', error);
      process.exit(1);
    }
  }

  async startVite() {
    console.log('📦 Starting Vite dev server...');

    return new Promise((resolve, reject) => {
      this.processes.vite = spawn('npm', ['run', 'dev'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: true,
        cwd: process.cwd(),
      });

      let output = '';
      this.processes.vite.stdout.on('data', (data) => {
        const text = data.toString();
        output += text;

        if (text.includes('ready in') || text.includes('Local:')) {
          this.emit('vite-ready');
          resolve();
        }

        // Forward Vite output
        process.stdout.write(`[Vite] ${text}`);
      });

      this.processes.vite.stderr.on('data', (data) => {
        process.stderr.write(`[Vite Error] ${data.toString()}`);
      });

      this.processes.vite.on('error', reject);
      this.processes.vite.on('close', (code) => {
        if (code !== 0 && !this.state.restarting) {
          console.error(`Vite process exited with code ${code}`);
          reject(new Error(`Vite process exited with code ${code}`));
        }
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (!this.state.viteReady) {
          reject(new Error('Vite server failed to start within timeout'));
        }
      }, 30000);
    });
  }

  async startTauri() {
    console.log('🦀 Starting Tauri development...');

    return new Promise((resolve, reject) => {
      // Wait for Vite to be ready first
      if (!this.state.viteReady) {
        this.once('vite-ready', () => this.startTauri().then(resolve).catch(reject));
        return;
      }

      this.processes.tauri = spawn('npm', ['run', 'tauri:dev'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: true,
        cwd: process.cwd(),
        env: {
          ...process.env,
          RUST_LOG: 'info',
          TAURI_DEBUG: 'true',
        },
      });

      let output = '';
      this.processes.tauri.stdout.on('data', (data) => {
        const text = data.toString();
        output += text;

        if (text.includes('listening on') || text.includes('app.ready')) {
          this.emit('tauri-ready');
          resolve();
        }

        // Forward Tauri output
        process.stdout.write(`[Tauri] ${text}`);
      });

      this.processes.tauri.stderr.on('data', (data) => {
        process.stderr.write(`[Tauri Error] ${data.toString()}`);
      });

      this.processes.tauri.on('error', reject);
      this.processes.tauri.on('close', (code) => {
        if (code !== 0 && !this.state.restarting) {
          console.error(`Tauri process exited with code ${code}`);
          reject(new Error(`Tauri process exited with code ${code}`));
        }
      });

      // Timeout after 60 seconds
      setTimeout(() => {
        if (!this.state.tauriReady) {
          reject(new Error('Tauri development failed to start within timeout'));
        }
      }, 60000);
    });
  }

  async setupFileWatchers() {
    console.log('👀 Setting up file watchers...');

    // Watch source files (TypeScript, CSS, etc.)
    const sourceWatcher = watch(this.options.sourceWatchDir, {
      recursive: true,
      persistent: true,
    });

    sourceWatcher.on('change', (filePath) => {
      const ext = extname(filePath).toLowerCase();
      if (['.ts', '.tsx', '.js', '.jsx', '.css', '.scss', '.less', '.json'].includes(ext)) {
        this.emit('source-changed', filePath);
      }
    });

    sourceWatcher.on('error', (error) => {
      console.error('Source watcher error:', error);
    });

    // Watch Rust files
    const rustWatcher = watch(this.options.tauriWatchDir, {
      recursive: true,
      persistent: true,
    });

    rustWatcher.on('change', (filePath) => {
      const ext = extname(filePath).toLowerCase();
      if (['.rs', '.toml'].includes(ext)) {
        this.emit('rust-changed', filePath);
      }
    });

    rustWatcher.on('error', (error) => {
      console.error('Rust watcher error:', error);
    });

    console.log(`📁 Watching ${this.options.sourceWatchDir} for frontend changes`);
    console.log(`📁 Watching ${this.options.tauriWatchDir} for backend changes`);
  }

  handleSourceChange(filePath) {
    // Add to pending changes
    this.pendingChanges.add(filePath);

    // Debounce rapid changes
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.processPendingSourceChanges();
    }, this.options.debounceDelay);
  }

  async processPendingSourceChanges() {
    if (this.pendingChanges.size === 0) return;

    const changes = Array.from(this.pendingChanges);
    this.pendingChanges.clear();
    this.debounceTimer = null;

    console.log(`🔄 Processing ${changes.length} source file changes...`);

    try {
      // Vite handles hot reload automatically for most file types
      // We just need to log the changes
      changes.forEach(filePath => {
        const ext = extname(filePath).toLowerCase();
        if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) {
          console.log(`   - Component/Logic: ${filePath}`);
        } else if (['.css', '.scss', '.less'].includes(ext)) {
          console.log(`   - Styles: ${filePath}`);
        } else {
          console.log(`   - Resource: ${filePath}`);
        }
      });

      this.emit('source-reloaded', changes);
    } catch (error) {
      console.error('❌ Error processing source changes:', error);
    }
  }

  async handleRustChange(filePath) {
    console.log(`🔄 Rust file changed, restarting Tauri: ${filePath}`);

    if (!this.options.autoRestart) {
      console.log('ℹ️ Auto-restart disabled. Manual restart required.');
      return;
    }

    try {
      await this.restartTauri();
    } catch (error) {
      console.error('❌ Error restarting Tauri:', error);
    }
  }

  async restartTauri() {
    if (this.state.restarting) {
      console.log('⏳ Tauri restart already in progress...');
      return;
    }

    this.state.restarting = true;
    this.state.tauriReady = false;

    console.log('🔄 Restarting Tauri development...');

    try {
      // Kill existing Tauri process
      if (this.processes.tauri) {
        this.processes.tauri.kill('SIGTERM');
        await new Promise(resolve => {
          this.processes.tauri.on('close', resolve);
          setTimeout(resolve, 5000); // Force close after 5 seconds
        });
      }

      // Start new Tauri process
      await this.startTauri();
      console.log('✅ Tauri development restarted successfully');

    } catch (error) {
      console.error('❌ Failed to restart Tauri:', error);
    } finally {
      this.state.restarting = false;
    }
  }

  checkReadyState() {
    if (this.state.viteReady && this.state.tauriReady) {
      console.log('\n🎉 Hot reload environment is ready!');
      console.log('   - Frontend: Hot reload enabled');
      console.log('   - Backend: Rust changes trigger restart');
      console.log('   - Press Ctrl+C to stop\n');
    }
  }

  async shutdown() {
    console.log('\n🛑 Shutting down hot reload coordinator...');

    try {
      // Kill processes
      if (this.processes.vite) {
        this.processes.vite.kill('SIGTERM');
      }

      if (this.processes.tauri) {
        this.processes.tauri.kill('SIGTERM');
      }

      // Clear timers
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
      }

      console.log('✅ Shutdown complete');
      process.exit(0);
    } catch (error) {
      console.error('❌ Error during shutdown:', error);
      process.exit(1);
    }
  }

  // Performance monitoring
  startPerformanceMonitoring() {
    console.log('📊 Starting performance monitoring...');

    setInterval(() => {
      const memUsage = process.memoryUsage();
      const cpuUsage = process.cpuUsage();

      console.log(`📈 Performance: RSS=${(memUsage.rss / 1024 / 1024).toFixed(1)}MB, Heap=${(memUsage.heapUsed / 1024 / 1024).toFixed(1)}MB`);
    }, 30000); // Every 30 seconds
  }

  // Health check
  async healthCheck() {
    const checks = {
      vite: this.processes.vape && !this.processes.vite.killed,
      tauri: this.processes.tauri && !this.processes.tauri.killed,
      viteReady: this.state.viteReady,
      tauriReady: this.state.tauriReady,
    };

    const healthy = Object.values(checks).every(Boolean);

    if (!healthy) {
      console.warn('⚠️ Health check failed:', checks);
      this.emit('health-check-failed', checks);
    }

    return healthy;
  }
}

// CLI interface
if (require.main === module) {
  const options = {
    vitePort: parseInt(process.env.VITE_PORT) || 1420,
    autoRestart: process.env.AUTO_RESTART !== 'false',
    debounceDelay: parseInt(process.env.DEBOUNCE_DELAY) || 300,
  };

  const coordinator = new HotReloadCoordinator(options);

  // Start performance monitoring
  coordinator.startPerformanceMonitoring();

  // Start health checks
  setInterval(() => coordinator.healthCheck(), 60000); // Every minute

  // Start the coordinator
  coordinator.start().catch(error => {
    console.error('❌ Failed to start hot reload coordinator:', error);
    process.exit(1);
  });
}

module.exports = HotReloadCoordinator;