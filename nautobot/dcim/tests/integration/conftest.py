"""DCIM Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects a DCIM test starts from.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

from nautobot.dcim.tests.integration.pages.devices_page import DevicesPage


@pytest.fixture
def device_bulk_edit_form(auth_page, base_url, created_device):
    """The bulk edit form for `created_device`, opened from the device list filtered by its device type."""
    devices = DevicesPage(auth_page, base_url)
    devices.navigate(device_type=created_device["device_type"]["id"])
    devices.select_row(created_device["device"]["name"])
    devices.click_edit_selected()
    return devices


@pytest.fixture
def created_pdu(create_object, created_device):
    """created_device plus a power port and a power outlet. The Power Utilization panel renders only for a device with both."""
    device_id = created_device["device"]["id"]
    # The panel's first column header is "Input", so a port with that name would pass on the header alone.
    power_port = create_object("dcim/power-ports/", device=device_id, name="Inlet A")
    power_outlet = create_object("dcim/power-outlets/", device=device_id, name="Outlet A", power_port=power_port["id"])
    return {**created_device, "power_port": power_port, "power_outlet": power_outlet}
