// Sostituisce le locandine che non si caricano con un segnaposto.
// Gli eventi "error" delle immagini non risalgono il DOM: serve la fase di capture.
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
