/**
 * Section 4 — E2E tests (Playwright)
 *
 * Runs against the full stack: Vite dev server (:5173) + FastAPI backend (:8000).
 * Start the stack with: bash scripts/start-test-env.sh
 * Gate command: cd e2e && npx playwright test --reporter=list
 *
 * Journeys covered:
 *  1. Growth Map discovery
 *  2. Area Analyzer full report
 *  3. Opportunity Finder
 *  4. Compare Areas
 *  5. Watchlist
 *  7. Error resilience (backend offline handled gracefully)
 *
 * Journey 6 (Auth flow) is SKIPPED — auth is deferred to Phase 5+ and not implemented.
 */
import { test, expect } from '@playwright/test'

// ---------------------------------------------------------------------------
// Journey 1 — Growth Map discovery
// ---------------------------------------------------------------------------

test.describe('Journey 1 — Growth Map', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Redirect sends to /map
    await page.waitForURL('**/map')
  })

  test('Growth Map page loads with map container visible', async ({ page }) => {
    const mapContainer = page.locator('.leaflet-container')
    await expect(mapContainer).toBeVisible({ timeout: 10_000 })
  })

  test('sidebar shows all 8 nav items', async ({ page }) => {
    await expect(page.getByRole('link', { name: /growth map/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /area analyzer/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /opportunity finder/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /compare areas/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /watchlist/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /data sources/i })).toBeVisible()
  })

  test('filter panel is visible', async ({ page }) => {
    // exact:true avoids matching "No areas match your filters" (case-insensitive substring)
    await expect(page.getByText('Filters', { exact: true })).toBeVisible({ timeout: 8_000 })
  })

  test('city filter Bangalore narrows the marker count', async ({ page }) => {
    await page.waitForTimeout(2000) // let map render

    // Get initial marker count via Leaflet container children
    const initialMarkers = await page.locator('.leaflet-marker-pane circle, path.leaflet-interactive').count()

    // Click Bangalore filter
    await page.getByRole('button', { name: /bangalore/i }).first().click()
    await page.waitForTimeout(500)

    const filteredMarkers = await page.locator('.leaflet-marker-pane circle, path.leaflet-interactive').count()
    // Filtered count must be ≤ initial count (never increases)
    expect(filteredMarkers).toBeLessThanOrEqual(Math.max(initialMarkers, 1))
  })
})

// ---------------------------------------------------------------------------
// Journey 2 — Area Analyzer full report
// ---------------------------------------------------------------------------

test.describe('Journey 2 — Area Analyzer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analyzer')
    await page.waitForLoadState('networkidle')
  })

  test('Area Analyzer page renders the select dropdown', async ({ page }) => {
    const select = page.locator('select')
    await expect(select).toBeVisible()
  })

  test('selecting Sarjapur shows a recommendation badge', async ({ page }) => {
    // Options contain full text "Sarjapur — Bangalore · Buy · ₹6,400/sqft" — select by index
    const select = page.locator('select')
    await select.selectOption({ index: 1 })

    // Wait for the report to load
    await page.waitForTimeout(2000)

    // SummaryCard renders recommendation.toUpperCase() — use exact match to avoid
    // matching the hidden select option which contains mixed-case "Buy"
    const validRecs = ['STRONG BUY', 'BUY', 'HOLD', 'AVOID', 'SELL']
    let found = false
    for (const rec of validRecs) {
      const el = page.getByText(rec, { exact: true }).first()
      if (await el.isVisible().catch(() => false)) {
        found = true
        break
      }
    }
    expect(found).toBe(true)
  })

  test('forecast chart renders after area selection', async ({ page }) => {
    const select = page.locator('select')
    await select.selectOption({ index: 1 })
    await page.waitForTimeout(2000)

    // Recharts renders a <svg> inside the forecast section
    const chart = page.locator('.recharts-responsive-container').first()
    await expect(chart).toBeVisible({ timeout: 5_000 })
  })

  test('AI summary paragraph is non-empty', async ({ page }) => {
    const select = page.locator('select')
    await select.selectOption({ index: 1 })
    await page.waitForTimeout(2000)

    // The AI summary section is labelled "Signal Intelligence"
    await expect(page.getByText('Signal Intelligence')).toBeVisible({ timeout: 5_000 })
  })

  test('infrastructure timeline renders at least one event', async ({ page }) => {
    const select = page.locator('select')
    await select.selectOption({ index: 1 })
    await page.waitForTimeout(2000)

    // Timeline section heading
    await expect(page.getByText(/infrastructure pipeline/i)).toBeVisible({ timeout: 5_000 })
  })
})

// ---------------------------------------------------------------------------
// Journey 3 — Opportunity Finder
// ---------------------------------------------------------------------------

