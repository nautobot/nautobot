import os
import re

from django.template import TemplateSyntaxError
from django.template.loader import get_template
from django.template.utils import get_app_template_dirs
from django.test import override_settings, SimpleTestCase
from django.urls import reverse

from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.extras.models import SavedView, Status


@override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
class TestSavedViewTitleFix(NautobotTestCase):
    """
    Tests the SavedView page, ensuring the browser title contains only one
    non-italicised SavedView title and that the html body contains
    italicised `Pending changes not saved`.
    """

    @staticmethod
    def get_browser_title(response):
        return re.findall(r"<title>(.*?)</title>", response.content.decode())[0]

    def test_saved_view_name_appears_once_in_browser_title_without_html_tags(self):
        saved_view = SavedView.objects.create(
            name="My Statuses",
            owner=self.user,
            view=f"{Status._meta.app_label}:{Status._meta.model_name}_list",
        )
        url = reverse(saved_view.view) + f"?saved_view={saved_view.pk}&table_changes_pending=true"
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

        browser_title = self.get_browser_title(response)
        self.assertEqual(browser_title.count(saved_view.name), 1)
        self.assertNotIn('<i title="Pending changes not saved">', browser_title)
        self.assertBodyContains(response, '— <i title="Pending changes not saved">')

    def test_other_view_for_errors(self):
        """A different object_list-based list view (no saved view) still renders after the fix."""
        location_response = self.client.get(reverse("dcim:location_list"))
        self.assertHttpStatus(location_response, 200)
        device_response = self.client.get(reverse("dcim:device_list"))
        self.assertHttpStatus(device_response, 200)
        prefix_response = self.client.get(reverse("ipam:prefix_list"))
        self.assertHttpStatus(prefix_response, 200)


class ObjectListChildrenCompileTest(SimpleTestCase):
    """
    Test every installed template that extends `generic/object_list.html` and confirm each one
    COMPILES.

    Scope/limits:
    - Only sees templates from INSTALLED apps.
    - Compile != render: `{% url %}` / missing-context errors are render-time and are covered by the
      per-view render suites (each list view's test GETs the page and asserts 200).
    """

    _EXTENDS_OBJECT_LIST = re.compile(r"""{%\s*extends\s+['"]generic/object_list\.html['"]\s*%}""")

    @classmethod
    def _object_list_children(cls):
        """Return the template names of every installed .html that extends generic/object_list.html."""
        template_dirs = [*get_app_template_dirs("templates")]
        names = set()
        for directory in template_dirs:
            for root, _dirs, files in os.walk(directory):
                for filename in files:
                    if not filename.endswith(".html"):
                        continue
                    path = os.path.join(root, filename)
                    with open(path, encoding="utf-8") as handle:
                        if cls._EXTENDS_OBJECT_LIST.search(handle.read()):
                            names.add(os.path.relpath(path, directory).replace(os.sep, "/"))
        return sorted(names)

    def test_all_object_list_children_compile(self):
        children = self._object_list_children()
        errors = {}
        if len(children) > 0:
            for name in children:
                try:
                    get_template(name)
                except TemplateSyntaxError as exc:
                    errors[name] = str(exc)
        self.assertEqual(errors, {}, f"object_list children failed to compile: {errors}")
