from nautobot.cloud.models import CloudAccount
from nautobot.core.testing.models import ModelTestCases


class CloudAccountModelTestCase(ModelTestCases.BaseModelTestCase):
    model = CloudAccount
