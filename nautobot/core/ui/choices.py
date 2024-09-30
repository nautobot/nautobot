"""ChoiceSets for Nautobot UI Framework."""

from nautobot.core.choices import ChoiceSet


class LayoutChoices(ChoiceSet):
    """Page (or more properly tab) column layout choices."""

    TWO_OVER_ONE = "2-over-1"
    ONE_OVER_TWO = "1-over-2"

    DEFAULT = TWO_OVER_ONE

    CHOICES = (
        (TWO_OVER_ONE, "Two Columns over One Column"),
        (ONE_OVER_TWO, "One Column over Two Columns"),
    )


class SectionChoices(ChoiceSet):
    """Sections of a Layout to assign panels to."""

    LEFT_HALF = "left-half"
    RIGHT_HALF = "right-half"
    FULL_WIDTH = "full-width"

    CHOICES = (
        (LEFT_HALF, "Left half of page"),
        (RIGHT_HALF, "Right half of page"),
        (FULL_WIDTH, "Full width of page"),
    )
