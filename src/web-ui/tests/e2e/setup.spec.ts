import { test, expect } from './fixtures/test-app';

test.describe('E2E Test Environment Setup', () => {
  test('should have application running', async ({ page }) => {
    await page.goto('/');

    // Check if the main application is loaded
    await expect(page.locator('[data-testid="app-container"]')).toBeVisible();

    // Check if critical UI elements are present
    await expect(page.locator('[data-testid="app-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
  });

  test('should meet performance thresholds', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // Should load within 2 seconds
    expect(loadTime).toBeLessThan(2000);

    // Check performance metrics
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint')[1]?.startTime || 0,
      };
    });

    // First contentful paint should be under 1 second
    expect(metrics.firstContentfulPaint).toBeLessThan(1000);

    console.log('Performance metrics:', metrics);
  });

  test('should have proper theme variables', async ({ page }) => {
    await page.goto('/');

    const themeVariables = await page.evaluate(() => {
      const styles = getComputedStyle(document.documentElement);
      return {
        background: styles.getPropertyValue('--background'),
        foreground: styles.getPropertyValue('--foreground'),
        primary: styles.getPropertyValue('--primary'),
        primaryForeground: styles.getPropertyValue('--primary-foreground'),
      };
    });

    // Should have theme variables defined
    expect(themeVariables.background).toBeTruthy();
    expect(themeVariables.foreground).toBeTruthy();
    expect(themeVariables.primary).toBeTruthy();
    expect(themeVariables.primaryForeground).toBeTruthy();
  });

  test('should handle responsive design', async ({ page }) => {
    await page.goto('/');

    // Test desktop viewport
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('[data-testid="desktop-layout"]')).toBeVisible();

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('[data-testid="mobile-layout"]')).toBeVisible();
  });

  test('should have accessibility attributes', async ({ page }) => {
    await page.goto('/');

    // Check for proper ARIA attributes
    await expect(page.locator('main')).toHaveAttribute('role', 'main');
    await expect(page.locator('[data-testid="skip-to-content"]')).toBeVisible();

    // Check keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
  });
});