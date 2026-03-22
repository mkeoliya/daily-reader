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

from renderer import render_daily_page, render_section, _estimate_reading_time
from sections import load_sections, save_sections

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SITE_DIR = Path(__file__).parent  # output to repo root for GitHub Pages

FEED_TITLE = "Daily Reader"
FEED_LINK = "https://mkeoliya.github.io/daily-reader/"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def generate(send_email: bool = False):
    """Generate today's reading pages across all sections."""
    sections = load_sections()
    if not sections:
        print("No sections found in data/. Add a config.yaml to a subdirectory.")
        return

    today = datetime.date.today()

    # Collect all section content
    page_sections = []  # list of dicts for the template
    all_images = {}
    pdf_renders = []  # (doc, first_page_0idx, count, stem) for WebP rendering

    for section in sections:
        remaining = section.pages_per_day
        section_docs = []

        for entry in section.queue:
            if remaining <= 0:
                break

            doc = entry.doc
            current_page = entry.current_page

            if current_page >= doc.total_pages:
                continue  # finished this document

            pages = doc.get_pages(current_page, remaining)
            if not pages:
                continue

            # Bundle all pages for this doc
            first_page = pages[0].page_number
            last_page = pages[-1].page_number
            combined_body = "\n".join(p.html for p in pages)

            # Track PDF pages for desktop viewer (rendered at build time)
            pdf_pages = []
            if doc.is_pdf:
                stem = doc.title.lower().replace(' ', '-')
                pdf_pages = [f"{stem}-p{first_page + i}.webp" for i in range(len(pages))]
                pdf_renders.append((doc, current_page, len(pages), stem))
            elif doc.pdf_url:
                # ArXiv: download and render at build time (TODO)
                pass

            section_docs.append({
                "title": doc.title,
                "page_info": f"Pages {first_page}–{last_page} of {doc.total_pages}",
                "body_html": combined_body,
                "pdf_pages": pdf_pages,
            })

            # Collect images
            for p in pages:
                all_images.update(p.images)

            # Update bookmark in the queue entry
            entry.current_page = last_page
            remaining -= len(pages)
            print(f"  [{section.name}] {doc.title} — Pages {first_page}–{last_page}/{doc.total_pages}")

        # Move finished docs to the finished list
        still_queued = []
        for entry in section.queue:
            if entry.current_page >= entry.doc.total_pages:
                section.finished.append(entry.doc.source_path.name)
                print(f"  [{section.name}] ✓ Finished: {entry.doc.title}")
            else:
                still_queued.append(entry)
        section.queue = still_queued

        if section_docs:
            page_sections.append({
                "section_name": section.name,
                "documents": section_docs,
            })

    if not page_sections:
        print("All documents fully read!")
        return

    # Sort sections: books first, then the rest
    page_sections.sort(key=lambda s: s['section_name'] != 'books')

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

    # Write section fragments for progressive loading (sections 2+)
    from renderer.engine import _slugify
    for i, s in enumerate(page_sections[1:], start=1):
        s["slug"] = _slugify(s["section_name"])
        next_s = page_sections[i + 1] if i + 1 < len(page_sections) else None
        if next_s:
            next_s["slug"] = _slugify(next_s["section_name"])
        frag = render_section(s, next_s)
        (page_dir / f"section-{s['slug']}.html").write_text(frag)

    # Write images
    for img_name, img_data in all_images.items():
        img_path = page_dir / img_name
        if hasattr(img_data, "save"):
            img_data.save(str(img_path))
        elif isinstance(img_data, bytes):
            img_path.write_bytes(img_data)

    # Render PDF pages to WebP images for desktop viewer
    import pypdfium2 as pdfium
    from PIL import Image as PILImage
    RENDER_SCALE = 2.5
    WEBP_QUALITY = 95
    for doc, start_page, count, stem in pdf_renders:
        pdf_path = doc.split_pages(start_page, count, page_dir / f"{stem}.pdf")
        pdf_doc = pdfium.PdfDocument(str(pdf_path))
        for i in range(len(pdf_doc)):
            page = pdf_doc[i]
            bmp = page.render(scale=RENDER_SCALE)
            img = bmp.to_pil()
            img.save(str(page_dir / f"{stem}-p{start_page + i}.webp"), 'webp', quality=WEBP_QUALITY)
        pdf_doc.close()
        pdf_path.unlink()  # remove the split PDF, images are enough

    page_url = f"{FEED_LINK}pages/{today.isoformat()}/"

    # Write root index.html as redirect to today's page
    redirect_html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={page_url}"></head></html>'
    (SITE_DIR / "index.html").write_text(redirect_html)

    # Save state back to config files
    save_sections(sections)
    print(f"\nState saved to section configs")

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
