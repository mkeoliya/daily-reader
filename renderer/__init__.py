"""
renderer — Daily Reader rendering package.

Re-exports public API:
    from renderer import render_page_html, render_bookshelf, ...
"""

from renderer.engine import (
    render_page_html,
    render_today_page,
    render_bookshelf,
    _estimate_reading_time,
)

__all__ = [
    "render_page_html",
    "render_today_page",
    "render_bookshelf",
    "_estimate_reading_time",
]
