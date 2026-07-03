import { useState, useEffect } from 'react'
import type { AreaReport } from '@/types/report'
import { API_BASE } from '@/lib/api'

export function useAreaReport(areaId: number | null) {
  const [report, setReport] = useState<AreaReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (areaId === null) { setReport(null); return }

    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/areas/${areaId}/report`)
      .then(r => {
        if (!r.ok) throw new Error(`API ${r.status}`)
        return r.json() as Promise<AreaReport>
      })
      .then(data => { setReport(data); setLoading(false) })
      .catch(e => { setError(String(e.message)); setLoading(false) })
  }, [areaId])

  return { report, loading, error }
}
