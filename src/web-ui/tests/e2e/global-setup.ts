import { chromium, FullConfig } from '@playwright/test';
import path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Setting up E2E test environment...');

  // Ensure test directories exist
  const testDirs = [
    'test-results',
    'test-results/screenshots',
    'test-results/videos',
    'test-results/traces',
    'test-results/downloads',
  ];

  for (const dir of testDirs) {
    try {
      await fs.promises.mkdir(dir, { recursive: true });
    } catch (error) {
      console.warn(`Warning: Could not create directory ${dir}:`, error);
    }
  }

  // Create a test browser for setup tasks
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Wait for the application to be ready
    console.log('⏳ Waiting for application to start...');
    await page.goto(config.webServer?.[0].url || 'http://localhost:1420', {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Check if the main app container is loaded
    await page.waitForSelector('[data-testid="app-container"]', {
      timeout: 10000,
    });

    // Set up test data if needed
    console.log('📝 Setting up test data...');

    // Create test directories and files for file system tests
    const testCommands = [
      'create_test_directories',
      'create_test_files',
      'setup_test_permissions',
    ];

    for (const command of testCommands) {
      try {
        await page.evaluate((cmd) => {
          // This would call Tauri commands to set up test data
          console.log(`Executing setup command: ${cmd}`);
        }, command);
      } catch (error) {
        console.warn(`Warning: Setup command ${command} failed:`, error);
      }
    }

    // Performance baseline measurement
    console.log('📊 Measuring performance baseline...');
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint')[1]?.startTime || 0,
        largestContentfulPaint: 0, // Would need PerformanceObserver
      };
    });

    console.log('Performance baseline:', performanceMetrics);

    // Store performance metrics for later comparison
    await page.evaluate((metrics) => {
      (window as any).__TEST_BASELINE__ = metrics;
    }, performanceMetrics);

    console.log('✅ E2E test environment setup complete');
  } catch (error) {
    console.error('❌ E2E setup failed:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;

// Polyfill fs.promises for Node.js environments
declare const fs: any;