from nautobot.core.celery import register_jobs
from nautobot.extras.models import Role
from nautobot.extras.jobs import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    IPAddressVar,
    IPAddressWithMaskVar,
    IPNetworkVar,
    Job,
    MultiChoiceVar,
    MultiObjectVar,
    ObjectVar,
    StringVar,
    TextVar,
)


CHOICES = (("ff0000", "Red"), ("00ff00", "Green"), ("0000ff", "Blue"))


class BooleanVarJob(Job):
    var1 = BooleanVar()


class ChoiceVarJob(Job):
    var1 = ChoiceVar(choices=CHOICES)


class FileVarJob(Job):
    var1 = FileVar()


class IntegerVarJob(Job):
    var1 = IntegerVar(min_value=5, max_value=10)


class IPAddressVarJob(Job):
    var1 = IPAddressVar()


class IPAddressWithMaskVarJob(Job):
    var1 = IPAddressWithMaskVar()


class IPNetworkVarJob(Job):
    var1 = IPNetworkVar()


class MultiChoiceVarJob(Job):
    var1 = MultiChoiceVar(choices=CHOICES)


class MultiObjectVarJob(Job):
    var1 = MultiObjectVar(model=Role)


class ObjectVarJob(Job):
    var1 = ObjectVar(model=Role)


class StringVarJob(Job):
    var1 = StringVar(min_length=3, max_length=3, regex=r"[a-z]+")


class TextVarJob(Job):
    var1 = TextVar()


job_list = [
    BooleanVarJob,
    ChoiceVarJob,
    FileVarJob,
    IntegerVarJob,
    IPAddressVarJob,
    IPAddressWithMaskVarJob,
    IPNetworkVarJob,
    MultiChoiceVarJob,
    MultiObjectVarJob,
    ObjectVarJob,
    StringVarJob,
    TextVarJob,
]

# Avoid registering the jobs with Celery when this is imported directly as a file
if __name__ == "test_job_variables":
    register_jobs(*job_list)
