# Daily Reader

A mobile-first educational reading tool that converts PDF books and papers into a daily styled HTML reading session. Built to replace doomscrolling with focused, finite reading.

## What is this?

Daily Reader takes your PDF textbooks, converts them page-by-page into styled, mobile-responsive HTML, and delivers them as:

- **A daily email** with a teaser and link to the full content
- **A static website** hosted on [GitHub Pages](https://mkeoliya.github.io/daily-reader/)

## Features

| Feature | Where it's implemented |
|---------|----------------------|
| 📱 Mobile-first typography (Source Serif 4, Inter) | [`renderer/static/daily-reader.css`](renderer/static/daily-reader.css) |
| 🌙 Automatic dark mode (`prefers-color-scheme`) | [`daily-reader.css` :root vars](renderer/static/daily-reader.css#L14-L24) |
| 📐 LaTeX math via KaTeX | [`documents.py: _convert_math_tags()`](documents.py) + [`ml.html`](renderer/templates/ml.html) |
| 📊 Sticky progress bar (bottom of viewport) | [`daily-reader.css: .dr-progress-bar`](renderer/static/daily-reader.css#L72-L86) + [`page.html`](renderer/templates/page.html) |
| ⏱️ Reading time estimate | [`engine.py: _estimate_reading_time()`](renderer/engine.py) |
| ✅ "Done for today" end marker | [`page.html: .dr-done`](renderer/templates/page.html) |
| 📚 Bookshelf with SVG progress rings | [`engine.py: render_bookshelf()`](renderer/engine.py) + [`bookshelf.html`](renderer/templates/bookshelf.html) |
| 📖 Section-based reading cadence | [`sections.py`](sections.py) + [`data/*/config.yaml`](data/ml/config.yaml) |
| 📄 Document abstraction (PDF, Markdown) | [`documents.py`](documents.py) — `PdfDocument`, `MarkdownDocument` |
| 🔖 YAML bookmark state | [`state.yaml`](state.yaml) — simple `{file: page_number}` |
| ✉️ Daily teaser email | [`mailer.py`](mailer.py) |

## Architecture

```
data/ml/                      ← Section with config.yaml (pages_per_day: 20)
  ├── config.yaml
  ├── Deep Learning.pdf       ← Source documents
  └── Differentiable.pdf

documents.py                  ← Document/Page abstraction
  ├── PdfDocument             ← Uses Marker ML pipeline
  └── MarkdownDocument        ← Uses python-markdown

renderer/                     ← Jinja2 templating + CSS (format-agnostic)
  ├── engine.py               ← render_page_html(), render_bookshelf()
  ├── templates/{base,page,ml,today,bookshelf}.html
  └── static/daily-reader.css

sections.py                   ← Section discovery from data/ subdirs
mailer.py                     ← Email via Red Mail + Gmail SMTP
generate_feed.py              ← Orchestrator (~180 lines)
state.yaml                    ← Bookmark: {file_path: current_page}
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
2. Add a `config.yaml`:
   ```yaml
   pages_per_day: 5
   template: page    # or create a custom template in renderer/templates/
   ```
3. Drop PDFs or `.md` files into the directory
4. Run `uv run python generate_feed.py`

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
