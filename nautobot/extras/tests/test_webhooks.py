import json
import uuid
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from requests import Session

from nautobot.dcim.api.serializers import SiteSerializer
from nautobot.dcim.models import Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import Webhook
from nautobot.extras.tasks import process_webhook
from nautobot.extras.utils import generate_signature
from nautobot.utilities.testing import APITestCase


class WebhookTest(APITestCase):
    @classmethod
    def setUpTestData(cls):

        site_ct = ContentType.objects.get_for_model(Site)
        DUMMY_URL = "http://localhost/"
        DUMMY_SECRET = "LOOKATMEIMASECRETSTRING"

        webhooks = (
            Webhook.objects.create(
                name="Site Create Webhook",
                type_create=True,
                payload_url=DUMMY_URL,
                secret=DUMMY_SECRET,
                additional_headers="X-Foo: Bar",
            ),
        )
        for webhook in webhooks:
            webhook.content_types.set([site_ct])

    def test_webhooks_process_webhook(self):
        """
        Mock a Session.send to inspect the result of `process_webhook()`.
        Note that process_webhook is called directly, not via a celery task.
        """

        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        def dummy_send(_, request, **kwargs):
            """
            A dummy implementation of Session.send() to be used for testing.
            Always returns a 200 HTTP response.
            """
            signature = generate_signature(request.body, webhook.secret)

            # Validate the outgoing request headers
            self.assertEqual(request.headers["Content-Type"], webhook.http_content_type)
            self.assertEqual(request.headers["X-Hook-Signature"], signature)
            self.assertEqual(request.headers["X-Foo"], "Bar")

            # Validate the outgoing request body
            body = json.loads(request.body)
            self.assertEqual(body["event"], "created")
            self.assertEqual(body["timestamp"], timestamp)
            self.assertEqual(body["model"], "site")
            self.assertEqual(body["username"], "testuser")
            self.assertEqual(body["request_id"], str(request_id))
            self.assertEqual(body["data"]["name"], "Site 1")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our dummy_send() method, then process the webhook for sending
        with patch.object(Session, "send", dummy_send):
            site = Site.objects.create(name="Site 1", slug="site-1")
            serializer_context = {
                "request": None,
            }
            serializer = SiteSerializer(site, context=serializer_context)

            process_webhook(
                webhook.pk,
                serializer.data,
                Site._meta.model_name,
                ObjectChangeActionChoices.ACTION_CREATE,
                timestamp,
                self.user.username,
                request_id,
            )
