import { useState, FormEvent } from 'react'
import { X } from 'lucide-react'
import { useSubscription } from '@/context/SubscriptionContext'

interface Props {
  onSuccess: () => void
  onClose: () => void
}

export function LoginModal({ onSuccess, onClose }: Props) {
  const { login, isLoading } = useSubscription()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }
    try {
      await login(email.trim(), name.trim() || undefined)
      onSuccess()
    } catch {
      setError('Could not sign in. Please try again.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-sm rounded-xl border border-[hsl(217_33%_20%)] bg-[hsl(222_47%_8%)] p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[hsl(215_20%_45%)] hover:text-white"
        >
          <X className="w-4 h-4" />
        </button>

        <h2 className="text-lg font-semibold text-white mb-1">Sign in to continue</h2>
        <p className="text-sm text-[hsl(215_20%_50%)] mb-5">
          Enter your email to get instant access. No password needed.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[hsl(215_20%_60%)] mb-1">
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[hsl(215_20%_35%)] focus:outline-none focus:border-cyan-500/60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[hsl(215_20%_60%)] mb-1">
              Name <span className="text-[hsl(215_20%_40%)]">(optional)</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Your name"
              className="w-full bg-[hsl(222_47%_11%)] border border-[hsl(217_33%_22%)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[hsl(215_20%_35%)] focus:outline-none focus:border-cyan-500/60"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-60 text-black font-medium text-sm py-2 rounded-lg transition-colors"
          >
            {isLoading ? 'Signing in…' : 'Continue'}
          </button>
        </form>

        <p className="mt-4 text-[10px] text-[hsl(215_20%_35%)] text-center">
          By continuing you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
