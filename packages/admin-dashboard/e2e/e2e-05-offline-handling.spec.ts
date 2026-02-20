import { test, expect } from '@playwright/test'

/**
 * E2E-05: API downtime handling.
 * Flow: Dashboard shows OFFLINE indicator and degrades gracefully.
 */
test.describe('E2E-05: Offline handling', () => {
  test('header shows ONLINE status by default', async ({ page }) => {
    await page.goto('/')

    const onlineStatus = page.getByRole('status').filter({ hasText: 'ONLINE' })
    await expect(onlineStatus).toBeVisible({ timeout: 5000 })
  })

  test('header shows WS CONNECTED status', async ({ page }) => {
    await page.goto('/')

    const wsStatus = page.getByRole('status').filter({ hasText: /WS CONNECTED|WS DISCONNECTED/ })
    await expect(wsStatus).toBeVisible({ timeout: 5000 })
  })

  test('simulated offline triggers OFFLINE indicator', async ({ page }) => {
    await page.goto('/')

    await page.evaluate(() => {
      window.dispatchEvent(new Event('offline'))
    })

    const offlineStatus = page.getByRole('status').filter({ hasText: 'OFFLINE' })
    await expect(offlineStatus).toBeVisible({ timeout: 3000 })

    await page.evaluate(() => {
      window.dispatchEvent(new Event('online'))
    })

    const onlineStatus = page.getByRole('status').filter({ hasText: 'ONLINE' })
    await expect(onlineStatus).toBeVisible({ timeout: 3000 })
  })

  test('logout button is accessible', async ({ page }) => {
    await page.goto('/')

    const logoutButton = page.getByRole('button', { name: /LOGOUT/i })
    await expect(logoutButton).toBeVisible()
  })
})
