"""
RSS Feed Generator — converts documents in data/ to a styled HTML RSS feed.

Usage:
    uv run python generate_feed.py [--pages-per-run N] [--output feed.xml] [--send-email]

State is tracked in published.csv (append-only) so each run picks up where it left off.
PDF files are converted via Marker with our custom DailyReaderRenderer.
HTML pages are written to site/ for GitHub Pages hosting.
"""

import argparse
import csv
import datetime
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

import markdown
import rfeed
from dotenv import load_dotenv

from marker_converter import MarkerConverter
from renderer import render_page_html, render_today_page, _estimate_reading_time

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
SITE_DIR = Path(__file__).parent / "site"
STATE_FILE = Path(__file__).parent / "published.csv"
FEED_FILE = Path(__file__).parent / "feed.xml"
PAGES_PER_RUN = 10  # 10 pages/day across all active books

FEED_TITLE = "Daily Reader"
FEED_LINK = "https://mkeoliya.github.io/daily-reader/"
FEED_DESC = "A page a day from my reading list."

# Email config
EMAIL_TO = "keoliyamayank@gmail.com"
EMAIL_FROM = "keoliyamayank@gmail.com"

# Markdown extensions for non-PDF fallback
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "def_list",
    "footnotes",
    "md_in_html",
]

# Lazy-init: converter is created on first use to avoid model loading overhead
_converter: Optional[MarkerConverter] = None

logger = logging.getLogger(__name__)


def get_converter() -> MarkerConverter:
    """Lazy singleton for the MarkerConverter (models are heavy)."""
    global _converter
    if _converter is None:
        logger.info("Initializing Marker models...")
        _converter = MarkerConverter()
    return _converter


def get_email_sender():
    """Lazy-init email sender (only when --send-email is used)."""
    from redmail import EmailSender

    return EmailSender(
        host="smtp.gmail.com",
        port=587,
        username=EMAIL_FROM,
        password=os.environ["GMAIL_APP_PASSWORD"],
    )


# ---------------------------------------------------------------------------
# State (append-only CSV: file, page, total_pages, guid, pubdate)
# ---------------------------------------------------------------------------

CSV_FIELDS = ["file", "page", "total_pages", "guid", "pubdate", "title"]


def load_published() -> list[dict]:
    """Load all previously published items from CSV."""
    if not STATE_FILE.exists():
        return []
    with open(STATE_FILE, newline="") as f:
        return list(csv.DictReader(f))


def append_published(items: list[dict]):
    """Append new items to the CSV state file."""
    write_header = not STATE_FILE.exists()
    with open(STATE_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        for item in items:
            writer.writerow({
                "file": item["source_file"],
                "page": item["page_num"],
                "total_pages": item["total_pages"],
                "guid": item["guid"],
                "pubdate": item["pubDate"],
                "title": item["title"],
            })


def get_current_position(published: list[dict]) -> tuple[int, int]:
    """Determine which file/page to resume from based on published history."""
    if not published:
        return 0, 0

    files = get_document_files()
    file_names = [f.name for f in files]

    last = published[-1]
    last_file = last["file"]
    last_page = int(last["page"])
    last_total = int(last["total_pages"])

    if last_file not in file_names:
        return 0, 0

    file_idx = file_names.index(last_file)

    if last_page >= last_total:
        # Finished this file, move to next
        return file_idx + 1, 0
    else:
        return file_idx, last_page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_document_files() -> list[Path]:
    """Return sorted list of documents in the data directory."""
    exts = {".md", ".txt", ".pdf"}
    files = sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in exts)
    return files


def split_text_into_pages(text: str, lines_per_page: int = 40) -> list[str]:
    """Split a text/markdown document into pages. Fallback for non-PDF files."""
    lines = text.splitlines(keepends=True)
    pages = []
    for i in range(0, len(lines), lines_per_page):
        page = "".join(lines[i : i + lines_per_page])
        if page.strip():
            pages.append(page)
    return pages


def md_to_styled_html(md_text: str) -> str:
    """Convert markdown text to styled HTML. Fallback for non-PDF files."""
    html_body = markdown.markdown(md_text, extensions=MD_EXTENSIONS)
    return html_body


