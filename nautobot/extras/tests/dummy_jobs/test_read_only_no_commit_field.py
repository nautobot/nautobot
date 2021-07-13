from nautobot.extras.jobs import Job, StringVar


class TestReadOnlyNoCommitField(Job):
    """My job demo."""

    var = StringVar(description="Hello")

    class Meta:
        read_only = True
