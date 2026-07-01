import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test-utils'
import DataSources from '../DataSources'
import type { DataSource } from '@/hooks/useDataSources'

const mockFetch = vi.fn()

const MOCK_SOURCES: DataSource[] = [
  { id: 1, name: 'CREDAI Price Registry', category: 'Pricing', status: 'active',
    description: 'Developer transaction data', coverage: 'Pan-India', last_updated: null },
  { id: 2, name: 'NHAI Project Tracker', category: 'Infrastructure', status: 'active',
    description: 'NHAI project status', coverage: 'Pan-India', last_updated: null },
  { id: 3, name: 'Census 2011 + Projections', category: 'Demographics', status: 'degraded',
    description: 'Population estimates', coverage: 'Pan-India', last_updated: null },
  { id: 4, name: 'IMD Flood Hazard Maps', category: 'Risk/Environmental', status: 'offline',
    description: 'Flood zone data', coverage: 'Pan-India', last_updated: null },
]

describe('DataSources page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    vi.stubGlobal('fetch', mockFetch)
  })

  it('shows loading state while fetching', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<DataSources />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows error message when API fails', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 })
    renderWithProviders(<DataSources />)
    await waitFor(() => {
      expect(screen.getByText(/failed to load data sources/i)).toBeInTheDocument()
    })
  })

  it('renders data source names after successful fetch', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(MOCK_SOURCES) })
    renderWithProviders(<DataSources />)
    await waitFor(() => {
      expect(screen.getByText('CREDAI Price Registry')).toBeInTheDocument()
      expect(screen.getByText('NHAI Project Tracker')).toBeInTheDocument()
    })
  })

  it('renders correct status badges', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(MOCK_SOURCES) })
    renderWithProviders(<DataSources />)
    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(2)
      expect(screen.getByText('Degraded')).toBeInTheDocument()
      expect(screen.getByText('Offline')).toBeInTheDocument()
    })
  })

  it('shows summary stats bar', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(MOCK_SOURCES) })
    renderWithProviders(<DataSources />)
    await waitFor(() => {
      expect(screen.getByText(/4 total feeds/i)).toBeInTheDocument()
      expect(screen.getByText(/2 active/i)).toBeInTheDocument()
      expect(screen.getByText(/1 degraded/i)).toBeInTheDocument()
      expect(screen.getByText(/1 offline/i)).toBeInTheDocument()
    })
  })

  it('renders category column for each source', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(MOCK_SOURCES) })
    renderWithProviders(<DataSources />)
    await waitFor(() => {
      expect(screen.getByText('Pricing')).toBeInTheDocument()
      expect(screen.getByText('Infrastructure')).toBeInTheDocument()
      expect(screen.getByText('Demographics')).toBeInTheDocument()
    })
  })
})
