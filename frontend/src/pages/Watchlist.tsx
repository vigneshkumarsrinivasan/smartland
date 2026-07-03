import { useState } from 'react'
import { Bookmark, Bell, BellOff, X, Check } from 'lucide-react'
import { useWatchlist } from '@/context/WatchlistContext'
import { useAreas } from '@/hooks/useAreas'
import { AreaCard } from '@/components/common/AreaCard'
import { useSubscription } from '@/context/SubscriptionContext'
import { LoginModal } from '@/components/ui/LoginModal'
import { API_BASE } from '@/lib/api'

interface AlertConfig {
  area_id: number
  alert_type: string
  channel: string
  threshold: number
  phone: string
}

const DEFAULT_CONFIG: Omit<AlertConfig, 'area_id'> = {
  alert_type: 'price_movement',
  channel: 'email',
  threshold: 5,
  phone: '',
}

export default function Watchlist() {
  const { watchlist } = useWatchlist()
  const { areas, loading } = useAreas()
  const { isLoggedIn, token } = useSubscription()

  const [configAreaId, setConfigAreaId] = useState<number | null>(null)
  const [config, setConfig] = useState<Omit<AlertConfig, 'area_id'>>(DEFAULT_CONFIG)
  const [saving, setSaving] = useState(false)
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set())
  const [showLogin, setShowLogin] = useState(false)

  const watched = areas.filter(a => watchlist.includes(a.id))

  const openConfig = (areaId: number) => {
    if (!isLoggedIn) { setShowLogin(true); return }
    setConfigAreaId(areaId)
    setConfig(DEFAULT_CONFIG)
  }

  const saveAlert = async () => {
    if (!configAreaId || !token) return
    setSaving(true)
    try {
      const body: AlertConfig = { area_id: configAreaId, ...config }
      const res = await fetch(`${API_BASE}/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        setSavedIds(prev => new Set([...prev, configAreaId]))
        setConfigAreaId(null)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 text-sm">
        Loading…
      </div>
    )
  }

  if (watchlist.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
        <Bookmark className="w-10 h-10 opacity-20" />
        <p className="text-sm">No areas watched yet</p>
        <p className="text-[11px] text-slate-700">
          Click the bookmark icon on any area card to add it here
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-y-auto h-full">
      <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
        <span className="text-[11px] text-slate-500">
          {watched.length} area{watched.length !== 1 ? 's' : ''} on watchlist
        </span>
        <span className="text-[11px] text-slate-600">
          {isLoggedIn ? 'Click Bell to set alerts' : 'Sign in to enable alerts'}
        </span>
      </div>

      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {watched.map((area, i) => (
          <div key={area.id} className="relative group">
            <AreaCard area={area} rank={i + 1} />
            <button
              onClick={() => openConfig(area.id)}
              className="absolute top-2 right-2 p-1.5 rounded-md bg-slate-900/80 border border-slate-700 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Set price alert"
            >
              {savedIds.has(area.id)
                ? <Bell className="w-3.5 h-3.5 text-cyan-400" />
                : <BellOff className="w-3.5 h-3.5 text-slate-400" />}
            </button>
          </div>
        ))}
      </div>

      {/* Alert config modal */}
      {configAreaId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="relative w-full max-w-sm rounded-xl border border-[hsl(217_33%_20%)] bg-[hsl(222_47%_8%)] p-6 shadow-2xl">
            <button
              onClick={() => setConfigAreaId(null)}
              className="absolute top-4 right-4 text-slate-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
            <h3 className="text-base font-semibold text-white mb-1">Set Alert</h3>
            <p className="text-xs text-slate-500 mb-5">
              {watched.find(a => a.id === configAreaId)?.name}
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Alert type</label>
                <select
                  value={config.alert_type}
                  onChange={e => setConfig(c => ({ ...c, alert_type: e.target.value }))}
                  className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/60"
                >
                  <option value="price_movement">Price movement</option>
                  <option value="score_change">Score change</option>
                  <option value="weekly_digest">Weekly digest</option>
                </select>
              </div>

              {config.alert_type !== 'weekly_digest' && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Threshold ({config.alert_type === 'price_movement' ? '% price change' : 'score points'})
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={config.threshold}
                    onChange={e => setConfig(c => ({ ...c, threshold: Number(e.target.value) }))}
                    className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/60"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Channel</label>
                <select
                  value={config.channel}
                  onChange={e => setConfig(c => ({ ...c, channel: e.target.value }))}
                  className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/60"
                >
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="both">Email + WhatsApp</option>
                </select>
              </div>

              {(config.channel === 'whatsapp' || config.channel === 'both') && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    WhatsApp number (E.164, e.g. 919876543210)
                  </label>
                  <input
                    type="tel"
                    value={config.phone}
                    onChange={e => setConfig(c => ({ ...c, phone: e.target.value }))}
                    placeholder="919876543210"
                    className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/60"
                  />
                </div>
              )}
            </div>

            <button
              onClick={saveAlert}
              disabled={saving}
              className="mt-5 w-full flex items-center justify-center gap-2 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-60 text-black font-medium text-sm py-2 rounded-lg transition-colors"
            >
              {saving ? 'Saving…' : <><Check className="w-4 h-4" /> Save alert</>}
            </button>
          </div>
        </div>
      )}

      {showLogin && (
        <LoginModal
          onSuccess={() => setShowLogin(false)}
          onClose={() => setShowLogin(false)}
        />
      )}
    </div>
  )
}
