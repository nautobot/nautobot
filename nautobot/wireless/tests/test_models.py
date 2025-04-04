from nautobot.core.testing.models import ModelTestCases
from nautobot.wireless import models


class SupportedDataRateTestCase(ModelTestCases.BaseModelTestCase):
    model = models.SupportedDataRate


class RadioProfileTestCase(ModelTestCases.BaseModelTestCase):
    model = models.RadioProfile


class WirelessNetworkTestCase(ModelTestCases.BaseModelTestCase):
    model = models.WirelessNetwork


class ControllerManagedDeviceGroupWirelessNetworkAssignmentTestCase(ModelTestCases.BaseModelTestCase):
    model = models.ControllerManagedDeviceGroupWirelessNetworkAssignment


class ControllerManagedDeviceGroupRadioProfileAssignmentTestCase(ModelTestCases.BaseModelTestCase):
    model = models.ControllerManagedDeviceGroupRadioProfileAssignment