def make_guid(filepath: str, page_num: int) -> str:
    """Create a deterministic GUID for a page."""
    raw = f"{filepath}:page:{page_num}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def write_page_html(item: dict, site_dir: Path):
    """Write a styled HTML page to the site directory."""
    page_dir = site_dir / "pages"
    page_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{item['guid']}.html"
    filepath = page_dir / filename
    filepath.write_text(item["html_full"])

    # Save images if present
    if item.get("images"):
        for img_name, img_data in item["images"].items():
            img_path = page_dir / img_name
            if hasattr(img_data, "save"):
                # PIL Image
                img_data.save(str(img_path))
            elif isinstance(img_data, bytes):
                img_path.write_bytes(img_data)

    return f"{FEED_LINK}pages/{filename}"


def write_today_page(items: list[dict], site_dir: Path):
    """Write the 'Today's Reading' index page."""
    site_dir.mkdir(parents=True, exist_ok=True)

    today_items = []
    for item in items:
        today_items.append({
            "title": item["title"],
            "subtitle": f"~{_estimate_reading_time(item.get('description', ''))} min read",
            "url": item.get("page_url", "#"),
        })

    html = render_today_page(today_items)
    (site_dir / "index.html").write_text(html)


# ---------------------------------------------------------------------------
# Email (teaser + link)
# ---------------------------------------------------------------------------


def send_email(items: list[dict]):
    """Send a teaser email with links to the full pages on GitHub Pages."""
    # Build teaser list
    links_html = ""
    for item in items:
        url = item.get("page_url", FEED_LINK)
        links_html += f'<li><a href="{url}">{item["title"]}</a></li>\n'

    today = datetime.date.today().strftime("%B %d, %Y")
    html_body = f"""\
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; color: #333; }}
  h1 {{ font-size: 1.3em; }}
  ul {{ padding-left: 1.2em; }}
  li {{ margin-bottom: 0.5em; }}
  a {{ color: #2d5a8e; }}
  .footer {{ font-size: 0.8em; color: #999; margin-top: 2em; border-top: 1px solid #eee; padding-top: 1em; }}
</style>
</head>
<body>
  <h1>📖 {FEED_TITLE}</h1>
  <p>{len(items)} new page(s) — {today}</p>
  <ul>
    {links_html}
  </ul>
  <p><a href="{FEED_LINK}">Read on Daily Reader →</a></p>
  <p class="footer">Sent by Daily Reader</p>
</body>
</html>"""

    gmail = get_email_sender()
    gmail.send(
        subject=f"📖 {FEED_TITLE} — {items[0]['title']}",
        receivers=[EMAIL_TO],
        html=html_body,
    )
    print(f"  ✉ Email sent to {EMAIL_TO}")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def convert_pdf_pages(filepath: Path, start_page: int, count: int) -> list[dict]:
    """Convert specific pages from a PDF using Marker.

    Returns a list of dicts with html_full, description (snippet), images, etc.
    Marker converts the full PDF, then we extract the requested page range
    from the paginated <div class='page' data-page-id='N'> blocks.
    """
    import re
    from bs4 import BeautifulSoup

    converter = get_converter()
    result = converter.convert(str(filepath))

    total_pages = len(result.metadata.get("page_stats", []))

    # Extract the body content (between <main> tags)
    soup = BeautifulSoup(result.html, "html.parser")
    main_tag = soup.find("main")
    if not main_tag:
        logger.warning("No <main> tag found in rendered HTML")
        return []

    # Find all page divs
    page_divs = main_tag.find_all("div", class_="page")

    if not page_divs:
        # Fallback: if no page divs, treat the whole body as one page
        page_divs = [main_tag]
        total_pages = 1

    pages_to_take = min(count, len(page_divs) - start_page)
    if pages_to_take <= 0:
        return []

    items = []
    for i in range(pages_to_take):
        page_idx = start_page + i
        page_num = page_idx + 1  # 1-indexed
        progress_pct = (page_num / total_pages) * 100

        # Get the HTML content for this specific page
        page_body = str(page_divs[page_idx])

        # Create a standalone styled HTML page for this page
        page_html = render_page_html(
            body_html=page_body,
            title=filepath.stem,
            page_info=f"Page {page_num} of {total_pages}",
            progress_pct=progress_pct,
            is_last_page=(page_num == total_pages),
        )

        guid = make_guid(str(filepath), page_num)

        # Text snippet for RSS description / email teaser
        page_text = page_divs[page_idx].get_text(separator=" ", strip=True)[:300]

        items.append({
            "title": f"{filepath.stem} — Page {page_num}/{total_pages}",
            "description": page_text + "..." if len(page_text) >= 300 else page_text,
            "html_full": page_html,
            "images": result.images if i == 0 else {},  # images saved with first page
            "guid": guid,
            "pubDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_file": filepath.name,
            "page_num": page_num,
            "total_pages": total_pages,
        })

    return items


