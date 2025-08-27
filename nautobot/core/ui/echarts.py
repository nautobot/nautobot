from abc import ABC, abstractmethod

from django.core.exceptions import ObjectDoesNotExist

from nautobot.core.ui.choices import EChartsTypeChoices, EChartsTypeThema


# Strategy Interface
class EChartsStrategy(ABC):
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
        return {}

    def get_toolbox_config(self, toolbox_enable, save_image_options={}, data_view_options={}):
        """Default toolbox config, can be overridden."""
        toolbox_config = {
            "show": toolbox_enable,
            "feature": {
                "dataView": data_view_options,
                "saveAsImage": save_image_options,
            },
        }
        return toolbox_config


class BarEChartsStrategy(EChartsStrategy):
    def get_series_config(self, data):
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": "bar",
                "data": s["data"],
                "itemStyle": s.get("itemStyle", {}),
            }
            for s in series_data
        ]

    def get_axis_config(self, data, x_label, y_label):
        return {
            "xAxis": {"name": x_label, "data": data.get("x", []), "type": "category"},
            "yAxis": {"name": y_label, "type": "value"},
        }


class PieEChartsStrategy(EChartsStrategy):
    def get_series_config(self, data):
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": "pie",
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
        return {"trigger": "item", "formatter": "{a} <br/>{b}: {c} ({d}%)"}


class LineEChartsStrategy(EChartsStrategy):
    def get_series_config(self, data):
        series_data = data.get("series", [])
        return [
            {
                "name": s["name"],
                "type": "line",
                "data": s["data"],
                "smooth": s.get("smooth", False),
                "lineStyle": s.get("lineStyle", {}),
            }
            for s in series_data
        ]

    def get_axis_config(self, data, x_label, y_label):
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
    def get_strategy(cls, chart_type: EChartsTypeChoices) -> EChartsStrategy:
        strategy_class = cls._strategies.get(chart_type)
        if not strategy_class:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        return strategy_class()


