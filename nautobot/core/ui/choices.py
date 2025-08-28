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


class EChartsTypeChoices(ChoiceSet):
    """Available chart types for ECharts.

    Attributes:
        BAR (str): Bar chart (value: bar)
        LINE (str): Line chart (value: line)
        PIE (str): Pie chart (value: pie)
    """

    BAR = "bar"
    LINE = "line"
    PIE = "pie"

    CHOICES = (
        (BAR, "Bar chart"),
        (LINE, "Line chart"),
        (PIE, "Pie chart"),
    )


class EChartsTypeTheme(ChoiceSet):
    """Available chart theme for ECharts.

    Attributes:
        LIGHT (str): Light theme (value: light)
        DARK (str): Dark theme (value: dark)
    """

    LIGHT = "default"
    DARK = "dark"

    DEFAULT = LIGHT

    CHOICES = (
        (LIGHT, "Default theme"),
        (DARK, "Dark theme"),
    )
