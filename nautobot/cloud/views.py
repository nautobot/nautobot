from nautobot.cloud.api.serializers import CloudAccountSerializer, CloudTypeSerializer
from nautobot.cloud.filters import CloudAccountFilterSet, CloudTypeFilterSet
from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.cloud.tables import CloudAccountTable, CloudTypeTable
from nautobot.core.views.viewsets import NautobotUIViewSet


class CloudAccountUIViewSet(NautobotUIViewSet):
    queryset = CloudAccount.objects.all()
    filterset_class = CloudAccountFilterSet
    serializer_class = CloudAccountSerializer
    table_class = CloudAccountTable


class CloudTypeUIViewSet(NautobotUIViewSet):
    queryset = CloudType.objects.all()
    filterset_class = CloudTypeFilterSet
    serializer_class = CloudTypeSerializer
    table_class = CloudTypeTable
