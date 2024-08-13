from django.test import TestCase

from nautobot.extras.api.serializers import ContactAssociationSerializer


class ContactAssociationTest(TestCase):
    def test_secrets_group_is_not_required(self):
        """Assert ContactAssociation serializer role field is required: Fix for https://github.com/nautobot/nautobot/issues/6097"""
        ContactAssociationSerializer
        self.assertTrue(ContactAssociationSerializer().fields["role"].required)
