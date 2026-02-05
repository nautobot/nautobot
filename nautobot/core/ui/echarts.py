from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Callable

from django.db.models import QuerySet
from django.template import Context

from nautobot.core.ui.choices import EChartsThemeColors, EChartsTypeChoices
from nautobot.core.utils.lookup import resolve_attr


# Strategy Interface
class EChartsStrategy(ABC):
    def __init__(self, additional_config=None):
        self.additional_config = additional_config or {}

    @abstractmethod
    def get_series_config(self, data):
        """Generate series configuration specific to chart type."""

    @abstractmethod
    def get_axis_config(self, data, x_label, y_label):
        """Generate axis configuration specific to chart type."""

    def get_tooltip_config(self):
        """Default tooltip config, can be overridden."""
        return {}

    def get_additional_config(self):
        """Additional chart-specific configuration."""
        return self.additional_config

    def get_toolbox_config(self, show_toolbox, save_image_options=None, data_view_options=None):
        """Default toolbox config, can be overridden."""
        toolbox_config = {
            "show": show_toolbox,
            "feature": {
                "dataView": data_view_options or {},
                "saveAsImage": save_image_options or {},
            },
        }
        return toolbox_config


class BarEChartsStrategy(EChartsStrategy):
    """Strategy for rendering bar charts using ECharts.

    This strategy transforms the internal data format into the
    configuration dictionary required by ECharts for bar charts.
    """

    def get_series_config(self, data):
        """Build the series configuration for a bar chart.

        Args:
            data (dict): Internal chart data in the form
            Each series item supports the base keys:
                - "name": str   - Legend label.
                - "data": list  - Values aligned with data["x"].
        Returns:
            list[dict]: ECharts-compatible `series` config for bar.

        """
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": EChartsTypeChoices.BAR,
                "data": s["data"],
            }
            for s in series_data
        ]

    def get_axis_config(self, data, x_label, y_label):
        """Build the axis configuration for a bar chart.

        For more information check:
        - https://echarts.apache.org/en/option.html#xAxis
        - https://echarts.apache.org/en/option.html#yAxis
        """
        return {
            "xAxis": {"name": x_label, "data": data.get("x", []), "type": "category"},
            "yAxis": {"name": y_label, "type": "value"},
        }


class PieEChartsStrategy(EChartsStrategy):
    """Strategy for rendering pie charts using ECharts.

    This strategy transforms the internal data format into the
    configuration dictionary required by ECharts for pie charts.
    """

    def get_series_config(self, data):
        """Build the series configuration for a pie chart.

        Args:
            data (dict): Internal chart data in the form

            Each series item supports the base keys:
                - "name": str   - Legend label.
                - "data": list  - Values aligned with data["x"], used to form pie slices.

            Pie-specific optional keys:
                - "radius": str|list - Size of pie (default "50%"). Pie radius, e.g. "50%" or ["40%", "70%"].
                    See: https://echarts.apache.org/en/option.html#series-pie.radius
                - "center": list     - Position of pie center (default ["50%", "50%"]).
                    Center positionvof Pie chart, e.g. ["50%", "50%"].
                    The first of which is the horizontal position, and the second is the vertical position.
                    See: https://echarts.apache.org/en/option.html#series-pie.center
        Returns:
            list[dict]: ECharts-compatible `series` config for pie.

        """
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": EChartsTypeChoices.PIE,
                "data": [{"name": name, "value": value} for name, value in zip(data.get("x", []), s["data"])],
                "radius": s.get("radius", "50%"),
                "center": s.get("center", ["50%", "50%"]),
            }
            for s in series_data
        ]

    def get_axis_config(self, data, x_label, y_label):
        # Pie charts don't use traditional axes
        return {}

    def get_tooltip_config(self):
        """Override tooltip configuration for pie charts.

        Returns:
            dict: Custom tooltip config with percentage formatting.
        """
        return {"trigger": "item", "formatter": "{a} <br/>{b}: {c} ({d}%)"}


