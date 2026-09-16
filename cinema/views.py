import logging
from datetime import timedelta, timezone as dt_timezone
from itertools import groupby

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from . import services
from .forms import BookingForm

logger = logging.getLogger(__name__)


def home(request):
    films = []
    error = None
    try:
        films = services.get_films()
    except services.CinemaAPIError as exc:
        logger.warning('Errore nel recupero dei film: %s', exc)
        error = 'Al momento non riusciamo a caricare la programmazione. Riprova tra qualche minuto.'

    genres = sorted({film['genre'] for film in films if film.get('genre')})
    return render(request, 'cinema/home.html', {'films': films, 'error': error, 'genres': genres})


def film_detail(request):
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

    screening_days = _group_upcoming_by_day(screenings)
    return render(request, 'cinema/film_detail.html', {
        'film': film,
        'screening_days': screening_days,
        'next_screening': _first_bookable(screening_days),
    })


def booking(request, screening_id):
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
                'duration': screening['film'].get('duration'),
                'hall': screening['hall']['name'],
                'starts_at': screening['starts_at'].isoformat(),
            }
            return redirect('cinema:booking_success')

    return render(request, 'cinema/booking.html', {
        'screening': screening,
        'form': form,
        'is_bookable': is_bookable,
    })


def booking_success(request):
    last_booking = request.session.get('last_booking')
    if not last_booking:
        return redirect('cinema:home')

    last_booking = {**last_booking, 'starts_at': parse_datetime(last_booking['starts_at'])}
    return render(request, 'cinema/booking_success.html', {'booking': last_booking})


def booking_ticket(request):
    last_booking = request.session.get('last_booking')
    if not last_booking:
        return redirect('cinema:home')

    start = parse_datetime(last_booking['starts_at'])
    end = start + timedelta(minutes=last_booking.get('duration') or 120)
    holder = f"{last_booking['first_name']} {last_booking['last_name']}"
    calendar = '\r\n'.join([
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//ITS Cinema//Prenotazioni//IT',
        'BEGIN:VEVENT',
        f"UID:prenotazione-{last_booking['id']}@its-cinema",
        f'DTSTAMP:{_ics_datetime(timezone.now())}',
        f'DTSTART:{_ics_datetime(start)}',
        f'DTEND:{_ics_datetime(end)}',
        f"SUMMARY:{_ics_text(last_booking['film_title'])} - ITS Cinema",
        f"LOCATION:{_ics_text(last_booking['hall'])}",
        f"DESCRIPTION:Prenotazione {last_booking['id']} a nome {_ics_text(holder)}",
        'END:VEVENT',
        'END:VCALENDAR',
    ])

    response = HttpResponse(calendar, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="its-cinema.ics"'
    return response


def _ics_datetime(value):
    return value.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _ics_text(value):
    return str(value).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def _group_upcoming_by_day(screenings):
    now = timezone.now()
    upcoming = sorted(
        (s for s in screenings if s.get('starts_at') and s['starts_at'] >= now),
        key=lambda s: s['starts_at'],
    )
    for screening in upcoming:
        screening['seats_status'] = _seats_status(screening)
        screening['seats_percent'] = _seats_percent(screening)

    return [
        {'date': day, 'screenings': list(items)}
        for day, items in groupby(upcoming, key=lambda s: timezone.localdate(s['starts_at']))
    ]


def _seats_status(screening):
    available = screening['available_seats']
    if available <= 0:
        return 'sold_out'
    if available <= screening['hall']['capacity'] * 0.1:
        return 'low'
    return 'available'


def _seats_percent(screening):
    capacity = screening['hall'].get('capacity') or 0
    if not capacity:
        return 0
    return max(0, min(100, round(screening['available_seats'] / capacity * 100)))


def _first_bookable(screening_days):
    for day in screening_days:
        for screening in day['screenings']:
            if screening['seats_status'] != 'sold_out':
                return screening
    return None


def _add_api_errors(form, exc):
    if not exc.details:
        form.add_error(None, exc.message)
    for field, message in exc.details.items():
        form.add_error(field if field in form.fields else None, message)
