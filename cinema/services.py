"""Client per l'API esterna del cinema (https://its-cinema.vercel.app/api/)."""
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime


class CinemaAPIError(Exception):
    """Errore generico nella comunicazione con l'API del cinema."""


class NotFoundError(CinemaAPIError):
    """La risorsa richiesta non esiste (HTTP 404)."""


class InvalidRequestError(CinemaAPIError):
    """L'API ha rifiutato la richiesta (HTTP 400): dati non validi o posti esauriti."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details if isinstance(details, dict) else {}


def _request(method, path, **kwargs):
    """Esegue una richiesta HTTP sull'API e restituisce il JSON decodificato."""
    url = urljoin(settings.CINEMA_API_BASE_URL, path)
    send = getattr(requests, method)
    try:
        response = send(url, timeout=settings.CINEMA_API_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise CinemaAPIError(f'Impossibile contattare {url}') from exc

    if response.status_code == 404:
        raise NotFoundError(f'Risorsa non trovata: {url}')
    if response.status_code == 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            payload = {}
        raise InvalidRequestError(payload.get('error', 'Richiesta non valida'), payload.get('details'))
    if not response.ok:
        raise CinemaAPIError(f'Risposta inattesa ({response.status_code}) da {url}')

    try:
        return response.json()
    except ValueError as exc:
        raise CinemaAPIError(f'Risposta non valida da {url}') from exc


def _with_start_time(screening):
    """Converte `starts_at` (stringa ISO 8601 in UTC) in un datetime."""
    screening['starts_at'] = parse_datetime(screening['starts_at'])
    return screening


def get_films():
    """GET /films — elenco dei film in programmazione."""
    return _request('get', 'films')


def get_film(film_id):
    """GET /films/{id} — dettaglio di un film."""
    return _request('get', f'films/{film_id}')


def get_film_screenings(film_id):
    """GET /films/{id}/screenings — spettacoli di un film."""
    return [_with_start_time(screening) for screening in _request('get', f'films/{film_id}/screenings')]


def get_screening(screening_id):
    """GET /screenings/{id} — dettaglio di uno spettacolo, con i dati del film e della sala."""
    return _with_start_time(_request('get', f'screenings/{screening_id}'))


def create_booking(screening_id, first_name, last_name, email):
    """POST /screenings/{id}/bookings — prenota un posto per lo spettacolo."""
    return _request('post', f'screenings/{screening_id}/bookings', json={
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
    })
