import { Bookmark } from 'lucide-react'
import { useWatchlist } from '@/context/WatchlistContext'
import { useAreas } from '@/hooks/useAreas'
import { AreaCard } from '@/components/common/AreaCard'

export default function Watchlist() {
  const { watchlist } = useWatchlist()
  const { areas, loading } = useAreas()

  const watched = areas.filter(a => watchlist.includes(a.id))

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
        <span className="text-[11px] text-slate-500">{watched.length} area{watched.length !== 1 ? 's' : ''} on watchlist</span>
      </div>
      <div className="p-5 grid grid-cols-2 xl:grid-cols-3 gap-4">
        {watched.map((area, i) => (
          <AreaCard key={area.id} area={area} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}
