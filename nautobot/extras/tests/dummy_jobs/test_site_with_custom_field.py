from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Site
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.jobs import Job
from nautobot.extras.models import CustomField


class TestCreateSiteWithCustomField(Job):
    class Meta:
        name = "Site and Custom Field Creation"
        description = "Site with a custom field"

    def run(self, data, commit):
        obj_type = ContentType.objects.get_for_model(Site)
        cf = CustomField.objects.create(name="cf1", type=CustomFieldTypeChoices.TYPE_TEXT)
        cf.content_types.set([obj_type])

        self.log_success(obj=cf, message="CustomField created successfully.")

        site = Site.objects.create(name="Test Site", slug="test-site")
        site.cf[cf.name] = "some-value"
        site.save()
        self.log_success(obj=site, message="Created a new site")

        return "Job completed."
