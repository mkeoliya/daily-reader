/* laptop.js — Toggle between Markdown and PDF view.
 * PDFs load eagerly in the background so they're ready when toggled.
 * Keyboard shortcut: Ctrl+Shift+P (Cmd+Shift+P on Mac).
 * Default view: Markdown.
 */

(async () => {
  // Only load PDF.js on desktop-width screens
  if (!window.matchMedia('(min-width: 769px)').matches) return;

  const pdfjsLib = await import(
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.min.mjs'
  );
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.worker.min.mjs';

  const RENDER_SCALE = Math.max(window.devicePixelRatio || 1, 2.5);
  const pdfDocs = document.querySelectorAll('.dr-doc[data-pdf]');
  const allPageEls = [];
  let currentPage = 0;

  // --- Eagerly render all PDFs in the background ---
  for (const docEl of pdfDocs) {
    const pdfUrl = docEl.dataset.pdf;
    const container = docEl.querySelector('.pdf-view');
    if (!container) continue;

    try {
      const pdf = await pdfjsLib.getDocument(pdfUrl).promise;
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const viewport = page.getViewport({ scale: RENDER_SCALE });

        const wrapper = document.createElement('div');
        wrapper.className = 'pdf-page';

        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({
          canvasContext: canvas.getContext('2d'),
          viewport,
        }).promise;

        wrapper.appendChild(canvas);
        container.appendChild(wrapper);
        allPageEls.push(wrapper);
      }
    } catch (err) {
      console.warn('pdf.js: failed to load', pdfUrl, err);
    }
  }

  // --- Toast helper ---
  const toast = document.querySelector('.dr-view-toast');
  let toastTimer = null;
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1200);
  }

  // --- IntersectionObserver for page tracking (PDF view) ---
  if (allPageEls.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          currentPage = allPageEls.indexOf(e.target);
        }
      }
    }, { threshold: 0.5 });
    allPageEls.forEach((el) => observer.observe(el));
  }

  // --- Keyboard shortcut: Ctrl+Shift+P / Cmd+Shift+P ---
  document.addEventListener('keydown', (e) => {
    const isPdfView = document.body.classList.contains('view-pdf');

    // Toggle shortcut
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
      e.preventDefault();
      document.body.classList.toggle('view-pdf');
      const nowPdf = document.body.classList.contains('view-pdf');
      showToast(nowPdf ? '📄 PDF view' : '📝 Markdown view');
      return;
    }

    // Arrow key navigation (only in PDF view)
    if (!isPdfView || allPageEls.length === 0) return;

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      const next = Math.min(currentPage + 1, allPageEls.length - 1);
      allPageEls[next].scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      const prev = Math.max(currentPage - 1, 0);
      allPageEls[prev].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
})();
