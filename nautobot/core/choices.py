class ChoiceSetMeta(type):
    """
    Metaclass for ChoiceSet
    """

    def __call__(cls, *args, **kwargs):
        # Django will check if a 'choices' value is callable, and if so assume that it returns an iterable
        return getattr(cls, "CHOICES", ())

    def __iter__(cls):
        choices = getattr(cls, "CHOICES", ())
        return iter(choices)

    def __getattribute__(cls, attr):
        """
        Overrides the default __getattribute__ method to provide custom behavior when accessing attributes of a ChoiceSet
        instance. If the attribute name is an uppercase string and not equal to 'CHOICES', this method returns a new class
        instance of the same type as the original attribute value, but with an additional 'label' property. This 'label'
        property looks up the choice label for the given attribute value in the 'CHOICES' sequence and returns it.
        """
        value = super().__getattribute__(attr)
        # Check if the attribute is a member of the CHOICES sequence and is uppercase;
        # Mostly only ChoiceSet choices are uppercase
        if attr != "CHOICES" and attr.isupper():
            choices = cls.as_dict()

            class Choice(value.__class__):
                @property
                def label(self):
                    return choices.get(self)

            return Choice(value)
        return value


class ChoiceSet(metaclass=ChoiceSetMeta):
    """
    Base class for defining choices for a model and/or menu.

    Subclasses should define a CHOICES constant which consists of a list of tuples of the form `(value, display_str)`,
    or optionally as tuples of the form `(grouping, ((value, display_str), (value, display_str), ...))`.

    Example:
        ```python
        class GreekCapitalLetterChoices(ChoiceSet):
            ALPHA = "Α"
            BETA = "Β"
            GAMMA = "Γ"

            CHOICES = (
                (ALPHA, "alpha"),
                (BETA, "beta"),
                (GAMMA, "gamma"),
            )
        ```
    """

    CHOICES = []

    @classmethod
    def values(cls):
        """Get a flat list of all values defined in this ChoiceSet's `CHOICES`."""
        return [c[0] for c in unpack_grouped_choices(cls.CHOICES)]

    @classmethod
    def as_dict(cls):
        """Get a dictionary representation of this ChoiceSet's `CHOICES`."""
        # Unpack grouped choices before casting as a dict
        return dict(unpack_grouped_choices(cls.CHOICES))


def unpack_grouped_choices(choices):
    """
    Unpack a grouped choices hierarchy into a flat list of two-tuples. For example:

    choices = (
        ('Foo', (
            (1, 'A'),
            (2, 'B')
        )),
        ('Bar', (
            (3, 'C'),
            (4, 'D')
        ))
    )

    becomes:

    choices = (
        (1, 'A'),
        (2, 'B'),
        (3, 'C'),
        (4, 'D')
    )
    """
    unpacked_choices = []
    for key, value in choices:
        if isinstance(value, (list, tuple)):
            # Entered an optgroup
            for optgroup_key, optgroup_value in value:
                unpacked_choices.append((optgroup_key, optgroup_value))
        else:
            unpacked_choices.append((key, value))
    return unpacked_choices


#
# Generic color choices
#


class ColorChoices(ChoiceSet):
    COLOR_DARK_RED = "aa1409"
    COLOR_RED = "f44336"
    COLOR_PINK = "e91e63"
    COLOR_ROSE = "ffe4e1"
    COLOR_FUCHSIA = "ff66ff"
    COLOR_PURPLE = "9c27b0"
    COLOR_DARK_PURPLE = "673ab7"
    COLOR_INDIGO = "3f51b5"
    COLOR_BLUE = "2196f3"
    COLOR_LIGHT_BLUE = "03a9f4"
    COLOR_CYAN = "00bcd4"
    COLOR_TEAL = "009688"
    COLOR_AQUA = "00ffff"
    COLOR_DARK_GREEN = "2f6a31"
    COLOR_GREEN = "4caf50"
    COLOR_LIGHT_GREEN = "8bc34a"
    COLOR_LIME = "cddc39"
    COLOR_YELLOW = "ffeb3b"
    COLOR_AMBER = "ffc107"
    COLOR_ORANGE = "ff9800"
    COLOR_DARK_ORANGE = "ff5722"
    COLOR_BROWN = "795548"
    COLOR_LIGHT_GREY = "c0c0c0"
    COLOR_GREY = "9e9e9e"
    COLOR_DARK_GREY = "607d8b"
    COLOR_BLACK = "111111"
    COLOR_WHITE = "ffffff"

    CHOICES = (
        (COLOR_DARK_RED, "Dark red"),
        (COLOR_RED, "Red"),
        (COLOR_PINK, "Pink"),
        (COLOR_ROSE, "Rose"),
        (COLOR_FUCHSIA, "Fuchsia"),
        (COLOR_PURPLE, "Purple"),
        (COLOR_DARK_PURPLE, "Dark purple"),
        (COLOR_INDIGO, "Indigo"),
        (COLOR_BLUE, "Blue"),
        (COLOR_LIGHT_BLUE, "Light blue"),
        (COLOR_CYAN, "Cyan"),
        (COLOR_TEAL, "Teal"),
        (COLOR_AQUA, "Aqua"),
        (COLOR_DARK_GREEN, "Dark green"),
        (COLOR_GREEN, "Green"),
        (COLOR_LIGHT_GREEN, "Light green"),
        (COLOR_LIME, "Lime"),
        (COLOR_YELLOW, "Yellow"),
        (COLOR_AMBER, "Amber"),
        (COLOR_ORANGE, "Orange"),
        (COLOR_DARK_ORANGE, "Dark orange"),
        (COLOR_BROWN, "Brown"),
        (COLOR_LIGHT_GREY, "Light grey"),
        (COLOR_GREY, "Grey"),
        (COLOR_DARK_GREY, "Dark grey"),
        (COLOR_BLACK, "Black"),
        (COLOR_WHITE, "White"),
    )


