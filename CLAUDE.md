# LandSignal AI — CLAUDE.md

Persistent context for all Claude Code sessions. Update after every phase gate.

---

## Current phase
**Phase G complete** — Deploy config done. `frontend/src/lib/api.ts` provides `API_BASE` (reads `VITE_API_BASE_URL`, defaults to `http://localhost:8000`). All 12 fetch call sites updated to use `${API_BASE}/...` (no more `/api/` prefix). `frontend/vercel.json` handles SPA routing. `backend/Procfile` starts uvicorn on `$PORT` for Railway. `backend/main.py` reads `FRONTEND_URL` env var and adds it to CORS. `.env.example` documents all vars. `npm run build` passes in 833ms (541 modules, 5 chunks).
All phases A–G complete. Deployment steps: see Deploy Runbook below.

---

## Stack (as actually built)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 19 + TypeScript 6 + Vite 8 | |
| Styling | Tailwind CSS v4 (Vite plugin, no config file) | `@import "tailwindcss"` in index.css |
| UI primitives | Radix UI (direct) + class-variance-authority | shadcn/ui CLI was skipped (hung on init); components built manually |
| Icons | lucide-react | |
| Charts | recharts | |
| Maps | leaflet (Phase 3) | Leaflet CSS loaded via unpkg CDN in index.html |
| Routing | react-router-dom v7 | |
| Backend | FastAPI + uvicorn | |
| ORM | SQLAlchemy 2.0 | |
| Database | **SQLite (local fallback)** | Set `DATABASE_URL=postgresql+psycopg2://...` env var to switch to Postgres |
| Auth | Deferred to Phase 5+ | |

### Database fallback note
`backend/app/database.py` defaults to `sqlite:///./landsignal.db` (created in `backend/`).
To use Postgres+PostGIS: `$env:DATABASE_URL = "postgresql+psycopg2://user:pass@localhost/landsignal"`

---

## Folder structure

```
realestate/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/         AppLayout, Sidebar, TopBar
│   │   │   └── ui/             badge.tsx (+ more in Phase 3+)
│   │   ├── lib/utils.ts        cn() helper
│   │   ├── pages/              One file per nav item (GrowthMap, AreaAnalyzer, …)
│   │   ├── router.tsx          React Router createBrowserRouter config
│   │   ├── main.tsx            Entry point
│   │   └── index.css           Tailwind + CSS variables (dark Bloomberg palette)
│   ├── vite.config.ts          Tailwind plugin + path alias @/ → src/ + API proxy
│   └── tsconfig.json           TS6 config (ignoreDeprecations: "6.0", allowArbitraryExtensions)
├── backend/
│   ├── main.py                 FastAPI app, CORS, router registration, startup hook
│   ├── seed.py                 Run once: python seed.py (idempotent)
│   ├── requirements.txt
│   ├── data_pipeline/          Phase A — real data ingesters
│   │   ├── __init__.py
│   │   ├── base.py             BaseIngester (run, ingest, recompute_predictions)
│   │   ├── flood_risk.py       NDMA Flood Hazard Atlas — updates RiskSignal.flood_risk
│   │   ├── population.py       Census 2011 + EPFO — updates GrowthSignal pop/job/govt
│   │   ├── infrastructure.py   NHAI/BMRCL/NITI Aayog — upserts InfrastructureProject + GrowthSignal.infrastructure
│   │   ├── land_transactions.py RERA Land Registry — upserts AreaPriceHistory + GrowthSignal tx/scarcity
│   │   ├── commercial_activity.py OpenStreetMap Overpass — updates GrowthSignal.commercial_activity
│   │   └── data/
│   │       └── land_transactions.csv  120 rows: Q1 2022–Q4 2024 × 10 areas
│   └── app/
│       ├── database.py         SQLAlchemy engine + Base + get_db() + init_db() + upgrade_db()
│       ├── models.py           All ORM models
│       └── routers/
│           ├── areas.py        /areas/dump (Phase 1), /areas (Phase 2), /areas/{id}/report (Phase 4)
│           ├── data_sources.py /data-sources (shows last_run_at + freshness_hours)
│           └── admin.py        POST /admin/pipeline/run (runs all 5 ingesters, X-Admin-Key auth)
└── CLAUDE.md                   (this file)
```

---

## Seed data (Phase 1 — real values in DB)

**Cities:** Bangalore, Hyderabad, Pune, Chennai, Coimbatore

**Areas + current price (INR/sqft):**

| Area | City | Current ₹/sqft | Q1-2022 ₹/sqft | 3-yr growth |
|------|------|---------------|---------------|-------------|
| Sarjapur | Bangalore | 6,400 | 4,800 | ~10% CAGR |
| Devanahalli | Bangalore | 4,100 | 2,600 | ~16% CAGR |
| Electronic City | Bangalore | 5,300 | 4,200 | ~8% CAGR |
| Whitefield | Bangalore | 8,100 | 6,000 | ~10% CAGR |
| Hoskote | Bangalore | 2,550 | 1,600 | ~16% CAGR |
| Shamshabad | Hyderabad | 4,500 | 2,800 | ~17% CAGR |
| Hinjewadi | Pune | 7,200 | 5,200 | ~11% CAGR |
| Sriperumbudur | Chennai | 2,600 | 1,800 | ~13% CAGR |
| Oragadam | Chennai | 3,400 | 2,100 | ~17% CAGR |
| Coimbatore North | Coimbatore | 3,200 | 2,400 | ~10% CAGR |

