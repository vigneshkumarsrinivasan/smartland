import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { API_BASE } from '@/lib/api'

export interface Plan {
  id: number
  name: string
  slug: string
  price_inr: number
  billing_cycle: string
  max_reports_per_month: number | null
  features: string[]
  razorpay_plan_id: string | null
}

export interface SubscriptionInfo {
  id: number
  plan_id: number
  razorpay_subscription_id: string | null
  status: string
  current_period_end: string | null
}

export interface UserInfo {
  id: number
  email: string
  name: string | null
  plan: Plan | null
}

interface UsageInfo {
  reports_used_this_month: number
  reports_limit: number | null
}

interface SubscriptionState {
  user: UserInfo | null
  subscription: SubscriptionInfo | null
  usage: UsageInfo
  isLoading: boolean
  isLoggedIn: boolean
  token: string | null
  login: (email: string, name?: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const TOKEN_KEY = 'ls-auth-token'

const defaultUsage: UsageInfo = { reports_used_this_month: 0, reports_limit: 3 }

const SubscriptionContext = createContext<SubscriptionState>({
  user: null,
  subscription: null,
  usage: defaultUsage,
  isLoading: false,
  isLoggedIn: false,
  token: null,
  login: async () => {},
  logout: () => {},
  refresh: async () => {},
})

export function SubscriptionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [usage, setUsage] = useState<UsageInfo>(defaultUsage)
  const [isLoading, setIsLoading] = useState(false)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))

  const refresh = useCallback(async () => {
    const stored = localStorage.getItem(TOKEN_KEY)
    if (!stored) return
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/billing/me`, {
        headers: { Authorization: `Bearer ${stored}` },
      })
      if (res.status === 401) {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
        setSubscription(null)
        return
      }
      if (res.ok) {
        const data = await res.json()
        setUser(data.user)
        setSubscription(data.subscription)
        setUsage(data.usage)
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Load on mount if token exists
  useEffect(() => {
    if (token) refresh()
  }, [token, refresh])

  const login = async (email: string, name?: string) => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/billing/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name }),
      })
      if (!res.ok) throw new Error('Registration failed')
      const data = await res.json()
      localStorage.setItem(TOKEN_KEY, data.token)
      setToken(data.token)
      setUser(data.user)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    setSubscription(null)
    setUsage(defaultUsage)
  }

  return (
    <SubscriptionContext.Provider
      value={{
        user,
        subscription,
        usage,
        isLoading,
        isLoggedIn: !!user,
        token,
        login,
        logout,
        refresh,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  )
}

export function useSubscription() {
  return useContext(SubscriptionContext)
}

/** Returns true if user has an active paid subscription (Pro or Enterprise). */
export function useIsPro(): boolean {
  const { user, subscription } = useSubscription()
  if (!user || !user.plan) return false
  if (user.plan.slug === 'free') return false
  if (!subscription) return false
  return ['active', 'authenticated'].includes(subscription.status)
}

/** Returns remaining free reports this month (null = unlimited). */
export function useReportsRemaining(): number | null {
  const { usage } = useSubscription()
  if (usage.reports_limit === null) return null
  return Math.max(0, usage.reports_limit - usage.reports_used_this_month)
}
