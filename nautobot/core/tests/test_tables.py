from django.test import TestCase

from nautobot.dcim.tables import RackGroupTable, RegionTable
from nautobot.dcim.tables.template_code import MPTT_LINK, MPTT_LINK_WITHOUT_NESTING


class TableTestCase(TestCase):
    def test_mttp_model_table_name_nesting_on_sort(self):
        """Assert tree model(MPTTModel) table column `name` template_code is changed when sorting"""
        # The name nesting when sorting on the Tree Model Table results in rows appearing as children of the wrong parent rows which is caused.
        # Assert that this nesting is removed when sorting by changing the default name template code
        tree_model_tables = (RegionTable, RackGroupTable)

        for table in tree_model_tables:
            queryset = table.Meta.model.objects.all()
            table_instance = table(queryset)
            self.assertEqual(table_instance.columns["name"].column.template_code, MPTT_LINK)
            table_instance = table(queryset, order_by=["name"])
            self.assertEqual(table_instance.columns["name"].column.template_code, MPTT_LINK_WITHOUT_NESTING)