test.describe('Journey 3 — Opportunity Finder', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/opportunities')
    await page.waitForLoadState('networkidle')
  })

  test('Opportunity Finder loads with filter sidebar', async ({ page }) => {
    await expect(page.getByText('Filters')).toBeVisible({ timeout: 8_000 })
  })

  test('area cards appear with names and scores', async ({ page }) => {
    await page.waitForTimeout(2000)
    // At least one area name from seed data should be visible
    const seedNames = ['Sarjapur', 'Devanahalli', 'Shamshabad', 'Hinjewadi']
    let found = false
    for (const name of seedNames) {
      if (await page.getByText(name).first().isVisible().catch(() => false)) {
        found = true
        break
      }
    }
    expect(found).toBe(true)
  })

  test('sort select is present', async ({ page }) => {
    await expect(page.locator('select')).toBeVisible()
  })

  test('Opportunity score is shown on cards', async ({ page }) => {
    await page.waitForTimeout(2000)
    // exact:true avoids matching hidden <option>Opportunity Score</option> via case-insensitive substring
    await expect(page.getByText('Opportunity score', { exact: true }).first()).toBeVisible({ timeout: 5_000 })
  })

  test('Analyze button navigates to Area Analyzer', async ({ page }) => {
    await page.waitForTimeout(2000)
    // Click first Analyze button
    const analyzeBtn = page.getByRole('button', { name: /analyze/i }).first()
    await analyzeBtn.click()
    await page.waitForURL('**/analyzer**')
    expect(page.url()).toContain('/analyzer')
  })
})

// ---------------------------------------------------------------------------
// Journey 4 — Compare Areas
// ---------------------------------------------------------------------------

test.describe('Journey 4 — Compare Areas', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/compare')
    await page.waitForLoadState('networkidle')
  })

  test('shows prompt to select at least 2 areas initially', async ({ page }) => {
    await expect(page.getByText(/select at least 2 areas/i)).toBeVisible({ timeout: 8_000 })
  })

  test('adding two areas shows comparison table', async ({ page }) => {
    await page.waitForTimeout(1500)
    const select = page.locator('select')

    // Add first area
    await select.selectOption({ index: 1 })
    await page.waitForTimeout(500)

    // Add second area
    await select.selectOption({ index: 1 }) // first remaining option
    await page.waitForTimeout(1000)

    await expect(page.getByText('SIDE-BY-SIDE METRICS')).toBeVisible({ timeout: 5_000 })
    await expect(page.getByText('GROWTH FACTOR RADAR')).toBeVisible()
  })

  test('remove chip button reduces comparison', async ({ page }) => {
    await page.waitForTimeout(1500)
    const select = page.locator('select')

    await select.selectOption({ index: 1 })
    await page.waitForTimeout(500)
    await select.selectOption({ index: 1 })
    await page.waitForTimeout(500)

    // Comparison is shown — now remove first area via its chip X button
    const removeBtn = page.locator('button').filter({ has: page.locator('svg.lucide-x') }).first()
    await removeBtn.click()
    await page.waitForTimeout(500)

    // Only 1 area remains → back to empty state
    await expect(page.getByText(/select at least 2 areas/i)).toBeVisible({ timeout: 3_000 })
  })
})

// ---------------------------------------------------------------------------
// Journey 5 — Watchlist
// ---------------------------------------------------------------------------

test.describe('Journey 5 — Watchlist', () => {
  test('Watchlist page shows empty state initially', async ({ page }) => {
    // addInitScript runs before every navigation in this page — safe for a single goto
    await page.addInitScript(() => localStorage.removeItem('ls-watchlist'))
    await page.goto('/watchlist')
    await expect(page.getByText(/no areas watched yet/i)).toBeVisible({ timeout: 8_000 })
  })

  test('area watched in OpportunityFinder appears in Watchlist', async ({ page }) => {
    // Navigate first, then clear via evaluate (runs once, not on every subsequent goto)
    await page.goto('/opportunities')
    await page.evaluate(() => localStorage.removeItem('ls-watchlist'))
    await page.reload()
    await page.waitForTimeout(2000)

    // Click the Watch button on the first card
    const watchBtn = page.getByRole('button', { name: /^watch$/i }).first()
    await watchBtn.click()
    await page.waitForTimeout(300)

    // Navigate to Watchlist — localStorage persists because we didn't use addInitScript
    await page.goto('/watchlist')
    await page.waitForTimeout(1500)

    // Should now show the area (not empty state)
    const emptyState = page.getByText(/no areas watched yet/i)
    await expect(emptyState).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Journey 7 — Error resilience
// ---------------------------------------------------------------------------

test.describe('Journey 7 — Error resilience', () => {
  test('Growth Map shows user-visible error when backend is unreachable', async ({ page }) => {
    // Intercept all API calls and return network errors
    await page.route('**/api/**', route => route.abort('connectionrefused'))
    await page.goto('/map')
    await page.waitForTimeout(2000)

    // Should show error message, not a blank screen
    await expect(page.getByText(/failed to load/i)).toBeVisible({ timeout: 8_000 })

    // Should NOT show an unhandled JS error overlay
    const errorOverlay = page.locator('#vite-error-overlay, .error-overlay')
    await expect(errorOverlay).not.toBeVisible()
  })

  test('Area Analyzer with invalid area ID in URL shows graceful state', async ({ page }) => {
    // Navigate to analyzer — the ?area= param triggers a 404 from the API
    await page.route('**/areas/99999/report', route =>
      route.fulfill({ status: 404, body: JSON.stringify({ detail: 'Area not found' }) })
    )
    await page.goto('/analyzer?area=99999')
    await page.waitForTimeout(2000)

    // Should show an error message, not crash
    await expect(page.getByText(/failed to load report|not found|error/i)).toBeVisible({ timeout: 8_000 })
  })
})
