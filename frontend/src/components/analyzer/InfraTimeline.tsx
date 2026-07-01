import { cn } from '@/lib/utils'
import type { InfraProject } from '@/types/report'

const STATUS_STYLE: Record<string, { dot: string; badge: string }> = {
  'Completed':         { dot: 'bg-emerald-500', badge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25' },
  'Under Construction':{ dot: 'bg-amber-400',   badge: 'text-amber-400 bg-amber-500/10 border-amber-500/25' },
  'Announced':         { dot: 'bg-blue-400',    badge: 'text-blue-400 bg-blue-500/10 border-blue-500/25' },
}

const TYPE_ICONS: Record<string, string> = {
  'Metro':       '🚇',
  'Highway':     '🛣️',
  'Airport':     '✈️',
  'IT Park':     '🏢',
  'Industrial':  '🏭',
  'Commercial':  '🏪',
  'Infrastructure': '⚙️',
}

interface Props { projects: InfraProject[] }

export function InfraTimeline({ projects }: Props) {
  const sorted = [...projects].sort((a, b) => a.target_year - b.target_year)

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-200 mb-1">Infrastructure Pipeline</h3>
      <p className="text-[11px] text-slate-500 mb-4">{projects.length} projects · sorted by target year</p>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[17px] top-2 bottom-2 w-px bg-slate-800" />

        <div className="space-y-4">
          {sorted.map((p, i) => {
            const style = STATUS_STYLE[p.status] ?? STATUS_STYLE['Announced']
            const icon = TYPE_ICONS[p.type] ?? '📌'

            return (
              <div key={i} className="flex gap-4 relative">
                {/* Dot */}
                <div className={cn('w-[9px] h-[9px] rounded-full shrink-0 mt-1.5 ml-[13px] z-10', style.dot)} />

                {/* Content */}
                <div className="flex-1 min-w-0 pb-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[12px] font-medium text-slate-200 leading-snug">{icon} {p.name}</p>
                    <span className="text-[11px] font-bold text-slate-400 shrink-0">{p.target_year}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
                      {p.type}
                    </span>
                    <span className={cn('text-[9px] font-semibold px-1.5 py-0.5 rounded border', style.badge)}>
                      {p.status.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-slate-500 ml-auto">
                      Impact: <span className="text-cyan-400 font-semibold">{p.impact_score}/10</span>
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
