import { useState, useMemo } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import { MapView } from '@/components/map/MapView'
import { FilterPanel } from '@/components/map/FilterPanel'
import { useAreas } from '@/hooks/useAreas'
import { DEFAULT_FILTERS } from '@/types/area'
import type { AreaFilters } from '@/types/area'

export default function GrowthMap() {
  const { areas, loading, error } = useAreas()
  const [filters, setFilters] = useState<AreaFilters>(DEFAULT_FILTERS)

  const filteredAreas = useMemo(() => {
    return areas.filter(area => {
      if (filters.cities.length > 0 && !filters.cities.includes(area.city)) return false
      if (filters.recommendations.length > 0 && !filters.recommendations.includes(area.recommendation)) return false
      if (area.growth_score < filters.minGrowthScore) return false
      if (area.risk_score > filters.maxRiskScore) return false
      if (area.current_price_sqft < filters.minPriceSqft) return false
      if (area.current_price_sqft > filters.maxPriceSqft) return false
      return true
    })
  }, [areas, filters])

  return (
    <div className="flex h-full overflow-hidden">
      {/* Map area */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
            <div className="flex items-center gap-3 text-slate-300">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
              <span className="text-sm">Loading signal data…</span>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-slate-950/80">
            <div className="flex items-center gap-3 bg-slate-900 border border-red-500/30 rounded-xl px-5 py-4">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
              <div>
                <p className="text-sm text-slate-200 font-medium">Failed to load areas</p>
                <p className="text-xs text-slate-500 mt-0.5">{error} — is the backend running?</p>
              </div>
            </div>
          </div>
        )}
        <MapView areas={filteredAreas} />
      </div>

      {/* Filter sidebar */}
      <FilterPanel
        areas={areas}
        filteredCount={filteredAreas.length}
        filters={filters}
        onChange={setFilters}
      />
    </div>
  )
}
