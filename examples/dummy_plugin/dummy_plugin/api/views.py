import json
import os
import tempfile

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from nautobot.core.api.views import ModelViewSet

from dummy_plugin.api.serializers import DummyModelSerializer
from dummy_plugin.filters import DummyModelFilterSet
from dummy_plugin.models import DummyModel


class DummyViewSet(ModelViewSet):
    queryset = DummyModel.objects.all()
    serializer_class = DummyModelSerializer
    filterset_class = DummyModelFilterSet


#
# Webhook Testing
#


class DummyModelWebhook(APIView):
    """
    Dummy view used in testing webhooks for plugins.
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):
        with open(
            os.path.join(tempfile.gettempdir(), self.request.META.get("HTTP_TEST_NAME", "NO-TEST-NAME")), "w+"
        ) as f:
            f.write(json.dumps(self.request.data, indent=4))
        return Response({"message": "Submitted"})
