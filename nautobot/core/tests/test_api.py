import json

from django.urls import reverse

from nautobot.utilities.testing import APITestCase


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)

    def test_status(self):
        url = reverse("api-status")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)

    def test_non_existent_resource(self):
        url = reverse("api-root")
        response = self.client.get(f"{url}/non-existent-resource-url/", **self.header)
        self.assertEqual(response.status_code, 404)
        response_json = json.loads(response.content)
        self.assertEqual(response_json, {"detail": "Not found."})
