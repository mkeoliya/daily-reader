/* daily-reader.js — Section loading & PDF view toggle.
 *
 * Loading strategy (books-first architecture):
 *   1. Initial paint: first section (books) — lightweight, no JS needed
 *   2. On "Continue" click: replaces <main> content (no DOM growth, no reload)
 *   3. PDF pages pre-rendered as WebP at build time — zero client-side rendering
 *   4. Ctrl+Shift+P toggles PDF/Markdown view via CSS only
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
});

// --- PDF view toggle (desktop only, pure CSS) ---
if (window.matchMedia('(min-width: 769px)').matches) {
  const toast = document.querySelector('.dr-view-toast');
  let toastTimer;
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1200);
  }

  let currentPage = 0;

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
      e.preventDefault();
      document.body.classList.toggle('view-pdf');
      showToast(document.body.classList.contains('view-pdf') ? '📄 PDF view' : '📝 Markdown view');
      currentPage = 0;
      return;
    }

    // Arrow key navigation in PDF view
    if (!document.body.classList.contains('view-pdf')) return;
    const pages = document.querySelectorAll('.pdf-page');
    if (pages.length === 0) return;

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      currentPage = Math.min(currentPage + 1, pages.length - 1);
      pages[currentPage].scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      currentPage = Math.max(currentPage - 1, 0);
      pages[currentPage].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
}
