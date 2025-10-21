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

    COLORS = {
        LIGHT: [
            UI_COLORS["blue"]["light"],
            UI_COLORS["purple"]["light"],
            UI_COLORS["turquoise"]["light"],
            UI_COLORS["orange"]["light"],
            UI_COLORS["green"]["light"],
            UI_COLORS["red"]["light"],
            UI_COLORS["gray"]["light"],
            UI_COLORS["blue-lighter"]["light"],
            UI_COLORS["purple-lighter"]["light"],
            UI_COLORS["turquoise-lighter"]["light"],
            UI_COLORS["orange-lighter"]["light"],
            UI_COLORS["green-lighter"]["light"],
            UI_COLORS["red-lighter"]["light"],
            UI_COLORS["gray-lighter"]["light"],
            UI_COLORS["blue-darker"]["light"],
            UI_COLORS["purple-darker"]["light"],
            UI_COLORS["turquoise-darker"]["light"],
            UI_COLORS["orange-darker"]["light"],
            UI_COLORS["green-darker"]["light"],
            UI_COLORS["red-darker"]["light"],
            UI_COLORS["gray-darker"]["light"],
        ],
        DARK: [
            UI_COLORS["blue"]["dark"],
            UI_COLORS["purple"]["dark"],
            UI_COLORS["turquoise"]["dark"],
            UI_COLORS["orange"]["dark"],
            UI_COLORS["green"]["dark"],
            UI_COLORS["red"]["dark"],
            UI_COLORS["gray"]["dark"],
            UI_COLORS["blue-lighter"]["dark"],
            UI_COLORS["purple-lighter"]["dark"],
            UI_COLORS["turquoise-lighter"]["dark"],
            UI_COLORS["orange-lighter"]["dark"],
            UI_COLORS["green-lighter"]["dark"],
            UI_COLORS["red-lighter"]["dark"],
            UI_COLORS["gray-lighter"]["dark"],
            UI_COLORS["blue-darker"]["dark"],
            UI_COLORS["purple-darker"]["dark"],
            UI_COLORS["turquoise-darker"]["dark"],
            UI_COLORS["orange-darker"]["dark"],
            UI_COLORS["green-darker"]["dark"],
            UI_COLORS["red-darker"]["dark"],
            UI_COLORS["gray-darker"]["dark"],
        ],
    }


class NavigationIconChoices(ChoiceSet):
    """Navigation icons for major Nautobot sections."""

    DEVICES = "server"
    IPAM = "sitemap-outline"
    ORGANIZATION = "organization"
    CIRCUITS = "cable-data"
    VPN = "route"
    POWER = "battery-3"
    WIRELESS = "wifi"
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
        (POWER, "Power"),
        (WIRELESS, "Wireless"),
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

    DEVICES = 100
    IPAM = 200
    ORGANIZATION = 300
    CIRCUITS = 400
    VPN = 450
    POWER = 500
    WIRELESS = 550
    SECRETS = 600
    SECURITY = 650
    LOAD_BALANCERS = 700
    VIRTUALIZATION = 750
    CLOUD = 800
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
        (POWER, "Power"),
        (WIRELESS, "Wireless"),
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
