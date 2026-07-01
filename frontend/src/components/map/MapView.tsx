import { useRef, useEffect } from 'react'
import L from 'leaflet'
import type { AreaSummary } from '@/types/area'
import { markerColor, markerRadius, displayLabel, REC_COLORS } from '@/lib/markerColors'

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png'
const TILE_ATTR = '&copy; <a href="https://carto.com/attributions">CARTO</a>'
const MAP_CENTER: [number, number] = [14.8, 78.0]
const MAP_ZOOM = 7

function buildPopup(area: AreaSummary): string {
  const color = markerColor(area)
  const label = displayLabel(area)
  const cagr = area.cagr_pct != null ? `${area.cagr_pct.toFixed(1)}%` : '—'
  const price = area.current_price_sqft.toLocaleString('en-IN')
  const riskColor = area.risk_score > 60 ? '#ef4444' : area.risk_score > 40 ? '#f59e0b' : '#10b981'

  return `
    <div style="font-family:system-ui,sans-serif;min-width:230px;padding:2px 0">
      <div style="font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:3px">${area.name}</div>
      <div style="font-size:11px;color:#64748b;margin-bottom:10px">${area.city} &nbsp;·&nbsp; ${area.land_type}</div>
      <div style="display:inline-block;padding:2px 12px;border-radius:99px;background:${color}22;color:${color};border:1px solid ${color}44;font-size:11px;font-weight:700;margin-bottom:12px;letter-spacing:.03em">${label.toUpperCase()}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 16px">
        <div>
          <div style="font-size:9px;color:#475569;letter-spacing:.08em;margin-bottom:2px">PRICE / SQFT</div>
          <div style="font-size:15px;font-weight:600;color:#f1f5f9">₹${price}</div>
        </div>
        <div>
          <div style="font-size:9px;color:#475569;letter-spacing:.08em;margin-bottom:2px">3-YR CAGR</div>
          <div style="font-size:15px;font-weight:600;color:#10b981">${cagr}</div>
        </div>
        <div>
          <div style="font-size:9px;color:#475569;letter-spacing:.08em;margin-bottom:2px">GROWTH SCORE</div>
          <div style="font-size:15px;font-weight:600;color:#06b6d4">${area.growth_score}</div>
        </div>
        <div>
          <div style="font-size:9px;color:#475569;letter-spacing:.08em;margin-bottom:2px">RISK SCORE</div>
          <div style="font-size:15px;font-weight:600;color:${riskColor}">${area.risk_score}</div>
        </div>
        <div>
          <div style="font-size:9px;color:#475569;letter-spacing:.08em;margin-bottom:2px">CONFIDENCE</div>
          <div style="font-size:15px;font-weight:600;color:#f1f5f9">${area.confidence_score}%</div>
        </div>
      </div>
    </div>
  `
}

const LEGEND_ITEMS = [
  { label: 'Strong Buy', color: REC_COLORS['Strong Buy'] },
  { label: 'Buy',        color: REC_COLORS['Buy'] },
  { label: 'Emerging',   color: REC_COLORS['Emerging'] },
  { label: 'Hold',       color: REC_COLORS['Hold'] },
  { label: 'Avoid',      color: REC_COLORS['Avoid'] },
]

export function MapView({ areas }: { areas: AreaSummary[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.CircleMarker[]>([])

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    mapRef.current = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: true,
    }).setView(MAP_CENTER, MAP_ZOOM)

    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current)

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      maxZoom: 19,
    }).addTo(mapRef.current)

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [])

  // Re-render markers when filtered areas change
  useEffect(() => {
    if (!mapRef.current) return

    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    areas.forEach(area => {
      const color = markerColor(area)
      const radius = markerRadius(area)

      const marker = L.circleMarker([area.lat, area.lng], {
        radius,
        fillColor: color,
        color: 'rgba(255,255,255,0.6)',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.88,
      })

      marker.bindPopup(buildPopup(area), {
        maxWidth: 300,
        className: 'landsignal-popup',
      })

      marker.addTo(mapRef.current!)
      markersRef.current.push(marker)
    })
  }, [areas])

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute bottom-8 left-3 z-[1000] bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2.5 backdrop-blur-sm">
        <p className="text-[9px] text-slate-500 font-semibold tracking-widest mb-2">SIGNAL</p>
        <div className="space-y-1.5">
          {LEGEND_ITEMS.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ background: color }}
              />
              <span className="text-[11px] text-slate-300">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Empty state */}
      {areas.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[999]">
          <div className="bg-slate-900/80 border border-slate-700 rounded-xl px-6 py-4 text-center backdrop-blur-sm">
            <p className="text-slate-300 text-sm font-medium">No areas match your filters</p>
            <p className="text-slate-500 text-xs mt-1">Adjust the filter panel to show results</p>
          </div>
        </div>
      )}
    </div>
  )
}
