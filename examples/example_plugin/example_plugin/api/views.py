import json
import os
import tempfile

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from nautobot.apps.api import NautobotModelViewSet

from example_plugin.api.serializers import (
    AnotherExampleModelSerializer,
    ExampleModelSerializer,
    ValueModelSerializer,
    ClassificationGroupsModelSerializer,
)
from example_plugin.filters import (
    AnotherExampleModelFilterSet,
    ExampleModelFilterSet,
    ValueModelFilterSet,
    ClassificationGroupsModelFilterSet,
)
from example_plugin.models import AnotherExampleModel, ExampleModel, ValueModel, ClassificationGroupsModel


class AnotherExampleModelViewSet(NautobotModelViewSet):
    queryset = AnotherExampleModel.objects.all()
    serializer_class = AnotherExampleModelSerializer
    filterset_class = AnotherExampleModelFilterSet


class ExampleModelViewSet(NautobotModelViewSet):
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleModelSerializer
    filterset_class = ExampleModelFilterSet


class ValueModelViewSet(NautobotModelViewSet):
    queryset = ValueModel.objects.all()
    serializer_class = ValueModelSerializer
    filterset_class = ValueModelFilterSet


class ClassificationGroupsModelViewSet(NautobotModelViewSet):
    queryset = ClassificationGroupsModel.objects.all()
    serializer_class = ClassificationGroupsModelSerializer
    filterset_class = ClassificationGroupsModelFilterSet


#
# Webhook Testing
#


@extend_schema(exclude=True)
class ExampleModelWebhook(APIView):
    """
    Example view used in testing webhooks for plugins.
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        with open(
            os.path.join(tempfile.gettempdir(), self.request.META.get("HTTP_TEST_NAME", "NO-TEST-NAME")), "w+"
        ) as f:
            f.write(json.dumps(self.request.data, indent=4))
        return Response({"message": "Submitted"})
