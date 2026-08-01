import os
import re

from django.template import engines, TemplateSyntaxError
from django.template.loader import get_template
from django.template.utils import get_app_template_dirs
from django.test import override_settings, SimpleTestCase
from django.urls import reverse

from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.extras.models import SavedView, Status

# A minimal stand-in for the real `base.html`/`base_django.html` chain, isolated from
# Nautobot's actual nav menu/request/permission requirements.
SYNTHETIC_TEMPLATES = {
    "base.html": "<title>{% block title %}Default Title{% endblock %}</title>",
    "middle.html": "{% extends 'base.html' %}",
}


@override_settings(
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": False,
            "OPTIONS": {
                "loaders": [("django.template.loaders.locmem.Loader", SYNTHETIC_TEMPLATES)],
            },
        }
    ]
)
class TestDjangoTemplateBlockChanges(SimpleTestCase):
    def render_child(self, title_block_body, parent="base.html"):
        template_string = f"{{% extends '{parent}' %}}" + title_block_body
        return engines["django"].from_string(template_string).render({})

    def test_block_renders(self):
        rendered = self.render_child("""{% block title %}My Override{% endblock %}""")
        self.assertEqual(rendered, "<title>My Override</title>")

    def test_title_block_override_scenarios(self):
        """
        Almost any content can be dropped into `{% block title %}`, and in most cases
        the template will render without raising.
        """
        cases = [
            ("empty override", "{% block title %}{% endblock %}", "<title></title>"),
            (
                "plain text",
                "{% block title %}Single Source of Truth{% endblock %}",
                "<title>Single Source of Truth</title>",
            ),
            (
                "extends parent default via block.super",
                "{% block title %}{{ block.super }} - Extra{% endblock %}",
                "<title>Default Title - Extra</title>",
            ),
            (
                "No override",
                "",
                "<title>Default Title</title>",
            ),
        ]
        for label, title_block_body, expected in cases:
            with self.subTest(label):
                rendered = self.render_child(title_block_body)
                self.assertEqual(rendered, expected)

    def test_title_block_override_through_intermediate_template_without_override(self):
        """
        Checks triple-nested block title. Extends a middle.html, which does not implement block title,
        but inherits it from one level above.
        """
        rendered = self.render_child("{% block title %}Single Source of Truth{% endblock %}", parent="middle.html")
        self.assertEqual(rendered, "<title>Single Source of Truth</title>")

    def test_title_block_super_through_intermediate_template_without_override(self):
        """Tests the {{ block.super }} falling back to what is defined at the top level."""
        rendered = self.render_child("{% block title %}{{ block.super }} - Extra{% endblock %}", parent="middle.html")
        self.assertEqual(rendered, "<title>Default Title - Extra</title>")

    def test_no_override_anywhere_falls_back_to_grandparent_default(self):
        """Tests the title falling back to what is defined at the top level."""
        rendered = self.render_child("", parent="middle.html")
        self.assertEqual(rendered, "<title>Default Title</title>")


@override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
class TestSavedViewTitleFix(NautobotTestCase):
    """
    End-to-end regression tests, exercising the
    `generic/object_list.html` / `base_django.html` templates through an actual view
    request rather than synthetic templates.

    Before the fix, `generic/object_list.html` defined both:
        {% block title %}{{ block.super }}{% saved_view_title %}{% endblock %}
    and `{% block document_title_extra %}{% saved_view_title "plain" %}{% endblock %}`.
    The first used the default "html" mode of `saved_view_title`, so the saved view
    name was appended twice to the browser tab title, and once as raw `<i>` markup
    that a browser can't render inside `<title>`.
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
        self.assertNotIn("<i", browser_title)
        self.assertBodyContains(response, '— <i title="Pending changes not saved">')

    def test_other_view_for_errors(self):
        """A different object_list-based list view (no saved view) still renders after the fix."""
        response = self.client.get(reverse("dcim:location_list"))
        self.assertHttpStatus(response, 200)


class ObjectListChildrenCompileTest(SimpleTestCase):
    """
    Discover every installed template that extends `generic/object_list.html` and confirm each one
    COMPILES. This catches the structural break class — a missing `{% load %}`, a syntax error, or a
    broken parent chain — for ALL children at once, without needing each view's render context.

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
