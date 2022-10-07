from django.test import TestCase
from jinja2.exceptions import TemplateAssertionError

from netutils.utils import jinja2_convenience_function

from nautobot.utilities.utils import render_jinja2


class NautobotJinjaFilterTest(TestCase):
    def test_invalid_templatetags_raise_exception(self):
        """Validate that executing render_jinja2 with an invalid filter will raise TemplateAssertionError."""
        helpers_not_valid = ["notvalid"]

        for helper in helpers_not_valid:
            with self.assertRaises(TemplateAssertionError):
                render_jinja2("{{ data | " + helper + " }}", {"data": None})

    def test_templatetags_helpers_in_jinja(self):
        """
        Only validate that all templatetags helpers have been properly registered as Django Jinja
        no need to check the returned value since we already have some unit tests for that
        """

        helpers_to_validate = [
            "placeholder",
            "render_json",
            "render_yaml",
            "render_markdown",
            "meta",
            "viewname",
            "validated_viewname",
            "bettertitle",
            "humanize_speed",
            "tzoffset",
            "fgcolor",
            "divide",
            "percentage",
            "get_docs_url",
            "has_perms",
            "has_one_or_more_perms",
            "split",
            "as_range",
            "meters_to_feet",
            "get_item",
        ]

        # For each helper, try to render a jinja template with render_jinja2 and fail if TemplateAssertionError is raised
        for helper in helpers_to_validate:
            try:
                render_jinja2("{{ data | " + helper + " }}", {"data": None})
            except TemplateAssertionError:
                raise
            except Exception:
                pass

    def test_netutils_filters_in_jinja(self):
        """Import the list of all Jinja filters from Netutils and validate that all of them have been properly loaded in Django Jinja"""
        filters = jinja2_convenience_function()

        for filter_ in filters.keys():
            try:
                render_jinja2("{{ data | " + filter_ + " }}", {"data": None})
            except TemplateAssertionError:
                raise
            except Exception:
                pass
