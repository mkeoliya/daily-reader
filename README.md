# Daily Reader

A mobile-first educational reading tool that converts PDF books, markdown files, and arXiv papers into a daily styled HTML reading session. Built to replace doomscrolling with focused, finite reading.

## What is this?

Daily Reader takes your PDF textbooks, markdown files, and arXiv papers, converts them into styled, mobile-responsive HTML, and delivers them as:

- **Progressive daily pages** — sections load one at a time (books first, then the rest), keeping the DOM small and scrolling smooth
- **A daily email** with the first section's content and a link to the full page
- **A static website** hosted on [GitHub Pages](https://mkeoliya.github.io/daily-reader/)

## Features

| Feature | Where it's implemented |
|---------|----------------------|
| 📱 Mobile-first typography (Source Serif 4, Inter) | [`daily-reader.css`](renderer/static/daily-reader.css) |
| ☀️ Light theme | [`daily-reader.css` :root vars](renderer/static/daily-reader.css) |
| 📐 LaTeX math via KaTeX (always enabled) | [`documents.py: _convert_math_tags()`](documents.py) + [`base.html`](renderer/templates/base.html) |
| 📊 CSS-only scroll progress bar | [`daily-reader.css: @keyframes dr-progress-grow`](renderer/static/daily-reader.css) |
| ⏱️ Reading time estimate | [`engine.py: _estimate_reading_time()`](renderer/engine.py) |
| ✅ "Done for today" end marker | [`page.html: .dr-done`](renderer/templates/page.html) |
| 📖 Progressive section loading (books first) | [`daily-reader.js`](renderer/static/daily-reader.js) + [`section.html`](renderer/templates/section.html) |
| 🎨 Per-section CSS theming | [`renderer/static/sections/*.css`](renderer/static/sections/) |
| 📄 Lazy PDF viewer (Ctrl+Shift+P) | [`daily-reader.js`](renderer/static/daily-reader.js) + [`laptop.css`](renderer/static/laptop.css) |
| 📖 Section-based reading cadence | [`sections.py`](sections.py) + [`data/*/config.yaml`](data/ml/config.yaml) |
| 📄 Document abstraction (PDF, Markdown, arXiv) | [`documents.py`](documents.py) — `PdfDocument`, `MarkdownDocument`, `ArxivDocument` |
| 🔖 Queue-based config with bookmarks | [`config.yaml`](data/ml/config.yaml) — queue + start/page per doc |
| ✉️ Daily teaser email | [`mailer.py`](mailer.py) |

## Architecture

```
data/
  ├── ml/                         ← Section: ML textbooks
  │   ├── config.yaml             ← queue, pages_per_day, bookmarks
  │   ├── Deep Learning.pdf
  │   └── Differentiable.pdf
  ├── arxiv/                      ← Section: arXiv papers
  │   ├── config.yaml
  │   └── attention-is-all-you-need.arxiv
  └── books/                      ← Section: general reading
      ├── config.yaml
      └── a.md

documents.py                      ← Document/Page abstraction
  ├── PdfDocument                 ← Uses Marker ML pipeline
  ├── MarkdownDocument            ← Uses python-markdown
  └── ArxivDocument               ← Fetches HTML from ar5iv

renderer/                         ← Jinja2 templating + CSS
  ├── engine.py                   ← render_daily_page(), render_section()
  ├── templates/
  │   ├── base.html               ← Fonts, KaTeX, scripts, progress bar
  │   ├── page.html               ← First section (books) daily page
  │   └── section.html            ← Lazy-loaded section fragment
  └── static/
      ├── daily-reader.css        ← Core styles
      ├── daily-reader.js         ← Section loading + PDF viewer
      ├── laptop.css              ← PDF viewer styles
      └── sections/               ← Per-section CSS overrides

sections.py                       ← Section config + queue management
mailer.py                         ← Email via Red Mail + Gmail SMTP
generate_feed.py                  ← Orchestrator
```

## Usage

```bash
# Generate today's pages (cadence set per section in config.yaml)
uv run python generate_feed.py

# Generate and send email
uv run python generate_feed.py --send-email
```

## Adding a Section

1. Create a subdirectory under `data/`, e.g. `data/papers/`
2. Drop PDFs, `.md` files, or `.arxiv` files into the directory
3. Add a `config.yaml` with a reading queue:
   ```yaml
   pages_per_day: 5

   queue:
   - {file: My Paper.pdf, start: 3}
   - {file: notes.md}
   ```
   For PDFs, set `start` to the first page of actual content (0-indexed) to skip
   title pages, copyright, and table of contents. The script auto-updates a `page`
   bookmark after each run and moves finished documents to a `finished:` list.
4. Optionally add section styling at `renderer/static/sections/papers.css`
5. Run `uv run python generate_feed.py`

### Adding an arXiv paper

Create a `.arxiv` file containing just the arXiv ID:
```
1706.03762
```
The HTML is fetched from [ar5iv](https://ar5iv.labs.arxiv.org/) and embedded as-is (one paper = one page). Fetched HTML is cached locally in `.cache/` to avoid re-downloading.

## Setup

```bash
# Install dependencies
uv sync

# Set up email (optional)
echo 'GMAIL_APP_PASSWORD=your-app-password' > .env
```

## Future Roadmap

- 🔁 Spaced repetition prompts (revisit key concepts from past readings)
- 🀄 Chinese character learning (card-based layout)
- 📖 ePUB source support
