"""Page object for the Device create form (/dcim/devices/add/), the form the embedded-action tests start from."""

from nautobot.playwright.form_page import FormPage


class DeviceFormPage(FormPage):
    """The Device create form. Its related fields carry both embedded actions, and some prefill a content type."""

    ADD_PATH = "/dcim/devices/add/"
