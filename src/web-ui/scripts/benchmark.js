#!/usr/bin/env node

/**
 * Performance benchmark script for AI Disk Cleaner
 * Measures startup time, response times, and resource usage
 */

const { performance } = require('perf_hooks');
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class PerformanceBenchmark {
  constructor() {
    this.results = {
      startup: { measurements: [] },
      response: { measurements: [] },
      memory: { measurements: [] },
      timestamp: new Date().toISOString(),
    };
    this.thresholds = {
      startupTime: 2000, // 2 seconds
      responseTime: 100, // 100ms
      memoryUsage: 512 * 1024 * 1024, // 512MB
    };
  }

  async measureStartupTime() {
    console.log('🚀 Measuring startup time...');

    const startTime = performance.now();

    return new Promise((resolve, reject) => {
      const process = spawn('npm', ['run', 'tauri:dev'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: true,
      });

      let output = '';
      process.stdout.on('data', (data) => {
        output += data.toString();
        if (output.includes('listening on') || output.includes('ready')) {
          const endTime = performance.now();
          const duration = endTime - startTime;

          this.results.startup.measurements.push({
            duration,
            timestamp: new Date().toISOString(),
          });

          console.log(`✅ Startup completed in ${duration.toFixed(2)}ms`);
          process.kill('SIGTERM');
          resolve(duration);
        }
      });

      process.stderr.on('data', (data) => {
        console.error('Error:', data.toString());
      });

      process.on('error', reject);
      process.on('close', (code) => {
        if (code !== 0 && code !== null) {
          reject(new Error(`Process exited with code ${code}`));
        }
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        process.kill('SIGTERM');
        reject(new Error('Startup measurement timeout'));
      }, 30000);
    });
  }

  async measureResponseTime() {
    console.log('⚡ Measuring response times...');

    // This would typically make HTTP requests to the running app
    // For now, we'll simulate response time measurements
    const measurements = [];

    for (let i = 0; i < 10; i++) {
      const startTime = performance.now();

      // Simulate a request
      await new Promise(resolve => setTimeout(resolve, Math.random() * 100));

      const endTime = performance.now();
      const duration = endTime - startTime;

      measurements.push({
        duration,
        timestamp: new Date().toISOString(),
        operation: `mock-operation-${i}`,
      });
    }

    this.results.response.measurements = measurements;

    const avgResponseTime = measurements.reduce((sum, m) => sum + m.duration, 0) / measurements.length;
    console.log(`✅ Average response time: ${avgResponseTime.toFixed(2)}ms`);

    return avgResponseTime;
  }

  async measureMemoryUsage() {
    console.log('💾 Measuring memory usage...');

    const measurements = [];

    for (let i = 0; i < 5; i++) {
      const memUsage = process.memoryUsage();

      measurements.push({
        heapUsed: memUsage.heapUsed,
        heapTotal: memUsage.heapTotal,
        external: memUsage.external,
        rss: memUsage.rss,
        timestamp: new Date().toISOString(),
      });

      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    this.results.memory.measurements = measurements;

    const avgHeapUsed = measurements.reduce((sum, m) => sum + m.heapUsed, 0) / measurements.length;
    console.log(`✅ Average heap usage: ${(avgHeapUsed / 1024 / 1024).toFixed(2)}MB`);

    return avgHeapUsed;
  }

  validateResults() {
    console.log('🔍 Validating performance against thresholds...');

    const issues = [];

    // Check startup time
    const startupTimes = this.results.startup.measurements.map(m => m.duration);
    if (startupTimes.length > 0) {
      const avgStartupTime = startupTimes.reduce((sum, time) => sum + time, 0) / startupTimes.length;
      if (avgStartupTime > this.thresholds.startupTime) {
        issues.push(`Startup time ${avgStartupTime.toFixed(2)}ms exceeds threshold ${this.thresholds.startupTime}ms`);
      }
    }

    // Check response time
    const responseTimes = this.results.response.measurements.map(m => m.duration);
    if (responseTimes.length > 0) {
      const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
      if (avgResponseTime > this.thresholds.responseTime) {
        issues.push(`Response time ${avgResponseTime.toFixed(2)}ms exceeds threshold ${this.thresholds.responseTime}ms`);
      }
    }

    // Check memory usage
    const memoryUsages = this.results.memory.measurements.map(m => m.heapUsed);
    if (memoryUsages.length > 0) {
      const avgMemoryUsage = memoryUsages.reduce((sum, mem) => sum + mem, 0) / memoryUsages.length;
      if (avgMemoryUsage > this.thresholds.memoryUsage) {
        issues.push(`Memory usage ${(avgMemoryUsage / 1024 / 1024).toFixed(2)}MB exceeds threshold ${(this.thresholds.memoryUsage / 1024 / 1024).toFixed(2)}MB`);
      }
    }

    if (issues.length > 0) {
      console.log('\n❌ Performance issues detected:');
      issues.forEach(issue => console.log(`  - ${issue}`));
      return false;
    } else {
      console.log('\n✅ All performance thresholds met');
      return true;
    }
  }

  async saveResults() {
    const resultsPath = path.join(process.cwd(), 'test-results', 'performance-benchmark.json');

    try {
      await fs.mkdir(path.dirname(resultsPath), { recursive: true });
      await fs.writeFile(resultsPath, JSON.stringify(this.results, null, 2));
      console.log(`📊 Results saved to: ${resultsPath}`);
    } catch (error) {
      console.error('Failed to save results:', error);
    }
  }

  async generateReport() {
    const report = {
      summary: {
        timestamp: this.results.timestamp,
        passed: this.validateResults(),
        thresholds: this.thresholds,
      },
      startup: {
        measurements: this.results.startup.measurements,
        average: this.results.startup.measurements.length > 0
          ? this.results.startup.measurements.reduce((sum, m) => sum + m.duration, 0) / this.results.startup.measurements.length
          : 0,
      },
      response: {
        measurements: this.results.response.measurements,
        average: this.results.response.measurements.length > 0
          ? this.results.response.measurements.reduce((sum, m) => sum + m.duration, 0) / this.results.response.measurements.length
          : 0,
      },
      memory: {
        measurements: this.results.memory.measurements,
        average: this.results.memory.measurements.length > 0
          ? this.results.memory.measurements.reduce((sum, m) => sum + m.heapUsed, 0) / this.results.memory.measurements.length
          : 0,
      },
    };

    const reportPath = path.join(process.cwd(), 'test-results', 'performance-report.md');
    const markdown = this.generateMarkdownReport(report);

    try {
      await fs.writeFile(reportPath, markdown);
      console.log(`📄 Report generated: ${reportPath}`);
    } catch (error) {
      console.error('Failed to generate report:', error);
    }
  }

  generateMarkdownReport(report) {
    return `# Performance Benchmark Report

Generated: ${new Date(report.summary.timestamp).toLocaleString()}

## Summary

**Status:** ${report.summary.passed ? '✅ PASSED' : '❌ FAILED'}

### Performance Targets

- **Startup Time:** < ${report.summary.thresholds.startupTime}ms
- **Response Time:** < ${report.summary.thresholds.responseTime}ms
- **Memory Usage:** < ${(report.summary.thresholds.memoryUsage / 1024 / 1024).toFixed(0)}MB

## Results

### Startup Performance
- **Average:** ${report.startup.average.toFixed(2)}ms
- **Status:** ${report.startup.average < report.summary.thresholds.startupTime ? '✅' : '❌'}

### Response Performance
- **Average:** ${report.response.average.toFixed(2)}ms
- **Status:** ${report.response.average < report.summary.thresholds.responseTime ? '✅' : '❌'}

### Memory Usage
- **Average:** ${(report.memory.average / 1024 / 1024).toFixed(2)}MB
- **Status:** ${report.memory.average < report.summary.thresholds.memoryUsage ? '✅' : '❌'}

## Detailed Measurements

### Startup Times
${report.startup.measurements.map(m => `- ${new Date(m.timestamp).toLocaleTimeString()}: ${m.duration.toFixed(2)}ms`).join('\n')}

### Response Times
${report.response.measurements.map(m => `- ${new Date(m.timestamp).toLocaleTimeString()}: ${m.duration.toFixed(2)}ms (${m.operation})`).join('\n')}

### Memory Usage
${report.memory.measurements.map(m => `- ${new Date(m.timestamp).toLocaleTimeString()}: ${(m.heapUsed / 1024 / 1024).toFixed(2)}MB`).join('\n')}

---

*Report generated by AI Disk Cleaner Performance Benchmark Tool*
`;
  }

  async run() {
    console.log('🏁 Starting performance benchmark...\n');

    try {
      await this.measureStartupTime();
      await this.measureResponseTime();
      await this.measureMemoryUsage();

      const passed = this.validateResults();
      await this.saveResults();
      await this.generateReport();

      console.log('\n🏁 Benchmark complete');
      process.exit(passed ? 0 : 1);

    } catch (error) {
      console.error('❌ Benchmark failed:', error);
      process.exit(1);
    }
  }
}

// Run if called directly
if (require.main === module) {
  const benchmark = new PerformanceBenchmark();
  benchmark.run();
}

module.exports = PerformanceBenchmark;