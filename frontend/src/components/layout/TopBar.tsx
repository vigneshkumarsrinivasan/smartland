import { Bell, Settings, User } from 'lucide-react'
import { useLocation } from 'react-router-dom'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/map': { title: 'Growth Map', subtitle: 'Visualize price-growth signals across India' },
  '/analyzer': { title: 'Area Analyzer', subtitle: 'Deep-dive report for any area' },
  '/opportunities': { title: 'Opportunity Finder', subtitle: 'Discover high-potential markets' },
  '/compare': { title: 'Compare Areas', subtitle: 'Side-by-side area analysis' },
  '/watchlist': { title: 'Watchlist', subtitle: 'Track areas you\'re monitoring' },
  '/reports': { title: 'Reports', subtitle: 'Export and share analysis' },
  '/data-sources': { title: 'Data Sources', subtitle: 'Signal feed status and coverage' },
  '/admin': { title: 'Admin', subtitle: 'Platform configuration' },
}

export function TopBar() {
  const { pathname } = useLocation()
  const meta = PAGE_TITLES[pathname] ?? { title: 'LandSignal AI', subtitle: '' }

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-[hsl(217_33%_16%)] bg-[hsl(222_47%_6%)] shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-white">{meta.title}</h1>
        {meta.subtitle && (
          <p className="text-[11px] text-[hsl(215_20%_50%)]">{meta.subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button className="p-2 rounded-md text-[hsl(215_20%_50%)] hover:text-white hover:bg-[hsl(217_33%_14%)] transition-colors">
          <Bell className="w-4 h-4" />
        </button>
        <button className="p-2 rounded-md text-[hsl(215_20%_50%)] hover:text-white hover:bg-[hsl(217_33%_14%)] transition-colors">
          <Settings className="w-4 h-4" />
        </button>
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/40 ml-2">
          <User className="w-4 h-4 text-cyan-400" />
        </div>
      </div>
    </header>
  )
}
