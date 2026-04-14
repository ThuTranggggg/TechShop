from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_health_endpoint_returns_success_payload(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success"], True)
        self.assertEqual(response.json()["message"], "OK")

    def test_schema_endpoint_is_exposed(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, 200)
