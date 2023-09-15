import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.extras.models import Role, Status
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer


def create_test_device():
    test_uuid = str(uuid.uuid4())
    device_role, _ = Role.objects.get_or_create(name="Device Role")
    device_ct = ContentType.objects.get_for_model(Device)
    device_role.content_types.add(device_ct)
    manufacturer = Manufacturer.objects.create(
        name=f"Test Manufacturer {test_uuid}",
    )
    device_type = DeviceType.objects.create(manufacturer=manufacturer, model=f"Test Model {test_uuid}")
    location_type = LocationType.objects.create(name=f"Test Location Type {test_uuid}")
    location_type.content_types.add(ContentType.objects.get_for_model(Device))
    location_status = Status.objects.get_for_model(Location).first()
    location = Location.objects.create(
        name=f"Test Location {test_uuid}",
        status=location_status,
        location_type=location_type,
    )
    device = Device.objects.create(
        name=f"Test Device {test_uuid}",
        role=device_role,
        device_type=device_type,
        location=location,
        status=location_status,
    )
    return device
