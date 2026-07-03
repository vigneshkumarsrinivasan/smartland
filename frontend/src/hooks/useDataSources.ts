import { useState, useEffect } from 'react'
import { API_BASE } from '@/lib/api'

export interface DataSource {
  id: number
  name: string
  category: string
  description: string | null
  status: 'active' | 'degraded' | 'offline'
  coverage: string | null
  last_updated: string | null
}

export function useDataSources() {
  const [sources, setSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/data-sources`)
      .then(r => { if (!r.ok) throw new Error(`API ${r.status}`); return r.json() as Promise<DataSource[]> })
      .then(d => { setSources(d); setLoading(false) })
      .catch(e => { setError(String(e.message)); setLoading(false) })
  }, [])

  return { sources, loading, error }
}
