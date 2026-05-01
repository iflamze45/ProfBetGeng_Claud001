import { test, expect } from '@playwright/test'

function setupMocks(page) {
  return Promise.all([
    page.route('/api/v1/keys', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ key: 'test-api-key-123', label: 'test' }),
      })
    }),
    page.route('/api/v1/history', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ records: [], count: 0 }),
      })
    }),
    page.route('/api/v1/quant/arbs', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ windows: [] }),
      })
    }),
  ])
}

async function goToConvertTab(page) {
  await setupMocks(page)
  await page.goto('http://localhost:5299', { waitUntil: 'domcontentloaded' })
  await page.locator('nav button', { hasText: 'MATRIX_CONVERT' }).click()
  await expect(page.getByText('Matrix Translation')).toBeVisible({ timeout: 10000 })
}

test.describe('Core Convert Flow', () => {
  test('renders the conversion UI', async ({ page }) => {
    await goToConvertTab(page)
    await expect(page.getByText('Matrix Translation')).toBeVisible()
  })

  test('shows error on empty submission', async ({ page }) => {
    await goToConvertTab(page)
    const btn = page.locator('button', { hasText: 'Execute Bridge Translation' })
    await expect(btn).toBeDisabled()
  })

  test('convert flow succeeds with valid input', async ({ page }) => {
    await page.route('/api/v1/convert', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          converted: {
            source_booking_code: 'WEB-TEST',
            target_platform: 'bet9ja',
            selections: [
              { event_id: '1', event_name: 'Arsenal vs Chelsea', market: '1X2', pick: 'Home', odds: 2.10, original_market: '1X2' },
            ],
            converted_count: 1,
            skipped_count: 0,
            total_odds: 2.10,
            warnings: [],
          },
          analysis: null,
        }),
      })
    })

    await page.route('/api/v1/analyse/stream', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: [DONE]\n\n',
      })
    })

    await goToConvertTab(page)

    const textarea = page.locator('textarea')
    await textarea.fill('Arsenal vs Chelsea | 1X2 | Home | 2.10')

    const btn = page.locator('button', { hasText: 'Execute Bridge Translation' })
    await btn.click()

    await expect(page.getByText('Conversion Complete')).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('cell', { name: 'Arsenal vs Chelsea' })).toBeVisible()
  })
})
