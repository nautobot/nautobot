from nautobot.extras.jobs import Job, StringVar


class TestNoFieldOrder(Job):
    """My job demo."""

    var23 = StringVar(description="I want to be second")

    var2 = StringVar(description="Hello")


class BaseJobClassWithVariable(Job):
    testvar1 = StringVar(description="This var should come before any vars defined in subclasses")


class TestDefaultFieldOrderWithInheritance(BaseJobClassWithVariable):
    b_testvar2 = StringVar(description="This var should be second")
    a_testvar3 = StringVar(description="This var should be third")
