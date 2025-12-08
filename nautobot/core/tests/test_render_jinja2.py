import re
from unittest import skip
from unittest.mock import patch
import uuid

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from nautobot.core import testing
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.templatetags.helpers import humanize_speed
from nautobot.dcim import choices as dcim_choices, models as dcim_models
from nautobot.extras import models as extras_models
from nautobot.ipam import models as ipam_models
from nautobot.tenancy import models as tenancy_models


class RenderJinjaTemplateTestMixin:
    def render_jinja_template(self, template_code, content_type, object_uuid, **extra_payload):
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": template_code,
                "content_type": content_type,
                "object_uuid": object_uuid,
                **extra_payload,
            },
            format="json",
            **self.header,
        )

        return response


class JinjaSuccessfulTemplateTestMixin(RenderJinjaTemplateTestMixin):
    def render_jinja_template_and_assert_success(self, template_code, content_type, object_uuid, **extra_payload):
        response = super().render_jinja_template(template_code, content_type, object_uuid, **extra_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("rendered_template", response.data)

        return response.data


class RenderJinjaBasicRequestTest(testing.APITestCase):
    """Basic tests to ensure the utterly invalid requests are rejected."""

    def test_render_jinja_template_validation_missing_both(self):
        """Test validation error when neither context nor object fields provided."""
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {"template_code": "{{ obj.name }}"},  # Only template, no context or object
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Either 'context' or object selection", str(response.data))

    def test_render_jinja_template_validation_both_provided(self):
        """Test validation error when both context and object fields provided."""
        self.add_permissions("dcim.view_location")

        location = dcim_models.Location.objects.first()
        content_type = ContentType.objects.get_for_model(dcim_models.Location)
        for label, selector in [
            ("string", {"content_type": "dcim.location"}),
            ("id", {"content_type_id": content_type.pk}),
        ]:
            with self.subTest(selector=label):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": "{{ obj.name }}",
                        "context": {"test": "data"},  # Both context AND object fields
                        "object_uuid": str(location.pk),
                        **selector,
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("Cannot specify both", str(response.data))


class RenderJinjaViewJSONContextTest(testing.APITestCase):
    """Tests for the RenderJinjaView with JSON context."""

    def test_render_jinja_template_with_json_context(self):
        """
        Test rendering a valid Jinja template with JSON context.
        """
        interfaces = ["Ethernet1/1", "Ethernet1/2", "Ethernet1/3"]

        template_code = "\n".join(
            [
                r"{% for int in interfaces -%}",
                r"interface {{ int }}",
                r"  speed {{ 1000000000|humanize_speed }}",
                r"  duplex full",
                r"{% endfor %}",
            ]
        )

        expected_response = "\n".join(
            [
                "\n".join(
                    [
                        f"interface {int}",
                        f"  speed {humanize_speed(1000000000)}",
                        r"  duplex full",
                    ]
                )
                for int in interfaces
            ]
            + [""]  # Add an extra newline at the end because jinja whitespace control is "fun"
        )

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": template_code,
                "context": {"interfaces": interfaces},
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSequenceEqual(
            list(response.data.keys()),
            ["rendered_template", "rendered_template_lines", "template_code", "context"],
        )
        self.assertEqual(response.data["rendered_template"], expected_response)
        self.assertEqual(response.data["rendered_template_lines"], expected_response.split("\n"))

    def test_render_jinja_template_json_reserved_keys_edge_cases(self):
        """Test reserved keys with user data in JSON mode."""

        test_cases = [
            # obj key with user data (bring this back)
            {
                "name": "obj_user_data",
                "context": {"obj": {"name": "test-object"}},
                "template": "{{ obj.name }}",
                "expected": "test-object",
            },
            # user key with user data
            {
                "name": "user_user_data",
                "context": {"user": {"username": "john", "role": "admin"}},
                "template": "{{ user.username }}-{{ user.role }}",
                "expected": "john-admin",
            },
            # perms as different types
            {
                "name": "perms_list",
                "context": {"perms": ["admin", "user"]},
                "template": "{{ perms|join(',') }}",
                "expected": "admin,user",
            },
            {"name": "perms_string", "context": {"perms": "admin"}, "template": "{{ perms }}", "expected": "admin"},
            {
                "name": "perms_dict",
                "context": {"perms": {"role": "admin", "level": 5}},
                "template": "{{ perms.role }}-{{ perms.level }}",
                "expected": "admin-5",
            },
            # debug with user data
            {
                "name": "debug_user_data",
                "context": {"debug": {"level": "verbose", "trace": True}},
                "template": "{{ debug.level }}-{{ debug.trace }}",
                "expected": "verbose-True",
            },
            # request key preservation
            {
                "name": "request_user_data",
                "context": {"request": {"method": "POST", "authenticated": True}},
                "template": "{{ request.method }}:{{ request.authenticated }}",
                "expected": "POST:True",
            },
            # Mixed reserved and custom keys
            {
                "name": "mixed_keys",
                "context": {
                    "obj": {"id": 123},
                    "custom": {"data": "value"},
                    "perms": ["read"],
                    "config": {"timeout": 30},
                },
                "template": "{{ obj.id }}-{{ custom.data }}-{{ perms[0] }}-{{ config.timeout }}",
                "expected": "123-value-read-30",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": case["template"],
                        "context": case["context"],
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["rendered_template"], case["expected"])

    def test_render_jinja_template_context_serialization_edge_cases(self):
        """Test edge cases for context serialization."""

        test_cases = [
            # None values in reserved keys
            {
                "name": "none_values",
                "context": {"obj": None, "debug": None},
                "template": "{{ obj is none }}-{{ debug is none }}",
                "expected": "True-True",
            },
            # Falsy but valid values
            {
                "name": "falsy_values",
                "context": {"perms": [], "debug": False, "obj": {}},
                "template": "{{ perms|length }}-{{ debug }}-{{ obj|length }}",
                "expected": "0-False-0",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": case["template"],
                        "context": case["context"],
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["rendered_template"], case["expected"])

    def test_render_jinja_template_with_empty_context(self):
        """Test that empty context {} is valid for static templates."""
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "Hello world",  # Static template, no variables
                "context": {},  # Empty but present
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rendered_template"], "Hello world")
        self.assertEqual(response.data["context"], {})

    def test_render_jinja_validation_template_rejects_context_with_partial_object_fields(self):
        """Providing context together with either content_type or object_uuid should raise a validation error."""
        # Use a real object for a valid UUID
        location = dcim_models.Location.objects.first()
        content_type = ContentType.objects.get_for_model(dcim_models.Location)

        # Case 1: context + content_type only (string and id variants)
        for label, selector in [
            ("string", {"content_type": "dcim.location"}),
            ("id", {"content_type_id": content_type.pk}),
        ]:
            with self.subTest(selector=label):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": "Hello",
                        "context": {"foo": "bar"},
                        **selector,
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("Cannot specify both 'context' and partial object selection", str(response.data))

        # Case 2: context + object_uuid only
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "Hello",
                "context": {"foo": "bar"},
                "object_uuid": str(location.pk),
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot specify both 'context' and partial object selection", str(response.data))


class RenderJinjaTemplateObjectContextTest(testing.APITestCase):
    """Test cases for RenderJinjaView with object context."""

    def test_render_jinja_template_with_object_context(self):
        """
        Test rendering a valid Jinja template with object context across different object types.
        """
        self.add_permissions("dcim.view_location")
        self.add_permissions("dcim.view_device")
        self.add_permissions("dcim.view_interface")

        test_cases = [
            ("dcim.location", dcim_models.Location.objects.first(), "Location: {{ obj.name }}"),
            ("dcim.device", dcim_models.Device.objects.first(), "Device: {{ obj.name }}"),
            ("dcim.interface", dcim_models.Interface.objects.first(), "Interface: {{ obj.name }}"),
        ]

        for content_type_str, obj, template_code in test_cases:
            content_type = ContentType.objects.get_for_model(type(obj))
            for label, selector in [
                ("string", {"content_type": content_type_str}),
                ("id", {"content_type_id": content_type.pk}),
            ]:
                with self.subTest(content_type=content_type_str, selector=label):
                    response = self.client.post(
                        reverse("core-api:render_jinja_template"),
                        {
                            "template_code": template_code,
                            "object_uuid": str(obj.pk),
                            **selector,
                        },
                        format="json",
                        **self.header,
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertSequenceEqual(
                        list(response.data.keys()),
                        ["rendered_template", "rendered_template_lines", "template_code", "context"],
                    )

                    expected_response = f"{content_type.model.title()}: {obj.name}"
                    self.assertEqual(response.data["rendered_template"], expected_response)
                    self.assertEqual(response.data["rendered_template_lines"], expected_response.split("\n"))

                    # Verify context contains expected object data
                    # self.assertIn("obj", response.data["context"])

    @skip("Context data for object context is currently being added to the response")
    def test_render_jinja_template_object_context_variables(self):
        """
        Test that object context includes all expected variables.
        """
        self.add_permissions("dcim.view_location")

        # Use existing location from test database
        location = dcim_models.Location.objects.first()

        template_code = "\n".join(
            [
                "Object: {{ obj.name }}",
            ]
        )

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": template_code,
                "content_type": "dcim.location",
                "object_uuid": str(location.pk),
            },
            format="json",
            **self.header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify context contains all expected variables
        context = response.data["context"]
        self.assertIn("obj", context)

        # Verify context structure
        self.assertEqual(context["obj"]["id"], str(location.pk))
        self.assertEqual(context["obj"]["name"], location.name)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_render_jinja_template_without_object_view_permission(self):
        """User lacking view permission on the object should not be able to render it."""
        location = dcim_models.Location.objects.first()

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "{{ obj.name }}",
                "content_type": "dcim.location",
                "object_uuid": str(location.pk),
            },
            format="json",
            **self.header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Object not found", str(response.data))

    def test_render_jinja_template_validation_incomplete_object(self):
        """Test validation when object mode fields are incomplete."""
        self.add_permissions("dcim.view_location")

        test_cases = [
            {"content_type": "dcim.location"},  # Missing object_uuid
            {"object_uuid": str(uuid.uuid4())},  # Missing content_type
        ]

        for data in test_cases:
            with self.subTest(data):
                data["template_code"] = "{{ obj.name }}"
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    data,
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("Either 'context' or object selection", str(response.data))

    def test_render_jinja_template_validation_empty_strings(self):
        """Test that validation properly handles empty strings and whitespace."""
        self.add_permissions("dcim.view_location")

        # Test cases that should be caught by field validation
        field_validation_cases = [
            {
                "data": {"content_type": "  ", "object_uuid": str(uuid.uuid4())},
                "expected_error": "Invalid value. Specify a content type",
                "description": "Whitespace-only content_type",
            },
            {
                "data": {"content_type": "dcim.location", "object_uuid": ""},
                "expected_error": "Must be a valid UUID",
                "description": "Empty object_uuid string",
            },
            {
                "data": {"content_type": "dcim.location", "object_uuid": "   "},
                "expected_error": "Must be a valid UUID",
                "description": "Whitespace-only object_uuid",
            },
        ]

        # Test cases that should be caught by our custom validation
        custom_validation_cases = [
            {
                "data": {"content_type": "", "object_uuid": str(uuid.uuid4())},
                "description": "Empty content_type string",
            },
        ]

        # Test field validation catches format/type issues
        for case in field_validation_cases:
            with self.subTest(description=case["description"]):
                case["data"]["template_code"] = "{{ obj.name }}"
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    case["data"],
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                # Field validation should catch these
                self.assertIn(case["expected_error"], str(response.data))

        # Test custom validation catches business logic issues
        for case in custom_validation_cases:
            with self.subTest(description=case["description"]):
                case["data"]["template_code"] = "{{ obj.name }}"
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    case["data"],
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                # Our validation should catch these as incomplete
                self.assertIn("Either 'context' or object selection", str(response.data))

    def test_render_jinja_template_validation_wrong_data_types(self):
        """Test that validation handles wrong data types appropriately."""
        self.add_permissions("dcim.view_location")

        # Field validation catches these
        field_validation_cases = [
            {
                "data": {"content_type": 123, "object_uuid": str(uuid.uuid4())},
                "expected_error": "Invalid value. Specify a content type",
                "description": "Integer content_type",
            },
            {
                "data": {"content_type": ["dcim.location"], "object_uuid": str(uuid.uuid4())},
                "expected_error": "Invalid value. Specify a content type",
                "description": "List content_type",
            },
            {
                "data": {"content_type": "dcim.location", "object_uuid": {}},
                "expected_error": "Must be a valid UUID",
                "description": "Dict object_uuid",
            },
        ]

        # Object lookup catches these (UUIDField converts integers to UUIDs)
        object_lookup_cases = [
            {
                "data": {"content_type": "dcim.location", "object_uuid": 123},
                "expected_error": "Object not found",
                "description": "Integer object_uuid (converted to valid UUID but object doesn't exist)",
            },
        ]

        # Test field validation
        for case in field_validation_cases:
            with self.subTest(description=case["description"]):
                case["data"]["template_code"] = "{{ obj.name }}"
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    case["data"],
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(case["expected_error"], str(response.data))

        # Test object lookup validation
        for case in object_lookup_cases:
            with self.subTest(description=case["description"]):
                case["data"]["template_code"] = "{{ obj.name }}"
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    case["data"],
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(case["expected_error"], str(response.data))

    def test_render_jinja_template_invalid_content_type(self):
        """Test error handling for invalid content types."""
        test_cases = {
            "invalid": "Invalid value. Specify a content type",  # Not app_label.model format
            "nonexistent.model": "Invalid content type: nonexistent.model",  # App doesn't exist
            "dcim.nonexistent": "Invalid content type: dcim.nonexistent",  # Model doesn't exist
        }

        for content_type, expected_error in test_cases.items():
            with self.subTest(content_type=content_type):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": "{{ obj.name }}",
                        "content_type": content_type,
                        "object_uuid": str(uuid.uuid4()),
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(expected_error, str(response.data))

    def test_render_jinja_template_rejects_both_content_type_and_id(self):
        """Submitting both content_type (string) and content_type_id (PK) should raise a validation error."""
        self.add_permissions("dcim.view_location")

        content_type = ContentType.objects.get_for_model(dcim_models.Location)
        location = dcim_models.Location.objects.first()

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "{{ obj.name }}",
                "content_type": f"{content_type.app_label}.{content_type.model}",
                "content_type_id": content_type.pk,
                "object_uuid": str(location.pk),
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("either 'content_type' or 'content_type_id'", str(response.data).lower())

    def test_render_jinja_template_model_class_none(self):
        """Test error handling when ContentType exists but model_class() returns None (stale content type)."""
        stale_ct = ContentType.objects.create(app_label="ghostapp", model="ghostmodel")

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "{{ obj.name }}",
                "content_type": f"{stale_ct.app_label}.{stale_ct.model}",
                "object_uuid": str(uuid.uuid4()),
            },
            format="json",
            **self.header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Model not found for ghostapp.ghostmodel", str(response.data))

    def test_render_jinja_template_nonexistent_object(self):
        """Test error handling for non-existent object UUID."""
        self.add_permissions("dcim.view_location")

        fake_uuid = str(uuid.uuid4())
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": "{{ obj.name }}",
                "content_type": "dcim.location",
                "object_uuid": fake_uuid,
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Object not found", str(response.data))

    def test_render_jinja_template_wrong_object_type(self):
        """Test error when valid content_type and UUID but UUID is for different object type."""
        self.add_permissions("dcim.view_device")

        location = dcim_models.Location.objects.first()
        content_type = ContentType.objects.get_for_model(dcim_models.Device)

        # Try to get a Device using a Location's UUID (string and id variants)
        for label, selector in [
            ("string", {"content_type": "dcim.device"}),
            ("id", {"content_type_id": content_type.pk}),
        ]:
            with self.subTest(selector=label):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": "{{ obj.name }}",
                        "object_uuid": str(location.pk),  # But using Location UUID
                        **selector,
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("Object not found", str(response.data))

    def test_render_jinja_template_failures(self):
        """
        Test rendering invalid Jinja templates.
        """
        test_data = [
            {
                "template_code": r"{% hello world %}",
                "error_msg": "Encountered unknown tag 'hello'.",
            },
            {
                "template_code": r"{{ hello world %}",
                "error_msg": "expected token 'end of print statement', got 'world'",
            },
        ]

        for data in test_data:
            with self.subTest(data):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": data["template_code"],
                        "context": {"foo": "bar"},
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertSequenceEqual(list(response.data.keys()), ["detail"])
                self.assertEqual(response.data["detail"], f"Failed to render Jinja template: {data['error_msg']}")


class RenderJinjaTemplateObjectContextPermissionsTest(JinjaSuccessfulTemplateTestMixin, testing.APITestCase):
    """Test case for the RenderJinjaTemplateObjectContextPermissionsView API view."""

    @classmethod
    def setUpTestData(cls):
        cls.device_empty_part_number = dcim_models.Device.objects.filter(device_type__part_number="").first()
        cls.device_with_part_number = dcim_models.Device.objects.exclude(device_type__part_number="").first()
        cls.ipaddress_status = extras_models.Status.objects.get_for_model(ipam_models.IPAddress).first()
        cls.prefix_status = extras_models.Status.objects.get_for_model(ipam_models.Prefix).first()
        location = dcim_models.Location.objects.first()

        rack_status = extras_models.Status.objects.get_for_model(dcim_models.Rack).first()
        cls.racks = []
        for i in range(2):
            cls.racks.append(
                dcim_models.Rack.objects.create(
                    name=f"RJinjaRack {i}",
                    facility_id=f"RJ-TEST-{i}",
                    location=location,
                    status=rack_status,
                )
            )
        cls.rack = cls.racks[0]

        cls.depth_test_device = dcim_models.Device.objects.filter(
            interfaces__ip_addresses__tenant__racks__isnull=False
        ).first()

        if cls.depth_test_device is None:
            cls.depth_test_device = dcim_models.Device.objects.filter(interfaces__isnull=False).first()

            if cls.depth_test_device is not None:
                interfaces = list(cls.depth_test_device.interfaces.all())
                if interfaces:
                    tenant, _ = tenancy_models.Tenant.objects.get_or_create(
                        name="Depth Test Tenant", defaults={"description": "Auto-generated for depth tests"}
                    )
                    if tenant.racks.count() == 0:
                        tenant.racks.set(cls.racks)

                    ip_candidates = list(
                        ipam_models.IPAddress.objects.filter(interfaces__isnull=True)[: len(interfaces)]
                    )
                    if len(ip_candidates) >= len(interfaces):
                        for iface, ip in zip(interfaces, ip_candidates):
                            ip.tenant = tenant
                            ip.save()
                            ip.interfaces.add(iface)
                    else:
                        cls.depth_test_device = None

        if cls.depth_test_device is None:
            raise RuntimeError("Unable to prepare device with IP hierarchy for depth tests")

    def test_object_will_not_render_without_permission(self):
        """Without the model permission, object will not render."""

        template_code = "Device: {{ obj.name }}"

        response = super().render_jinja_template(template_code, "dcim.device", str(self.device_with_part_number.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Object not found", str(response.data))

    def test_object_basic_attributes_visible_with_permission(self):
        """With the model permission, object renders and attributes are visible."""
        self.add_permissions("dcim.view_device")

        response = self.render_jinja_template_and_assert_success(
            "Device: {{ obj.name }}", "dcim.device", str(self.device_with_part_number.pk)
        )
        self.assertIn(self.device_with_part_number.name, response["rendered_template"])

    #
    # Tests which verify object fk brief info is available when user has perm on obj but not on the fk model
    def test_object_fk_brief_renders_when_missing_related_permission(self):
        """Forward FK should render only brief info when user lacks the related model permission."""
        self.add_permissions("dcim.view_device")

        response = self.render_jinja_template_and_assert_success(
            "Device Type: {{ obj.device_type.display }}", "dcim.device", str(self.device_with_part_number.pk)
        )
        self.assertEqual(
            response["rendered_template"], f"Device Type: {self.device_with_part_number.device_type.display}"
        )

    def test_object_fk_full_does_not_render_when_missing_related_permission(self):
        """Forward FK should not render when user lacks the related model permission."""
        self.add_permissions("dcim.view_device")

        template_code_prefix = "Device Type Part Number:"
        template_code = template_code_prefix + " {{ obj.device_type.part_number }}"

        response = self.render_jinja_template_and_assert_success(
            template_code, "dcim.device", str(self.device_with_part_number.pk)
        )
        rendered = response["rendered_template"]
        self.assertIn(template_code_prefix, rendered)
        self.assertNotIn(self.device_with_part_number.device_type.part_number, rendered)
        self.assertNotIn("no such element", rendered)

    @override_settings(DEBUG=True)
    def test_object_fk_full_does_not_render_when_missing_related_permission_debug(self):
        """Forward FK should not render when user lacks the related model permission."""
        self.add_permissions("dcim.view_device")

        template_code_prefix = "Device Type Part Number:"
        template_code = template_code_prefix + " {{ obj.device_type.part_number }}"
        print(f"Part number: {self.device_with_part_number.device_type.part_number}")

        response = self.render_jinja_template_and_assert_success(
            template_code, "dcim.device", str(self.device_with_part_number.pk)
        )
        rendered = response["rendered_template"]
        self.assertIn(template_code_prefix, rendered)
        self.assertNotIn(self.device_with_part_number.device_type.part_number, rendered)
        self.assertIn("no such element", rendered)

    #
    # Verify object fk full info is available when user has perm on obj and fk model
    def test_object_fk_full_renders_with_related_permission(self):
        """Forward FK should render detailed info when user has the related model permission."""
        self.add_permissions("dcim.view_device")
        self.add_permissions("dcim.view_devicetype")

        template_code_prefix = "Device Type Part Number:"
        template_code = template_code_prefix + " {{ obj.device_type.part_number }}"

        response = self.render_jinja_template_and_assert_success(
            template_code, "dcim.device", str(self.device_with_part_number.pk)
        )
        rendered = response["rendered_template"]
        self.assertIn(template_code_prefix, rendered)
        self.assertIn(self.device_with_part_number.device_type.part_number, rendered)

    #
    # Verify relation model is not rendered when user lacks related model permission but has perm on obj
    def test_object_relation_brief_without_related_permission(self):
        """Reverse relations should not render when user lacks related model permission."""
        self.add_permissions("dcim.view_location")

        template_code = "{% for rack in obj.racks.all() %}{{ rack.name }} {% endfor %}"

        response = self.render_jinja_template_and_assert_success(
            template_code, "dcim.location", str(self.rack.location.pk)
        )
        self.assertEqual("", response["rendered_template"].strip())

    def test_object_relation_full_with_related_permission(self):
        """Reverse relations should render detailed info when user has related model permission."""
        permissions_list = [
            "dcim.view_location",
            "dcim.view_rack",
        ]
        self.add_permissions(*permissions_list)

        templates = {
            "name": "{% for rack in obj.racks.all() %}{{ rack.name }}{% endfor %}",
            "facility_id": "{% for rack in obj.racks.all() %}{{ rack.facility_id }}{% endfor %}",
        }

        for template_name, template_code in templates.items():
            with self.subTest(template_name=template_name):
                response = self.render_jinja_template_and_assert_success(
                    template_code, "dcim.location", str(self.rack.location.pk)
                )
                rendered = response["rendered_template"]

                for rack in self.racks:
                    attribute = getattr(rack, template_name)
                    self.assertIn(attribute, rendered)

    def test_zero_arg_method_accessible_with_permission(self):
        """Zero-arg helper method should be accessible when the user has permission."""
        self.add_permissions("dcim.view_device")

        templates = {
            "get_absolute_url": "{{ obj.get_absolute_url() }}",
            "has_computed_fields": "{{ obj.has_computed_fields() }}",
        }

        for method_name, template_code in templates.items():
            with self.subTest(method_name=method_name):
                response = self.render_jinja_template_and_assert_success(
                    template_code, "dcim.device", str(self.device_with_part_number.pk)
                )
                rendered = response["rendered_template"]
                #
                # Call the method and get the result
                value = getattr(self.device_with_part_number, method_name)()

                self.assertEqual(str(value), rendered)

    def test_depth_limits_rendered_attributes(self):
        """Depth alone should gate how far traversal can go when permissions allow."""
        self.add_permissions(
            "dcim.view_device",
            "dcim.view_interface",
            "ipam.view_ipaddress",
            "tenancy.view_tenant",
            "dcim.view_rack",
        )

        #
        # Scenarios
        #
        # Fields required for each scenario:
        # - name: The name of the scenario
        # - depth: The depth of the object graph to include in the template context
        # - template: The template code to render
        # - should_contain: A list of tokens that should be present in the rendered template
        # - should_not_contain: A list of tokens that should not be present in the rendered template
        scenarios = [
            {
                "name": "interfaces_only_depth0",
                "depth": 0,
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    iface: {{ iface.name }}
                    {% endfor %}
                """,
                "should_contain": ["iface:"],
                "should_not_contain": ["ip:", "tenant:", "rack:"],
            },
            {
                "name": "interfaces_and_ips_depth2",
                "depth": 2,
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    iface: {{ iface.name }}
                    {% for ip in iface.ip_addresses.all() %}
                        ip: {{ ip.address }}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["iface:", "ip:"],
                "should_not_contain": ["tenant:", "rack:"],
            },
            {
                "name": "tenant_depth3",
                "depth": 3,
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    {% for ip in iface.ip_addresses.all() %}
                        {% if ip.tenant %}
                            tenant: {{ ip.tenant.name }}
                        {% endif %}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["tenant:"],
                "should_not_contain": ["rack:"],
            },
            {
                "name": "rack_depth4",
                "depth": 4,
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    {% for ip in iface.ip_addresses.all() %}
                        {% if ip.tenant %}
                            {% for rack in ip.tenant.racks.all() %}
                                rack: {{ rack.name }}
                            {% endfor %}
                        {% endif %}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["rack:"],
                "should_not_contain": [],
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"], depth=scenario["depth"]):
                response = self.render_jinja_template_and_assert_success(
                    scenario["template"],
                    "dcim.device",
                    str(self.depth_test_device.pk),
                    depth=scenario["depth"],
                )
                rendered = response["rendered_template"]

                for token in scenario["should_contain"]:
                    self.assertIn(token, rendered)

                for token in scenario["should_not_contain"]:
                    self.assertNotIn(token, rendered)

    def test_depth_and_permissions_gate_visibility(self):
        """Permissions at each level should gate visibility even when depth is sufficient."""
        #
        # Scenarios
        #
        # Fields required for each scenario:
        # - name: The name of the scenario
        # - perms: A list of permissions to grant to the user
        # - template: The template code to render
        # - should_contain: A list of tokens that should be present in the rendered template
        # - should_not_contain: A list of tokens that should not be present in the rendered template
        scenarios = [
            {
                "name": "device_and_interface_only",
                "perms": ["dcim.view_device", "dcim.view_interface"],
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    iface: {{ iface.name }}
                    {% endfor %}
                """,
                "should_contain": ["iface:"],
                "should_not_contain": ["ip:", "tenant:", "rack:"],
            },
            {
                "name": "include_ip_permission",
                "perms": ["dcim.view_device", "dcim.view_interface", "ipam.view_ipaddress"],
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    {% for ip in iface.ip_addresses.all() %}
                        ip: {{ ip.address }}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["ip:"],
                "should_not_contain": ["tenant:", "rack:"],
            },
            {
                "name": "include_tenant_permission",
                "perms": [
                    "dcim.view_device",
                    "dcim.view_interface",
                    "ipam.view_ipaddress",
                    "tenancy.view_tenant",
                ],
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    {% for ip in iface.ip_addresses.all() %}
                        tenant: {{ ip.tenant.name }}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["tenant:"],
                "should_not_contain": ["rack:"],
            },
            {
                "name": "all_permissions",
                "perms": [
                    "dcim.view_device",
                    "dcim.view_interface",
                    "ipam.view_ipaddress",
                    "tenancy.view_tenant",
                    "dcim.view_rack",
                ],
                "template": """
                    {% for iface in obj.interfaces.all() %}
                    {% for ip in iface.ip_addresses.all() %}
                        {% for rack in ip.tenant.racks.all() %}
                            rack: {{ rack.name }}
                        {% endfor %}
                    {% endfor %}
                    {% endfor %}
                """,
                "should_contain": ["rack:"],
                "should_not_contain": [],
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                self.user.user_permissions.clear()
                if scenario["perms"]:
                    self.add_permissions(*scenario["perms"])

                response = self.render_jinja_template_and_assert_success(
                    scenario["template"],
                    "dcim.device",
                    str(self.depth_test_device.pk),
                    depth=4,
                )
                rendered = response["rendered_template"]

                for token in scenario["should_contain"]:
                    self.assertIn(token, rendered)

                for token in scenario["should_not_contain"]:
                    self.assertNotIn(token, rendered)

    def test_prefetched_relations_respect_permissions(self):
        """Prefetched relations should still honor restrict() results."""
        template_code = """
            {% for iface in obj.interfaces.all() %}
                {% for ip in iface.ip_addresses.all() %}
                    pass-one: {{ ip.address }}
                {% endfor %}
                {% for ip in iface.ip_addresses.all() %}
                    pass-two: {{ ip.address }} / tenant: {{ ip.tenant.name }}
                {% endfor %}
            {% endfor %}
        """

        #
        # Scenarios
        #
        # Fields required for each scenario:
        # - name: The name of the scenario
        # - perms: A list of permissions to grant to the user
        # - expect_status: The expected status code of the response
        # - expect_tokens: A list of tokens that should be present in the rendered template
        scenarios = [
            {
                "name": "without_ip_permission",
                "perms": ["dcim.view_device", "dcim.view_interface"],
                "expect_status": status.HTTP_400_BAD_REQUEST,
                "expect_tokens": [],
            },
            {
                "name": "with_ip_permission",
                "perms": ["dcim.view_device", "dcim.view_interface", "ipam.view_ipaddress"],
                "expect_status": status.HTTP_200_OK,
                "expect_tokens": ["pass-one:", "pass-two:"],
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                self.user.user_permissions.clear()
                self.add_permissions(*scenario["perms"])

                response = super().render_jinja_template(
                    template_code,
                    "dcim.device",
                    str(self.depth_test_device.pk),
                    depth=3,
                )
                self.assertEqual(response.status_code, scenario["expect_status"])
                if response.status_code == status.HTTP_200_OK:
                    rendered = response.data.get("rendered_template", "")
                    for token in scenario.get("expect_tokens", []):
                        self.assertIn(token, rendered)

    #
    # needed test list
    #
    # 1. [done] object attributes are hidden when the user lacks the permission
    # 2. [done] object attributes are visible when the user has the permission or is a superuser
    # 3. [done] object fk brief info is available when user has perm on obj but not on the fk model
    # 4. [done] object fk full info is available when user has perm on obj and fk model
    # 5. [done] object relation brief info is available when user has perm on obj but not on the relation model
    # 6. [done] object relation full info is available when user has perm on obj and relation model
    # 7. [done] get/has_ zero-arg methods are available when the user has perm on the object
    # 8. [done] the above tests should all pass for arbitrary object depth
    # 9. [done] prefetched/cached relations still honor restrict() and visibility

    def test_superuser_bypasses_permission_filters(self):
        """Superuser should bypass proxy/facade and render forward FK attributes regardless of depth or perms."""
        # Elevate to superuser; token remains valid for the same user
        self.user.is_superuser = True
        self.user.save()

        template_code_prefix = "Device Type Part #:"
        template_code = template_code_prefix + " {{ obj.device_type.part_number }}"

        for device in [self.device_empty_part_number, self.device_with_part_number]:
            with self.subTest(depth="default", device=device):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": template_code,
                        "content_type": "dcim.device",
                        "object_uuid": str(device.pk),
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                rendered = response.data.get("rendered_template", "")
                if device.device_type.part_number == "":
                    self.assertEqual(template_code_prefix, rendered.rstrip())
                else:
                    self.assertIn(device.device_type.part_number, rendered)

    def test_modular_components_hidden_without_permission(self):
        """All modular component relations should disappear when the user lacks the child permission."""
        from nautobot.dcim.models.device_components import ModularComponentModel

        #
        # Build a list of all modular component models dynamically; this future-proofs the test against new modular component models.
        component_models = [
            model
            for model in ModularComponentModel.__subclasses__()
            if not model._meta.abstract and model._meta.app_label == "dcim"
        ]

        for component_model in component_models:
            with self.subTest(component=component_model.__name__):
                # Determine relation name (ForeignKeyWithAutoRelatedName uses verbose_name_plural). This is the same logic
                # used by ForeignKeyWithAutoRelatedName to set the related_name.
                relation_name = "_".join(re.findall(r"\w+", str(component_model._meta.verbose_name_plural))).lower()
                perm = f"{component_model._meta.app_label}.view_{component_model._meta.model_name}"

                component = component_model.objects.select_related("device").first()

                template_code = f"{{% for obj in obj.{relation_name}.all() %}}{{{{ obj.name }}}}{{% endfor %}}"
                expected_names = list(getattr(component.device, relation_name).values_list("name", flat=True))

                # Without component permission
                self.add_permissions("dcim.view_device")
                response = self.render_jinja_template_and_assert_success(
                    template_code,
                    "dcim.device",
                    str(component.device.pk),
                )
                self.assertEqual("", response["rendered_template"].strip())

                # With component permission
                self.add_permissions(perm)

                response = self.render_jinja_template_and_assert_success(
                    template_code,
                    "dcim.device",
                    str(component.device.pk),
                )
                rendered = response["rendered_template"]
                for name in expected_names:
                    self.assertIn(name, rendered)

    def test_ip_parent_visible_only_with_ipaddress_permission(self):
        """
        Traversing from interface -> ip -> parent should require ipam.view_ipaddress.
        Without it, the proxy returns brief facades that raise AttributeError.
        """
        device = dcim_models.Device.objects.filter(interfaces__isnull=False).first()
        interface = dcim_models.Interface.objects.filter(device=device).first()

        prefix = ipam_models.Prefix.objects.create(prefix="10.10.10.0/24", status=self.prefix_status)
        ip = ipam_models.IPAddress.objects.create(address="10.10.10.1/24", parent=prefix, status=self.ipaddress_status)
        ip.interfaces.add(interface)

        template_code = """
            {% for iface in obj.interfaces.all() %}
            iface: {{ iface.name }}
            {% for ip in iface.ip_addresses.all() %}
                ip: {{ ip.address }}
                prefix: {{ ip.parent }}
            {% endfor %}
            {% endfor %}
        """

        scenarios = [
            {"name": "without_ip_perm", "grant_ip_perm": False, "expect_success": False},
            {"name": "with_ip_perm", "grant_ip_perm": True, "expect_success": True},
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Reset permissions each iteration
                self.user.user_permissions.clear()
                self.add_permissions("dcim.view_device")
                self.add_permissions("dcim.view_interface")
                if scenario["grant_ip_perm"]:
                    self.add_permissions("ipam.view_ipaddress")

                response = self.render_jinja_template_and_assert_success(
                    template_code,
                    "dcim.device",
                    str(device.pk),
                    depth=3,
                )
                rendered = response["rendered_template"]

                if scenario["expect_success"]:
                    self.assertIn(str(prefix.prefix), rendered)
                else:
                    self.assertNotIn(str(prefix.prefix), rendered)

    ### LEGACY TESTS ###

    def test_unprefetched_relation_invokes_restrict(self):
        """
        Relations that were not prefetched should call restrict() to enforce permissions.
        """
        device = dcim_models.Device.objects.filter(device_bays__isnull=False).first()
        if device is None:
            device = dcim_models.Device.objects.filter(
                device_type__subdevice_role=dcim_choices.SubdeviceRoleChoices.ROLE_PARENT
            ).first()
            if device is None:
                self.skipTest("No suitable device with parent support for device bays")
            dcim_models.DeviceBay.objects.create(device=device, name="RenderJinjaTestBay")

        self.add_permissions("dcim.view_device")
        self.add_permissions("dcim.view_devicebay")

        template_code = """
            {% for bay in obj.device_bays.all() %}
                {{ bay.name }}
            {% endfor %}
        """
        with patch.object(
            RestrictedQuerySet, "restrict", wraps=RestrictedQuerySet.restrict, autospec=True
        ) as mock_restrict:
            response = self.client.post(
                reverse("core-api:render_jinja_template"),
                {
                    "template_code": template_code,
                    "content_type": "dcim.device",
                    "object_uuid": str(device.pk),
                },
                format="json",
                **self.header,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        device_bay_calls = [
            call
            for call in mock_restrict.call_args_list
            if getattr(call.args[0], "model", None) is dcim_models.DeviceBay
        ]
        self.assertTrue(device_bay_calls, "restrict() should be invoked for unprefetched DeviceBay relations")

    def test_ips_visible_without_ipaddress_perm_tenant_name_depends_on_tenant_perm(self):
        """
        Users with device/interface view but without ip address permission should still see IPs on interfaces.
        Tenant name on those IPs should only be visible with tenancy.view_tenant or as superuser.
        """
        # Prepare data: choose a device with interfaces, attach IPs with a tenant to several interfaces
        device = dcim_models.Device.objects.filter(interfaces__isnull=False).first()
        interfaces = list(dcim_models.Interface.objects.filter(device=device)[:3])
        tenant, _ = tenancy_models.Tenant.objects.get_or_create(
            name="Renderer Test Tenant 2", defaults={"description": "Renderer Test Tenant 2"}
        )

        parent_prefix = ipam_models.Prefix.objects.create(prefix="203.0.113.0/24", status=self.prefix_status)
        created_ips = []
        base_octet = 20
        for idx, iface in enumerate(interfaces, start=1):
            ip = ipam_models.IPAddress.objects.create(
                address=f"203.0.113.{base_octet + idx}/32",
                tenant=tenant,
                status=self.ipaddress_status,
                parent=parent_prefix,
            )
            ip.interfaces.add(iface)
            created_ips.append(ip)
        ip_address_str = str(created_ips[0].address)
        tenant_name = tenant.name

        # Baseline perms: device + interface only (no ipam.view_ipaddress)
        self.add_permissions("dcim.view_device")
        self.add_permissions("dcim.view_interface")

        template_code_prefix = "IP_LINE:"
        template_code = (
            "{% for iface in obj.interfaces.all() %}"
            "{% for ip in iface.ip_addresses.all() %}"
            f"{template_code_prefix} "
            "{{ ip.address }} | {{ ip.tenant.name }}"
            "{% endfor %}"
            "{% endfor %}"
        )

        scenarios = [
            {"name": "no_tenant_perm", "grant_tenant_perm": False, "superuser": False, "expect_tenant": False},
            {"name": "with_tenant_perm", "grant_tenant_perm": True, "superuser": False, "expect_tenant": True},
            {"name": "superuser", "grant_tenant_perm": False, "superuser": True, "expect_tenant": True},
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Reset superuser flag
                self.user.is_superuser = scenario["superuser"]
                self.user.save()

                if scenario["grant_tenant_perm"]:
                    self.add_permissions("ipam.view_ipaddress")

                response = self.render_jinja_template(
                    template_code,
                    "dcim.device",
                    str(device.pk),
                    depth=3,
                )

                if scenario["expect_tenant"]:
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    rendered = response.data.get("rendered_template", "")
                    self.assertIn(ip_address_str, rendered)
                    self.assertIn(tenant_name, rendered)
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertIn("has no attribute 'tenant'", str(response.data))

    def test_reverse_relation_interfaces_count_varies_by_permissions(self):
        """Reverse FK iterable (interfaces) should reflect permissions and superuser bypass."""
        # Choose a device that has at least one interface
        device = dcim_models.Device.objects.filter(interfaces__isnull=False).first()

        total_if_count = dcim_models.Interface.objects.filter(device=device).count()
        template_code_prefix = "IF_COUNT:"
        template_code = template_code_prefix + " {{ obj.interfaces.count() }}"

        # Base: ensure device itself can be viewed for non-superuser cases
        self.add_permissions("dcim.view_device")

        scenarios = [
            {"name": "no_perm", "grant_interface_perm": False, "superuser": False, "expected": "0"},
            {
                "name": "with_interface_perm",
                "grant_interface_perm": True,
                "superuser": False,
                "expected": str(total_if_count),
            },
            {"name": "superuser", "grant_interface_perm": False, "superuser": True, "expected": str(total_if_count)},
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                # Toggle superuser as requested
                self.user.is_superuser = scenario["superuser"]
                self.user.save()

                if scenario["grant_interface_perm"]:
                    self.add_permissions("dcim.view_interface")

                response = self.render_jinja_template_and_assert_success(
                    template_code,
                    "dcim.device",
                    str(device.pk),
                )

                rendered = response["rendered_template"]
                self.assertTrue(rendered.startswith(template_code_prefix))
                # Extract count after prefix and whitespace
                count_str = rendered.split(":")[-1].strip()
                self.assertEqual(count_str, scenario["expected"])
