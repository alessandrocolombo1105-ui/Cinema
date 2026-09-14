import logging

from django.shortcuts import render

from . import services

logger = logging.getLogger(__name__)


def home(request):
    """Homepage: elenco dei film in programmazione."""
    films = []
    error = None
    try:
        films = services.get_films()
    except services.CinemaAPIError as exc:
        logger.warning('Errore nel recupero dei film: %s', exc)
        error = 'Al momento non riusciamo a caricare la programmazione. Riprova tra qualche minuto.'

    return render(request, 'cinema/home.html', {'films': films, 'error': error})


def film_detail(request):
    """Dettaglio film."""
    return render(request, 'cinema/film_detail.html', {'film_id': request.GET.get('id')})
