from nautobot.extras.jobs import Job


class TestDuplicateName1(Job):
    """
    Job with duplicate name.
    """

    class Meta:
        name = "This name is not unique."


class TestDuplicateName2(Job):
    """
    Job with duplicate name.
    """

    class Meta:
        name = "This name is not unique."


class TestDuplicateNameNoMeta(Job):
    pass
