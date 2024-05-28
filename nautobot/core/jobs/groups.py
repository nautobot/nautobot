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
        description = "Re-calculate and re-cache the membership lists of Dynamic Groups."
        has_sensitive_variables = False

    def run(self, single_group=None):
        if single_group is not None:
            groups = DynamicGroup.objects.restrict(self.user, "view").filter(pk=single_group.pk)
        else:
            groups = DynamicGroup.objects.restrict(self.user, "view")

        for group in groups:
            self.logger.info("Refreshing membership cache", extra={"object": group})
            group.update_cached_members()

        self.logger.info("All caches refreshed")
