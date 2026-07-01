import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface WatchlistCtx {
  watchlist: number[]
  toggle: (id: number) => void
  isWatched: (id: number) => boolean
}

const Ctx = createContext<WatchlistCtx>({ watchlist: [], toggle: () => {}, isWatched: () => false })

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [watchlist, setWatchlist] = useState<number[]>(() => {
    try { return JSON.parse(localStorage.getItem('ls-watchlist') ?? '[]') }
    catch { return [] }
  })

  useEffect(() => {
    localStorage.setItem('ls-watchlist', JSON.stringify(watchlist))
  }, [watchlist])

  const toggle = (id: number) =>
    setWatchlist(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  return (
    <Ctx.Provider value={{ watchlist, toggle, isWatched: id => watchlist.includes(id) }}>
      {children}
    </Ctx.Provider>
  )
}

export const useWatchlist = () => useContext(Ctx)
