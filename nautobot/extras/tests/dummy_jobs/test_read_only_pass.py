from nautobot.dcim.models import Site
from nautobot.extras.jobs import Job


class TestReadOnlyPass(Job):
    """
    Ready only Job with pass result.
    """

    description = "Validate job import"

    class Meta:
        read_only = True

    def run(self, data, commit):
        """
        Job function.
        """

        site = Site.objects.create(name="Site", slug="site")

        self.log_success(obj=site)
