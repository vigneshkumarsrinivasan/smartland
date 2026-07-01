import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, MOCK_AREAS } from '@/test-utils'
import { AreaCard } from '../AreaCard'

const SARJAPUR = MOCK_AREAS[0] // Buy, ₹6400, growth=75.2, risk=35.2

describe('AreaCard component', () => {
  it('renders area name and city', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    expect(screen.getByText('Sarjapur')).toBeInTheDocument()
    expect(screen.getByText(/bangalore/i)).toBeInTheDocument()
  })

  it('renders recommendation badge', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    expect(screen.getByText('BUY')).toBeInTheDocument()
  })

  it('renders current price', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    expect(screen.getByText('₹6,400')).toBeInTheDocument()
  })

  it('renders growth and risk scores', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    // Each score appears twice: once in the metric row, once in the bar label
    expect(screen.getAllByText('75.2').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('35.2').length).toBeGreaterThanOrEqual(1)
  })

  it('renders CAGR when provided', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    expect(screen.getByText('10.1%')).toBeInTheDocument()
  })

  it('renders rank number when provided', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} rank={3} />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders topDriver label when provided', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} topDriver="Infrastructure momentum" />)
    expect(screen.getByText('Infrastructure momentum')).toBeInTheDocument()
  })

  it('renders opportunity score when provided', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} opportunityScore={57.6} />)
    expect(screen.getByText('57.6')).toBeInTheDocument()
  })

  it('toggles Watch / Watching when bookmark is clicked', async () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    const watchBtn = screen.getByRole('button', { name: /watch/i })
    expect(screen.getByText('Watch')).toBeInTheDocument()

    await userEvent.click(watchBtn)
    expect(screen.getByText('Watching')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /watching/i }))
    expect(screen.getByText('Watch')).toBeInTheDocument()
  })

  it('renders Analyze button', () => {
    renderWithProviders(<AreaCard area={SARJAPUR} />)
    expect(screen.getByRole('button', { name: /analyze/i })).toBeInTheDocument()
  })

  it('renders correct badge color for Strong Buy', () => {
    const area = MOCK_AREAS[1] // Devanahalli, Strong Buy
    renderWithProviders(<AreaCard area={area} />)
    const badge = screen.getByText('STRONG BUY')
    expect(badge).toHaveClass('text-emerald-400')
  })

  it('renders correct badge color for Avoid', () => {
    const area = MOCK_AREAS[4] // Hoskote, Avoid
    renderWithProviders(<AreaCard area={area} />)
    const badge = screen.getByText('AVOID')
    expect(badge).toHaveClass('text-red-400')
  })

  it('renders correct badge color for Hold', () => {
    const area = MOCK_AREAS[2] // Electronic City, Hold
    renderWithProviders(<AreaCard area={area} />)
    const badge = screen.getByText('HOLD')
    expect(badge).toHaveClass('text-amber-400')
  })
})
