"""
renderer/engine.py — Rendering logic for Daily Reader.

Contains all Python logic for generating styled HTML pages via Jinja2
templates. Subclasses Marker's HTMLRenderer for PDF pipeline integration.

Usage:
    from renderer import render_page_html
    html = render_page_html("<p>Hello</p>", title="My Book", progress_pct=42.0)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from bs4 import BeautifulSoup
from marker.renderers.html import HTMLRenderer, HTMLOutput
from marker.schema.document import Document


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
# Document / Page abstractions (format-agnostic, for future ePUB/HTML/etc.)
# ---------------------------------------------------------------------------


@dataclass
class ReaderDocument:
    """Format-agnostic document metadata."""

    title: str
    total_pages: int
    source_path: Path
    source_format: str = "pdf"  # future: "epub", "html", etc.


@dataclass
class ReaderPage:
    """A single rendered page with metadata."""

    html_content: str
    page_number: int
    document: ReaderDocument
    section_title: Optional[str] = None
    word_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _estimate_reading_time(html: str) -> int:
    """Estimate reading time in minutes from HTML content."""
    text = re.sub(r"<[^>]+>", "", html)
    words = len(text.split())
    return max(1, math.ceil(words / 200))


def _convert_math_tags(html: str) -> str:
    """Convert Marker's <math display='inline'>...</math> to KaTeX delimiters."""
    # Inline math: <math display="inline">...</math> → $...$
    html = re.sub(
        r'<math\s+display="inline">(.*?)</math>',
        r"$\1$",
        html,
        flags=re.DOTALL,
    )
    # Display math: <math display="block">...</math> → $$...$$
    html = re.sub(
        r'<math\s+display="block">(.*?)</math>',
        r"$$\1$$",
        html,
        flags=re.DOTALL,
    )
    # Plain <math>...</math> → $...$
    html = re.sub(
        r"<math>(.*?)</math>",
        r"$\1$",
        html,
        flags=re.DOTALL,
    )
    return html


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
) -> str:
    """Wrap body HTML in a full styled page."""
    if reading_time is None:
        reading_time = _estimate_reading_time(body_html)

    body_html = _convert_math_tags(body_html)

    tmpl = _env.get_template("page.html")
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

    # Normalize items to have url/subtitle keys
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
    books: list[ReaderDocument], progress: dict[str, int] | None = None
) -> str:
    """Render a minimalist bookshelf page with progress."""
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


# ---------------------------------------------------------------------------
# Custom Marker Renderer
# ---------------------------------------------------------------------------


class DailyReaderRenderer(HTMLRenderer):
    """
    Custom Marker renderer that produces mobile-first styled HTML.

    Plugs into Marker via:
        PdfConverter(artifact_dict={}, renderer="renderer.engine.DailyReaderRenderer")
    """

    # Inherited from BaseRenderer — filter out page headers/footers
    keep_pageheader_in_output: bool = False
    keep_pagefooter_in_output: bool = False
    paginate_output: bool = True  # wrap each page in <div class='page'>

    def __call__(self, document: Document) -> HTMLOutput:
        document_output = document.render(self.block_config)
        full_html, images = self.extract_html(document, document_output)

        # Apply math tag conversion
        full_html = _convert_math_tags(full_html)

        # Build document metadata for the header
        title = self._extract_title(document)
        total_pages = len(document.pages)

        styled_html = render_page_html(
            body_html=full_html,
            title=title,
            page_info=f"{total_pages} pages",
            progress_pct=100.0,  # full doc render shows 100%
        )

        return HTMLOutput(
            html=styled_html,
            images=images,
            metadata=self.generate_document_metadata(document, document_output),
        )

    def _extract_title(self, document: Document) -> str:
        """Try to extract a title from the document's table of contents."""
        toc = document.table_of_contents
        if toc:
            return toc[0].get("title", "Untitled")
        return "Untitled"
