from django.shortcuts import HttpResponse, render
from django.utils.html import format_html
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from nautobot.apps import ui, views
from nautobot.circuits.models import Circuit
from nautobot.circuits.tables import CircuitTable
from nautobot.circuits.views import CircuitUIViewSet
from nautobot.core.ui.object_detail import TextPanel
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
                label="Custom Table 1 - with dynamic data and hard-coded columns",
                weight=200,
                context_data_key="data_1",
                columns=["col_1", "col_2", "col_3"],
                column_headers=["Column 1", "Column 2", "Column 3"],
            ),
            # A table of non-object data with dynamic (render-time) columns
            ui.DataTablePanel(
                section=ui.SectionChoices.FULL_WIDTH,
                label="Custom Table 2 - with dynamic data and dynamic columns",
                weight=100,
                context_data_key="data_2",
                context_columns_key="columns_2",
                context_column_headers_key="column_headers_2",
            ),
            ui.TextPanel(
                section=ui.SectionChoices.LEFT_HALF,
                label="Text panel with JSON",
                weight=300,
                context_field="text_panel_content",
                render_as=TextPanel.RenderOptions.JSON,
            ),
            ui.TextPanel(
                section=ui.SectionChoices.LEFT_HALF,
                label="Text panel with YAML",
                weight=300,
                context_field="text_panel_content",
                render_as=TextPanel.RenderOptions.YAML,
            ),
            ui.TextPanel(
                section=ui.SectionChoices.RIGHT_HALF,
                label="Text panel with PRE tag usage",
                weight=300,
                context_field="text_panel_code_content",
                render_as=TextPanel.RenderOptions.CODE,
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
                # Because the DataTablePanel defined above specifies the `columns`, col_4 data will not appear
                {"col_1": "value_1a", "col_2": "value_2", "col_3": "value_3", "col_4": "not shown"},
                # Demonstration that null and missing column data is handled safely/correctly
                {"col_1": "value_1b", "col_2": None},
            ]
            # Some more arbitrary data to render
            # Dynamically specify the columns and column_headers for this data table, instead of at declaration time
            context["columns_2"] = ["a", "e", "i", "o", "u"]
            context["column_headers_2"] = ["A", "E", "I", "O", "U"]
            context["data_2"] = [
                {
                    # Column values can include appropriately constructed HTML
                    "a": format_html('<a href="https://en.wikipedia.org/wiki/{val}">{val}</a>', val="a"),
                    # Inappropriately constructed HTML is appropriately escaped on render
                    "e": '<a href="https://example.org/evil-link/e/">e</a>',
                    # Unicode is handled correctly
                    "i": "ℹ︎",  # noqa:RUF001 - intentional letter-like unicode
                    "o": "º",
                    "u": "µ",
                },
                # As above, data not matching a specific `columns` entry will not be rendered
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
            # Add data for TextPanel's
            context["text_panel_content"] = {
                "device_name": "Router1",
                "ip_address": "192.168.1.1",
                "subnet_mask": "255.255.255.0",
                "gateway": "192.168.1.254",
                "interfaces": [
                    {
                        "interface_name": "GigabitEthernet0/0",
                        "ip_address": "10.0.0.1",
                        "subnet_mask": "255.255.255.252",
                        "mac_address": "00:1A:2B:3C:4D:5E",
                    },
                ],
            }
            context["text_panel_code_content"] = 'import abc\nabc()\nprint("Hello world!")'

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


override_views = {
    "circuits:circuit_list": CircuitUIViewSet.as_view({"get": "list"})  # For testing override_views
}