class LineEChartsStrategy(EChartsStrategy):
    """Strategy for rendering line charts using ECharts.

    This strategy transforms the internal data format into the
    configuration dictionary required by ECharts for line charts.
    """

    def get_series_config(self, data):
        """Build the series configuration for a line chart.

        Args:
            data (dict): Internal chart data in the form

            Each series item supports the base keys:
                - "name": str   - Legend label.
                - "data": list  - Values aligned with data["x"]

            Line-specific optional keys:
            - "smooth": bool     - Whether to show as smooth curve (default False).
            - "lineStyle": dict  - Styling options for the line (e.g., {"type": "dashed"}).
                See https://echarts.apache.org/en/option.html#series-line.lineStyle

        Returns:
            list[dict]: ECharts-compatible `series` config for line.

        """
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": EChartsTypeChoices.LINE,
                "data": s["data"],
                "smooth": s.get("smooth", False),
                "lineStyle": s.get("lineStyle", {}),
            }
            for s in series_data
        ]

    def get_axis_config(self, data, x_label, y_label):
        """Build the axis configuration for a bar chart.

        For more information check:
        - https://echarts.apache.org/en/option.html#xAxis
        - https://echarts.apache.org/en/option.html#yAxis
        """
        return {
            "xAxis": {"name": x_label, "data": data.get("x", []), "type": "category"},
            "yAxis": {"name": y_label, "type": "value"},
        }


class EChartsStrategyFactory:
    _strategies = {
        EChartsTypeChoices.BAR: BarEChartsStrategy,
        EChartsTypeChoices.LINE: LineEChartsStrategy,
        EChartsTypeChoices.PIE: PieEChartsStrategy,
    }

    @classmethod
    def get_strategy(cls, chart_type: EChartsTypeChoices, additional_config=None) -> EChartsStrategy:
        strategy_class = cls._strategies.get(chart_type)
        if not strategy_class:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        return strategy_class(additional_config=additional_config)


