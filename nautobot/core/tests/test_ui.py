"""Test cases for nautobot.core.ui module."""

from unittest.mock import patch

from django.db.models import Sum
from django.template import Context
from django.test import RequestFactory
from django.urls import reverse

from nautobot.cloud.models import CloudNetwork, CloudResourceType, CloudService
from nautobot.cloud.tables import CloudServiceTable
from nautobot.cloud.views import CloudResourceTypeUIViewSet
from nautobot.core.models.querysets import count_related
from nautobot.core.templatetags.helpers import HTML_NONE
from nautobot.core.testing import TestCase
from nautobot.core.ui.choices import EChartsTypeChoices
from nautobot.core.ui.echarts import (
    EChartsBase,
    queryset_to_nested_dict_keys_as_series,
    queryset_to_nested_dict_records_as_series,
)
from nautobot.core.ui.object_detail import (
    _ObjectDetailAdvancedTab,
    _ObjectDetailMainTab,
    BaseTextPanel,
    DataTablePanel,
    DistinctViewTab,
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    Panel,
    SectionChoices,
)
from nautobot.dcim.models import Device, DeviceRedundancyGroup, Location
from nautobot.dcim.tables import DeviceModuleInterfaceTable
from nautobot.dcim.tables.devices import DeviceTable
from nautobot.dcim.views import DeviceUIViewSet
from nautobot.ipam.models import Prefix


class DataTablePanelTest(TestCase):
    def test_init(self):
        # Minimal arguments
        DataTablePanel(context_data_key="data", weight=100)

        # Conflicting arguments
        with self.assertRaises(ValueError):
            DataTablePanel(context_data_key="data", weight=100, columns=[1, 2, 3], context_columns_key="columns")
        with self.assertRaises(ValueError):
            DataTablePanel(
                context_data_key="data",
                weight=100,
                column_headers=[1, 2, 3],
                context_column_headers_key="column_headers",
            )

        # Maximal arguments
        DataTablePanel(context_data_key="data", weight=100, columns=[1, 2, 3], column_headers=["One", "Two", "Three"])
        DataTablePanel(context_data_key="data", weight=100, context_columns_key="c", context_column_headers_key="ch")

    def test_get_columns(self):
        context = Context({"data": [{1: 1, 2: 2, 3: 3}, {1: 10, 2: 20, 3: 30}], "columns": [1, 3]})

        self.assertEqual(DataTablePanel(context_data_key="data", weight=100).get_columns(context), [1, 2, 3])
        self.assertEqual(
            DataTablePanel(context_data_key="data", weight=100, columns=[1, 2]).get_columns(context), [1, 2]
        )
        self.assertEqual(
            DataTablePanel(context_data_key="data", weight=100, context_columns_key="columns").get_columns(context),
            [1, 3],
        )

    def test_get_column_headers(self):
        context = Context(
            {
                "data": [{1: 1, 2: 2, 3: 3}, {1: 10, 2: 20, 3: 30}],
                "columns": [1, 3],
                "column_headers": ["One", "Three"],
            }
        )

        self.assertEqual(DataTablePanel(context_data_key="data", weight=100).get_column_headers(context), [])
        self.assertEqual(
            DataTablePanel(context_data_key="data", weight=100, column_headers=["one", "two"]).get_column_headers(
                context
            ),
            ["one", "two"],
        )
        self.assertEqual(
            DataTablePanel(
                context_data_key="data", weight=100, context_column_headers_key="column_headers"
            ).get_column_headers(context),
            ["One", "Three"],
        )


class ObjectFieldsPanelTest(TestCase):
    def test_get_data_ignore_nonexistent_fields(self):
        panel = ObjectFieldsPanel(weight=100, fields=["name", "foo", "bar"], ignore_nonexistent_fields=True)
        redundancy_group = DeviceRedundancyGroup.objects.first()
        context = Context({"object": redundancy_group})
        data = panel.get_data(context)
        self.assertEqual(data, {"name": redundancy_group.name})  # no keys for nonexistent fields

        panel = ObjectFieldsPanel(weight=100, fields=["name", "foo", "bar"], ignore_nonexistent_fields=False)
        with self.assertRaises(AttributeError):
            data = panel.get_data(context)


