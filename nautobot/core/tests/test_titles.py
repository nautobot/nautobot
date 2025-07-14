"""
Unit tests for titles.py following Nautobot testing conventions.
"""

from django.template import Context

from nautobot.core.testing import TestCase
from nautobot.core.ui.titles import Titles, DEFAULT_TITLES, DocumentTitles, PageHeadings
from nautobot.dcim.models import LocationType
from nautobot.extras.models import SavedView
from nautobot.users.models import User


class TitlesTestCase(TestCase):
    """Test cases for the base Titles class."""

    def setUp(self):
        self.titles = Titles()

    def test_init_with_defaults(self):
        """Test that Titles initializes with default titles."""
        self.assertEqual(self.titles.titles, DEFAULT_TITLES)
        self.assertEqual(self.titles.template_plugins, ["helpers"])

    def test_init_with_custom_titles(self):
        """Test that custom titles override defaults."""
        custom_titles = Titles(list_action="Custom List Title", custom_action="Custom Action Title")
        self.assertEqual(custom_titles.titles["list_action"], "Custom List Title")
        self.assertEqual(custom_titles.titles["custom_action"], "Custom Action Title")
        # Ensure defaults are still present
        self.assertEqual(custom_titles.titles["retrieve_action"], DEFAULT_TITLES["retrieve_action"])

    def test_init_with_custom_plugins(self):
        """Test initialization with custom template plugins."""
        custom_plugins = ["custom_plugin", "another_plugin"]
        titles = Titles(template_plugins=custom_plugins)
        self.assertEqual(titles.template_plugins, custom_plugins)

    def test_template_plugins_str(self):
        """Test template plugin string generation."""
        titles = Titles(template_plugins=["plugin1", "plugin2"])
        expected = "{% load plugin1 %}{% load plugin2 %}"
        self.assertEqual(titles.template_plugins_str, expected)

    def test_render_various_actions(self):
        """Test rendering with different action contexts."""
        location_type = LocationType.objects.create(name="Test Location Type Title")
        test_cases = [
            {
                "name": "list_action",
                "context": {"view_action": "list", "verbose_name_plural": "devices"},
                "expected": "Devices",
            },
            {
                "name": "retrieve_action",
                "context": {
                    "view_action": "retrieve",
                    "object": location_type,
                },
                "expected": "Test Location Type Title",
            },
            {
                "name": "create_action",
                "context": {"view_action": "create", "verbose_name": "device"},
                "expected": "Add a new device",
            },
            {
                "name": "update_action",
                "context": {
                    "view_action": "update",
                    "verbose_name": "location type",
                    "object": location_type,
                },
                "expected": "Editing location type Test Location Type Title",
            },
            {
                "name": "destroy_action",
                "context": {"view_action": "destroy", "verbose_name": "device"},
                "expected": "Delete device?",
            },
            {
                "name": "bulk_destroy_action",
                "context": {"view_action": "bulk_destroy", "total_objs_to_delete": 5, "verbose_name_plural": "devices"},
                "expected": "Delete 5 Devices?",
            },
            {
                "name": "bulk_rename_action",
                "context": {
                    "view_action": "bulk_rename",
                    "selected_objects": ["obj1", "obj2", "obj3"],
                    "verbose_name_plural": "devices",
                    "parent_name": "Site A",
                },
                "expected": "Renaming 3 Devices on Site A",
            },
            {
                "name": "bulk_update_action",
                "context": {"view_action": "bulk_update", "objs_count": 10, "verbose_name_plural": "devices"},
                "expected": "Editing 10 Devices",
            },
            {
                "name": "changelog_action",
                "context": {
                    "view_action": "changelog",
                    "object": location_type,
                },
                "expected": "Test Location Type Title - Change Log",
            },
            {
                "name": "notes_action",
                "context": {
                    "view_action": "notes",
                    "object": location_type,
                },
                "expected": "Test Location Type Title - Notes",
            },
            {
                "name": "approve_action",
                "context": {"view_action": "approve", "verbose_name": "device"},
                "expected": "Approve Device?",
            },
            {
                "name": "deny_action",
                "context": {"view_action": "deny", "verbose_name": "device"},
                "expected": "Deny Device?",
            },
        ]

        for test_case in test_cases:
            with self.subTest(action=test_case["name"]):
                context = Context(test_case["context"])
                result = self.titles.render(context)
                self.assertEqual(result, test_case["expected"])

    def test_render_with_missing_action(self):
        """Test rendering with an action that doesn't exist in titles."""
        context = Context({"view_action": "nonexistent"})
        result = self.titles.render(context)
        self.assertEqual(result, "")

    def test_render_default_action(self):
        """Test rendering when no view_action is provided."""
        context = Context({"verbose_name_plural": "devices"})
        result = self.titles.render(context)
        self.assertEqual(result, "Devices")  # Should use list_action as default

    def test_get_extra_context(self):
        """Test that get_extra_context returns empty dict by default."""
        context = Context({})
        extra_context = self.titles.get_extra_context(context)
        self.assertEqual(extra_context, {})

    def test_get_extra_context_is_being_used_during_render(self):
        """Test that get_extra_context returns empty dict by default."""
        context = Context({})

        class TitlesSubClass(Titles):
            def get_extra_context(self, context: Context) -> dict:
                return {"verbose_name_plural": "devices"}

        rendered_title = TitlesSubClass().render(context)
        self.assertEqual(rendered_title, "Devices")


