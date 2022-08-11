import json
import uuid
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from requests import Session

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.dcim.api.serializers import SiteSerializer
from nautobot.dcim.models import Site
from nautobot.dcim.models.sites import Region
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Webhook
from nautobot.extras.models.statuses import Status
from nautobot.extras.tasks import process_webhook
from nautobot.extras.utils import generate_signature
from nautobot.utilities.testing import APITestCase
from nautobot.utilities.utils import get_changes_for_model


User = get_user_model()


class WebhookTest(APITestCase):
    @classmethod
    def setUpTestData(cls):

        site_ct = ContentType.objects.get_for_model(Site)
        MOCK_URL = "http://localhost/"
        MOCK_SECRET = "LOOKATMEIMASECRETSTRING"

        webhooks = (
            Webhook.objects.create(
                name="Site Create Webhook",
                type_create=True,
                payload_url=MOCK_URL,
                secret=MOCK_SECRET,
                additional_headers="X-Foo: Bar",
            ),
        )
        for webhook in webhooks:
            webhook.content_types.set([site_ct])

        cls.active_status = Status.objects.get_for_model(Site).get(slug="active")
        cls.planned_status = Status.objects.get_for_model(Site).get(slug="planned")
        cls.region_one = Region.objects.create(name="Region One", slug="region-one")
        cls.region_two = Region.objects.create(name="Region Two", slug="region-two")

    def test_webhooks_process_webhook_on_update(self):
        """
        Mock a Session.send to inspect the result of `process_webhook()`.
        Note that process_webhook is called directly, not via a celery task.
        """

        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):
            """
            A mock implementation of Session.send() to be used for testing.
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
            self.assertEqual(body["username"], "nautobotuser")
            self.assertEqual(body["request_id"], str(request_id))
            self.assertEqual(body["data"]["name"], "Site Update")
            self.assertEqual(body["data"]["status"]["value"], self.planned_status.slug)
            self.assertEqual(body["data"]["region"]["slug"], self.region_two.slug)
            self.assertEqual(body["snapshots"]["prechange"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["prechange"]["status"]["value"], self.active_status.slug)
            self.assertEqual(body["snapshots"]["prechange"]["region"]["slug"], self.region_one.slug)
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Site Update")
            self.assertEqual(body["snapshots"]["postchange"]["status"]["value"], self.planned_status.slug)
            self.assertEqual(body["snapshots"]["postchange"]["region"]["slug"], self.region_two.slug)
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Site Update")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            self.client.force_login(self.user)

            with web_request_context(self.user, change_id=request_id):
                site = Site(name="Site 1", slug="site-1", status=self.active_status, region=self.region_one)
                site.save()

                site.name = "Site Update"
                site.status = self.planned_status
                site.region = self.region_two
                site.save()

                serializer = SiteSerializer(site, context={"request": None})
                oc = get_changes_for_model(site).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Site._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    def test_webhooks_snapshot_on_create(self):
        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):
            # Validate the outgoing request body
            body = json.loads(request.body)
            self.assertEqual(body["data"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["prechange"], None)
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["differences"]["removed"], None)
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Site 1")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            with web_request_context(self.user, change_id=request_id):
                site = Site(name="Site 1", slug="site-1")
                site.save()

                serializer = SiteSerializer(site, context={"request": None})
                oc = get_changes_for_model(site).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Site._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    def test_webhooks_snapshot_on_delete(self):
        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):
            # Validate the outgoing request body
            body = json.loads(request.body)
            self.assertEqual(body["data"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["prechange"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["postchange"], None)
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["differences"]["added"], None)

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            with web_request_context(self.user, change_id=request_id):
                site = Site(name="Site 1", slug="site-1")
                site.save()

                # deepcopy instance state to be used by SiteSerializer and get_snapshots
                temp_site = deepcopy(site)
                site.delete()

                serializer = SiteSerializer(temp_site, context={"request": None})
                oc = get_changes_for_model(temp_site).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Site._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    @patch("nautobot.utilities.api.get_serializer_for_model")
    def test_webhooks_snapshot_without_model_api_serializer(self, get_serializer_for_model):
        def get_serializer(model_class):
            raise SerializerNotFound

        get_serializer_for_model.side_effect = get_serializer

        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):

            # Validate the outgoing request body
            body = json.loads(request.body)

            self.assertEqual(body["snapshots"]["prechange"]["status"], str(self.active_status.id))
            self.assertEqual(body["snapshots"]["prechange"]["region"], str(self.region_one.id))
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Site Update")
            self.assertEqual(body["snapshots"]["postchange"]["status"], str(self.planned_status.id))
            self.assertEqual(body["snapshots"]["postchange"]["region"], str(self.region_two.id))
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Site 1")
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Site Update")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        with patch.object(Session, "send", mock_send):
            self.client.force_login(self.user)

            with web_request_context(self.user, change_id=request_id):
                site = Site(name="Site 1", slug="site-1", status=self.active_status, region=self.region_one)
                site.save()

                site.name = "Site Update"
                site.status = self.planned_status
                site.region = self.region_two
                site.save()

                serializer = SiteSerializer(site, context={"request": None})
                oc = get_changes_for_model(site).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Site._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    def test_webhook_render_body_with_utf8(self):
        self.assertEqual(Webhook().render_body({"utf8": "I am UTF-8! 😀"}), '{"utf8": "I am UTF-8! 😀"}')
