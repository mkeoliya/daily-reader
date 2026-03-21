# Daily Reader

A mobile-first educational reading tool that converts PDF books and papers into a daily RSS feed with beautifully styled HTML pages. Built to replace doomscrolling with focused, finite reading sessions.

## What is this?

Daily Reader takes your PDF textbooks and research papers, converts them page-by-page into styled, mobile-responsive HTML, and serves them as:

- **A daily email** with a teaser and link to the full content
- **An RSS feed** you can subscribe to in any feed reader
- **A static website** hosted on [GitHub Pages](https://mkeoliya.github.io/daily-reader/)

## Features

- **📱 Mobile-first design** — clean serif typography, responsive layout, designed for phone reading
- **🌙 Dark mode** — automatic via `prefers-color-scheme`, OLED-friendly
- **📐 LaTeX math** — rendered beautifully via KaTeX
- **📊 Progress tracking** — "Page 37 of 412 · Deep Learning" with a progress bar
- **⏱️ Reading time** — estimated reading time per page
- **✅ Daily dose** — finite reading sessions (10 pages/day), with a "Done for today" screen
- **📚 Bookshelf** — minimalist list of all active reads with progress rings
- **📖 Multi-book** — read multiple books simultaneously, pages distributed across active reads

## Architecture

```
PDF → Marker (PdfConverter) → DailyReaderRenderer → Styled HTML → GitHub Pages
                                                  → RSS Feed (feed.xml)
                                                  → Email (teaser + link)
```

### Key files

| File | Purpose |
|------|---------|
| `renderer.py` | Custom Marker renderer — mobile-first HTML with KaTeX, dark mode, progress bar |
| `marker_converter.py` | Thin wrapper around Marker's Python API |
| `generate_feed.py` | Orchestrator — converts pages, builds RSS feed, sends email, writes site |
| `data/` | Source PDFs (books, papers) |
| `site/` | Generated HTML output (deployed to GitHub Pages) |

## Usage

```bash
# Generate today's pages (10 pages across all active books)
uv run python generate_feed.py --pages-per-run 10

# Generate and send email
uv run python generate_feed.py --pages-per-run 10 --send-email

# Preview a specific PDF
uv run python marker_converter.py data/my-book.pdf
```

## Setup

```bash
# Install dependencies
uv sync

# Set up email (optional)
echo 'GMAIL_APP_PASSWORD=your-app-password' > .env
```

## Future Roadmap

- Progress bar
- Bookshelf view (for current reads, i.e. current `Document` objects)
- 🔁 Spaced repetition prompts (revisit key concepts from past readings)
- 🤖 "Explain this" (send a passage to an LLM for simplified explanation)
- 📄 ePUB / HTML source support (via Document/Page abstractions)
