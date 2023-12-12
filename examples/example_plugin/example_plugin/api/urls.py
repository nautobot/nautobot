from django.urls import include, path

from nautobot.apps.api import OrderedDefaultRouter
from example_plugin.api.views import AnotherExampleModelViewSet, ExampleModelViewSet, ExampleModelWebhook


router = OrderedDefaultRouter()
router.register("models", ExampleModelViewSet)
router.register("other-models", AnotherExampleModelViewSet)

urlpatterns = [
    path(
        "webhook/", ExampleModelWebhook.as_view(), name="examplemodel_webhook"
    ),  # URL path for testing plugin webhooks
    path("", include(router.urls)),
]
