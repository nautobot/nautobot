import json
import os
import tempfile

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from nautobot.apps.api import NautobotModelViewSet

from example_app.api.serializers import AnotherExampleModelSerializer, ExampleModelSerializer
from example_app.filters import AnotherExampleModelFilterSet, ExampleModelFilterSet
from example_app.models import AnotherExampleModel, ExampleModel


class AnotherExampleModelViewSet(NautobotModelViewSet):
    queryset = AnotherExampleModel.objects.all()
    serializer_class = AnotherExampleModelSerializer
    filterset_class = AnotherExampleModelFilterSet


class ExampleModelViewSet(NautobotModelViewSet):
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleModelSerializer
    filterset_class = ExampleModelFilterSet


#
# Webhook Testing
#


@extend_schema(exclude=True)
class ExampleModelWebhook(APIView):
    """
    Example view used in testing webhooks for Apps.
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        with open(
            os.path.join(tempfile.gettempdir(), self.request.META.get("HTTP_TEST_NAME", "NO-TEST-NAME")), "w+"
        ) as f:
            f.write(json.dumps(self.request.data, indent=4))
        return Response({"message": "Submitted"})
