"""Test Templatetags provided by Extras."""

from django.contrib.contenttypes.models import ContentType
from django.test.client import RequestFactory
from django.urls import reverse
from nautobot.dcim.models import Site
from nautobot.extras.models import Job, JobButton
from nautobot.extras.templatetags.job_buttons import job_buttons
from nautobot.utilities.testing import TestCase


class JobButtonsTest(TestCase):
    """Test Rendering of Job Buttons."""

    def setUp(self):
        super().setUp()
        self.site = Site.objects.create(name="Test", slug="test")
        self.job = Job.objects.get(job_class_name="TestJobButtonReceiverSimple")

        self.site_type = ContentType.objects.get_for_model(Site)

        job_button_config = {
            "name": "Job Button Site",
            "job": self.job,
            "defaults": {
                "text": "Job Button Site",
                "button_class": "primary",
            },
        }
        self.jobbutton, _ = JobButton.objects.get_or_create(**job_button_config)
        self.jobbutton.content_types.set([self.site_type])

    def test_job_buttons_non_grouped(self):
        """Job Button without a group and missing permissions renders disabled with a confirmation."""

        result = self._build_request()
        self.assertIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn("disabled", result)

    def test_job_buttons_non_grouped_no_confirm(self):
        """Job Button without a group and missing permissions renders disabled without a confirmation."""

        self.jobbutton.confirmation = False
        self.jobbutton.save()

        result = self._build_request()
        self.assertNotIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn("disabled", result)

    def test_job_buttons_non_grouped_perms(self):
        """Job Button without a group renders with a confirmation."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")

        result = self._build_request()
        self.assertIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertNotIn("disabled", result)

    def test_job_buttons_non_grouped_conditional_rendering(self):
        """Job Button Conditional Rendering Success Path renders."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")
        self.jobbutton.text = "{% if obj.slug == 'test' %}Job Button Site{% endif %}"
        self.jobbutton.save()

        result = self._build_request()
        self.assertIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertNotIn("disabled", result)

    def test_job_buttons_non_grouped_conditional_rendering_false(self):
        """Job Button Conditional Rendering Failure Path does not render."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")
        self.jobbutton.text = "{% if obj.slug == 'nope' %}Job Button Site{% endif %}"
        self.jobbutton.save()

        result = self._build_request()
        self.assertEqual(
            "",
            result,
        )

    def test_job_buttons_non_grouped_conditional_rendering_exception(self):
        """Job Button Conditional Rendering Exception Path renders."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")
        self.jobbutton.text = "{% if obj.slug == 'nope' %}Job Button Site"
        self.jobbutton.save()

        result = self._build_request()
        self.assertNotIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertNotIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn("disabled", result)

    def test_job_buttons_grouped(self):
        """Job Button with a group and missing permissions renders disabled with a confirmation."""

        self.jobbutton.group_name = "Site Buttons"
        self.jobbutton.save()

        result = self._build_request()
        self.assertIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn("Site Buttons", result)
        self.assertIn("disabled", result)

    def test_job_buttons_grouped_perms(self):
        """Job Button with a group and renders with a confirmation."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")
        self.jobbutton.group_name = "Site Buttons"
        self.jobbutton.save()

        result = self._build_request()
        self.assertIn(
            f'id="confirm_modal_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn(
            f'id="form_id_{self.jobbutton.pk}"',
            result,
        )
        self.assertIn("Site Buttons", result)
        self.assertNotIn("disabled", result)

    def test_job_buttons_grouped_conditional_rendering_false(self):
        """Job Button with a group does not render if Conditional Rendering False."""

        self.add_permissions("extras.run_jobbutton", "extras.run_job")
        self.jobbutton.group_name = "Site Buttons"
        self.jobbutton.text = "{% if obj.slug == 'nope' %}Job Site Button{% endif %}"
        self.jobbutton.save()

        result = self._build_request()
        self.assertEqual("", result)

    def test_job_buttons_no_buttons(self):
        self.jobbutton.delete()
        self.assertEqual(
            "",
            self._build_request(),
        )

    def _build_request(self):
        request = RequestFactory().get(
            reverse(
                "dcim:site",
                kwargs={"slug": self.site.slug},
            )
        )
        context = {
            "request": request,
            "user": self.user,
            "perms": {},
            "csrf_token": "",
            "settings": {},
        }
        return job_buttons(context=context, obj=self.site)
