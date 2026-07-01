import { NavLink } from 'react-router-dom'
import {
  Map, BarChart2, Compass, GitCompare, Bookmark,
  FileText, Database, ShieldCheck, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/map', icon: Map, label: 'Growth Map' },
  { to: '/analyzer', icon: BarChart2, label: 'Area Analyzer' },
  { to: '/opportunities', icon: Compass, label: 'Opportunity Finder' },
  { to: '/compare', icon: GitCompare, label: 'Compare Areas' },
  { to: '/watchlist', icon: Bookmark, label: 'Watchlist' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/data-sources', icon: Database, label: 'Data Sources' },
  { to: '/admin', icon: ShieldCheck, label: 'Admin' },
]

export function Sidebar() {
  return (
    <aside className="flex flex-col w-[220px] min-h-screen bg-[hsl(222_47%_7%)] border-r border-[hsl(217_33%_16%)] shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-[hsl(217_33%_16%)]">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40">
          <Zap className="w-4 h-4 text-cyan-400" />
        </div>
        <div>
          <div className="text-sm font-bold text-white leading-none">LandSignal</div>
          <div className="text-[10px] text-cyan-400 font-medium tracking-wider leading-none mt-0.5">AI</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-cyan-500/15 text-cyan-400 font-medium'
                  : 'text-[hsl(215_20%_55%)] hover:text-white hover:bg-[hsl(217_33%_14%)]'
              )
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[hsl(217_33%_16%)]">
        <p className="text-[10px] text-[hsl(215_20%_40%)] leading-relaxed">
          We don't list land.<br />We predict its future.
        </p>
      </div>
    </aside>
  )
}
