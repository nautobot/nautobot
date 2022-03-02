import uuid

from nautobot.extras.models import Status
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site


def create_test_device():
    test_uuid = str(uuid.uuid4())
    device_role = DeviceRole.objects.create(
        name=f"Test Role {test_uuid}",
        slug=f"test-role-{test_uuid}",
    )
    manufacturer = Manufacturer.objects.create(
        name=f"Test Manufacturer {test_uuid}",
        slug=f"test-manufacturer-{test_uuid}",
    )
    device_type = DeviceType.objects.create(
        manufacturer=manufacturer, model=f"Test Model {test_uuid}", slug=f"test-model-{test_uuid}"
    )
    site = Site.objects.create(
        name=f"Test Site {test_uuid}",
        slug=f"test-site-{test_uuid}",
        status=Status.objects.get_for_model(Site).get(slug="active"),
    )
    device = Device.objects.create(
        name=f"Test Device {test_uuid}",
        device_role=device_role,
        device_type=device_type,
        site=site,
        status=Status.objects.get_for_model(Device).get(slug="active"),
    )
    return device
