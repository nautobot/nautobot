from nautobot.core.api import OrderedDefaultRouter

from .views import DummyViewSet


router = OrderedDefaultRouter()
router.register("models", DummyViewSet)
urlpatterns = router.urls
