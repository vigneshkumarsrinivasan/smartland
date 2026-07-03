"""
Notification delivery — Email (Resend) + WhatsApp (Interakt).

Both channels are mock-safe: if the API key is not configured, the message
is logged to stdout instead of sent. This keeps dev/CI working without
real credentials while the same code path runs in production.

Email:  Set RESEND_API_KEY  → emails sent via api.resend.com
WhatsApp: Set INTERAKT_API_KEY → messages sent via Interakt WhatsApp Business API
"""
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
INTERAKT_API_KEY = os.getenv("INTERAKT_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "alerts@landsignal.ai")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success."""
    if not RESEND_API_KEY:
        logger.info("[MOCK EMAIL] to=%s subject=%s", to, subject)
        return True

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info("Email sent to %s (id=%s)", to, resp.json().get("id"))
            return True
        logger.warning("Resend API error %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("Email delivery failed: %s", exc)
        return False


def send_alert_email(
    to: str,
    area_name: str,
    city: str,
    alert_type: str,
    message: str,
    growth_score: float,
    risk_score: float,
    recommendation: str,
) -> bool:
    badge_color = {
        "Strong Buy": "#059669",
        "Buy": "#0891b2",
        "Hold": "#d97706",
        "Avoid": "#ea580c",
        "Sell": "#dc2626",
    }.get(recommendation, "#6b7280")

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:20px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;">
    <div style="background:#0f172a;padding:20px 24px;">
      <span style="color:#06b6d4;font-weight:700;font-size:16px;">LandSignal AI</span>
      <span style="color:#64748b;font-size:12px;margin-left:8px;">Alert</span>
    </div>
    <div style="padding:24px;">
      <h2 style="color:#0f172a;margin:0 0 4px;">{area_name}</h2>
      <p style="color:#64748b;margin:0 0 16px;font-size:14px;">{city}</p>
      <p style="color:#374151;font-size:15px;line-height:1.6;">{message}</p>
      <div style="display:flex;gap:12px;margin:20px 0;">
        <div style="flex:1;background:#f8fafc;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#0891b2;">{growth_score:.0f}</div>
          <div style="font-size:11px;color:#6b7280;">Growth Score</div>
        </div>
        <div style="flex:1;background:#f8fafc;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#f97316;">{risk_score:.0f}</div>
          <div style="font-size:11px;color:#6b7280;">Risk Score</div>
        </div>
        <div style="flex:1;background:#f8fafc;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:13px;font-weight:700;color:{badge_color};">{recommendation}</div>
          <div style="font-size:11px;color:#6b7280;">Signal</div>
        </div>
      </div>
      <a href="{FRONTEND_URL}/analyzer"
         style="display:inline-block;background:#06b6d4;color:#fff;font-weight:600;font-size:14px;padding:10px 20px;border-radius:8px;text-decoration:none;">
        View Full Report →
      </a>
    </div>
    <div style="background:#f8fafc;padding:14px 24px;border-top:1px solid #e5e7eb;">
      <p style="color:#9ca3af;font-size:11px;margin:0;">
        You're receiving this because you set up a {alert_type.replace('_', ' ')} alert for {area_name}.
        <a href="{FRONTEND_URL}/watchlist" style="color:#06b6d4;">Manage alerts</a>
      </p>
    </div>
  </div>
</body>
</html>
"""
    subject = f"LandSignal Alert: {area_name} — {recommendation}"
    return send_email(to, subject, html)


def send_weekly_digest_email(
    to: str,
    areas: list[dict],
) -> bool:
    rows = ""
    for a in areas:
        badge_color = {
            "Strong Buy": "#059669", "Buy": "#0891b2",
            "Hold": "#d97706", "Avoid": "#ea580c", "Sell": "#dc2626",
        }.get(a.get("recommendation", ""), "#6b7280")
        rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;">{a['name']}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;color:#6b7280;font-size:13px;">{a['city']}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;text-align:center;font-weight:700;color:#0891b2;">{a.get('growth_score', 0):.0f}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;text-align:center;font-weight:700;color:#f97316;">{a.get('risk_score', 0):.0f}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;text-align:center;">
            <span style="color:{badge_color};font-weight:600;font-size:12px;">{a.get('recommendation', '—')}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #f0f4f8;text-align:right;font-size:13px;">₹{a.get('current_price_sqft', 0):,.0f}</td>
        </tr>"""

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;">
    <div style="background:#0f172a;padding:20px 24px;">
      <span style="color:#06b6d4;font-weight:700;font-size:16px;">LandSignal AI</span>
      <span style="color:#64748b;font-size:12px;margin-left:8px;">Weekly Digest</span>
    </div>
    <div style="padding:24px;">
      <h2 style="color:#0f172a;margin:0 0 4px;">Your Watchlist Summary</h2>
      <p style="color:#64748b;margin:0 0 20px;font-size:14px;">Here's how your tracked areas are performing this week.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f8fafc;">
            <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;font-weight:600;">Area</th>
            <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;font-weight:600;">City</th>
            <th style="padding:10px 8px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">Growth</th>
            <th style="padding:10px 8px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">Risk</th>
            <th style="padding:10px 8px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">Signal</th>
            <th style="padding:10px 8px;text-align:right;font-size:12px;color:#64748b;font-weight:600;">Price/sqft</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <div style="margin-top:20px;">
        <a href="{FRONTEND_URL}/map"
           style="display:inline-block;background:#06b6d4;color:#fff;font-weight:600;font-size:14px;padding:10px 20px;border-radius:8px;text-decoration:none;">
          Open Growth Map →
        </a>
      </div>
    </div>
    <div style="background:#f8fafc;padding:14px 24px;border-top:1px solid #e5e7eb;">
      <p style="color:#9ca3af;font-size:11px;margin:0;">
        Weekly digest from LandSignal AI.
        <a href="{FRONTEND_URL}/watchlist" style="color:#06b6d4;">Manage alerts</a>
      </p>
    </div>
  </div>
</body>
</html>
"""
    return send_email(to, "LandSignal AI — Your Weekly Watchlist Digest", html)


# ── WhatsApp (Interakt) ───────────────────────────────────────────────────────

def send_whatsapp(phone: str, template_name: str, body_values: list[str]) -> bool:
    """
    Send a WhatsApp message via Interakt template API.
    phone: E.164 format without '+', e.g. "919876543210"
    template_name: pre-approved template in Interakt dashboard
    body_values: list of positional variables for the template body
    """
    if not INTERAKT_API_KEY:
        logger.info("[MOCK WHATSAPP] phone=%s template=%s values=%s", phone, template_name, body_values)
        return True

    try:
        import base64
        encoded = base64.b64encode(INTERAKT_API_KEY.encode()).decode()
        resp = requests.post(
            "https://api.interakt.ai/v1/public/message/",
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json",
            },
            json={
                "countryCode": "+91",
                "phoneNumber": phone,
                "callbackData": "landsignal_alert",
                "type": "Template",
                "template": {
                    "name": template_name,
                    "languageCode": "en",
                    "bodyValues": body_values,
                },
            },
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info("WhatsApp sent to %s via template %s", phone, template_name)
            return True
        logger.warning("Interakt API error %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("WhatsApp delivery failed: %s", exc)
        return False


def send_alert_whatsapp(
    phone: str,
    area_name: str,
    recommendation: str,
    growth_score: float,
    message: str,
) -> bool:
    """Send a price/score alert via WhatsApp using the 'landsignal_alert' template."""
    return send_whatsapp(
        phone,
        template_name="landsignal_alert",
        body_values=[area_name, recommendation, f"{growth_score:.0f}", message],
    )
