import { Bell, Settings, User, Menu } from 'lucide-react'
import { useLocation, Link } from 'react-router-dom'
import { useSubscription } from '@/context/SubscriptionContext'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/map': { title: 'Growth Map', subtitle: 'Visualize price-growth signals across India' },
  '/analyzer': { title: 'Area Analyzer', subtitle: 'Deep-dive report for any area' },
  '/opportunities': { title: 'Opportunity Finder', subtitle: 'Discover high-potential markets' },
  '/compare': { title: 'Compare Areas', subtitle: 'Side-by-side area analysis' },
  '/watchlist': { title: 'Watchlist', subtitle: 'Track areas you\'re monitoring' },
  '/reports': { title: 'Reports', subtitle: 'Export and share analysis' },
  '/data-sources': { title: 'Data Sources', subtitle: 'Signal feed status and coverage' },
  '/admin': { title: 'Admin', subtitle: 'Platform configuration and API keys' },
  '/pricing': { title: 'Pricing', subtitle: 'Plans and billing' },
}

interface TopBarProps {
  onMenuClick: () => void
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const { pathname } = useLocation()
  const { user, isLoggedIn } = useSubscription()
  const meta = PAGE_TITLES[pathname] ?? { title: 'LandSignal AI', subtitle: '' }

  return (
    <header
      className="flex items-center justify-between h-14 px-4 md:px-6 border-b border-[hsl(217_33%_16%)] bg-[hsl(222_47%_6%)] shrink-0"
      role="banner"
    >
      {/* Left: hamburger (mobile only) + page title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          className="md:hidden p-2 -ml-1 rounded-md text-[hsl(215_20%_50%)] hover:text-white hover:bg-[hsl(217_33%_14%)] transition-colors"
        >
          <Menu className="w-5 h-5" aria-hidden="true" />
        </button>
        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-white truncate">{meta.title}</h1>
          {meta.subtitle && (
            <p className="text-[11px] text-[hsl(215_20%_50%)] hidden sm:block truncate">{meta.subtitle}</p>
          )}
        </div>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          aria-label="Notifications"
          className="p-2 rounded-md text-[hsl(215_20%_50%)] hover:text-white hover:bg-[hsl(217_33%_14%)] transition-colors"
        >
          <Bell className="w-4 h-4" aria-hidden="true" />
        </button>
        <button
          aria-label="Settings"
          className="hidden sm:flex p-2 rounded-md text-[hsl(215_20%_50%)] hover:text-white hover:bg-[hsl(217_33%_14%)] transition-colors"
        >
          <Settings className="w-4 h-4" aria-hidden="true" />
        </button>
        <Link
          to="/admin"
          aria-label={isLoggedIn ? `Account: ${user?.email}` : 'Sign in'}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/40 ml-1 hover:bg-cyan-500/30 transition-colors"
        >
          <User className="w-4 h-4 text-cyan-400" aria-hidden="true" />
        </Link>
        {isLoggedIn && (
          <span className="hidden lg:block text-[11px] text-[hsl(215_20%_45%)] ml-1 max-w-[120px] truncate">
            {user?.plan?.slug ?? 'free'}
          </span>
        )}
      </div>
    </header>
  )
}
