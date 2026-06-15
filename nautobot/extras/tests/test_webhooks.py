from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
import requests
from requests import Session

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.testing import APITestCase, TestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.api.serializers import LocationSerializer
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Tag, Webhook
from nautobot.extras.models.statuses import Status
from nautobot.extras.registry import registry
from nautobot.extras.tasks import _send_webhook_request_pinned, process_webhook
from nautobot.extras.utils import generate_signature
from nautobot.extras.webhooks import validate_webhook_url, validate_webhook_url_format

User = get_user_model()


class WebhookTest(APITestCase):
    def setUp(self):
        super().setUp()
        location_ct = ContentType.objects.get_for_model(Location)
        # https://8.8.8.8/ skips DNS resolution (IP literal), isn't in any block-list, and uses HTTPS with
        # verification (the default), so the worker takes the requests.Session.send path that these tests mock.
        # No actual network traffic occurs because Session.send is patched.
        MOCK_URL = "https://8.8.8.8/"
        MOCK_SECRET = "LOOKATMEIMASECRETSTRING"  # noqa: S105  # hardcoded-password-string -- OK as this is test code

        webhooks = (
            Webhook.objects.create(
                name="Location Create Webhook",
                type_create=True,
                payload_url=MOCK_URL,
                secret=MOCK_SECRET,
                additional_headers="X-Foo: Bar",
            ),
            Webhook.objects.create(
                name="Location Update Webhook",
                type_update=True,
                payload_url=MOCK_URL,
                secret=MOCK_SECRET,
                additional_headers="X-Foo: Baz",
            ),
            Webhook.objects.create(
                name="Location Delete Webhook",
                type_delete=True,
                payload_url=MOCK_URL,
                secret=MOCK_SECRET,
                additional_headers="X-Foo: Bat",
            ),
        )
        for webhook in webhooks:
            webhook.content_types.set([location_ct])

        self.statuses = Status.objects.get_for_model(Location)

    def test_webhooks_process_webhook_on_update(self):
        """
        Mock a Session.send to inspect the result of `process_webhook()`.
        Note that process_webhook is called directly, not via a celery task.
        """

        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_update=True)
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
            self.assertEqual(request.headers["X-Foo"], "Baz")

            # Validate the outgoing request body
            body = json.loads(request.body)
            self.assertEqual(body["event"], "updated")
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

            # create the object to be updated in a separate context
            with web_request_context(self.user):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", status=self.statuses[0], location_type=location_type)
                location.save()

            with web_request_context(self.user, change_id=request_id):
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
                    ObjectChangeActionChoices.ACTION_UPDATE,
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
        webhook = Webhook.objects.get(type_delete=True)
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):
            signature = generate_signature(request.body, webhook.secret)

            # Validate the outgoing request headers
            self.assertEqual(request.headers["Content-Type"], webhook.http_content_type)
            self.assertEqual(request.headers["X-Hook-Signature"], signature)
            self.assertEqual(request.headers["X-Foo"], "Bat")

            # Validate the outgoing request body
            body = json.loads(request.body)
            self.assertEqual(body["event"], "deleted")
            self.assertEqual(body["timestamp"], timestamp)
            self.assertEqual(body["model"], "location")
            self.assertEqual(body["username"], "nautobotuser")
            self.assertEqual(body["request_id"], str(request_id))
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
                    ObjectChangeActionChoices.ACTION_DELETE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    @patch("nautobot.core.api.utils.get_serializer_for_model")
    def test_webhooks_snapshot_without_model_api_serializer(self, mock_get_serializer_for_model):
        def get_serializer(model_class):
            raise SerializerNotFound

        mock_get_serializer_for_model.side_effect = get_serializer

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

            # create the object to be updated in a separate context
            with web_request_context(self.user):
                location_type = LocationType.objects.get(name="Campus")
                location = Location(name="Location 1", status=self.statuses[0], location_type=location_type)
                location.save()

            with web_request_context(self.user, change_id=request_id):
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
                    ObjectChangeActionChoices.ACTION_UPDATE,
                    timestamp,
                    self.user.username,
                    request_id,
                    snapshots,
                )

    def test_webhook_render_body_with_utf8(self):
        self.assertEqual(Webhook().render_body({"utf8": "I am UTF-8! 😀"}), '{"utf8": "I am UTF-8! 😀"}')

    def test_webhook_body_template_is_used(self):
        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        webhook.body_template = '{"message": "{{ event }}"}'
        webhook.validated_save()
        timestamp = str(timezone.now())

        def mock_send(_, request, **kwargs):
            # Validate the outgoing request body
            body = json.loads(request.body)

            self.assertEqual(body, {"message": "created"})

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

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

    def test_process_webhook_does_not_follow_redirects(self):
        """SSRF defense: redirects must not be followed, since the SSRF block-list only validates the initial URL."""
        request_id = uuid.uuid4()
        webhook = Webhook.objects.get(type_create=True)
        timestamp = str(timezone.now())

        captured_kwargs = {}

        def mock_send(_, request, **kwargs):
            captured_kwargs.update(kwargs)

            class FakeResponse:
                ok = True
                status_code = 200

            return FakeResponse()

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

        self.assertEqual(captured_kwargs.get("allow_redirects"), False)

    def _process_webhook(self, webhook):
        """Drive `process_webhook` end-to-end with a freshly-saved Location object change."""
        request_id = uuid.uuid4()
        timestamp = str(timezone.now())
        with web_request_context(self.user, change_id=request_id):
            location_type = LocationType.objects.get(name="Campus")
            location = Location(name="Location SSRF", location_type=location_type, status=self.statuses[0])
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

    def test_process_webhook_uses_pinning_for_http(self):
        """HTTP webhooks go through the pinned-IP helper rather than `requests.Session.send`."""
        webhook = Webhook.objects.get(type_create=True)
        webhook.payload_url = "http://target.example/"
        webhook.save()

        with (
            patch("nautobot.extras.tasks._send_webhook_request_pinned") as mock_pinned,
            patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve,
        ):
            mock_resolve.return_value = [(2, 1, 6, "", ("8.8.8.8", 0))]
            mock_pinned.return_value.ok = True
            mock_pinned.return_value.status_code = 200
            self._process_webhook(webhook)

        # Second positional arg is the validated IP that came back from validate_webhook_url. The webhook fires
        # both via Location.save() (auto-enqueue) and via the explicit process_webhook call -- we only care that
        # the pinned helper handled it (not the requests.Session.send path).
        mock_pinned.assert_called()
        self.assertEqual(mock_pinned.call_args.args[1], "8.8.8.8")

    def test_process_webhook_raises_on_ssrf_blocked_url(self):
        """Worker re-validates: a webhook whose hostname resolves to a blocked IP at send time is rejected."""
        webhook = Webhook.objects.get(type_create=True)
        webhook.payload_url = "http://rebound.example/"
        webhook.save()

        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]
            with self.assertRaises(ValidationError):
                self._process_webhook(webhook)

    @patch("nautobot.extras.tasks.process_webhook.apply_async")
    def test_enqueue_webhooks(self, mock_async):
        request_id = uuid.uuid4()
        self.client.force_login(self.user)

        with web_request_context(self.user, change_id=request_id):
            location_type = LocationType.objects.get(name="Campus")
            location = Location(name="Location 1", location_type=location_type, status=self.statuses[0])
            location.save()

        mock_async.assert_called_once()
        args = mock_async.call_args[1]["args"]
        self.assertEqual(args[0], Webhook.objects.get(type_create=True).pk)
        self.assertEqual(args[1]["name"], "Location 1")
        self.assertEqual(args[2], "location")
        self.assertEqual(args[3], ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(args[5], self.user.username)
        self.assertEqual(args[6], request_id)
        self.assertEqual(args[7]["prechange"], None)
        self.assertEqual(args[7]["postchange"]["name"], "Location 1")
        self.assertEqual(args[7]["differences"]["removed"], None)
        self.assertEqual(args[7]["differences"]["added"]["name"], "Location 1")

    @patch("nautobot.extras.tasks.process_webhook.apply_async")
    def test_enqueue_webhooks_m2m_update(self, mock_async):
        """
        Make sure a webhook is enqueued if there's **only** an m2m change.

        https://github.com/nautobot/nautobot/issues/4327
        """
        request_id = uuid.uuid4()
        self.client.force_login(self.user)
        location_type = LocationType.objects.get(name="Campus")
        location = Location(name="Location 1", location_type=location_type, status=self.statuses[0])
        location.save()

        tag = Tag.objects.create(name="Tag 1")

        all_changes = get_changes_for_model(location)
        # Mimicking when all changes have been pruned via CHANGELOG_RETENTION / cleanup system Job
        all_changes.delete()

        with web_request_context(self.user, change_id=request_id):
            location.tags.add(tag)

        mock_async.assert_called_once()
        args = mock_async.call_args[1]["args"]
        self.assertEqual(args[0], Webhook.objects.get(type_update=True).pk)
        self.assertEqual(args[1]["name"], "Location 1")
        self.assertEqual(args[2], "location")
        self.assertEqual(args[3], ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(args[5], self.user.username)
        self.assertEqual(args[6], request_id)
        self.assertNotEqual(args[7], {})

    @patch("nautobot.extras.context_managers.enqueue_webhooks")
    def test_enqueue_webhooks_create_update(self, mock_enqueue_webhooks):
        """
        Make sure only one webhook is enqueued if there's a create and update in the same change context.
        """
        location_type = LocationType.objects.get(name="Campus")

        with web_request_context(self.user):
            location = Location(name="Location 1", location_type=location_type, status=self.statuses[0])
            location.save()
            location.description = "changed"
            location.save()

        all_changes = get_changes_for_model(location)
        self.assertEqual(all_changes.count(), 1)
        change = all_changes.first()
        mock_enqueue_webhooks.assert_called_once_with(change, snapshots=change.get_snapshots(), webhook_queryset=None)

    @unittest.expectedFailure  # IPAddressRange API endpoint not yet implemented
    def test_all_webhook_supported_models(self):
        """
        Assert that all models registered to support webhooks also support change logging
        and have an API serializer.
        """

        for app_label, models in registry["model_features"]["webhooks"].items():
            for model_name in models:
                model_class = apps.get_model(app_label, model_name)
                get_serializer_for_model(model_class)
                self.assertTrue(hasattr(model_class, "to_objectchange"))


class WebhookURLFormatValidatorTest(TestCase):
    """Tests for `validate_webhook_url_format` -- save-time validation, no DNS resolution."""

    def test_validate_format_default_policy(self):
        # (description, url, should_pass)
        cases = [
            # Empty / malformed
            ("empty url is rejected", "", False),
            ("invalid syntax is rejected", "not a url", False),
            # Scheme allow-list (default = http, https)
            ("file scheme is rejected", "file:///etc/passwd", False),
            ("ftp scheme is rejected", "ftp://example.com/", False),
            ("gopher scheme is rejected", "gopher://example.com/", False),
            ("javascript scheme is rejected", "javascript:alert(1)", False),
            ("http is accepted", "http://example.com/", True),
            ("https is accepted", "https://example.com/", True),
            # Built-in block-list (IP literals)
            ("loopback v4 is rejected", "http://127.0.0.1/", False),
            ("loopback v4 wider range is rejected", "http://127.5.6.7/", False),
            ("loopback v6 is rejected", "http://[::1]/", False),
            ("link-local v4 (cloud metadata) is rejected", "http://169.254.169.254/latest/meta-data/", False),
            ("link-local v6 is rejected", "http://[fe80::1]/", False),
            ("multicast v4 is rejected", "http://224.0.0.1/", False),
            ("broadcast is rejected", "http://255.255.255.255/", False),
            ("unspecified v4 is rejected", "http://0.0.0.0/", False),
            ("class-E reserved is rejected", "http://240.0.0.1/", False),
            # Public IP literals
            ("public v4 is accepted", "http://8.8.8.8/", True),
            ("public v6 is accepted", "http://[2001:4860:4860::8888]/", True),
            # RFC1918 private ranges -- intentionally NOT blocked by default
            ("RFC1918 10/8 is accepted by default", "http://10.0.0.1/", True),
            ("RFC1918 192.168/16 is accepted by default", "http://192.168.1.1/", True),
            ("RFC1918 172.16/12 is accepted by default", "http://172.16.0.1/", True),
            # Hostnames -- DNS deferred to worker, so any syntactically-valid hostname passes save-time
            ("hostname passes without DNS lookup", "http://internal-nonresolvable-host.example/", True),
        ]
        for desc, url, should_pass in cases:
            with self.subTest(desc):
                if should_pass:
                    validate_webhook_url_format(url)
                else:
                    with self.assertRaises(ValidationError):
                        validate_webhook_url_format(url)

    @override_settings(WEBHOOK_ALLOWED_SCHEMES=["ftp"])
    def test_allowed_schemes_setting_overrides_default(self):
        validate_webhook_url_format("ftp://example.com/")
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://example.com/")

    @override_settings(
        WEBHOOK_ALLOWED_HOSTS=["10.20.30.40"],
        WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS=["10.0.0.0/8"],
    )
    def test_allow_list_literal_bypasses_admin_extended_block_list(self):
        # Allow-list bypasses WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS for the matching host.
        validate_webhook_url_format("http://10.20.30.40/")
        # Other hosts in the same admin-extended range are still blocked.
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://10.99.99.99/")

    @override_settings(WEBHOOK_ALLOWED_HOSTS=[".internal.example.com"])
    def test_allow_list_subdomain_wildcard(self):
        validate_webhook_url_format("http://api.internal.example.com/")
        validate_webhook_url_format("http://internal.example.com/")

    @override_settings(WEBHOOK_ALLOWED_HOSTS=["127.0.0.1", "169.254.169.254", "*"])
    def test_allow_list_does_not_bypass_built_in_block_list(self):
        # Built-in block-list is enforced unconditionally; allow-listing (including wildcard) cannot expose
        # loopback / cloud-metadata IP literals at save time.
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://127.0.0.1/")
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://169.254.169.254/")

    @override_settings(WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS=["10.0.0.0/8", "fc00::/7"])
    def test_additional_blocked_networks_extends_built_in(self):
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://10.20.30.40/")
        # IPv6 ULA (fc00::/7) -- exercises the cross-family skip path: an IPv4 addr is matched only against
        # IPv4 networks in WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS, and vice versa.
        with self.assertRaises(ValidationError):
            validate_webhook_url_format("http://[fd00::1]/")
        validate_webhook_url_format("http://192.168.1.1/")
        validate_webhook_url_format("http://[2001:4860:4860::8888]/")


class WebhookURLSendTimeValidatorTest(TestCase):
    """Tests for `validate_webhook_url` -- send-time validation, includes DNS resolution."""

    def test_resolves_and_rejects_blocked_hostname(self):
        # Mock getaddrinfo to return a loopback address for an arbitrary hostname.
        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]
            with self.assertRaises(ValidationError):
                validate_webhook_url("http://attacker-controlled.example/")

    def test_resolves_and_accepts_public_hostname_returns_chosen_ip(self):
        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, "", ("8.8.8.8", 0))]
            self.assertEqual(validate_webhook_url("http://example.com/"), "8.8.8.8")

    def test_ip_literal_returns_literal(self):
        self.assertEqual(validate_webhook_url("http://8.8.8.8/"), "8.8.8.8")

    @override_settings(
        WEBHOOK_ALLOWED_HOSTS=["allowed.example"],
        WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS=["8.0.0.0/8"],
    )
    def test_allow_list_bypasses_admin_extended_at_send_time(self):
        # Allow-listed host whose DNS lands inside the admin-extended block-list passes (the allow-list overrides
        # the admin extension), and the validator returns the resolved IP for connection pinning.
        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, "", ("8.8.8.8", 0))]
            self.assertEqual(validate_webhook_url("http://allowed.example/"), "8.8.8.8")

    @override_settings(WEBHOOK_ALLOWED_HOSTS=["allowed.example", "*"])
    def test_allow_list_does_not_bypass_built_in_at_send_time(self):
        # Allow-list (and wildcard) cannot expose the built-in block-list at send time -- a hostname whose DNS
        # resolves to (e.g.) loopback is still rejected. This is the rebinding-into-metadata scenario.
        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, "", ("169.254.169.254", 0))]
            with self.assertRaises(ValidationError):
                validate_webhook_url("http://allowed.example/")

    def test_unresolvable_host_raises(self):
        import socket

        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.side_effect = socket.gaierror("nodename nor servname provided")
            with self.assertRaises(ValidationError):
                validate_webhook_url("http://nonexistent.example/")

    def test_rejects_when_any_resolved_address_is_blocked(self):
        # If a hostname resolves to *any* blocked address (DNS round-robin, dual-stack with a blocked v6, etc.),
        # we reject. This protects against partial-match bypasses.
        with patch("nautobot.extras.webhooks.socket.getaddrinfo") as mock_resolve:
            mock_resolve.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 0)),  # public
                (2, 1, 6, "", ("127.0.0.1", 0)),  # loopback -- should cause rejection
            ]
            with self.assertRaises(ValidationError):
                validate_webhook_url("http://mixed.example/")


