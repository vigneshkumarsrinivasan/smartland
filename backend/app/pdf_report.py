"""
PDF report renderer using WeasyPrint + Jinja2.

Falls back to returning raw HTML if WeasyPrint is unavailable (e.g. missing
GTK+ runtime on Windows dev machines). The HTML template is styled for both
screen preview and print-to-PDF from the browser.
"""
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

# Register enumerate as both filter (for `list | enumerate` syntax) and global
_jinja_env.filters["enumerate"] = enumerate
_jinja_env.globals["enumerate"] = enumerate

try:
    import weasyprint as _wp
    _WEASYPRINT_AVAILABLE = True
except Exception:
    _WEASYPRINT_AVAILABLE = False


def _rec_slug(recommendation: str) -> str:
    return recommendation.lower().replace(" ", "-")


def render_report(report_data: dict) -> tuple[bytes, str]:
    """
    Render the area report to PDF (or HTML fallback).

    Returns:
        (content_bytes, media_type)
        media_type is "application/pdf" or "text/html"
    """
    area = report_data["area"]
    now = datetime.utcnow()

    ctx = {
        "area": {
            **area,
            "recommendation": area["recommendation"],
        },
        "rec_slug": _rec_slug(area["recommendation"]),
        "ai_summary": report_data["ai_summary"],
        "growth_signals": report_data["growth_signals"],
        "risk_signals": report_data["risk_signals"],
        "price_history": report_data["price_history"],
        "infrastructure_projects": report_data["infrastructure_projects"],
        "forecast": report_data["forecast"],
        "generated_at": now.strftime("%d %b %Y, %H:%M UTC"),
        "generated_year": now.year,
    }

    template = _jinja_env.get_template("report.html")
    html_str = template.render(**ctx)

    if _WEASYPRINT_AVAILABLE:
        pdf_bytes = _wp.HTML(string=html_str).write_pdf()
        return pdf_bytes, "application/pdf"

    # WeasyPrint not available — return styled HTML; user can print to PDF
    return html_str.encode("utf-8"), "text/html"


def is_pdf_available() -> bool:
    return _WEASYPRINT_AVAILABLE