class BaseTextPanelTest(TestCase):
    def test_init_set_object_params(self):
        # Test default settings
        panel = BaseTextPanel(weight=100)
        self.assertEqual(panel.render_as, BaseTextPanel.RenderOptions.MARKDOWN)
        self.assertTrue(panel.render_placeholder)

        # Test initialization with custom arguments
        panel = BaseTextPanel(weight=100, render_as=BaseTextPanel.RenderOptions.JSON, render_placeholder=False)
        self.assertEqual(panel.render_as, BaseTextPanel.RenderOptions.JSON)
        self.assertFalse(panel.render_placeholder)

    @patch.object(Panel, "__init__")
    def test_init_passes_args_and_kwargs(self, panel_init_mock):
        custom_template_path = "custom_template_path.html"

        BaseTextPanel(weight=100, body_content_template_path=custom_template_path)

        panel_init_mock.assert_called_once_with(weight=100, body_content_template_path=custom_template_path)

    @patch.object(BaseTextPanel, "get_value")
    def test_render_body_content(self, get_value_mock):
        test_cases = [
            {
                "render_as": BaseTextPanel.RenderOptions.JSON,
                "value": {"key": "value"},
                "expected_output": '<pre><code class="language-json">{    &quot;key&quot;: &quot;value&quot; }</code></pre>',
            },
            {
                "render_as": BaseTextPanel.RenderOptions.YAML,
                "value": {"key": "value"},
                "expected_output": '<pre><code class="language-yaml">key: value</code></pre>',
            },
            {
                "render_as": BaseTextPanel.RenderOptions.MARKDOWN,
                "value": "# Header",
                "expected_output": "<h1>Header</h1>",
            },
            {
                "render_as": BaseTextPanel.RenderOptions.CODE,
                "value": "print('Hello, world!')",
                "expected_output": "<pre>print(&#x27;Hello, world!&#x27;)</pre>",
            },
            {
                "render_as": BaseTextPanel.RenderOptions.PLAINTEXT,
                "value": "Simple text",
                "expected_output": "Simple text",
            },
        ]

        for case in test_cases:
            with self.subTest(render_as=case["render_as"]):
                panel = BaseTextPanel(weight=100, render_as=case["render_as"])

                get_value_mock.return_value = case["value"]
                context = Context()

                result = panel.render_body_content(context)

                self.assertHTMLEqual(result, case["expected_output"])

    @patch.object(BaseTextPanel, "get_value")
    def test_render_body_content_render_placeholder(self, get_value_mock):
        get_value_mock.return_value = ""
        context = Context()

        panel = BaseTextPanel(weight=100, render_as=BaseTextPanel.RenderOptions.PLAINTEXT)

        self.assertHTMLEqual(panel.render_body_content(context), HTML_NONE)

    @patch.object(BaseTextPanel, "get_value")
    def test_render_body_content_not_render_placeholder(self, get_value_mock):
        get_value_mock.return_value = ""
        context = Context()

        panel = BaseTextPanel(weight=100, render_as=BaseTextPanel.RenderOptions.PLAINTEXT, render_placeholder=False)

        self.assertHTMLEqual(panel.render_body_content(context), "")

    def test_get_value(self):
        panel = BaseTextPanel(weight=100)
        with self.assertRaises(NotImplementedError):
            panel.get_value({})


