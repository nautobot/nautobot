from nautobot.core.testing.models import ModelTestCases
from nautobot.wireless import models


class AccessPointGroupTestCase(ModelTestCases.BaseModelTestCase):
    model = models.AccessPointGroup


class SupportedDataRateTestCase(ModelTestCases.BaseModelTestCase):
    model = models.SupportedDataRate


class RadioProfileTestCase(ModelTestCases.BaseModelTestCase):
    model = models.RadioProfile


class WirelessNetworkTestCase(ModelTestCases.BaseModelTestCase):
    model = models.WirelessNetwork


class AccessPointGroupWirelessNetworkAssignmentTestCase(ModelTestCases.BaseModelTestCase):
    model = models.AccessPointGroupWirelessNetworkAssignment


class AccessPointGroupRadioProfileTestCase(ModelTestCases.BaseModelTestCase):
    model = models.AccessPointGroupRadioProfileAssignment


class AccessPointGroupDeviceAssignmentTestCase(ModelTestCases.BaseModelTestCase):
    model = models.AccessPointGroupDeviceAssignment
