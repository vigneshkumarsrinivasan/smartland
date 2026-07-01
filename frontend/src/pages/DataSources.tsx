import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Database } from 'lucide-react'
import { useDataSources } from '@/hooks/useDataSources'
import { cn } from '@/lib/utils'

const STATUS_CONFIG = {
  active:   { label: 'Active',   icon: CheckCircle,   cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  degraded: { label: 'Degraded', icon: AlertTriangle,  cls: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  offline:  { label: 'Offline',  icon: XCircle,        cls: 'text-red-400 bg-red-500/10 border-red-500/30' },
} as const

const CATEGORY_COLORS: Record<string, string> = {
  'Government':   'text-violet-400',
  'Transaction':  'text-cyan-400',
  'Demographic':  'text-blue-400',
  'Economic':     'text-emerald-400',
  'Environmental':'text-amber-400',
  'News':         'text-pink-400',
}

export default function DataSources() {
  const { sources, loading, error } = useDataSources()

  const activeCount   = sources.filter(s => s.status === 'active').length
  const degradedCount = sources.filter(s => s.status === 'degraded').length
  const offlineCount  = sources.filter(s => s.status === 'offline').length

  return (
    <div className="overflow-y-auto h-full">
      {/* Summary bar */}
      <div className="px-5 py-3 border-b border-slate-800 bg-slate-950 flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-[11px] text-slate-500">{sources.length} total feeds</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-[11px] text-slate-500">{activeCount} active</span>
        </div>
        {degradedCount > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-[11px] text-slate-500">{degradedCount} degraded</span>
          </div>
        )}
        {offlineCount > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-[11px] text-slate-500">{offlineCount} offline</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-1.5 text-[11px] text-slate-600">
          <RefreshCw className="w-3 h-3" />
          <span>Last sync: just now</span>
        </div>
      </div>

      {/* Content */}
      {loading && (
        <div className="flex items-center justify-center h-48 text-slate-600 text-sm">Loading…</div>
      )}

      {error && (
        <div className="m-5 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-[11px]">
          Failed to load data sources: {error}
        </div>
      )}

      {!loading && !error && (
        <div className="p-5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left px-4 py-2.5 text-slate-600 tracking-widest text-[9px] font-semibold">SOURCE</th>
                  <th className="text-left px-4 py-2.5 text-slate-600 tracking-widest text-[9px] font-semibold">CATEGORY</th>
                  <th className="text-left px-4 py-2.5 text-slate-600 tracking-widest text-[9px] font-semibold">COVERAGE</th>
                  <th className="text-left px-4 py-2.5 text-slate-600 tracking-widest text-[9px] font-semibold">LAST UPDATED</th>
                  <th className="text-left px-4 py-2.5 text-slate-600 tracking-widest text-[9px] font-semibold">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(src => {
                  const cfg = STATUS_CONFIG[src.status]
                  const Icon = cfg.icon
                  return (
                    <tr key={src.id} className="border-b border-slate-800/60 hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <p className="text-slate-200 font-medium">{src.name}</p>
                        {src.description && (
                          <p className="text-[10px] text-slate-600 mt-0.5">{src.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('font-medium', CATEGORY_COLORS[src.category] ?? 'text-slate-400')}>
                          {src.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{src.coverage ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-500">{src.last_updated ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span className={cn('inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full border', cfg.cls)}>
                          <Icon className="w-3 h-3" />
                          {cfg.label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
