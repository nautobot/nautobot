from django.test import TestCase

from nautobot.dcim.tables import CableTable, DeviceTypeTable, LocationTable, RegionTable


class TableTestCase(TestCase):
    def test_model_table_orderable(self):
        """Assert tree model table orderable is set to False, and non tree model table is True by default"""
        tree_model_tables = (RegionTable, LocationTable)
        non_tree_model_tables = (DeviceTypeTable, CableTable)

        for table in tree_model_tables:
            queryset = table.Meta.model.objects.all()[:2]
            self.assertFalse(table(queryset).orderable)

        for table in non_tree_model_tables:
            queryset = table.Meta.model.objects.all()[:2]
            self.assertTrue(table(queryset).orderable)
