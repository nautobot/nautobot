"""Test cases for nautobot.core.ui module."""

from unittest.mock import patch

from django.template import Context
from django.test import RequestFactory
from django.urls import reverse

from nautobot.cloud.models import CloudNetwork, CloudResourceType, CloudService
from nautobot.cloud.tables import CloudServiceTable
from nautobot.cloud.views import CloudResourceTypeUIViewSet
from nautobot.core.templatetags.helpers import HTML_NONE
from nautobot.core.testing import TestCase
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
from nautobot.dcim.models import DeviceRedundancyGroup
from nautobot.dcim.tables.devices import DeviceTable


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
        self.default_tabs_id = ["main", "advanced", "contacts", "dynamic_groups", "object_metadata"]

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
