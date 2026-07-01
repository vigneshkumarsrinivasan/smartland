import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, MOCK_AREAS } from '@/test-utils'
import GrowthMap from '../GrowthMap'

// Mock the fetch used by useAreas
const mockFetch = vi.fn()

// MapView renders a Leaflet map in useEffect — jsdom can't handle DOM elements
// required by Leaflet, so we stub MapView to a simple data container.
vi.mock('@/components/map/MapView', () => ({
  MapView: ({ areas }: { areas: { name: string }[] }) => (
    <div data-testid="map-view" data-area-count={areas.length}>
      {areas.map(a => (
        <div key={a.name} data-testid="map-marker">{a.name}</div>
      ))}
    </div>
  ),
}))

describe('GrowthMap page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
  })

  it('shows loading indicator while fetching', () => {
    // Never resolve the promise
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<GrowthMap />)
    expect(screen.getByText(/loading signal data/i)).toBeInTheDocument()
  })

  it('shows error message when API call fails', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 })
    renderWithProviders(<GrowthMap />)
    await waitFor(() => {
      expect(screen.getByText(/failed to load areas/i)).toBeInTheDocument()
    })
  })

  it('renders map with all 10 area markers on successful fetch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_AREAS),
    })
    renderWithProviders(<GrowthMap />)
    await waitFor(() => {
      const markers = screen.getAllByTestId('map-marker')
      expect(markers).toHaveLength(10)
    })
  })

  it('city filter reduces visible markers to only that city', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_AREAS),
    })
    renderWithProviders(<GrowthMap />)

    // Wait for data to load
    await waitFor(() => expect(screen.getAllByTestId('map-marker')).toHaveLength(10))

    // Click Bangalore in the city filter
    const bangaloreBtn = screen.getByRole('button', { name: /bangalore/i })
    await userEvent.click(bangaloreBtn)

    await waitFor(() => {
      const markers = screen.getAllByTestId('map-marker')
      // 5 Bangalore areas in mock data
      expect(markers).toHaveLength(5)
      markers.forEach(m => {
        const bangaloreAreas = ['Sarjapur', 'Devanahalli', 'Electronic City', 'Whitefield', 'Hoskote']
        expect(bangaloreAreas).toContain(m.textContent)
      })
    })
  })

  it('passes only filtered areas to map when city filter is active', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_AREAS),
    })
    renderWithProviders(<GrowthMap />)
    await waitFor(() => expect(screen.getAllByTestId('map-marker')).toHaveLength(10))

    // Enable Hyderabad filter (only 1 area)
    await userEvent.click(screen.getByRole('button', { name: /hyderabad/i }))

    await waitFor(() => {
      const mapView = screen.getByTestId('map-view')
      expect(mapView).toHaveAttribute('data-area-count', '1')
    })
  })
})
