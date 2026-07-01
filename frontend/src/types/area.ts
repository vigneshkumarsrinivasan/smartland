export type Recommendation = 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid' | 'Sell'

export interface AreaSummary {
  id: number
  name: string
  city: string
  lat: number
  lng: number
  land_type: string
  current_price_sqft: number
  growth_score: number
  risk_score: number
  confidence_score: number
  recommendation: Recommendation
  cagr_pct: number | null
}

export interface AreaFilters {
  cities: string[]
  recommendations: Recommendation[]
  minGrowthScore: number
  maxRiskScore: number
  minPriceSqft: number
  maxPriceSqft: number
}

export const REC_ORDER: Recommendation[] = ['Strong Buy', 'Buy', 'Hold', 'Avoid', 'Sell']

export const DEFAULT_FILTERS: AreaFilters = {
  cities: [],
  recommendations: [],
  minGrowthScore: 0,
  maxRiskScore: 100,
  minPriceSqft: 0,
  maxPriceSqft: 25000,
}
