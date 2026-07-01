import type { AreaSummary } from './area'

export interface PricePoint {
  date: string
  price_sqft: number
}

export interface ForecastPoint {
  year: number
  price_sqft: number
}

export interface GrowthSignals {
  infrastructure: number
  job_growth: number
  population_growth: number
  commercial_activity: number
  transaction_velocity: number
  land_scarcity: number
  government_spending: number
}

export interface RiskSignals {
  flood: number
  water: number
  legal: number
  overvaluation: number
  pollution: number
  crime: number
  delay: number
}

export interface InfraProject {
  name: string
  type: string
  status: 'Completed' | 'Under Construction' | 'Announced'
  target_year: number
  impact_score: number
}

export interface AreaReport {
  area: AreaSummary
  price_history: PricePoint[]
  forecast: {
    base: ForecastPoint[]
    optimistic: ForecastPoint[]
    risk: ForecastPoint[]
  }
  growth_signals: GrowthSignals
  risk_signals: RiskSignals
  infrastructure_projects: InfraProject[]
  ai_summary: string
}
