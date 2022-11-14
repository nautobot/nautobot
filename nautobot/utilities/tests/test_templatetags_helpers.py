from django.test import TestCase
from django.templatetags.static import static
from django.conf import settings
from unittest import skipIf

from nautobot.utilities.templatetags.helpers import (
    hyperlinked_object,
    placeholder,
    add_html_id,
    render_boolean,
    render_json,
    render_yaml,
    render_markdown,
    meta,
    viewname,
    validated_viewname,
    bettertitle,
    humanize_speed,
    tzoffset,
    fgcolor,
    divide,
    percentage,
    get_docs_url,
    has_perms,
    has_one_or_more_perms,
    split,
    as_range,
    meters_to_feet,
    get_item,
)
from nautobot.dcim.models import Site
from example_plugin.models import AnotherExampleModel, ExampleModel


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class NautobotTemplatetagsHelperTest(TestCase):
    def test_hyperlinked_object(self):
        # None gives a placeholder
        self.assertEqual(hyperlinked_object(None), placeholder(None))
        # An object without get_absolute_url gives a string
        self.assertEqual(hyperlinked_object("hello"), "hello")
        # An object with get_absolute_url gives a hyperlink
        site = Site.objects.first()
        self.assertEqual(hyperlinked_object(site), f'<a href="/dcim/sites/{site.slug}/">{site.name}</a>')
        # An object with get_absolute_url and a description gives a titled hyperlink
        site.description = "An important site"
        site.save()
        self.assertEqual(
            hyperlinked_object(site), f'<a href="/dcim/sites/{site.slug}/" title="An important site">{site.name}</a>'
        )
        # Optionally you can request a field other than the object's display string
        self.assertEqual(
            hyperlinked_object(site, "slug"),
            f'<a href="/dcim/sites/{site.slug}/" title="An important site">{site.slug}</a>',
        )
        # If you request a nonexistent field, it defaults to the string representation
        self.assertEqual(
            hyperlinked_object(site, "foo"),
            f'<a href="/dcim/sites/{site.slug}/" title="An important site">{site!s}</a>',
        )

    def test_placeholder(self):
        self.assertEqual(placeholder(None), '<span class="text-muted">&mdash;</span>')
        self.assertEqual(placeholder([]), '<span class="text-muted">&mdash;</span>')
        self.assertEqual(placeholder("something"), "something")

    def test_add_html_id(self):
        # Case where what we have isn't actually a HTML element but just a bare string
        self.assertEqual(add_html_id("hello", "my-id"), "hello")
        # Basic success case
        self.assertEqual(add_html_id("<div></div>", "my-div"), '<div id="my-div" ></div>')
        # Cases of more complex HTML
        self.assertEqual(
            add_html_id('<a href="..." title="...">Hello!</a>', "my-a"),
            '<a id="my-a" href="..." title="...">Hello!</a>',
        )
        self.assertEqual(
            add_html_id('Hello\n<div class="...">\nGoodbye\n</div>', "my-div"),
            'Hello\n<div id="my-div" class="...">\nGoodbye\n</div>',
        )

    def test_render_markdown(self):
        self.assertTrue(callable(render_markdown))
        # Test common markdown formatting.
        self.assertEqual(render_markdown("**bold**"), "<p><strong>bold</strong></p>")
        self.assertEqual(render_markdown("__bold__"), "<p><strong>bold</strong></p>")
        self.assertEqual(render_markdown("_italics_"), "<p><em>italics</em></p>")
        self.assertEqual(render_markdown("*italics*"), "<p><em>italics</em></p>")
        self.assertEqual(render_markdown("**bold and _italics_**"), "<p><strong>bold and <em>italics</em></strong></p>")
        self.assertEqual(render_markdown("* list"), "<ul>\n<li>list</li>\n</ul>")
        self.assertEqual(
            render_markdown("[I am a link](https://www.example.com)"),
            '<p><a href="https://www.example.com">I am a link</a></p>',
        )

    def test_render_json(self):
        self.assertEqual(
            render_json({"first": [1, 2, 3]}), '{\n    "first": [\n        1,\n        2,\n        3\n    ]\n}'
        )
        self.assertEqual('"I am UTF-8! 😀"', render_json("I am UTF-8! 😀"))

    def test_render_yaml(self):
        self.assertEqual("utf8:\n- 😀😀\n- 😀\n", render_yaml({"utf8": ["😀😀", "😀"]}))

    def test_meta(self):
        site = Site.objects.first()

        self.assertEqual(meta(site, "app_label"), "dcim")
        self.assertEqual(meta(Site, "app_label"), "dcim")
        self.assertEqual(meta(site, "not_present"), "")

        self.assertEqual(meta(ExampleModel, "app_label"), "example_plugin")

    def test_viewname(self):
        site = Site.objects.first()

        self.assertEqual(viewname(site, "edit"), "dcim:site_edit")
        self.assertEqual(viewname(Site, "test"), "dcim:site_test")

        self.assertEqual(viewname(ExampleModel, "edit"), "plugins:example_plugin:examplemodel_edit")

    def test_validated_viewname(self):
        site = Site.objects.first()

        self.assertEqual(validated_viewname(site, "list"), "dcim:site_list")
        self.assertIsNone(validated_viewname(Site, "notvalid"))

        self.assertEqual(validated_viewname(ExampleModel, "list"), "plugins:example_plugin:examplemodel_list")
        self.assertIsNone(validated_viewname(ExampleModel, "notvalid"))

    def test_bettertitle(self):
        self.assertEqual(bettertitle("myTITle"), "MyTITle")
        self.assertEqual(bettertitle("mytitle"), "Mytitle")
        self.assertEqual(bettertitle("my title"), "My Title")

    def test_humanize_speed(self):
        self.assertEqual(humanize_speed(1544), "1.544 Mbps")
        self.assertEqual(humanize_speed(100000), "100 Mbps")
        self.assertEqual(humanize_speed(10000000), "10 Gbps")

    def test_tzoffset(self):
        self.assertTrue(callable(tzoffset))
        # TODO add unit tests for tzoffset

    def test_fgcolor(self):
        self.assertEqual(fgcolor("#999999"), "#ffffff")
        self.assertEqual(fgcolor("#111111"), "#ffffff")
        self.assertEqual(fgcolor("#000000"), "#ffffff")
        self.assertEqual(fgcolor("#ffffff"), "#000000")

    def test_divide(self):
        self.assertEqual(divide(10, 3), 3)
        self.assertEqual(divide(12, 4), 3)
        self.assertEqual(divide(11, 3), 4)

    def test_percentage(self):
        self.assertEqual(percentage(2, 10), 20)
        self.assertEqual(percentage(10, 3), 333)

    def test_get_docs_url(self):
        self.assertTrue(callable(get_docs_url))
        site = Site.objects.first()
        self.assertEqual(get_docs_url(site), static("docs/models/dcim/site.html"))
        example_model = ExampleModel.objects.create(name="test", number=1)
        self.assertEqual(get_docs_url(example_model), static("example_plugin/docs/models/examplemodel.html"))
        # AnotherExampleModel does not have documentation.
        another_model = AnotherExampleModel.objects.create(name="test", number=1)
        self.assertIsNone(get_docs_url(another_model))

    def test_has_perms(self):
        self.assertTrue(callable(has_perms))
        # TODO add unit tests for has_perms

    def test_has_one_or_more_perms(self):
        self.assertTrue(callable(has_one_or_more_perms))
        # TODO add more unit tests for has_one_or_more_perms

    def test_split(self):
        self.assertEqual(split("nothing"), ["nothing"])
        self.assertEqual(split("1,2,3"), ["1", "2", "3"])
        self.assertEqual(split("1,2,3", "|"), ["1,2,3"])
        self.assertEqual(split("1|2|3", "|"), ["1", "2", "3"])

    def test_as_range(self):
        self.assertEqual(as_range(2), range(0, 2))
        self.assertEqual(as_range("3"), range(0, 3))
        self.assertEqual(as_range("four"), [])

    def test_meters_to_feet(self):
        self.assertEqual(meters_to_feet(11), 36.08924)
        self.assertEqual(meters_to_feet("22"), 72.17848)

    def test_get_item(self):
        data = {"first": "1st", "second": "2nd"}
        self.assertEqual(get_item(data, "first"), "1st")
        self.assertEqual(get_item(data, "second"), "2nd")

    def test_render_boolean(self):
        for value in [True, "arbitrary string", 1]:
            self.assertEqual(
                render_boolean(value),
                '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>',
            )
        for value in [False, "", 0]:
            self.assertEqual(
                render_boolean(value), '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>'
            )
        self.assertEqual(render_boolean(None), '<span class="text-muted">&mdash;</span>')
