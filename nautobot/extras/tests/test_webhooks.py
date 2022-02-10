import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from requests import Session

from nautobot.dcim.api.serializers import SiteSerializer
from nautobot.dcim.models import Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import Webhook, ObjectChange
from nautobot.extras.tasks import process_webhook
from nautobot.extras.utils import generate_signature, get_instance_snapshot
from nautobot.utilities.testing import APITestCase


User = get_user_model()


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
            self.assertEqual(body["data"]["name"], "Site Update")
            self.assertEqual(body["snapshot"]["prev_change"]["name"], "Site 1")
            self.assertEqual(body["snapshot"]["post_change"]["name"], "Site Update")
            self.assertEqual(body["snapshot"]["differences"]["removed"]["name"], "Site 1")
            self.assertEqual(body["snapshot"]["differences"]["added"]["name"], "Site Update")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our dummy_send() method, then process the webhook for sending
        with patch.object(Session, "send", dummy_send):
            users = User.objects.create(username="user1")

            site_name = "Site 1"
            site = Site.objects.create(name=site_name, slug="site-1")
            # store object changes
            ObjectChange.objects.create(
                user=users,
                user_name=users.username,
                request_id=uuid.uuid4(),
                action=ObjectChangeActionChoices.ACTION_CREATE,
                changed_object=site,
                object_repr=str(site),
                object_data={"name": site_name, "slug": site.slug},
            )

            # make an update to site
            site.name = "Site Update"
            site.save()
            # store object changes
            ObjectChange.objects.create(
                user=users,
                user_name=users.username,
                request_id=uuid.uuid4(),
                action=ObjectChangeActionChoices.ACTION_UPDATE,
                changed_object=site,
                object_repr=str(site),
                object_data={"name": site.name, "slug": site.slug},
            )

            serializer_context = {"request": None}
            serializer = SiteSerializer(site, context=serializer_context)
            snapshot = get_instance_snapshot(site, ObjectChangeActionChoices.ACTION_UPDATE)

            process_webhook(
                webhook.pk,
                serializer.data,
                snapshot,
                Site._meta.model_name,
                ObjectChangeActionChoices.ACTION_CREATE,
                timestamp,
                self.user.username,
                request_id,
            )
