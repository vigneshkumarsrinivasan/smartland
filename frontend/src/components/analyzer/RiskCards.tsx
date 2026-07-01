import { cn } from '@/lib/utils'
import type { RiskSignals } from '@/types/report'

const RISK_FACTORS: { key: keyof RiskSignals; label: string; desc: string; weight: number }[] = [
  { key: 'flood',         label: 'Flood Risk',        desc: 'Proximity to flood zones & drainage', weight: 0.20 },
  { key: 'water',         label: 'Water Scarcity',    desc: 'Groundwater table & supply reliability', weight: 0.20 },
  { key: 'legal',         label: 'Legal / Title',     desc: 'Land disputes & encumbrance status', weight: 0.20 },
  { key: 'overvaluation', label: 'Overvaluation',     desc: 'Price vs. intrinsic value gap', weight: 0.15 },
  { key: 'pollution',     label: 'Pollution',         desc: 'Air, water & noise pollution levels', weight: 0.10 },
  { key: 'crime',         label: 'Crime Index',       desc: 'Local crime rate vs. city average', weight: 0.10 },
  { key: 'delay',         label: 'Project Delay',     desc: 'Infrastructure execution risk', weight: 0.05 },
]

function riskLevel(score: number): { label: string; cls: string; bar: string } {
  if (score < 30) return { label: 'Low',      cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25', bar: '#10b981' }
  if (score < 50) return { label: 'Moderate', cls: 'text-amber-400 bg-amber-500/10 border-amber-500/25',   bar: '#f59e0b' }
  if (score < 70) return { label: 'High',     cls: 'text-orange-400 bg-orange-500/10 border-orange-500/25', bar: '#f97316' }
  return           { label: 'Critical',  cls: 'text-red-400 bg-red-500/10 border-red-500/25',       bar: '#ef4444' }
}

interface Props { signals: RiskSignals }

export function RiskCards({ signals }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-200 mb-1">Risk Breakdown</h3>
      <p className="text-[11px] text-slate-500 mb-4">Seven-factor risk model (higher = more risk)</p>

      <div className="space-y-3">
        {RISK_FACTORS.map(({ key, label, desc, weight }) => {
          const score = signals[key]
          const { label: lvl, cls, bar } = riskLevel(score)

          return (
            <div key={key} className="flex items-center gap-3">
              {/* Score circle */}
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold border"
                style={{ background: `${bar}15`, color: bar, borderColor: `${bar}30` }}
              >
                {score}
              </div>

              {/* Label + bar */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] font-medium text-slate-300">{label}</span>
                  <span className={cn('text-[9px] font-semibold px-1.5 py-0.5 rounded border', cls)}>
                    {lvl.toUpperCase()}
                  </span>
                </div>
                <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${score}%`, background: bar }}
                  />
                </div>
                <p className="text-[10px] text-slate-600 mt-0.5">{desc} · ×{(weight * 100).toFixed(0)}% weight</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
