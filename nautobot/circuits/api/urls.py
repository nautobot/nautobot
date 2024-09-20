from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Circuits")

# Providers
router.register("providers", views.ProviderViewSet)

# Circuits
router.register("circuit-types", views.CircuitTypeViewSet)
router.register("circuits", views.CircuitViewSet)
router.register("circuit-terminations", views.CircuitTerminationViewSet)

router.register("provider-networks", views.ProviderNetworkViewSet)

app_name = "circuits-api"
urlpatterns = router.urls
