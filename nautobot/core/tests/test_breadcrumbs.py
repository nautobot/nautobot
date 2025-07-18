"""
Unit tests for the updated breadcrumbs.py following Nautobot testing conventions.
"""

from unittest.mock import patch

from django.template import Context

from nautobot.core.testing import TestCase
from nautobot.core.ui.breadcrumbs import BreadcrumbItem, Breadcrumbs, DEFAULT_BREADCRUMBS
from nautobot.dcim.models import Device, LocationType


class BreadcrumbItemTestCase(TestCase):
    """Test cases for BreadcrumbItem class."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.location_type = LocationType.objects.create(name="Test Location Type Breadcrumbs")

    def test_view_name_mode(self):
        """Test breadcrumb item with view_name mode."""
        item = BreadcrumbItem(view_name="home", label="Home")
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, "/")
        self.assertEqual(label, "Home")

    def test_view_name_mode_with_kwargs_and_query_params(self):
        """Test breadcrumb item in view_name mode and kwargs."""
        item = BreadcrumbItem(
            view_name="dcim:locationtype",
            reverse_kwargs={"pk": self.location_type.pk},
            reverse_query_params={"name": "test"},
            label="Filtered Locations Types",
        )
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, f"/dcim/location-types/{self.location_type.pk}/?name=test")
        self.assertEqual(label, "Filtered Locations Types")

    def test_model_mode(self):
        """Test breadcrumb item in model mode."""
        test_cases = [
            {
                "name": "model_class",
                "kwargs": {"model": Device},
                "expected_url": "/dcim/devices/",
                "expected_label": "Devices",
            },
            {
                "name": "model_instance",
                "kwargs": {"model": self.location_type},
                "expected_url": "/dcim/location-types/",
                "expected_label": "Location Types",
            },
            {
                "name": "model_str",
                "kwargs": {"model": "dcim.device"},
                "expected_url": "/dcim/devices/",
                "expected_label": "Devices",
            },
            {
                "name": "model_class_custom_url_action",
                "kwargs": {"model": Device, "model_url_action": "add", "model_label_type": "singular"},
                "expected_url": "/dcim/devices/add/",
                "expected_label": "Device",
            },
            {
                "name": "model_class_with_kwargs",
                "kwargs": {
                    "model": Device,
                    "model_url_action": "",
                    "model_label_type": "singular",
                    "reverse_kwargs": {"pk": "947a8a80-9e62-5605-ab18-7a47c588f0ad"},
                },
                "expected_url": "/dcim/devices/947a8a80-9e62-5605-ab18-7a47c588f0ad/",
                "expected_label": "Device",
            },
            {
                "name": "model_class_with_query_params",
                "kwargs": {"model": Device, "reverse_query_params": {"filter": "abc"}},
                "expected_url": "/dcim/devices/?filter=abc",
                "expected_label": "Devices",
            },
        ]
        for test_case in test_cases:
            with self.subTest(action=test_case["name"]):
                item = BreadcrumbItem(**test_case["kwargs"])
                context = Context({})

                url, label = item.as_pair(context)

                self.assertEqual(url, test_case["expected_url"])
                self.assertEqual(label, test_case["expected_label"])

    def test_model_mode_from_context(self):
        """Test breadcrumb item with model from context."""
        item = BreadcrumbItem(model_key="location_type")
        context = Context({"location_type": self.location_type})

        url, label = item.as_pair(context)

        self.assertEqual(url, "/dcim/location-types/")
        self.assertEqual(label, "Location Types")

    def test_instance_mode(self):
        """Test breadcrumb item with instance from context."""
        item = BreadcrumbItem(instance_key="object")
        context = Context({"object": self.location_type})

        url, label = item.as_pair(context)

        self.assertEqual(url, f"/dcim/location-types/{self.location_type.pk}/")
        self.assertEqual(label, str(self.location_type))

    def test_label_override(self):
        """Test that explicit label overrides automatic label generation."""
        item = BreadcrumbItem(model=Device, label="Custom Label")
        context = Context({})

        _, label = item.as_pair(context)
        self.assertEqual(label, "Custom Label")

    def test_no_reverse_match(self):
        """Test handling of NoReverseMatch exception."""
        item = BreadcrumbItem(view_name="nonexistent")
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, "")
        self.assertEqual(label, "")

    def test_empty_context_keys(self):
        """Test breadcrumb item when context keys are missing."""
        item = BreadcrumbItem(instance_key="missing_key")
        context = Context({})

        url, label = item.as_pair(context)
        self.assertEqual(url, "")
        self.assertEqual(label, "")


class BreadcrumbsTestCase(TestCase):
    """Test cases for Breadcrumbs class."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.location_type = LocationType.objects.create(name="Test Location Type Breadcrumbs")

    def test_default_initialization(self):
        """Test that Breadcrumbs initializes with default values."""
        breadcrumbs = Breadcrumbs()

        # Should have deep copy of defaults
        self.assertEqual(breadcrumbs.items.keys(), DEFAULT_BREADCRUMBS.keys())

        # Verify deep copy by modifying
        breadcrumbs.items["list"] = []
        self.assertNotEqual(DEFAULT_BREADCRUMBS.get("list"), [])

    def test_custom_items(self):
        """Test Breadcrumbs with custom items."""
        custom_list_item = BreadcrumbItem(view_name="home", label="Home")
        custom_items = {
            "list": [BreadcrumbItem(view_name="home", label="Home")],
        }
        breadcrumbs = Breadcrumbs(items=custom_items)

        self.assertEqual(len(breadcrumbs.items["list"]), 1)
        self.assertEqual(breadcrumbs.items["list"][0], custom_list_item)

        # Other defaults should still exist
        self.assertIn("detail", breadcrumbs.items)

    def test_prepend_append_items(self):
        """Test prepend and append functionality."""
        prepend = {"list": [BreadcrumbItem(view_name="home", label="Home")]}
        append = {"list": [BreadcrumbItem(label="End")]}
        expected_items = [
            ("/", "Home"),
            ("/dcim/location-types/", "Location Types"),
            ("", "End"),
        ]

        breadcrumbs = Breadcrumbs(prepend_items=prepend, append_items=append)
        context = Context({"model": LocationType})

        items = breadcrumbs.get_breadcrumbs_items(context)

        # Should have prepend + default + append
        # Default list action has one item, so prepend + default + append = 2
        self.assertEqual(len(items), 3)
        self.assertEqual(items, expected_items)

    def test_get_items_from_action_static_method(self):
        """Test the _get_items_from_action static method."""
        test_items = {"list": [BreadcrumbItem(label="List Item")], "detail": [BreadcrumbItem(label="Detail Item")]}

        # Test specific action found
        result = Breadcrumbs.get_items_for_action(test_items, "list", False)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].label, "List Item")

        # Test fallback to detail when action not found and detail=True
        result = Breadcrumbs.get_items_for_action(test_items, "nonexistent", True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].label, "Detail Item")

        # Test no fallback when detail=False
        result = Breadcrumbs.get_items_for_action(test_items, "nonexistent", False)
        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])

    def test_detail_fallback_behavior(self):
        """Test that detail fallback works correctly in get_breadcrumbs_items."""
        custom_items = {"detail": [BreadcrumbItem(model_key="model"), BreadcrumbItem(instance_key="object")]}
        breadcrumbs = Breadcrumbs(items=custom_items)
        expected_items = [
            ("/dcim/location-types/", "Location Types"),
            (f"/dcim/location-types/{self.location_type.pk}/", str(self.location_type)),
        ]

        # Test with an action that doesn't exist but detail=True
        context = Context(
            {"view_action": "custom_action", "detail": True, "model": LocationType, "object": self.location_type}
        )

        items = breadcrumbs.get_breadcrumbs_items(context)

        # Should get 2 items from detail fallback
        self.assertEqual(len(items), 2)
        self.assertEqual(items, expected_items)

    def test_render_method(self):
        """Test the render method."""
        breadcrumbs = Breadcrumbs()
        context = Context({"view_action": "list", "model": Device})

        html = breadcrumbs.render(context)

        expected_html = """<ol class="breadcrumb"><li><a href="/dcim/devices/">Devices</a></li></ol>"""
        self.assertHTMLEqual(html, expected_html)

    def test_get_extra_context(self):
        """Test that get_extra_context can be extended."""

        class CustomBreadcrumbs(Breadcrumbs):
            def get_extra_context(self, context: Context):
                return {"custom_key": "custom_value"}

        render_context = {}

        def capture_context(template, context):
            nonlocal render_context
            render_context = context.flatten()
            return ""

        breadcrumbs = CustomBreadcrumbs(items={"list": []})
        context = Context({})

        with patch("nautobot.core.ui.breadcrumbs.render_component_template", side_effect=capture_context):
            breadcrumbs.render(context)

        # Check that custom context was passed
        self.assertEqual(render_context.get("custom_key"), "custom_value")

    def test_deep_copy_behavior(self):
        """Verify that modifications don't affect the original DEFAULT_BREADCRUMBS."""
        breadcrumbs1 = Breadcrumbs()
        breadcrumbs2 = Breadcrumbs()

        # Modify the first instance
        breadcrumbs1.items["list"] = [BreadcrumbItem(label="Modified")]

        # Second instance should not be affected
        self.assertNotEqual(breadcrumbs1.items["list"], breadcrumbs2.items["list"])

        # Original defaults should not be affected
        self.assertEqual(DEFAULT_BREADCRUMBS.get("list")[0].model_key, "model")
