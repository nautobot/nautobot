"""Page object for the Device create form (/dcim/devices/add/)."""

from nautobot.playwright.create_form_page import CreateFormPage


class DeviceCreatePage(CreateFormPage):
    """The Device create form."""

    ADD_PATH = "/dcim/devices/add/"

    def fill_required_fields(self, name, location, device_type, role, status):
        """Fill the name and pick the required related records, given as API records."""
        self.fill_input("name", name)
        self.pick_related("role", role)
        # The API search does not match a device type's "<manufacturer> <model>" display text.
        self.pick_related("device_type", device_type, search=device_type["model"])
        self.pick_related("location", location)
        self.pick_related("status", status)
