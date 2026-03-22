"""
documents.py — Document and Page abstractions for Daily Reader.

Each document type is self-contained: handles its own conversion and any
format-specific post-processing (e.g. math tag conversion for PDFs).
"""

from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import markdown

logger = logging.getLogger(__name__)




# ---------------------------------------------------------------------------
# Core abstractions
# ---------------------------------------------------------------------------


@dataclass
class Page:
    """A single converted page of content."""

    html: str
    page_number: int  # 1-indexed
    images: dict[str, Any] = field(default_factory=dict)


class Document(ABC):
    """Abstract base for any document type (PDF, Markdown, ePub, etc.)."""

    is_pdf: bool = False

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.title: str = source_path.stem
        self.total_pages: int = self._count_pages()

    @abstractmethod
    def _count_pages(self) -> int:
        """Count total pages without doing full conversion."""
        ...

    @abstractmethod
    def get_pages(self, start: int, count: int) -> list[Page]:
        """Return converted pages for a range.

        Args:
            start: 0-indexed start page.
            count: Max number of pages to return.

        Returns:
            List of Page objects (may be fewer than count if near end of doc).
        """
        ...


# ---------------------------------------------------------------------------
# PDF-specific: Marker integration + math tag conversion
# ---------------------------------------------------------------------------



def _convert_math_tags(html: str) -> str:
    """Convert Marker's <math display='inline'>...</math> to KaTeX delimiters.

    This is PDF-specific post-processing: Marker emits MathML-like tags
    that need to be converted to KaTeX's $...$ / $$...$$ delimiters.
    """
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


from marker.renderers.html import HTMLRenderer, HTMLOutput
from marker.schema.document import Document as MarkerDocument


class DailyReaderRenderer(HTMLRenderer):
    """Custom Marker renderer that produces paginated HTML with math conversion.

    Loaded by Marker via string path:
        PdfConverter(renderer="documents.DailyReaderRenderer")
    """

    keep_pageheader_in_output: bool = False
    keep_pagefooter_in_output: bool = False
    paginate_output: bool = True

    def __call__(self, document: MarkerDocument) -> HTMLOutput:
        document_output = document.render(self.block_config)
        full_html, images = self.extract_html(document, document_output)
        full_html = _convert_math_tags(full_html)

        return HTMLOutput(
            html=full_html,
            images=images,
            metadata=self.generate_document_metadata(document, document_output),
        )


class PdfDocument(Document):
    """PDF document — uses Marker for conversion."""

    is_pdf: bool = True
    _converter = None

    @classmethod
    def _get_converter(cls):
        if cls._converter is None:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict

            logger.info("Initializing Marker models...")
            models = create_model_dict()
            cls._converter = PdfConverter(
                artifact_dict=models,
                renderer="documents.DailyReaderRenderer",
            )
        return cls._converter

    def _count_pages(self) -> int:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(self.source_path))
        n = len(doc)
        doc.close()
        return n

    def get_pages(self, start: int, count: int) -> list[Page]:
        from bs4 import BeautifulSoup

        pages_to_take = min(count, self.total_pages - start)
        if pages_to_take <= 0:
            return []

        page_range = list(range(start, start + pages_to_take))
        converter = self._get_converter()

        converter.config = converter.config or {}
        if isinstance(converter.config, dict):
            converter.config["page_range"] = page_range

        result = converter(str(self.source_path))

        # The renderer now returns raw paginated HTML (no styled wrapper)
        # Parse out individual page divs
        soup = BeautifulSoup(result.html, "html.parser")
        page_divs = soup.find_all("div", class_="page")
        if not page_divs:
            page_divs = [soup]

        pages = []
        for i, div in enumerate(page_divs):
            html = _convert_math_tags(str(div))
            pages.append(
                Page(
                    html=html,
                    page_number=start + i + 1,
                    images=result.images if i == 0 else {},
                )
            )

        return pages

    def split_pages(self, start: int, count: int, output_path: Path) -> Path:
        """Extract a page range from the source PDF into a new file.

        Args:
            start: 0-indexed start page.
            count: Number of pages to extract.
            output_path: Where to write the split PDF.

        Returns:
            The output_path for convenience.
        """
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(self.source_path))
        new_doc = pdfium.PdfDocument.new()
        end = min(start + count, len(doc))
        for i in range(start, end):
            new_doc.import_pages(doc, [i])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            new_doc.save(f)
        new_doc.close()
        doc.close()
        logger.info("Split PDF pages %d–%d → %s", start + 1, end, output_path)
        return output_path


# ---------------------------------------------------------------------------
# Markdown document
# ---------------------------------------------------------------------------


class MarkdownDocument(Document):
    """Markdown/text document — uses python-markdown for conversion."""

    _LINES_PER_PAGE = 40
    _MD_EXTENSIONS = [
        "tables",
        "fenced_code",
        "codehilite",
        "def_list",
        "footnotes",
        "md_in_html",
    ]

    def _count_pages(self) -> int:
        text = self.source_path.read_text()
        lines = text.splitlines()
        return max(1, math.ceil(len(lines) / self._LINES_PER_PAGE))

    def get_pages(self, start: int, count: int) -> list[Page]:
        text = self.source_path.read_text()
        lines = text.splitlines(keepends=True)

        pages_to_take = min(count, self.total_pages - start)
        if pages_to_take <= 0:
            return []

        pages = []
        for i in range(pages_to_take):
            page_idx = start + i
            line_start = page_idx * self._LINES_PER_PAGE
            line_end = line_start + self._LINES_PER_PAGE
            page_text = "".join(lines[line_start:line_end])

            if not page_text.strip():
                continue

            html = markdown.markdown(page_text, extensions=self._MD_EXTENSIONS)
            pages.append(
                Page(
                    html=html,
                    page_number=page_idx + 1,
                )
            )

        return pages


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def load_document(path: Path) -> Document:
    """Create the right Document subclass based on file extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return PdfDocument(path)
    elif ext in (".md", ".txt"):
        return MarkdownDocument(path)
    else:
        raise ValueError(f"Unsupported document format: {ext}")
