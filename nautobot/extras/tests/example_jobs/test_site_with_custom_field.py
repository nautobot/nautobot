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
        cf = CustomField(name="cf1", type=CustomFieldTypeChoices.TYPE_TEXT, default="-")
        cf.validated_save()
        cf.content_types.set([obj_type])

        self.log_success(obj=cf, message="CustomField created successfully.")

        site_1 = Site.objects.create(name="Test Site One", slug="test-site-one")
        # 2.0 TODO: #824 cf.slug rather than cf.name
        site_1.cf[cf.name] = "some-value"
        site_1.save()
        self.log_success(obj=site_1, message="Created a new site")

        site_2 = Site.objects.create(name="Test Site Two", slug="test-site-two")
        self.log_success(obj=site_2, message="Created another new site")

        return "Job completed."
