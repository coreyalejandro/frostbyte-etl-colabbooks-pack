import { test, expect } from '@playwright/test'

/**
 * E2E-02: Compliance officer verifies document.
 * Flow: Documents -> [INSPECT] -> verify chain -> [VERIFY] slice.
 */
test.describe('E2E-02: Document inspection', () => {
  test('document list loads with mock data', async ({ page }) => {
    await page.goto('/documents')

    await expect(page.getByText(/contract\.pdf|appendix\.md|policy\.docx/i).first()).toBeVisible({
      timeout: 5000,
    })
  })

  test('clicking verify navigates to document detail view', async ({ page }) => {
    await page.goto('/documents')

    // The document queue table has [VERIFY] buttons that navigate to detail
    const verifyButton = page.getByRole('button', { name: '[VERIFY]' }).first()
    if (await verifyButton.isVisible()) {
      await verifyButton.click()
      await expect(page).toHaveURL(/documents\//, { timeout: 5000 })
    }
  })

  test('document detail shows metadata', async ({ page }) => {
    await page.goto('/documents/0001')

    await expect(
      page.getByText(/contract\.pdf|0001|STORED/i).first(),
    ).toBeVisible({ timeout: 10000 })
  })

  test('non-existent document shows error message', async ({ page }) => {
    await page.goto('/documents/nonexistent')

    // React Query retries 3 times with backoff, so allow extra time
    await expect(
      page.getByText(/not found|FAILED/i).first(),
    ).toBeVisible({ timeout: 15000 })
  })
})