class EChartsBase:
    """Base definition for an ECharts chart (no rendering)."""

    def __init__(
        self,
        *,
        chart_type=EChartsTypeChoices.BAR,
        data=None,
        header="",
        description="",
        x_label="X",
        y_label="Y",
        legend=None,
        theme_colors=None,
        renderer="canvas",
        show_toolbox=True,
        save_image_options=None,
        data_view_options=None,
        additional_config=None,
        permission=None,
        combined_with=None,
    ):
        """
        Args:
            chart_type (str): One of `EChartsTypeChoices`.
            data (dict|callable): The dataset to render. Can be:
                1. A dict in internal format: {"x": [...], "series": [{"name": str, "data": [...]}]}
                2. A nested dict: {"Series1": {"x1": val1, "x2": val2}, ...}
                3. A callable (e.g., lambda or function) returning any of the above.
            header (str): Title/header of the chart.
            description (str): More detailed explanation.
            x_label (str): X-axis label (default: "X").
            y_label (str): Y-axis label (default: "Y").
            legend (dict): Legend configuration. By default, it is placed at the upper right corner of the chart.
                You can customize its position using a dict like:
                    {
                        "orient": "vertical",
                        "right": 10,
                        "top": "center"
                    }
                You can also hide the legend entirely by setting `"show": False`.
                More details here: https://echarts.apache.org/handbook/en/concepts/legend.
            theme_colors (list[dict[str, str]]): Color palette for chart, each color is {'light': str, 'dark': str}
                (default: EChartsThemeColors.NAUTOBOT_COLORS).
            renderer (str): If the renderer is set to 'canvas' when chart initialized (default), then
                'png' (default) and 'jpg' are supported. If the renderer is set to 'svg' when chart
                initialized, then only 'svg' is supported for type. See more details:
                https://echarts.apache.org/en/option.html#toolbox.feature.saveAsImage.type
            show_toolbox (boolean): Show or not show toolbox, default True (show). See:
                https://echarts.apache.org/en/option.html#toolbox
            save_image_options (dict): Options for saving the chart image. See:
                https://echarts.apache.org/en/option.html#toolbox.feature.saveAsImage
            data_view_options (dict): Option how data view toolbox will work. See:
                https://echarts.apache.org/en/option.html#toolbox.feature.dataView
            additional_config (dict): Not all ECharts options are implemented; this allows passing
                additional configuration. Be careful as it can override existing settings. For safety,
                override `additional_config` in your subclass. See:
                https://echarts.apache.org/en/option.html
            permission (str): Optional permission required to view.
            combined_with (EChartsBase): Another chart to merge with.
        """
        self.additional_config = additional_config
        self.chart_type = chart_type
        self._data = data
        self.header = header
        self.description = description
        self.x_label = x_label
        self.y_label = y_label
        self.legend = legend or {}
        self.theme_colors = theme_colors or EChartsThemeColors.NAUTOBOT_COLORS
        self.renderer = renderer
        self.show_toolbox = show_toolbox
        self.save_image_options = {"name": self.header or "echart", "show": True, **(save_image_options or {})}
        self.data_view_options = {"readOnly": True, "show": True, **(data_view_options or {})}
        self.permission = permission
        self.combined_with = combined_with

    def get_transform_data(self, context: Context | None = None) -> dict[str, Any]:
        """Get the chart data in ECharts format, ready for rendering."""
        if context and callable(self._data):
            resolved_data = self._data(context)
        else:
            resolved_data = self._data() if callable(self._data) else self._data
        return self._transform_data(resolved_data or {})

    @property
    def data(self) -> dict[str, Any] | Callable[[Context], dict[str, Any]] | None:
        """Get the data.

        Returns:
            dict[str, Any] | Callable[[Context], dict[str, Any]] | None:
                Either a dictionary:
                    1. A dict in internal format: {"x": [...], "series": [{"name": str, "data": [...]}]}
                    2. A nested dict: {"Series1": {"x1": val1, "x2": val2}, ...}
                or , a callable (e.g., lambda or function) returning any of the above.
                or `None` if not set.
        """
        return self._data

    @property
    def chart_type(self):
        """Get the current chart type."""
        return self._chart_type

    @chart_type.setter
    def chart_type(self, new_chart_type: EChartsTypeChoices):
        """Set the chart type and update the strategy accordingly."""
        self._chart_type = new_chart_type
        self.strategy = EChartsStrategyFactory.get_strategy(new_chart_type, self.additional_config)

    def _transform_data(self, data):
        """
        Transform data from nested format to internal format.

        Input format: {"Series1": {"x1": val1, "x2": val2}, "Series2": {"x1": val3, "x2": val4}}
        Output format: {"x": ["x1", "x2"], "series": [{"name": "Series1", "data": [val1, val2]}, ...]}
        """
        # If data is already in the internal format, return as is
        if isinstance(data, dict) and "x" in data and "series" in data:
            return data

        # If data is empty or not in expected nested format
        if not data or not isinstance(data, dict):
            return {"x": [], "series": []}

        # Check if all values are dictionaries (nested format)
        if not all(isinstance(v, dict) for v in data.values()):
            return {"x": [], "series": []}

        # Collect union of all x labels
        x_labels = sorted({k for series in data.values() for k in series.keys()})

        # Build series list, filling missing values with 0
        series_list = [
            {"name": name, "data": [series.get(label, 0) for label in x_labels]} for name, series in data.items()
        ]

        return {"x": x_labels, "series": series_list}

    def _deep_update(self, original: dict, updates: dict) -> dict:
        """
        Recursively update a nested dictionary (and lists of dicts).

        Args:
            original (dict): The base configuration dictionary that will be updated.
            updates (dict): The dictionary containing overrides / new values.

        Returns:
            dict: The updated dictionary (same object as `original`).
        """
        for key, value in updates.items():
            # Case 1: nested dict -> recurse
            if isinstance(value, Mapping):
                original[key] = self._deep_update(original.get(key, {}), value)

            # Case 2: list of dicts -> update element by index
            elif isinstance(value, list) and isinstance(original.get(key), list):
                for index, item in enumerate(value):
                    if index < len(original[key]) and isinstance(item, dict) and isinstance(original[key][index], dict):
                        original[key][index] = self._deep_update(original[key][index], item)
                    else:
                        # append if list is shorter or item is not a dict
                        if index >= len(original[key]):
                            original[key].append(item)
                        else:
                            original[key][index] = item

            # Case 3: scalar or completely new key -> overwrite
            else:
                original[key] = value

        return original

    def get_config(self, context: Context | None = None):
        """Return a dict ready to dump into echarts option JSON."""
        data = self.get_transform_data(context=context)

        # Base configuration
        config = {
            "title": {"text": self.header, "subtext": self.description},
            "tooltip": self.strategy.get_tooltip_config(),
            "toolbox": self.strategy.get_toolbox_config(
                self.show_toolbox, self.save_image_options, self.data_view_options
            ),
            "color": self.theme_colors,
            "legend": self.legend,
        }
        axis_config = self.strategy.get_axis_config(data, self.x_label, self.y_label)
        config.update(axis_config)

        # Add series configuration (chart-type specific)
        config["series"] = self.strategy.get_series_config(data)

        # Add any additional chart-specific configuration
        additional_config = self.strategy.get_additional_config()
        self._deep_update(config, additional_config)

        # Handle combined charts
        if self.combined_with:
            data = self.combined_with.get_transform_data(context=context)
            combined_series = self.combined_with.strategy.get_series_config(data)
            config["series"].extend(combined_series)

        return config


