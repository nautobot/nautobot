import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status


def create_test_device(name=None, location_name=None, test_uuid=None):
    if not test_uuid:
        test_uuid = str(uuid.uuid4())
    if not name:
        name = f"Test Device {test_uuid}"
    if not location_name:
        location_name = f"Test Location {test_uuid}"

    location_type, location_type_created = LocationType.objects.get_or_create(name=f"Test Location Type {test_uuid}")
    if location_type_created:
        location_type.content_types.add(ContentType.objects.get_for_model(Device))
        location_type.save()

    location_status = Status.objects.get_for_model(Location).first()
    location, _ = Location.objects.get_or_create(
        name=location_name,
        status=location_status,
        location_type=location_type,
    )

    device_role, device_role_created = Role.objects.get_or_create(name="Device Role")
    if device_role_created:
        device_role.content_types.add(ContentType.objects.get_for_model(Device))
        device_role.save()

    manufacturer, _ = Manufacturer.objects.get_or_create(
        name=f"Test Manufacturer {test_uuid}",
    )

    device_type, _ = DeviceType.objects.get_or_create(manufacturer=manufacturer, model=f"Test Model {test_uuid}")

    return Device.objects.create(
        name=name,
        role=device_role,
        device_type=device_type,
        location=location,
        status=location_status,
    )
