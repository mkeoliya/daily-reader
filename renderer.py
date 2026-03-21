"""
renderer.py — Custom Marker renderer for Daily Reader.

Subclasses Marker's HTMLRenderer to produce mobile-first, styled HTML
with KaTeX math rendering, dark mode, progress bar, and reading time.

Usage with Marker's PdfConverter:
    converter = PdfConverter(
        artifact_dict={},
        renderer="renderer:DailyReaderRenderer"
    )
    result = converter("path/to/file.pdf")
    # result.html is fully styled, self-contained HTML
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from marker.renderers.html import HTMLRenderer, HTMLOutput
from marker.schema.document import Document


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
# CSS
# ---------------------------------------------------------------------------

DAILY_READER_CSS = """\
:root {
    --text: #1a1a2e;
    --text-secondary: #4a4a6a;
    --text-muted: #8888a0;
    --bg: #fefefe;
    --bg-alt: #f8f7f4;
    --bg-code: #f5f4f0;
    --accent: #2d5a8e;
    --accent-light: #e8f0fe;
    --border: #e2e0dc;
    --max-width: 680px;
    --radius: 8px;
}

@media (prefers-color-scheme: dark) {
    :root {
        --text: #e0e0e8;
        --text-secondary: #a0a0b8;
        --text-muted: #6a6a80;
        --bg: #0f0f14;
        --bg-alt: #161620;
        --bg-code: #1c1c28;
        --accent: #5b9bd5;
        --accent-light: #1a2a3e;
        --border: #2a2a3a;
    }
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html {
    font-size: 18px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    scroll-behavior: smooth;
}

body {
    font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
    line-height: 1.75;
    color: var(--text);
    background: var(--bg);
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
}

/* -- Header / progress -- */
.dr-header {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}

.dr-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.25rem;
}

.dr-meta {
    font-size: 0.8rem;
    color: var(--text-muted);
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
}

.dr-progress-bar {
    width: 100%;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
}

.dr-progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.3s ease;
}

.dr-done {
    text-align: center;
    padding: 2rem;
    margin-top: 2rem;
    font-family: 'Inter', sans-serif;
    color: var(--text-muted);
    font-size: 0.9rem;
    border-top: 1px solid var(--border);
}

.dr-done .checkmark {
    font-size: 2rem;
    display: block;
    margin-bottom: 0.5rem;
}

/* -- Content typography -- */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.3;
    margin-top: 2.5rem;
    margin-bottom: 0.75rem;
    color: var(--text);
}

h1 { font-size: 2rem; font-weight: 700; border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem; margin-top: 3rem; }
h2 { font-size: 1.5rem; font-weight: 600; color: var(--accent); }
h3, h4 { font-size: 1.15rem; font-weight: 600; color: var(--text-secondary); }

p {
    margin-bottom: 1.25rem;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

blockquote {
    border-left: 3px solid var(--accent);
    margin: 1.5rem 0;
    padding: 0.75rem 1.25rem;
    color: var(--text-secondary);
    background: var(--accent-light);
    border-radius: 0 var(--radius) var(--radius) 0;
    font-style: italic;
}

pre {
    background: var(--bg-code);
    padding: 1rem 1.25rem;
    border-radius: var(--radius);
    overflow-x: auto;
    font-size: 0.85rem;
    line-height: 1.6;
    margin: 1.5rem 0;
    border: 1px solid var(--border);
}

code {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.85em;
    background: var(--bg-code);
    padding: 0.15em 0.4em;
    border-radius: 4px;
}

pre code { background: none; padding: 0; font-size: inherit; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5rem 0;
    font-size: 0.9rem;
}

th, td { border: 1px solid var(--border); padding: 0.6rem 0.9rem; text-align: left; }
th {
    background: var(--accent-light);
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

img {
    max-width: 100%;
    height: auto;
    border-radius: var(--radius);
    margin: 1.5rem auto;
    display: block;
}

a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s ease; }
a:hover { border-bottom-color: var(--accent); }

.katex-display { margin: 1.5rem 0; overflow-x: auto; padding: 0.5rem 0; }

ul, ol { margin: 1rem 0 1.5rem 1.5rem; }
li { margin-bottom: 0.4rem; }

hr { border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }

/* -- Page separator -- */
.page { margin-bottom: 2rem; }
.page + .page { padding-top: 2rem; border-top: 1px dashed var(--border); }

/* -- Responsive -- */
@media (max-width: 600px) {
    html { font-size: 16px; }
    body { padding: 1rem 1rem 3rem; }
    h1 { font-size: 1.6rem; }
    h2 { font-size: 1.3rem; }
    .dr-meta { flex-direction: column; gap: 0.25rem; }
}

/* -- Bookshelf -- */
.bookshelf { list-style: none; padding: 0; margin: 0; }
.bookshelf li {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border);
}

