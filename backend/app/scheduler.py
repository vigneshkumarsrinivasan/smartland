"""
APScheduler background scheduler for LandSignal AI.

Jobs:
  check_price_alerts   — daily at 02:00 UTC
                         Checks each active Alert against the area's latest prediction.
                         Fires if growth_score or risk_score changed by ≥ threshold points,
                         or if the last AreaPriceHistory price changed by ≥ threshold %.

  send_weekly_digest   — every Monday at 03:00 UTC
                         Sends a digest email/WhatsApp to users who have any active alerts,
                         summarising all their watched areas' current scores.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ── Job functions ──────────────────────────────────────────────────────────────

def check_price_alerts() -> None:
    """Daily job: evaluate all active alerts and send notifications if thresholds crossed."""
    from app.database import SessionLocal
    from app.models import Alert, Prediction, AreaPriceHistory
    from app.notifications import send_alert_email, send_alert_whatsapp

    logger.info("[scheduler] check_price_alerts starting")
    db = SessionLocal()
    fired = 0
    try:
        alerts = db.query(Alert).filter(Alert.is_active == True).all()
        for alert in alerts:
            area = alert.area
            if not area:
                continue

            # Latest prediction
            pred = (
                db.query(Prediction)
                .filter(Prediction.area_id == area.id)
                .order_by(Prediction.generated_at.desc())
                .first()
            )
            if not pred:
                continue

            triggered = False
            message = ""

            if alert.alert_type in ("score_change", "price_movement"):
                # Check score change since last trigger (or last 24h if never triggered)
                since = alert.last_triggered_at or (datetime.utcnow() - timedelta(days=1))
                prev_pred = (
                    db.query(Prediction)
                    .filter(
                        Prediction.area_id == area.id,
                        Prediction.generated_at <= since,
                    )
                    .order_by(Prediction.generated_at.desc())
                    .first()
                )

                if alert.alert_type == "score_change" and prev_pred:
                    delta_growth = abs(pred.growth_score - prev_pred.growth_score)
                    delta_risk = abs(pred.risk_score - prev_pred.risk_score)
                    threshold = alert.threshold or 10.0
                    if delta_growth >= threshold or delta_risk >= threshold:
                        triggered = True
                        direction = "improved" if pred.growth_score > prev_pred.growth_score else "declined"
                        message = (
                            f"{area.name}'s growth score has {direction} by "
                            f"{delta_growth:.1f} points to {pred.growth_score:.0f}/100."
                        )

                elif alert.alert_type == "price_movement":
                    # Compare latest vs previous AreaPriceHistory entry
                    history = (
                        db.query(AreaPriceHistory)
                        .filter(AreaPriceHistory.area_id == area.id)
                        .order_by(AreaPriceHistory.date.desc())
                        .limit(2)
                        .all()
                    )
                    if len(history) == 2:
                        latest, prev = history[0], history[1]
                        if prev.price_sqft > 0:
                            pct_change = (latest.price_sqft - prev.price_sqft) / prev.price_sqft * 100
                            threshold = alert.threshold or 5.0
                            if abs(pct_change) >= threshold:
                                triggered = True
                                direction = "risen" if pct_change > 0 else "fallen"
                                message = (
                                    f"{area.name} prices have {direction} by {abs(pct_change):.1f}% "
                                    f"to ₹{latest.price_sqft:,.0f}/sqft."
                                )

            if not triggered:
                continue

            user = alert.user
            if not user:
                continue

            # Send email
            if alert.channel in ("email", "both") and user.email:
                send_alert_email(
                    to=user.email,
                    area_name=area.name,
                    city=area.city.name if area.city else "",
                    alert_type=alert.alert_type,
                    message=message,
                    growth_score=pred.growth_score,
                    risk_score=pred.risk_score,
                    recommendation=pred.recommendation,
                )

            # Send WhatsApp
            if alert.channel in ("whatsapp", "both") and alert.phone:
                send_alert_whatsapp(
                    phone=alert.phone,
                    area_name=area.name,
                    recommendation=pred.recommendation,
                    growth_score=pred.growth_score,
                    message=message,
                )

            alert.last_triggered_at = datetime.utcnow()
            fired += 1

        if fired:
            db.commit()
        logger.info("[scheduler] check_price_alerts done — fired=%d", fired)
    except Exception as exc:
        logger.error("[scheduler] check_price_alerts error: %s", exc)
    finally:
        db.close()


def send_weekly_digest() -> None:
    """Weekly job: send digest email to users who have active alerts."""
    from app.database import SessionLocal
    from app.models import Alert, Prediction
    from app.notifications import send_weekly_digest_email, send_whatsapp

    logger.info("[scheduler] send_weekly_digest starting")
    db = SessionLocal()
    sent = 0
    try:
        # Group active alerts by user
        alerts = db.query(Alert).filter(Alert.is_active == True).all()
        user_areas: dict[int, dict] = {}
        for alert in alerts:
            uid = alert.user_id
            if uid not in user_areas:
                user_areas[uid] = {"user": alert.user, "areas": set()}
            user_areas[uid]["areas"].add(alert.area_id)

        for uid, data in user_areas.items():
            user = data["user"]
            if not user or not user.email:
                continue

            area_summaries = []
            for area_id in data["areas"]:
                from app.models import Area
                area = db.query(Area).filter(Area.id == area_id).first()
                pred = (
                    db.query(Prediction)
                    .filter(Prediction.area_id == area_id)
                    .order_by(Prediction.generated_at.desc())
                    .first()
                )
                if area and pred:
                    area_summaries.append({
                        "name": area.name,
                        "city": area.city.name if area.city else "",
                        "growth_score": pred.growth_score,
                        "risk_score": pred.risk_score,
                        "recommendation": pred.recommendation,
                        "current_price_sqft": area.current_price_sqft,
                    })

            if area_summaries:
                send_weekly_digest_email(user.email, sorted(area_summaries, key=lambda x: -x["growth_score"]))
                sent += 1

        logger.info("[scheduler] send_weekly_digest done — sent=%d", sent)
    except Exception as exc:
        logger.error("[scheduler] send_weekly_digest error: %s", exc)
    finally:
        db.close()


# ── Lifecycle ──────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        check_price_alerts,
        trigger=CronTrigger(hour=2, minute=0),
        id="check_price_alerts",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        send_weekly_digest,
        trigger=CronTrigger(day_of_week="mon", hour=3, minute=0),
        id="send_weekly_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "[scheduler] started — jobs: %s",
        [j.id for j in _scheduler.get_jobs()],
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] stopped")
