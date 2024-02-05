from django.test import TestCase

from nautobot.core.models.querysets import count_related
from nautobot.dcim.models.racks import Rack
from nautobot.dcim.tables import LocationTable, LocationTypeTable, RackGroupTable


class TableTestCase(TestCase):
    def _validate_sorted_tree_queryset_same_with_table_queryset(self, queryset, table_class, field_name):
        with self.subTest(f"Assert sorting {table_class.__name__} on '{field_name}'"):
            table = table_class(queryset, order_by=field_name)
            table_queryset_data = table.data.data.values_list("pk", flat=True)
            sorted_queryset = queryset.with_tree_fields().extra(order_by=[field_name]).values_list("pk", flat=True)
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    def test_tree_model_table_orderable(self):
        """Assert TreeNode model table are orderable."""
        tree_node_model_tables = [LocationTable, LocationTypeTable, RackGroupTable]

        # Each of the table has at-least two sortable field_names in the field_names
        model_field_names = ["name", "location", "parent", "location_type"]
        for table_class in tree_node_model_tables:
            queryset = table_class.Meta.model.objects.all()
            table_avail_fields = set(model_field_names) & set(table_class.Meta.fields)
            for table_field_name in table_avail_fields:
                self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, table_class, table_field_name)
                self._validate_sorted_tree_queryset_same_with_table_queryset(
                    queryset, table_class, f"-{table_field_name}"
                )

        # Test for `rack_count`
        queryset = RackGroupTable.Meta.model.objects.annotate(rack_count=count_related(Rack, "rack_group")).all()
        self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, RackGroupTable, "rack_count")
        self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, RackGroupTable, "-rack_count")
