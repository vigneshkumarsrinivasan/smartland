"""
Seed the three billing plans (Free, Pro, Enterprise).
Idempotent — safe to call on every startup.
"""
import json
from sqlalchemy.orm import Session
from app.models import Plan


PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "price_inr": 0,
        "billing_cycle": "monthly",
        "max_reports_per_month": 3,
        "features": [
            "3 area reports per month",
            "Growth Map (all 10 areas)",
            "Basic opportunity finder",
            "Price history charts",
        ],
    },
    {
        "name": "Pro",
        "slug": "pro",
        "price_inr": 999,
        "billing_cycle": "monthly",
        "max_reports_per_month": None,  # unlimited
        "features": [
            "Unlimited area reports",
            "Full Growth Map + signals breakdown",
            "Opportunity Finder with custom filters",
            "Compare up to 5 areas side-by-side",
            "Watchlist with alerts",
            "PDF report export",
            "Priority email support",
        ],
    },
    {
        "name": "Enterprise",
        "slug": "enterprise",
        "price_inr": 4999,
        "billing_cycle": "monthly",
        "max_reports_per_month": None,  # unlimited
        "features": [
            "Everything in Pro",
            "REST API access (rate-limited)",
            "Team seats (up to 10 users)",
            "Custom area coverage on request",
            "WhatsApp + email alerts",
            "Dedicated account manager",
            "SLA: 99.9% uptime guarantee",
        ],
    },
]


def seed_plans(db: Session) -> None:
    for spec in PLANS:
        existing = db.query(Plan).filter(Plan.slug == spec["slug"]).first()
        if not existing:
            plan = Plan(
                name=spec["name"],
                slug=spec["slug"],
                price_inr=spec["price_inr"],
                billing_cycle=spec["billing_cycle"],
                max_reports_per_month=spec["max_reports_per_month"],
                features_json=json.dumps(spec["features"]),
                is_active=True,
            )
            db.add(plan)
    db.commit()
