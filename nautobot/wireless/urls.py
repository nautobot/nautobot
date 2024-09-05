from nautobot.core.views.routers import NautobotUIViewSetRouter

# from . import views

app_name = "wireless"
router = NautobotUIViewSetRouter()

urlpatterns = []
urlpatterns += router.urls
