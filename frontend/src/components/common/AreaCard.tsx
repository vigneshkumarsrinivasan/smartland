import { Bookmark, BookmarkCheck, ArrowRight, TrendingUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { REC_COLORS } from '@/lib/markerColors'
import { useWatchlist } from '@/context/WatchlistContext'
import type { AreaSummary } from '@/types/area'

const REC_STYLE: Record<string, string> = {
  'Strong Buy': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  'Buy':        'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  'Hold':       'text-amber-400 bg-amber-500/10 border-amber-500/30',
  'Avoid':      'text-red-400 bg-red-500/10 border-red-500/30',
  'Sell':       'text-orange-400 bg-orange-500/10 border-orange-500/30',
}

interface Props {
  area: AreaSummary
  rank?: number
  topDriver?: string
  opportunityScore?: number
}

export function AreaCard({ area, rank, topDriver, opportunityScore }: Props) {
  const navigate = useNavigate()
  const { isWatched, toggle } = useWatchlist()
  const watched = isWatched(area.id)
  const recStyle = REC_STYLE[area.recommendation] ?? 'text-slate-400 bg-slate-500/10 border-slate-500/30'
  const recColor = REC_COLORS[area.recommendation] ?? '#94a3b8'

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 hover:border-slate-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2.5">
          {rank != null && (
            <span className="mt-0.5 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold text-slate-500 bg-slate-800 shrink-0">
              {rank}
            </span>
          )}
          <div>
            <p className="text-sm font-semibold text-slate-200 leading-tight">{area.name}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">{area.city} · {area.land_type}</p>
          </div>
        </div>
        <span className={cn('shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border', recStyle)}>
          {area.recommendation.toUpperCase()}
        </span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <p className="text-[9px] text-slate-500 tracking-widest">PRICE</p>
          <p className="text-[13px] font-semibold text-slate-200">₹{area.current_price_sqft.toLocaleString('en-IN')}</p>
          <p className="text-[9px] text-slate-600">per sqft</p>
        </div>
        <div>
          <p className="text-[9px] text-slate-500 tracking-widest">GROWTH</p>
          <p className="text-[13px] font-semibold" style={{ color: recColor }}>{area.growth_score}</p>
          <p className="text-[9px] text-slate-600">/ 100</p>
        </div>
        <div>
          <p className="text-[9px] text-slate-500 tracking-widest">CAGR</p>
          <p className="text-[13px] font-semibold text-emerald-400">
            {area.cagr_pct != null ? `${area.cagr_pct.toFixed(1)}%` : '—'}
          </p>
          <p className="text-[9px] text-slate-600">3-year</p>
        </div>
      </div>

      {/* Score bars */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 w-12">Growth</span>
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-cyan-500" style={{ width: `${area.growth_score}%` }} />
          </div>
          <span className="text-[9px] text-slate-400 w-6 text-right">{area.growth_score}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 w-12">Risk</span>
          <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${area.risk_score}%`,
                background: area.risk_score > 60 ? '#ef4444' : area.risk_score > 40 ? '#f59e0b' : '#10b981',
              }}
            />
          </div>
          <span className="text-[9px] text-slate-400 w-6 text-right">{area.risk_score}</span>
        </div>
      </div>

      {/* Driver tag */}
      {topDriver && (
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-3 h-3 text-slate-500 shrink-0" />
          <span className="text-[10px] text-slate-500 truncate">{topDriver}</span>
        </div>
      )}

      {/* Opportunity score */}
      {opportunityScore != null && (
        <div className="flex items-center justify-between border-t border-slate-800 pt-2.5">
          <span className="text-[10px] text-slate-500">Opportunity score</span>
          <span className="text-[12px] font-bold text-cyan-400">{opportunityScore.toFixed(1)}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-auto border-t border-slate-800 pt-2.5">
        <button
          onClick={() => toggle(area.id)}
          className={cn(
            'flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-md border transition-colors',
            watched
              ? 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30 hover:bg-cyan-500/20'
              : 'text-slate-500 border-slate-700 hover:text-slate-300 hover:border-slate-600'
          )}
        >
          {watched ? <BookmarkCheck className="w-3 h-3" /> : <Bookmark className="w-3 h-3" />}
          {watched ? 'Watching' : 'Watch'}
        </button>
        <button
          onClick={() => navigate(`/analyzer?area=${area.id}`)}
          className="flex items-center gap-1.5 text-[11px] px-2.5 py-1.5 rounded-md border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors ml-auto"
        >
          Analyze <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
