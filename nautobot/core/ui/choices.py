"""ChoiceSets for Nautobot UI Framework."""

from nautobot.core.choices import ChoiceSet


class LayoutChoices(ChoiceSet):
    """Page (or more properly tab) column layout choices.

    Attributes:
        TWO_OVER_ONE (str): Half-width panels will be above full-width panels (value: 2-over-1)
        ONE_OVER_TWO (str): Full-width panels will be above half-width panels (value: 1-over-2)

        DEFAULT (str): Two columns of half-width panels on top; full-width panels below. (value of TWO_OVER_ONE)
    """

    TWO_OVER_ONE = "2-over-1"
    ONE_OVER_TWO = "1-over-2"

    DEFAULT = TWO_OVER_ONE

    CHOICES = (
        (TWO_OVER_ONE, "Two Columns over One Column"),
        (ONE_OVER_TWO, "One Column over Two Columns"),
    )


class SectionChoices(ChoiceSet):
    """Sections of a Layout to assign panels to. Placement of panels is determined by [`LayoutChoices`](./ui.md#nautobot.apps.ui.LayoutChoices) set on `Tab.layout`

    Attributes:
        LEFT_HALF (str): Left side, half-width (value: left-half)
        RIGHT_HALF (str): Right side, half-width (value: right-half)
        FULL_WIDTH (str): Full width (value: full-width)
    """

    LEFT_HALF = "left-half"
    RIGHT_HALF = "right-half"
    FULL_WIDTH = "full-width"

    CHOICES = (
        (LEFT_HALF, "Left half of page"),
        (RIGHT_HALF, "Right half of page"),
        (FULL_WIDTH, "Full width of page"),
    )


class EChartTypeChoices(ChoiceSet):
    """Available chart types for ECharts.

    Attributes:
        BAR (str): Bar chart (value: bar)
        LINE (str): Line chart (value: line)
        PIE (str): Pie chart (value: pie)
        SCATTER (str): Scatter plot (value: scatter)
        EFFECT_SCATTER (str): Effect scatter plot (value: effectScatter)
        CANDLESTICK (str): Candlestick chart (value: candlestick)
        RADAR (str): Radar chart (value: radar)
        HEATMAP (str): Heatmap chart (value: heatmap)
        TREE (str): Tree diagram (value: tree)
        TREEMAP (str): Treemap (value: treemap)
        SUNBURST (str): Sunburst chart (value: sunburst)
        MAP (str): Map chart (value: map)
        LINES (str): Line series on map (value: lines)
        GRAPH (str): Graph/network chart (value: graph)
        BOXPLOT (str): Boxplot (value: boxplot)
        PARALLEL (str): Parallel coordinates (value: parallel)
        GAUGE (str): Gauge chart (value: gauge)
        FUNNEL (str): Funnel chart (value: funnel)
        SANKEY (str): Sankey diagram (value: sankey)
        THEME_RIVER (str): ThemeRiver chart (value: themeRiver)
        PICTORIAL_BAR (str): Pictorial bar chart (value: pictorialBar)
        CUSTOM (str): Custom chart (value: custom)
    """

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    EFFECT_SCATTER = "effectScatter"
    CANDLESTICK = "candlestick"
    RADAR = "radar"
    HEATMAP = "heatmap"
    TREE = "tree"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    MAP = "map"
    LINES = "lines"
    GRAPH = "graph"
    BOXPLOT = "boxplot"
    PARALLEL = "parallel"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    SANKEY = "sankey"
    THEME_RIVER = "themeRiver"
    PICTORIAL_BAR = "pictorialBar"
    CUSTOM = "custom"

    CHOICES = (
        (BAR, "Bar chart"),
        (LINE, "Line chart"),
        (PIE, "Pie chart"),
        (SCATTER, "Scatter plot"),
        (EFFECT_SCATTER, "Effect scatter plot"),
        (CANDLESTICK, "Candlestick chart"),
        (RADAR, "Radar chart"),
        (HEATMAP, "Heatmap"),
        (TREE, "Tree diagram"),
        (TREEMAP, "Treemap"),
        (SUNBURST, "Sunburst"),
        (MAP, "Map"),
        (LINES, "Map lines"),
        (GRAPH, "Graph / network"),
        (BOXPLOT, "Boxplot"),
        (PARALLEL, "Parallel coordinates"),
        (GAUGE, "Gauge"),
        (FUNNEL, "Funnel"),
        (SANKEY, "Sankey diagram"),
        (THEME_RIVER, "Theme river"),
        (PICTORIAL_BAR, "Pictorial bar"),
        (CUSTOM, "Custom"),
    )


class EChartTypeThema(ChoiceSet):
    """Available chart thema for ECharts.

    Attributes:
        LIGHT (str): Light thema (value: light)
        DARK (str): Dark thema (value: dark)
    """

    LIGHT = "default"
    DARK = "dark"

    DEFAULT = LIGHT

    CHOICES = (
        (LIGHT, "Default thema"),
        (DARK, "Dark thema"),
    )
