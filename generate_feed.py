"""
generate_feed.py — Daily Reader orchestrator.

Reads section configs, converts document pages, writes a single combined
HTML page to site/, and optionally sends a teaser email.

Usage:
    uv run python generate_feed.py [--send-email]
"""

import argparse
import datetime
import logging
from pathlib import Path

import yaml

from documents import Document
from renderer import render_daily_page, _estimate_reading_time
from sections import load_sections

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SITE_DIR = Path(__file__).parent  # output to repo root for GitHub Pages
STATE_FILE = Path(__file__).parent / "state.yaml"

FEED_TITLE = "Daily Reader"
FEED_LINK = "https://mkeoliya.github.io/daily-reader/"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State (YAML bookmark: file path → current page number)
# ---------------------------------------------------------------------------


def load_state() -> dict[str, int]:
    """Load bookmark state: {relative_path: current_page}."""
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return yaml.safe_load(f) or {}


def save_state(state: dict[str, int]):
    """Write bookmark state back to YAML."""
    with open(STATE_FILE, "w") as f:
        yaml.dump(state, f, default_flow_style=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def relative_path(doc: Document, data_dir: Path) -> str:
    """Get a stable relative path key for state tracking."""
    return str(doc.source_path.relative_to(data_dir))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def generate(send_email: bool = False):
    """Generate today's reading pages across all sections."""
    sections = load_sections()
    if not sections:
        print("No sections found in data/. Add a config.yaml to a subdirectory.")
        return

    state = load_state()
    data_dir = Path(__file__).parent / "data"
    today = datetime.date.today()

    # Collect all section content
    page_sections = []  # list of dicts for the template
    all_images = {}

    for section in sections:
        remaining = section.pages_per_day
        section_docs = []

        for doc in section.documents:
            if remaining <= 0:
                break

            key = relative_path(doc, data_dir)
            current_page = state.get(key, 0)

            if current_page >= doc.total_pages:
                continue  # finished this document

            pages = doc.get_pages(current_page, remaining)
            if not pages:
                continue

            # Bundle all pages for this doc
            first_page = pages[0].page_number
            last_page = pages[-1].page_number
            combined_body = "\n".join(p.html for p in pages)

            section_docs.append({
                "title": doc.title,
                "page_info": f"Pages {first_page}–{last_page} of {doc.total_pages}",
                "body_html": combined_body,
            })

            # Collect images
            for p in pages:
                all_images.update(p.images)

            # Update state
            state[key] = last_page
            remaining -= len(pages)
            print(f"  [{section.name}] {doc.title} — Pages {first_page}–{last_page}/{doc.total_pages}")

        if section_docs:
            page_sections.append({
                "section_name": section.name,
                "documents": section_docs,
            })

    if not page_sections:
        print("All documents fully read!")
        return

    # Render combined page
    page_html = render_daily_page(
        sections=page_sections,
        title=FEED_TITLE,
        today_date=today.strftime("%B %d, %Y"),
    )

    # Write to pages/{date}/index.html
    page_dir = SITE_DIR / "pages" / today.isoformat()
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "index.html").write_text(page_html)

    # Write images
    for img_name, img_data in all_images.items():
        img_path = page_dir / img_name
        if hasattr(img_data, "save"):
            img_data.save(str(img_path))
        elif isinstance(img_data, bytes):
            img_path.write_bytes(img_data)

    page_url = f"{FEED_LINK}pages/{today.isoformat()}/"

    # Write root index.html as redirect to today's page
    redirect_html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={page_url}"></head></html>'
    (SITE_DIR / "index.html").write_text(redirect_html)

    # Save state
    save_state(state)
    print(f"\nState saved to {STATE_FILE}")

    # Send email
    if send_email:
        from mailer import send_email as _send_email
        # Pass first section's content for the email body
        first_section = page_sections[0]
        _send_email(
            section_name=first_section["section_name"],
            documents=first_section["documents"],
            page_url=page_url,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Daily Reader — generate today's pages")
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send a teaser email with links to the new pages",
    )
    args = parser.parse_args()

    generate(send_email=args.send_email)


if __name__ == "__main__":
    main()
