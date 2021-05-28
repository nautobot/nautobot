from nautobot.core.api.views import ModelViewSet

from dummy_plugin.api.serializers import DummyModelSerializer
from dummy_plugin.filters import DummyModelFilterSet
from dummy_plugin.models import DummyModel


class DummyViewSet(ModelViewSet):
    queryset = DummyModel.objects.all()
    serializer_class = DummyModelSerializer
    filterset_class = DummyModelFilterSet
