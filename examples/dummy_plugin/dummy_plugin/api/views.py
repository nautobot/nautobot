from rest_framework.permissions import IsAuthenticated
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

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        with open(f'/tmp/{self.request.META.get("HTTP_TEST_NAME", "NO-TEST-NAME")}', "w") as f:
            f.write("Test flag.")
        return Response("Submitted")
