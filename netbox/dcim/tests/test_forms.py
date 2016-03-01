from django.test import TestCase
from dcim.forms import *
from dcim.models import *


def get_id(model, slug):
    return model.objects.get(slug=slug).id


class DeviceTestCase(TestCase):

    fixtures = ['dcim', 'ipam']

    def test_racked_device(self):
        test = DeviceForm(data={
            'device_role': get_id(DeviceRole, 'leaf-switch'),
            'name': 'test',
            'site': get_id(Site, 'test1'),
            'face': RACK_FACE_FRONT,
            'platform': get_id(Platform, 'juniper-junos'),
            'device_type': get_id(DeviceType, 'qfx5100-48s'),
            'position': 41,
            'rack': '1',
            'manufacturer': get_id(Manufacturer, 'juniper'),
        })
        self.assertTrue(test.is_valid(), test.fields['position'].choices)
        self.assertTrue(test.save())

    def test_racked_device_occupied(self):
        test = DeviceForm(data={
            'device_role': get_id(DeviceRole, 'leaf-switch'),
            'name': 'test',
            'site': get_id(Site, 'test1'),
            'face': RACK_FACE_FRONT,
            'platform': get_id(Platform, 'juniper-junos'),
            'device_type': get_id(DeviceType, 'qfx5100-48s'),
            'position': 1,
            'rack': '1',
            'manufacturer': get_id(Manufacturer, 'juniper'),
        })
        self.assertFalse(test.is_valid())

    def test_non_racked_device(self):
        test = DeviceForm(data={
            'device_role': get_id(DeviceRole, 'pdu'),
            'name': 'test',
            'site': get_id(Site, 'test1'),
            'face': None,
            'platform': None,
            'device_type': get_id(DeviceType, 'cwg-24vym415c9'),
            'position': None,
            'rack': '1',
            'manufacturer': get_id(Manufacturer, 'servertech'),
        })
        self.assertTrue(test.is_valid())
        self.assertTrue(test.save())

    def test_non_racked_device_with_face(self):
        test = DeviceForm(data={
            'device_role': get_id(DeviceRole, 'pdu'),
            'name': 'test',
            'site': get_id(Site, 'test1'),
            'face': RACK_FACE_REAR,
            'platform': None,
            'device_type': get_id(DeviceType, 'cwg-24vym415c9'),
            'position': None,
            'rack': '1',
            'manufacturer': get_id(Manufacturer, 'servertech'),
        })
        self.assertTrue(test.is_valid())
        self.assertTrue(test.save())
