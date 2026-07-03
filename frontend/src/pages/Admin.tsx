import { useState, useEffect, useCallback } from 'react'
import { ShieldCheck, Key, Plus, Trash2, Copy, Check, AlertCircle } from 'lucide-react'
import { useSubscription } from '@/context/SubscriptionContext'
import { API_BASE } from '@/lib/api'
import { LoginModal } from '@/components/ui/LoginModal'

interface ApiKey {
  id: number
  name: string
  key_prefix: string
  scopes: string
  requests_per_minute: number
  last_used_at: string | null
  created_at: string
  key?: string  // only present at creation
}

export default function Admin() {
  const { isLoggedIn, token, user } = useSubscription()
  const [showLogin, setShowLogin] = useState(false)
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  const planSlug = user?.plan?.slug ?? 'free'
  const canCreateKey = planSlug === 'pro' || planSlug === 'enterprise'

  const fetchKeys = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) setKeys(await res.json())
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (isLoggedIn) fetchKeys()
  }, [isLoggedIn, fetchKeys])

  const createKey = async () => {
    if (!newKeyName.trim() || !token) return
    setCreating(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: newKeyName.trim(), scopes: 'read' }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Failed to create key')
        return
      }
      setCreatedKey(data.key)
      setNewKeyName('')
      fetchKeys()
    } finally {
      setCreating(false)
    }
  }

  const revokeKey = async (id: number) => {
    if (!token) return
    await fetch(`${API_BASE}/api-keys/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    setKeys(prev => prev.filter(k => k.id !== id))
  }

  const copyKey = () => {
    if (!createdKey) return
    navigator.clipboard.writeText(createdKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-[hsl(215_20%_50%)]">
        <ShieldCheck className="w-12 h-12 opacity-30" />
        <div className="text-center">
          <p className="text-lg font-medium text-[hsl(215_20%_65%)]">Admin</p>
          <p className="text-sm mt-1 mb-4">Sign in to manage API keys and account settings</p>
          <button
            onClick={() => setShowLogin(true)}
            className="bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-medium px-5 py-2 rounded-lg transition-colors"
          >
            Sign in
          </button>
        </div>
        {showLogin && (
          <LoginModal onSuccess={() => setShowLogin(false)} onClose={() => setShowLogin(false)} />
        )}
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <ShieldCheck className="w-6 h-6 text-cyan-400" />
        <div>
          <h1 className="text-lg font-semibold text-white">Admin</h1>
          <p className="text-xs text-[hsl(215_20%_45%)]">{user?.email} · {planSlug} plan</p>
        </div>
      </div>

      {/* API Keys section */}
      <div className="bg-[hsl(222_47%_8%)] border border-[hsl(217_33%_20%)] rounded-xl p-5 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-white">API Keys</h2>
          <span className="text-[10px] text-[hsl(215_20%_40%)] ml-auto">
            {planSlug === 'enterprise' ? '300 req/min' : planSlug === 'pro' ? '60 req/min' : 'Pro+ required'}
          </span>
        </div>

        {!canCreateKey && (
          <div className="flex items-center gap-3 bg-[hsl(222_47%_10%)] border border-[hsl(217_33%_22%)] rounded-lg px-4 py-3 mb-4">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <p className="text-xs text-[hsl(215_20%_60%)]">
              API keys are available on Pro and Enterprise plans.{' '}
              <a href="/pricing" className="text-cyan-400 hover:text-cyan-300">Upgrade →</a>
            </p>
          </div>
        )}

        {/* Created key banner */}
        {createdKey && (
          <div className="mb-4 bg-emerald-900/20 border border-emerald-500/30 rounded-lg p-4">
            <p className="text-xs font-medium text-emerald-400 mb-2">
              API key created — copy it now. It won't be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-black/30 rounded px-3 py-2 text-xs text-emerald-300 font-mono break-all">
                {createdKey}
              </code>
              <button onClick={copyKey} className="shrink-0 p-2 rounded border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10">
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <button onClick={() => setCreatedKey(null)} className="text-[10px] text-[hsl(215_20%_40%)] mt-2 hover:text-white">
              Dismiss
            </button>
          </div>
        )}

        {/* Create new key form */}
        {canCreateKey && (
          <div className="flex gap-2 mb-4">
            <input
              value={newKeyName}
              onChange={e => setNewKeyName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createKey()}
              placeholder="Key name (e.g. Production app)"
              className="flex-1 bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[hsl(215_20%_35%)] focus:outline-none focus:border-cyan-500/60"
            />
            <button
              onClick={createKey}
              disabled={creating || !newKeyName.trim()}
              className="flex items-center gap-1.5 px-3 py-2 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-black text-sm font-medium rounded-lg transition-colors shrink-0"
            >
              <Plus className="w-4 h-4" />
              {creating ? 'Creating…' : 'Create'}
            </button>
          </div>
        )}
        {error && <p className="text-xs text-red-400 mb-3">{error}</p>}

        {/* Keys list */}
        {loading ? (
          <p className="text-sm text-[hsl(215_20%_45%)]">Loading…</p>
        ) : keys.length === 0 ? (
          <p className="text-sm text-[hsl(215_20%_40%)] text-center py-4">No API keys yet.</p>
        ) : (
          <div className="space-y-2">
            {keys.map(k => (
              <div key={k.id} className="flex items-center gap-3 bg-[hsl(222_47%_10%)] border border-[hsl(217_33%_18%)] rounded-lg px-4 py-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white truncate">{k.name}</span>
                    <span className="text-[10px] bg-[hsl(217_33%_16%)] text-[hsl(215_20%_50%)] px-2 py-0.5 rounded">
                      {k.scopes}
                    </span>
                    <span className="text-[10px] text-cyan-400">{k.requests_per_minute} req/min</span>
                  </div>
                  <code className="text-[11px] text-[hsl(215_20%_45%)] font-mono">{k.key_prefix}…</code>
                  {k.last_used_at && (
                    <span className="text-[10px] text-[hsl(215_20%_35%)] ml-2">
                      last used {new Date(k.last_used_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => revokeKey(k.id)}
                  className="p-1.5 rounded text-[hsl(215_20%_45%)] hover:text-red-400 hover:bg-red-400/10 transition-colors shrink-0"
                  title="Revoke key"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Rate limit info */}
      <div className="bg-[hsl(222_47%_8%)] border border-[hsl(217_33%_20%)] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Rate Limits</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[hsl(215_20%_45%)] text-xs text-left">
              <th className="pb-2 font-medium">Plan</th>
              <th className="pb-2 font-medium">API rate limit</th>
              <th className="pb-2 font-medium">Scope</th>
            </tr>
          </thead>
          <tbody className="text-[hsl(215_20%_65%)]">
            {[
              { plan: 'Free', limit: '30 req / minute', scope: '—' },
              { plan: 'Pro', limit: '60 req / minute', scope: 'read' },
              { plan: 'Enterprise', limit: '300 req / minute', scope: 'read + write' },
            ].map(row => (
              <tr key={row.plan} className={row.plan.toLowerCase() === planSlug ? 'text-cyan-400 font-medium' : ''}>
                <td className="py-1.5">{row.plan}</td>
                <td className="py-1.5">{row.limit}</td>
                <td className="py-1.5">{row.scope}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-[10px] text-[hsl(215_20%_35%)] mt-3">
          Pass your key as: <code className="font-mono">X-Api-Key: ls_live_...</code> header on all API requests.
          Rate limit headers returned: <code className="font-mono">X-RateLimit-Limit</code>, <code className="font-mono">X-RateLimit-Remaining</code>.
        </p>
      </div>
    </div>
  )
}
