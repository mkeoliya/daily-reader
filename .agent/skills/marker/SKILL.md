---
name: marker
description: How to convert PDFs to structured content using Marker (Python API and CLI)
---

# Marker — PDF to Markdown/HTML/JSON

Marker converts PDF documents to markdown, HTML, or JSON using deep learning models for layout detection, OCR, and text recognition. It runs locally and optionally uses LLMs for improved accuracy.

- **Package**: `marker-pdf` (installed in `.venv`)
- **Venv binary**: `/home/mkeoliya/projects/scratch/.venv/bin/marker_single`

## Python API (Preferred)

```python
from marker.converters.pdf import PdfConverter

# Basic usage with default HTML renderer
converter = PdfConverter(artifact_dict={})
result = converter("path/to/file.pdf")

# With custom renderer (our DailyReaderRenderer)
converter = PdfConverter(
    artifact_dict={},
    renderer="renderer:DailyReaderRenderer"
)
result = converter("path/to/file.pdf")
# result.html → styled HTML
# result.images → dict of extracted images
# result.metadata → table of contents, page stats
```

### Key API classes

| Class | Description |
|-------|-------------|
| `PdfConverter(artifact_dict, renderer, llm_service)` | Main converter. `renderer` is an import path string. |
| `Document` | Parsed document with `.pages`, `.get_page(id)`, `.render()`, `.table_of_contents` |
| `Page` | Single page with `.children` (blocks), `.page_id` |
| `BaseRenderer` | Base class for renderers. Handles image extraction, math merging, header/footer filtering. |
| `HTMLRenderer` | Renders to HTML. Our `DailyReaderRenderer` subclasses this. |
| `HTMLOutput` | Output with `.html`, `.images`, `.metadata` |

### Custom renderer pattern

Subclass `HTMLRenderer` and override `__call__`:

```python
from marker.renderers.html import HTMLRenderer, HTMLOutput

class MyRenderer(HTMLRenderer):
    keep_pageheader_in_output = False
    keep_pagefooter_in_output = False
    paginate_output = True  # wraps pages in <div class='page'>
    
    def __call__(self, document):
        document_output = document.render(self.block_config)
        full_html, images = self.extract_html(document, document_output)
        # ... custom post-processing ...
        return HTMLOutput(html=..., images=images, metadata=...)
```

## CLI Usage

```bash
# Basic conversion
marker_single input.pdf --output_dir ./output --output_format markdown

# Specific pages
marker_single input.pdf --output_dir ./output --page_range "0,5-10"

# With LLM enhancement
marker_single input.pdf --output_dir ./output --use_llm \
    --llm_service marker.services.gemini.GoogleGeminiService

# All output formats: markdown, json, html, chunks
marker_single input.pdf --output_dir ./output --output_format json
```

## Performance Tuning (TO EXPLORE)

> [!NOTE]
> These options have NOT been systematically tested yet. Default values work well
> but there may be significant speed/quality gains from tuning.

| Flag | Default | Notes |
|------|---------|-------|
| `--lowres_image_dpi` | 96 | DPI for layout/line detection. Lower = faster. |
| `--highres_image_dpi` | 192 | DPI for OCR. Lower = faster, less accurate. |
| `--layout_batch_size` | auto | Batch size for layout model. Larger = faster on GPU. |
| `--disable_ocr` | False | Skip OCR entirely (if PDF has embedded text). |
| `--disable_image_extraction` | False | Skip image extraction (smaller output). |

## LLM Integration (TO EXPLORE)

> [!NOTE]
> Using `--use_llm` can significantly improve accuracy for complex tables,
> inline math, and ambiguous layouts. Cost vs quality tradeoff not yet measured.

Available services:
- `marker.services.gemini.GoogleGeminiService` — needs `GOOGLE_API_KEY` env var
- `marker.services.openai.OpenAIService` — needs `OPENAI_API_KEY`
- `marker.services.ollama.OllamaService` — local LLMs, no API key needed

## Output Formats

| Format | Size per page | Use case |
|--------|--------------|----------|
| Markdown | ~2-5 KB | Human reading, LLM input |
| JSON | ~15-30 KB | Programmatic access, block-level metadata |
| HTML | ~10-20 KB | Direct rendering (no math) |
| Custom (DailyReaderRenderer) | ~20-30 KB | Styled HTML with KaTeX, dark mode |

## JSON Block Types

When using JSON output, each block has a `block_type`:

| Type | Description |
|------|-------------|
| `Text` | Regular paragraph |
| `SectionHeader` | Heading (h1-h6) |
| `Code` | Code block |
| `Figure` | Figure with caption |
| `Picture` | Standalone image |
| `PageHeader` | Running page header (usually filtered out) |
| `PageFooter` | Running page footer (usually filtered out) |
