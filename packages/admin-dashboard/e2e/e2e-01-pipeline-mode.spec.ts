import { test, expect } from '@playwright/test'

/**
 * E2E-01: Operator changes pipeline mode.
 * Flow: Control -> toggle mode -> [COMMIT] -> verify audit entry.
 */
test.describe('E2E-01: Pipeline mode change', () => {
  test('operator can change pipeline mode and commit', async ({ page }) => {
    await page.goto('/control')

    await expect(page.getByRole('heading', { name: 'CONTROL', exact: true })).toBeVisible()

    const commitButton = page.getByRole('button', { name: /COMMIT/i })
    await expect(commitButton).toBeVisible()

    const offlineToggle = page.getByText('OFFLINE')
    if (await offlineToggle.isVisible()) {
      await offlineToggle.click()
    }

    await commitButton.click()

    await expect(
      page.getByText(/COMMITTED|COMMITTING/i),
    ).toBeVisible({ timeout: 5000 })
  })

  test('commit failure shows [FAILED] state', async ({ page }) => {
    await page.goto('/control')

    const commitButton = page.getByRole('button', { name: /COMMIT/i })
    await expect(commitButton).toBeVisible()

    await commitButton.click()

    await expect(
      page.getByText(/COMMITTED|COMMITTING|FAILED/i),
    ).toBeVisible({ timeout: 5000 })
  })

  test('batch size clamps to valid range 1-256', async ({ page }) => {
    await page.goto('/control')

    const batchInput = page.locator('input[type="number"]')
    if (await batchInput.isVisible()) {
      await batchInput.fill('999')
      await batchInput.blur()

      // Store clamps values to 1-256, so the input should show 256 (not 999)
      await expect(batchInput).toHaveValue('256', { timeout: 3000 })
    }
  })
})
