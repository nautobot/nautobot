from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

# TODO: deprecate this app_name and use users
app_name = "user"

router = NautobotUIViewSetRouter()
router.register("api-tokens", views.TokenUIViewSet, basename="token")

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("preferences/", views.UserConfigView.as_view(), name="preferences"),
    path("navbar-favorites/", views.UserNavbarFavoritesAddView.as_view(), name="navbar_favorites_add"),
    path("navbar-favorites/delete/", views.UserNavbarFavoritesDeleteView.as_view(), name="navbar_favorites_delete"),
    path("password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("advanced-settings/", views.AdvancedProfileSettingsEditView.as_view(), name="advanced_settings_edit"),
]

urlpatterns += router.urls
