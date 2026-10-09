from itertools import combinations

from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.test import RequestFactory

from nautobot.core.testing import TestCase
from nautobot.core.views import generic
from nautobot.dcim.models import Location
from nautobot.dcim.tables import LocationTable


class TestViewsGeneric(TestCase):
    def test_object_list_template_renders_without_list_url(self):
        """
        Test that `generic/object_list.html` can be rendered by a view that doesn't provide `list_url` in the context.

        This is the case for an App whose list view overrides `get()` and builds its own template context.
        """
        request = RequestFactory().get("/custom-location-list/")
        request.user = self.user
        context = {
            "content_type": ContentType.objects.get_for_model(Location),
            "model": Location,
            "table": LocationTable(Location.objects.all()),
            "title": "Locations",
        }

        content = render_to_string("generic/object_list.html", context, request=request)

        self.assertIn("Locations", content)
        # Saved Views cannot be offered without knowing which list view they would apply to.
        self.assertNotIn('id="saved_view_modal"', content)
        self.assertNotIn('data-nb-target="#SavedViews_drawer"', content)

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
