from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView

from nautobot.apps.urls import NautobotUIViewSetRouter
from nautobot.apps.views import ObjectDynamicGroupsView

from example_app import views
from example_app.models import AnotherExampleModel, ExampleModel

app_name = "example_app"
router = NautobotUIViewSetRouter()
# ExampleModel is registered using the ViewSet
router.register("models", views.ExampleModelUIViewSet)
router.register("other-models", views.AnotherExampleModelUIViewSet)

urlpatterns = [
    path("", views.ExampleAppHomeView.as_view(), name="home"),
    path("config/", views.ExampleAppConfigView.as_view(), name="config"),
    # Still have the ability to add routes to a model that is using the NautbotUIViewSet.
    path(
        "models/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="examplemodel_dynamicgroups",
        kwargs={"model": ExampleModel},
    ),
    path(
        "other-models/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="anotherexamplemodel_dynamicgroups",
        kwargs={"model": AnotherExampleModel},
    ),
    path(
        "docs/",
        RedirectView.as_view(url=static("example_app/docs/index.html")),
        name="docs",
    ),
    path("circuits/<uuid:pk>/example-app-tab/", views.CircuitDetailAppTabView.as_view(), name="circuit_detail_tab"),
    path(
        "devices/<uuid:pk>/example-app-tab-1/",
        views.DeviceDetailAppTabOneView.as_view(),
        name="device_detail_tab_1",
    ),
    path(
        "devices/<uuid:pk>/example-app-tab-2/",
        views.DeviceDetailAppTabTwoView.as_view(),
        name="device_detail_tab_2",
    ),
    # This URL definition is here in order to test the override_views functionality which is defined
    # in examples.example_app_with_view_override.example_app_with_view_override.views
    path("override-target/", views.ViewToBeOverridden.as_view(), name="view_to_be_overridden"),
]
urlpatterns += router.urls
