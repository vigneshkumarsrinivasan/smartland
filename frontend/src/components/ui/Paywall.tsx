import { ReactNode, useState } from 'react'
import { Lock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useSubscription, useIsPro, useReportsRemaining } from '@/context/SubscriptionContext'
import { LoginModal } from './LoginModal'

interface PaywallProps {
  /** Which feature gate to check */
  feature: 'area_report' | 'compare' | 'export' | 'api'
  children: ReactNode
  /** Override the upgrade message shown in the overlay */
  message?: string
}

function featureLabel(feature: PaywallProps['feature']): string {
  switch (feature) {
    case 'area_report': return 'area report'
    case 'compare': return 'area comparison'
    case 'export': return 'PDF export'
    case 'api': return 'API access'
  }
}

export function Paywall({ feature, children, message }: PaywallProps) {
  const { isLoggedIn } = useSubscription()
  const isPro = useIsPro()
  const remaining = useReportsRemaining()
  const [showLogin, setShowLogin] = useState(false)

  const isBlocked =
    !isLoggedIn ||
    (feature === 'area_report' && remaining !== null && remaining <= 0) ||
    (feature === 'compare' && !isPro) ||
    (feature === 'export' && !isPro) ||
    (feature === 'api' && !isPro)

  if (!isBlocked) return <>{children}</>

  const defaultMessage = !isLoggedIn
    ? `Sign in to access ${featureLabel(feature)}`
    : feature === 'area_report'
      ? `You've used all your free reports this month. Upgrade to Pro for unlimited access.`
      : `${featureLabel(feature).charAt(0).toUpperCase() + featureLabel(feature).slice(1)} is a Pro feature.`

  return (
    <>
      <div className="relative">
        {/* Blurred content */}
        <div className="pointer-events-none select-none blur-sm opacity-40">
          {children}
        </div>

        {/* Overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[hsl(222_47%_6%)]/70 backdrop-blur-[2px] rounded-lg z-10">
          <div className="text-center max-w-xs px-6">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-[hsl(222_47%_10%)] border border-[hsl(217_33%_22%)] mx-auto mb-4">
              <Lock className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-sm text-[hsl(215_20%_70%)] mb-4">
              {message ?? defaultMessage}
            </p>
            {!isLoggedIn ? (
              <button
                onClick={() => setShowLogin(true)}
                className="bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-medium px-5 py-2 rounded-lg transition-colors"
              >
                Sign in
              </button>
            ) : (
              <Link
                to="/pricing"
                className="inline-block bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-medium px-5 py-2 rounded-lg transition-colors"
              >
                Upgrade to Pro
              </Link>
            )}
          </div>
        </div>
      </div>

      {showLogin && (
        <LoginModal
          onSuccess={() => setShowLogin(false)}
          onClose={() => setShowLogin(false)}
        />
      )}
    </>
  )
}
