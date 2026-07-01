import { useState, useEffect } from 'react'
import type { AreaSummary } from '@/types/area'

export function useAreas() {
  const [areas, setAreas] = useState<AreaSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/areas')
      .then(r => {
        if (!r.ok) throw new Error(`API ${r.status}`)
        return r.json() as Promise<AreaSummary[]>
      })
      .then(data => { setAreas(data); setLoading(false) })
      .catch(e => { setError(String(e.message)); setLoading(false) })
  }, [])

  return { areas, loading, error }
}
