from django.db.models import Q
from django.test import override_settings
from django.test import TestCase

from nautobot.extras.api.serializers import(
  ConfigContextSerializer
)

class ConfigContextSerializerTestCase(TestCase):
  @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
  def test_with_dynamic_groups_enabled(self):
    serializer = ConfigContextSerializer()
    self.assertIsNotNone(serializer.fields.get("dynamic_groups", None))

  @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=False)
  def test_without_dynamic_groups_enabled(self):
    serializer = ConfigContextSerializer()
    self.assertIsNone(serializer.fields.get("dynamic_groups", None))
