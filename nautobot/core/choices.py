from nautobot.utilities import choices as utilities_choices


#
# Dynamic Groups
#


class DynamicGroupOperatorChoices(utilities_choices.ChoiceSet):
    OPERATOR_UNION = "union"
    OPERATOR_INTERSECTION = "intersection"
    OPERATOR_DIFFERENCE = "difference"

    CHOICES = (
        (OPERATOR_UNION, "Include (OR)"),
        (OPERATOR_INTERSECTION, "Restrict (AND)"),
        (OPERATOR_DIFFERENCE, "Exclude (NOT)"),
    )
