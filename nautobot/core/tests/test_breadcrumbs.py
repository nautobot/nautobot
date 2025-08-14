"""
Unit tests for the updated breadcrumbs.py following Nautobot testing conventions.
"""

from operator import itemgetter
from unittest.mock import patch

from django.template import Context
from django.utils.http import urlencode

from nautobot.core.testing import TestCase
from nautobot.core.ui.breadcrumbs import (
    BaseBreadcrumbItem,
    Breadcrumbs,
    InstanceBreadcrumbItem,
    ModelBreadcrumbItem,
    ViewNameBreadcrumbItem,
)
from nautobot.dcim.models import Device, LocationType


class BreadcrumbItemsTestCase(TestCase):
    """Test cases for BreadcrumbItem class."""

    @classmethod
    def setUpTestData(cls):
        """Create test data."""
        cls.location_type = LocationType.objects.create(name="Test Location Type Breadcrumbs")

    def test_view_name_item(self):
        """Test breadcrumb view name item."""
        item = ViewNameBreadcrumbItem(view_name="home", label="Home")
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, "/")
        self.assertEqual(label, "Home")

    def test_view_name_item_with_kwargs_and_query_params(self):
        """Test breadcrumb view name item and kwargs."""
        item = ViewNameBreadcrumbItem(
            view_name="dcim:locationtype",
            reverse_kwargs={"pk": self.location_type.pk},
            reverse_query_params={"name": "test"},
            label="Filtered Locations Types",
        )
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, f"/dcim/location-types/{self.location_type.pk}/?name=test")
        self.assertEqual(label, "Filtered Locations Types")

    def test_view_name_item_with_kwargs_and_query_params_callable(self):
        """Test breadcrumb view name item and kwargs."""
        item = ViewNameBreadcrumbItem(
            view_name="dcim:locationtype",
            reverse_kwargs=lambda c: {"pk": c["object"].pk},
            reverse_query_params=lambda c: {"name": c["object"].name},
            label="Filtered Locations Types",
        )
        context = Context({"object": self.location_type})

        url, label = item.as_pair(context)

        self.assertEqual(
            url, f"/dcim/location-types/{self.location_type.pk}/?{urlencode({'name': self.location_type.name})}"
        )
        self.assertEqual(label, "Filtered Locations Types")

    def test_callable_label_and_view_name(self):
        """Test label and view_name as callables."""
        item = ViewNameBreadcrumbItem(
            view_name=lambda _: "home",
            label=lambda context: f"Hi, {context['user']}!",
        )
        context = Context({"user": "Frodo"})
        url, label = item.as_pair(context)
        self.assertEqual(url, "/")
        self.assertEqual(label, "Hi, Frodo!")

    def test_model_items(self):
        """Test breadcrumb model items."""
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
                "name": "model_instance_callable",
                "kwargs": {"model": itemgetter("object")},
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
                "kwargs": {"model": Device, "action": "add", "label_type": "singular"},
                "expected_url": "/dcim/devices/add/",
                "expected_label": "Device",
            },
            {
                "name": "model_class_with_kwargs",
                "kwargs": {
                    "model": Device,
                    "action": "",
                    "label_type": "singular",
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
            {
                "name": "model_class_with_query_params_callable",
                "kwargs": {
                    "model": itemgetter("model_type"),
                    "reverse_query_params": lambda c: {"name": c["device_name"]},
                },
                "expected_url": "/dcim/devices/?name=abc",
                "expected_label": "Devices",
            },
        ]
        for test_case in test_cases:
            with self.subTest(action=test_case["name"]):
                item = ModelBreadcrumbItem(**test_case["kwargs"])
                context = Context({"object": self.location_type, "model_type": Device, "device_name": "abc"})

                url, label = item.as_pair(context)

                self.assertEqual(url, test_case["expected_url"])
                self.assertEqual(label, test_case["expected_label"])

    def test_model_item_from_context(self):
        """Test breadcrumb item with model from context."""
        item = ModelBreadcrumbItem(model_key="object")
        context = Context({"object": self.location_type})

        url, label = item.as_pair(context)

        self.assertEqual(url, "/dcim/location-types/")
        self.assertEqual(label, "Location Types")

    def test_instance_item(self):
        """Test breadcrumb item with instance from context."""
        item = InstanceBreadcrumbItem(instance_key="object")
        context = Context({"object": self.location_type})

        url, label = item.as_pair(context)

        self.assertEqual(url, f"/dcim/location-types/{self.location_type.pk}/")
        self.assertEqual(label, str(self.location_type))

    def test_label_override(self):
        """Test that explicit label overrides automatic label generation."""
        items = [
            ViewNameBreadcrumbItem(view_name="dcim:locationtype", label="Custom Label"),
            ModelBreadcrumbItem(model=LocationType, label="Custom Label"),
            InstanceBreadcrumbItem(label="Custom Label"),
        ]

        context = Context({"object": self.location_type})

        for item in items:
            with self.subTest():
                _, label = item.as_pair(context)
                self.assertEqual(label, "Custom Label")

    def test_no_reverse_match(self):
        """Test handling of NoReverseMatch exception."""
        item = ViewNameBreadcrumbItem(view_name="nonexistent")
        context = Context({})

        url, label = item.as_pair(context)

        self.assertEqual(url, "")
        self.assertEqual(label, "")

    def test_empty_context_keys(self):
        """Test breadcrumb item when context keys are missing."""
        context = Context({})
        item = InstanceBreadcrumbItem(instance_key="missing_key")

        url, label = item.as_pair(context)
        self.assertEqual(url, "")
        self.assertEqual(label, "")

        item = ModelBreadcrumbItem(model_key="missing_key")
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

        # Should have defaults for list and details
        self.assertEqual(len(breadcrumbs.items["list"]), 2)
        self.assertEqual(len(breadcrumbs.items["detail"]), 3)

        # Verify adding items
        new_item = BaseBreadcrumbItem()
        breadcrumbs = Breadcrumbs(items={"detail": [new_item], "list": [new_item], "custom_action": [new_item]})

        self.assertEqual(len(breadcrumbs.items["list"]), 1)
        self.assertEqual(breadcrumbs.items["list"][0], new_item)

        self.assertEqual(len(breadcrumbs.items["detail"]), 2)
        self.assertEqual(breadcrumbs.items["detail"][0], new_item)

        self.assertEqual(len(breadcrumbs.items["custom_action"]), 1)
        self.assertEqual(breadcrumbs.items["custom_action"][0], new_item)

    def test_custom_items(self):
        """Test Breadcrumbs with custom items."""
        custom_list_item = ViewNameBreadcrumbItem(view_name="home", label="Home")
        custom_items = {
            "list": [ViewNameBreadcrumbItem(view_name="home", label="Home")],
        }
        breadcrumbs = Breadcrumbs(items=custom_items)

        self.assertEqual(len(breadcrumbs.items["list"]), 1)
        self.assertEqual(breadcrumbs.items["list"][0], custom_list_item)

        # Other defaults should still exist
        self.assertIn("detail", breadcrumbs.items)
        self.assertEqual(len(breadcrumbs.items["detail"]), 3)

    def test_get_items_from_action_static_method(self):
        """Test the _get_items_from_action static method."""
        test_items = {
            "list": [ViewNameBreadcrumbItem(view_name="", label="List Item")],
            "detail": [ViewNameBreadcrumbItem(view_name="", label="Detail Item")],
        }

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
        breadcrumbs = Breadcrumbs()
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

        def capture_context(template, context, **kwargs):
            nonlocal render_context
            render_context = context.flatten()
            return ""

        breadcrumbs = CustomBreadcrumbs(items={"list": []})
        context = Context({})

        with patch("nautobot.core.ui.breadcrumbs.render_component_template", side_effect=capture_context):
            breadcrumbs.render(context)

        # Check that custom context was passed
        self.assertEqual(render_context.get("custom_key"), "custom_value")

    def test_should_render_skips_items(self):
        """Breadcrumbs should skip items where should_render(context) is False."""

        item_visible = ViewNameBreadcrumbItem(view_name="home", label="Visible", should_render=lambda _: True)
        item_hidden = ViewNameBreadcrumbItem(view_name="home", label="Hidden", should_render=lambda _: False)
        breadcrumbs = Breadcrumbs(items={"custom_action": [item_visible, item_hidden]})
        context = Context({"view_action": "custom_action"})

        items = breadcrumbs.get_breadcrumbs_items(context)
        self.assertEqual(len(items), 1)
        self.assertIn(("/", "Visible"), items)
        self.assertNotIn(("/", "Hidden"), items)

    def test_filter_breadcrumbs_items_removes_empty_pairs(self):
        """filter_breadcrumbs_items should remove items where label is empty or None."""

        breadcrumbs = Breadcrumbs()
        # (url, label) pairs: only the last should remain
        pairs = [
            ("", ""),  # empty
            ("", "   "),  # whitespace
            ("", "\t"),  # whitespace
            ("", "Non-empty"),  # label not empty
            ("/foo", ""),  # url not empty
            ("/foo", "Label"),  # url, label not empty
            (None, None),  # both None
            (None, "Label"),  # label not None
            ("/bar", None),  # url not None
        ]
        expected = [
            ("", "Non-empty"),
            ("/foo", "Label"),
            (None, "Label"),
        ]
        filtered = breadcrumbs.filter_breadcrumbs_items(pairs, Context({}))
        self.assertEqual(filtered, expected)
