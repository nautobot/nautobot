from nautobot.cloud.api.serializers import CloudAccountSerializer, CloudServiceSerializer, CloudTypeSerializer
from nautobot.cloud.filters import CloudAccountFilterSet, CloudServiceFilterSet, CloudTypeFilterSet
from nautobot.cloud.forms import (
    CloudAccountBulkEditForm,
    CloudAccountFilterForm,
    CloudAccountForm,
    CloudServiceBulkEditForm,
    CloudServiceFilterForm,
    CloudServiceForm,
    CloudTypeBulkEditForm,
    CloudTypeFilterForm,
    CloudTypeForm,
)
from nautobot.cloud.models import CloudAccount, CloudService, CloudType
from nautobot.cloud.tables import CloudAccountTable, CloudServiceTable, CloudTypeTable
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


class CloudServiceUIViewSet(NautobotUIViewSet):
    queryset = CloudService.objects.all()
    filterset_class = CloudServiceFilterSet
    filterset_form_class = CloudServiceFilterForm
    serializer_class = CloudServiceSerializer
    table_class = CloudServiceTable
    form_class = CloudServiceForm
    bulk_update_form_class = CloudServiceBulkEditForm
