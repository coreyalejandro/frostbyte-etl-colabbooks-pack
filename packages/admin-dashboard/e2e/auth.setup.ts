import { test as setup, expect } from '@playwright/test'

/**
 * Shared authentication setup: logs in once and stores state
 * for all E2E tests to reuse. Mock mode accepts any non-empty key.
 */
setup('authenticate', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByText('FROSTBYTE ADMIN')).toBeVisible()

  await page.getByLabel('Admin API Key').fill('test-admin-key')
  await page.getByRole('button', { name: '[SIGN IN]' }).click()

  await page.waitForURL('/')
  await expect(page.getByText('[LOGOUT]')).toBeVisible()

  await page.context().storageState({ path: './e2e/.auth/state.json' })
})