#
# Button color choices
#


class ButtonColorChoices(ChoiceSet):
    """
    Map standard button color choices to Bootstrap color classes
    """

    DEFAULT = "default"
    BLUE = "primary"
    GREY = "secondary"
    GREEN = "success"
    RED = "danger"
    YELLOW = "warning"
    BLACK = "dark"

    CHOICES = (
        (DEFAULT, "Default"),
        (BLUE, "Blue"),
        (GREY, "Grey"),
        (GREEN, "Green"),
        (RED, "Red"),
        (YELLOW, "Yellow"),
        (BLACK, "Black"),
    )


class ButtonActionColorChoices(ChoiceSet):
    """
    Map standard button actions to Bootstrap color classes.
    """

    ADD = "success"
    CANCEL = "default"
    CLONE = "success"
    CONFIGURE = "default"
    CONNECT = "success"
    DEFAULT = "default"
    DELETE = "danger"
    DISCONNECT = "info"
    EDIT = "warning"
    EXPORT = "success"
    IMPORT = "primary"
    INFO = "info"
    SUBMIT = "primary"
    SWAP = "primary"

    CHOICES = (
        (ADD, "Add"),
        (CANCEL, "Cancel"),
        (CLONE, "Clone"),
        (CONFIGURE, "Configure"),
        (CONNECT, "Connect"),
        (DEFAULT, "Default"),
        (DELETE, "Delete"),
        (DISCONNECT, "Disconnect"),
        (EDIT, "Edit"),
        (EXPORT, "Export"),
        (IMPORT, "Import"),
        (INFO, "Info"),
        (SUBMIT, "Submit"),
        (SWAP, "Swap"),
    )


class ButtonActionIconChoices(ChoiceSet):
    """
    Map standard button actions to Material Design Icons classes.
    """

    ADD = "mdi-plus-thick"
    ALERT = "mdi-alert"
    ARROW_DOWN = "mdi-arrow-down-bold"
    ARROW_UP = "mdi-arrow-up-bold"
    CONFIGURE = "mdi-cogs"
    CONNECT = "mdi-ethernet-cable"
    DELETE = "mdi-trash-can-outline"
    DISCONNECT = "mdi-ethernet-cable-off"
    EDIT = "mdi-pencil"
    EXPORT = "mdi-database-export-outline"
    HELP = "mdi-help-circle"
    INFO = "mdi-help-circle"
    IMPORT = "mdi-database-import-outline"
    LOCK = "mdi-lock"
    MAGNIFY = "mdi-magnify"
    NOTE = "mdi-note-text"
    SWAP = "mdi-swap-vertical"
    TRASH = "mdi-trash-can-outline"

    CHOICES = (
        (ADD, "Add"),
        (ALERT, "Alert"),
        (ARROW_DOWN, "Arrow Down"),
        (ARROW_UP, "Arrow Up"),
        (CONFIGURE, "Configure"),
        (CONNECT, "Connect"),
        (DELETE, "Delete"),
        (DISCONNECT, "Disconnect"),
        (EDIT, "Edit"),
        (EXPORT, "Export"),
        (HELP, "Help"),
        (INFO, "Info"),
        (IMPORT, "Import"),
        (LOCK, "Lock"),
        (MAGNIFY, "Magnify"),
        (NOTE, "Note"),
        (SWAP, "Swap"),
        (TRASH, "Trash"),
    )
