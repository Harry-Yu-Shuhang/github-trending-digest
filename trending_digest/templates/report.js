(() => {
  'use strict';
  const root = document.documentElement;
  const theme = document.getElementById('theme');
  let saved = null;
  try { saved = localStorage.getItem('brief-theme'); } catch (_) { /* File access may be restricted. */ }
  const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  root.dataset.theme = preferred;
  theme.setAttribute('aria-pressed', String(preferred === 'dark'));
  theme.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    theme.setAttribute('aria-pressed', String(next === 'dark'));
    try { localStorage.setItem('brief-theme', next); } catch (_) { /* Theme still works without storage. */ }
  });
  document.getElementById('print').addEventListener('click', () => window.print());
  const progress = document.querySelector('.reading-progress');
  const updateProgress = () => {
    const height = root.scrollHeight - window.innerHeight;
    progress.style.transform = `scaleX(${height > 0 ? Math.min(1, Math.max(0, window.scrollY / height)) : 0})`;
  };
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
  updateProgress();
  const cards = [...document.querySelectorAll('.project')];
  const search = document.getElementById('search');
  if (!search) return;
  const technology = document.getElementById('technology');
  const count = document.getElementById('result-count');
  const reset = document.getElementById('reset');
  const jump = document.getElementById('jump');
  const empty = document.getElementById('empty-state');
  const toc = [...document.querySelectorAll('[data-project]')];
  const terms = new Map(cards.map(card => [card, card.textContent.toLocaleLowerCase()]));
  const filter = () => {
    const phrase = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const card of cards) {
      const matches = terms.get(card).includes(phrase) && (!technology.value || card.dataset.language === technology.value);
      card.hidden = !matches;
      if (matches) visible += 1;
      const item = toc.find(entry => entry.dataset.project === card.id);
      if (item) item.hidden = !matches;
      const option = [...jump.options].find(entry => entry.value === card.id);
      if (option) { option.disabled = !matches; option.hidden = !matches; }
    }
    count.textContent = count.dataset.template.replace('{visible}', String(visible)).replace('{total}', String(cards.length));
    empty.hidden = visible !== 0;
    reset.hidden = !phrase && !technology.value;
    jump.value = '';
    updateProgress();
  };
  search.addEventListener('input', filter);
  technology.addEventListener('change', filter);
  reset.addEventListener('click', () => { search.value = ''; technology.value = ''; filter(); search.focus(); });
  jump.addEventListener('change', () => {
    const project = document.getElementById(jump.value);
    if (project && !project.hidden) {
      project.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
      project.querySelector('h2 a').focus({ preventScroll: true });
    }
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.target.hidden) continue;
        for (const item of toc) {
          const link = item.querySelector('a');
          if (item.dataset.project === entry.target.id) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        }
      }
    }, { rootMargin: '-5% 0px -60% 0px' });
    cards.forEach(card => observer.observe(card));
  }
})();
