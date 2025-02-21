"""Django urlpatterns declaration for nautobot_data_validation_engine app."""

from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView, ObjectNotesView
from nautobot.nautobot_data_validation_engine import models, views

app_name = "nautobot_data_validation_engine"

router = NautobotUIViewSetRouter()
router.register("data-compliance", views.DataComplianceListView)
router.register("regex-rules", views.RegularExpressionValidationRuleUIViewSet)
router.register("min-max-rules", views.MinMaxValidationRuleUIViewSet)
router.register("required-rules", views.RequiredValidationRuleUIViewSet)
router.register("unique-rules", views.UniqueValidationRuleUIViewSet)

urlpatterns = [
    path(
        "data-compliance/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="datacompliance_changelog",
        kwargs={"model": models.DataCompliance},
    ),
    path(
        "data-compliance/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="datacompliance_notes",
        kwargs={"model": models.DataCompliance},
    ),
    path(
        "data-compliance/<model>/<uuid:id>/",
        views.DataComplianceObjectView.as_view(),
        name="data-compliance-tab",
    ),
    path(
        "regex-rules/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="regularexpressionvalidationrule_changelog",
        kwargs={"model": models.RegularExpressionValidationRule},
    ),
    path(
        "regex-rules/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="regularexpressionvalidationrule_notes",
        kwargs={"model": models.RegularExpressionValidationRule},
    ),
    path(
        "min-max-rules/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="minmaxvalidationrule_changelog",
        kwargs={"model": models.MinMaxValidationRule},
    ),
    path(
        "min-max-rules/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="minmaxvalidationrule_notes",
        kwargs={"model": models.MinMaxValidationRule},
    ),
    path(
        "required-rules/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="requiredvalidationrule_changelog",
        kwargs={"model": models.RequiredValidationRule},
    ),
    path(
        "required-rules/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="requiredvalidationrule_notes",
        kwargs={"model": models.RequiredValidationRule},
    ),
    path(
        "unique-rules/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="uniquevalidationrule_changelog",
        kwargs={"model": models.UniqueValidationRule},
    ),
    path(
        "unique-rules/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="uniquevalidationrule_notes",
        kwargs={"model": models.UniqueValidationRule},
    ),
    *router.urls,
]