.bookshelf .progress-ring {
    flex-shrink: 0;
    width: 48px;
    height: 48px;
}

.bookshelf .book-info { flex: 1; }
.bookshelf .book-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: var(--text);
}

.bookshelf .book-progress {
    font-size: 0.8rem;
    color: var(--text-muted);
}
"""


# ---------------------------------------------------------------------------
# HTML template helpers
# ---------------------------------------------------------------------------

KATEX_HEAD = """\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false},
            {left: '\\\\(', right: '\\\\)', display: false},
            {left: '\\\\[', right: '\\\\]', display: true}
        ],
        throwOnError: false
    });"></script>"""

GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,600;0,700;1,400'
    '&family=Inter:wght@400;500;600;700'
    '&family=JetBrains+Mono:wght@400;500'
    '&display=swap" rel="stylesheet">'
)


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

    progress_bar = ""
    if progress_pct is not None:
        progress_bar = f"""\
<div class="dr-progress-bar">
  <div class="dr-progress-fill" style="width: {progress_pct:.1f}%"></div>
</div>"""

    done_marker = ""
    if is_last_page:
        done_marker = """\
<div class="dr-done">
  <span class="checkmark">✅</span>
  Done for today. See you tomorrow.
</div>"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{GOOGLE_FONTS}
{KATEX_HEAD}
<style>
{DAILY_READER_CSS}
</style>
</head>
<body>
  <header class="dr-header">
    <h1>{title}</h1>
    <div class="dr-meta">
      <span>{page_info}</span>
      <span>~{reading_time} min read</span>
    </div>
    {progress_bar}
  </header>
  <main>
    {body_html}
  </main>
  {done_marker}
</body>
</html>"""


def render_today_page(items: list[dict]) -> str:
    """Render the 'Today's Reading' index page."""
    import datetime

    cards = []
    for item in items:
        cards.append(f"""\
<li>
  <div class="book-info">
    <div class="book-title"><a href="{item.get('url', '#')}">{item['title']}</a></div>
    <div class="book-progress">{item.get('subtitle', '')}</div>
  </div>
</li>""")

    cards_html = "\n".join(cards)
    today = datetime.date.today().strftime("%B %d, %Y")

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Today's Reading — Daily Reader</title>
{GOOGLE_FONTS}
<style>
{DAILY_READER_CSS}
</style>
</head>
<body>
  <header class="dr-header">
    <h1>📖 Today's Reading</h1>
    <div class="dr-meta"><span>{today}</span></div>
  </header>
  <main>
    <ul class="bookshelf">
      {cards_html}
    </ul>
  </main>
</body>
</html>"""


def render_bookshelf(books: list[ReaderDocument], progress: dict[str, int] | None = None) -> str:
    """Render a minimalist bookshelf page with progress."""
    progress = progress or {}
    items = []
    for book in books:
        current = progress.get(book.title, 0)
        pct = (current / book.total_pages * 100) if book.total_pages > 0 else 0
        items.append(f"""\
<li>
  <svg class="progress-ring" viewBox="0 0 48 48">
    <circle cx="24" cy="24" r="20" fill="none" stroke="var(--border)" stroke-width="3"/>
    <circle cx="24" cy="24" r="20" fill="none" stroke="var(--accent)" stroke-width="3"
      stroke-dasharray="{pct * 1.257} {125.7 - pct * 1.257}"
      stroke-linecap="round" transform="rotate(-90 24 24)"/>
    <text x="24" y="27" text-anchor="middle" font-size="11"
      font-family="Inter, sans-serif" fill="var(--text-secondary)">{int(pct)}%</text>
  </svg>
  <div class="book-info">
    <div class="book-title">{book.title}</div>
    <div class="book-progress">Page {current} of {book.total_pages}</div>
  </div>
</li>""")

    items_html = "\n".join(items)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bookshelf — Daily Reader</title>
{GOOGLE_FONTS}
<style>
{DAILY_READER_CSS}
</style>
</head>
<body>
  <header class="dr-header">
    <h1>📚 Bookshelf</h1>
  </header>
  <main>
    <ul class="bookshelf">
      {items_html}
    </ul>
  </main>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Custom Marker Renderer
# ---------------------------------------------------------------------------


class DailyReaderRenderer(HTMLRenderer):
    """
    Custom Marker renderer that produces mobile-first styled HTML.

    Plugs into Marker via:
        PdfConverter(artifact_dict={}, renderer="renderer:DailyReaderRenderer")
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
