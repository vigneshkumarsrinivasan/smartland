# LandSignal AI

> We don't list land. We predict the future of land.

Land/area price-growth intelligence platform for the Indian market. Predicts whether an area's land prices will rise, stay stable, or decline using infrastructure, population, economic, and risk signals.

## Quick start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Health check: curl http://localhost:8000/health
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

## Stack
- **Frontend:** React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + Recharts + Leaflet
- **Backend:** FastAPI + SQLAlchemy
- **Database:** SQLite (local) / PostgreSQL+PostGIS (production)

See `CLAUDE.md` for full architecture docs, schema state, and the ML scoring seam.
