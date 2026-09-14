from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

import requests
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .templatetags.cinema_extras import durata

FILM = {
    'id': 1,
    'title': 'Oppenheimer',
    'genre': 'Biografico',
    'duration': 180,
    'director': 'Christopher Nolan',
    'description': 'La storia del fisico J. Robert Oppenheimer.',
    'poster_url': 'https://example.com/oppenheimer.jpg',
    'year': 2023,
    'rating': 'VM14',
}


def make_screening(screening_id, starts_at, hall='Sala 1', seats=100, capacity=150):
    return {
        'id': screening_id,
        'starts_at': starts_at,
        'hall': {'id': 1, 'name': hall, 'capacity': capacity},
        'available_seats': seats,
    }


def api_response(payload, status_code=200):
    return Mock(status_code=status_code, ok=status_code < 400, json=Mock(return_value=payload))


class ServicesTests(SimpleTestCase):
    @patch('cinema.services.requests.get')
    def test_get_films_returns_json(self, mock_get):
        mock_get.return_value = api_response([FILM])

        self.assertEqual(services.get_films(), [FILM])
        mock_get.assert_called_once_with(
            'https://its-cinema.vercel.app/api/films', params=None, timeout=settings.CINEMA_API_TIMEOUT
        )

    @patch('cinema.services.requests.get', side_effect=requests.ConnectionError)
    def test_network_error_raises_api_error(self, _):
        with self.assertRaises(services.CinemaAPIError):
            services.get_films()

    @patch('cinema.services.requests.get')
    def test_404_raises_not_found(self, mock_get):
        mock_get.return_value = api_response({'error': 'Film non trovato'}, status_code=404)

        with self.assertRaises(services.NotFoundError):
            services.get_film(999)

    @patch('cinema.services.requests.get')
    def test_get_film_screenings_parses_start_time(self, mock_get):
        mock_get.return_value = api_response([make_screening(155, '2026-05-15T15:00:00.000Z')])

        screenings = services.get_film_screenings(1)

        self.assertEqual(screenings[0]['starts_at'], datetime(2026, 5, 15, 15, 0, tzinfo=dt_timezone.utc))
        mock_get.assert_called_once_with(
            'https://its-cinema.vercel.app/api/films/1/screenings', params=None, timeout=settings.CINEMA_API_TIMEOUT
        )


class DurataFilterTests(SimpleTestCase):
    def test_formats_minutes(self):
        self.assertEqual(durata(180), '3 h 00 min')
        self.assertEqual(durata(94), '1 h 34 min')
        self.assertEqual(durata(45), '45 min')
        self.assertEqual(durata(None), '')


class HomeViewTests(SimpleTestCase):
    @patch('cinema.services.get_films', return_value=[FILM])
    def test_home_lists_films(self, _):
        response = self.client.get(reverse('cinema:home'))

        self.assertContains(response, 'Oppenheimer')
        self.assertContains(response, 'Scopri di più')
        self.assertContains(response, f"{reverse('cinema:film_detail')}?id=1")

    @patch('cinema.services.get_films', side_effect=services.CinemaAPIError('offline'))
    def test_home_shows_error_when_api_fails(self, _):
        with self.assertLogs('cinema.views', level='WARNING'):
            response = self.client.get(reverse('cinema:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alert-danger')


class FilmDetailViewTests(SimpleTestCase):
    def get_detail(self, query=''):
        return self.client.get(reverse('cinema:film_detail') + query)

    def test_missing_or_invalid_id_returns_404(self):
        for query in ('', '?id=', '?id=abc', '?id=-1'):
            with self.subTest(query=query):
                self.assertEqual(self.get_detail(query).status_code, 404)

    @patch('cinema.services.get_film', side_effect=services.NotFoundError('404'))
    def test_unknown_film_returns_404(self, _):
        self.assertEqual(self.get_detail('?id=999').status_code, 404)

    @patch('cinema.services.get_film_screenings')
    @patch('cinema.services.get_film', return_value=FILM)
    def test_shows_film_and_upcoming_screenings_in_order(self, _, mock_screenings):
        now = timezone.now()
        mock_screenings.return_value = [
            make_screening(1, now + timedelta(days=2), hall='Sala IMAX'),
            make_screening(2, now - timedelta(days=1), hall='Sala Chiusa'),
            make_screening(3, now + timedelta(days=1), hall='Sala Lumière', seats=0),
            make_screening(4, now + timedelta(days=3), hall='Sala 2', seats=5),
        ]

        response = self.get_detail('?id=1')

        self.assertContains(response, 'Oppenheimer')
        self.assertContains(response, 'Christopher Nolan')
        self.assertContains(response, '3 h 00 min')
        self.assertContains(response, 'Sala IMAX')
        self.assertContains(response, 'Esaurito')
        self.assertContains(response, 'Ultimi posti')
        self.assertNotContains(response, 'Sala Chiusa')

        days = response.context['screening_days']
        self.assertEqual([s['id'] for day in days for s in day['screenings']], [3, 1, 4])

    @patch('cinema.services.get_film_screenings', return_value=[])
    @patch('cinema.services.get_film', return_value=FILM)
    def test_shows_message_when_no_screenings(self, *_):
        self.assertContains(self.get_detail('?id=1'), 'Non ci sono spettacoli in programma')

    @patch('cinema.services.get_film', side_effect=services.CinemaAPIError('offline'))
    def test_api_error_shows_message(self, _):
        with self.assertLogs('cinema.views', level='WARNING'):
            response = self.get_detail('?id=1')

        self.assertContains(response, 'alert-danger', status_code=503)
