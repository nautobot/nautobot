"""ChoiceSets for Nautobot UI Framework."""

from nautobot.core.choices import ChoiceSet

from .constants import UI_COLORS


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


class EChartsThemeColors(ChoiceSet):
    """Available chart colors for ECharts."""

    NAUTOBOT = "default"
    LIGHTER_GREEN_AND_RED_ONLY = "lighter-green-red-only"
    DEFAULT = NAUTOBOT

    # Color lists - direct access
    NAUTOBOT_COLORS = (
        UI_COLORS["blue"],
        UI_COLORS["purple"],
        UI_COLORS["turquoise"],
        UI_COLORS["orange"],
        UI_COLORS["green"],
        UI_COLORS["red"],
        UI_COLORS["gray"],
        UI_COLORS["blue-lighter"],
        UI_COLORS["purple-lighter"],
        UI_COLORS["turquoise-lighter"],
        UI_COLORS["orange-lighter"],
        UI_COLORS["green-lighter"],
        UI_COLORS["red-lighter"],
        UI_COLORS["gray-lighter"],
        UI_COLORS["blue-darker"],
        UI_COLORS["purple-darker"],
        UI_COLORS["turquoise-darker"],
        UI_COLORS["orange-darker"],
        UI_COLORS["green-darker"],
        UI_COLORS["red-darker"],
        UI_COLORS["gray-darker"],
    )

    LIGHTER_GREEN_RED_COLORS = (
        UI_COLORS["green-lighter"],
        UI_COLORS["red-lighter"],
    )

    CHOICES = (
        (NAUTOBOT, "Default Nautobot Colors"),
        (LIGHTER_GREEN_AND_RED_ONLY, "Lighter Green and Red Only"),
    )

    COLORS = {
        NAUTOBOT: NAUTOBOT_COLORS,
        LIGHTER_GREEN_AND_RED_ONLY: LIGHTER_GREEN_RED_COLORS,
    }


class NavigationIconChoices(ChoiceSet):
    """Navigation icons for major Nautobot sections."""

    DEVICES = "server"
    IPAM = "sitemap-outline"
    ORGANIZATION = "organization"
    CIRCUITS = "cable-data"
    VPN = "bus-shield"
    ROUTING = "route"
    POWER = "battery-3"
    WIRELESS = "wifi"
    DEVICE_LIFECYCLE = "device-lifecycle"
    SECRETS = "secrets"
    SECURITY = "security"
    LOAD_BALANCERS = "arrow-decision"
    VIRTUALIZATION = "cloud-upload"
    CLOUD = "cloud"
    DESIGN = "hammer"
    APPROVAL_WORKFLOWS = "checkbox-circle"
    EXTENSIBILITY = "extensibility"
    GOLDEN_CONFIG = "sliders-vert-2"
    JOBS = "share"
    APPS = "elements"

    CHOICES = (
        (DEVICES, "Devices"),
        (IPAM, "IPAM"),
        (ORGANIZATION, "Organization"),
        (CIRCUITS, "Circuits"),
        (VPN, "VPN"),
        (ROUTING, "Routing"),
        (POWER, "Power"),
        (WIRELESS, "Wireless"),
        (DEVICE_LIFECYCLE, "Device Lifecycle"),
        (SECRETS, "Secrets"),
        (SECURITY, "Security"),
        (LOAD_BALANCERS, "Load Balancers"),
        (VIRTUALIZATION, "Virtualization"),
        (CLOUD, "Cloud"),
        (DESIGN, "Design"),
        (APPROVAL_WORKFLOWS, "Approval Workflows"),
        (EXTENSIBILITY, "Extensibility"),
        (GOLDEN_CONFIG, "Golden Config"),
        (JOBS, "Jobs"),
        (APPS, "Apps"),
    )


class NavigationWeightChoices(ChoiceSet):
    """Navigation weights for major Nautobot sections."""

    # In general we are looking to:
    # - Keep data models before the default weight of 1000
    # - Leave a gap between the default location of 1000
    # - Keep non-model items after the default weight of 1000
    # - Keep key items of GC, Jobs, and Apps at the end for easy access
    DEVICES = 100
    IPAM = 200
    ORGANIZATION = 300
    CIRCUITS = 400
    VPN = 450
    ROUTING = 500
    POWER = 550
    WIRELESS = 600
    DEVICE_LIFECYCLE = 650
    SECRETS = 700
    SECURITY = 750
    LOAD_BALANCERS = 800
    VIRTUALIZATION = 850
    CLOUD = 900
    # We leave a gap here to allow for future expansion and don't use 1000
    # since it the default weight for NavMenuTab if none is specified.
    DESIGN = 1100
    APPROVAL_WORKFLOWS = 1200
    EXTENSIBILITY = 1300
    # look to keep these last few items at the end of the nav for easy access
    GOLDEN_CONFIG = 2000
    JOBS = 2100
    APPS = 2200

    CHOICES = (
        (DEVICES, "Devices"),
        (IPAM, "IPAM"),
        (ORGANIZATION, "Organization"),
        (CIRCUITS, "Circuits"),
        (VPN, "VPN"),
        (ROUTING, "Routing"),
        (POWER, "Power"),
        (WIRELESS, "Wireless"),
        (DEVICE_LIFECYCLE, "Device Lifecycle"),
        (SECRETS, "Secrets"),
        (SECURITY, "Security"),
        (VIRTUALIZATION, "Virtualization"),
        (LOAD_BALANCERS, "Load Balancers"),
        (CLOUD, "Cloud"),
        (DESIGN, "Design"),
        (APPROVAL_WORKFLOWS, "Approval Workflows"),
        (EXTENSIBILITY, "Extensibility"),
        (GOLDEN_CONFIG, "Golden Config"),
        (JOBS, "Jobs"),
        (APPS, "Apps"),
    )
