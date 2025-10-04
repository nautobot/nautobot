from itertools import combinations

from nautobot.core.testing import TestCase
from nautobot.core.views import generic
from nautobot.dcim.models import Location


class TestViewsGeneric(TestCase):
    def test_mro_resolve_for_generic_views(self):
        """
        Test if all the generic views can be used extend view class.

        Tries to detect if there is no MRO issues according to the #7829.
        """
        generic_views = [
            generic.GenericView,
            generic.ObjectListView,
            generic.ObjectView,
            generic.ObjectEditView,
            generic.ObjectDeleteView,
            generic.BulkCreateView,
            generic.ObjectImportView,
            generic.BulkImportView,
            generic.BulkEditView,
            generic.BulkRenameView,
            generic.BulkDeleteView,
            generic.ComponentCreateView,
            generic.BulkComponentCreateView,
        ]
        generic_views_pairs = combinations(generic_views, 2)

        for base_view, extension_view in generic_views_pairs:
            with self.subTest("Test different class inheritance."):

                class MyMixin(base_view):
                    pass

                # Defining this class will fail if there is MRO issue
                # pylint: disable=unused-variable
                class MyView(MyMixin, extension_view):
                    queryset = Location.objects.all()

                # pylint: enable=unused-variable
