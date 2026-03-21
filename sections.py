"""
sections.py — Section discovery and configuration for Daily Reader.

Scans data/ subdirectories for config.yaml files defining reading sections
(e.g. "ml", "papers", "books") with per-section cadence settings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from documents import Document, load_document

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Section:
    """A reading section (e.g. 'ml', 'papers') with its config and documents."""

    name: str
    path: Path
    pages_per_day: int = 10
    template: str = "page"  # template name (without .html) in renderer/templates/
    documents: list[Document] = field(default_factory=list)


def load_sections(data_dir: Path = DATA_DIR) -> list[Section]:
    """Scan data/ for subdirectories with config.yaml, return configured sections."""
    sections = []

    for subdir in sorted(data_dir.iterdir()):
        if not subdir.is_dir():
            continue

        config_file = subdir / "config.yaml"
        if not config_file.exists():
            logger.debug(f"Skipping {subdir.name}: no config.yaml")
            continue

        # Load config
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        pages_per_day = config.get("pages_per_day", 10)
        template = config.get("template", "page")

        # Discover documents in this section
        doc_exts = {".pdf", ".md", ".txt"}
        doc_files = sorted(
            p for p in subdir.iterdir()
            if p.is_file() and p.suffix.lower() in doc_exts
        )

        documents = []
        for doc_path in doc_files:
            try:
                documents.append(load_document(doc_path))
            except ValueError as e:
                logger.warning(f"Skipping {doc_path}: {e}")

        if not documents:
            logger.info(f"Section '{subdir.name}': no documents found, skipping")
            continue

        section = Section(
            name=subdir.name,
            path=subdir,
            pages_per_day=pages_per_day,
            template=template,
            documents=documents,
        )
        sections.append(section)
        logger.info(
            f"Section '{section.name}': {len(documents)} docs, "
            f"{pages_per_day} pages/day"
        )

    return sections
