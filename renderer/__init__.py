"""
renderer — Daily Reader rendering package.

Re-exports public API for backward compatibility:
    from renderer import render_page_html, DailyReaderRenderer, ...
"""

from renderer.engine import (
    render_page_html,
    render_today_page,
    render_bookshelf,
    DailyReaderRenderer,
    ReaderDocument,
    ReaderPage,
    _estimate_reading_time,
    _convert_math_tags,
)

__all__ = [
    "render_page_html",
    "render_today_page",
    "render_bookshelf",
    "DailyReaderRenderer",
    "ReaderDocument",
    "ReaderPage",
    "_estimate_reading_time",
    "_convert_math_tags",
]
