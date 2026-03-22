/* daily-reader.js — Section loading & PDF viewer lifecycle.
 *
 * Loading strategy (books-first architecture):
 *   1. Initial paint: first section (books) — no JS needed
 *   2. Background: pdf.js import fires immediately, loads while user reads
 *   3. On "Continue" click: replaces <main> content (no DOM growth, no reload)
 *   4. PDF canvases render only on first Ctrl+Shift+P toggle (no scroll jank)
 */

// --- KaTeX config ---
const KATEX_OPTS = {
  delimiters: [
    { left: '$$', right: '$$', display: true },
    { left: '$', right: '$', display: false },
    { left: '\\(', right: '\\)', display: false },
    { left: '\\[', right: '\\]', display: true },
  ],
  throwOnError: false,
};

// --- Section loading (replaces content, no DOM growth) ---
document.addEventListener('click', async (e) => {
  const a = e.target.closest('[data-section]');
  if (!a) return;
  e.preventDefault();
  const main = document.querySelector('main');
  main.innerHTML = await (await fetch(a.href)).text();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  renderMathInElement?.(main, KATEX_OPTS);
  initPdfs(main);
});

// --- PDF viewer (desktop only, lazy rendering) ---
const isDesktop = window.matchMedia('(min-width: 769px)').matches;

// Eagerly preload pdf.js while user reads books
const pdfjsReady = isDesktop
  ? import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.min.mjs')
  : null;

let initPdfs = () => {};

if (isDesktop) {
  let allPages = [];
  let currentPage = 0;
  let pdfRendered = false;
  const SCALE = Math.max(window.devicePixelRatio || 1, 2.5);

  // Toast
  const toast = document.querySelector('.dr-view-toast');
  let toastTimer;
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1200);
  }

  // Page tracking
  const observer = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) currentPage = allPages.indexOf(e.target);
    }
  }, { threshold: 0.5 });

  // Render PDFs for [data-pdf] elements within a root
  async function renderPdfs(root = document) {
    const docs = root.querySelectorAll('.dr-doc[data-pdf]');
    if (docs.length === 0) return;

    const pdfjsLib = await pdfjsReady;
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.worker.min.mjs';

    for (const docEl of docs) {
      const container = docEl.querySelector('.pdf-view');
      if (!container || container.children.length > 0) continue;

      try {
        const pdf = await pdfjsLib.getDocument(docEl.dataset.pdf).promise;
        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i);
          const vp = page.getViewport({ scale: SCALE });
          const wrapper = document.createElement('div');
          wrapper.className = 'pdf-page';
          const canvas = document.createElement('canvas');
          canvas.width = vp.width;
          canvas.height = vp.height;
          await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;
          wrapper.appendChild(canvas);
          container.appendChild(wrapper);
          allPages.push(wrapper);
          observer.observe(wrapper);
        }
      } catch (err) {
        console.warn('pdf.js:', docEl.dataset.pdf, err);
      }
    }
  }

  // initPdfs: called after loading a new section — marks PDFs as pending
  initPdfs = (root) => {
    pdfRendered = false;
    allPages = [];
  };

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const isPdf = document.body.classList.contains('view-pdf');

    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
      e.preventDefault();
      document.body.classList.toggle('view-pdf');
      const nowPdf = document.body.classList.contains('view-pdf');
      showToast(nowPdf ? '📄 PDF view' : '📝 Markdown view');
      // Lazy render: only on first toggle to PDF
      if (nowPdf && !pdfRendered) {
        pdfRendered = true;
        renderPdfs();
      }
      return;
    }

    if (!isPdf || allPages.length === 0) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      currentPage = Math.min(currentPage + 1, allPages.length - 1);
      allPages[currentPage].scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      currentPage = Math.max(currentPage - 1, 0);
      allPages[currentPage].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
}
