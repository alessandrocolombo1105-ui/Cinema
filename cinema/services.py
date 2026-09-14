"""Client per l'API esterna del cinema (https://its-cinema.vercel.app/api/)."""
from urllib.parse import urljoin

import requests
from django.conf import settings


class CinemaAPIError(Exception):
    """Errore generico nella comunicazione con l'API del cinema."""


class NotFoundError(CinemaAPIError):
    """La risorsa richiesta non esiste (HTTP 404)."""


def _get(path, params=None):
    """Esegue una GET sull'API e restituisce il JSON decodificato."""
    url = urljoin(settings.CINEMA_API_BASE_URL, path)
    try:
        response = requests.get(url, params=params, timeout=settings.CINEMA_API_TIMEOUT)
    except requests.RequestException as exc:
        raise CinemaAPIError(f'Impossibile contattare {url}') from exc

    if response.status_code == 404:
        raise NotFoundError(f'Risorsa non trovata: {url}')
    if not response.ok:
        raise CinemaAPIError(f'Risposta inattesa ({response.status_code}) da {url}')

    try:
        return response.json()
    except ValueError as exc:
        raise CinemaAPIError(f'Risposta non valida da {url}') from exc


def get_films():
    """GET /films — elenco dei film in programmazione."""
    return _get('films')
