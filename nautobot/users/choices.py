from nautobot.core.choices import ChoiceSet


class ObjectPermissionActionChoices(ChoiceSet):
    VIEW = "view"
    ADD = "add"
    CHANGE = "change"
    DELETE = "delete"

    CHOICES = (
        (VIEW, "View"),
        (ADD, "Add"),
        (CHANGE, "Change"),
        (DELETE, "Delete"),
    )
