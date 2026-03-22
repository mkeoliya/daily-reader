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


def _slugify(name: str) -> str:
    """Simple slug from a section name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------


def render_daily_page(
    sections: list[dict],
    title: str = "Daily Reader",
    today_date: str = "",
    has_pdf: bool = False,
) -> str:
    """Render a combined daily page with all sections.

    Args:
        sections: List of dicts, each with:
            - section_name: str (e.g. "ml", "books")
            - documents: list of dicts with title, page_info, body_html,
              and optionally pdf_filename
        title: Page title.
        today_date: Formatted date string.
        has_pdf: Whether any document has a PDF viewer attachment.
    """
    # Compute combined reading time and add slugs
    all_html = ""
    for s in sections:
        s["slug"] = _slugify(s["section_name"])
        for doc in s["documents"]:
            all_html += doc["body_html"]

    reading_time = _estimate_reading_time(all_html)

    tmpl = _env.get_template("page.html")
    return tmpl.render(
        title=title,
        today_date=today_date,
        reading_time=reading_time,
        sections=sections,
        has_pdf=has_pdf,
    )


def render_bookshelf(sections: list) -> str:
    """Render a minimalist bookshelf page with progress.

    Args:
        sections: List of Section objects with .queue (DocumentQueue entries)
                  and .finished lists.
    """
    book_data = []
    for section in sections:
        for entry in section.queue:
            total = entry.doc.total_pages
            current = entry.current_page
            pct = (current / total * 100) if total > 0 else 0
            book_data.append({
                "title": entry.doc.title,
                "current": current,
                "total": total,
                "pct": pct,
                "pct_int": int(pct),
                "section": section.name,
            })
        for name in section.finished:
            book_data.append({
                "title": Path(name).stem,
                "current": 1,
                "total": 1,
                "pct": 100,
                "pct_int": 100,
                "section": section.name,
            })

    tmpl = _env.get_template("bookshelf.html")
    return tmpl.render(title="Bookshelf", books=book_data)
