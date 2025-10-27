from django.template import Context

from nautobot.core.templatetags import ui_framework
from nautobot.core.testing import TestCase
from nautobot.core.ui.breadcrumbs import Breadcrumbs
from nautobot.core.ui.titles import Titles


class NautobotTemplatetagsUIComponentsTest(TestCase):
    """Tests template tags from ui_framework module."""

    # ---------------------------
    # render_title
    # ---------------------------

    def test_render_title_with_legacy_title_present(self):
        context = Context(
            {
                "title": "Custom Title",
                "view_titles": Titles(),
                "verbose_name_plural": "Default Title",
            }
        )
        output = ui_framework.render_title(context)

        self.assertEqual(output, "Custom Title")

    def test_render_title_with_view_titles_only(self):
        context = Context(
            {
                "view_titles": Titles(),
                "verbose_name_plural": "Default Title",
            }
        )
        output = ui_framework.render_title(context)

        self.assertEqual(output, "Default Title")

    def test_render_title_with_invalid_view_titles(self):
        class MyStuff:
            pass

        context = Context(
            {
                "view_titles": MyStuff(),
                "verbose_name_plural": "Default Title",
            }
        )
        output = ui_framework.render_title(context)

        self.assertEqual(output, "")

    def test_render_title_with_empty_context(self):
        context = Context({})
        output = ui_framework.render_title(context)

        self.assertEqual(output, "")

    # ---------------------------
    # render_breadcrumbs
    # ---------------------------

    def test_render_breadcrumbs(self):
        context = Context(
            {
                "list_url": "home",
                "title": "New Home",
                "detail": True,
                "breadcrumbs": Breadcrumbs(),
            }
        )
        output = ui_framework.render_breadcrumbs(context)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">New Home</a></li></ol></nav>',
        )

    def test_render_breadcrumbs_empty_context(self):
        context = Context({})
        output = ui_framework.render_breadcrumbs(context)

        self.assertHTMLEqual(output, '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"></ol></nav>')

    def test_render_breadcrumbs_with_legacy_breadcrumbs(self):
        legacy_breadcrumbs = '<li class="breadcrumb-item"><a href="/">Home</a></li>'
        context = Context({})
        output = ui_framework.render_breadcrumbs(context, legacy_breadcrumbs)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">Home</a></li></ol></nav>',
        )

    def test_render_breadcrumbs_with_legacy_and_block_breadcrumbs_the_same_with_breadcrumbs_class(self):
        legacy_breadcrumbs = block_breadcrumbs = '<li class="breadcrumb-item"><a href="/">Home</a></li>'
        context = Context(
            {
                "list_url": "home",
                "title": "New Home",
                "detail": True,
                "breadcrumbs": Breadcrumbs(),
            }
        )
        output = ui_framework.render_breadcrumbs(context, legacy_breadcrumbs, block_breadcrumbs)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">New Home</a></li></ol></nav>',
        )

    def test_render_breadcrumbs_with_legacy_and_block_breadcrumbs_the_same_and_no_breadcrumbs_class(self):
        legacy_breadcrumbs = block_breadcrumbs = '<li class="breadcrumb-item"><a href="/">Home</a></li>'
        context = Context({})
        output = ui_framework.render_breadcrumbs(context, legacy_breadcrumbs, block_breadcrumbs)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">Home</a></li></ol></nav>',
        )

    def test_render_breadcrumbs_with_legacy_breadcrumbs_override(self):
        legacy_breadcrumbs = '<li class="breadcrumb-item"><a href="/">Home</a></li>'
        block_breadcrumbs = '<li class="breadcrumb-item"><a href="/">Override</a></li>'
        context = Context(
            {
                "list_url": "home",
                "title": "New Home",
                "detail": True,
                "breadcrumbs": Breadcrumbs(),
            }
        )
        output = ui_framework.render_breadcrumbs(context, legacy_breadcrumbs, block_breadcrumbs)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">Override</a></li></ol></nav>',
        )

    def test_render_breadcrumbs_strips_tags(self):
        legacy_breadcrumbs = """
        <li class="breadcrumb-item">
            <a href="/">Home</a>
        </li>"""

        block_breadcrumbs = """<li class="breadcrumb-item">

            <a href="/">Home</a></li>
        """

        context = Context(
            {
                "list_url": "home",
                "title": "New Home",
                "detail": True,
                "breadcrumbs": Breadcrumbs(),
            }
        )
        output = ui_framework.render_breadcrumbs(context, legacy_breadcrumbs, block_breadcrumbs)

        self.assertHTMLEqual(
            output,
            '<nav aria-label="Breadcrumbs" class="mt-1"><ol class="breadcrumb"><li class="breadcrumb-item"><a href="/">New Home</a></li></ol></nav>',
        )
