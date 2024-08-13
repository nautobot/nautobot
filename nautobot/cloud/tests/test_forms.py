from django.test import TestCase

from nautobot.cloud.forms import CloudAccountForm


class CloudAccountTest(TestCase):
    def test_secrets_group_is_not_required(self):
        """Assert Secrets Group form field is not required: Fix for https://github.com/nautobot/nautobot/issues/6096"""
        self.assertFalse(CloudAccountForm().fields["secrets_group"].required)
