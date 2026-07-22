import json

from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Module, ModuleBay, ModuleType
from nautobot.extras.models import Status
from nautobot.extras.tests.integration import create_test_device

# The module-bays panel header renders this "Expand all" toggle (an HTMX `.btn`) only when the device has
# nested module bays. It is our real-world test subject for the icon-swap path.
EXPAND_BUTTON = "a.btn[hx-get*='expand_all=true']"
EXPAND_BUTTON_ICON = f"{EXPAND_BUTTON} span.mdi"
NO_ICON_BUTTON = "#nb-spinner-test-btn"

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

    def _dispatch_htmx_event(self, css_selector, event_name):
        """Fire an HTMX lifecycle event on the matched element, mimicking what HTMX dispatches during a request."""
        self.browser.execute_script(
            f"var el = document.querySelector({json.dumps(css_selector)});"
            f"el.dispatchEvent(new CustomEvent({json.dumps(event_name)}, "
            "{bubbles: true, detail: {elt: el}}));"
        )

    def _class_of(self, css_selector):
        return self.browser.evaluate_script(f"document.querySelector({json.dumps(css_selector)}).className")

    def test_spinner_replaces_icon_during_htmx_request(self):
        # The "Expand all" button carries a leading MDI icon, so the spinner should swap that icon's classes.
        self.assertTrue(
            self.browser.is_element_present_by_css(EXPAND_BUTTON, wait_time=5),
            "The module-bays 'Expand all' HTMX button was not rendered.",
        )
        original_class = self._class_of(EXPAND_BUTTON_ICON)
        self.assertIn(EXPAND_ICON_CLASS, original_class)
        self.assertNotIn(SPINNER_CLASS, original_class)

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:beforeRequest")
        during_class = self._class_of(EXPAND_BUTTON_ICON)
        self.assertIn(SPINNER_CLASS, during_class, "Icon was not replaced by the spinner on htmx:beforeRequest.")
        self.assertNotIn(EXPAND_ICON_CLASS, during_class)

        self._dispatch_htmx_event(EXPAND_BUTTON, "htmx:afterRequest")
        restored_class = self._class_of(EXPAND_BUTTON_ICON)
        self.assertEqual(restored_class, original_class, "Original icon was not restored on htmx:afterRequest.")

    def test_spinner_prepended_when_button_has_no_icon(self):
        # Inject an icon-less `.btn` on the loaded page (the bundle's body-level listeners are already active).
        self.browser.execute_script(
            "var b = document.createElement('button');"
            "b.className = 'btn btn-primary';"
            "b.id = 'nb-spinner-test-btn';"
            "b.textContent = 'Save';"
            "document.body.appendChild(b);"
        )
        injected_selector = f"{NO_ICON_BUTTON} [data-nb-injected-spinner]"
        self.assertEqual(
            self.browser.evaluate_script(f"document.querySelectorAll({json.dumps(injected_selector)}).length"),
            0,
        )

        self._dispatch_htmx_event(NO_ICON_BUTTON, "htmx:beforeRequest")
        self.assertEqual(
            self.browser.evaluate_script(f"document.querySelectorAll({json.dumps(injected_selector)}).length"),
            1,
            "A spinner span was not prepended to the icon-less button on htmx:beforeRequest.",
        )
        self.assertIn(SPINNER_CLASS, self._class_of(injected_selector))
        self.assertTrue(
            self.browser.evaluate_script(
                f"document.querySelector({json.dumps(NO_ICON_BUTTON)})"
                ".firstElementChild.hasAttribute('data-nb-injected-spinner')"
            ),
            "The spinner was not inserted as the first child (before the label).",
        )

        self._dispatch_htmx_event(NO_ICON_BUTTON, "htmx:afterRequest")
        self.assertEqual(
            self.browser.evaluate_script(f"document.querySelectorAll({json.dumps(injected_selector)}).length"),
            0,
            "The injected spinner was not removed on htmx:afterRequest.",
        )
        self.assertIn(
            "Save", self.browser.evaluate_script(f"document.querySelector({json.dumps(NO_ICON_BUTTON)}).textContent")
        )
