from nautobot.cloud.api.serializers import CloudAccountSerializer, CloudTypeSerializer
from nautobot.cloud.filters import CloudAccountFilterSet, CloudTypeFilterSet
from nautobot.cloud.forms import (
    CloudAccountBulkEditForm,
    CloudAccountFilterForm,
    CloudAccountForm,
    CloudTypeBulkEditForm,
    CloudTypeFilterForm,
    CloudTypeForm,
)
from nautobot.cloud.models import CloudAccount, CloudType
from nautobot.cloud.tables import CloudAccountTable, CloudTypeTable
from nautobot.core.views.viewsets import NautobotUIViewSet


class CloudAccountUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = CloudAccountBulkEditForm
    queryset = CloudAccount.objects.all()
    filterset_class = CloudAccountFilterSet
    filterset_form_class = CloudAccountFilterForm
    serializer_class = CloudAccountSerializer
    table_class = CloudAccountTable
    form_class = CloudAccountForm


class CloudTypeUIViewSet(NautobotUIViewSet):
    queryset = CloudType.objects.all()
    filterset_class = CloudTypeFilterSet
    filterset_form_class = CloudTypeFilterForm
    serializer_class = CloudTypeSerializer
    table_class = CloudTypeTable
    form_class = CloudTypeForm
    bulk_update_form_class = CloudTypeBulkEditForm
