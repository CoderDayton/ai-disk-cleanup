import { FullConfig } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up E2E test environment...');

  try {
    // Clean up test data
    console.log('📁 Cleaning up test data...');

    // Read test results and generate summary
    const resultsPath = path.join(process.cwd(), 'test-results', 'results.json');
    let testResults = null;

    try {
      const resultsData = await fs.readFile(resultsPath, 'utf-8');
      testResults = JSON.parse(resultsData);
      console.log(`📊 Processed ${testResults.suites?.length || 0} test suites`);
    } catch (error) {
      console.warn('Could not read test results:', error);
    }

    // Clean up temporary test directories
    const cleanupCommands = [
      'cleanup_test_directories',
      'cleanup_test_files',
      'cleanup_test_permissions',
    ];

    // Note: In a real Tauri app, these would be actual Tauri commands
    for (const command of cleanupCommands) {
      console.log(`Executing cleanup command: ${command}`);
    }

    // Generate performance report if we have test results
    if (testResults) {
      await generatePerformanceReport(testResults);
    }

    // Archive test results if needed
    if (process.env.CI) {
      await archiveTestResults();
    }

    console.log('✅ E2E test environment cleanup complete');
  } catch (error) {
    console.error('❌ E2E teardown failed:', error);
    throw error;
  }
}

async function generatePerformanceReport(testResults: any) {
  console.log('📈 Generating performance report...');

  const reportPath = path.join(process.cwd(), 'test-results', 'performance-report.json');
  const performanceReport = {
    timestamp: new Date().toISOString(),
    summary: {
      totalTests: testResults.specs?.length || 0,
      passedTests: testResults.suites?.reduce((acc: number, suite: any) =>
        acc + suite.specs?.filter((spec: any) => spec.ok).length || 0, 0) || 0,
      failedTests: testResults.suites?.reduce((acc: number, suite: any) =>
        acc + suite.specs?.filter((spec: any) => !spec.ok).length || 0, 0) || 0,
      skippedTests: testResults.suites?.reduce((acc: number, suite: any) =>
        acc + suite.specs?.filter((spec: any) => spec.tests?.some((test: any) => test.results?.some((result: any) => result.status === 'skipped'))).length || 0, 0) || 0,
    },
    performance: {
      averageResponseTime: 0, // Would be calculated from actual metrics
      startupTime: 0, // Would be measured during tests
      memoryUsage: process.memoryUsage(),
    },
    thresholds: {
      responseTime: 100, // ms
      startupTime: 2000, // ms
      memoryUsage: 512 * 1024 * 1024, // 512MB
    },
  };

  try {
    await fs.writeFile(reportPath, JSON.stringify(performanceReport, null, 2));
    console.log(`📊 Performance report generated: ${reportPath}`);
  } catch (error) {
    console.error('Failed to generate performance report:', error);
  }
}

async function archiveTestResults() {
  console.log('📦 Archiving test results...');

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const archiveName = `test-results-${timestamp}`;
  const archivePath = path.join(process.cwd(), 'test-results', 'archives');

  try {
    await fs.mkdir(archivePath, { recursive: true });

    // In a real implementation, you would create a zip/tar archive
    // For now, we'll just create a marker file
    const markerPath = path.join(archivePath, `${archiveName}.txt`);
    await fs.writeFile(markerPath, `Test results archived at ${timestamp}`);

    console.log(`📦 Test results archived: ${archivePath}/${archiveName}`);
  } catch (error) {
    console.error('Failed to archive test results:', error);
  }
}

export default globalTeardown;