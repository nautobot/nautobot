import json
import uuid
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from requests import Session

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.testing import APITestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.api.serializers import LocationSerializer
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Webhook
from nautobot.extras.models.statuses import Status
from nautobot.extras.tasks import process_webhook
from nautobot.extras.utils import generate_signature


User = get_user_model()


class WebhookTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get_for_model(Location)
        MOCK_URL = "http://localhost/"
        MOCK_SECRET = "LOOKATMEIMASECRETSTRING"

        webhooks = (
            Webhook.objects.create(
                name="Location Create Webhook",
                type_create=True,
                payload_url=MOCK_URL,
                secret=MOCK_SECRET,
                additional_headers="X-Foo: Bar",
            ),
        )
        for webhook in webhooks:
            webhook.content_types.set([location_ct])

        cls.statuses = Status.objects.get_for_model(Location)

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
            self.assertEqual(body["model"], "location")
            self.assertEqual(body["username"], "nautobotuser")
            self.assertEqual(body["request_id"], str(request_id))
            self.assertEqual(body["data"]["name"], "Location Update")
            self.assertEqual(body["data"]["status"]["name"], self.statuses[1].name)
            self.assertEqual(body["snapshots"]["prechange"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["prechange"]["status"]["name"], self.statuses[0].name)
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Location Update")
            self.assertEqual(body["snapshots"]["postchange"]["status"]["name"], self.statuses[1].name)
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Location Update")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            self.client.force_login(self.user)

            with web_request_context(self.user, change_id=request_id):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", status=self.statuses[0], location_type=location_type)
                location.save()

                location.name = "Location Update"
                location.status = self.statuses[1]
                location.save()

                serializer = LocationSerializer(location, context={"request": None, "depth": 1})
                oc = get_changes_for_model(location).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Location._meta.model_name,
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
            self.assertEqual(body["data"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["prechange"], None)
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["differences"]["removed"], None)
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Location 1")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            with web_request_context(self.user, change_id=request_id):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", location_type=location_type, status=self.statuses[0])
                location.save()

                serializer = LocationSerializer(location, context={"request": None})
                oc = get_changes_for_model(location).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Location._meta.model_name,
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
            self.assertEqual(body["data"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["prechange"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["postchange"], None)
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["differences"]["added"], None)

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        # Patch the Session object with our mock_send() method, then process the webhook for sending
        with patch.object(Session, "send", mock_send):
            with web_request_context(self.user, change_id=request_id):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", location_type=location_type, status=self.statuses[0])
                location.save()

                # deepcopy instance state to be used by LocationSerializer and get_snapshots
                temp_location = deepcopy(location)
                location.delete()

                serializer = LocationSerializer(temp_location, context={"request": None})
                oc = get_changes_for_model(temp_location).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Location._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    @patch("nautobot.core.api.utils.get_serializer_for_model")
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

            self.assertEqual(body["snapshots"]["prechange"]["status"], str(self.statuses[0].id))
            self.assertEqual(body["snapshots"]["postchange"]["name"], "Location Update")
            self.assertEqual(body["snapshots"]["postchange"]["status"], str(self.statuses[1].id))
            self.assertEqual(body["snapshots"]["differences"]["removed"]["name"], "Location 1")
            self.assertEqual(body["snapshots"]["differences"]["added"]["name"], "Location Update")

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

        with patch.object(Session, "send", mock_send):
            self.client.force_login(self.user)

            with web_request_context(self.user, change_id=request_id):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", status=self.statuses[0], location_type=location_type)
                location.save()

                location.name = "Location Update"
                location.status = self.statuses[1]
                location.save()

                serializer = LocationSerializer(location, context={"request": None})
                oc = get_changes_for_model(location).first()
                snapshots = oc.get_snapshots()

                process_webhook(
                    webhook.pk,
                    serializer.data,
                    Location._meta.model_name,
                    ObjectChangeActionChoices.ACTION_CREATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    def test_webhook_render_body_with_utf8(self):
        self.assertEqual(Webhook().render_body({"utf8": "I am UTF-8! 😀"}), '{"utf8": "I am UTF-8! 😀"}')
