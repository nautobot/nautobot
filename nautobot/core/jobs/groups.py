from nautobot.extras.jobs import Job, ObjectVar
from nautobot.extras.models import DynamicGroup


name = "System Jobs"


class RefreshDynamicGroupCaches(Job):
    """
    System job to recalculate and re-cache the members of Dynamic Groups for improved performance.
    """

    single_group = ObjectVar(
        description="Select to refresh only a single specified group instead of all groups",
        model=DynamicGroup,
        required=False,
    )

    class Meta:
        name = "Refresh Dynamic Group Caches"
        has_sensitive_variables = False

    def run(self, single_group=None):
        if single_group is not None:
            groups = [single_group]
        else:
            groups = DynamicGroup.objects.all()

        for group in groups:
            self.logger.info("Refreshing membership cache", extra={"object": group})
            group.update_cached_members()

        self.logger.info("All caches refreshed")
