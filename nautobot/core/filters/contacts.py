from nautobot.core.models.contacts import Contact, Team
from nautobot.extras.filters import NautobotFilterSet, RoleModelFilterSetMixin

from .filtersets import NameSearchFilterSet


class ContactFilterSet(NameSearchFilterSet, RoleModelFilterSetMixin, NautobotFilterSet):
    class Meta:
        model = Contact
        fields = "__all__"


class TeamFilterSet(NameSearchFilterSet, RoleModelFilterSetMixin, NautobotFilterSet):
    class Meta:
        model = Team
        fields = "__all__"
