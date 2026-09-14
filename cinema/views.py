import logging
from itertools import groupby

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from . import services
from .forms import BookingForm

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


def booking(request, screening_id):
    """Prenotazione di un posto: riepilogo dello spettacolo e form con i dati dello spettatore."""
    try:
        screening = services.get_screening(screening_id)
    except services.NotFoundError:
        raise Http404('Spettacolo non trovato') from None
    except services.CinemaAPIError as exc:
        logger.warning('Errore nel recupero dello spettacolo %s: %s', screening_id, exc)
        context = {'error': 'Al momento non riusciamo a caricare lo spettacolo. Riprova tra qualche minuto.'}
        return render(request, 'cinema/booking.html', context, status=503)

    is_bookable = screening['available_seats'] > 0 and screening['starts_at'] > timezone.now()
    form = BookingForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and is_bookable and form.is_valid():
        try:
            created = services.create_booking(screening_id, **form.cleaned_data)
        except services.InvalidRequestError as exc:
            _add_api_errors(form, exc)
        except services.NotFoundError:
            raise Http404('Spettacolo non trovato') from None
        except services.CinemaAPIError as exc:
            logger.warning('Errore nella prenotazione dello spettacolo %s: %s', screening_id, exc)
            form.add_error(None, 'Non è stato possibile completare la prenotazione. Riprova tra qualche minuto.')
        else:
            request.session['last_booking'] = {
                'id': created.get('id'),
                **form.cleaned_data,
                'film_id': screening['film']['id'],
                'film_title': screening['film']['title'],
                'hall': screening['hall']['name'],
                'starts_at': screening['starts_at'].isoformat(),
            }
            # Redirect dopo il POST: ricaricando la pagina non si invia una seconda prenotazione
            return redirect('cinema:booking_success')

    return render(request, 'cinema/booking.html', {
        'screening': screening,
        'form': form,
        'is_bookable': is_bookable,
    })


def booking_success(request):
    """Conferma dell'ultima prenotazione effettuata nella sessione corrente."""
    last_booking = request.session.get('last_booking')
    if not last_booking:
        return redirect('cinema:home')

    last_booking = {**last_booking, 'starts_at': parse_datetime(last_booking['starts_at'])}
    return render(request, 'cinema/booking_success.html', {'booking': last_booking})


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


def _add_api_errors(form, exc):
    """Riporta sul form gli errori restituiti dall'API, sul singolo campo quando indicato."""
    if not exc.details:
        form.add_error(None, exc.message)
    for field, message in exc.details.items():
        form.add_error(field if field in form.fields else None, message)
