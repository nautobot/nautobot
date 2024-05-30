from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.core.testing.models import ModelTestCases


class CloudAccountModelTestCase(ModelTestCases.BaseModelTestCase):
    model = CloudAccount


class CloudTypeModelTestCase(ModelTestCases.BaseModelTestCase):
    model = CloudType
