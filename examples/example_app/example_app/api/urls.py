from django.urls import include, path

from nautobot.apps.api import OrderedDefaultRouter

from example_app.api.views import AnotherExampleModelViewSet, ExampleModelViewSet, ExampleModelWebhook

router = OrderedDefaultRouter(view_name="Example App")
router.register("models", ExampleModelViewSet)
router.register("other-models", AnotherExampleModelViewSet)

urlpatterns = [
    path("webhook/", ExampleModelWebhook.as_view(), name="examplemodel_webhook"),  # URL path for testing App webhooks
    path("", include(router.urls)),
]
