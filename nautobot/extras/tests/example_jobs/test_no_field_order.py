from nautobot.extras.jobs import Job, StringVar


class TestNoFieldOrder(Job):
    """My job demo."""

    var23 = StringVar(description="I want to be second")

    var2 = StringVar(description="Hello")
