from nautobot.extras.jobs import Job, StringVar


class TestFieldOrder(Job):
    """My job demo."""

    var23 = StringVar(description="I want to be second")

    var2 = StringVar(description="Hello")

    class Meta:
        """Metaclass attrs."""

        field_order = ["var2", "var23"]
