# ECharts

This module is based on [Apache ECharts](https://echarts.apache.org/en/index.html). To create and configure charts in Nautobot, the `EChartsBase` class is used. It handles transforming input data, applying themes, and generating a valid ECharts option config JSON.

## EChartsBase

Base definition for an ECharts chart (no rendering logic). This class transforms input data, applies theme colors, and generates a valid ECharts option config.

## Example Usage in a Django View

```no-highlight
template_name = "detail.html"
def get_extra_context(self, request, instance):
    chart = EChartsBase(
        chart_type=EChartsTypeChoices.BAR,
        header="Traffic per Interface",
        description="Example chart",
        data={
            "Compliant": {"aaa": 5, "dns": 12, "ntp": 8},
            "Non Compliant": {"aaa": 10, "dns": 20, "ntp": 15},
        },
    )

    chart_config = chart.get_config()

    return {
        "chart": chart,
        "chart_config": chart.get_config(),
        "chart_width": self.width,
        "chart_height": self.height,
        "chart_container_id": slugify(f"echart-{self.header}"),
    }
```

Corresponding Template (`detail.html`)

```no-highlight
{% load helpers %}
{% render_echart chart chart_config chart_widht chart_height chart_container_id %}
```

## Example Usage as a Nautobot UI Component

```no-highlight
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import EChartsTypeChoices, SectionChoices

object_detail_content = object_detail.ObjectDetailContent(
    panels=[
        object_detail.EChartsPanel(
            section=object_detail.SectionChoices.FULL_WIDTH,
            weight=200,
            label="EChart - BAR",
            chart_kwargs={
                "chart_type": EChartsTypeChoices.BAR,
                "header": "Traffic per Interface Bar",
                "description": "Example bar chart from EChartsBase",
                "data": {"Compliant": {"aaa": 5, "dns": 12, "ntp": 8}, "Non Compliant": {"aaa": 10, "dns": 20, "ntp": 15}},
            },
        ),
    ]
)
```
