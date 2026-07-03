import { useEffect, useState } from 'react'
import { Check, Zap, Building2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSubscription, useIsPro, Plan } from '@/context/SubscriptionContext'
import { API_BASE } from '@/lib/api'
import { LoginModal } from '@/components/ui/LoginModal'

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Razorpay: any
  }
}

const PLAN_ICONS: Record<string, React.ElementType> = {
  free: Zap,
  pro: Sparkles,
  enterprise: Building2,
}

const PLAN_COLORS: Record<string, string> = {
  free: 'border-[hsl(217_33%_20%)]',
  pro: 'border-cyan-500/60 ring-1 ring-cyan-500/30',
  enterprise: 'border-violet-500/60',
}

const PLAN_BADGE: Record<string, string | null> = {
  free: null,
  pro: 'Most Popular',
  enterprise: null,
}

export default function Pricing() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [pendingSlug, setPendingSlug] = useState<string | null>(null)
  const { user, token, isLoggedIn, refresh } = useSubscription()
  const isPro = useIsPro()

  useEffect(() => {
    fetch(`${API_BASE}/billing/plans`)
      .then(r => r.json())
      .then(setPlans)
      .catch(console.error)
  }, [])

  const handleSubscribe = async (plan: Plan) => {
    if (!isLoggedIn) {
      setPendingSlug(plan.slug)
      setShowLogin(true)
      return
    }
    if (plan.slug === 'free') return  // already on free
    setLoadingSlug(plan.slug)
    try {
      const res = await fetch(`${API_BASE}/billing/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan_slug: plan.slug }),
      })
      if (!res.ok) {
        const err = await res.json()
        alert(err.detail || 'Subscription failed')
        return
      }
      const data = await res.json()

      if (data.mock_mode || !window.Razorpay) {
        // Mock mode: subscription is already activated server-side
        await refresh()
        alert(`Subscribed to ${plan.name} (mock mode — no real payment)`)
        return
      }

      // Live Razorpay checkout
      const rzp = new window.Razorpay({
        ...data.checkout_params,
        handler: async () => {
          await refresh()
          alert(`Payment successful! Welcome to ${plan.name}.`)
        },
        modal: { ondismiss: () => setLoadingSlug(null) },
        theme: { color: '#06b6d4' },
      })
      rzp.open()
    } catch (e) {
      console.error(e)
      alert('Something went wrong. Please try again.')
    } finally {
      setLoadingSlug(null)
    }
  }

  const handleLoginSuccess = async () => {
    setShowLogin(false)
    if (pendingSlug) {
      const plan = plans.find(p => p.slug === pendingSlug)
      if (plan) await handleSubscribe(plan)
      setPendingSlug(null)
    }
  }

  const currentSlug = user?.plan?.slug ?? 'free'

  return (
    <div className="min-h-full bg-[hsl(222_47%_6%)] px-6 py-10">
      {/* Header */}
      <div className="max-w-4xl mx-auto text-center mb-10">
        <h1 className="text-3xl font-bold text-white mb-3">
          Simple, transparent pricing
        </h1>
        <p className="text-[hsl(215_20%_55%)] text-base">
          Unlock India's most actionable land-price intelligence. Cancel anytime.
        </p>
        {isLoggedIn && (
          <p className="mt-3 text-sm text-cyan-400">
            Signed in as <span className="font-medium">{user?.email}</span>
            {' · '}
            <span className="capitalize">{currentSlug}</span> plan
          </p>
        )}
      </div>

      {/* Plan cards */}
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map(plan => {
          const Icon = PLAN_ICONS[plan.slug] ?? Zap
          const badge = PLAN_BADGE[plan.slug]
          const isCurrent = plan.slug === currentSlug
          const isPopular = plan.slug === 'pro'

          return (
            <div
              key={plan.slug}
              className={cn(
                'relative flex flex-col rounded-xl border bg-[hsl(222_47%_8%)] p-6',
                PLAN_COLORS[plan.slug] ?? 'border-[hsl(217_33%_20%)]'
              )}
            >
              {badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-cyan-500 text-black text-[10px] font-bold px-3 py-0.5 rounded-full uppercase tracking-wider">
                    {badge}
                  </span>
                </div>
              )}

              {/* Plan header */}
              <div className="mb-5">
                <div className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-lg mb-3',
                  isPopular ? 'bg-cyan-500/20 border border-cyan-500/40' : 'bg-[hsl(217_33%_14%)] border border-[hsl(217_33%_22%)]'
                )}>
                  <Icon className={cn('w-5 h-5', isPopular ? 'text-cyan-400' : 'text-[hsl(215_20%_55%)]')} />
                </div>
                <h2 className="text-lg font-semibold text-white">{plan.name}</h2>
                <div className="mt-1 flex items-baseline gap-1">
                  {plan.price_inr === 0 ? (
                    <span className="text-3xl font-bold text-white">Free</span>
                  ) : (
                    <>
                      <span className="text-3xl font-bold text-white">₹{plan.price_inr.toLocaleString('en-IN')}</span>
                      <span className="text-[hsl(215_20%_45%)] text-sm">/month</span>
                    </>
                  )}
                </div>
              </div>

              {/* Features */}
              <ul className="flex-1 space-y-2 mb-6">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-[hsl(215_20%_70%)]">
                    <Check className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              {isCurrent ? (
                <div className="w-full text-center py-2 rounded-lg border border-[hsl(217_33%_22%)] text-[hsl(215_20%_50%)] text-sm">
                  Current plan
                </div>
              ) : plan.slug === 'enterprise' ? (
                <a
                  href="mailto:sales@landsignal.ai?subject=Enterprise inquiry"
                  className="w-full text-center py-2 rounded-lg border border-violet-500/50 text-violet-400 text-sm hover:bg-violet-500/10 transition-colors block"
                >
                  Contact sales
                </a>
              ) : (
                <button
                  onClick={() => handleSubscribe(plan)}
                  disabled={loadingSlug === plan.slug}
                  className={cn(
                    'w-full py-2 rounded-lg text-sm font-medium transition-colors',
                    isPro && plan.slug === 'free'
                      ? 'border border-[hsl(217_33%_22%)] text-[hsl(215_20%_50%)] hover:bg-[hsl(217_33%_12%)]'
                      : isPopular
                        ? 'bg-cyan-500 text-black hover:bg-cyan-400 disabled:opacity-60'
                        : 'border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10'
                  )}
                >
                  {loadingSlug === plan.slug
                    ? 'Processing…'
                    : plan.slug === 'free'
                      ? 'Downgrade to Free'
                      : `Upgrade to ${plan.name}`}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Fine print */}
      <div className="max-w-4xl mx-auto mt-8 text-center">
        <p className="text-xs text-[hsl(215_20%_35%)]">
          Prices are in INR. GST applicable as per Indian tax law.
          Subscriptions auto-renew monthly. Cancel anytime from your account settings.
          Payments processed securely by Razorpay.
        </p>
      </div>

      {showLogin && (
        <LoginModal
          onSuccess={handleLoginSuccess}
          onClose={() => { setShowLogin(false); setPendingSlug(null) }}
        />
      )}
    </div>
  )
}
