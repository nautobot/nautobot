from django.test import TestCase
from jinja2.exceptions import SecurityError, TemplateAssertionError
from netutils.utils import jinja2_convenience_function

from nautobot.core.utils import data
from nautobot.dcim import models as dcim_models
from nautobot.extras import models as extras_models
from nautobot.ipam import models as ipam_models


class NautobotJinjaFilterTest(TestCase):
    def test_invalid_templatetags_raise_exception(self):
        """Validate that executing render_jinja2 with an invalid filter will raise TemplateAssertionError."""
        helpers_not_valid = ["notvalid"]

        for helper in helpers_not_valid:
            with self.assertRaises(TemplateAssertionError):
                data.render_jinja2("{{ data | " + helper + " }}", {"data": None})

    def test_templatetags_helpers_in_jinja(self):
        """
        Only validate that all templatetags helpers have been properly registered as Django Jinja
        no need to check the returned value since we already have some unit tests for that
        """

        helpers_to_validate = [
            "placeholder",
            "render_json",
            "render_yaml",
            "render_markdown",
            "meta",
            "viewname",
            "validated_viewname",
            "validated_api_viewname",
            "bettertitle",
            "humanize_speed",
            "tzoffset",
            "fgcolor",
            "divide",
            "percentage",
            "get_docs_url",
            "has_perms",
            "has_one_or_more_perms",
            "split",
            "as_range",
            "meters_to_feet",
            "get_item",
            "settings_or_config",
            "slugify",
            "dbm",
        ]

        # For each helper, try to render jinja template with render_jinja2 and fail if TemplateAssertionError is raised
        for helper in helpers_to_validate:
            try:
                data.render_jinja2("{{ data | " + helper + " }}", {"data": None})
            except TemplateAssertionError:
                raise
            except Exception:  # noqa: S110  # try-except-pass -- an antipattern in general, but OK here
                pass

    def test_netutils_filters_in_jinja(self):
        """Import all Jinja filters from Netutils and validate that all have been properly loaded in Django Jinja."""
        filters = jinja2_convenience_function()

        for filter_ in filters.keys():
            try:
                data.render_jinja2("{{ data | " + filter_ + " }}", {"data": None})
            except TemplateAssertionError:
                raise
            except Exception:  # noqa: S110  # try-except-pass -- an antipattern in general, but OK here
                pass

    def test_sandboxed_render(self):
        """Assert that Jinja template rendering is sandboxed."""
        template_code = "{{ ''.__class__.__name__ }}"
        with self.assertRaises(SecurityError):
            data.render_jinja2(template_code=template_code, context={})

    def test_safe_render(self):
        """Assert that safe Jinja rendering still works."""
        location = dcim_models.Location.objects.filter(parent__isnull=False).first()
        template_code = "{{ obj.parent.name }}"
        try:
            value = data.render_jinja2(template_code=template_code, context={"obj": location})
        except SecurityError:
            self.fail("SecurityError raised on safe Jinja template render")
        else:
            self.assertEqual(value, location.parent.name)

    def test_render_blocks_various_unsafe_methods(self):
        """Assert that Jinja template rendering correctly blocks various unsafe Nautobot APIs."""
        device = dcim_models.Device.objects.first()
        dynamic_group = extras_models.DynamicGroup.objects.first()
        git_repository = extras_models.GitRepository.objects.create(
            name="repo", slug="repo", remote_url="file:///", branch="main"
        )
        interface = dcim_models.Interface.objects.first()
        interface_template = dcim_models.InterfaceTemplate.objects.first()
        location = dcim_models.Location.objects.first()
        module = dcim_models.Module.objects.first()
        prefix = ipam_models.Prefix.objects.first()
        secret = extras_models.Secret.objects.create(name="secret", provider="environment-variable")
        vrf = ipam_models.VRF.objects.first()

        context = {
            "device": device,
            "dynamic_group": dynamic_group,
            "git_repository": git_repository,
            "interface": interface,
            "interface_template": interface_template,
            "location": location,
            "module": module,
            "prefix": prefix,
            "secret": secret,
            "vrf": vrf,
            "JobResult": extras_models.JobResult,
            "ScheduledJob": extras_models.ScheduledJob,
        }

        for call in [
            "device.create_components()",
            "dynamic_group.add_members([])",
            "dynamic_group.remove_members([])",
            "git_repository.sync(None)",
            "git_repository.clone_to_directory()",
            "git_repository.cleanup_cloned_directory('/tmp/')",
            "interface.render_name_template()",
            "interface.add_ip_addresses([])",
            "interface_template.instantiate(device)",
            "interface_template.instantiate_model(interface_template, device)",
            "location.validated_save()",
            "module.create_components()",
            "module.render_component_names()",
            "prefix.reparent_ips()",
            "prefix.reparent_subnets()",
            "secret.get_value()",
            "vrf.add_device(device)",
            "vrf.add_prefix(prefix)",
            "JobResult.enqueue_job(None, None)",
            "JobResult.log('hello world')",
            "ScheduledJob.create_schedule(None, None)",
        ]:
            with self.subTest(call=call):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code="{{ " + call + " }}", context=context)