class EChartsBase:
    """Base definition for an ECharts chart (no rendering)."""

    def __init__(
        self,
        *,
        chart_type=EChartsTypeChoices.BAR,
        data={},
        header="",
        description="",
        x_label="X",
        y_label="Y",
        legend={},
        theme=EChartsTypeThema.DEFAULT,
        renderer="canvas",
        toolbox_enable=True,
        save_image_options=None,
        data_view_options=None,
        additional_config=None,
        permission=None,
        combined_with=None,
    ):
        """
        Args:
            chart_type (str): One of `EChartsTypeChoices`.
            data (dict|QuerySet): The dataset to render.
            header (str): Title/header of the chart.
            description (str): More detailed explanation.
            x_label (str): X-axis label (default: sane fallback).
            y_label (str): Y-axis label (default: sane fallback).
            legend (dict): Position of legend. It is always placed at the upper right corner of the chart. If you want to change it use template like
            {
                orient: 'vertical',
                right: 10,
                top: 'center'
            } more details here: https://echarts.apache.org/handbook/en/concepts/legend
            theme (str): Theme for chart, default "NTC".
            renderer (str): If the renderer is set to be 'canvas' when chart initialized (default), then 'png' (default) and 'jpg' are supported.
            If the renderer is set to be 'svg' when chart initialized, then only 'svg' is supported for type ('svg' type is supported since v4.8.0). See more details: https://echarts.apache.org/en/option.html#toolbox.feature.saveAsImage.type
            toolbox_enable (boolean): Show or not show toolbox, default True (show). See: https://echarts.apache.org/en/option.html#toolbox
            save_image_options (dict): Option how echarts should be saved, more details here: https://echarts.apache.org/en/option.html#toolbox.feature.saveAsImage
            data_view_options (dict): Option how data view toolbox will work, more details here: https://echarts.apache.org/en/option.html#toolbox.feature.dataView
            additional_config (dict): Not everything is implemented from echarts, so it's a way to check some additional config be carefull it can override your all data which you already set using separated filed. To be sure that this field is applied override method `additional_config` in your ECharts. Check: https://echarts.apache.org/en/option.html
            permission (str): Optional permission required to view.
            combined_with (EChartsBase): Another chart to merge with. Have to be the same type as `chart_type`.
        """
        self.chart_type = chart_type
        self.data = self._transform_data(data)
        self.header = header
        self.description = description
        self.x_label = x_label
        self.y_label = y_label
        self.legend = legend
        self.theme = theme
        self.renderer = renderer
        self.toolbox_enable = toolbox_enable
        self.save_image_options = {"name": self.header or "echart", "show": True, **(save_image_options or {})}
        self.data_view_options = {"readOnly": True, "show": True, **(data_view_options or {})}
        self.additional_config = additional_config
        self.permission = permission
        self.combined_with = combined_with
        self.strategy = EChartsStrategyFactory.get_strategy(chart_type)

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

        # Extract x-axis labels from the first series
        first_series_key = next(iter(data))
        x_labels = list(data[first_series_key].keys())

        # Ensure all series have the same x-axis labels
        for series_name, series_data in data.items():
            if list(series_data.keys()) != x_labels:
                # Handle mismatched keys - use union and fill missing with 0
                all_labels = set()
                for s in data.values():
                    all_labels.update(s.keys())
                x_labels = sorted(list(all_labels))
                break

        # Transform to internal format
        series = []
        for series_name, series_data in data.items():
            series.append({"name": series_name, "data": [series_data.get(label, 0) for label in x_labels]})

        return {"x": x_labels, "series": series}

    def _get_theme_colors(self):
        """Map SCSS palette to echarts theme colors (manual sync)."""
        if self.theme == EChartsTypeThema.DARK:
            return [
                "#045ab4",  # blue-0-dark
                "#e07807",  # orange-0-dark
                "#005c09",  # green-0-dark
                "#960606",  # red-0-dark
                "#4f5868",  # gray-3-dark
            ]
        # Default light
        return [
            "#007dff",  # blue-0
            "#e07807",  # orange-0
            "#1ca92a",  # green-0
            "#e01f1f",  # red-0
            "#505d68",  # gray-3
        ]

    def get_config(self):
        """Return a dict ready to dump into echarts option JSON."""
        # Base configuration
        config = {
            "title": {"text": self.header, "subtext": self.description},
            "tooltip": self.strategy.get_tooltip_config(),
            "toolbox": self.strategy.get_toolbox_config(
                self.toolbox_enable, self.save_image_options, self.data_view_options
            ),
            "color": self._get_theme_colors(),
            "legend": self.legend,
        }
        axis_config = self.strategy.get_axis_config(self.data, self.x_label, self.y_label)
        config.update(axis_config)

        # Add series configuration (chart-type specific)
        config["series"] = self.strategy.get_series_config(self.data)

        # Add any additional chart-specific configuration
        additional_config = self.strategy.get_additional_config()
        config.update(additional_config)

        # Handle combined charts
        if self.combined_with and self.combined_with.chart_type == self.chart_type:
            combined_series = self.combined_with.strategy.get_series_config(self.combined_with.data)
            config["series"].extend(combined_series)

        return config

    def change_chart_type(self, new_chart_type: EChartsTypeChoices):
        """Dynamically change the chart type strategy."""
        self.chart_type = new_chart_type
        self.strategy = EChartsStrategyFactory.get_strategy(new_chart_type)


def resolve_attr(obj, dotted_field):
    """
    Resolve nested attributes like 'location_type__nestable' on a Django model instance.
    """
    attrs = dotted_field.split("__")
    val = obj
    try:
        for attr in attrs:
            val = getattr(val, attr)
            if val is None:
                return None
    except (AttributeError, ObjectDoesNotExist):
        return None

    # handle booleans specially
    if isinstance(val, bool):
        # take last part of dotted_field ("nestable" in "location_type__nestable")
        field_label = attrs[-1].replace("_", " ").title()
        return field_label if val else f"No/Non {field_label}"

    return val


def queryset_to_nested_dict_records_as_series(queryset, record_key, value_keys):
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


def queryset_to_nested_dict_keys_as_series(queryset, record_key, value_keys):
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
