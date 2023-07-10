from django.test import TestCase

from nautobot.dcim.tables import DeviceTypeTable, LocationTable, LocationTypeTable, RackGroupTable, RegionTable
from nautobot.dcim.tables.template_code import MPTT_LINK, MPTT_LINK_WITHOUT_NESTING


class TableTestCase(TestCase):
    def test_mptt_model_table_name_nesting_on_sort(self):
        """Assert MPTTModel table column `name` template_code is changed when sorting"""
        # The name nesting when sorting on the MPTTModel Table results in rows appearing as children of the wrong parent rows which is caused.
        # Assert that this nesting is removed when sorting by changing the default name template code
        mptt_model_tables = (RegionTable, RackGroupTable)

        for table in mptt_model_tables:
            queryset = table.Meta.model.objects.all()
            table_instance = table(queryset)
            self.assertEqual(table_instance.columns["name"].column.template_code, MPTT_LINK)
            table_instance = table(queryset, order_by=["name"])
            self.assertEqual(table_instance.columns["name"].column.template_code, MPTT_LINK_WITHOUT_NESTING)

    def test_model_table_orderable(self):
        """Assert TreeNode model table orderable is set to False, and non tree model table is True by default"""
        tree_node_model_tables = (LocationTypeTable, LocationTable)
        non_tree_node_model_tables = (DeviceTypeTable, RegionTable)

        for table in tree_node_model_tables:
            queryset = table.Meta.model.objects.all()
            self.assertFalse(table(queryset).orderable)

        for table in non_tree_node_model_tables:
            queryset = table.Meta.model.objects.all()
            self.assertTrue(table(queryset).orderable)
