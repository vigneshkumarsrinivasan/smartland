import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Loader2, AlertCircle, Sparkles } from 'lucide-react'
import { useAreas } from '@/hooks/useAreas'
import { useAreaReport } from '@/hooks/useAreaReport'
import { SummaryCard } from '@/components/analyzer/SummaryCard'
import { GrowthFactorBars } from '@/components/analyzer/GrowthFactorBars'
import { RiskCards } from '@/components/analyzer/RiskCards'
import { ForecastChart } from '@/components/analyzer/ForecastChart'
import { InfraTimeline } from '@/components/analyzer/InfraTimeline'

export default function AreaAnalyzer() {
  const { areas } = useAreas()
  const [searchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  // Pre-select area from ?area= query param (set by AreaCard "Analyze →" button)
  useEffect(() => {
    const param = searchParams.get('area')
    if (param) setSelectedId(Number(param))
  }, [searchParams])
  const { report, loading, error } = useAreaReport(selectedId)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Search bar */}
      <div className="shrink-0 border-b border-slate-800 bg-slate-950 px-6 py-3">
        <div className="flex items-center gap-3 max-w-lg">
          <Search className="w-4 h-4 text-slate-500 shrink-0" />
          <select
            value={selectedId ?? ''}
            onChange={e => setSelectedId(e.target.value ? Number(e.target.value) : null)}
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/30 transition-colors appearance-none cursor-pointer"
          >
            <option value="">Select an area to analyze…</option>
            {areas.map(a => (
              <option key={a.id} value={a.id}>
                {a.name} — {a.city} &nbsp;·&nbsp; {a.recommendation} &nbsp;·&nbsp; ₹{a.current_price_sqft.toLocaleString('en-IN')}/sqft
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {!selectedId && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
            <Search className="w-10 h-10 opacity-20" />
            <p className="text-sm">Select an area above to view its full intelligence report</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-full gap-3 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
            <span className="text-sm">Loading report…</span>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-3 bg-slate-900 border border-red-500/30 rounded-xl px-5 py-4">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
              <div>
                <p className="text-sm text-slate-200 font-medium">Failed to load report</p>
                <p className="text-xs text-slate-500 mt-0.5">{error}</p>
              </div>
            </div>
          </div>
        )}

        {report && !loading && (
          <div className="p-6 space-y-4 max-w-5xl mx-auto">
            {/* Summary card */}
            <SummaryCard report={report} />

            {/* AI Summary */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-slate-200">Signal Intelligence</h3>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{report.ai_summary}</p>
            </div>

            {/* Forecast chart (full width) */}
            <ForecastChart
              history={report.price_history}
              forecast={report.forecast}
              currentPrice={report.area.current_price_sqft}
            />

            {/* Growth factors + Risk cards side by side */}
            <div className="grid grid-cols-2 gap-4">
              <GrowthFactorBars signals={report.growth_signals} />
              <RiskCards signals={report.risk_signals} />
            </div>

            {/* Infrastructure timeline */}
            <InfraTimeline projects={report.infrastructure_projects} />
          </div>
        )}
      </div>
    </div>
  )
}
