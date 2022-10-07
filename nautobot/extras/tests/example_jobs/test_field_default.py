from nautobot.extras.jobs import IntegerVar, Job


class TestFieldDefault(Job):
    """My job demo."""

    var_int = IntegerVar(default=0, min_value=0, max_value=3600, description="Test default of 0 Falsey")
    var_int_no_default = IntegerVar(
        required=False, min_value=0, max_value=3600, description="Test default without default"
    )

    class Meta:
        """Metaclass attrs."""

        field_order = ["var_int", "var_int_no_default"]
