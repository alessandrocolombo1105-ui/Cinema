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

// Form di prenotazione: validazione nel browser con gli stili Bootstrap e blocco del doppio invio.
document.addEventListener('DOMContentLoaded', () => {
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
        form.querySelector(':invalid')?.focus();
        return;
      }
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Invio in corso…';
    });

    // Tornando indietro con il browser la pagina può essere ripristinata dalla cache: riattiva il pulsante
    window.addEventListener('pageshow', () => {
      submitButton.disabled = false;
      submitButton.innerHTML = originalLabel;
    });
  });
});
