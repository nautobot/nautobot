from django.urls import include, path

from nautobot.core.api import OrderedDefaultRouter
from example_plugin.api.views import ExampleModelViewSet, ExampleModelWebhook


router = OrderedDefaultRouter()
router.register("models", ExampleModelViewSet)

urlpatterns = [
    path(
        "webhook/", ExampleModelWebhook.as_view(), name="examplemodel_webhook"
    ),  # URL path for testing plugin webhooks
    path("", include(router.urls)),
]
