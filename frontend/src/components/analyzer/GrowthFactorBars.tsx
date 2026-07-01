import type { GrowthSignals } from '@/types/report'

const FACTORS: { key: keyof GrowthSignals; label: string; weight: number }[] = [
  { key: 'infrastructure',       label: 'Infrastructure',       weight: 0.25 },
  { key: 'job_growth',           label: 'Job Growth',           weight: 0.20 },
  { key: 'population_growth',    label: 'Population Growth',    weight: 0.15 },
  { key: 'commercial_activity',  label: 'Commercial Activity',  weight: 0.10 },
  { key: 'transaction_velocity', label: 'Transaction Velocity', weight: 0.10 },
  { key: 'land_scarcity',        label: 'Land Scarcity',        weight: 0.10 },
  { key: 'government_spending',  label: 'Govt. Spending',       weight: 0.10 },
]

function barColor(score: number) {
  if (score >= 75) return '#10b981'
  if (score >= 55) return '#06b6d4'
  if (score >= 40) return '#f59e0b'
  return '#ef4444'
}

interface Props { signals: GrowthSignals }

export function GrowthFactorBars({ signals }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-200 mb-1">Growth Drivers</h3>
      <p className="text-[11px] text-slate-500 mb-4">Weighted contribution to growth score</p>

      <div className="space-y-3.5">
        {FACTORS.map(({ key, label, weight }) => {
          const score = signals[key]
          const contribution = score * weight
          const color = barColor(score)

          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-300 font-medium">{label}</span>
                  <span className="text-[10px] text-slate-600">×{(weight * 100).toFixed(0)}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">
                    +{contribution.toFixed(1)} pts
                  </span>
                  <span className="text-[11px] font-semibold w-8 text-right" style={{ color }}>
                    {score}
                  </span>
                </div>
              </div>
              <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${score}%`, background: color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
