from django.test import TestCase

from nautobot.core.models.querysets import count_related
from nautobot.dcim.models.locations import Location
from nautobot.ipam.models import Prefix
from nautobot.ipam.tables import PrefixTable


class PrefixTableTestCase(TestCase):
    def _validate_sorted_queryset_same_with_table_queryset(self, queryset, table_class, field_name):
        with self.subTest(f"Assert sorting {table_class.__name__} on '{field_name}'"):
            table = table_class(queryset, order_by=field_name)
            table_queryset_data = table.data.data.values_list("pk", flat=True)
            sorted_queryset = queryset.order_by(field_name).values_list("pk", flat=True)
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    def test_prefix_table_sort(self):
        """Assert TreeNode model table are orderable."""
        # Due to MySQL's lack of support for combining 'LIMIT' and 'ORDER BY' in a single query,
        # hence this approach.
        pk_list = Prefix.objects.all().values_list("pk", flat=True)[:20]
        pk_list = [str(pk) for pk in pk_list]
        queryset = Prefix.objects.filter(pk__in=pk_list)

        # Assets model names
        table_avail_fields = ["tenant", "vlan", "namespace"]
        for table_field_name in table_avail_fields:
            self._validate_sorted_queryset_same_with_table_queryset(queryset, PrefixTable, table_field_name)
            self._validate_sorted_queryset_same_with_table_queryset(queryset, PrefixTable, f"-{table_field_name}")

        # Assert `prefix`
        table_queryset_data = PrefixTable(queryset, order_by="prefix").data.data.values_list("pk", flat=True)
        prefix_queryset = queryset.order_by("network", "prefix_length").values_list("pk", flat=True)
        self.assertEqual(list(table_queryset_data), list(prefix_queryset))
        table_queryset_data = PrefixTable(queryset, order_by="-prefix").data.data.values_list("pk", flat=True)
        prefix_queryset = queryset.order_by("-network", "-prefix_length").values_list("pk", flat=True)
        self.assertEqual(list(table_queryset_data), list(prefix_queryset))

        # Assets `location_count`
        location_count_queryset = queryset.annotate(location_count=count_related(Location, "prefixes")).all()
        self._validate_sorted_queryset_same_with_table_queryset(location_count_queryset, PrefixTable, "location_count")
        self._validate_sorted_queryset_same_with_table_queryset(location_count_queryset, PrefixTable, "-location_count")