class WebhookSendPinningTest(TestCase):
    """Tests for `_send_webhook_request_pinned` -- DNS-rebinding mitigation for HTTP and unverified HTTPS."""

    def _make_prepared(self, url, method="POST", body=b'{"ok": true}'):
        return requests.Request(method=method, url=url, data=body).prepare()

    def test_pinned_http_connects_to_validated_ip_with_original_host_header(self):
        prepared = self._make_prepared("http://attacker.example/path?x=1")

        with patch("nautobot.extras.tasks.urllib3.HTTPConnectionPool") as mock_pool_cls:
            mock_pool = mock_pool_cls.return_value
            mock_pool.urlopen.return_value.status = 200
            mock_pool.urlopen.return_value.headers = {}
            mock_pool.urlopen.return_value.data = b""
            _send_webhook_request_pinned(prepared, validated_ip="203.0.113.5")

        # Pool was constructed against the validated IP, not the hostname.
        self.assertEqual(mock_pool_cls.call_args.kwargs["host"], "203.0.113.5")
        self.assertEqual(mock_pool_cls.call_args.kwargs["port"], 80)
        # Host header preserved as the original hostname so vhost-routed receivers still match.
        urlopen_kwargs = mock_pool.urlopen.call_args.kwargs
        self.assertEqual(urlopen_kwargs["headers"]["Host"], "attacker.example")
        self.assertEqual(urlopen_kwargs["url"], "/path?x=1")
        self.assertFalse(urlopen_kwargs["redirect"])

    def test_pinned_https_unverified_sets_sni_to_hostname_and_disables_cert_check(self):
        prepared = self._make_prepared("https://internal.example/")

        with patch("nautobot.extras.tasks.urllib3.HTTPSConnectionPool") as mock_pool_cls:
            mock_pool = mock_pool_cls.return_value
            mock_pool.urlopen.return_value.status = 200
            mock_pool.urlopen.return_value.headers = {}
            mock_pool.urlopen.return_value.data = b""
            _send_webhook_request_pinned(prepared, validated_ip="10.20.30.40")

        kwargs = mock_pool_cls.call_args.kwargs
        self.assertEqual(kwargs["host"], "10.20.30.40")
        self.assertEqual(kwargs["port"], 443)
        # SNI/TLS hostname is the original hostname so SNI-routed receivers continue to work.
        self.assertEqual(kwargs["server_hostname"], "internal.example")
        self.assertEqual(kwargs["cert_reqs"], "CERT_NONE")

    def test_pinned_uses_explicit_port_when_present(self):
        prepared = self._make_prepared("http://attacker.example:8080/")

        with patch("nautobot.extras.tasks.urllib3.HTTPConnectionPool") as mock_pool_cls:
            mock_pool = mock_pool_cls.return_value
            mock_pool.urlopen.return_value.status = 200
            mock_pool.urlopen.return_value.headers = {}
            mock_pool.urlopen.return_value.data = b""
            _send_webhook_request_pinned(prepared, validated_ip="203.0.113.5")

        self.assertEqual(mock_pool_cls.call_args.kwargs["port"], 8080)
        # Non-default port is included in the Host header.
        self.assertEqual(mock_pool.urlopen.call_args.kwargs["headers"]["Host"], "attacker.example:8080")
