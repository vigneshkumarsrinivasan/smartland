import { SlidersHorizontal, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AreaSummary, AreaFilters, Recommendation } from '@/types/area'
import { DEFAULT_FILTERS, REC_ORDER } from '@/types/area'
import { REC_COLORS } from '@/lib/markerColors'

// Investment horizon maps to a minGrowthScore heuristic
const HORIZON_GROWTH: Record<string, number> = {
  any: 0,
  '3yr': 55,
  '5yr': 65,
  '10yr': 75,
}

// Risk appetite maps to a maxRiskScore cap
const RISK_APP_MAX: Record<string, number> = {
  aggressive: 100,
  moderate: 60,
  conservative: 40,
}

const ALL_CITIES = ['Bangalore', 'Hyderabad', 'Pune', 'Chennai', 'Coimbatore']

interface Props {
  areas: AreaSummary[]
  filteredCount: number
  filters: AreaFilters
  onChange: (f: AreaFilters) => void
}

function SliderRow({
  label, value, min, max, onChange, invert = false,
}: {
  label: string; value: number; min: number; max: number
  onChange: (v: number) => void; invert?: boolean
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-[11px] text-slate-400">{label}</span>
        <span className="text-[11px] font-semibold text-slate-200">{value}</span>
      </div>
      <input
        type="range" min={min} max={max} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className={cn(
          'w-full h-1 rounded-full appearance-none cursor-pointer',
          '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5',
          '[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400',
          '[&::-webkit-slider-thumb]:cursor-pointer',
          invert ? 'bg-gradient-to-r from-red-500/40 to-slate-700' : 'bg-gradient-to-r from-slate-700 to-cyan-500/40'
        )}
      />
    </div>
  )
}

