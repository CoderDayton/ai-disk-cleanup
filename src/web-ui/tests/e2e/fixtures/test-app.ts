import { test as base, Page, BrowserContext, Browser } from '@playwright/test';
import { createMockFileSystem } from '../utils/test-helpers';

// Define test fixtures
export interface TestFixtures {
  authenticatedPage: Page;
  testFileSystem: any;
  mockResponses: Record<string, any>;
}

// Extend base test with custom fixtures
export const test = base.extend<TestFixtures>({
  // Authenticated page fixture
  authenticatedPage: async ({ page, context }, use) => {
    // Mock authentication
    await context.route('**/api/auth/status', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: true,
          user: { id: 'test-user', name: 'Test User' },
        }),
      });
    });

    // Mock user data
    await context.route('**/api/user/profile', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-user',
          name: 'Test User',
          email: 'test@example.com',
          preferences: {
            theme: 'light',
            language: 'en',
          },
        }),
      });
    });

    await use(page);
  },

  // Mock file system fixture
  testFileSystem: async ({}, use) => {
    const mockFs = createMockFileSystem({
      '/home/test/Documents': {
        type: 'directory',
        files: [
          { name: 'document1.pdf', size: 1024 * 1024, type: 'file' },
          { name: 'document2.txt', size: 1024, type: 'file' },
        ],
      },
      '/home/test/Downloads': {
        type: 'directory',
        files: [
          { name: 'installer.exe', size: 50 * 1024 * 1024, type: 'file' },
          { name: 'image.png', size: 2 * 1024 * 1024, type: 'file' },
        ],
      },
    });

    await use(mockFs);
  },

  // Mock API responses fixture
  mockResponses: async ({ page }, use) => {
    const responses: Record<string, any> = {};

    // Mock file system API
    await page.route('**/api/filesystem/**', (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace('/api/filesystem', '');

      if (responses[path]) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(responses[path]),
        });
      } else {
        route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Path not found' }),
        });
      }
    });

    // Mock analysis API
    await page.route('**/api/analysis/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-analysis',
          status: 'completed',
          results: {
            totalFiles: 100,
            totalSize: 1024 * 1024 * 100, // 100MB
            duplicates: 20,
            largeFiles: 5,
            oldFiles: 10,
          },
        }),
      });
    });

    // Mock cleanup API
    await page.route('**/api/cleanup/**', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-cleanup',
          status: 'completed',
          filesDeleted: 10,
          spaceFreed: 50 * 1024 * 1024, // 50MB
        }),
      });
    });

    await use(responses);
  },
});

// Re-export commonly used test utilities
export { expect } from '@playwright/test';
export { Page, BrowserContext, Browser } from '@playwright/test';

// Custom test helpers
export class AppPage {
  constructor(public page: Page) {}

  // Navigation helpers
  async goto(path = '/') {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  async navigateToTab(tabName: string) {
    await this.page.click(`[data-testid="tab-${tabName}"]`);
    await this.page.waitForSelector(`[data-testid="tab-content-${tabName}"]`);
  }

  // File system helpers
  async selectDirectory(path: string) {
    await this.page.click('[data-testid="directory-selector"]');
    await this.page.fill('[data-testid="directory-input"]', path);
    await this.page.click('[data-testid="directory-confirm"]');
    await this.page.waitForSelector(`[data-testid="directory-selected"][data-path="${path}"]`);
  }

  async startAnalysis() {
    await this.page.click('[data-testid="start-analysis"]');
    await this.page.waitForSelector('[data-testid="analysis-progress"]');
    await this.page.waitForSelector('[data-testid="analysis-results"]', { timeout: 30000 });
  }

  async selectFile(fileName: string) {
    await this.page.click(`[data-testid="file-item"][data-name="${fileName}"] [data-testid="file-checkbox"]`);
  }

  async deleteSelectedFiles() {
    await this.page.click('[data-testid="delete-selected"]');
    await this.page.click('[data-testid="confirm-delete"]');
    await this.page.waitForSelector('[data-testid="delete-progress"]');
    await this.page.waitForSelector('[data-testid="delete-complete"]', { timeout: 30000 });
  }

  // Performance helpers
  async measurePageLoad() {
    const metrics = await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint')[1]?.startTime || 0,
      };
    });
    return metrics;
  }

  async waitForComponentLoad(componentTestid: string, timeout = 5000) {
    await this.page.waitForSelector(`[data-testid="${componentTestid}"]`, { timeout });
  }

  async measureInteractionTime(action: () => Promise<void>) {
    const start = Date.now();
    await action();
    const end = Date.now();
    return end - start;
  }

  // Validation helpers
  async expectElementToBeVisible(testid: string) {
    await this.page.waitForSelector(`[data-testid="${testid}"]`);
    const element = this.page.locator(`[data-testid="${testid}"]`);
    await expect(element).toBeVisible();
  }

  async expectElementToContainText(testid: string, text: string) {
    const element = this.page.locator(`[data-testid="${testid}"]`);
    await expect(element).toContainText(text);
  }

  async expectButtonToBeEnabled(testid: string) {
    const button = this.page.locator(`[data-testid="${testid}"]`);
    await expect(button).toBeEnabled();
  }

  async expectButtonToBeDisabled(testid: string) {
    const button = this.page.locator(`[data-testid="${testid}"]`);
    await expect(button).toBeDisabled();
  }
}