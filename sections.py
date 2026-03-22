"""
sections.py — Section discovery and configuration for Daily Reader.

Scans data/ subdirectories for config.yaml files defining reading sections
(e.g. "ml", "papers", "books") with per-section queue and reading state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from documents import Document, load_document

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# FlowDict — compact YAML serialization for queue entries
# ---------------------------------------------------------------------------


class FlowDict(dict):
    """Dict subclass that serializes as a YAML flow mapping: {key: val, ...}"""
    pass


def _flow_dict_representer(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


yaml.add_representer(FlowDict, _flow_dict_representer)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DocumentQueue:
    """A document in a section's reading queue with bookmark state."""

    doc: Document
    start_page: int = 0       # 0-indexed page to start from (skip TOC/intro)
    current_page: int = -1    # 0-indexed bookmark (-1 = not started, use start_page)

    def __post_init__(self):
        if self.current_page < 0:
            self.current_page = self.start_page


@dataclass
class Section:
    """A reading section (e.g. 'ml', 'papers') with its config and document queue."""

    name: str
    path: Path
    pages_per_day: int = 10
    template: str = "page"
    queue: list[DocumentQueue] = field(default_factory=list)
    finished: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------


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

        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        pages_per_day = config.get("pages_per_day", 10)
        template = config.get("template", "page")

        # Parse document queue
        queue = []
        for entry in config.get("queue", []):
            filename = entry.get("file", "") if isinstance(entry, dict) else str(entry)
            doc_path = subdir / filename
            if not doc_path.exists():
                logger.warning(f"Queue entry '{filename}' not found in {subdir.name}, skipping")
                continue
            try:
                doc = load_document(doc_path)
            except ValueError as e:
                logger.warning(f"Skipping {doc_path}: {e}")
                continue

            start_page = entry.get("start", 0) if isinstance(entry, dict) else 0
            current_page = entry.get("page", -1) if isinstance(entry, dict) else -1

            queue.append(DocumentQueue(doc=doc, start_page=start_page, current_page=current_page))

        finished = config.get("finished", []) or []

        if not queue:
            logger.info(f"Section '{subdir.name}': empty queue, skipping")
            continue

        section = Section(
            name=subdir.name, path=subdir,
            pages_per_day=pages_per_day, template=template,
            queue=queue, finished=finished,
        )
        sections.append(section)
        logger.info(f"Section '{section.name}': {len(queue)} queued, {pages_per_day} pages/day")

    return sections


def save_sections(sections: list[Section]):
    """Write updated state (current_page, finished) back to each section's config.yaml."""
    for section in sections:
        config: dict = {"pages_per_day": section.pages_per_day}
        if section.template != "page":
            config["template"] = section.template

        # Queue entries as compact flow dicts
        queue_list = []
        for entry in section.queue:
            item: dict = {"file": entry.doc.source_path.name}
            if entry.start_page > 0:
                item["start"] = entry.start_page
            if entry.current_page != entry.start_page:
                item["page"] = entry.current_page
            queue_list.append(FlowDict(item))
        if queue_list:
            config["queue"] = queue_list

        if section.finished:
            config["finished"] = section.finished

        with open(section.path / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved config for section '{section.name}'")
