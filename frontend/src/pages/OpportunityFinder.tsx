import { useState, useMemo } from 'react'
import { Compass, SlidersHorizontal } from 'lucide-react'
import { useAreas } from '@/hooks/useAreas'
import { AreaCard } from '@/components/common/AreaCard'
import { cn } from '@/lib/utils'
import type { AreaSummary } from '@/types/area'

const GROWTH_DRIVER_LABELS: Record<string, string> = {
  infrastructure: 'Infrastructure momentum',
  job_growth: 'Strong job creation',
  population_growth: 'Population growth',
  commercial_activity: 'Commercial expansion',
  transaction_velocity: 'High transaction volume',
  land_scarcity: 'Land scarcity premium',
  government_spending: 'Government investment',
}

// Simple opportunity score: rewards high growth + low risk
function opportunityScore(a: AreaSummary) {
  return Math.round((a.growth_score - a.risk_score * 0.5) * 10) / 10
}

const REC_FILTERS = ['All', 'Strong Buy', 'Buy', 'Hold', 'Avoid'] as const
const CITY_FILTERS = ['All Cities', 'Bangalore', 'Hyderabad', 'Pune', 'Chennai', 'Coimbatore'] as const
const SORT_OPTIONS = [
  { key: 'opportunity', label: 'Opportunity Score' },
  { key: 'growth',      label: 'Growth Score' },
  { key: 'cagr',        label: '3yr CAGR' },
  { key: 'price_asc',   label: 'Price: Low → High' },
  { key: 'price_desc',  label: 'Price: High → Low' },
] as const

type SortKey = typeof SORT_OPTIONS[number]['key']

function sortAreas(areas: AreaSummary[], key: SortKey): AreaSummary[] {
  return [...areas].sort((a, b) => {
    switch (key) {
      case 'opportunity': return opportunityScore(b) - opportunityScore(a)
      case 'growth':      return b.growth_score - a.growth_score
      case 'cagr':        return (b.cagr_pct ?? 0) - (a.cagr_pct ?? 0)
      case 'price_asc':   return a.current_price_sqft - b.current_price_sqft
      case 'price_desc':  return b.current_price_sqft - a.current_price_sqft
      default:            return 0
    }
  })
}

export default function OpportunityFinder() {
  const { areas, loading } = useAreas()
  const [recFilter, setRecFilter] = useState<string>('All')
  const [cityFilter, setCityFilter] = useState<string>('All Cities')
  const [minGrowth, setMinGrowth] = useState(0)
  const [maxPrice, setMaxPrice] = useState(25000)
  const [sortKey, setSortKey] = useState<SortKey>('opportunity')

  const filtered = useMemo(() => {
    let result = areas
    if (recFilter !== 'All') result = result.filter(a => a.recommendation === recFilter)
    if (cityFilter !== 'All Cities') result = result.filter(a => a.city === cityFilter)
    result = result.filter(a => a.growth_score >= minGrowth && a.current_price_sqft <= maxPrice)
    return sortAreas(result, sortKey)
  }, [areas, recFilter, cityFilter, minGrowth, maxPrice, sortKey])

  return (
    <div className="flex h-full overflow-hidden">
      {/* Filter sidebar */}
      <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-950 overflow-y-auto">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
          <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-sm font-semibold text-slate-200">Filters</span>
        </div>
        <div className="px-4 py-4 space-y-5">
          {/* Signal */}
          <section>
            <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">SIGNAL</p>
            <div className="space-y-1">
              {REC_FILTERS.map(r => (
                <button
                  key={r}
                  onClick={() => setRecFilter(r)}
                  className={cn(
                    'w-full text-left px-3 py-1.5 rounded-md text-[11px] transition-colors',
                    recFilter === r
                      ? 'bg-cyan-500/15 text-cyan-300 font-medium'
                      : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </section>

          {/* City */}
          <section>
            <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">CITY</p>
            <div className="space-y-1">
              {CITY_FILTERS.map(c => (
                <button
                  key={c}
                  onClick={() => setCityFilter(c)}
                  className={cn(
                    'w-full text-left px-3 py-1.5 rounded-md text-[11px] transition-colors',
                    cityFilter === c
                      ? 'bg-cyan-500/15 text-cyan-300 font-medium'
                      : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
          </section>

          {/* Min growth */}
          <section>
            <div className="flex justify-between mb-2">
              <p className="text-[9px] font-semibold text-slate-500 tracking-widest">MIN GROWTH</p>
              <span className="text-[11px] text-slate-300 font-semibold">{minGrowth}</span>
            </div>
            <input
              type="range" min={0} max={90} value={minGrowth}
              onChange={e => setMinGrowth(Number(e.target.value))}
              className="w-full h-1 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-slate-700 to-cyan-500/40 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer"
            />
          </section>

          {/* Max price */}
          <section>
            <div className="flex justify-between mb-2">
              <p className="text-[9px] font-semibold text-slate-500 tracking-widest">MAX PRICE</p>
              <span className="text-[11px] text-slate-300 font-semibold">
                {maxPrice >= 25000 ? 'Any' : `₹${maxPrice.toLocaleString('en-IN')}`}
              </span>
            </div>
            <input
              type="range" min={1000} max={25000} step={500} value={maxPrice}
              onChange={e => setMaxPrice(Number(e.target.value))}
              className="w-full h-1 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-slate-700 to-cyan-500/40 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer"
            />
          </section>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 overflow-y-auto">
        {/* Sort bar */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-2.5 border-b border-slate-800 bg-slate-950/90 backdrop-blur-sm">
          <span className="text-xs text-slate-500">
            {loading ? 'Loading…' : `${filtered.length} areas found`}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500">Sort by</span>
            <select
              value={sortKey}
              onChange={e => setSortKey(e.target.value as SortKey)}
              className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-[11px] text-slate-300 focus:outline-none"
            >
              {SORT_OPTIONS.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
            </select>
          </div>
        </div>

        {/* Cards grid */}
        <div className="p-5 grid grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((area, i) => (
            <AreaCard
              key={area.id}
              area={area}
              rank={i + 1}
              topDriver={GROWTH_DRIVER_LABELS[
                area.growth_score > 70 ? 'infrastructure' : 'land_scarcity'
              ]}
              opportunityScore={opportunityScore(area)}
            />
          ))}
          {!loading && filtered.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-16 text-slate-600 gap-3">
              <Compass className="w-10 h-10 opacity-20" />
              <p className="text-sm">No areas match your filters</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
