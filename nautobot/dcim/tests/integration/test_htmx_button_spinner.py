import json

from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Module, ModuleBay, ModuleType
from nautobot.extras.models import Status
from nautobot.extras.tests.integration import create_test_device

# The module-bays panel header renders this "Expand all" toggle (an HTMX `.btn`) only when the device has
# nested module bays. It is our real-world test subject for both spinner paths.
EXPAND_BUTTON = "a.btn[hx-get*='expand_all=true']"
EXPAND_BUTTON_ICON = f"{EXPAND_BUTTON} span.mdi"
INJECTED_SPINNER = f"{EXPAND_BUTTON} [data-nb-injected-spinner]"

SPINNER_CLASS = "spinner-border"
EXPAND_ICON_CLASS = "mdi-arrow-expand-vertical"


class HtmxButtonSpinnerTestCase(SeleniumTestCase):
    """Integration tests for the global HTMX button spinner (`htmx-button-spinner.js`).

    Rather than race a real request (the spinner is transient and vanishes on swap), these dispatch the same
    lifecycle events HTMX fires -- `htmx:beforeRequest` and `htmx:afterRequest` -- so the resulting DOM state is
    stable to assert. This is the pattern existing integration tests use to drive JS behavior (see `test_jobs.py`).
    """

    def setUp(self):
        super().setUp()
        # Build a device with a nested module (bay -> module -> nested bay -> module) so the "Expand all" toggle
        # renders. `create_test_device` supplies the location/role/manufacturer/device-type prerequisites.
        self.device = create_test_device("HTMX Spinner Test Device")
        module_status = Status.objects.get_for_model(Module).first()
        module_type = ModuleType.objects.create(
            manufacturer=self.device.device_type.manufacturer, model="HTMX Spinner Test Module"
        )
        top_bay = ModuleBay(parent_device=self.device, name="Slot 0", position="0")
        top_bay.validated_save()
        top_module = Module(module_type=module_type, status=module_status, parent_module_bay=top_bay, serial="TOP")
        top_module.validated_save()
        nested_bay = ModuleBay(parent_module=top_module, name="Sub 0/0", position="0/0")
        nested_bay.validated_save()
        nested_module = Module(
            module_type=module_type, status=module_status, parent_module_bay=nested_bay, serial="NESTED"
        )
        nested_module.validated_save()

        self.login_as_superuser()
        self.browser.visit(self.live_server_url + reverse("dcim:device_modulebays", kwargs={"pk": self.device.pk}))
        self.assertTrue(
            self.browser.is_element_present_by_css(EXPAND_BUTTON, wait_time=5),
            "The module-bays 'Expand all' HTMX button was not rendered.",
        )

    def _dispatch_htmx_event(self, css_selector, event_name):
        """Fire an HTMX lifecycle event on the matched element, mimicking what HTMX dispatches during a request."""
        self.browser.execute_script(
            f"var el = document.querySelector({json.dumps(css_selector)});"
            f"el.dispatchEvent(new CustomEvent({json.dumps(event_name)}, "
            "{bubbles: true, detail: {elt: el}}));"
        )

    def test_spinner_replaces_icon_during_htmx_request(self):
        # The "Expand all" button carries a leading MDI icon, so the spinner should swap that icon's classes.
        # The same element handle stays valid throughout -- only its `class` attribute changes.
        icon = self.browser.find_by_css(EXPAND_BUTTON_ICON).first
        original_class = icon["class"]
        self.assertTrue(icon.has_class(EXPAND_ICON_CLASS))
        self.assertFalse(icon.has_class(SPINNER_CLASS))

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:beforeRequest")
        self.assertTrue(icon.has_class(SPINNER_CLASS), "Icon was not replaced by the spinner on htmx:beforeRequest.")
        self.assertFalse(icon.has_class(EXPAND_ICON_CLASS))

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:afterRequest")
        self.assertEqual(icon["class"], original_class, "Original icon was not restored on htmx:afterRequest.")

    def test_spinner_prepended_when_button_has_no_icon(self):
        # Remove the real button's icon so the same button exercises the no-icon (injected spinner) path.
        self.browser.execute_script(f"document.querySelector({json.dumps(EXPAND_BUTTON_ICON)}).remove();")
        self.assertTrue(self.browser.is_element_not_present_by_css(INJECTED_SPINNER))

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:beforeRequest")
        spinners = self.browser.find_by_css(INJECTED_SPINNER)
        self.assertEqual(
            len(spinners), 1, "A spinner span was not prepended to the icon-less button on htmx:beforeRequest."
        )
        self.assertTrue(spinners.first.has_class(SPINNER_CLASS))
        self.assertTrue(spinners.first.has_class("me-4"))
        self.assertTrue(
            self.browser.is_element_present_by_css(f"{INJECTED_SPINNER}:first-child"),
            "The spinner was not inserted as the first child (before the label).",
        )

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:afterRequest")
        self.assertTrue(
            self.browser.is_element_not_present_by_css(INJECTED_SPINNER),
            "The injected spinner was not removed on htmx:afterRequest.",
        )
        # `textContent`, not `.text`: the panel header is styled `text-transform: uppercase`, so the
        # rendered text is "EXPAND ALL" while the label markup remains untouched.
        self.assertIn("Expand All", self.browser.find_by_css(EXPAND_BUTTON).first["textContent"])
