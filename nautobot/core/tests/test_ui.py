"""Test cases for nautobot.core.ui module."""

from unittest.mock import patch

from django.template import Context

from nautobot.core.templatetags.helpers import HTML_NONE
from nautobot.core.testing import TestCase
from nautobot.core.ui.object_detail import BaseTextPanel, DataTablePanel, Panel


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
