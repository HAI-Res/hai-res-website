document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.site-nav');
  if (nav) {
    const path = window.location.pathname.replace(/\/$/, '') || '/index.html';
    nav.querySelectorAll('a').forEach((link) => {
      const href = link.getAttribute('href') || '';
      const normalized = href.replace(/^\.\//, '/').replace(/\/$/, '');
      if (normalized === path || (path.endsWith('index.html') && normalized === path.replace('/index.html', ''))) {
        link.setAttribute('aria-current', 'page');
      }
    });
  }

  const peopleGrids = document.querySelectorAll('[data-monthly-shuffle]');
  peopleGrids.forEach((grid) => shuffleMonthly(grid));
});

function monthlySeed() {
  const now = new Date();
  return now.getFullYear() * 12 + now.getMonth();
}

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function isAnnaCard(item) {
  const href = item.getAttribute('href') || '';
  return href.includes('/anna_huang/');
}

function shuffleMonthly(container) {
  const items = Array.from(container.children);
  if (items.length < 2) return;

  const pinned = items.filter(isAnnaCard);
  const rest = items.filter((item) => !isAnnaCard(item));

  container.style.visibility = 'hidden';
  const random = mulberry32(monthlySeed());
  for (let i = rest.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [rest[i], rest[j]] = [rest[j], rest[i]];
  }
  [...pinned, ...rest].forEach((item) => container.appendChild(item));
  container.style.visibility = '';
}
