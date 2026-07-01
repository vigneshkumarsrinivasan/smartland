import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import type { PricePoint, ForecastPoint } from '@/types/report'

interface ChartPoint {
  label: string
  actual?: number
  base?: number
  optimistic?: number
  risk?: number
}

function buildChartData(
  history: PricePoint[],
  forecast: { base: ForecastPoint[]; optimistic: ForecastPoint[]; risk: ForecastPoint[] },
  currentPrice: number,
): ChartPoint[] {
  // Annual historical: use Jan of each year (first occurrence per year)
  const byYear: Record<number, number> = {}
  for (const h of history) {
    const yr = new Date(h.date).getFullYear()
    if (!(yr in byYear)) byYear[yr] = h.price_sqft
  }

  const histPoints: ChartPoint[] = Object.entries(byYear)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([yr, price]) => ({ label: yr, actual: price }))

  // Anchor 2025 as current price shared by all series
  const anchor: ChartPoint = {
    label: '2025',
    actual: currentPrice,
    base: currentPrice,
    optimistic: currentPrice,
    risk: currentPrice,
  }

  // Forecast 2026-2035
  const forecastPoints: ChartPoint[] = forecast.base.slice(1).map((b, i) => ({
    label: String(b.year),
    base: b.price_sqft,
    optimistic: forecast.optimistic[i + 1].price_sqft,
    risk: forecast.risk[i + 1].price_sqft,
  }))

  return [...histPoints, anchor, ...forecastPoints]
}

function fmtPrice(v: number) {
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`
  if (v >= 1000) return `₹${(v / 1000).toFixed(0)}K`
  return `₹${v}`
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-xs shadow-xl">
      <p className="text-slate-400 font-semibold mb-1.5">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 py-0.5">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-400">{p.name}</span>
          <span className="font-semibold text-slate-200 ml-auto pl-3">
            {p.value ? fmtPrice(p.value) : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

interface Props {
  history: PricePoint[]
  forecast: { base: ForecastPoint[]; optimistic: ForecastPoint[]; risk: ForecastPoint[] }
  currentPrice: number
}

export function ForecastChart({ history, forecast, currentPrice }: Props) {
  const data = buildChartData(history, forecast, currentPrice)

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-200 mb-0.5">Price Forecast</h3>
      <p className="text-[11px] text-slate-500 mb-4">
        Historical (2022–2024) + projected scenarios (2025–2035)
      </p>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />

          <XAxis
            dataKey="label"
            tick={{ fill: '#475569', fontSize: 11 }}
            axisLine={{ stroke: '#1e293b' }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={fmtPrice}
            tick={{ fill: '#475569', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend
            wrapperStyle={{ fontSize: '11px', paddingTop: '12px', color: '#94a3b8' }}
          />

          {/* Separator between history and forecast */}
          <ReferenceLine x="2025" stroke="#334155" strokeDasharray="4 2" label={{ value: 'Today', fill: '#475569', fontSize: 10, position: 'insideTopLeft' }} />

          <Line
            dataKey="actual"
            name="Actual"
            stroke="#94a3b8"
            strokeWidth={2}
            dot={{ r: 3, fill: '#94a3b8' }}
            connectNulls
          />
          <Line
            dataKey="base"
            name="Base"
            stroke="#06b6d4"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            connectNulls
          />
          <Line
            dataKey="optimistic"
            name="Optimistic"
            stroke="#10b981"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
            connectNulls
          />
          <Line
            dataKey="risk"
            name="Risk"
            stroke="#ef4444"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="text-[10px] text-slate-600 mt-3">
        Base: growth_score × 0.20% pa · Optimistic: ×1.25 · Risk: ×0.60
      </p>
    </div>
  )
}
