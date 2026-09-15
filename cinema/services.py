from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime


class CinemaAPIError(Exception):
    pass


class NotFoundError(CinemaAPIError):
    pass


class InvalidRequestError(CinemaAPIError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details if isinstance(details, dict) else {}


def _request(method, path, **kwargs):
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
    screening['starts_at'] = parse_datetime(screening['starts_at'])
    return screening


def get_films():
    return _request('get', 'films')


def get_film(film_id):
    return _request('get', f'films/{film_id}')


def get_film_screenings(film_id):
    return [_with_start_time(screening) for screening in _request('get', f'films/{film_id}/screenings')]


def get_screening(screening_id):
    return _with_start_time(_request('get', f'screenings/{screening_id}'))


def create_booking(screening_id, first_name, last_name, email):
    return _request('post', f'screenings/{screening_id}/bookings', json={
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
    })
