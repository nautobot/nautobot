from unittest.mock import MagicMock

from django.core.exceptions import FieldDoesNotExist
from django.db.models import CharField
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from nautobot.core.templatetags.buttons import consolidate_bulk_action_buttons


class ConsolidateBulkActionButtonsTest(TestCase):
    """Tests for the consolidate_bulk_action_buttons templatetag."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = MagicMock()
        self.user.has_perms.return_value = True

    def _make_context(self, has_rename=True, is_dg_associable=True, has_edit=True, has_delete=True):
        """Build a minimal template context for the templatetag."""
        model = MagicMock()
        if has_rename:
            model._meta.get_field.return_value = CharField()
        else:
            model._meta.get_field.side_effect = FieldDoesNotExist
        model.is_dynamic_group_associable_model = is_dg_associable

        request = self.factory.get("/")

        return {
            "request": request,
            "model": model,
            "user": self.user,
            "bulk_edit_url": "dcim:device_bulk_edit" if has_edit else "",
            "bulk_delete_url": "dcim:device_bulk_delete" if has_delete else "",
            "bulk_rename_url": "dcim:device_bulk_rename" if has_rename else "",
            "permissions": {
                "change": has_edit,
                "delete": has_delete,
            },
        }

    def _get_buttons_html(self, **kwargs):
        """Call the templatetag and return the joined HTML of all buttons."""
        context = self._make_context(**kwargs)
        result = consolidate_bulk_action_buttons(context)
        return "".join(str(b) for b in result["bulk_action_buttons"])

    def _get_buttons_list(self, **kwargs):
        """Call the templatetag and return the raw button list."""
        context = self._make_context(**kwargs)
        return consolidate_bulk_action_buttons(context)["bulk_action_buttons"]

    def test_all_four_buttons(self):
        """Edit + Delete + StaticGroup + Rename → split dropdown with all items."""
        html = self._get_buttons_html(has_rename=True, is_dg_associable=True, has_edit=True, has_delete=True)
        self.assertIn("Edit Selected", html)
        self.assertIn("Delete Selected", html)
        self.assertIn("Update Group Assignment", html)
        self.assertIn("Rename Selected", html)
        self.assertIn("dropdown-toggle", html)
        self.assertIn("dropdown-divider", html)

    def test_edit_delete_rename_no_static_group(self):
        """Edit + Delete + Rename → split dropdown, divider between delete and rename."""
        html = self._get_buttons_html(has_rename=True, is_dg_associable=False, has_edit=True, has_delete=True)
        self.assertIn("Edit Selected", html)
        self.assertIn("Delete Selected", html)
        self.assertIn("Rename Selected", html)
        self.assertNotIn("Update Group Assignment", html)
        self.assertIn("dropdown-toggle", html)
        self.assertIn("dropdown-divider", html)

    def test_edit_delete_static_group_no_name(self):
        """Edit + Delete + StaticGroup (no name) → split dropdown, divider, no rename."""
        html = self._get_buttons_html(has_rename=False, is_dg_associable=True, has_edit=True, has_delete=True)
        self.assertIn("Edit Selected", html)
        self.assertIn("Delete Selected", html)
        self.assertIn("Update Group Assignment", html)
        self.assertNotIn("Rename Selected", html)
        self.assertIn("dropdown-toggle", html)
        self.assertIn("dropdown-divider", html)

    def test_edit_delete_only(self):
        """Edit + Delete → split dropdown, no divider (no non-destructive items after delete)."""
        html = self._get_buttons_html(has_rename=False, is_dg_associable=False, has_edit=True, has_delete=True)
        self.assertIn("Edit Selected", html)
        self.assertIn("Delete Selected", html)
        self.assertNotIn("Rename Selected", html)
        self.assertNotIn("Update Group Assignment", html)
        self.assertIn("dropdown-toggle", html)
        self.assertNotIn("dropdown-divider", html)

    def test_edit_only(self):
        """Edit only → standalone button, no dropdown."""
        html = self._get_buttons_html(has_rename=False, is_dg_associable=False, has_edit=True, has_delete=False)
        self.assertIn("Edit Selected", html)
        self.assertNotIn("Delete Selected", html)
        self.assertNotIn("dropdown-toggle", html)
        self.assertNotIn("dropdown-divider", html)

    def test_delete_only(self):
        """Delete only → standalone button, no dropdown."""
        html = self._get_buttons_html(has_rename=False, is_dg_associable=False, has_edit=False, has_delete=True)
        self.assertIn("Delete Selected", html)
        self.assertNotIn("Edit Selected", html)
        self.assertNotIn("dropdown-toggle", html)

    def test_delete_static_group_no_edit(self):
        """Delete + StaticGroup (no edit/change perm) → 'Bulk Actions' dropdown."""
        html = self._get_buttons_html(has_rename=False, is_dg_associable=True, has_edit=False, has_delete=True)
        self.assertIn("Bulk Actions", html)
        self.assertIn("Delete Selected", html)
        self.assertIn("Update Group Assignment", html)
        self.assertNotIn("Edit Selected", html)
        self.assertNotIn("Rename Selected", html)
        self.assertIn("dropdown-divider", html)

    def test_no_buttons(self):
        """No permissions → empty list."""
        buttons = self._get_buttons_list(has_rename=False, is_dg_associable=False, has_edit=False, has_delete=False)
        self.assertEqual(buttons, [])

    def _get_button_order(self, buttons):
        """Extract the order of button labels from the rendered button list."""
        labels = []
        for html in (str(b) for b in buttons):
            if "Edit Selected" in html:
                labels.append("Edit")
            elif "Delete Selected" in html:
                labels.append("Delete")
            elif "Update Group Assignment" in html:
                labels.append("StaticGroup")
            elif "Rename Selected" in html:
                labels.append("Rename")
            elif "dropdown-divider" in html:
                labels.append("Divider")
            elif "Bulk Actions" in html:
                labels.append("BulkActions")
        return labels

    def test_order_all_four_buttons(self):
        """Dropup order: Edit (primary) → Delete → Divider → StaticGroup → Rename (closest to Edit)."""
        buttons = self._get_buttons_list(has_rename=True, is_dg_associable=True, has_edit=True, has_delete=True)
        self.assertEqual(self._get_button_order(buttons), ["Edit", "Delete", "Divider", "StaticGroup", "Rename"])

    def test_order_edit_delete_rename(self):
        """Dropup order: Edit → Delete → Divider → Rename."""
        buttons = self._get_buttons_list(has_rename=True, is_dg_associable=False, has_edit=True, has_delete=True)
        self.assertEqual(self._get_button_order(buttons), ["Edit", "Delete", "Divider", "Rename"])

    def test_order_edit_delete_static_group(self):
        """Dropup order: Edit → Delete → Divider → StaticGroup."""
        buttons = self._get_buttons_list(has_rename=False, is_dg_associable=True, has_edit=True, has_delete=True)
        self.assertEqual(self._get_button_order(buttons), ["Edit", "Delete", "Divider", "StaticGroup"])

    def test_order_delete_static_group_no_edit(self):
        """Dropup order: BulkActions → Delete → Divider → StaticGroup."""
        buttons = self._get_buttons_list(has_rename=False, is_dg_associable=True, has_edit=False, has_delete=True)
        self.assertEqual(self._get_button_order(buttons), ["BulkActions", "Delete", "Divider", "StaticGroup"])


class CopyButtonTest(TestCase):
    """Tests for the copy_button templatetag."""

    @staticmethod
    def _render(args=""):
        return Template("{% load buttons %}{% copy_button " + args + " %}").render(Context())

    def test_target_variant(self):
        """`target` renders a data-clipboard-target attribute and the canonical hover-copy markup."""
        html = self._render('target="#uuid_copy"')
        self.assertInHTML(
            """
            <button type="button" class="btn btn-secondary nb-btn-inline-hover" data-clipboard-target="#uuid_copy">
                <span aria-hidden="true" class="mdi mdi-content-copy"></span>
                <span class="visually-hidden">Copy</span>
            </button>
            """,
            html,
        )

    def test_text_variant(self):
        """`text` renders a data-clipboard-text attribute with a literal value to copy."""
        html = self._render('text="hello world" label="Copy name"')
        self.assertInHTML(
            """
            <button type="button" class="btn btn-secondary nb-btn-inline-hover" data-clipboard-text="hello world">
                <span aria-hidden="true" class="mdi mdi-content-copy"></span>
                <span class="visually-hidden">Copy name</span>
            </button>
            """,
            html,
        )

    def test_size_and_css_class(self):
        """`size` and `css_class` are appended to the button class list."""
        html = self._render('target="#x" size="sm" css_class="my-extra"')
        self.assertIn("btn-sm", html)
        self.assertIn("my-extra", html)

    def test_no_target_or_text_renders_nothing(self):
        """Without `target` or `text`, no button is rendered."""
        self.assertNotIn("<button", self._render())
