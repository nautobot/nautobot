from django.urls import include, path

from nautobot.core.api import OrderedDefaultRouter
from dummy_plugin.api.views import DummyViewSet, DummyModelWebhook


router = OrderedDefaultRouter()
router.register("models", DummyViewSet)

urlpatterns = [
    path("webhook/", DummyModelWebhook.as_view(), name="dummymodel_webhook"),  # URL path for testing plugin webhooks
    path("", include(router.urls)),
]
