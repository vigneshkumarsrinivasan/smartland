import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, MOCK_AREAS } from '@/test-utils'
import CompareAreas from '../CompareAreas'

const mockFetch = vi.fn()

describe('CompareAreas page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_AREAS),
    })
  })

  it('shows empty state prompt when fewer than 2 areas selected', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => {
      expect(screen.getByText(/select at least 2 areas/i)).toBeInTheDocument()
    })
  })

  it('renders area picker dropdown after data loads', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })
  })

  it('shows comparison table and radar chart after selecting 2 areas', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())

    const select = screen.getByRole('combobox')

    // Select Sarjapur (id=1)
    await userEvent.selectOptions(select, '1')
    await waitFor(() => expect(screen.getByText('Sarjapur')).toBeInTheDocument())

    // Select Devanahalli (id=2)
    await userEvent.selectOptions(select, '2')
    // Devanahalli appears in chip + table header + growth bar section — use getAllByText
    await waitFor(() => expect(screen.getAllByText('Devanahalli').length).toBeGreaterThanOrEqual(1))

    // Both selected → comparison should render
    await waitFor(() => {
      expect(screen.getByText('SIDE-BY-SIDE METRICS')).toBeInTheDocument()
      expect(screen.getByText('GROWTH FACTOR RADAR')).toBeInTheDocument()
    })
  })

  it('shows metric rows in comparison table', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())

    await userEvent.selectOptions(screen.getByRole('combobox'), '1')
    await userEvent.selectOptions(screen.getByRole('combobox'), '2')

    await waitFor(() => {
      expect(screen.getByText('Price / sqft')).toBeInTheDocument()
      expect(screen.getByText('Growth Score')).toBeInTheDocument()
      expect(screen.getByText('Risk Score')).toBeInTheDocument()
      expect(screen.getByText('3yr CAGR')).toBeInTheDocument()
      expect(screen.getByText('Signal')).toBeInTheDocument()
    })
  })

  it('can add up to 5 areas without error', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())

    const select = screen.getByRole('combobox')
    for (const id of [1, 2, 3, 4, 5]) {
      await userEvent.selectOptions(select, String(id))
    }

    // All 5 chips should be visible
    await waitFor(() => {
      const chips = screen.getAllByRole('button', { name: '' }) // X buttons on chips
      expect(chips.length).toBeGreaterThanOrEqual(5)
    })
  })

  it('picker is disabled after 5 areas are selected', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())

    const select = screen.getByRole('combobox')
    for (const id of [1, 2, 3, 4, 5]) {
      await userEvent.selectOptions(select, String(id))
    }

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeDisabled()
    })
  })

  it('remove button removes area from comparison', async () => {
    renderWithProviders(<CompareAreas />)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())

    await userEvent.selectOptions(screen.getByRole('combobox'), '1')
    await userEvent.selectOptions(screen.getByRole('combobox'), '2')

    await waitFor(() => expect(screen.getAllByText('Sarjapur').length).toBeGreaterThanOrEqual(1))

    // The chip for Sarjapur contains a button (the X icon). Find by querying the
    // first svg-only button (no accessible text) inside a chip span.
    const allButtons = screen.getAllByRole('button')
    // Chip X-buttons have no text — filter to those without text content
    const removeButtons = allButtons.filter(b => b.textContent?.trim() === '')
    await userEvent.click(removeButtons[0])

    await waitFor(() => {
      // After removing Sarjapur, only 1 area remains → should show empty state
      expect(screen.getByText(/select at least 2 areas/i)).toBeInTheDocument()
    })
  })
})