def queryset_to_nested_dict_records_as_series(
    queryset: QuerySet, record_key: str, value_keys: list[str]
) -> dict[str, dict[str, Any]]:
    """
    Transform data with one series per record.
    Format: {"<record1>": {"key1": val1, "key2": val2}, "<record2>": {"key1": val3, "key2": val4}}

    Args:
        queryset: Django queryset with annotated fields
        record_key: Field name to identify each record (becomes outer keys)
        value_keys: List of field names to extract as values (becomes inner keys)

    Returns:
        dict: Nested dictionary with records as series
    Examples:
        # Records as series - locations as outer keys
        queryset_to_nested_dict_records_as_series(qs, record_key='name', value_keys=['prefix_count', 'device_count'])
        # Returns: {"Location1": {"prefix_count": 10, "device_count": 5}, ...}
    """
    result = {}

    for obj in queryset:
        record_name = str(resolve_attr(obj, record_key))
        result.setdefault(record_name, {})

        for value_key in value_keys:
            result[record_name][value_key] = result[record_name].get(value_key, 0) + getattr(obj, value_key)
    return result


def queryset_to_nested_dict_keys_as_series(
    queryset: QuerySet, record_key: str, value_keys: list[str]
) -> dict[str, dict[str, Any]]:
    """
    Transform data with one series per key/field.
    Format: {"key1": {"<record1>": val1, "<record2>": val3}, "key2": {"<record1>": val2, "<record2>": val4}}

    Args:
        queryset: Django queryset with annotated fields
        record_key: Field name to identify each record (becomes inner keys)
        value_keys: List of field names to extract as series (becomes outer keys)

    Returns:
        dict: Nested dictionary with keys as series
    Examples:
        # Keys as series - metrics as outer keys
        queryset_to_nested_dict_keys_as_series(qs, record_key='name', value_keys=['prefix_count', 'device_count'])
        # Returns: {"prefix_count": {"Location1": 10, ...}, "device_count": {"Location1": 5, ...}}
    """
    result = {}

    for value_key in value_keys:
        result.setdefault(value_key, {})

        for obj in queryset:
            record_name = str(resolve_attr(obj, record_key))
            result[value_key][record_name] = result[value_key].get(record_name, 0) + getattr(obj, value_key)
    return result