def convert_text_pages(filepath: Path, start_page: int, count: int) -> list[dict]:
    """Convert pages from a markdown/text file. Fallback for non-PDF files."""
    text = filepath.read_text()
    pages = split_text_into_pages(text)
    total_pages = len(pages)

    pages_to_take = min(count, total_pages - start_page)
    items = []

    for i in range(pages_to_take):
        page_idx = start_page + i
        page_num = page_idx + 1
        page_content = pages[page_idx]
        html_body = md_to_styled_html(page_content)
        progress_pct = (page_num / total_pages) * 100

        page_html = render_page_html(
            body_html=html_body,
            title=filepath.stem,
            page_info=f"Page {page_num} of {total_pages}",
            progress_pct=progress_pct,
            is_last_page=(page_num == total_pages),
        )

        guid = make_guid(str(filepath), page_num)
        items.append({
            "title": f"{filepath.stem} — Page {page_num}/{total_pages}",
            "description": html_body,
            "html_full": page_html,
            "images": {},
            "guid": guid,
            "pubDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_file": filepath.name,
            "page_num": page_num,
            "total_pages": total_pages,
        })

    return items


def generate_new_items(pages_per_run: int) -> list[dict]:
    """Generate the next batch of feed items."""
    files = get_document_files()
    if not files:
        print("No documents found in data/")
        return []

    published = load_published()
    file_idx, page_idx = get_current_position(published)

    new_items = []
    remaining = pages_per_run

    while remaining > 0:
        if file_idx >= len(files):
            print("All documents have been fully published!")
            break

        filepath = files[file_idx]

        if filepath.suffix.lower() == ".pdf":
            items = convert_pdf_pages(filepath, page_idx, remaining)
        else:
            items = convert_text_pages(filepath, page_idx, remaining)

        if not items:
            file_idx += 1
            page_idx = 0
            continue

        new_items.extend(items)
        page_idx += len(items)
        remaining -= len(items)

        # Check if we finished this file
        if items and items[-1]["page_num"] >= items[-1]["total_pages"]:
            file_idx += 1
            page_idx = 0

    return new_items


def build_feed(published: list[dict], new_items: list[dict]) -> str:
    """Build the full RSS feed XML from all published + new items."""
    feed_items = []

    # Rebuild from CSV history (lightweight — just title/guid/date)
    for row in published:
        pub = datetime.datetime.fromisoformat(row["pubdate"])
        feed_items.append(
            rfeed.Item(
                title=row["title"],
                guid=rfeed.Guid(row["guid"]),
                pubDate=pub,
            )
        )

    # Add new items with links to GitHub Pages
    for item_data in new_items:
        pub = datetime.datetime.fromisoformat(item_data["pubDate"])
        page_url = item_data.get("page_url", "")
        feed_items.append(
            rfeed.Item(
                title=item_data["title"],
                description=item_data["description"],
                link=page_url,
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
        help="Number of pages to publish per run (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=FEED_FILE,
        help="Output RSS feed file path",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send a teaser email with links to the new pages",
    )
    args = parser.parse_args()

    # Ensure site directory exists
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate new items
    published = load_published()
    new_items = generate_new_items(args.pages_per_run)

    if new_items:
        for item in new_items:
            # Write each page as a standalone HTML file
            page_url = write_page_html(item, SITE_DIR)
            item["page_url"] = page_url
            print(f"  + {item['title']} → {page_url}")

        # Write today's reading index
        write_today_page(new_items, SITE_DIR)
        print(f"  📄 Today's reading: {SITE_DIR / 'index.html'}")

        # Send email if requested
        if args.send_email:
            send_email(new_items)

        # Append to CSV state
        append_published(new_items)

    # Build and write feed
    rss_xml = build_feed(published, new_items)
    args.output.write_text(rss_xml)
    print(f"\nFeed written to {args.output} ({len(published) + len(new_items)} total items)")


if __name__ == "__main__":
    main()
