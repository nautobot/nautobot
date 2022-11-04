from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import GitRepository, JobResult, ObjectChange


def get_job_results(request):
    """Callback function to collect job history for panel."""
    return (
        JobResult.objects.filter(status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES)
        .defer("data")
        .order_by("-completed")[:10]
    )


def get_changelog(request):
    """Callback function to collect changelog for panel."""
    # v2 TODO(jathan): Replace prefetch_related with select_related
    return ObjectChange.objects.restrict(request.user, "view").prefetch_related("user", "changed_object_type")[:15]


layout = (
    HomePagePanel(
        name="Data Sources",
        weight=700,
        items=(
            HomePageItem(
                name="Git Repositories",
                link="extras:gitrepository_list",
                model=GitRepository,
                description="Collections of data and/or job files",
                permissions=["extras.view_gitrepository"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="Job History",
        permissions=["extras.view_jobresult"],
        weight=800,
        custom_data={"job_results": get_job_results},
        custom_template="panel_jobhistory.html",
    ),
    HomePagePanel(
        name="Change Log",
        permissions=["extras.view_objectchange"],
        weight=900,
        custom_data={"changelog": get_changelog},
        custom_template="panel_changelog.html",
    ),
)
