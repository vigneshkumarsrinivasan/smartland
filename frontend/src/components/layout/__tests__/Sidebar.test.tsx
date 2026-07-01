import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/test-utils'
import { Sidebar } from '../Sidebar'

const NAV_LABELS = [
  'Growth Map', 'Area Analyzer', 'Opportunity Finder', 'Compare Areas',
  'Watchlist', 'Reports', 'Data Sources', 'Admin',
]

describe('Sidebar', () => {
  it('renders all 8 nav items', () => {
    renderWithProviders(<Sidebar />)
    NAV_LABELS.forEach(label => {
      expect(screen.getByText(label)).toBeInTheDocument()
    })
  })

  it('renders the LandSignal brand name', () => {
    renderWithProviders(<Sidebar />)
    expect(screen.getByText('LandSignal')).toBeInTheDocument()
  })

  it('renders the AI tagline', () => {
    renderWithProviders(<Sidebar />)
    // The tagline is split across a <br />, so match via container text
    expect(screen.getByText(/we predict its future/i)).toBeInTheDocument()
  })

  it('renders nav links with correct hrefs', () => {
    renderWithProviders(<Sidebar />)
    const mapLink = screen.getByRole('link', { name: /growth map/i })
    expect(mapLink).toHaveAttribute('href', '/map')
    const analyzerLink = screen.getByRole('link', { name: /area analyzer/i })
    expect(analyzerLink).toHaveAttribute('href', '/analyzer')
  })
})
