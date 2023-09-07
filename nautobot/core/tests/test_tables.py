from django.test import TestCase

from nautobot.dcim.tables import ManufacturerTable, DeviceTypeTable, LocationTable, LocationTypeTable, RackGroupTable


class TableTestCase(TestCase):
    def test_model_table_orderable(self):
        """Assert TreeNode model table orderable is set to False, and non tree model table is True by default"""
        tree_node_model_tables = (LocationTypeTable, LocationTable, RackGroupTable)
        non_tree_node_model_tables = (DeviceTypeTable, ManufacturerTable)

        for table in tree_node_model_tables:
            queryset = table.Meta.model.objects.all()
            self.assertFalse(table(queryset).orderable)

        for table in non_tree_node_model_tables:
            queryset = table.Meta.model.objects.all()
            self.assertTrue(table(queryset).orderable)