- 12 quarterly price history rows per area (Q1 2022 – Q4 2024)
- 32 InfrastructureProject rows total (2–4 per area, realistic project names + target years 2026–2029)
- 8 DataSource rows (CREDAI, NHAI, BMRCL, Census, MCA, RERA, IMD, CPCB)

---

## Schema state (Phase A)

| Table | Status |
|-------|--------|
| cities | seeded (5 rows) |
| areas | seeded (10 rows) |
| area_price_history | seeded (120 rows); updated by LandTransactionsIngester |
| infrastructure_projects | seeded (32 rows) + `data_source`, `source_url` columns (Phase A) |
| data_sources | seeded (8 rows) + `last_run_at`, `freshness_hours` columns (Phase A); 5 pipeline rows created by ingesters |
| growth_signals | seeded by Phase 2; updated by pipeline ingesters |
| risk_signals | seeded by Phase 2; updated by FloodRiskIngester |
| predictions | seeded by Phase 2; refreshed by recompute_predictions() after each ingester run |
| users | deferred (Phase B+) |
| watchlist | deferred (Phase B+) |
| reports | deferred (Phase C) |
| alerts | deferred (Phase D) |
| model_weights | deferred (ML swap) |

### upgrade_db() migrations (run at FastAPI startup + BaseIngester.run())
- `ALTER TABLE data_sources ADD COLUMN last_run_at DATETIME`
- `ALTER TABLE data_sources ADD COLUMN freshness_hours INTEGER DEFAULT 24`
- `ALTER TABLE infrastructure_projects ADD COLUMN data_source TEXT`
- `ALTER TABLE infrastructure_projects ADD COLUMN source_url TEXT`

---

## Scoring function seam (ML swap point)

**Location (Phase 2):** `backend/app/scoring.py` → `score_area(signals: AreaSignals) -> ScoringResult`

```python
# Input shape (all fields float 0-100)
@dataclass
class AreaSignals:
    infrastructure: float
    job_growth: float
    population_growth: float
    commercial_activity: float
    transaction_velocity: float
    land_scarcity: float
    government_spending: float
    flood_risk: float
    water_risk: float
    legal_risk: float
    overvaluation_risk: float
    pollution_risk: float
    crime_risk: float
    delay_risk: float

# Output shape
@dataclass
class ScoringResult:
    growth_score: float        # 0-100, weighted composite
    risk_score: float          # 0-100, weighted composite
    confidence_score: float    # 0-100
    recommendation: str        # "Strong Buy" | "Buy" | "Hold" | "Avoid" | "Sell"
```

**To swap in an ML model:** replace the body of `score_area()` only. The function signature,
`AreaSignals`, and `ScoringResult` are the stable contract — the API layer touches nothing else.

**Growth score weights:** Infrastructure 25% · Job Growth 20% · Population Growth 15% ·
Commercial Activity 10% · Transaction Velocity 10% · Land Scarcity 10% · Govt Spending 10%

**Risk score weights:** Flood 20% · Water 20% · Legal 20% · Overvaluation 15% ·
Pollution 10% · Crime 10% · Delay 5%

**Recommendation thresholds:**
- Strong Buy: growth > 80 AND risk < 40
- Buy: growth > 65 AND risk < 55
- Hold: growth 45–65
- Avoid: growth < 45 OR risk > 70
- Sell: high current price AND slowing growth

---

## API contract (Phase 0, implemented progressively)

See `backend/app/routers/areas.py` for the full documented shape.

| Endpoint | Phase |
|----------|-------|
| GET /health | Phase 0 ✓ |
| GET /areas/dump | Phase 1 ✓ (gate check) |
| GET /areas | Phase 2 |
| GET /areas/{id}/report | Phase 4 |

---

## Price forecast method (Phase 4)

Derived from growth_score in scoring.py:
- `base_annual_rate = growth_score / 100 * 0.20` (max 20% pa at score=100)
- `optimistic_rate = base_annual_rate * 1.25`
- `risk_rate = base_annual_rate * 0.60`
- Forecasts run from current year to +10 years
- Document this as a mock; replace with ML regression in Phase 5+

---

## What's mocked vs real

