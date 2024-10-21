from django.shortcuts import HttpResponse, render
from django.utils.html import format_html
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from nautobot.apps import ui, views
from nautobot.circuits.models import Circuit
from nautobot.circuits.tables import CircuitTable
from nautobot.dcim.models import Device

from example_app import filters, forms, tables
from example_app.api import serializers
from example_app.models import AnotherExampleModel, ExampleModel


class CircuitDetailAppTabView(views.ObjectView):
    """
    This view's template extends the circuit detail template,
    making it suitable to show as a tab on the circuit detail page.

    Views that are intended to be for an object detail tab's content rendering must
    always inherit from nautobot.apps.views.ObjectView.
    """

    queryset = Circuit.objects.all()
    template_name = "example_app/tab_circuit_detail.html"


class DeviceDetailAppTabOneView(views.ObjectView):
    """
    This view's template extends the device detail template,
    making it suitable to show as a tab on the device detail page.

    Views that are intended to be for an object detail tab's content rendering must
    always inherit from nautobot.apps.views.ObjectView.
    """

    queryset = Device.objects.all()
    template_name = "example_app/tab_device_detail_1.html"


class DeviceDetailAppTabTwoView(views.ObjectView):
    """
    Same as DeviceDetailAppTabOneView view above but using a different template.
    """

    queryset = Device.objects.all()
    template_name = "example_app/tab_device_detail_2.html"


class ExampleAppHomeView(views.GenericView):
    def get(self, request):
        return render(request, "example_app/home.html")


class ExampleAppConfigView(views.GenericView):
    def get(self, request):
        """Render the configuration page for this App.

        Just an example - in reality you'd want to use real config data here as appropriate to your App, if any.
        """
        form = forms.ExampleAppConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "example_app/config.html", {"form": form})

    def post(self, request):
        """Handle configuration changes for this App.

        Not actually implemented here.
        """
        form = forms.ExampleAppConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "example_app/config.html", {"form": form})


class ExampleModelUIViewSet(views.NautobotUIViewSet):
    bulk_update_form_class = forms.ExampleModelBulkEditForm
    filterset_class = filters.ExampleModelFilterSet
    filterset_form_class = forms.ExampleModelFilterForm
    form_class = forms.ExampleModelForm
    queryset = ExampleModel.objects.all()
    serializer_class = serializers.ExampleModelSerializer
    table_class = tables.ExampleModelTable
    object_detail_content = ui.ObjectDetailContent(
        panels=(
            ui.ObjectFieldsPanel(
                section=ui.SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            # A table of objects derived dynamically in `get_extra_context()`
            ui.ObjectsTablePanel(
                section=ui.SectionChoices.RIGHT_HALF,
                weight=100,
                context_table_key="dynamic_table",
                max_display_count=3,
            ),
            # A table of non-object data with staticly defined columns
            ui.DataTablePanel(
                section=ui.SectionChoices.RIGHT_HALF,
                label="Custom Table 1",
                weight=200,
                context_data_key="data_1",
                columns=["col_1", "col_2", "col_3"],
                column_headers=["Column 1", "Column 2", "Column 3"],
            ),
            # A table of non-object data with dynamic (render-time) columns
            ui.DataTablePanel(
                section=ui.SectionChoices.FULL_WIDTH,
                label="Custom Table 2",
                weight=100,
                context_data_key="data_2",
                context_columns_key="columns_2",
                context_column_headers_key="column_headers_2",
            ),
        ),
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # Add dynamic table of objects for custom panel
            context["dynamic_table"] = CircuitTable(Circuit.objects.restrict(request.user, "view"))
            # Add non-object data for object detail view custom tables
            context["data_1"] = [
                {"col_1": "value_1a", "col_2": "value_2", "col_3": "value_3", "col_4": "not shown"},
                {"col_1": "value_1b", "col_2": None},
            ]
            context["data_2"] = [
                {
                    "a": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val=1),
                    "e": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val=5),
                    "i": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val=9),
                    "o": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val=15),
                    "u": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val=21),
                },
                {"a": 97, "b": 98, "c": 99, "e": 101, "i": 105, "o": 111, "u": 17},
                {"a": "0x61", "b": "0x62", "c": "0x63", "e": "0x65", "i": "0x69", "o": "0x6f", "u": "0x75"},
                {
                    "u": 21 + instance.number,
                    "o": 15 + instance.number,
                    "i": 9 + instance.number,
                    "e": 5 + instance.number,
                    "a": 1 + instance.number,
                },
            ]
            context["columns_2"] = ["a", "e", "i", "o", "u"]
            context["column_headers_2"] = ["A", "E", "I", "O", "U"]
        return context

    @action(detail=False, name="All Names", methods=["get"], url_path="all-names", url_name="all_names")
    def all_names(self, request):
        """
        Returns a list of all the example model names.
        """
        all_example_models = self.get_queryset()
        return render(
            request,
            "example_app/examplemodel_custom_action_get_all_example_model_names.html",
            {"data": [model.name for model in all_example_models]},
        )


# Example excluding the BulkUpdateViewSet
class AnotherExampleModelUIViewSet(
    views.ObjectBulkDestroyViewMixin,
    views.ObjectBulkUpdateViewMixin,
    views.ObjectChangeLogViewMixin,
    views.ObjectNotesViewMixin,
    views.ObjectDestroyViewMixin,
    views.ObjectDetailViewMixin,
    views.ObjectEditViewMixin,
    views.ObjectListViewMixin,
):
    action_buttons = ["add", "export"]
    bulk_update_form_class = forms.AnotherExampleModelBulkEditForm
    filterset_class = filters.AnotherExampleModelFilterSet
    filterset_form_class = forms.AnotherExampleModelFilterForm
    create_form_class = forms.AnotherExampleModelCreateForm
    update_form_class = forms.AnotherExampleModelUpdateForm
    lookup_field = "pk"
    queryset = AnotherExampleModel.objects.all()
    serializer_class = serializers.AnotherExampleModelSerializer
    table_class = tables.AnotherExampleModelTable


class ViewToBeOverridden(views.GenericView):
    def get(self, request, *args, **kwargs):
        return HttpResponse("I am a view in the example App which will be overridden by another App.")


class ViewWithCustomPermissions(views.ObjectListViewMixin):
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_class = filters.ExampleModelFilterSet
    queryset = ExampleModel.objects.all()
    serializer_class = serializers.ExampleModelSerializer
    table_class = tables.ExampleModelTable
