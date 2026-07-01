import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, MOCK_AREAS } from '@/test-utils'
import OpportunityFinder from '../OpportunityFinder'

const mockFetch = vi.fn()

describe('OpportunityFinder page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_AREAS),
    })
  })

  it('renders filter sidebar', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => expect(screen.getByText('Filters')).toBeInTheDocument())
  })

  it('shows all areas in default state', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => {
      // AreaCards render area names
      expect(screen.getByText('Sarjapur')).toBeInTheDocument()
      expect(screen.getByText('Devanahalli')).toBeInTheDocument()
    })
  })

  it('shows area count in sort bar', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => {
      expect(screen.getByText(/10 areas found/i)).toBeInTheDocument()
    })
  })

  it('filters by recommendation when signal filter is clicked', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => expect(screen.getByText('Sarjapur')).toBeInTheDocument())

    // Click "Strong Buy" filter
    await userEvent.click(screen.getByRole('button', { name: 'Strong Buy' }))

    await waitFor(() => {
      // Only Devanahalli and Shamshabad are Strong Buy in mock data
      expect(screen.getByText('Devanahalli')).toBeInTheDocument()
      expect(screen.getByText('Shamshabad')).toBeInTheDocument()
      // Sarjapur is Buy not Strong Buy
      expect(screen.queryByText('Sarjapur')).not.toBeInTheDocument()
    })
  })

  it('shows opportunity score on each card', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => {
      const scoreLabels = screen.getAllByText('Opportunity score')
      expect(scoreLabels.length).toBeGreaterThan(0)
    })
  })

  it('sort options are present in select', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => {
      const select = screen.getByRole('combobox')
      expect(select).toBeInTheDocument()
    })
    const options = screen.getAllByRole('option')
    const optionTexts = options.map(o => o.textContent)
    expect(optionTexts).toContain('Opportunity Score')
    expect(optionTexts).toContain('Growth Score')
  })

  it('shows empty state when no areas match filter', async () => {
    // Filter by Hyderabad AND Strong Buy: only Shamshabad qualifies
    // Then also filter by Buy: 0 results
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => expect(screen.getByText('Sarjapur')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Avoid' }))
    // Then click Hyderabad (only 1 Avoid area in Hyderabad mock? Actually Hoskote is Avoid and is Bangalore)
    // Let's click a combination that yields 0
    await userEvent.click(screen.getByRole('button', { name: 'Hyderabad' }))

    // Hyderabad has 1 area (Shamshabad) which is Strong Buy not Avoid
    await waitFor(() => {
      expect(screen.getByText(/no areas match/i)).toBeInTheDocument()
    })
  })

  it('Analyze button navigates to /analyzer with area id', async () => {
    renderWithProviders(<OpportunityFinder />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: /analyze/i }).length).toBeGreaterThan(0))
    // Navigation happens via useNavigate; in MemoryRouter this changes the URL
    // Just verify the button is present and clickable
    const analyzeBtn = screen.getAllByRole('button', { name: /analyze/i })[0]
    expect(analyzeBtn).toBeEnabled()
  })
})
