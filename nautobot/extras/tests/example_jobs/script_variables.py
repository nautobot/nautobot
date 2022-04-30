from nautobot.dcim.models import DeviceRole
from nautobot.extras.scripts import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    IPAddressVar,
    IPAddressWithMaskVar,
    IPNetworkVar,
    MultiChoiceVar,
    MultiObjectVar,
    ObjectVar,
    Script,
    StringVar,
    TextVar,
)


CHOICES = (("ff0000", "Red"), ("00ff00", "Green"), ("0000ff", "Blue"))


class BooleanVarScript(Script):
    var1 = BooleanVar()


class ChoiceVarScript(Script):
    var1 = ChoiceVar(choices=CHOICES)


class FileVarScript(Script):
    var1 = FileVar()


class IntegerVarScript(Script):
    var1 = IntegerVar(min_value=5, max_value=10)


class IPAddressVarScript(Script):
    var1 = IPAddressVar()


class IPAddressWithMaskVarScript(Script):
    var1 = IPAddressWithMaskVar()


class IPNetworkVarScript(Script):
    var1 = IPNetworkVar()


class MultiChoiceVarScript(Script):
    var1 = MultiChoiceVar(choices=CHOICES)


class MultiObjectVarScript(Script):
    var1 = MultiObjectVar(model=DeviceRole)


class ObjectVarScript(Script):
    var1 = ObjectVar(model=DeviceRole)


class StringVarScript(Script):
    var1 = StringVar(min_length=3, max_length=3, regex=r"[a-z]+")


class TextVarScript(Script):
    var1 = TextVar()
