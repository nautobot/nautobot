from nautobot.extras.jobs import Job, FileVar, StringVar


class TestFieldOrder(Job):
    """My job demo."""

    var23 = StringVar(description="I want to be second")

    var2 = StringVar(description="Hello")

    var1 = FileVar(description="Some file wants to be first")

    class Meta:
        """Metaclass attrs."""

        field_order = ["var1", "var2", "var23"]
