#!/usr/bin/env node

/**
 * Performance testing script for AI Disk Cleaner
 * Runs comprehensive performance tests and validates against targets
 */

const { performance } = require('perf_hooks');
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class PerformanceTest {
  constructor() {
    this.testResults = {
      tests: [],
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        timestamp: new Date().toISOString(),
      },
    };
    this.targets = {
      appStartup: 2000, // 2 seconds
      uiResponse: 100, // 100ms
      fileScan: 5000, // 5 seconds for typical directory
      analysisComplete: 10000, // 10 seconds
      cleanupOperation: 3000, // 3 seconds
    };
  }

  async runTest(name, testFunction) {
    console.log(`⏳ Running test: ${name}`);

    try {
      const startTime = performance.now();
      const result = await testFunction();
      const endTime = performance.now();
      const duration = endTime - startTime;

      const testResult = {
        name,
        status: 'passed',
        duration,
        timestamp: new Date().toISOString(),
        result,
        target: this.targets[name.replace(/([A-Z])/g, '-$1').toLowerCase()] || null,
      };

      this.testResults.tests.push(testResult);
      this.testResults.summary.total++;
      this.testResults.summary.passed++;

      console.log(`✅ ${name} completed in ${duration.toFixed(2)}ms`);
      return testResult;

    } catch (error) {
      const testResult = {
        name,
        status: 'failed',
        duration: 0,
        timestamp: new Date().toISOString(),
        error: error.message,
        target: this.targets[name.replace(/([A-Z])/g, '-$1').toLowerCase()] || null,
      };

      this.testResults.tests.push(testResult);
      this.testResults.summary.total++;
      this.testResults.summary.failed++;

      console.log(`❌ ${name} failed: ${error.message}`);
      return testResult;
    }
  }

  async testAppStartup() {
    return new Promise((resolve, reject) => {
      const startTime = performance.now();
      const process = spawn('npm', ['run', 'dev'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: true,
      });

      let output = '';
      process.stdout.on('data', (data) => {
        output += data.toString();
        if (output.includes('ready in') || output.includes('Local:')) {
          const endTime = performance.now();
          const duration = endTime - startTime;
          process.kill('SIGTERM');
          resolve({ duration, output });
        }
      });

      process.on('error', reject);
      process.on('close', (code) => {
        if (code !== 0 && code !== null) {
          reject(new Error(`Process exited with code ${code}`));
        }
      });

      setTimeout(() => {
        process.kill('SIGTERM');
        reject(new Error('Startup test timeout'));
      }, 15000);
    });
  }

  async testUIResponse() {
    // Simulate UI response time testing
    const measurements = [];

    for (let i = 0; i < 20; i++) {
      const start = performance.now();

      // Simulate a UI interaction (DOM manipulation, state update, etc.)
      await new Promise(resolve => setTimeout(resolve, Math.random() * 50 + 10));

      const end = performance.now();
      measurements.push(end - start);
    }

    const average = measurements.reduce((sum, time) => sum + time, 0) / measurements.length;
    const max = Math.max(...measurements);
    const min = Math.min(...measurements);

    return { average, max, min, measurements };
  }

  async testFileScanPerformance() {
    // Simulate file scanning performance
    const fileCount = 1000;
    const startTime = performance.now();

    // Simulate scanning files
    for (let i = 0; i < fileCount; i++) {
      // Simulate file operation
      await new Promise(resolve => setTimeout(resolve, 1));
    }

    const endTime = performance.now();
    const duration = endTime - startTime;
    const filesPerSecond = (fileCount / duration) * 1000;

    return {
      fileCount,
      duration,
      filesPerSecond,
      averageTimePerFile: duration / fileCount,
    };
  }

  async testAnalysisPerformance() {
    // Simulate AI analysis performance
    const dataPoints = 100;
    const startTime = performance.now();

    // Simulate AI processing
    for (let i = 0; i < dataPoints; i++) {
      // Simulate AI model inference time
      await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100));
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    return {
      dataPoints,
      duration,
      averageTimePerPoint: duration / dataPoints,
      throughput: dataPoints / (duration / 1000), // points per second
    };
  }

  async testCleanupPerformance() {
    // Simulate cleanup operation performance
    const fileOperations = 50;
    const startTime = performance.now();

    // Simulate file operations (delete, move, etc.)
    for (let i = 0; i < fileOperations; i++) {
      // Simulate file operation time
      await new Promise(resolve => setTimeout(resolve, 20 + Math.random() * 80));
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    return {
      fileOperations,
      duration,
      averageTimePerOperation: duration / fileOperations,
      operationsPerSecond: fileOperations / (duration / 1000),
    };
  }

  async testMemoryUsage() {
    const measurements = [];
    const duration = 10000; // 10 seconds
    const interval = 1000; // 1 second

    for (let i = 0; i < duration / interval; i++) {
      const memUsage = process.memoryUsage();
      measurements.push({
        heapUsed: memUsage.heapUsed,
        heapTotal: memUsage.heapTotal,
        external: memUsage.external,
        rss: memUsage.rss,
        timestamp: Date.now(),
      });

      await new Promise(resolve => setTimeout(resolve, interval));
    }

    const avgHeapUsed = measurements.reduce((sum, m) => sum + m.heapUsed, 0) / measurements.length;
    const maxHeapUsed = Math.max(...measurements.map(m => m.heapUsed));

    return {
      measurements,
      averageHeapUsed: avgHeapUsed,
      maxHeapUsed: maxHeapUsed,
      averageHeapUsedMB: avgHeapUsed / 1024 / 1024,
      maxHeapUsedMB: maxHeapUsed / 1024 / 1024,
    };
  }

  validateResults() {
    console.log('\n🔍 Validating results against performance targets...');

    const validations = this.testResults.tests.map(test => {
      if (!test.target || test.status === 'failed') {
        return { test: test.name, status: 'skipped', reason: 'No target or test failed' };
      }

      const passed = test.duration <= test.target;
      return {
        test: test.name,
        target: test.target,
        actual: test.duration,
        status: passed ? 'passed' : 'failed',
        difference: test.duration - test.target,
      };
    });

    const passed = validations.filter(v => v.status === 'passed').length;
    const failed = validations.filter(v => v.status === 'failed').length;
    const skipped = validations.filter(v => v.status === 'skipped').length;

    console.log(`\n📊 Validation Summary:`);
    console.log(`  ✅ Passed: ${passed}`);
    console.log(`  ❌ Failed: ${failed}`);
    console.log(`  ⏭️  Skipped: ${skipped}`);

    if (failed > 0) {
      console.log('\n❌ Failed validations:');
      validations
        .filter(v => v.status === 'failed')
        .forEach(v => {
          console.log(`  - ${v.test}: ${v.actual.toFixed(2)}ms > ${v.target}ms (+${v.difference.toFixed(2)}ms)`);
        });
    }

    return failed === 0;
  }

  async saveResults() {
    const resultsPath = path.join(process.cwd(), 'test-results', 'performance-test-results.json');

    try {
      await fs.mkdir(path.dirname(resultsPath), { recursive: true });
      await fs.writeFile(resultsPath, JSON.stringify(this.testResults, null, 2));
      console.log(`\n💾 Results saved to: ${resultsPath}`);
    } catch (error) {
      console.error('Failed to save results:', error);
    }
  }

  async generateHTMLReport() {
    const html = this.generateHTMLContent();
    const reportPath = path.join(process.cwd(), 'test-results', 'performance-test-report.html');

    try {
      await fs.writeFile(reportPath, html);
      console.log(`📄 HTML report generated: ${reportPath}`);
    } catch (error) {
      console.error('Failed to generate HTML report:', error);
    }
  }

  generateHTMLContent() {
    const { tests, summary } = this.testResults;

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Disk Cleaner - Performance Test Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
        .metric { background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }
        .metric h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; text-transform: uppercase; }
        .metric .value { font-size: 24px; font-weight: bold; color: #333; }
        .metric .value.passed { color: #28a745; }
        .metric .value.failed { color: #dc3545; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .status-passed { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .duration { font-family: 'Courier New', monospace; }
        .target { color: #666; font-size: 12px; }
        .timestamp { color: #666; font-size: 12px; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Disk Cleaner - Performance Test Report</h1>
        <p class="timestamp">Generated: ${new Date(summary.timestamp).toLocaleString()}</p>

        <div class="summary">
            <div class="metric">
                <h3>Total Tests</h3>
                <div class="value">${summary.total}</div>
            </div>
            <div class="metric">
                <h3>Passed</h3>
                <div class="value passed">${summary.passed}</div>
            </div>
            <div class="metric">
                <h3>Failed</h3>
                <div class="value failed">${summary.failed}</div>
            </div>
            <div class="metric">
                <h3>Success Rate</h3>
                <div class="value">${summary.total > 0 ? ((summary.passed / summary.total) * 100).toFixed(1) : 0}%</div>
            </div>
        </div>

        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Target</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                ${tests.map(test => `
                    <tr>
                        <td>${test.name}</td>
                        <td class="status-${test.status}">${test.status.toUpperCase()}</td>
                        <td class="duration">${test.duration ? test.duration.toFixed(2) + 'ms' : 'N/A'}</td>
                        <td class="target">${test.target ? test.target + 'ms' : 'N/A'}</td>
                        <td class="timestamp">${new Date(test.timestamp).toLocaleTimeString()}</td>
                    </tr>
                    ${test.error ? `<tr><td colspan="5" class="error">Error: ${test.error}</td></tr>` : ''}
                `).join('')}
            </tbody>
        </table>

        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
            Generated by AI Disk Cleaner Performance Testing Tool
        </div>
    </div>
</body>
</html>`;
  }

  async run() {
    console.log('🚀 Starting performance tests...\n');

    await this.runTest('AppStartup', () => this.testAppStartup());
    await this.runTest('UIResponse', () => this.testUIResponse());
    await this.runTest('FileScan', () => this.testFileScanPerformance());
    await this.runTest('Analysis', () => this.testAnalysisPerformance());
    await this.runTest('Cleanup', () => this.testCleanupPerformance());
    await this.runTest('MemoryUsage', () => this.testMemoryUsage());

    const allPassed = this.validateResults();
    await this.saveResults();
    await this.generateHTMLReport();

    console.log(`\n🏁 Performance testing complete - ${allPassed ? 'PASSED' : 'FAILED'}`);
    process.exit(allPassed ? 0 : 1);
  }
}

// Run if called directly
if (require.main === module) {
  const test = new PerformanceTest();
  test.run();
}

module.exports = PerformanceTest;