import type { AreaReport } from '@/types/report'
import { REC_COLORS } from '@/lib/markerColors'
import { cn } from '@/lib/utils'

const REC_BG: Record<string, string> = {
  'Strong Buy': 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
  'Buy':        'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
  'Hold':       'bg-amber-500/10 border-amber-500/30 text-amber-400',
  'Avoid':      'bg-red-500/10 border-red-500/30 text-red-400',
  'Sell':       'bg-orange-500/10 border-orange-500/30 text-orange-400',
}

function fmt(n: number) {
  return n.toLocaleString('en-IN')
}

interface Props { report: AreaReport }

export function SummaryCard({ report }: Props) {
  const { area, forecast } = report
  const recColor = REC_COLORS[area.recommendation] ?? '#94a3b8'
  const recClass = REC_BG[area.recommendation] ?? 'bg-slate-500/10 border-slate-500/30 text-slate-400'

  // Extract forecast prices for 1, 3, 5, 10 years from base scenario
  const base = forecast.base
  const f1  = base[1]?.price_sqft
  const f3  = base[3]?.price_sqft
  const f5  = base[5]?.price_sqft
  const f10 = base[10]?.price_sqft

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      {/* Top row */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-bold text-white">{area.name}</h2>
          <p className="text-sm text-slate-400 mt-0.5">{area.city} · {area.land_type}</p>
        </div>
        <span
          className={cn('shrink-0 px-4 py-1.5 rounded-full border text-sm font-bold tracking-wide', recClass)}
        >
          {area.recommendation.toUpperCase()}
        </span>
      </div>

      {/* Price + forecast row */}
      <div className="grid grid-cols-5 gap-3 mb-5 pb-5 border-b border-slate-800">
        <div className="col-span-1">
          <p className="text-[10px] text-slate-500 tracking-widest mb-1">NOW</p>
          <p className="text-2xl font-bold text-white">₹{fmt(area.current_price_sqft)}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">per sqft</p>
        </div>
        {[
          { label: '+1 YR', val: f1 },
          { label: '+3 YR', val: f3 },
          { label: '+5 YR', val: f5 },
          { label: '+10 YR', val: f10 },
        ].map(({ label, val }) => {
          const pct = val && area.current_price_sqft
            ? ((val - area.current_price_sqft) / area.current_price_sqft * 100).toFixed(0)
            : null
          return (
            <div key={label} className="bg-slate-800/60 rounded-lg px-3 py-2.5">
              <p className="text-[10px] text-slate-500 tracking-widest mb-1">{label}</p>
              <p className="text-base font-semibold text-slate-200">
                {val ? `₹${fmt(val)}` : '—'}
              </p>
              {pct && (
                <p className="text-[10px] font-medium mt-0.5" style={{ color: recColor }}>
                  +{pct}%
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Scores row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'GROWTH SCORE', val: area.growth_score, color: '#06b6d4', suffix: '/100' },
          { label: 'RISK SCORE',   val: area.risk_score,   color: area.risk_score > 60 ? '#ef4444' : area.risk_score > 40 ? '#f59e0b' : '#10b981', suffix: '/100' },
          { label: 'CONFIDENCE',  val: area.confidence_score, color: '#a78bfa', suffix: '%' },
          { label: '3-YR CAGR',  val: area.cagr_pct ?? 0, color: '#10b981', suffix: '%' },
        ].map(({ label, val, color, suffix }) => (
          <div key={label}>
            <p className="text-[10px] text-slate-500 tracking-widest mb-1">{label}</p>
            <div className="flex items-end gap-0.5">
              <span className="text-2xl font-bold" style={{ color }}>{val.toFixed(1)}</span>
              <span className="text-sm text-slate-500 mb-0.5">{suffix}</span>
            </div>
            <div className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${Math.min(val, 100)}%`, background: color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
