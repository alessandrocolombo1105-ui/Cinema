from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch

import requests
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .templatetags.cinema_extras import durata

API_URL = settings.CINEMA_API_BASE_URL
TIMEOUT = settings.CINEMA_API_TIMEOUT

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

BOOKING_DATA = {'first_name': 'Mario', 'last_name': 'Rossi', 'email': 'mario.rossi@example.com'}


def make_screening(screening_id, starts_at, hall='Sala 1', seats=100, capacity=150, film=None):
    screening = {
        'id': screening_id,
        'starts_at': starts_at,
        'hall': {'id': 1, 'name': hall, 'capacity': capacity},
        'available_seats': seats,
    }
    if film:
        screening['film'] = film
    return screening


def api_response(payload, status_code=200):
    return Mock(status_code=status_code, ok=status_code < 400, json=Mock(return_value=payload))


class ServicesTests(SimpleTestCase):
    @patch('cinema.services.requests.get')
    def test_get_films_returns_json(self, mock_get):
        mock_get.return_value = api_response([FILM])

        self.assertEqual(services.get_films(), [FILM])
        mock_get.assert_called_once_with(API_URL + 'films', timeout=TIMEOUT)

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
        mock_get.assert_called_once_with(API_URL + 'films/1/screenings', timeout=TIMEOUT)

    @patch('cinema.services.requests.get')
    def test_get_screening_parses_start_time(self, mock_get):
        mock_get.return_value = api_response(make_screening(10, '2026-10-12T18:30:00.000Z', film=FILM))

        screening = services.get_screening(10)

        self.assertEqual(screening['starts_at'], datetime(2026, 10, 12, 18, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(screening['film']['title'], 'Oppenheimer')

    @patch('cinema.services.requests.post')
    def test_create_booking_posts_json(self, mock_post):
        mock_post.return_value = api_response({'id': 42, 'screening_id': 10, **BOOKING_DATA}, status_code=201)

        booking = services.create_booking(10, **BOOKING_DATA)

        self.assertEqual(booking['id'], 42)
        mock_post.assert_called_once_with(API_URL + 'screenings/10/bookings', json=BOOKING_DATA, timeout=TIMEOUT)

    @patch('cinema.services.requests.post')
    def test_create_booking_validation_error_exposes_details(self, mock_post):
        mock_post.return_value = api_response(
            {'error': 'Dati non validi', 'details': {'email': 'Formato email non valido'}}, status_code=400
        )

        with self.assertRaises(services.InvalidRequestError) as ctx:
            services.create_booking(10, **BOOKING_DATA)

        self.assertEqual(ctx.exception.details, {'email': 'Formato email non valido'})

    @patch('cinema.services.requests.post')
    def test_create_booking_without_seats(self, mock_post):
        mock_post.return_value = api_response(
            {'error': 'Nessun posto disponibile per questo spettacolo'}, status_code=400
        )

        with self.assertRaises(services.InvalidRequestError) as ctx:
            services.create_booking(10, **BOOKING_DATA)

        self.assertEqual(ctx.exception.message, 'Nessun posto disponibile per questo spettacolo')
        self.assertEqual(ctx.exception.details, {})


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

        # Solo gli spettacoli con posti liberi sono prenotabili
        self.assertContains(response, reverse('cinema:booking', args=[1]))
        self.assertNotContains(response, reverse('cinema:booking', args=[3]))

    @patch('cinema.services.get_film_screenings', return_value=[])
    @patch('cinema.services.get_film', return_value=FILM)
    def test_shows_message_when_no_screenings(self, *_):
        self.assertContains(self.get_detail('?id=1'), 'Non ci sono spettacoli in programma')

    @patch('cinema.services.get_film', side_effect=services.CinemaAPIError('offline'))
    def test_api_error_shows_message(self, _):
        with self.assertLogs('cinema.views', level='WARNING'):
            response = self.get_detail('?id=1')

        self.assertContains(response, 'alert-danger', status_code=503)


class BookingViewTests(TestCase):
    def setUp(self):
        self.screening = make_screening(
            10, timezone.now() + timedelta(days=1), hall='Sala IMAX', seats=50, capacity=250, film=FILM
        )
        patcher = patch('cinema.services.get_screening', return_value=self.screening)
        self.mock_get_screening = patcher.start()
        self.addCleanup(patcher.stop)
        self.url = reverse('cinema:booking', args=[10])

    def test_get_shows_summary_and_form(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'Oppenheimer')
        self.assertContains(response, 'Sala IMAX')
        for name in BOOKING_DATA:
            self.assertContains(response, f'name="{name}"')

    @patch('cinema.services.create_booking', return_value={'id': 42, 'screening_id': 10, **BOOKING_DATA})
    def test_valid_post_creates_booking_and_shows_confirmation(self, mock_create):
        response = self.client.post(self.url, BOOKING_DATA)

        mock_create.assert_called_once_with(10, **BOOKING_DATA)
        self.assertRedirects(response, reverse('cinema:booking_success'))

        confirmation = self.client.get(reverse('cinema:booking_success'))
        self.assertContains(confirmation, '#42')
        self.assertContains(confirmation, 'Mario Rossi')
        self.assertContains(confirmation, 'Oppenheimer')
        self.assertContains(confirmation, 'Sala IMAX')

    @patch('cinema.services.create_booking')
    def test_invalid_form_does_not_call_api(self, mock_create):
        response = self.client.post(self.url, {**BOOKING_DATA, 'email': 'non-valida', 'first_name': ''})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-invalid')
        mock_create.assert_not_called()

    @patch('cinema.services.create_booking', side_effect=services.InvalidRequestError(
        'Dati non validi', {'email': 'Formato email non valido'}
    ))
    def test_api_validation_errors_are_shown_on_fields(self, _):
        response = self.client.post(self.url, BOOKING_DATA)

        self.assertContains(response, 'Formato email non valido')
        self.assertContains(response, 'is-invalid')

    @patch('cinema.services.create_booking', side_effect=services.InvalidRequestError(
        'Nessun posto disponibile per questo spettacolo'
    ))
    def test_no_seats_error_is_shown(self, _):
        response = self.client.post(self.url, BOOKING_DATA)

        self.assertContains(response, 'Nessun posto disponibile per questo spettacolo')

    @patch('cinema.services.create_booking', side_effect=services.CinemaAPIError('offline'))
    def test_api_down_during_booking_shows_message(self, _):
        with self.assertLogs('cinema.views', level='WARNING'):
            response = self.client.post(self.url, BOOKING_DATA)

        self.assertContains(response, 'Non è stato possibile completare la prenotazione')

    @patch('cinema.services.create_booking')
    def test_sold_out_screening_is_not_bookable(self, mock_create):
        self.screening['available_seats'] = 0

        get_response = self.client.get(self.url)
        self.assertContains(get_response, 'non è più prenotabile')
        self.assertNotContains(get_response, 'name="email"')

        self.client.post(self.url, BOOKING_DATA)
        mock_create.assert_not_called()

    def test_unknown_screening_returns_404(self):
        self.mock_get_screening.side_effect = services.NotFoundError('404')

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_api_error_loading_screening_shows_message(self):
        self.mock_get_screening.side_effect = services.CinemaAPIError('offline')

        with self.assertLogs('cinema.views', level='WARNING'):
            response = self.client.get(self.url)

        self.assertContains(response, 'alert-danger', status_code=503)

    def test_confirmation_without_booking_redirects_home(self):
        response = self.client.get(reverse('cinema:booking_success'))

        self.assertRedirects(response, reverse('cinema:home'), fetch_redirect_response=False)
