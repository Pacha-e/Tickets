from unittest import mock

from django.test import RequestFactory, TestCase

from .views import health


class HealthViewTests(TestCase):
    def test_health_ok(self):
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    def test_health_error(self):
        request = RequestFactory().get('/health')
        with mock.patch('config.views.connection.cursor', side_effect=Exception('db down')):
            response = health(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn(b'db down', response.content)