class DocumentTitlesTestCase(TestCase):
    """Test cases for the DocumentTitles class."""

    def setUp(self):
        self.document_titles = DocumentTitles()

    def test_render_strips_html_tags(self):
        """Test that DocumentTitles strips HTML tags from rendered output."""
        context = Context({"view_action": "list", "verbose_name_plural": "devices"})
        self.document_titles.titles["list_action"] = "<strong>{{ verbose_name_plural|bettertitle }}</strong>"
        result = self.document_titles.render(context)
        self.assertEqual(result, "Devices")

    def test_render_with_complex_html(self):
        """Test stripping of complex HTML content."""
        doc_titles = DocumentTitles(
            list_action='<div class="title"><span>{{ verbose_name_plural|bettertitle }}</span></div>'
        )
        context = Context({"view_action": "list", "verbose_name_plural": "devices"})
        result = doc_titles.render(context)
        self.assertEqual(result, "Devices")


class PageHeadingsTestCase(TestCase):
    """Test cases for the PageHeadings class."""

    def setUp(self):
        self.user = User.objects.create_user(username="Saved View test user")
        self.page_headings = PageHeadings()

    def test_default_list_action_override(self):
        """Test that PageHeadings overrides the default list_action."""
        expected = "{% format_title_with_saved_view verbose_name_plural|bettertitle %}"
        self.assertEqual(self.page_headings.titles["list_action"], expected)

    def test_render_with_saved_view_formatting(self):
        """Test rendering with the custom list action template."""
        saved_view = SavedView.objects.create(name="My filters!", owner=self.user, view="dcim:location_list")
        test_cases = [
            {
                "name": "no_saved_view",
                "context": {
                    "verbose_name_plural": "devices",
                },
                "expected": "Devices",
            },
            {
                "name": "with_saved_view_saved",
                "context": {
                    "verbose_name_plural": "devices",
                    "current_saved_view": saved_view,
                },
                "expected": "Devices - My filters!",
            },
            {
                "name": "with_saved_view_not_saved",
                "context": {
                    "verbose_name_plural": "devices",
                    "current_saved_view": saved_view,
                    "new_changes_not_applied": True,
                },
                "expected": 'Devices — <i title="Pending changes not saved">My filters!</i>',
            },
        ]

        for test_case in test_cases:
            with self.subTest(action=test_case["name"]):
                context = Context(test_case["context"])
                result = self.page_headings.render(context)
                self.assertEqual(result, test_case["expected"])
