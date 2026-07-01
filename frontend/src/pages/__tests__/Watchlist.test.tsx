import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, MOCK_AREAS } from '@/test-utils'
import Watchlist from '../Watchlist'

const mockFetch = vi.fn()

// Clear localStorage before each test so watchlist state is clean
beforeEach(() => {
  localStorage.clear()
  mockFetch.mockReset()
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(MOCK_AREAS),
  })
})

describe('Watchlist page', () => {
  it('shows empty state when no areas are watched', async () => {
    renderWithProviders(<Watchlist />)
    await waitFor(() => {
      expect(screen.getByText(/no areas watched yet/i)).toBeInTheDocument()
    })
  })

  it('shows watchlist prompt when empty', async () => {
    renderWithProviders(<Watchlist />)
    await waitFor(() => {
      expect(screen.getByText(/click the bookmark icon/i)).toBeInTheDocument()
    })
  })

  it('shows watched area when it is in localStorage', async () => {
    // Pre-populate watchlist with area id=1 (Sarjapur)
    localStorage.setItem('ls-watchlist', JSON.stringify([1]))

    renderWithProviders(<Watchlist />)
    await waitFor(() => {
      expect(screen.getByText('Sarjapur')).toBeInTheDocument()
    })
  })

  it('shows correct count in header', async () => {
    localStorage.setItem('ls-watchlist', JSON.stringify([1, 2]))
    renderWithProviders(<Watchlist />)
    await waitFor(() => {
      expect(screen.getByText(/2 areas on watchlist/i)).toBeInTheDocument()
    })
  })

  it('shows singular count for 1 area', async () => {
    localStorage.setItem('ls-watchlist', JSON.stringify([6]))
    renderWithProviders(<Watchlist />)
    await waitFor(() => {
      expect(screen.getByText(/1 area on watchlist/i)).toBeInTheDocument()
    })
  })

  it('removing area via bookmark toggle updates the list', async () => {
    localStorage.setItem('ls-watchlist', JSON.stringify([1]))
    renderWithProviders(<Watchlist />)

    await waitFor(() => expect(screen.getByText('Sarjapur')).toBeInTheDocument())

    // Click the "Watching" bookmark toggle button to remove from watchlist
    const watchingBtn = screen.getByRole('button', { name: /watching/i })
    await userEvent.click(watchingBtn)

    await waitFor(() => {
      // After removal, empty state appears
      expect(screen.getByText(/no areas watched yet/i)).toBeInTheDocument()
    })
  })

  it('shows loading state before fetch completes', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<Watchlist />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})
