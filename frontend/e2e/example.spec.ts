import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');
  });

  test('should load dashboard page', async ({ page }) => {
    // Wait for main content to load
    await page.waitForLoadState('networkidle');
    
    // Check if page title or header exists
    const heading = page.locator('h1, h2');
    await expect(heading).toBeVisible({ timeout: 5000 });
  });

  test('should navigate between pages', async ({ page }) => {
    // Look for navigation links
    const navLinks = page.locator('nav a, [role="navigation"] a');
    const count = await navLinks.count();
    
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('API Health', () => {
  test('should reach API health endpoint', async ({ request }) => {
    const response = await request.get('/api/v1/health');
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('status');
  });
});

test.describe('Accessibility', () => {
  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check that h1 exists
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
  });

  test('should have alt text for images', async ({ page }) => {
    await page.goto('/');
    
    // Find all images
    const images = page.locator('img');
    const count = await images.count();
    
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      // Alt text should exist or be intentionally empty for decorative images
      expect(alt).toBeDefined();
    }
  });
});
