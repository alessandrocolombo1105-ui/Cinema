document.documentElement.classList.add('js');

document.addEventListener('error', (event) => {
  const img = event.target;
  if (!(img instanceof HTMLImageElement) || !img.closest('.film-poster')) {
    return;
  }
  const placeholder = document.createElement('div');
  placeholder.className = 'poster-placeholder d-flex align-items-center justify-content-center';
  placeholder.innerHTML = '<i class="bi bi-film"></i>';
  img.replaceWith(placeholder);
}, true);

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function setupReveal() {
  const items = document.querySelectorAll('.reveal');
  if (!items.length) {
    return;
  }
  if (reducedMotion() || !('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
  items.forEach((item) => observer.observe(item));
}

function setupNavbar() {
  const nav = document.querySelector('[data-site-nav]');
  const toTop = document.querySelector('[data-back-to-top]');
  const onScroll = () => {
    if (nav) {
      nav.classList.toggle('is-scrolled', window.scrollY > 24);
    }
    if (toTop) {
      toTop.classList.toggle('is-visible', window.scrollY > 600);
    }
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  if (toTop) {
    toTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' });
    });
  }
}

function setupSpotlight() {
  const hero = document.querySelector('[data-spotlight]');
  if (!hero || reducedMotion()) {
    return;
  }
  hero.addEventListener('pointermove', (event) => {
    const rect = hero.getBoundingClientRect();
    hero.style.setProperty('--mx', `${((event.clientX - rect.left) / rect.width) * 100}%`);
    hero.style.setProperty('--my', `${((event.clientY - rect.top) / rect.height) * 100}%`);
  });
}

function setupFilmFilters() {
  const grid = document.querySelector('[data-film-grid]');
  if (!grid) {
    return;
  }
  const cards = Array.from(grid.querySelectorAll('.film-col'));
  if (!cards.length) {
    return;
  }
  const search = document.querySelector('[data-film-search]');
  const sort = document.querySelector('[data-film-sort]');
  const chips = Array.from(document.querySelectorAll('[data-genre]'));
  const counter = document.querySelector('[data-film-count]');
  const empty = document.querySelector('[data-film-empty]');
  let genre = '';

  const apply = () => {
    const query = (search ? search.value : '').trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const haystack = `${card.dataset.title} ${card.dataset.director} ${card.dataset.genre}`.toLowerCase();
      const matches = (!query || haystack.includes(query)) && (!genre || card.dataset.genre === genre);
      card.classList.toggle('d-none', !matches);
      if (matches) {
        visible += 1;
      }
    });
    if (counter) {
      counter.textContent = visible === 1 ? '1 film trovato' : `${visible} film trovati`;
    }
    if (empty) {
      empty.classList.toggle('d-none', visible > 0);
    }
  };

  if (search) {
    search.addEventListener('input', apply);
  }
  if (sort) {
    sort.addEventListener('change', () => {
      const mode = sort.value;
      if (!mode) {
        return;
      }
      const ordered = [...cards].sort((a, b) => {
        if (mode === 'year') {
          return Number(b.dataset.year) - Number(a.dataset.year);
        }
        if (mode === 'duration') {
          return Number(a.dataset.duration) - Number(b.dataset.duration);
        }
        return a.dataset.title.localeCompare(b.dataset.title, 'it');
      });
      ordered.forEach((card) => grid.appendChild(card));
    });
  }
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((other) => other.classList.toggle('is-active', other === chip));
      genre = chip.dataset.genre;
      apply();
    });
  });
  apply();
}

function setupScreeningFilters() {
  const container = document.querySelector('[data-screenings]');
  if (!container) {
    return;
  }
  const blocks = Array.from(container.querySelectorAll('[data-day-index]'));
  if (!blocks.length) {
    return;
  }
  const chips = Array.from(container.querySelectorAll('[data-day]'));
  const onlyAvailable = container.querySelector('[data-only-available]');
  const empty = container.querySelector('[data-screenings-empty]');
  let day = '';

  const apply = () => {
    let total = 0;
    blocks.forEach((block) => {
      let shown = 0;
      block.querySelectorAll('[data-available]').forEach((card) => {
        const free = !onlyAvailable || !onlyAvailable.checked || Number(card.dataset.available) > 0;
        card.classList.toggle('d-none', !free);
        if (free) {
          shown += 1;
        }
      });
      const visible = shown > 0 && (!day || block.dataset.dayIndex === day);
      block.classList.toggle('d-none', !visible);
      if (visible) {
        total += shown;
      }
    });
    if (empty) {
      empty.classList.toggle('d-none', total > 0);
    }
  };

  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((other) => other.classList.toggle('is-active', other === chip));
      day = chip.dataset.day;
      apply();
    });
  });
  if (onlyAvailable) {
    onlyAvailable.addEventListener('change', apply);
  }
  apply();
}

function setupCountdowns() {
  const nodes = Array.from(document.querySelectorAll('[data-countdown]'));
  if (!nodes.length) {
    return;
  }
  const label = (target) => {
    const diff = target - Date.now();
    if (diff <= 0) {
      return 'in corso';
    }
    const minutes = Math.floor(diff / 60000);
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    if (days > 0) {
      return `tra ${days} ${days === 1 ? 'giorno' : 'giorni'} e ${hours} h`;
    }
    if (hours > 0) {
      return `tra ${hours} h ${minutes % 60} min`;
    }
    return `tra ${minutes} min`;
  };
  const update = () => {
    nodes.forEach((node) => {
      const target = Date.parse(node.dataset.countdown);
      if (!Number.isNaN(target)) {
        node.innerHTML = `<i class="bi bi-hourglass-split"></i>${label(target)}`;
      }
    });
  };
  update();
  window.setInterval(update, 30000);
}

function setupCopyButtons() {
  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
      } catch (error) {
        return;
      }
      const original = button.innerHTML;
      button.innerHTML = '<i class="bi bi-check2 me-2"></i>Codice copiato';
      button.disabled = true;
      window.setTimeout(() => {
        button.innerHTML = original;
        button.disabled = false;
      }, 2000);
    });
  });
}

function setupConfetti() {
  const host = document.querySelector('[data-confetti]');
  if (!host) {
    return;
  }
  if (reducedMotion()) {
    host.remove();
    return;
  }
  const colors = ['#ffc94a', '#ff9f1c', '#8ad7ff', '#ffffff'];
  for (let i = 0; i < 70; i += 1) {
    const piece = document.createElement('span');
    piece.className = 'confetti-piece';
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = `${Math.random() * 1.2}s`;
    piece.style.animationDuration = `${2.6 + Math.random() * 1.8}s`;
    host.appendChild(piece);
  }
  window.setTimeout(() => host.remove(), 6500);
}

function setupBookingForm() {
  document.querySelectorAll('form[data-booking-form]').forEach((form) => {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalLabel = submitButton.innerHTML;

    form.addEventListener('input', (event) => {
      event.target.classList.remove('is-invalid');
    });

    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        form.classList.add('was-validated');
        const invalid = form.querySelector(':invalid');
        if (invalid) {
          invalid.focus();
        }
        return;
      }
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Invio in corso…';
    });

    window.addEventListener('pageshow', () => {
      submitButton.disabled = false;
      submitButton.innerHTML = originalLabel;
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupReveal();
  setupNavbar();
  setupSpotlight();
  setupFilmFilters();
  setupScreeningFilters();
  setupCountdowns();
  setupCopyButtons();
  setupConfetti();
  setupBookingForm();
});
