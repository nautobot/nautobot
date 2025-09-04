from constance.test import override_config
from django.conf import settings
from django.templatetags.static import static
from django.test import override_settings, TestCase

from nautobot.core.templatetags import helpers
from nautobot.dcim import models
from nautobot.ipam.models import VLAN

from example_app.models import AnotherExampleModel, ExampleModel


class NautobotTemplatetagsHelperTest(TestCase):
    def test_hyperlinked_object(self):
        # None gives a placeholder
        self.assertEqual(helpers.hyperlinked_object(None), helpers.placeholder(None))
        # An object without get_absolute_url gives a string
        self.assertEqual(helpers.hyperlinked_object("hello"), "hello")
        # An object with get_absolute_url gives a hyperlink
        location = models.Location.objects.first()
        # Initially remove description if any
        location.description = ""
        location.save()
        self.assertEqual(
            helpers.hyperlinked_object(location), f'<a href="/dcim/locations/{location.pk}/">{location.display}</a>'
        )
        # An object with get_absolute_url and a description gives a titled hyperlink
        location.description = "An important location"
        location.save()
        self.assertEqual(
            helpers.hyperlinked_object(location),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location">{location.display}</a>',
        )
        # Optionally you can request a field other than the object's display string
        self.assertEqual(
            helpers.hyperlinked_object(location, "name"),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location">{location.name}</a>',
        )
        # If you request a nonexistent field, it defaults to the string representation
        self.assertEqual(
            helpers.hyperlinked_object(location, "foo"),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location">{location!s}</a>',
        )

    def test_hyperlinked_email(self):
        self.assertEqual(
            helpers.hyperlinked_email("admin@example.com"), '<a href="mailto:admin@example.com">admin@example.com</a>'
        )
        self.assertEqual(helpers.hyperlinked_email(None), '<span class="text-muted">&mdash;</span>')

    def test_hyperlinked_phone_number(self):
        self.assertEqual(helpers.hyperlinked_phone_number("555-1234"), '<a href="tel:555-1234">555-1234</a>')
        self.assertEqual(helpers.hyperlinked_phone_number(None), '<span class="text-muted">&mdash;</span>')

    def test_placeholder(self):
        self.assertEqual(helpers.placeholder(None), '<span class="text-muted">&mdash;</span>')
        self.assertEqual(helpers.placeholder([]), '<span class="text-muted">&mdash;</span>')
        self.assertEqual(helpers.placeholder("something"), "something")

    def test_pre_tag(self):
        self.assertEqual(helpers.pre_tag(None), '<span class="text-muted">&mdash;</span>')
        self.assertEqual(helpers.pre_tag([]), "<pre>[]</pre>")
        self.assertEqual(helpers.pre_tag("something"), "<pre>something</pre>")

    def test_add_html_id(self):
        # Case where what we have isn't actually a HTML element but just a bare string
        self.assertEqual(helpers.add_html_id("hello", "my-id"), "hello")
        # Basic success case
        self.assertEqual(helpers.add_html_id("<div></div>", "my-div"), '<div id="my-div" ></div>')
        # Cases of more complex HTML
        self.assertEqual(
            helpers.add_html_id('<a href="..." title="...">Hello!</a>', "my-a"),
            '<a id="my-a" href="..." title="...">Hello!</a>',
        )
        self.assertEqual(
            helpers.add_html_id('Hello\n<div class="...">\nGoodbye\n</div>', "my-div"),
            'Hello\n<div id="my-div" class="...">\nGoodbye\n</div>',
        )

    def test_render_markdown(self):
        self.assertTrue(callable(helpers.render_markdown))
        # Test common markdown formatting.
        self.assertEqual(helpers.render_markdown("**bold**"), "<p><strong>bold</strong></p>")
        self.assertEqual(helpers.render_markdown("__bold__"), "<p><strong>bold</strong></p>")
        self.assertEqual(helpers.render_markdown("_italics_"), "<p><em>italics</em></p>")
        self.assertEqual(helpers.render_markdown("*italics*"), "<p><em>italics</em></p>")
        self.assertEqual(
            helpers.render_markdown("**bold and _italics_**"), "<p><strong>bold and <em>italics</em></strong></p>"
        )
        self.assertEqual(helpers.render_markdown("* list"), "<ul>\n<li>list</li>\n</ul>")
        self.assertHTMLEqual(
            helpers.render_markdown("[I am a link](https://www.example.com)"),
            '<p><a href="https://www.example.com" rel="noopener noreferrer">I am a link</a></p>',
        )

    def test_render_markdown_security(self):
        self.assertEqual(helpers.render_markdown('<script>alert("XSS")</script>'), "")
        self.assertHTMLEqual(
            helpers.render_markdown('[link](javascript:alert("XSS"))'),
            '<p><a title="XSS" rel="noopener noreferrer">link</a>)</p>',  # the trailing ) seems weird to me, but...
        )
        self.assertHTMLEqual(
            helpers.render_markdown(
                "[link\nJS]"
                "(&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A"  # '(javascript:'
                "&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29)"  # 'alert("XSS"))'
            ),
            '<p><a rel="noopener noreferrer">link JS</a></p>',
        )

    def test_render_json(self):
        self.assertEqual(
            helpers.render_json({"syntax": "highlight"}),
            '<code class="language-json">{\n    &quot;syntax&quot;: &quot;highlight&quot;\n}</code>',
        )
        self.assertEqual(
            helpers.render_json({"first": [1, 2, 3]}, False),
            '{\n    "first": [\n        1,\n        2,\n        3\n    ]\n}',
        )
        self.assertEqual('"I am UTF-8! 😀"', helpers.render_json("I am UTF-8! 😀", False))

    def test_render_uptime(self):
        self.assertEqual(helpers.render_uptime(1024768), "11 days 20 hours 39 minutes")
        self.assertEqual(helpers.render_uptime(""), helpers.placeholder(""))
        self.assertEqual(helpers.render_uptime("123456"), "1 day 10 hours 17 minutes")
        self.assertEqual(helpers.render_uptime(0), "0 days 0 hours 0 minutes")
        self.assertEqual(helpers.render_uptime("foo bar"), helpers.placeholder("foo bar"))

    def test_render_yaml(self):
        self.assertEqual(
            helpers.render_yaml({"syntax": "highlight"}), '<code class="language-yaml">syntax: highlight\n</code>'
        )
        self.assertEqual("utf8:\n- 😀😀\n- 😀\n", helpers.render_yaml({"utf8": ["😀😀", "😀"]}, False))

    def test_meta(self):
        location = models.Location.objects.first()

        self.assertEqual(helpers.meta(location, "app_label"), "dcim")
        self.assertEqual(helpers.meta(models.Location, "app_label"), "dcim")
        self.assertEqual(helpers.meta(location, "not_present"), "")

        self.assertEqual(helpers.meta(ExampleModel, "app_label"), "example_app")

    def test_viewname(self):
        location = models.Location.objects.first()

        self.assertEqual(helpers.viewname(location, "edit"), "dcim:location_edit")
        self.assertEqual(helpers.viewname(models.Location, "test"), "dcim:location_test")

        self.assertEqual(helpers.viewname(ExampleModel, "edit"), "plugins:example_app:examplemodel_edit")

    def test_validated_viewname(self):
        location = models.Location.objects.first()

        self.assertEqual(helpers.validated_viewname(location, "list"), "dcim:location_list")
        self.assertIsNone(helpers.validated_viewname(models.Location, "notvalid"))

        self.assertEqual(helpers.validated_viewname(ExampleModel, "list"), "plugins:example_app:examplemodel_list")
        self.assertIsNone(helpers.validated_viewname(ExampleModel, "notvalid"))

    def test_validated_api_viewname(self):
        location = models.Location.objects.first()

        self.assertEqual(helpers.validated_api_viewname(location, "list"), "dcim-api:location-list")
        self.assertIsNone(helpers.validated_api_viewname(models.Location, "notvalid"))

        self.assertEqual(
            helpers.validated_api_viewname(ExampleModel, "list"), "plugins-api:example_app-api:examplemodel-list"
        )
        self.assertIsNone(helpers.validated_api_viewname(ExampleModel, "notvalid"))

        # Assert detail views get validated as well
        self.assertEqual(helpers.validated_api_viewname(location, "detail"), "dcim-api:location-detail")

    def test_bettertitle(self):
        self.assertEqual(helpers.bettertitle("myTITle"), "MyTITle")
        self.assertEqual(helpers.bettertitle("mytitle"), "Mytitle")
        self.assertEqual(helpers.bettertitle("my title"), "My Title")

    def test_humanize_speed(self):
        self.assertEqual(helpers.humanize_speed(1544), "1.544 Mbps")
        self.assertEqual(helpers.humanize_speed(100000), "100 Mbps")
        self.assertEqual(helpers.humanize_speed(10000000), "10 Gbps")

    def test_tzoffset(self):
        self.assertTrue(callable(helpers.tzoffset))
        # TODO add unit tests for tzoffset

    def test_fgcolor(self):
        self.assertEqual(helpers.fgcolor("#999999"), "#ffffff")
        self.assertEqual(helpers.fgcolor("#111111"), "#ffffff")
        self.assertEqual(helpers.fgcolor("#000000"), "#ffffff")
        self.assertEqual(helpers.fgcolor("#ffffff"), "#000000")

    def test_divide(self):
        self.assertEqual(helpers.divide(10, 3), 3)
        self.assertEqual(helpers.divide(12, 4), 3)
        self.assertEqual(helpers.divide(11, 3), 4)

    def test_percentage(self):
        self.assertEqual(helpers.percentage(2, 10), 20)
        self.assertEqual(helpers.percentage(10, 3), 333)

    def test_get_docs_url(self):
        self.assertTrue(callable(helpers.get_docs_url))
        location = models.Location.objects.first()
        self.assertEqual(helpers.get_docs_url(location), static("docs/user-guide/core-data-model/dcim/location.html"))
        example_model = ExampleModel.objects.create(name="test", number=1)
        self.assertEqual(helpers.get_docs_url(example_model), static("example_app/docs/models/examplemodel.html"))
        # AnotherExampleModel does not have documentation.
        another_model = AnotherExampleModel.objects.create(name="test", number=1)
        self.assertIsNone(helpers.get_docs_url(another_model))

    def test_has_perms(self):
        self.assertTrue(callable(helpers.has_perms))
        # TODO add unit tests for has_perms

    def test_has_one_or_more_perms(self):
        self.assertTrue(callable(helpers.has_one_or_more_perms))
        # TODO add more unit tests for has_one_or_more_perms

    def test_split(self):
        self.assertEqual(helpers.split("nothing"), ["nothing"])
        self.assertEqual(helpers.split("1,2,3"), ["1", "2", "3"])
        self.assertEqual(helpers.split("1,2,3", "|"), ["1,2,3"])
        self.assertEqual(helpers.split("1|2|3", "|"), ["1", "2", "3"])

    def test_as_range(self):
        self.assertEqual(helpers.as_range(2), range(0, 2))
        self.assertEqual(helpers.as_range("3"), range(0, 3))
        self.assertEqual(helpers.as_range("four"), [])

    def test_meters_to_feet(self):
        self.assertEqual(helpers.meters_to_feet(11), 36.08924)
        self.assertEqual(helpers.meters_to_feet("22"), 72.17848)

    def test_get_item(self):
        data = {"first": "1st", "second": "2nd"}
        self.assertEqual(helpers.get_item(data, "first"), "1st")
        self.assertEqual(helpers.get_item(data, "second"), "2nd")

    def test_render_boolean(self):
        for value in [True, "arbitrary string", 1]:
            self.assertEqual(
                helpers.render_boolean(value),
                '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>',
            )
        for value in [False, "", 0]:
            self.assertEqual(
                helpers.render_boolean(value),
                '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>',
            )
        self.assertEqual(helpers.render_boolean(None), '<span class="text-muted">&mdash;</span>')

    def test_hyperlinked_object_with_color(self):
        vlan_with_role = VLAN.objects.filter(role__isnull=False).first()
        role = vlan_with_role.role
        color = role.color
        fbcolor = helpers.fgcolor(color)
        display = helpers.hyperlinked_object(role)
        self.assertEqual(
            helpers.hyperlinked_object_with_color(obj=role),
            f'<span class="label" style="color: {fbcolor}; background-color: #{color}">{display}</span>',
        )
        # Assert when obj is None
        self.assertEqual(helpers.hyperlinked_object_with_color(obj=None), '<span class="text-muted">&mdash;</span>')

    @override_settings(BANNER_TOP="¡Hola, mundo!")
    @override_config(example_app__SAMPLE_VARIABLE="Testing")
    def test_settings_or_config(self):
        self.assertEqual(helpers.settings_or_config("BANNER_TOP"), "¡Hola, mundo!")
        self.assertEqual(helpers.settings_or_config("SAMPLE_VARIABLE", "example_app"), "Testing")

    def test_support_message(self):
        """Test the `support_message` tag with config and settings."""
        with override_settings():
            del settings.SUPPORT_MESSAGE
            with override_config():
                self.assertHTMLEqual(
                    helpers.support_message(),
                    "<p>If further assistance is required, please join the <code>#nautobot</code> channel "
                    'on <a href="https://slack.networktocode.com/" rel="noopener noreferrer">Network to Code\'s '
                    "Slack community</a> and post your question.</p>",
                )

            with override_config(SUPPORT_MESSAGE="Reach out to your support team for assistance."):
                self.assertHTMLEqual(
                    helpers.support_message(),
                    "<p>Reach out to your support team for assistance.</p>",
                )

        with override_settings(SUPPORT_MESSAGE="Settings **support** message:\n\n- Item 1\n- Item 2"):
            with override_config(SUPPORT_MESSAGE="Config support message"):
                self.assertHTMLEqual(
                    helpers.support_message(),
                    "<p>Settings <strong>support</strong> message:</p><ul><li>Item 1</li><li>Item 2</li></ul>",
                )

    def test_hyperlinked_object_target_new_tab(self):
        # None gives a placeholder
        self.assertEqual(helpers.hyperlinked_object_target_new_tab(None), helpers.placeholder(None))
        # An object without get_absolute_url gives a string
        self.assertEqual(helpers.hyperlinked_object_target_new_tab("hello"), "hello")
        # An object with get_absolute_url gives a hyperlink
        location = models.Location.objects.first()
        # Initially remove description if any
        location.description = ""
        location.save()
        self.assertEqual(
            helpers.hyperlinked_object_target_new_tab(location),
            f'<a href="/dcim/locations/{location.pk}/" target="_blank" rel="noreferrer">{location.display}</a>',
        )
        # An object with get_absolute_url and a description gives a titled hyperlink
        location.description = "An important location"
        location.save()
        self.assertEqual(
            helpers.hyperlinked_object_target_new_tab(location),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location" target="_blank" rel="noreferrer">{location.display}</a>',
        )
        # Optionally you can request a field other than the object's display string
        self.assertEqual(
            helpers.hyperlinked_object_target_new_tab(location, "name"),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location" target="_blank" rel="noreferrer">{location.name}</a>',
        )
        # If you request a nonexistent field, it defaults to the string representation
        self.assertEqual(
            helpers.hyperlinked_object_target_new_tab(location, "foo"),
            f'<a href="/dcim/locations/{location.pk}/" title="An important location" target="_blank" rel="noreferrer">{location!s}</a>',
        )

    def test_dbm(self):
        self.assertEqual(
            helpers.dbm(12),
            "12 dBm",
        )
        self.assertEqual(
            helpers.dbm(-85),
            "-85 dBm",
        )
        self.assertEqual(helpers.dbm(None), helpers.placeholder(None))
