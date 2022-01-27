import json
import os
import tempfile

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from nautobot.core.api.views import ModelViewSet

from example_plugin.api.serializers import ExampleModelSerializer
from example_plugin.filters import ExampleModelFilterSet
from example_plugin.models import ExampleModel


class ExampleModelViewSet(ModelViewSet):
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleModelSerializer
    filterset_class = ExampleModelFilterSet


#
# Webhook Testing
#


class ExampleModelWebhook(APIView):
    """
    Example view used in testing webhooks for plugins.
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):
        with open(
            os.path.join(tempfile.gettempdir(), self.request.META.get("HTTP_TEST_NAME", "NO-TEST-NAME")), "w+"
        ) as f:
            f.write(json.dumps(self.request.data, indent=4))
        return Response({"message": "Submitted"})
