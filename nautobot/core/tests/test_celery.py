import json
from uuid import uuid4

from nautobot.core import celery
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device


class CeleryTest(TestCase):
    def test__dumps(self):
        self.assertEqual('"I am UTF-8! 😀"', celery._dumps("I am UTF-8! 😀"))

    def test__dumps_and__loads_handle_model_instances_but_warn(self):
        device = Device.objects.first()
        self.assertIsNotNone(device)
        with self.assertWarns(DeprecationWarning):
            json_data = celery._dumps(device)

        self.assertEqual(
            json_data,
            json.dumps(
                {
                    "id": str(device.id),
                    "__nautobot_type__": "nautobot.dcim.models.devices.Device",
                    "display": device.display,
                },
                ensure_ascii=False,
            ),
        )

        with self.assertWarns(DeprecationWarning):
            device_obj = celery._loads(json_data)

        self.assertEqual(device_obj.id, device.id)

    def test__dumps_tags(self):
        device = Device.objects.filter(tags__isnull=False).first()
        self.assertIsNotNone(device)
        with self.assertWarns(DeprecationWarning):
            json_data = celery._dumps(device.tags)

        self.assertEqual(
            json_data, json.dumps([str(val) for val in device.tags.values_list("id", flat=True)], ensure_ascii=False)
        )

    def test__loads_unknown_type(self):
        with self.assertRaises(TypeError):
            celery._loads(
                json.dumps(
                    {
                        "id": str(uuid4()),
                        "__nautobot_type__": "nautobot.invalid.module.path",
                        "display": "ignored",
                    },
                    ensure_ascii=False,
                )
            )
