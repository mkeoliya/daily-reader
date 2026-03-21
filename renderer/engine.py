"""
renderer/engine.py — Format-agnostic rendering for Daily Reader.

Pure HTML → styled page layer. No knowledge of PDF, Marker, or any specific
document format. All format-specific post-processing belongs in documents.py.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader


# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"

_env = Environment(
    loader=FileSystemLoader([str(_TEMPLATE_DIR), str(_STATIC_DIR)]),
    autoescape=False,  # we handle escaping manually; body_html is trusted
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _estimate_reading_time(html: str) -> int:
    """Estimate reading time in minutes from HTML content."""
    text = re.sub(r"<[^>]+>", "", html)
    words = len(text.split())
    return max(1, math.ceil(words / 200))


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


def render_page_html(
    body_html: str,
    title: str = "Daily Reader",
    page_info: str = "",
    reading_time: Optional[int] = None,
    progress_pct: Optional[float] = None,
    is_last_page: bool = False,
    template: str = "page",
) -> str:
    """Wrap body HTML in a full styled page.

    Args:
        template: Template name without .html extension (e.g. "page", "ml").
                  Must be a file in renderer/templates/{name}.html that
                  extends base.html.
    """
    if reading_time is None:
        reading_time = _estimate_reading_time(body_html)

    tmpl = _env.get_template(f"{template}.html")
    return tmpl.render(
        title=title,
        page_info=page_info,
        reading_time=reading_time,
        progress_pct=progress_pct,
        is_last_page=is_last_page,
        body_html=body_html,
    )


def render_today_page(items: list[dict]) -> str:
    """Render the 'Today's Reading' index page."""
    import datetime

    today = datetime.date.today().strftime("%B %d, %Y")

    normalized = []
    for item in items:
        normalized.append({
            "title": item["title"],
            "subtitle": item.get("subtitle", ""),
            "url": item.get("url", "#"),
        })

    tmpl = _env.get_template("today.html")
    return tmpl.render(title="Today's Reading", today_date=today, items=normalized)


def render_bookshelf(
    books: list, progress: dict[str, int] | None = None
) -> str:
    """Render a minimalist bookshelf page with progress.

    Args:
        books: List of objects with .title and .total_pages attributes.
        progress: Dict mapping title → current page number.
    """
    progress = progress or {}

    book_data = []
    for book in books:
        current = progress.get(book.title, 0)
        pct = (current / book.total_pages * 100) if book.total_pages > 0 else 0
        book_data.append({
            "title": book.title,
            "current": current,
            "total": book.total_pages,
            "pct": pct,
            "pct_int": int(pct),
        })

    tmpl = _env.get_template("bookshelf.html")
    return tmpl.render(title="Bookshelf", books=book_data)