export function FilterPanel({ areas, filteredCount, filters, onChange }: Props) {
  const totalCount = areas.length

  // Rec counts (based on unfiltered areas so user can see what's available)
  const recCounts = REC_ORDER.reduce<Record<string, number>>((acc, r) => {
    acc[r] = areas.filter(a => a.recommendation === r).length
    return acc
  }, {})

  function toggleCity(city: string) {
    const next = filters.cities.includes(city)
      ? filters.cities.filter(c => c !== city)
      : [...filters.cities, city]
    onChange({ ...filters, cities: next })
  }

  function toggleRec(rec: Recommendation) {
    const next = filters.recommendations.includes(rec)
      ? filters.recommendations.filter(r => r !== rec)
      : [...filters.recommendations, rec]
    onChange({ ...filters, recommendations: next })
  }

  function setHorizon(key: string) {
    onChange({ ...filters, minGrowthScore: HORIZON_GROWTH[key] })
  }

  function setRiskApp(key: string) {
    onChange({ ...filters, maxRiskScore: RISK_APP_MAX[key] })
  }

  const currentHorizon = Object.entries(HORIZON_GROWTH).find(
    ([, v]) => v === filters.minGrowthScore
  )?.[0] ?? 'any'

  const currentRiskApp = Object.entries(RISK_APP_MAX).find(
    ([, v]) => v === filters.maxRiskScore
  )?.[0] ?? 'aggressive'

  const isDirty =
    filters.cities.length > 0 ||
    filters.recommendations.length > 0 ||
    filters.minGrowthScore > 0 ||
    filters.maxRiskScore < 100 ||
    filters.minPriceSqft > 0 ||
    filters.maxPriceSqft < DEFAULT_FILTERS.maxPriceSqft

  return (
    <aside className="w-72 shrink-0 flex flex-col border-l border-slate-800 bg-slate-950 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-sm font-semibold text-slate-200">Filters</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {filteredCount}/{totalCount} areas
          </span>
          {isDirty && (
            <button
              onClick={() => onChange({ ...DEFAULT_FILTERS })}
              className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              <X className="w-3 h-3" /> Reset
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 px-4 py-4 space-y-5">
        {/* City */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">CITY</p>
          <div className="flex flex-wrap gap-1.5">
            {ALL_CITIES.map(city => {
              const active = filters.cities.includes(city)
              return (
                <button
                  key={city}
                  onClick={() => toggleCity(city)}
                  className={cn(
                    'px-2.5 py-1 rounded-md text-[11px] font-medium transition-all',
                    active
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-500'
                  )}
                >
                  {city}
                </button>
              )
            })}
          </div>
        </section>

        {/* Recommendation */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">SIGNAL</p>
          <div className="space-y-1.5">
            {REC_ORDER.map(rec => {
              const active = filters.recommendations.includes(rec)
              const color = REC_COLORS[rec]
              const count = recCounts[rec] ?? 0
              return (
                <button
                  key={rec}
                  onClick={() => toggleRec(rec)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-1.5 rounded-md text-[11px] font-medium transition-all border',
                    active
                      ? 'border-current'
                      : 'border-slate-800 bg-slate-900 text-slate-500 hover:border-slate-600'
                  )}
                  style={active ? {
                    background: `${color}18`,
                    color,
                    borderColor: `${color}44`,
                  } : undefined}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ background: color }}
                    />
                    {rec}
                  </div>
                  <span className="text-[10px] opacity-60">{count}</span>
                </button>
              )
            })}
          </div>
        </section>

        {/* Investment Horizon */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">INVESTMENT HORIZON</p>
          <div className="grid grid-cols-4 gap-1">
            {[
              { key: 'any', label: 'Any' },
              { key: '3yr', label: '3 yr' },
              { key: '5yr', label: '5 yr' },
              { key: '10yr', label: '10 yr' },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setHorizon(key)}
                className={cn(
                  'py-1.5 rounded-md text-[11px] font-medium border transition-all',
                  currentHorizon === key
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : 'bg-slate-900 text-slate-500 border-slate-800 hover:border-slate-600'
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 mt-1.5">
            Longer horizons require higher growth signal
          </p>
        </section>

        {/* Risk Appetite */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-2">RISK APPETITE</p>
          <div className="grid grid-cols-3 gap-1">
            {[
              { key: 'aggressive', label: 'High', color: '#ef4444' },
              { key: 'moderate',   label: 'Med',  color: '#f59e0b' },
              { key: 'conservative', label: 'Low', color: '#10b981' },
            ].map(({ key, label, color }) => (
              <button
                key={key}
                onClick={() => setRiskApp(key)}
                className={cn(
                  'py-1.5 rounded-md text-[11px] font-medium border transition-all',
                  currentRiskApp === key
                    ? 'border-current'
                    : 'bg-slate-900 text-slate-500 border-slate-800 hover:border-slate-600'
                )}
                style={currentRiskApp === key ? {
                  background: `${color}18`,
                  color,
                  borderColor: `${color}44`,
                } : undefined}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {/* Growth Score slider */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-3">GROWTH SCORE</p>
          <SliderRow
            label="Minimum"
            value={filters.minGrowthScore}
            min={0} max={100}
            onChange={v => onChange({ ...filters, minGrowthScore: v })}
          />
        </section>

        {/* Budget Range */}
        <section>
          <p className="text-[9px] font-semibold text-slate-500 tracking-widest mb-3">BUDGET (₹/sqft)</p>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[11px] text-slate-400">Min</span>
                <span className="text-[11px] font-semibold text-slate-200">
                  ₹{filters.minPriceSqft.toLocaleString('en-IN')}
                </span>
              </div>
              <input
                type="range" min={0} max={20000} step={500} value={filters.minPriceSqft}
                onChange={e => onChange({ ...filters, minPriceSqft: Number(e.target.value) })}
                className="w-full h-1 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-slate-700 to-cyan-500/40 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[11px] text-slate-400">Max</span>
                <span className="text-[11px] font-semibold text-slate-200">
                  {filters.maxPriceSqft >= DEFAULT_FILTERS.maxPriceSqft
                    ? 'Any'
                    : `₹${filters.maxPriceSqft.toLocaleString('en-IN')}`}
                </span>
              </div>
              <input
                type="range" min={0} max={25000} step={500} value={filters.maxPriceSqft}
                onChange={e => onChange({ ...filters, maxPriceSqft: Number(e.target.value) })}
                className="w-full h-1 rounded-full appearance-none cursor-pointer bg-gradient-to-r from-slate-700 to-cyan-500/40 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer"
              />
            </div>
          </div>
        </section>
      </div>

      {/* Footer stats */}
      <div className="border-t border-slate-800 px-4 py-3">
        <div className="grid grid-cols-2 gap-3">
          {REC_ORDER.slice(0, 4).map(rec => {
            const color = REC_COLORS[rec]
            const shown = areas
              .filter(a => a.recommendation === rec)
              .filter(a => {
                if (filters.cities.length > 0 && !filters.cities.includes(a.city)) return false
                if (filters.recommendations.length > 0 && !filters.recommendations.includes(a.recommendation)) return false
                if (a.growth_score < filters.minGrowthScore) return false
                if (a.risk_score > filters.maxRiskScore) return false
                if (a.current_price_sqft < filters.minPriceSqft) return false
                if (a.current_price_sqft > filters.maxPriceSqft) return false
                return true
              }).length
            return (
              <div key={rec} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                <span className="text-[10px] text-slate-500 truncate">{rec}</span>
                <span className="text-[10px] font-semibold ml-auto" style={{ color }}>{shown}</span>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
