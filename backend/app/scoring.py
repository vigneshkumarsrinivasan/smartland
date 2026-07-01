"""
Scoring engine — pure functions, zero I/O, zero ORM imports.

ML SWAP SEAM
============
To replace this mock with a real model:
  1. Keep AreaSignals and ScoringResult exactly as-is (they are the API contract).
  2. Replace the body of score_area() only.
  3. The router and DB layer call score_area() and know nothing else.

Growth score weights  (must sum to 1.0):
  Infrastructure 25% · Job Growth 20% · Population Growth 15%
  Commercial Activity 10% · Transaction Velocity 10%
  Land Scarcity 10% · Government Spending 10%

Risk score weights (must sum to 1.0):
  Flood 20% · Water 20% · Legal 20% · Overvaluation 15%
  Pollution 10% · Crime 10% · Delay 5%
"""
from dataclasses import dataclass

_GROWTH_W = {
    "infrastructure":       0.25,
    "job_growth":           0.20,
    "population_growth":    0.15,
    "commercial_activity":  0.10,
    "transaction_velocity": 0.10,
    "land_scarcity":        0.10,
    "government_spending":  0.10,
}

_RISK_W = {
    "flood":         0.20,
    "water":         0.20,
    "legal":         0.20,
    "overvaluation": 0.15,
    "pollution":     0.10,
    "crime":         0.10,
    "delay":         0.05,
}


@dataclass
class AreaSignals:
    # Growth drivers (0-100)
    infrastructure: float
    job_growth: float
    population_growth: float
    commercial_activity: float
    transaction_velocity: float
    land_scarcity: float
    government_spending: float
    # Risk factors (0-100, higher = more risk)
    flood_risk: float
    water_risk: float
    legal_risk: float
    overvaluation_risk: float
    pollution_risk: float
    crime_risk: float
    delay_risk: float


@dataclass
class ScoringResult:
    growth_score: float         # 0-100 weighted composite
    risk_score: float           # 0-100 weighted composite
    confidence_score: float     # 0-100
    recommendation: str         # Strong Buy | Buy | Hold | Avoid | Sell


def score_area(signals: AreaSignals, confidence: float = 75.0) -> ScoringResult:
    """
    Compute growth score, risk score, and recommendation from signals.

    ML SWAP SEAM — replace body only; do not change signature or return type.
    """
    growth = (
        signals.infrastructure       * _GROWTH_W["infrastructure"]       +
        signals.job_growth           * _GROWTH_W["job_growth"]           +
        signals.population_growth    * _GROWTH_W["population_growth"]    +
        signals.commercial_activity  * _GROWTH_W["commercial_activity"]  +
        signals.transaction_velocity * _GROWTH_W["transaction_velocity"] +
        signals.land_scarcity        * _GROWTH_W["land_scarcity"]        +
        signals.government_spending  * _GROWTH_W["government_spending"]
    )

    risk = (
        signals.flood_risk        * _RISK_W["flood"]         +
        signals.water_risk        * _RISK_W["water"]         +
        signals.legal_risk        * _RISK_W["legal"]         +
        signals.overvaluation_risk * _RISK_W["overvaluation"] +
        signals.pollution_risk    * _RISK_W["pollution"]     +
        signals.crime_risk        * _RISK_W["crime"]         +
        signals.delay_risk        * _RISK_W["delay"]
    )

    # Recommendation — order matters (risk override before growth checks)
    if risk > 70:
        rec = "Avoid"
    elif growth < 45:
        rec = "Avoid"
    elif growth > 80 and risk < 40:
        rec = "Strong Buy"
    elif growth > 65 and risk < 55:
        rec = "Buy"
    elif 45 <= growth <= 65:
        rec = "Hold"
    else:
        # growth > 65 but risk >= 55: strong growth, elevated risk
        rec = "Sell"

    return ScoringResult(
        growth_score=round(growth, 1),
        risk_score=round(risk, 1),
        confidence_score=round(confidence, 1),
        recommendation=rec,
    )