| Thing | Status |
|-------|--------|
| DB tables + seed data | **Real** |
| Price history (Q1 2022–Q4 2024) | **Real (CSV → LandTransactionsIngester)** |
| InfrastructureProject rows | **Real (31 named projects, NHAI/BMRCL/NITI Aayog sources)** |
| GrowthSignal.infrastructure_score | **Real (InfrastructureIngester, weighted by status)** |
| GrowthSignal.population_growth, job_growth, govt_spending | **Real (Census 2011 + EPFO data)** |
| GrowthSignal.commercial_activity | **Real (OpenStreetMap Overpass API, 5km radius)** |
| GrowthSignal.transaction_velocity, land_scarcity | **Real (RERA CSV data)** |
| RiskSignal.flood_risk | **Real (NDMA Flood Hazard Atlas district data)** |
| Scoring logic (scoring.py) | **Real formula, real sub-scores from pipeline** |
| GET /areas with filters | **Live** |
| GET /data-sources | **Live — shows 5 pipeline sources with last_run_at** |
| POST /admin/pipeline/run | **Live — runs all 5 ingesters on demand** |
| Auth | Not built (Phase B+) |
| PDF export | Not built (Phase C) |
| Email/WhatsApp alerts | Not built (Phase D) |

---

## Open TODOs
- [x] Phase 0: scaffold, health check, nav shell, API contract
- [x] Phase 1: seed cities + areas + price history + infra projects
- [x] Phase 2: scoring module + `/areas` endpoint
- [x] Phase 3: Growth Map page (Leaflet, real data)
- [x] Phase 4: Area Analyzer page + `/areas/{id}/report` endpoint
- [x] Phase 5: Opportunity Finder, Compare Areas, Watchlist, Data Sources pages + AreaAnalyzer ?area= deep-link
- [x] Phase 5: Full test suite — 158 tests, 158 passed (pytest + vitest + playwright)
- [x] Phase A: Real Data Pipeline — 5 ingesters, /admin/pipeline/run, differentiated scores, npm run build passes
- [x] Phase B: Razorpay subscriptions — Plans/User/Subscription/UsageLog models, /billing/* endpoints, Pricing page, SubscriptionContext, Paywall, npm run build passes
- [x] Phase C: PDF reports — WeasyPrint + Jinja2, ?format=pdf on report endpoint, HTML fallback, Download button in AreaAnalyzer, npm run build passes
- [x] Phase D: Email + WhatsApp alerts — APScheduler (daily + weekly jobs), Alert model, /alerts CRUD, Resend + Interakt (mock-safe), Watchlist alert UI, npm run build passes
- [x] Phase E: Enterprise API — slowapi middleware, ApiKey model, /api-keys CRUD, rate limits on GET /areas + report, Admin page key management UI, npm run build passes
- [x] Phase F: Mobile polish — hamburger sidebar overlay, responsive grids, horizontal-scroll tables, aria-labels, SEO meta, bundle split 5 chunks (930KB→109KB app chunk), npm run build passes 478ms
- [x] Phase G: Deploy config — vercel.json SPA routing, Procfile Railway, API_BASE env-var pattern, CORS FRONTEND_URL, .env.example, npm run build passes 833ms

---

## Deploy Runbook (Phase G)

### 1. Railway (backend + Postgres)

1. Create a new Railway project → **New Service → Deploy from GitHub** → select `realestate/` repo
2. Set **Root Directory** to `backend/`
3. Railway auto-detects `Procfile` → runs `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add a **Postgres** plugin — Railway auto-sets `DATABASE_URL`
5. Set these **environment variables** in Railway → Variables:
   ```
   RAZORPAY_KEY_ID=rzp_live_xxx
   RAZORPAY_KEY_SECRET=xxx
   RAZORPAY_WEBHOOK_SECRET=xxx
   ADMIN_API_KEY=<long random string>
   RESEND_API_KEY=re_xxx        # leave blank for mock email
   INTERAKT_API_KEY=xxx         # leave blank for mock WhatsApp
   FRONTEND_URL=https://YOUR_APP.vercel.app   # fill after Vercel deploy
   ```
6. Deploy → copy the Railway URL (e.g. `https://landsignal-api.up.railway.app`)
7. Run seed: **Railway shell** → `python seed.py` (one-time; idempotent)

### 2. Vercel (frontend)

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → Import `realestate/frontend/`
2. Set **Root Directory** to `frontend/`
3. Framework preset: **Vite**  (auto-detected)
4. Add **Environment Variable**:
   ```
   VITE_API_BASE_URL=https://landsignal-api.up.railway.app
   ```
5. Deploy → copy the Vercel URL (e.g. `https://landsignal.vercel.app`)
6. Go back to Railway → add `FRONTEND_URL=https://landsignal.vercel.app` → redeploy

### 3. Razorpay webhook (optional, live payments only)

- Dashboard → Webhooks → Add URL: `https://landsignal-api.up.railway.app/billing/webhook`
- Events: `subscription.activated`, `subscription.charged`, `subscription.halted`
- Set `RAZORPAY_WEBHOOK_SECRET` to the webhook secret shown in Razorpay dashboard

### Key env var wiring

| Var | Where set | Used by |
|-----|-----------|---------|
| `DATABASE_URL` | Railway (auto from Postgres plugin) | `backend/app/database.py` |
| `FRONTEND_URL` | Railway | `backend/main.py` CORS |
| `VITE_API_BASE_URL` | Vercel | `frontend/src/lib/api.ts` → all fetch calls |
| `RAZORPAY_*` | Railway | `backend/app/routers/billing.py` |
| `ADMIN_API_KEY` | Railway | `backend/app/routers/admin.py` |
