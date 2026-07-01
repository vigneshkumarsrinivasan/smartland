"""
Section 1A — Scoring engine unit tests.

Tests the pure score_area() function directly without any DB or API involvement.
All expected values computed from the documented weights in CLAUDE.md / scoring.py:

  Growth weights: infra=0.25, job_growth=0.20, pop=0.15, commercial=0.10,
                  tx_velocity=0.10, land_scarcity=0.10, govt_spending=0.10

  Risk weights:   flood=0.20, water=0.20, legal=0.20, overvaluation=0.15,
                  pollution=0.10, crime=0.10, delay=0.05
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from app.scoring import AreaSignals, ScoringResult, score_area

VALID_RECS = {"Strong Buy", "Buy", "Hold", "Avoid", "Sell"}


def make_signals(**overrides) -> AreaSignals:
    """Return an AreaSignals with all fields at 50.0, optionally overridden."""
    defaults = dict(
        infrastructure=50, job_growth=50, population_growth=50,
        commercial_activity=50, transaction_velocity=50,
        land_scarcity=50, government_spending=50,
        flood_risk=50, water_risk=50, legal_risk=50,
        overvaluation_risk=50, pollution_risk=50,
        crime_risk=50, delay_risk=50,
    )
    defaults.update(overrides)
    return AreaSignals(**defaults)


# ---------------------------------------------------------------------------
# Growth score calculation
# ---------------------------------------------------------------------------

class TestGrowthScore:

    def test_all_zeros_growth_is_zero(self):
        s = make_signals(
            infrastructure=0, job_growth=0, population_growth=0,
            commercial_activity=0, transaction_velocity=0,
            land_scarcity=0, government_spending=0,
            flood_risk=0, water_risk=0, legal_risk=0,
            overvaluation_risk=0, pollution_risk=0, crime_risk=0, delay_risk=0,
        )
        r = score_area(s)
        assert r.growth_score == 0.0

    def test_all_hundreds_growth_is_100(self):
        s = make_signals(
            infrastructure=100, job_growth=100, population_growth=100,
            commercial_activity=100, transaction_velocity=100,
            land_scarcity=100, government_spending=100,
            flood_risk=0, water_risk=0, legal_risk=0,
            overvaluation_risk=0, pollution_risk=0, crime_risk=0, delay_risk=0,
        )
        r = score_area(s)
        assert r.growth_score == 100.0

    def test_weighted_mix_exact_growth(self):
        # infra=80, job=60, pop=50, comm=70, tx=40, scarcity=90, govt=55
        # expected = 80×0.25 + 60×0.20 + 50×0.15 + 70×0.10 + 40×0.10 + 90×0.10 + 55×0.10
        #          = 20.0  + 12.0  + 7.5  + 7.0  + 4.0  + 9.0  + 5.5  = 65.0
        s = make_signals(
            infrastructure=80, job_growth=60, population_growth=50,
            commercial_activity=70, transaction_velocity=40,
            land_scarcity=90, government_spending=55,
            flood_risk=0, water_risk=0, legal_risk=0,
            overvaluation_risk=0, pollution_risk=0, crime_risk=0, delay_risk=0,
        )
        r = score_area(s)
        assert r.growth_score == 65.0

    def test_fractional_sub_scores_no_int_cast(self):
        # 33.3 × 0.25 + 0 + ... = 8.325 → rounds to 8.3
        s = make_signals(
            infrastructure=33.3, job_growth=0, population_growth=0,
            commercial_activity=0, transaction_velocity=0,
            land_scarcity=0, government_spending=0,
            flood_risk=0, water_risk=0, legal_risk=0,
            overvaluation_risk=0, pollution_risk=0, crime_risk=0, delay_risk=0,
        )
        r = score_area(s)
        assert r.growth_score == round(33.3 * 0.25, 1)


# ---------------------------------------------------------------------------
# Risk score calculation
# ---------------------------------------------------------------------------

class TestRiskScore:

    def test_all_zeros_risk_is_zero(self):
        s = make_signals(
            infrastructure=0, job_growth=0, population_growth=0,
            commercial_activity=0, transaction_velocity=0,
            land_scarcity=0, government_spending=0,
            flood_risk=0, water_risk=0, legal_risk=0,
            overvaluation_risk=0, pollution_risk=0, crime_risk=0, delay_risk=0,
        )
        r = score_area(s)
        assert r.risk_score == 0.0

    def test_all_hundreds_risk_is_100(self):
        s = make_signals(
            infrastructure=0, job_growth=0, population_growth=0,
            commercial_activity=0, transaction_velocity=0,
            land_scarcity=0, government_spending=0,
            flood_risk=100, water_risk=100, legal_risk=100,
            overvaluation_risk=100, pollution_risk=100, crime_risk=100, delay_risk=100,
        )
        r = score_area(s)
        assert r.risk_score == 100.0

    def test_weighted_mix_exact_risk(self):
        # flood=60, water=40, legal=80, over=30, poll=50, crime=20, delay=70
        # expected = 60×0.20 + 40×0.20 + 80×0.20 + 30×0.15 + 50×0.10 + 20×0.10 + 70×0.05
        #          = 12.0 + 8.0 + 16.0 + 4.5 + 5.0 + 2.0 + 3.5 = 51.0
        s = make_signals(
            infrastructure=0, job_growth=0, population_growth=0,
            commercial_activity=0, transaction_velocity=0,
            land_scarcity=0, government_spending=0,
            flood_risk=60, water_risk=40, legal_risk=80,
            overvaluation_risk=30, pollution_risk=50, crime_risk=20, delay_risk=70,
        )
        r = score_area(s)
        assert r.risk_score == 51.0


# ---------------------------------------------------------------------------
# Recommendation logic — exhaustive boundary tests
# ---------------------------------------------------------------------------

class TestRecommendation:

    def _rec(self, growth_override: dict, risk_override: dict) -> str:
        s = make_signals(**growth_override, **risk_override)
        return score_area(s).recommendation

    def _rec_from_scores(self, growth_val: float, risk_val: float) -> str:
        """
        Build signals that produce exact growth/risk scores.
        Concentrates all weight into infrastructure (growth) and flood (risk).

        Growth: infrastructure × 0.25 → infra = growth_val / 0.25 = growth_val × 4
        But capped at 100, so only works for growth_val <= 25.
        Instead, split across all 7 growth dims equally to reach the target.

        Simpler: since all weights sum to 1.0, set all growth signals to growth_val
        and all risk signals to risk_val — then growth_score = risk_score = the target.
        """
        s = make_signals(
            infrastructure=growth_val, job_growth=growth_val, population_growth=growth_val,
            commercial_activity=growth_val, transaction_velocity=growth_val,
            land_scarcity=growth_val, government_spending=growth_val,
            flood_risk=risk_val, water_risk=risk_val, legal_risk=risk_val,
            overvaluation_risk=risk_val, pollution_risk=risk_val,
            crime_risk=risk_val, delay_risk=risk_val,
        )
        return score_area(s).recommendation

    # Strong Buy boundary
    def test_strong_buy_above_threshold(self):
        # growth=81, risk=39 → Strong Buy (growth>80 AND risk<40)
        s = AreaSignals(
            infrastructure=81, job_growth=81, population_growth=81, commercial_activity=81,
            transaction_velocity=81, land_scarcity=81, government_spending=81,
            flood_risk=39, water_risk=39, legal_risk=39, overvaluation_risk=39,
            pollution_risk=39, crime_risk=39, delay_risk=39,
        )
        assert score_area(s).recommendation == "Strong Buy"

    def test_strong_buy_boundary_growth_exactly_80(self):
        # growth=80 (NOT > 80), risk=39 → falls through to Buy (growth>65 and risk<55)
        s = AreaSignals(
            infrastructure=80, job_growth=80, population_growth=80, commercial_activity=80,
            transaction_velocity=80, land_scarcity=80, government_spending=80,
            flood_risk=39, water_risk=39, legal_risk=39, overvaluation_risk=39,
            pollution_risk=39, crime_risk=39, delay_risk=39,
        )
        result = score_area(s)
        # growth=80.0, risk=39.0 → growth > 80 is False; growth > 65 and risk < 55 → Buy
        assert result.growth_score == 80.0
        assert result.risk_score == 39.0
        assert result.recommendation == "Buy"

    def test_strong_buy_boundary_risk_exactly_40(self):
        # growth=81, risk=40 → risk<40 is False → Buy (growth>65 and risk<55)
        s = AreaSignals(
            infrastructure=81, job_growth=81, population_growth=81, commercial_activity=81,
            transaction_velocity=81, land_scarcity=81, government_spending=81,
            flood_risk=40, water_risk=40, legal_risk=40, overvaluation_risk=40,
            pollution_risk=40, crime_risk=40, delay_risk=40,
        )
        result = score_area(s)
        assert result.growth_score == 81.0
        assert result.risk_score == 40.0
        assert result.recommendation == "Buy"

    # Buy boundary
    def test_buy_above_threshold(self):
        # growth=66, risk=54 → Buy (growth>65 and risk<55)
        s = AreaSignals(
            infrastructure=66, job_growth=66, population_growth=66, commercial_activity=66,
            transaction_velocity=66, land_scarcity=66, government_spending=66,
            flood_risk=54, water_risk=54, legal_risk=54, overvaluation_risk=54,
            pollution_risk=54, crime_risk=54, delay_risk=54,
        )
        result = score_area(s)
        assert result.growth_score == 66.0
        assert result.risk_score == 54.0
        assert result.recommendation == "Buy"

    def test_buy_boundary_growth_exactly_65(self):
        # growth=65 (NOT > 65), risk=54 → 45<=65<=65 → Hold
        s = AreaSignals(
            infrastructure=65, job_growth=65, population_growth=65, commercial_activity=65,
            transaction_velocity=65, land_scarcity=65, government_spending=65,
            flood_risk=54, water_risk=54, legal_risk=54, overvaluation_risk=54,
            pollution_risk=54, crime_risk=54, delay_risk=54,
        )
        result = score_area(s)
        assert result.growth_score == 65.0
        assert result.recommendation == "Hold"

    def test_buy_boundary_risk_exactly_55(self):
        # growth=66, risk=55 (NOT < 55) → else branch → Sell
        s = AreaSignals(
            infrastructure=66, job_growth=66, population_growth=66, commercial_activity=66,
            transaction_velocity=66, land_scarcity=66, government_spending=66,
            flood_risk=55, water_risk=55, legal_risk=55, overvaluation_risk=55,
            pollution_risk=55, crime_risk=55, delay_risk=55,
        )
        result = score_area(s)
        assert result.growth_score == 66.0
        assert result.risk_score == 55.0
        assert result.recommendation == "Sell"

    # Hold
    def test_hold_mid_range(self):
        # growth=55, risk=50 → 45<=55<=65 → Hold
        s = AreaSignals(
            infrastructure=55, job_growth=55, population_growth=55, commercial_activity=55,
            transaction_velocity=55, land_scarcity=55, government_spending=55,
            flood_risk=50, water_risk=50, legal_risk=50, overvaluation_risk=50,
            pollution_risk=50, crime_risk=50, delay_risk=50,
        )
        result = score_area(s)
        assert result.growth_score == 55.0
        assert result.recommendation == "Hold"

    def test_hold_boundary_growth_exactly_45(self):
        # growth=45 → 45<=45<=65 → Hold
        s = AreaSignals(
            infrastructure=45, job_growth=45, population_growth=45, commercial_activity=45,
            transaction_velocity=45, land_scarcity=45, government_spending=45,
            flood_risk=30, water_risk=30, legal_risk=30, overvaluation_risk=30,
            pollution_risk=30, crime_risk=30, delay_risk=30,
        )
        result = score_area(s)
        assert result.growth_score == 45.0
        assert result.recommendation == "Hold"

    # Avoid — growth override
    def test_avoid_low_growth(self):
        # growth=44 → growth<45 → Avoid
        s = AreaSignals(
            infrastructure=44, job_growth=44, population_growth=44, commercial_activity=44,
            transaction_velocity=44, land_scarcity=44, government_spending=44,
            flood_risk=30, water_risk=30, legal_risk=30, overvaluation_risk=30,
            pollution_risk=30, crime_risk=30, delay_risk=30,
        )
        result = score_area(s)
        assert result.growth_score == 44.0
        assert result.recommendation == "Avoid"

    def test_avoid_high_risk_override(self):
        # growth=60 (would be Hold), risk=71 → risk>70 fires first → Avoid
        s = AreaSignals(
            infrastructure=60, job_growth=60, population_growth=60, commercial_activity=60,
            transaction_velocity=60, land_scarcity=60, government_spending=60,
            flood_risk=71, water_risk=71, legal_risk=71, overvaluation_risk=71,
            pollution_risk=71, crime_risk=71, delay_risk=71,
        )
        result = score_area(s)
        assert result.growth_score == 60.0
        assert result.risk_score == 71.0
        assert result.recommendation == "Avoid"

    def test_avoid_boundary_risk_exactly_70(self):
        # risk=70 → NOT > 70, so risk override does not fire
        # growth=60 → Hold
        s = AreaSignals(
            infrastructure=60, job_growth=60, population_growth=60, commercial_activity=60,
            transaction_velocity=60, land_scarcity=60, government_spending=60,
            flood_risk=70, water_risk=70, legal_risk=70, overvaluation_risk=70,
            pollution_risk=70, crime_risk=70, delay_risk=70,
        )
        result = score_area(s)
        assert result.risk_score == 70.0
        # risk is exactly 70, NOT > 70, so Hold applies
        assert result.recommendation == "Hold"

    # Sell
    def test_sell_high_growth_elevated_risk(self):
        # growth>65, risk>=55 and risk<=70 → else branch → Sell
        s = AreaSignals(
            infrastructure=75, job_growth=75, population_growth=75, commercial_activity=75,
            transaction_velocity=75, land_scarcity=75, government_spending=75,
            flood_risk=60, water_risk=60, legal_risk=60, overvaluation_risk=60,
            pollution_risk=60, crime_risk=60, delay_risk=60,
        )
        result = score_area(s)
        assert result.growth_score == 75.0
        assert result.risk_score == 60.0
        assert result.recommendation == "Sell"

    def test_no_combination_produces_undefined_recommendation(self):
        """Exhaustive sweep: every output must be a valid recommendation string."""
        test_points = [0, 25, 44, 45, 50, 65, 66, 70, 71, 80, 81, 100]
        for g in test_points:
            for r in test_points:
                s = AreaSignals(
                    infrastructure=g, job_growth=g, population_growth=g,
                    commercial_activity=g, transaction_velocity=g,
                    land_scarcity=g, government_spending=g,
                    flood_risk=r, water_risk=r, legal_risk=r,
                    overvaluation_risk=r, pollution_risk=r,
                    crime_risk=r, delay_risk=r,
                )
                result = score_area(s)
                assert result.recommendation in VALID_RECS, (
                    f"Invalid recommendation '{result.recommendation}' "
                    f"for growth={g}, risk={r}"
                )


# ---------------------------------------------------------------------------
# Score determinism
# ---------------------------------------------------------------------------

class TestDeterminism:

    def test_identical_inputs_produce_identical_outputs(self):
        s = make_signals(
            infrastructure=72, job_growth=65, population_growth=58,
            commercial_activity=78, transaction_velocity=60,
            land_scarcity=80, government_spending=55,
            flood_risk=35, water_risk=42, legal_risk=30,
            overvaluation_risk=28, pollution_risk=38,
            crime_risk=25, delay_risk=40,
        )
        r1 = score_area(s)
        r2 = score_area(s)
        assert r1.growth_score == r2.growth_score
        assert r1.risk_score == r2.risk_score
        assert r1.confidence_score == r2.confidence_score
        assert r1.recommendation == r2.recommendation

    def test_confidence_passthrough(self):
        s = make_signals(flood_risk=0, water_risk=0, legal_risk=0,
                         overvaluation_risk=0, pollution_risk=0,
                         crime_risk=0, delay_risk=0)
        assert score_area(s, confidence=90.0).confidence_score == 90.0
        assert score_area(s, confidence=60.5).confidence_score == 60.5
        assert score_area(s).confidence_score == 75.0  # default

    def test_result_is_dataclass_with_all_fields(self):
        r = score_area(make_signals())
        assert isinstance(r, ScoringResult)
        assert isinstance(r.growth_score, float)
        assert isinstance(r.risk_score, float)
        assert isinstance(r.confidence_score, float)
        assert isinstance(r.recommendation, str)
