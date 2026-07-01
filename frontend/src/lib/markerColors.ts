import type { AreaSummary } from '@/types/area'

export const REC_COLORS: Record<string, string> = {
  'Strong Buy': '#10b981',
  'Buy':        '#06b6d4',
  'Emerging':   '#3b82f6',  // Buy + price < ₹3500/sqft
  'Hold':       '#f59e0b',
  'Avoid':      '#ef4444',
  'Sell':       '#f97316',
}

export function isEmerging(area: AreaSummary) {
  return ['Strong Buy', 'Buy'].includes(area.recommendation) && area.current_price_sqft < 3500
}

export function markerColor(area: AreaSummary): string {
  if (isEmerging(area)) return REC_COLORS['Emerging']
  return REC_COLORS[area.recommendation] ?? '#94a3b8'
}

export function markerRadius(area: AreaSummary): number {
  if (area.recommendation === 'Strong Buy') return 14
  if (area.recommendation === 'Buy') return 12
  return 10
}

export function displayLabel(area: AreaSummary): string {
  return isEmerging(area) ? 'Emerging' : area.recommendation
}
