from nautobot.core.api.routers import OrderedDefaultRouter

# from . import views

router = OrderedDefaultRouter(view_name="Wireless")

app_name = "wireless-api"
urlpatterns = router.urls
