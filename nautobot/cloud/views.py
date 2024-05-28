from nautobot.cloud.api.serializers import CloudAccountSerializer
from nautobot.cloud.filters import CloudAccountFilterSet
from nautobot.cloud.models import CloudAccount
from nautobot.cloud.tables import CloudAccountTable
from nautobot.core.views.viewsets import NautobotUIViewSet


class CloudAccountUIViewSet(NautobotUIViewSet):
    queryset = CloudAccount.objects.all()
    filterset_class = CloudAccountFilterSet
    serializer_class = CloudAccountSerializer
    table_class = CloudAccountTable
