import logging
from itertools import groupby

from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

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
    """Dettaglio film con l'elenco dei prossimi spettacoli."""
    film_id = request.GET.get('id', '')
    if not film_id.isdigit():
        raise Http404('Film non trovato')

    try:
        film = services.get_film(film_id)
        screenings = services.get_film_screenings(film_id)
    except services.NotFoundError:
        raise Http404('Film non trovato') from None
    except services.CinemaAPIError as exc:
        logger.warning('Errore nel recupero del film %s: %s', film_id, exc)
        context = {'error': 'Al momento non riusciamo a caricare le informazioni del film. Riprova tra qualche minuto.'}
        return render(request, 'cinema/film_detail.html', context, status=503)

    return render(request, 'cinema/film_detail.html', {
        'film': film,
        'screening_days': _group_upcoming_by_day(screenings),
    })


def _group_upcoming_by_day(screenings):
    """Scarta gli spettacoli già iniziati e raggruppa gli altri per giorno (ora locale), in ordine cronologico."""
    now = timezone.now()
    upcoming = sorted(
        (s for s in screenings if s.get('starts_at') and s['starts_at'] >= now),
        key=lambda s: s['starts_at'],
    )
    for screening in upcoming:
        screening['seats_status'] = _seats_status(screening)

    return [
        {'date': day, 'screenings': list(items)}
        for day, items in groupby(upcoming, key=lambda s: timezone.localdate(s['starts_at']))
    ]


def _seats_status(screening):
    """Disponibilità dei posti: 'sold_out', 'low' (10% o meno della capienza) oppure 'available'."""
    available = screening['available_seats']
    if available <= 0:
        return 'sold_out'
    if available <= screening['hall']['capacity'] * 0.1:
        return 'low'
    return 'available'
