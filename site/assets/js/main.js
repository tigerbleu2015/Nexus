// Mobile nav
const toggle = document.querySelector('.nav-toggle');
const navCenter = document.querySelector('.nav-center');
const navLinks = document.querySelector('.nav-links');
if (toggle) {
  toggle.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    navCenter && navCenter.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
  });
}

// Sticky header shadow
const header = document.querySelector('.site-header');
if (header) {
  window.addEventListener('scroll', () => {
    header.style.boxShadow = window.scrollY > 10 ? '0 4px 30px rgba(0,0,0,0.5)' : 'none';
  }, { passive: true });
}

// Card entrance animation
if ('IntersectionObserver' in window) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateY(0)';
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.card').forEach((c, i) => {
    c.style.opacity = '0';
    c.style.transform = 'translateY(22px)';
    c.style.transition = `opacity 0.45s ease ${(i % 3) * 0.07}s, transform 0.45s ease ${(i % 3) * 0.07}s`;
    obs.observe(c);
  });
}

// Hero text entrance
document.querySelectorAll('.hero-text h1, .hero-text p, .hero-actions').forEach((el, i) => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(18px)';
  el.style.transition = `opacity 0.6s ease ${i * 0.12}s, transform 0.6s ease ${i * 0.12}s`;
  requestAnimationFrame(() => setTimeout(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
  }, 50));
});

// Active nav link
const path = window.location.pathname;
document.querySelectorAll('.nav-links a').forEach(a => {
  if (a.getAttribute('href') === path || (path.includes(a.getAttribute('href')) && a.getAttribute('href') !== '/')) {
    a.style.color = 'var(--teal)';
    a.style.background = 'var(--teal-dim)';
  }
});
