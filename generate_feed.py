"""
RSS Feed Generator — converts documents in data/ to a styled HTML RSS feed.

Usage:
    uv run python generate_feed.py [--pages-per-run N] [--output feed.xml]

State is tracked in state.json so each run picks up where it left off.
"""

import argparse
import json
import datetime
import hashlib
from pathlib import Path

import markdown
import rfeed

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = Path(__file__).parent / "state.json"
FEED_FILE = Path(__file__).parent / "feed.xml"
PAGES_PER_RUN = 1

FEED_TITLE = "Daily Reader"
FEED_LINK = "https://example.github.io/pdf-reader/"
FEED_DESC = "A page a day from my reading list."

# Markdown extensions for nice styled output
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "def_list",
    "footnotes",
    "md_in_html",
]

# Minimal CSS inlined into each article for readability in RSS readers
ARTICLE_CSS = """\
<style>
  body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; color: #222; max-width: 680px; margin: 0 auto; }
  h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }
  pre { background: #f5f5f5; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.9em; }
  code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }
  pre code { background: none; padding: 0; }
  blockquote { border-left: 3px solid #ccc; margin: 1em 0; padding: 0.5em 1em; color: #555; }
  table { border-collapse: collapse; margin: 1em 0; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #f5f5f5; }
  img { max-width: 100%; height: auto; }
</style>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load progress state from disk."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"current_file_index": 0, "current_page": 0, "items": []}


def save_state(state: dict):
    """Persist progress state."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_document_files() -> list[Path]:
    """Return sorted list of documents in the data directory."""
    exts = {".md", ".txt", ".pdf"}
    files = sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in exts)
    return files


def split_into_pages(text: str, lines_per_page: int = 40) -> list[str]:
    """Split a text document into pages of roughly `lines_per_page` lines."""
    lines = text.splitlines(keepends=True)
    pages = []
    for i in range(0, len(lines), lines_per_page):
        page = "".join(lines[i : i + lines_per_page])
        if page.strip():
            pages.append(page)
    return pages


def md_to_styled_html(md_text: str) -> str:
    """Convert markdown text to styled HTML."""
    html_body = markdown.markdown(md_text, extensions=MD_EXTENSIONS)
    return ARTICLE_CSS + html_body


def make_guid(filepath: str, page_num: int) -> str:
    """Create a deterministic GUID for a page."""
    raw = f"{filepath}:page:{page_num}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def generate_new_items(state: dict, pages_per_run: int) -> list[dict]:
    """Generate the next batch of feed items, updating state in-place."""
    files = get_document_files()
    if not files:
        print("No documents found in data/")
        return []

    new_items = []
    remaining = pages_per_run

    while remaining > 0:
        file_idx = state["current_file_index"]
        if file_idx >= len(files):
            print("All documents have been fully published!")
            break

        filepath = files[file_idx]
        text = filepath.read_text()
        pages = split_into_pages(text)
        page_idx = state["current_page"]

        if page_idx >= len(pages):
            # Move to next file
            state["current_file_index"] += 1
            state["current_page"] = 0
            continue

        # Grab as many pages as we need from this file
        pages_to_take = min(remaining, len(pages) - page_idx)
        for i in range(pages_to_take):
            p = page_idx + i
            page_content = pages[p]
            html = md_to_styled_html(page_content)
            guid = make_guid(str(filepath), p)

            item = {
                "title": f"{filepath.stem} — Page {p + 1}/{len(pages)}",
                "description": html,
                "guid": guid,
                "pubDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "source_file": str(filepath.name),
                "page_num": p + 1,
            }
            new_items.append(item)

        state["current_page"] = page_idx + pages_to_take
        remaining -= pages_to_take

    return new_items


def build_feed(all_items: list[dict]) -> str:
    """Build the full RSS feed XML from stored items."""
    feed_items = []
    for item_data in all_items:
        pub = datetime.datetime.fromisoformat(item_data["pubDate"])
        feed_items.append(
            rfeed.Item(
                title=item_data["title"],
                description=item_data["description"],
                guid=rfeed.Guid(item_data["guid"]),
                pubDate=pub,
            )
        )

    feed = rfeed.Feed(
        title=FEED_TITLE,
        link=FEED_LINK,
        description=FEED_DESC,
        language="en-US",
        lastBuildDate=datetime.datetime.now(datetime.timezone.utc),
        items=feed_items,
    )
    return feed.rss()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate RSS feed from documents")
    parser.add_argument(
        "--pages-per-run",
        type=int,
        default=PAGES_PER_RUN,
        help="Number of pages to publish per run (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=FEED_FILE,
        help="Output RSS feed file path",
    )
    args = parser.parse_args()

    # Load state
    state = load_state()

    # Generate new items
    new_items = generate_new_items(state, args.pages_per_run)
    if new_items:
        state["items"].extend(new_items)
        for item in new_items:
            print(f"  + {item['title']}")

    # Build and write feed
    rss_xml = build_feed(state["items"])
    args.output.write_text(rss_xml)
    print(f"\nFeed written to {args.output} ({len(state['items'])} total items)")

    # Save state
    save_state(state)


if __name__ == "__main__":
    main()
