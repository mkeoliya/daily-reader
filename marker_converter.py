"""
marker.py — PDF conversion wrapper using Marker's Python API.

Uses PdfConverter with our custom DailyReaderRenderer to produce
mobile-first styled HTML directly from PDF files.

Usage:
    from marker import MarkerConverter
    converter = MarkerConverter()
    result = converter.convert("path/to/file.pdf")
    # result.html  → styled HTML string
    # result.images → dict of extracted images
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.renderers.html import HTMLOutput

logger = logging.getLogger(__name__)


class MarkerConverter:
    """Thin wrapper around Marker's PdfConverter with our custom renderer."""

    def __init__(
        self,
        renderer: str = "renderer.engine.DailyReaderRenderer",
        use_llm: bool = False,
        llm_service: Optional[str] = None,
    ):
        """
        Initialize the converter.

        Args:
            renderer: Import path for the renderer class.
                      Default uses our custom DailyReaderRenderer.
            use_llm: Whether to use LLM for improved accuracy on
                     complex tables, math, and layouts.
            llm_service: LLM service import path, e.g.
                         "marker.services.gemini.GoogleGeminiService"
        """
        # Load model artifacts (downloads on first use, cached thereafter)
        models = create_model_dict()

        kwargs: dict = {
            "artifact_dict": models,
            "renderer": renderer,
        }
        if use_llm and llm_service:
            kwargs["llm_service"] = llm_service

        self.converter = PdfConverter(**kwargs)
        self.use_llm = use_llm

    def convert(
        self, pdf_path: str | Path, page_range: list[int] | None = None
    ) -> HTMLOutput:
        """
        Convert a PDF to styled HTML.

        Args:
            pdf_path: Path to the PDF file.
            page_range: Optional list of 0-indexed page numbers to convert.
                        If None, converts all pages.

        Returns:
            HTMLOutput with .html, .images, and .metadata
        """
        pdf_path = str(pdf_path)
        pages_desc = f"pages {page_range}" if page_range else "all pages"
        logger.info(f"Converting: {pdf_path} ({pages_desc})")

        # Pass page_range via config so PdfProvider only processes those pages
        if page_range is not None:
            self.converter.config = self.converter.config or {}
            if isinstance(self.converter.config, dict):
                self.converter.config["page_range"] = page_range

        result = self.converter(pdf_path)

        page_count = len(result.metadata.get("page_stats", []))
        logger.info(f"Conversion complete: {page_count} pages")

        return result
