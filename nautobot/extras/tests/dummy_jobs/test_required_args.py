from nautobot.extras.jobs import Job, StringVar


class TestRequired(Job):
    var = StringVar(required=True)
