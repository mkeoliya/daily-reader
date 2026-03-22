/* laptop.js — Desktop-only PDF viewer using pdf.js.
 * Finds all .dr-doc[data-pdf] elements and renders their PDFs to canvas.
 * Only runs on viewports >= 769px.
 */

if (window.matchMedia('(min-width: 769px)').matches) {
  (async () => {
    const pdfjsLib = await import(
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.min.mjs'
    );
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.worker.min.mjs';

    const RENDER_SCALE = Math.max(window.devicePixelRatio || 1, 2.5);
    const pdfDocs = document.querySelectorAll('.dr-doc[data-pdf]');

    // Global list of all PDF page elements (across all documents)
    const allPageEls = [];
    let currentPage = 0;

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
        console.warn('pdf.js failed for', pdfUrl, err);
        // Fallback: show the Marker HTML
        const body = docEl.querySelector('.dr-doc-body');
        if (body) body.style.display = '';
      }
    }

    // Single IntersectionObserver tracking all PDF pages
    if (allPageEls.length > 0) {
      const observer = new IntersectionObserver((entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            currentPage = allPageEls.indexOf(e.target);
          }
        }
      }, { threshold: 0.5 });
      allPageEls.forEach((el) => observer.observe(el));

      // Single keydown listener for arrow key navigation
      document.addEventListener('keydown', (e) => {
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
    }
  })();
}
