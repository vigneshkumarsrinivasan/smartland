"""
Shared pytest fixtures for both unit and integration test suites.
Uses an in-memory SQLite database seeded with the same data as seed.py.
"""
import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Make the backend package importable regardless of how pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import (
    City, Area, AreaPriceHistory, InfrastructureProject,
    GrowthSignal, RiskSignal, Prediction, DataSource,
)
from app.scoring import AreaSignals, score_area


# ---------------------------------------------------------------------------
# In-memory DB (scoped to the test session for speed)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    # StaticPool ensures all sessions share the single in-memory connection.
    # Without this, each SQLAlchemy connection checkout gets a fresh (empty) DB.
    eng = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="session")
def db_session(engine):
    """Seed the in-memory DB once for the entire test session."""
    Session = sessionmaker(bind=engine)
    db = Session()

    # Same seed data as seed.py (values must stay in sync with CLAUDE.md)
    from datetime import datetime

    QUARTERS = [
        datetime(2022, 1, 1), datetime(2022, 4, 1), datetime(2022, 7, 1), datetime(2022, 10, 1),
        datetime(2023, 1, 1), datetime(2023, 4, 1), datetime(2023, 7, 1), datetime(2023, 10, 1),
        datetime(2024, 1, 1), datetime(2024, 4, 1), datetime(2024, 7, 1), datetime(2024, 10, 1),
    ]

    CITIES = [
        {"name": "Bangalore",  "state": "Karnataka",   "lat": 12.9716, "lng": 77.5946},
        {"name": "Hyderabad",  "state": "Telangana",   "lat": 17.3850, "lng": 78.4867},
        {"name": "Pune",       "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
        {"name": "Chennai",    "state": "Tamil Nadu",  "lat": 13.0827, "lng": 80.2707},
        {"name": "Coimbatore", "state": "Tamil Nadu",  "lat": 11.0168, "lng": 76.9558},
    ]

    AREAS = [
        {
            "name": "Sarjapur", "city": "Bangalore",
            "lat": 12.8693, "lng": 77.7950, "current_price_sqft": 6400, "land_type": "Residential",
            "prices": [4800,4920,5050,5150,5280,5420,5550,5680,5820,5960,6100,6250],
            "infra": [
                {"name":"Peripheral Ring Road (Sarjapur Stretch)","type":"Highway","status":"Under Construction","target_year":2027,"impact_score":8.5},
                {"name":"Sarjapur Metro Extension","type":"Metro","status":"Announced","target_year":2029,"impact_score":9.0},
                {"name":"Sarjapur–Marathahalli Road Widening","type":"Highway","status":"Completed","target_year":2023,"impact_score":6.0},
            ],
            "growth_signals": dict(infrastructure=80,job_growth=78,population_growth=72,commercial_activity=75,transaction_velocity=70,land_scarcity_score=78,government_spending=65),
            "risk_signals": dict(flood=32,water=38,legal=35,overvaluation=45,pollution=28,crime=25,delay=42),
            "confidence": 82,
        },
        {
            "name": "Devanahalli", "city": "Bangalore",
            "lat": 13.2485, "lng": 77.7145, "current_price_sqft": 4100, "land_type": "Mixed",
            "prices": [2600,2700,2820,2950,3050,3160,3280,3400,3540,3680,3820,3960],
            "infra": [
                {"name":"Bangalore Airport Terminal 2 Expansion","type":"Airport","status":"Under Construction","target_year":2026,"impact_score":9.5},
                {"name":"Aerospace SEZ Phase 2","type":"IT Park","status":"Under Construction","target_year":2027,"impact_score":8.0},
                {"name":"BIAL Second Runway","type":"Airport","status":"Under Construction","target_year":2027,"impact_score":7.5},
                {"name":"Devanahalli Business Park","type":"Commercial","status":"Announced","target_year":2028,"impact_score":7.0},
            ],
            "growth_signals": dict(infrastructure=95,job_growth=80,population_growth=75,commercial_activity=72,transaction_velocity=78,land_scarcity_score=70,government_spending=88),
            "risk_signals": dict(flood=25,water=30,legal=28,overvaluation=35,pollution=22,crime=20,delay=45),
            "confidence": 88,
        },
        {
            "name": "Electronic City", "city": "Bangalore",
            "lat": 12.8458, "lng": 77.6603, "current_price_sqft": 5300, "land_type": "IT/Commercial",
            "prices": [4200,4290,4380,4450,4520,4600,4680,4760,4850,4950,5060,5180],
            "infra": [
                {"name":"Electronic City Elevated Expressway Phase 2","type":"Highway","status":"Under Construction","target_year":2026,"impact_score":7.5},
                {"name":"Electronic City Metro Station (Yellow Line)","type":"Metro","status":"Announced","target_year":2028,"impact_score":8.5},
                {"name":"IT SEZ Phase 3 Expansion","type":"IT Park","status":"Under Construction","target_year":2026,"impact_score":6.5},
            ],
            "growth_signals": dict(infrastructure=60,job_growth=65,population_growth=58,commercial_activity=68,transaction_velocity=55,land_scarcity_score=80,government_spending=52),
            "risk_signals": dict(flood=28,water=35,legal=38,overvaluation=58,pollution=40,crime=30,delay=32),
            "confidence": 76,
        },
        {
            "name": "Whitefield", "city": "Bangalore",
            "lat": 12.9698, "lng": 77.7499, "current_price_sqft": 8100, "land_type": "IT/Residential",
            "prices": [6000,6150,6320,6480,6640,6800,6960,7130,7310,7490,7700,7900],
            "infra": [
                {"name":"Whitefield-Kadugodi Metro Line","type":"Metro","status":"Completed","target_year":2023,"impact_score":9.0},
                {"name":"ITPL Road Signal-Free Corridor","type":"Highway","status":"Under Construction","target_year":2026,"impact_score":6.0},
                {"name":"Whitefield Smart City Upgrades","type":"Infrastructure","status":"Under Construction","target_year":2026,"impact_score":5.5},
            ],
            "growth_signals": dict(infrastructure=58,job_growth=62,population_growth=55,commercial_activity=70,transaction_velocity=52,land_scarcity_score=85,government_spending=50),
            "risk_signals": dict(flood=35,water=40,legal=42,overvaluation=65,pollution=45,crime=35,delay=35),
            "confidence": 78,
        },
        {
            "name": "Hoskote", "city": "Bangalore",
            "lat": 13.0704, "lng": 77.7985, "current_price_sqft": 2550, "land_type": "Residential/Agricultural",
            "prices": [1600,1660,1730,1800,1870,1960,2040,2120,2200,2300,2400,2480],
            "infra": [
                {"name":"Hoskote Industrial Area Phase 2","type":"Industrial","status":"Announced","target_year":2028,"impact_score":7.5},
                {"name":"NH 75 (Bangalore-Chennai) 6-Lane Widening","type":"Highway","status":"Under Construction","target_year":2026,"impact_score":8.0},
                {"name":"Peripheral Ring Road East Segment","type":"Highway","status":"Announced","target_year":2029,"impact_score":8.5},
            ],
            "growth_signals": dict(infrastructure=55,job_growth=48,population_growth=52,commercial_activity=42,transaction_velocity=58,land_scarcity_score=45,government_spending=50),
            "risk_signals": dict(flood=75,water=82,legal=88,overvaluation=52,pollution=65,crime=48,delay=78),
            "confidence": 60,
        },
        {
            "name": "Shamshabad", "city": "Hyderabad",
            "lat": 17.2403, "lng": 78.4294, "current_price_sqft": 4500, "land_type": "Mixed",
            "prices": [2800,2920,3050,3180,3310,3460,3600,3740,3880,4040,4200,4360],
            "infra": [
                {"name":"RGIA Terminal 2 Expansion","type":"Airport","status":"Under Construction","target_year":2027,"impact_score":9.0},
                {"name":"ORR Phase 3 Extension to Shamshabad","type":"Highway","status":"Announced","target_year":2028,"impact_score":8.5},
                {"name":"Pharma City Access Road","type":"Highway","status":"Under Construction","target_year":2026,"impact_score":7.0},
                {"name":"Hyderabad Pharma City SEZ","type":"Industrial","status":"Under Construction","target_year":2027,"impact_score":9.0},
            ],
            "growth_signals": dict(infrastructure=92,job_growth=85,population_growth=72,commercial_activity=78,transaction_velocity=76,land_scarcity_score=68,government_spending=82),
            "risk_signals": dict(flood=35,water=42,legal=30,overvaluation=28,pollution=38,crime=25,delay=40),
            "confidence": 85,
        },
        {
            "name": "Hinjewadi", "city": "Pune",
            "lat": 18.5912, "lng": 73.7382, "current_price_sqft": 7200, "land_type": "IT/Residential",
            "prices": [5200,5340,5490,5640,5800,5960,6130,6300,6480,6680,6900,7060],
            "infra": [
                {"name":"Hinjewadi-Shivajinagar Metro Line","type":"Metro","status":"Under Construction","target_year":2026,"impact_score":9.5},
                {"name":"IT Park Phase 4 (Rajiv Gandhi Infotech Park)","type":"IT Park","status":"Under Construction","target_year":2026,"impact_score":7.5},
                {"name":"Pune Ring Road (Hinjewadi Segment)","type":"Highway","status":"Announced","target_year":2029,"impact_score":7.0},
            ],
            "growth_signals": dict(infrastructure=78,job_growth=82,population_growth=70,commercial_activity=80,transaction_velocity=75,land_scarcity_score=68,government_spending=62),
            "risk_signals": dict(flood=30,water=45,legal=40,overvaluation=55,pollution=35,crime=30,delay=48),
            "confidence": 80,
        },
        {
            "name": "Sriperumbudur", "city": "Chennai",
            "lat": 12.9673, "lng": 79.9454, "current_price_sqft": 2600, "land_type": "Industrial",
            "prices": [1800,1860,1930,2000,2060,2130,2200,2270,2340,2420,2500,2560],
            "infra": [
                {"name":"Chennai-Bangalore Industrial Corridor Node","type":"Industrial","status":"Under Construction","target_year":2027,"impact_score":8.5},
                {"name":"Sriperumbudur SIPCOT Expansion","type":"Industrial","status":"Under Construction","target_year":2026,"impact_score":7.5},
                {"name":"NH 48 Access Road Widening","type":"Highway","status":"Completed","target_year":2024,"impact_score":6.0},
            ],
            "growth_signals": dict(infrastructure=45,job_growth=40,population_growth=35,commercial_activity=42,transaction_velocity=38,land_scarcity_score=32,government_spending=45),
            "risk_signals": dict(flood=38,water=42,legal=55,overvaluation=35,pollution=65,crime=35,delay=48),
            "confidence": 65,
        },
        {
            "name": "Oragadam", "city": "Chennai",
            "lat": 12.8342, "lng": 80.0557, "current_price_sqft": 3400, "land_type": "Industrial/Logistics",
            "prices": [2100,2200,2310,2430,2540,2660,2780,2910,3030,3160,3280,3360],
            "infra": [
                {"name":"SIPCOT Industrial Hub Phase 3","type":"Industrial","status":"Announced","target_year":2027,"impact_score":8.0},
                {"name":"Grand Southern Trunk Road Widening (Oragadam)","type":"Highway","status":"Under Construction","target_year":2026,"impact_score":7.0},
                {"name":"Oragadam-Sriperumbudur Connector Road","type":"Highway","status":"Announced","target_year":2028,"impact_score":7.5},
            ],
            "growth_signals": dict(infrastructure=72,job_growth=75,population_growth=65,commercial_activity=78,transaction_velocity=68,land_scarcity_score=62,government_spending=70),
            "risk_signals": dict(flood=45,water=48,legal=35,overvaluation=30,pollution=60,crime=28,delay=42),
            "confidence": 75,
        },
        {
            "name": "Coimbatore North", "city": "Coimbatore",
            "lat": 11.0711, "lng": 77.0028, "current_price_sqft": 3200, "land_type": "Residential",
            "prices": [2400,2470,2540,2620,2700,2770,2840,2920,3000,3060,3130,3180],
            "infra": [
                {"name":"Coimbatore Metro Phase 1","type":"Metro","status":"Under Construction","target_year":2027,"impact_score":9.0},
                {"name":"Avinashi Road 6-Lane Widening","type":"Highway","status":"Completed","target_year":2024,"impact_score":6.5},
                {"name":"Coimbatore North Industrial Corridor","type":"Industrial","status":"Announced","target_year":2029,"impact_score":7.0},
            ],
            "growth_signals": dict(infrastructure=62,job_growth=55,population_growth=60,commercial_activity=52,transaction_velocity=58,land_scarcity_score=70,government_spending=55),
            "risk_signals": dict(flood=40,water=50,legal=38,overvaluation=45,pollution=35,crime=42,delay=52),
            "confidence": 70,
        },
    ]

    city_map = {}
    for c in CITIES:
        city = City(**c)
        db.add(city)
        db.flush()
        city_map[c["name"]] = city

    for a in AREAS:
        area = Area(
            name=a["name"],
            city_id=city_map[a["city"]].id,
            lat=a["lat"], lng=a["lng"],
            current_price_sqft=a["current_price_sqft"],
            land_type=a["land_type"],
        )
        db.add(area)
        db.flush()

        for dt, price in zip(QUARTERS, a["prices"]):
            db.add(AreaPriceHistory(area_id=area.id, date=dt, price_sqft=float(price)))

        for proj in a["infra"]:
            db.add(InfrastructureProject(area_id=area.id, **proj))

        gs = a["growth_signals"]
        db.add(GrowthSignal(
            area_id=area.id,
            infrastructure_score=gs["infrastructure"],
            job_growth_score=gs["job_growth"],
            population_growth_score=gs["population_growth"],
            commercial_activity_score=gs["commercial_activity"],
            transaction_velocity_score=gs["transaction_velocity"],
            land_scarcity_score=gs["land_scarcity_score"],
            government_spending_score=gs["government_spending"],
        ))

        rs = a["risk_signals"]
        db.add(RiskSignal(
            area_id=area.id,
            flood_risk=rs["flood"], water_risk=rs["water"],
            legal_risk=rs["legal"], overvaluation_risk=rs["overvaluation"],
            pollution_risk=rs["pollution"], crime_risk=rs["crime"],
            delay_risk=rs["delay"],
        ))

        signals = AreaSignals(
            infrastructure=gs["infrastructure"], job_growth=gs["job_growth"],
            population_growth=gs["population_growth"], commercial_activity=gs["commercial_activity"],
            transaction_velocity=gs["transaction_velocity"], land_scarcity=gs["land_scarcity_score"],
            government_spending=gs["government_spending"],
            flood_risk=rs["flood"], water_risk=rs["water"], legal_risk=rs["legal"],
            overvaluation_risk=rs["overvaluation"], pollution_risk=rs["pollution"],
            crime_risk=rs["crime"], delay_risk=rs["delay"],
        )
        result = score_area(signals, confidence=float(a["confidence"]))
        db.add(Prediction(
            area_id=area.id,
            growth_score=result.growth_score, risk_score=result.risk_score,
            confidence_score=result.confidence_score, recommendation=result.recommendation,
        ))

    # --- Data sources ---
    DATA_SOURCES = [
        {"name": "CREDAI Price Registry", "category": "Pricing", "status": "active",
         "description": "Developer transaction data aggregated from CREDAI member filings",
         "coverage": "Bangalore, Hyderabad, Pune, Chennai, Coimbatore"},
        {"name": "NHAI Project Tracker", "category": "Infrastructure", "status": "active",
         "description": "National Highway Authority of India project status feed",
         "coverage": "Pan-India"},
        {"name": "BMRCL Metro Updates", "category": "Infrastructure", "status": "active",
         "description": "Bangalore Metro Rail Corporation project milestones",
         "coverage": "Bangalore"},
        {"name": "Census 2011 + Projections", "category": "Demographics", "status": "degraded",
         "description": "Population growth estimates (2011 base + NITI Aayog projections)",
         "coverage": "Pan-India"},
        {"name": "MCA Company Registrations", "category": "Economic", "status": "active",
         "description": "Ministry of Corporate Affairs new business registrations by district",
         "coverage": "Pan-India"},
        {"name": "RERA Filings", "category": "Legal/Pricing", "status": "active",
         "description": "State RERA project registrations and transaction data",
         "coverage": "Bangalore, Hyderabad, Pune, Chennai"},
        {"name": "IMD Flood Hazard Maps", "category": "Risk/Environmental", "status": "active",
         "description": "India Meteorological Department flood zone classifications",
         "coverage": "Pan-India"},
        {"name": "CPCB Pollution Index", "category": "Risk/Environmental", "status": "active",
         "description": "Central Pollution Control Board air and water quality data",
         "coverage": "Pan-India"},
    ]
    for ds in DATA_SOURCES:
        db.add(DataSource(**ds))

    db.commit()
    yield db
    db.close()


@pytest.fixture(scope="session")
def test_app(engine, db_session):
    """TestClient wired to the in-memory seeded DB (db_session ensures data is seeded first)."""
    from main import app
    from app.database import get_db

    # Override the DB dependency so the API uses our in-memory test DB
    Session = sessionmaker(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
