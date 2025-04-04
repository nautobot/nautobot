from nautobot.core.api.routers import OrderedDefaultRouter

from . import views

router = OrderedDefaultRouter(view_name="Users")

# Users and groups
router.register("users", views.UserViewSet)
router.register("groups", views.GroupViewSet)

# Tokens
router.register("tokens", views.TokenViewSet)

# Permissions
router.register("permissions", views.ObjectPermissionViewSet)

# User preferences
router.register("config", views.UserConfigViewSet, basename="userconfig")

app_name = "users-api"
urlpatterns = router.urls
