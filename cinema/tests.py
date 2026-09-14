from unittest.mock import Mock, patch

import requests
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse

from . import services

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


class ServicesTests(SimpleTestCase):
    @patch('cinema.services.requests.get')
    def test_get_films_returns_json(self, mock_get):
        mock_get.return_value = Mock(status_code=200, ok=True, json=Mock(return_value=[FILM]))

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
        mock_get.return_value = Mock(status_code=404, ok=False)

        with self.assertRaises(services.NotFoundError):
            services.get_films()


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
