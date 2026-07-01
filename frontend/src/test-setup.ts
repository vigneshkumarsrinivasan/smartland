import '@testing-library/jest-dom'

// Stub out Leaflet — it requires a browser canvas that jsdom doesn't provide
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      remove: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    circleMarker: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      bindPopup: vi.fn().mockReturnThis(),
      remove: vi.fn(),
    })),
    icon: vi.fn(),
  },
}))

// Stub ResizeObserver (used by recharts)
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
