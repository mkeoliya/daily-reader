---
name: pdf2htmlex
description: How to convert PDFs to HTML using pdf2htmlEX, with emphasis on email-optimized output
---

# PDF to HTML with pdf2htmlEX

`pdf2htmlEX` converts PDF pages to high-fidelity HTML with embedded fonts and images. It preserves the exact layout of the original PDF.

- **Binary**: `/home/mkeoliya/usr/local/bin/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-bionic-x86_64.AppImage`
- **Alias**: Add to `.bashrc`: `alias pdf2html='/home/mkeoliya/usr/local/bin/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-bionic-x86_64.AppImage'`

## Basic Usage

```bash
pdf2htmlEX input.pdf                    # → input.html (all pages, one file)
pdf2htmlEX input.pdf output.html        # custom output name
pdf2htmlEX -f 3 -l 5 input.pdf out.html # pages 3-5 only
```

## Email-Optimized Single Page (Recommended for RSS/Email)

Extract one self-contained page at a time with fonts/images embedded inline:

```bash
pdf2htmlEX \
  -f 1 -l 1 \
  --fit-width 680 \
  --dpi 96 \
  --optimize-text 1 \
  --font-size-multiplier 1 \
  --bg-format jpg \
  --embed-css 1 \
  --embed-font 1 \
  --embed-image 1 \
  --embed-javascript 0 \
  --process-outline 0 \
  --printing 0 \
  --dest-dir /output/dir \
  input.pdf page1.html
```

**Output size**: ~55-120KB per page depending on graphics content. Self-contained, no external dependencies.

### Key flags explained

| Flag | Value | Why |
|------|-------|-----|
| `-f N -l N` | page range | Extract specific pages |
| `--fit-width 680` | pixels | Constrain width for email clients (680px is standard) |
| `--dpi 96` | resolution | Good quality/size tradeoff (default 144 is overkill for screen) |
| `--optimize-text 1` | on | Reduces HTML element count |
| `--font-size-multiplier 1` | reduced | Default 4 increases precision but bloats HTML; 1 is fine for email |
| `--bg-format jpg` | JPEG | ~20% smaller than PNG for background images |
| `--embed-css 1` | default | Inline CSS (no external files) |
| `--embed-font 1` | default | Inline fonts as base64 woff (critical for fidelity) |
| `--embed-image 1` | default | Inline images as base64 (no external files) |
| `--embed-javascript 0` | **override** | Disable JS — not needed, stripped by email clients |
| `--process-outline 0` | **override** | Skip table of contents |
| `--printing 0` | **override** | Disable print CSS |

## Batch Pre-Processing (All Pages)

Convert an entire PDF into separate `.page` fragment files:

```bash
pdf2htmlEX \
  --split-pages 1 \
  --fit-width 680 \
  --embed-css 1 --embed-font 1 --embed-image 1 \
  --embed-javascript 0 --process-outline 0 --printing 0 \
  --dest-dir /output/dir \
  input.pdf
```

**Output**:
- `input.html` — parent shell with CSS/fonts (~100-125KB shared)
- `input1.page`, `input2.page`, ... — per-page HTML fragments (~10-100KB each)

> [!WARNING]
> The `.page` files are NOT standalone. They need the parent HTML's CSS and embedded fonts to render. They are loaded via JavaScript in the browser. **Not suitable for email** without recombining with the parent CSS.

## Sizing Reference

Tested on a research paper PDF (9MB source):

| Approach | Size per page | Self-contained? |
|----------|--------------|-----------------|
| Single-page (`-f 1 -l 1`, all embedded) | ~232KB | ✅ Yes |
| Single-page (no font embed) | ~127KB + external .woff files | ❌ No |
| Split pages (fragment) | ~11-114KB + parent shell | ❌ No |
| Fallback mode | ~232KB | ✅ Yes |

## Other Useful Flags

- `--dpi <N>` — Resolution for graphics (default: 144). Lower = smaller files.
- `--bg-format png|jpg` — Background image format (default: png). Use jpg for photos.
- `--zoom <float>` — Zoom ratio for rendering
- `--decompose-ligature 1` — Break ligatures like ﬁ → fi (better for search/copy)
- `--optimize-text 1` — Reduce HTML element count (smaller files, may affect layout)
- `-o` / `-u` — Owner/user passwords for encrypted PDFs
