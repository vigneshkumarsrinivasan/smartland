// In dev, set VITE_API_BASE_URL=http://localhost:8000 in frontend/.env.local
// In production, set VITE_API_BASE_URL=https://your-app.railway.app in Vercel env vars
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
