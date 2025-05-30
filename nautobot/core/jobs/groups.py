from nautobot.extras.choices import DynamicGroupTypeChoices
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
        query_params={
            "group_type": [DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET],
        },
        required=False,
    )

    class Meta:
        name = "Refresh Dynamic Group Caches"
        description = "Re-calculate and re-cache the membership lists of Dynamic Groups."
        has_sensitive_variables = False

    def run(self, single_group=None):  # pylint: disable=arguments-differ
        groups = DynamicGroup.objects.restrict(self.user, "view").exclude(
            group_type=DynamicGroupTypeChoices.TYPE_STATIC
        )
        if single_group is not None:
            groups = groups.filter(pk=single_group.pk)

        for group in groups:
            group.update_cached_members()
            self.logger.info("Cache refreshed successfully, now with %d members", group.count, extra={"object": group})

        self.logger.info("Cache(s) refreshed")
