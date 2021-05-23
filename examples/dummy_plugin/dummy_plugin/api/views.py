from nautobot.core.api.views import ModelViewSet

from dummy_plugin.models import DummyModel
from .serializers import DummySerializer
from ..filters import DummyModelFilterSet


class DummyViewSet(ModelViewSet):
    queryset = DummyModel.objects.all()
    serializer_class = DummySerializer
    filterset_class = DummyModelFilterSet
