import { useState, useMemo } from 'react'
import { X, BarChart3 } from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend,
} from 'recharts'
import { useAreas } from '@/hooks/useAreas'
import { cn } from '@/lib/utils'
import type { AreaSummary } from '@/types/area'

const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#a78bfa', '#f87171']

const REC_BADGE: Record<string, string> = {
  'Strong Buy': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  'Buy':        'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  'Hold':       'text-amber-400 bg-amber-500/10 border-amber-500/30',
  'Avoid':      'text-red-400 bg-red-500/10 border-red-500/30',
}

const METRICS: { key: keyof AreaSummary; label: string; fmt: (v: unknown) => string }[] = [
  { key: 'current_price_sqft', label: 'Price / sqft', fmt: v => `₹${(v as number).toLocaleString('en-IN')}` },
  { key: 'growth_score',       label: 'Growth Score', fmt: v => `${v}` },
  { key: 'risk_score',         label: 'Risk Score',   fmt: v => `${v}` },
  { key: 'confidence_score',   label: 'Confidence',   fmt: v => v != null ? `${v}` : '—' },
  { key: 'cagr_pct',           label: '3yr CAGR',     fmt: v => v != null ? `${(v as number).toFixed(1)}%` : '—' },
  { key: 'recommendation',     label: 'Signal',       fmt: v => `${v}` },
  { key: 'land_type',          label: 'Type',         fmt: v => `${v}` },
]

// Radar factor weights — mirrors scoring.py
const FACTOR_WEIGHTS = [0.20, 0.17, 0.13, 0.13, 0.10, 0.15, 0.12]
const RADAR_FACTORS = ['Infrastructure', 'Jobs', 'Population', 'Commercial', 'Transactions', 'Scarcity', 'Gov. Spend']

function buildRadarData(areas: AreaSummary[]) {
  return RADAR_FACTORS.map((factor, i) => {
    const row: Record<string, unknown> = { factor }
    areas.forEach(a => {
      row[a.name] = Math.round(a.growth_score * FACTOR_WEIGHTS[i] * 5)
    })
    return row
  })
}

export default function CompareAreas() {
  const { areas, loading } = useAreas()
  const [selected, setSelected] = useState<number[]>([])

  const selectedAreas = useMemo(
    () => selected.map(id => areas.find(a => a.id === id)).filter(Boolean) as AreaSummary[],
    [selected, areas]
  )

  const radarData = useMemo(() => buildRadarData(selectedAreas), [selectedAreas])

  function addArea(id: number) {
    if (selected.length >= 5 || selected.includes(id)) return
    setSelected(prev => [...prev, id])
  }

  function removeArea(id: number) {
    setSelected(prev => prev.filter(x => x !== id))
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Picker bar */}
      <div className="shrink-0 px-4 md:px-5 py-3 border-b border-slate-800 bg-slate-950 flex items-center gap-2 flex-wrap">
        <span className="text-[11px] text-slate-500 shrink-0">Add area (up to 5):</span>
        <select
          className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-[11px] text-slate-300 focus:outline-none"
          value=""
          onChange={e => e.target.value && addArea(Number(e.target.value))}
          disabled={loading || selected.length >= 5}
        >
          <option value="">— select area —</option>
          {areas
            .filter(a => !selected.includes(a.id))
            .map(a => <option key={a.id} value={a.id}>{a.name} ({a.city})</option>)}
        </select>

        {selectedAreas.map((a, i) => (
          <span
            key={a.id}
            className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full border"
            style={{ borderColor: COLORS[i] + '60', color: COLORS[i], backgroundColor: COLORS[i] + '15' }}
          >
            {a.name}
            <button onClick={() => removeArea(a.id)} aria-label={`Remove ${a.name}`} className="hover:opacity-60 transition-opacity">
              <X className="w-3 h-3" aria-hidden="true" />
            </button>
          </span>
        ))}

        {selected.length === 0 && !loading && (
          <span className="text-[11px] text-slate-600 italic">Select 2–5 areas to compare</span>
        )}
      </div>

      {/* Body */}
      {selected.length < 2 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-600 gap-3">
          <BarChart3 className="w-12 h-12 opacity-15" />
          <p className="text-sm">Select at least 2 areas using the picker above</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Radar */}
          <section>
            <h3 className="text-[10px] font-semibold text-slate-500 tracking-widest mb-3">GROWTH FACTOR RADAR</h3>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                  <PolarGrid stroke="#1e293b" />
                  <PolarAngleAxis dataKey="factor" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <PolarRadiusAxis tick={false} axisLine={false} />
                  {selectedAreas.map((a, i) => (
                    <Radar
                      key={a.id}
                      name={a.name}
                      dataKey={a.name}
                      stroke={COLORS[i]}
                      fill={COLORS[i]}
                      fillOpacity={0.12}
                      strokeWidth={1.5}
                    />
                  ))}
                  <Legend
                    wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
                    formatter={(val, entry) => (
                      <span style={{ color: (entry as { color: string }).color }}>{val}</span>
                    )}
                  />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                    labelStyle={{ color: '#94a3b8', fontSize: 11 }}
                    itemStyle={{ fontSize: 11 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Metrics table */}
          <section>
            <h3 className="text-[10px] font-semibold text-slate-500 tracking-widest mb-3">SIDE-BY-SIDE METRICS</h3>
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden overflow-x-auto">
              <table className="w-full min-w-[400px] text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left px-4 py-2.5 text-slate-600 font-semibold tracking-widest text-[9px]">METRIC</th>
                    {selectedAreas.map((a, i) => (
                      <th
                        key={a.id}
                        className="text-right px-4 py-2.5 font-semibold"
                        style={{ color: COLORS[i] }}
                      >
                        {a.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRICS.map(m => (
                    <tr key={m.key} className="border-b border-slate-800/60 hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-2.5 text-slate-500">{m.label}</td>
                      {selectedAreas.map(a => {
                        const val = a[m.key]
                        const isRec = m.key === 'recommendation'
                        return (
                          <td key={a.id} className="px-4 py-2.5 text-right">
                            {isRec ? (
                              <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full border', REC_BADGE[val as string] ?? 'text-slate-400 border-slate-700')}>
                                {String(val).toUpperCase()}
                              </span>
                            ) : (
                              <span className="text-slate-300">{m.fmt(val)}</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Growth vs Risk bars */}
          <section>
            <h3 className="text-[10px] font-semibold text-slate-500 tracking-widest mb-3">GROWTH vs RISK PROFILE</h3>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              {selectedAreas.map((a, i) => (
                <div key={a.id} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium" style={{ color: COLORS[i] }}>{a.name}</span>
                    <span className="text-[10px] text-slate-500">Growth {a.growth_score} · Risk {a.risk_score}</span>
                  </div>
                  <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="absolute left-0 top-0 h-full rounded-full opacity-80"
                      style={{ width: `${a.growth_score}%`, background: COLORS[i] }}
                    />
                    <div
                      className="absolute left-0 top-0 h-full rounded-full"
                      style={{ width: `${a.risk_score}%`, background: 'rgba(239,68,68,0.45)' }}
                    />
                  </div>
                </div>
              ))}
              <p className="text-[9px] text-slate-600 pt-1">Bar = growth score; red overlay = risk exposure</p>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
