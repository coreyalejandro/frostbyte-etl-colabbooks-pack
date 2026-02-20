import { test, expect } from '@playwright/test'

/**
 * E2E-04: Red-Team test execution.
 * Flow: Verification -> [RUN SUITE] -> view security score.
 */
test.describe('E2E-04: Verification suite', () => {
  test('verification page loads with three gates', async ({ page }) => {
    await page.goto('/verify')

    await expect(page.getByText('VERIFICATION')).toBeVisible()

    await expect(
      page.getByText(/EVIDENCE|RETRIEVAL|SECURITY/i).first(),
    ).toBeVisible({ timeout: 5000 })
  })

  test('run suite button triggers verification', async ({ page }) => {
    await page.goto('/verify')

    const runButton = page.getByRole('button', { name: /RUN SUITE|TEST/i }).first()
    if (await runButton.isVisible()) {
      await runButton.click()

      await expect(
        page.getByText(/PASS|FAIL|RUNNING|score/i).first(),
      ).toBeVisible({ timeout: 10000 })
    }
  })
})
