"""
generate_feed.py — Daily Reader orchestrator.

Reads section configs, converts document pages, writes styled HTML to site/,
and optionally sends a teaser email.

Usage:
    uv run python generate_feed.py [--send-email]
"""

import argparse
import datetime
import hashlib
import logging
from pathlib import Path

import yaml

from documents import Document
from renderer import render_page_html, render_today_page, _estimate_reading_time
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


def make_guid(filepath: str, page_num: int) -> str:
    """Create a deterministic GUID for a page."""
    raw = f"{filepath}:page:{page_num}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def relative_path(doc: Document, data_dir: Path) -> str:
    """Get a stable relative path key for state tracking."""
    return str(doc.source_path.relative_to(data_dir))


def write_page_html(item: dict, site_dir: Path) -> str:
    """Write a styled HTML page and its images to a per-page directory."""
    today = datetime.date.today().isoformat()
    page_dir = site_dir / "pages" / today
    page_dir.mkdir(parents=True, exist_ok=True)

    filepath = page_dir / "index.html"
    filepath.write_text(item["html_full"])

    # Save images alongside the HTML
    if item.get("images"):
        for img_name, img_data in item["images"].items():
            img_path = page_dir / img_name
            if hasattr(img_data, "save"):
                img_data.save(str(img_path))
            elif isinstance(img_data, bytes):
                img_path.write_bytes(img_data)

    return f"{FEED_LINK}pages/{today}/"


def write_today_page(items: list[dict], site_dir: Path):
    """Write the 'Today's Reading' index page."""
    site_dir.mkdir(parents=True, exist_ok=True)

    today_items = []
    for item in items:
        today_items.append({
            "title": item["title"],
            "subtitle": f"~{_estimate_reading_time(item.get('snippet', ''))} min read",
            "url": item.get("page_url", "#"),
        })

    html = render_today_page(today_items)
    (site_dir / "index.html").write_text(html)


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
    all_items = []

    for section in sections:
        remaining = section.pages_per_day

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

            # Bundle all pages into one HTML
            first_page = pages[0].page_number
            last_page = pages[-1].page_number
            combined_body = "\n".join(p.html for p in pages)

            progress_pct = (last_page / doc.total_pages) * 100
            is_last = last_page >= doc.total_pages

            page_html = render_page_html(
                body_html=combined_body,
                title=doc.title,
                page_info=f"Pages {first_page}–{last_page} of {doc.total_pages}",
                progress_pct=progress_pct,
                is_last_page=is_last,
                template=section.template,
            )

            # Collect all images from pages
            all_images = {}
            for p in pages:
                all_images.update(p.images)

            # Snippet for email
            snippet = pages[0].html[:300]
            guid = make_guid(str(doc.source_path), last_page)

            item = {
                "title": f"{doc.title} — Pages {first_page}–{last_page}/{doc.total_pages}",
                "snippet": snippet,
                "html_full": page_html,
                "images": all_images,
                "guid": guid,
            }
            all_items.append(item)

            # Update state
            state[key] = last_page
            remaining -= len(pages)
            print(f"  [{section.name}] {item['title']}")

    if not all_items:
        print("All documents fully read!")
        return

    # Write HTML pages
    for item in all_items:
        page_url = write_page_html(item, SITE_DIR)
        item["page_url"] = page_url

    # Write today's index page
    write_today_page(all_items, SITE_DIR)

    # Save state
    save_state(state)
    print(f"\nState saved to {STATE_FILE}")

    # Send email
    if send_email:
        from mailer import send_email as _send_email
        _send_email(all_items)


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