class ObjectsTablePanelTest(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_include_exclude_columns(self):
        panel = ObjectsTablePanel(
            weight=100,
            table_class=DeviceTable,
            table_attribute="devices_sorted",
            related_field_name="device_redundancy_group",
            include_columns=[
                "device_redundancy_group_priority",
            ],
            exclude_columns=[
                "rack",
            ],
        )
        redundancy_group = DeviceRedundancyGroup.objects.first()
        context = {
            "request": self.request,
            "object": redundancy_group,
        }
        result = panel.get_extra_context(context)
        columns = result["body_content_table"].columns
        self.assertIn("device_redundancy_group_priority", [col.name for col in columns])
        self.assertNotIn("rack", [col.name for col in columns])

    def test_invalid_include_columns(self):
        with self.assertRaises(ValueError) as context:
            panel = ObjectsTablePanel(
                weight=100,
                table_class=DeviceTable,
                table_attribute="devices_sorted",
                related_field_name="device_redundancy_group",
                include_columns=["non_existent_column"],
            )
            redundancy_group = DeviceRedundancyGroup.objects.first()
            context_data = {
                "request": self.request,
                "object": redundancy_group,
            }
            panel.get_extra_context(context_data)

        self.assertIn("non-existent column `non_existent_column`", str(context.exception))


class EChartsBaseTests(TestCase):
    def setUp(self):
        self.data_normalized = {"x": ["A", "B"], "series": [{"name": "S1", "data": [1, 2]}]}
        self.data_nested = {
            "Series1": {"x1": 10, "x2": 20},
            "Series2": {"x1": 30, "x2": 40},
        }
        self.chart = EChartsBase()

    def test_transform_data_internal_format(self):
        data = {"x": ["A", "B"], "series": [{"name": "S1", "data": [1, 2]}]}
        result = self.chart._transform_data(data)
        self.assertEqual(result, data)

    def test_transform_data_empty_dict(self):
        result = self.chart._transform_data({})
        self.assertEqual(result, {"x": [], "series": []})

    def test_transform_data_none_input(self):
        result = self.chart._transform_data(None)
        self.assertEqual(result, {"x": [], "series": []})

    def test_transform_data_nested_format(self):
        data = {"Series1": {"x1": 5, "x2": 10}, "Series2": {"x1": 7, "x2": 14}}
        expected = {
            "x": ["x1", "x2"],
            "series": [{"name": "Series1", "data": [5, 10]}, {"name": "Series2", "data": [7, 14]}],
        }
        result = self.chart._transform_data(data)
        self.assertEqual(result, expected)

    def test_transform_data_nested_format_mismatched_keys(self):
        data = {"Series1": {"x1": 5, "x2": 10}, "Series2": {"x2": 14, "x3": 20}}
        result = self.chart._transform_data(data)
        # Should use union of all x labels and fill missing with 0
        self.assertEqual(result["x"], ["x1", "x2", "x3"])
        series1_data = next(s["data"] for s in result["series"] if s["name"] == "Series1")
        series2_data = next(s["data"] for s in result["series"] if s["name"] == "Series2")
        self.assertEqual(series1_data, [5, 10, 0])
        self.assertEqual(series2_data, [0, 14, 20])

    def test_transform_data_non_dict_input(self):
        result = self.chart._transform_data([1, 2, 3])
        self.assertEqual(result, {"x": [], "series": []})

    def test_get_config_basic(self):
        chart = EChartsBase(
            chart_type=EChartsTypeChoices.BAR,
            header="Test Chart",
            description="Test Description",
            data=self.data_normalized,
        )

        config = chart.get_config()
        self.assertEqual(config["title"]["text"], "Test Chart")
        self.assertEqual(config["title"]["subtext"], "Test Description")
        self.assertEqual(config["tooltip"], {})
        self.assertEqual(
            config["toolbox"],
            {
                "show": True,
                "feature": {
                    "dataView": {"readOnly": True, "show": True},
                    "saveAsImage": {"name": "Test Chart", "show": True},
                },
            },
        )
        self.assertEqual(config["series"], [{"name": "S1", "data": [1, 2], "type": "bar"}])
        self.assertEqual(config["xAxis"]["data"], ["A", "B"])

    def test_get_config_with_raw_nested_data(self):
        chart = EChartsBase(data=self.data_nested)
        config = chart.get_config()
        self.assertEqual(len(config["series"]), 2)
        self.assertEqual(
            config["series"],
            [
                {"name": "Series1", "data": [10, 20], "type": "bar"},
                {"name": "Series2", "data": [30, 40], "type": "bar"},
            ],
        )
        self.assertEqual(config["xAxis"]["data"], ["x1", "x2"])

    def test_get_config_empty_data(self):
        chart = EChartsBase(data={})
        config = chart.get_config()
        self.assertEqual(config["series"], [])
        self.assertEqual(config["xAxis"]["data"], [])

    def test_get_config_additional_config(self):
        chart = EChartsBase(
            data=self.data_normalized,
        )
        config = chart.get_config()
        self.assertNotIn("grid", config)

        chart = EChartsBase(data=self.data_normalized, additional_config={"grid": {"show": True}})
        config = chart.get_config()
        self.assertIn("grid", config)
        self.assertEqual(config["grid"]["show"], True)

    def test_get_config_with_legend(self):
        legend = {"orient": "vertical", "right": 10, "top": "center"}
        chart = EChartsBase(data=self.data_normalized, legend=legend)
        config = chart.get_config()
        self.assertEqual(config["legend"], legend)

    def test_get_config_combined_charts(self):
        chart2 = EChartsBase(data={"x": ["A"], "series": [{"name": "S2", "data": [3]}]})
        chart1 = EChartsBase(data=self.data_normalized, combined_with=chart2)

        config = chart1.get_config()
        self.assertEqual(len(config["series"]), 2)
        self.assertEqual(config["series"][0]["name"], "S1")
        self.assertEqual(config["series"][1]["name"], "S2")

    def test_get_config_combined_charts_with_complex_data(self):
        chart2 = EChartsBase(
            chart_type=EChartsTypeChoices.LINE,
            data={
                "Compliant": {"aaa1": 5, "dns1": 12, "ntp1": 8},
                "Non Compliant": {"aaa1": 10, "dns1": 20, "ntp1": 15},
            },
        )
        chart1 = EChartsBase(
            chart_type=EChartsTypeChoices.BAR,
            data={
                "Compliant": {"aaa": 5, "dns": 12, "ntp": 8},
                "Non Compliant": {"aaa": 10, "dns": 20, "ntp": 15},
            },
            combined_with=chart2,
        )
        config = chart1.get_config()
        self.assertEqual(len(config["series"]), 4)

        self.assertEqual(config["series"][0], {"name": "Compliant", "type": "bar", "data": [5, 12, 8]})
        self.assertEqual(config["series"][1], {"name": "Non Compliant", "type": "bar", "data": [10, 20, 15]})
        self.assertEqual(
            config["series"][2],
            {"name": "Compliant", "type": "line", "data": [5, 12, 8], "smooth": False, "lineStyle": {}},
        )
        self.assertEqual(
            config["series"][3],
            {"name": "Non Compliant", "type": "line", "data": [10, 20, 15], "smooth": False, "lineStyle": {}},
        )

    def test_get_config_with_context_callable_and_combined_chart(self):
        def main_data(ctx):
            return {
                "Compliant": {"aaa1": ctx.get("aaa1_count", 0), "dns1": 13, "ntp1": 8},
                "Non Compliant": {"aaa1": 10, "dns1": 20, "ntp1": 15},
            }

        def combined_data(ctx):
            return {
                "Compliant": {"aaa": 5, "dns": ctx.get("dns_count", 0), "ntp1": 8},
                "Non Compliant": {"aaa": 10, "dns": 20, "ntp1": 15},
            }

        ctx = Context({"aaa1_count": 5, "dns_count": 12})
        combined_chart = EChartsBase(chart_type=EChartsTypeChoices.LINE, data=combined_data)
        main_chart = EChartsBase(
            chart_type=EChartsTypeChoices.BAR,
            data=main_data,
            combined_with=combined_chart,
        )
        config = main_chart.get_config(context=ctx)
        self.assertEqual(len(config["series"]), 4)

        self.assertEqual(config["series"][0]["data"][0], 5)  # aaa1_count
        self.assertEqual(config["series"][2]["data"][1], 12)  # dns_count

    def test_get_config_with_context_callable(self):
        def dynamic_data(ctx):
            return {"data": {"Devices": ctx.get("device_count", 0)}}

        ctx = Context({"device_count": 42})
        chart = EChartsBase(chart_type=EChartsTypeChoices.PIE, data=dynamic_data)
        config = chart.get_config(context=ctx)
        # check that after getting config data doesn't change it's still dynami_data function
        self.assertEqual(chart.data, dynamic_data)
        self.assertEqual(config["series"][0]["data"][0]["value"], 42)
        ctx = Context({"device_count": 45})
        config = chart.get_config(context=ctx)
        self.assertEqual(config["series"][0]["data"][0]["value"], 45)

    def test_get_config_with_context_ignored_when_data_is_not_callable(self):
        ctx = Context({"some": "value"})
        chart = EChartsBase(data=self.data_normalized)
        config = chart.get_config(context=ctx)
        self.assertEqual(config["series"][0]["data"], [1, 2])


class QuerySetToNestedDictTests(TestCase):
    def setUp(self):
        self.qs = Location.objects.annotate(
            device_count=count_related(Device, "location"), prefix_count=count_related(Prefix, "locations")
        )

    def test_records_as_series_basic_grouping(self):
        data = queryset_to_nested_dict_records_as_series(
            self.qs, record_key="name", value_keys=["device_count", "prefix_count"]
        )
        location_name = self.qs.first().name
        location_name_device_count = self.qs.get(name=location_name).device_count
        location_name_prefix_count = self.qs.get(name=location_name).prefix_count

        self.assertEqual(data[location_name]["device_count"], location_name_device_count)
        self.assertEqual(data[location_name]["prefix_count"], location_name_prefix_count)

    def test_keys_as_series_basic_series(self):
        data = queryset_to_nested_dict_keys_as_series(
            self.qs, record_key="name", value_keys=["device_count", "prefix_count"]
        )
        location_name = self.qs.first().name
        location_name_device_count = self.qs.get(name=location_name).device_count
        location_name_prefix_count = self.qs.get(name=location_name).prefix_count

        self.assertEqual(data["device_count"][location_name], location_name_device_count)
        self.assertEqual(data["prefix_count"][location_name], location_name_prefix_count)

    def test_records_as_series_accumulation(self):
        # If repeats should sum up
        data = queryset_to_nested_dict_records_as_series(self.qs, record_key="status", value_keys=["device_count"])
        location_status = str(self.qs.first().status)
        device_count_total = self.qs.filter(status__name=location_status).aggregate(total=Sum("device_count"))["total"]
        self.assertEqual(data[location_status]["device_count"], device_count_total)

    def test_keys_as_series_accumulation(self):
        # If repeats should sum up
        data = queryset_to_nested_dict_keys_as_series(self.qs, record_key="status", value_keys=["device_count"])
        location_status = str(self.qs.first().status)
        device_count_total = self.qs.filter(status__name=location_status).aggregate(total=Sum("device_count"))["total"]
        self.assertEqual(data["device_count"][location_status], device_count_total)

    def test_records_as_series_nested_record_key(self):
        data = queryset_to_nested_dict_records_as_series(
            self.qs, record_key="location_type__nestable", value_keys=["device_count"]
        )
        # should map boolean to friendly labels
        # "Nestable" and Not Nestable instead of True and False
        self.assertIn("Nestable", data)
        self.assertIn("Not Nestable", data)

    def test_keys_as_series_nested_record_key(self):
        data = queryset_to_nested_dict_keys_as_series(
            self.qs, record_key="location_type__nestable", value_keys=["device_count"]
        )
        # should map boolean to friendly labels
        # In this case "Nestable" and Not Nestable instead of True and False
        self.assertIn("Nestable", data["device_count"])
        self.assertIn("Not Nestable", data["device_count"])

    def test_records_as_series_empty_queryset(self):
        data = queryset_to_nested_dict_records_as_series(
            Location.objects.none(), record_key="name", value_keys=["device_count"]
        )
        self.assertEqual(data, {})

    def test_keys_as_series_empty_queryset(self):
        data = queryset_to_nested_dict_keys_as_series(
            Location.objects.none(), record_key="name", value_keys=["device_count"]
        )
        self.assertEqual(data, {"device_count": {}})


class ObjectDetailContentExtraTabsTest(TestCase):
    """
    Test suite for verifying the behavior of ObjectDetailContent when rendering default and extra tabs.
    """

    user_permissions = ["cloud.view_cloudresourcetype", "cloud.view_cloudservice", "cloud.view_cloudnetwork"]

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user
        self.default_tabs_id = ["main", "advanced", "contacts", "dynamic_groups", "object_metadata", "data_compliance"]

    def test_default_extra_tabs_exist(self):
        """
        Test the default set of tabs (main, advanced, contacts, dynamic_groups, object_metadata) is present.
        """
        content = ObjectDetailContent(
            panels=[],
        )

        self.assertEqual(len(content.tabs), len(self.default_tabs_id))
        tab_ids = [t.tab_id for t in content.tabs]
        self.assertListEqual(tab_ids, self.default_tabs_id)

    def test_extra_tabs_exist(self):
        """
        Test that extra tabs (e.g. "services") can be injected via the `extra_tabs` argument.
        Validating that tab IDs are correctly combined when extra tabs are provided.
        """
        content = ObjectDetailContent(
            panels=[],
            extra_tabs=[
                DistinctViewTab(
                    weight=1000,
                    tab_id="services",
                    label="Cloud Services",
                    url_name="cloud:cloudresourcetype_services",
                    related_object_attribute="cloud_services",
                    panels=(
                        ObjectsTablePanel(
                            section=SectionChoices.FULL_WIDTH,
                            weight=100,
                            table_class=CloudServiceTable,
                            table_filter="cloud_resource_type",
                            tab_id="services",
                        ),
                    ),
                ),
            ],
        )

        self.assertEqual(len(content.tabs), len(self.default_tabs_id) + 1)
        tab_ids = [t.tab_id for t in content.tabs]
        self.default_tabs_id.append("services")
        self.assertListEqual(tab_ids, self.default_tabs_id)

    def test_tab_id_url_as_action(self):
        """
        Test that when you create a panel with a tab_id that matches a viewset action,
        the return_url is constructed correctly.
        """
        self.add_permissions("dcim.add_interface", "dcim.change_interface")
        device_info = Device.objects.first()

        panel = DeviceUIViewSet.DeviceInterfacesTablePanel(
            weight=100,
            section=SectionChoices.FULL_WIDTH,
            table_title="Interfaces",
            table_class=DeviceModuleInterfaceTable,
            table_attribute="vc_interfaces",
            related_field_name="device",
            tab_id="interfaces",
        )
        context = {"request": self.request, "object": device_info}
        panel_context = panel.get_extra_context(context)

        return_url = f"/dcim/devices/{device_info.pk}/interfaces/"
        self.assertTrue(panel_context["body_content_table_add_url"].endswith(return_url))

    def test_tab_id_url_as_param(self):
        """
        Test that when you create a panel with a tab_id that does NOT matches a viewset action,
        the return_url is constructed correctly.
        """
        self.add_permissions("dcim.add_interface", "dcim.change_interface")
        device_info = Device.objects.first()

        panel = DeviceUIViewSet.DeviceInterfacesTablePanel(
            weight=100,
            section=SectionChoices.FULL_WIDTH,
            table_title="Interfaces",
            table_class=DeviceModuleInterfaceTable,
            table_attribute="vc_interfaces",
            related_field_name="device",
            tab_id="interfaces-not-exist",
        )
        context = {"request": self.request, "object": device_info}
        panel_context = panel.get_extra_context(context)

        return_url = f"&return_url=/dcim/devices/{device_info.pk}/?tab=interfaces-not-exist"
        self.assertTrue(panel_context["body_content_table_add_url"].endswith(return_url))

    def test_extra_tab_panel_context(self):
        """
        Confirming that extra tab panels produce the correct context,
        including `url` and `body_content_table` populated with the expected related objects.
        """
        cloud_resource_type = CloudResourceType.objects.get_for_model(CloudNetwork)[0]
        cloud_services = CloudService.objects.filter(cloud_resource_type=cloud_resource_type)

        tab = DistinctViewTab(
            weight=1000,
            tab_id="services",
            label="Cloud Services",
            url_name="cloud:cloudresourcetype_services",
            related_object_attribute="cloud_services",
            panels=(
                ObjectsTablePanel(
                    section=SectionChoices.FULL_WIDTH,
                    weight=100,
                    table_class=CloudServiceTable,
                    table_filter="cloud_resource_type",
                    tab_id="services",
                ),
            ),
        )
        context = {"request": self.request, "object": cloud_resource_type}
        extra_context = tab.get_extra_context(context)
        self.assertIn("url", extra_context)
        self.assertTrue(extra_context["url"].endswith("/services/"))

        panel = tab.panels[0]
        panel_context = panel.get_extra_context(context)

        self.assertIn("body_content_table", panel_context)
        table = panel_context["body_content_table"]
        self.assertQuerySetEqual(cloud_services, table.data)

    def test_tab_conditional_rendering(self):
        """
        Assert default tabs render on the main detail view but not sub-views, while distinct-view-tabs do the reverse.
        """
        cloud_resource_type = CloudResourceType.objects.get_for_model(CloudNetwork)[0]
        content = CloudResourceTypeUIViewSet.object_detail_content

        # Main detail view renders all base tabs and no DistinctViewTabs
        request = self.factory.get(cloud_resource_type.get_absolute_url())
        request.user = self.user
        context_data = {
            "request": request,
            "user": self.user,
            "object": cloud_resource_type,
            "settings": {},
            "csrf_token": "",
            "perms": [],
            "created_by": self.request.user,
            "last_updated_by": self.request.user,
            "view_action": "retrieve",
            "detail": True,
        }
        context = Context(context_data)
        for tab in content.tabs:
            if isinstance(tab, DistinctViewTab):
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertEqual(tab.render(context), "")
                    panel_render.assert_not_called()
            elif isinstance(tab, (_ObjectDetailMainTab, _ObjectDetailAdvancedTab)):  # other base tabs might not render
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertNotEqual(tab.render(context), "")
                    panel_render.assert_called()

        # Distinct tab view renders its tab *only*
        request = self.factory.get(reverse("cloud:cloudresourcetype_networks", kwargs={"pk": cloud_resource_type.pk}))
        request.user = self.user
        context_data["request"] = request
        context_data["view_action"] = "networks"
        context = Context(context_data)
        for tab in content.tabs:
            if isinstance(tab, DistinctViewTab) and tab.url_name == "cloud:cloudresourcetype_networks":  # pylint: disable=no-member
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertNotEqual(tab.render(context), "")
                    panel_render.assert_called()
            else:
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertEqual(tab.render(context), "")
                    panel_render.assert_not_called()

        # Same, but for a different distinct view tab
        request = self.factory.get(reverse("cloud:cloudresourcetype_services", kwargs={"pk": cloud_resource_type.pk}))
        request.user = self.user
        context_data["request"] = request
        context_data["view_action"] = "services"
        context = Context(context_data)
        for tab in content.tabs:
            if isinstance(tab, DistinctViewTab) and tab.url_name == "cloud:cloudresourcetype_services":  # pylint: disable=no-member
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertNotEqual(tab.render(context), "")
                    panel_render.assert_called()
            else:
                with patch.object(tab.panels[0], "render", wraps=tab.panels[0].render) as panel_render:
                    self.assertEqual(tab.render(context), "")
                    panel_render.assert_not_called()
