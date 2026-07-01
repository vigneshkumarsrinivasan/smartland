# LandSignal AI — CLAUDE.md

Persistent context for all Claude Code sessions. Update after every phase gate.

---

## Current phase
**Phase 5 complete** — Opportunity Finder, Compare Areas, Watchlist, Data Sources pages live. Full test suite passing (158/158).
Next: Phase 6+ (Auth · PDF Reports · Admin · ML scoring swap — scope each separately).

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
│   └── app/
│       ├── database.py         SQLAlchemy engine + Base + get_db() + init_db()
│       ├── models.py           All ORM models
│       └── routers/
│           └── areas.py        /areas/dump (Phase 1), /areas (Phase 2), /areas/{id}/report (Phase 4)
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

## Schema state (Phase 1)

| Table | Status |
|-------|--------|
| cities | seeded (5 rows) |
| areas | seeded (10 rows) |
| area_price_history | seeded (120 rows) |
| infrastructure_projects | seeded (32 rows) |
| data_sources | seeded (8 rows) |
| growth_signals | defined, not yet seeded (Phase 2) |
| risk_signals | defined, not yet seeded (Phase 2) |
| predictions | defined, not yet seeded (Phase 2) |
| users | deferred (Phase 5+) |
| watchlist | deferred (Phase 5+) |
| reports | deferred (Phase 5+) |
| alerts | deferred (Phase 5+) |
| model_weights | deferred (Phase 5+) |

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
| Price history (Q1 2022–Q4 2024) | **Real (fabricated-but-plausible)** |
| InfrastructureProject rows | **Real (fabricated-but-plausible)** |
| GrowthSignal / RiskSignal sub-scores | **Real (deterministic per area)** |
| Scoring logic (scoring.py) | **Real formula, mock sub-scores** |
| GET /areas with filters | **Live** |
| Map markers | Not yet — Phase 3 |
| Area report | Not yet — Phase 4 |
| Auth | Not built |
| PDF export | Not built |

---

## Open TODOs
- [x] Phase 0: scaffold, health check, nav shell, API contract
- [x] Phase 1: seed cities + areas + price history + infra projects
- [x] Phase 2: scoring module + `/areas` endpoint
- [x] Phase 3: Growth Map page (Leaflet, real data)
- [x] Phase 4: Area Analyzer page + `/areas/{id}/report` endpoint
- [x] Phase 5: Opportunity Finder, Compare Areas, Watchlist, Data Sources pages + AreaAnalyzer ?area= deep-link
- [x] Phase 5: Full test suite — 158 tests, 158 passed (pytest + vitest + playwright)
- [ ] Phase 6+: Auth, PDF Reports, Admin, ML scoring swap
