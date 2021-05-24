from nautobot.core.api import OrderedDefaultRouter

from dummy_plugin.api.views import DummyViewSet


router = OrderedDefaultRouter()
router.register("models", DummyViewSet)
urlpatterns = router.urls
