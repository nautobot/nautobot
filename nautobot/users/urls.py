from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

# TODO: deprecate this app_name and use users
app_name = "user"

router = NautobotUIViewSetRouter()

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("preferences/", views.UserConfigView.as_view(), name="preferences"),
    path("password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("api-tokens/", views.TokenListView.as_view(), name="token_list"),
    path("api-tokens/add/", views.TokenEditView.as_view(), name="token_add"),
    path("api-tokens/<uuid:pk>/edit/", views.TokenEditView.as_view(), name="token_edit"),
    path(
        "api-tokens/<uuid:pk>/delete/",
        views.TokenDeleteView.as_view(),
        name="token_delete",
    ),
    path("advanced-settings/", views.AdvancedProfileSettingsEditView.as_view(), name="advanced_settings_edit"),
]

urlpatterns += router.urls
