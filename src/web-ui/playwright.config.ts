import { defineConfig, devices } from '@playwright/test';
import { resolve } from 'path';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['list'],
    process.env.CI ? ['github'] : ['line']
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:1420',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Global timeout for each action */
    actionTimeout: 10 * 1000, // 10 seconds

    /* Global timeout for navigation */
    navigationTimeout: 30 * 1000, // 30 seconds

    /* Ignore HTTPS errors */
    ignoreHTTPSErrors: true,

    /* User agent */
    userAgent: 'AI-Disk-Cleanup-E2E-Tests',

    /* Viewport size */
    viewport: { width: 1280, height: 720 },

    /* Color scheme preference */
    colorScheme: 'light',

    /* Locale */
    locale: 'en-US',

    /* Timezone */
    timezoneId: 'America/New_York',

    /* Geolocation */
    geolocation: { longitude: -122.4194, latitude: 37.7749 }, // San Francisco

    /* Permissions */
    permissions: ['clipboard-read', 'clipboard-write'],
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testMatch: '**/chromium/*.spec.ts',
      dependencies: ['setup'],
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testMatch: '**/firefox/*.spec.ts',
      dependencies: ['setup'],
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testMatch: '**/webkit/*.spec.ts',
      dependencies: ['setup'],
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testMatch: '**/mobile/*.spec.ts',
      dependencies: ['setup'],
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      testMatch: '**/mobile/*.spec.ts',
      dependencies: ['setup'],
    },

    /* Test against branded browsers. */
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
      testMatch: '**/edge/*.spec.ts',
      dependencies: ['setup'],
    },

    /* Setup project for global teardown/setup */
    {
      name: 'setup',
      testMatch: '**/setup.spec.ts',
      teardown: 'teardown',
    },

    /* Teardown project */
    {
      name: 'teardown',
      testMatch: '**/teardown.spec.ts',
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:1420',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000, // 2 minutes
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run tauri:dev',
      url: 'http://localhost:1420',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000, // 2 minutes
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],

  /* Global setup and teardown */
  globalSetup: require.resolve('./tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./tests/e2e/global-teardown.ts'),

  /* Test timeout */
  timeout: 60 * 1000, // 60 seconds

  /* Expect timeout */
  expect: {
    timeout: 10 * 1000, // 10 seconds
  },

  /* Output directory */
  outputDir: 'test-results/',

  /* Metadata */
  metadata: {
    'Test Environment': 'E2E',
    'Test Type': 'Cross-platform',
    'Application': 'AI Disk Cleaner',
    'Version': '0.2.0',
  },

  /* Define custom test matchers */
  define: {
    CUSTOM_CONFIG: JSON.stringify({
      APP_VERSION: '0.2.0',
      PERFORMANCE_THRESHOLD: 100, // ms
      STARTUP_TIMEOUT: 2000, // ms
    }),
  },
});