/**
 * Shared test utilities: renders components inside the full router/context shell.
 */
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { WatchlistProvider } from '@/context/WatchlistContext'
import type { ReactElement, ReactNode } from 'react'
import type { AreaSummary } from '@/types/area'

// Convenience wrapper that provides all required context providers
function AllProviders({ children }: { children: ReactNode }) {
  return (
    <WatchlistProvider>
      <MemoryRouter>{children}</MemoryRouter>
    </WatchlistProvider>
  )
}

export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: AllProviders, ...options })
}

// ---------------------------------------------------------------------------
// Shared mock data — values match CLAUDE.md seed data exactly
// ---------------------------------------------------------------------------

export const MOCK_AREAS: AreaSummary[] = [
  {
    id: 1, name: 'Sarjapur', city: 'Bangalore', lat: 12.8693, lng: 77.7950,
    land_type: 'Residential', current_price_sqft: 6400,
    growth_score: 75.2, risk_score: 35.2, confidence_score: 82,
    recommendation: 'Buy', cagr_pct: 10.1,
  },
  {
    id: 2, name: 'Devanahalli', city: 'Bangalore', lat: 13.2485, lng: 77.7145,
    land_type: 'Mixed', current_price_sqft: 4100,
    growth_score: 82.4, risk_score: 29.5, confidence_score: 88,
    recommendation: 'Strong Buy', cagr_pct: 15.8,
  },
  {
    id: 3, name: 'Electronic City', city: 'Bangalore', lat: 12.8458, lng: 77.6603,
    land_type: 'IT/Commercial', current_price_sqft: 5300,
    growth_score: 62.5, risk_score: 36.7, confidence_score: 76,
    recommendation: 'Hold', cagr_pct: 8.2,
  },
  {
    id: 4, name: 'Whitefield', city: 'Bangalore', lat: 12.9698, lng: 77.7499,
    land_type: 'IT/Residential', current_price_sqft: 8100,
    growth_score: 61.8, risk_score: 42.2, confidence_score: 78,
    recommendation: 'Hold', cagr_pct: 10.4,
  },
  {
    id: 5, name: 'Hoskote', city: 'Bangalore', lat: 13.0704, lng: 77.7985,
    land_type: 'Residential/Agricultural', current_price_sqft: 2550,
    growth_score: 50.2, risk_score: 76.3, confidence_score: 60,
    recommendation: 'Avoid', cagr_pct: 15.9,
  },
  {
    id: 6, name: 'Shamshabad', city: 'Hyderabad', lat: 17.2403, lng: 78.4294,
    land_type: 'Mixed', current_price_sqft: 4500,
    growth_score: 81.5, risk_score: 34.3, confidence_score: 85,
    recommendation: 'Strong Buy', cagr_pct: 16.8,
  },
  {
    id: 7, name: 'Hinjewadi', city: 'Pune', lat: 18.5912, lng: 73.7382,
    land_type: 'IT/Residential', current_price_sqft: 7200,
    growth_score: 74.7, risk_score: 40.9, confidence_score: 80,
    recommendation: 'Buy', cagr_pct: 10.9,
  },
  {
    id: 8, name: 'Sriperumbudur', city: 'Chennai', lat: 12.9673, lng: 79.9454,
    land_type: 'Industrial', current_price_sqft: 2600,
    growth_score: 41.5, risk_score: 49.7, confidence_score: 65,
    recommendation: 'Avoid', cagr_pct: 12.5,
  },
  {
    id: 9, name: 'Oragadam', city: 'Chennai', lat: 12.8342, lng: 80.0557,
    land_type: 'Industrial/Logistics', current_price_sqft: 3400,
    growth_score: 71.3, risk_score: 44.5, confidence_score: 75,
    recommendation: 'Buy', cagr_pct: 17.2,
  },
  {
    id: 10, name: 'Coimbatore North', city: 'Coimbatore', lat: 11.0711, lng: 77.0028,
    land_type: 'Residential', current_price_sqft: 3200,
    growth_score: 60.9, risk_score: 43.5, confidence_score: 70,
    recommendation: 'Hold', cagr_pct: 9.9,
  },
]
