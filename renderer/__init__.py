"""
renderer — Daily Reader rendering package.

Re-exports public API:
    from renderer import render_daily_page, render_bookshelf, ...
"""

from renderer.engine import (
    render_daily_page,
    render_section,
    _estimate_reading_time,
)

__all__ = [
    "render_daily_page",
    "render_section",
    "_estimate_reading_time",
]
