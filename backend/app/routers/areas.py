"""
Areas router.
Phase 1: GET /areas/dump (gate check)
Phase 2: GET /areas — all areas with scores, CAGR, recommendation
Phase 4: GET /areas/{id}/report — full explainable report
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Area, AreaPriceHistory, Prediction,
    GrowthSignal, RiskSignal, InfrastructureProject,
)
from app.rate_limit import limiter

router = APIRouter(prefix="/areas", tags=["areas"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_cagr(history: list[AreaPriceHistory]) -> float | None:
    if len(history) < 2:
        return None
    s = sorted(history, key=lambda h: h.date)
    p0, p1 = s[0].price_sqft, s[-1].price_sqft
    years = (s[-1].date - s[0].date).days / 365.25
    if years <= 0 or p0 <= 0:
        return None
    return round(((p1 / p0) ** (1 / years) - 1) * 100, 2)


def _area_summary(area: Area, prediction: Prediction, history: list[AreaPriceHistory]) -> dict:
    return {
        "id": area.id,
        "name": area.name,
        "city": area.city.name,
        "lat": area.lat,
        "lng": area.lng,
        "land_type": area.land_type,
        "current_price_sqft": area.current_price_sqft,
        "growth_score": prediction.growth_score,
        "risk_score": prediction.risk_score,
        "confidence_score": prediction.confidence_score,
        "recommendation": prediction.recommendation,
        "cagr_pct": _compute_cagr(history),
    }


def _generate_summary(
    area_name: str,
    prediction: Prediction,
    growth_signals: dict[str, float],
    risk_signals: dict[str, float],
    cagr: float | None,
) -> str:
    GROWTH_LABELS: dict[str, str] = {
        "infrastructure": "infrastructure momentum",
        "job_growth": "job creation",
        "population_growth": "population growth",
        "commercial_activity": "commercial activity",
        "transaction_velocity": "transaction velocity",
        "land_scarcity": "land scarcity premium",
        "government_spending": "government investment",
    }
    RISK_LABELS: dict[str, str] = {
        "flood": "flood exposure",
        "water": "water scarcity",
        "legal": "legal/title complexity",
        "overvaluation": "overvaluation risk",
        "pollution": "pollution levels",
        "crime": "crime index",
        "delay": "project delay risk",
    }

    top_growth = sorted(growth_signals.items(), key=lambda x: x[1], reverse=True)[:2]
    top_risk = sorted(risk_signals.items(), key=lambda x: x[1], reverse=True)[0]

    cagr_str = f"{cagr:.1f}%" if cagr is not None else "N/A"
    momentum = "above-average" if prediction.growth_score > 65 else "steady"
    risk_level = (
        "low" if prediction.risk_score < 40
        else "moderate" if prediction.risk_score < 60
        else "elevated"
    )
    confidence_desc = (
        "high" if prediction.confidence_score >= 80
        else "moderate" if prediction.confidence_score >= 65
        else "fair"
    )

    d1 = GROWTH_LABELS[top_growth[0][0]]
    s1 = int(top_growth[0][1])
    d2 = GROWTH_LABELS[top_growth[1][0]]
    s2 = int(top_growth[1][1])
    r_label = RISK_LABELS[top_risk[0]]
    r_score = int(top_risk[1])

    return (
        f"{area_name} presents a {prediction.recommendation} signal, driven primarily by "
        f"strong {d1} ({s1}/100) and {d2} ({s2}/100). "
        f"The area demonstrates {momentum} price momentum with a {cagr_str} 3-year CAGR. "
        f"Overall risk exposure is {risk_level} at {prediction.risk_score:.0f}/100, with "
        f"{r_label} as the primary concern ({r_score}/100). "
        f"Signal confidence is {confidence_desc} at {prediction.confidence_score:.0f}%."
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dump")
def dump_areas(db: Session = Depends(get_db)):
    """Phase 1 gate check — raw dump of all areas with ordered price history."""
    areas = db.query(Area).all()
    result = []
    for area in areas:
        history = (
            db.query(AreaPriceHistory)
            .filter(AreaPriceHistory.area_id == area.id)
            .order_by(AreaPriceHistory.date)
            .all()
        )
        result.append({
            "id": area.id,
            "name": area.name,
            "city": area.city.name,
            "lat": area.lat,
            "lng": area.lng,
            "land_type": area.land_type,
            "current_price_sqft": area.current_price_sqft,
            "price_history": [
                {"date": h.date.strftime("%Y-%m-%d"), "price_sqft": h.price_sqft}
                for h in history
            ],
        })
    return result


@router.get("")
@limiter.limit("60/minute")
def list_areas(
    request: Request,
    city: Optional[str] = Query(None),
    min_growth_score: Optional[float] = Query(None, ge=0, le=100),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100),
    recommendation: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """All areas with growth scores, risk scores, and recommendations."""
    query = db.query(Area)
    if city:
        query = query.join(Area.city).filter(Area.city.has(name=city))
    areas = query.all()

    result = []
    for area in areas:
        prediction = (
            db.query(Prediction)
            .filter(Prediction.area_id == area.id)
            .order_by(Prediction.generated_at.desc())
            .first()
        )
        if not prediction:
            continue
        if min_growth_score is not None and prediction.growth_score < min_growth_score:
            continue
        if max_risk_score is not None and prediction.risk_score > max_risk_score:
            continue
        if recommendation and prediction.recommendation != recommendation:
            continue

        history = (
            db.query(AreaPriceHistory)
            .filter(AreaPriceHistory.area_id == area.id)
            .order_by(AreaPriceHistory.date)
            .all()
        )
        result.append(_area_summary(area, prediction, history))
    return result


@router.get("/{area_id}/report")
@limiter.limit("30/minute")
def get_area_report(
    request: Request,
    area_id: int,
    format: Optional[str] = Query(None, description="Response format: json (default), pdf, html"),
    db: Session = Depends(get_db),
):
    """Full explainable report for a single area. Add ?format=pdf for PDF download."""
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    prediction = (
        db.query(Prediction)
        .filter(Prediction.area_id == area_id)
        .order_by(Prediction.generated_at.desc())
        .first()
    )
    growth_signal = db.query(GrowthSignal).filter(GrowthSignal.area_id == area_id).first()
    risk_signal = db.query(RiskSignal).filter(RiskSignal.area_id == area_id).first()

    if not prediction or not growth_signal or not risk_signal:
        raise HTTPException(status_code=422, detail="Signal data missing — run seed.py")

    history = (
        db.query(AreaPriceHistory)
        .filter(AreaPriceHistory.area_id == area_id)
        .order_by(AreaPriceHistory.date)
        .all()
    )
    projects = (
        db.query(InfrastructureProject)
        .filter(InfrastructureProject.area_id == area_id)
        .order_by(InfrastructureProject.target_year)
        .all()
    )

    # Forecast: base 20% max pa at score=100; optimistic ×1.25; risk ×0.60
    current_price = area.current_price_sqft
    base_rate = prediction.growth_score / 100 * 0.20
    opt_rate = base_rate * 1.25
    risk_rate = base_rate * 0.60
    anchor_year = 2025
    n = 11  # 2025–2035

    def project(rate: float) -> list[dict]:
        return [
            {"year": anchor_year + i, "price_sqft": round(current_price * (1 + rate) ** i)}
            for i in range(n)
        ]

    gs = {
        "infrastructure": growth_signal.infrastructure_score,
        "job_growth": growth_signal.job_growth_score,
        "population_growth": growth_signal.population_growth_score,
        "commercial_activity": growth_signal.commercial_activity_score,
        "transaction_velocity": growth_signal.transaction_velocity_score,
        "land_scarcity": growth_signal.land_scarcity_score,
        "government_spending": growth_signal.government_spending_score,
    }
    rs = {
        "flood": risk_signal.flood_risk,
        "water": risk_signal.water_risk,
        "legal": risk_signal.legal_risk,
        "overvaluation": risk_signal.overvaluation_risk,
        "pollution": risk_signal.pollution_risk,
        "crime": risk_signal.crime_risk,
        "delay": risk_signal.delay_risk,
    }

    cagr = _compute_cagr(history)

    report_data = {
        "area": _area_summary(area, prediction, history),
        "price_history": [
            {"date": h.date.strftime("%Y-%m-%d"), "price_sqft": h.price_sqft}
            for h in history
        ],
        "forecast": {
            "base": project(base_rate),
            "optimistic": project(opt_rate),
            "risk": project(risk_rate),
        },
        "growth_signals": gs,
        "risk_signals": rs,
        "infrastructure_projects": [
            {
                "name": p.name, "type": p.type, "status": p.status,
                "target_year": p.target_year, "impact_score": p.impact_score,
            }
            for p in projects
        ],
        "ai_summary": _generate_summary(area.name, prediction, gs, rs, cagr),
    }

    if format in ("pdf", "html"):
        from app.pdf_report import render_report, is_pdf_available
        content, media_type = render_report(report_data)
        ext = "pdf" if (format == "pdf" and is_pdf_available()) else "html"
        filename = f"landsignal-{area.name.lower().replace(' ', '-')}-{datetime.utcnow().strftime('%Y%m%d')}.{ext}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return report_data
