# Daily Reader

A mobile-first educational reading tool that converts PDF books and papers into a daily styled HTML reading session. Built to replace doomscrolling with focused, finite reading.

## What is this?

Daily Reader takes your PDF textbooks and markdown files, converts them page-by-page into styled, mobile-responsive HTML, and delivers them as:

- **A single daily page** combining all sections with skip-to-section navigation
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
| 📚 Multi-section combined page with skip-to nav | [`page.html`](renderer/templates/page.html) + [`engine.py: render_daily_page()`](renderer/engine.py) |
| 🎨 Per-section CSS theming | [`renderer/static/sections/*.css`](renderer/static/sections/) |
| 📚 Bookshelf with SVG progress rings | [`engine.py: render_bookshelf()`](renderer/engine.py) + [`bookshelf.html`](renderer/templates/bookshelf.html) |
| 📖 Section-based reading cadence | [`sections.py`](sections.py) + [`data/*/config.yaml`](data/ml/config.yaml) |
| 📄 Document abstraction (PDF, Markdown) | [`documents.py`](documents.py) — `PdfDocument`, `MarkdownDocument` |
| 🔖 Queue-based config with bookmarks | [`config.yaml`](data/ml/config.yaml) — queue + start/page per doc |
| ✉️ Daily teaser email | [`mailer.py`](mailer.py) |

## Architecture

```
data/
  ├── ml/                         ← Section: ML textbooks
  │   ├── config.yaml             ← queue, pages_per_day, bookmarks
  │   ├── Deep Learning.pdf
  │   └── Differentiable.pdf
  └── books/                      ← Section: general reading
      ├── config.yaml
      └── a.md

documents.py                      ← Document/Page abstraction
  ├── PdfDocument                 ← Uses Marker ML pipeline
  └── MarkdownDocument            ← Uses python-markdown

renderer/                         ← Jinja2 templating + CSS
  ├── engine.py                   ← render_daily_page(), render_bookshelf()
  ├── templates/
  │   ├── base.html               ← Fonts, KaTeX, progress bar
  │   ├── page.html               ← Multi-section daily page
  │   └── bookshelf.html
  └── static/
      ├── daily-reader.css        ← Core styles
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
2. Drop PDFs or `.md` files into the directory
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

## Setup

```bash
# Install dependencies
uv sync

# Set up email (optional)
echo 'GMAIL_APP_PASSWORD=your-app-password' > .env
```

## Future Roadmap

- 🔁 Spaced repetition prompts (revisit key concepts from past readings)
- 📄 arXiv HTML support (embed via `<iframe>` from ar5iv)
- 🀄 Chinese character learning (card-based layout)
- 📖 ePUB source support
