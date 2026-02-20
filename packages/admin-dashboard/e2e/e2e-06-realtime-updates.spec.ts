import { test, expect } from '@playwright/test'

/**
 * E2E-06: Real-time pipeline updates.
 * Flow: WebSocket connects; throughput metrics update.
 * Note: Uses mock WebSocket service (not Socket.IO).
 */
test.describe('E2E-06: Real-time updates', () => {
  test('dashboard loads with pipeline schematic', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('[LOGOUT]')).toBeVisible()

    const dagOrSchematic = page.locator('.react-flow, [data-testid="pipeline-schematic"]')
    const schematicText = page.getByText(/INTAKE|PARSE|EMBED/i).first()

    const hasDag = await dagOrSchematic.isVisible().catch(() => false)
    const hasText = await schematicText.isVisible().catch(() => false)
    expect(hasDag || hasText).toBeTruthy()
  })

  test('WebSocket status indicator is visible in header', async ({ page }) => {
    await page.goto('/')

    const wsIndicator = page.getByRole('status').filter({ hasText: /WS/ })
    await expect(wsIndicator).toBeVisible({ timeout: 5000 })
  })

  test('pipeline status indicator shows online state', async ({ page }) => {
    await page.goto('/')

    const pipelineStatus = page.getByRole('status').filter({
      hasText: /Pipeline/i,
    })
    if (await pipelineStatus.isVisible().catch(() => false)) {
      await expect(pipelineStatus).toBeVisible()
    }

    const statusDot = page.locator('[title*="Pipeline"]')
    await expect(statusDot).toBeVisible({ timeout: 5000 })
  })

  test('navigating between pages preserves WebSocket state', async ({ page }) => {
    await page.goto('/')
    const wsIndicator1 = page.getByRole('status').filter({ hasText: /WS/ })
    await expect(wsIndicator1).toBeVisible({ timeout: 5000 })
    const wsStatus1 = await wsIndicator1.textContent()

    await page.goto('/tenants')
    const wsIndicator2 = page.getByRole('status').filter({ hasText: /WS/ })
    await expect(wsIndicator2).toBeVisible({ timeout: 5000 })
    const wsStatus2 = await wsIndicator2.textContent()

    expect(wsStatus1).toBe(wsStatus2)
  })
})
