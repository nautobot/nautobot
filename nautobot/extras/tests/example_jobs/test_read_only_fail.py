from nautobot.dcim.models import Location, LocationType
from nautobot.extras.jobs import Job


class TestReadOnlyFail(Job):
    """
    Read only Job with fail result.
    """

    description = "Validate job import"

    class Meta:
        read_only = True

    def run(self, data, commit):
        """
        Job function.
        """

        location_type = LocationType.objects.create(name="Job Root Type")
        location = Location.objects.create(name="New Location", location_type=location_type)

        self.log_success(obj=location)
        raise Exception("Test failure")
