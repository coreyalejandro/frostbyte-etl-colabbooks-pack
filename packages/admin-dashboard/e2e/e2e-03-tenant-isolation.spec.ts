import { test, expect } from '@playwright/test'

/**
 * E2E-03: Tenant isolation inspection.
 * Flow: Tenants -> click chamber -> focused view -> verify network barriers.
 */
test.describe('E2E-03: Tenant isolation', () => {
  test('tenant list loads with mock tenants', async ({ page }) => {
    await page.goto('/tenants')

    // TenantChambers renders "TENANT-01" (from PROD-01.replace('PROD-', ''))
    await expect(
      page.getByText(/TENANT-01|TENANT-02/i).first(),
    ).toBeVisible({ timeout: 5000 })
  })

  test('clicking a tenant navigates to detail', async ({ page }) => {
    await page.goto('/tenants')

    // TenantChambers renders buttons with "TENANT-01" text
    const tenantButton = page.getByText(/TENANT-01/i).first()
    await tenantButton.click()

    await expect(page).toHaveURL(/tenants\//, { timeout: 5000 })
  })

  test('tenant detail view shows isolation boundary', async ({ page }) => {
    await page.goto('/tenants/PROD-01/detail')

    // TenantDetailView renders "TENANT: PROD-01" and "NETWORK ISOLATION BOUNDARY"
    await expect(
      page.getByText(/TENANT.*PROD-01|NETWORK ISOLATION/i).first(),
    ).toBeVisible({ timeout: 5000 })
  })

  test('tenant detail view renders pipeline DAG', async ({ page }) => {
    await page.goto('/tenants/PROD-01/detail')

    const dagContainer = page.locator('.react-flow')
    await expect(dagContainer).toBeVisible({ timeout: 10000 })
  })
})
