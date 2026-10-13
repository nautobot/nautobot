import types

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.db.models import Case, Count, IntegerField, Max, Min, Subquery, Sum, Value, When
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.test import override_settings, TestCase
from jinja2.exceptions import SecurityError, TemplateAssertionError
from netutils.utils import jinja2_convenience_function
import regex

from nautobot.core.exceptions import SensitiveFieldError
from nautobot.core.templating import (
    deny_caller_supplied_sql,
    NautobotSandboxedContext,
    NautobotSandboxedEnvironment,
)
from nautobot.core.testing.utils import temporarily_sensitive_fields
from nautobot.core.utils import data
from nautobot.dcim import models as dcim_models
from nautobot.extras import models as extras_models
from nautobot.extras.choices import DynamicGroupTypeChoices
from nautobot.ipam import models as ipam_models
from nautobot.users import models as users_models


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

    def test_settings_or_config_app_name_not_supported_in_jinja(self):
        """Regression test for GHSA-6jmc-h6f2-46j4: the Jinja filter must not read app PLUGINS_CONFIG values."""
        with self.assertRaises(ValueError):
            data.render_jinja2("{{ 'SAMPLE_VARIABLE' | settings_or_config('example_app') }}", {})

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

    def test_render_blocks_orm_cursor_gadget_chain(self):
        """Assert the Django ORM -> raw database cursor SSTI gadget chain is blocked."""
        location = dcim_models.Location.objects.first()
        context = {
            "obj": location,
            # A live Query and database connection placed directly in context to prove the
            # "allow-nothing" container blocking, independent of how they were reached.
            "query": dcim_models.Location.objects.all().query,
            "connection": connections["default"],
        }

        # Using a blocked object any further (attribute access or call) raises SecurityError.
        for template_code in [
            # The full cursor chain and intermediate reaches into it.
            "{{ obj.tags.all().query.get_compiler('default').connection.cursor() }}",
            "{{ obj.tags.all().query.get_compiler('default') }}",
            "{{ obj.tags.all().query.get_compiler('default').connection.cursor().execute('SELECT 1') }}",
            # App-registry reach to arbitrary models, via both `get_meta()` and the `meta` filter.
            "{{ obj.tags.all().query.get_meta().apps.get_model('extras', 'tag') }}",
            "{{ (obj | meta('apps')).get_model('extras', 'tag') }}",
            # Alternate raw-SQL path via the model class and manager.
            "{{ obj.tags.model.objects.raw('SELECT 1') }}",
            # Container allow-nothing: DB/ORM internals expose nothing, including driver-specific and
            # credential-bearing attributes a name-only deny-list would miss.
            "{{ query.get_compiler('default') }}",
            "{{ connection.cursor() }}",
            # The `attr` filter routes through is_safe_attribute (see CVE-2025-27516), so it cannot be
            # used to sidestep the ORM blocks either.
            "{{ obj.tags.all() | attr('query') | attr('get_compiler')('default') }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

        # Terminal access to a blocked attribute yields empty output; the internal object never
        # escapes into the template (rendering the object directly would leak SQL or DB credentials).
        for template_code in [
            "{{ obj.tags.all().query }}",
            "{{ obj.tags.all() | attr('query') }}",
            "{{ query.get_compiler }}",
            "{{ connection.settings_dict }}",
            "{{ connection.cursor }}",
        ]:
            with self.subTest(template_code=template_code):
                self.assertEqual(data.render_jinja2(template_code=template_code, context=context), "")

    def test_render_allows_safe_orm_access(self):
        """Assert legitimate model/manager/queryset access is not over-blocked by the sandbox."""
        location = dcim_models.Location.objects.first()
        # A plain object whose attribute names collide with the Manager/QuerySet deny-list, proving
        # that block is scoped to Manager/QuerySet containers and not applied to ordinary objects.
        namespace = types.SimpleNamespace(query="safe-query", raw="safe-raw", model="safe-model", db="safe-db")
        context = {"obj": location, "ns": namespace}
        for template_code in [
            "{{ obj.name }}",
            "{{ obj.tags.all() | length }}",
            "{% for tag in obj.tags.all() %}{{ tag.name }}{% endfor %}",
            "{{ obj.tags.all().count() }}",
            "{{ obj.tags.filter(name='does-not-exist').first() }}",
            "{{ ns.query }}{{ ns.raw }}{{ ns.model }}{{ ns.db }}",
        ]:
            with self.subTest(template_code=template_code):
                try:
                    data.render_jinja2(template_code=template_code, context=context)
                except SecurityError:
                    self.fail(f"SecurityError raised on safe Jinja template render: {template_code}")

    def test_render_cannot_retrieve_a_sensitive_model_field(self):
        """Assert a user-authored template cannot read a field declared in a model's `sensitive_fields`.

        Templates are denied regardless of `STRICT_SENSITIVE_FIELDS`, which is why both values of the
        setting are exercised here. That setting exists so first-party code and Apps can migrate to the
        explicit opt-in methods over time; a user-authored template is untrusted input with no legitimate
        need for a credential, so it gets no such grace period.
        """
        user = users_models.User.objects.create_user(username="jinja-sensitive-fields-testuser")
        users_models.Token.objects.create(user=user)
        context = {"obj": user}
        for strict in (True, False):
            for template_code in [
                "{{ obj.tokens.first().key }}",
                "{{ obj.tokens.values_list('key', flat=True) | list }}",
                "{{ obj.tokens.values('key') | list }}",
                "{{ obj.tokens.all().values_list('key') | list }}",
                "{% for t in obj.tokens.all() %}{{ t.key }}{% endfor %}",
                # Subscript syntax reaches `Environment.getitem()` rather than `getattr()`.
                "{% for t in obj.tokens.all() %}{{ t['key'] }}{% endfor %}",
                # The explicit opt-in API must not be reachable from a template, or it would sidestep
                # every other check, including the annotation alias it stores the value under.
                "{{ obj.tokens.first().get_sensitive_field('key') }}",
                "{{ obj.tokens.with_sensitive_fields('key').first().key }}",
                "{{ obj.tokens.with_sensitive_fields('key').values_list('_sensitive_field_key') | list }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        with self.assertRaises((SecurityError, SensitiveFieldError)):
                            data.render_jinja2(template_code=template_code, context=context)

    def test_render_cannot_retrieve_a_sensitive_field_via_in_bulk(self):
        """Assert `in_bulk()` cannot be used to return sensitive values as the keys of its result.

        `in_bulk(field_name=...)` takes the field to key its result by as a keyword-only argument, so it
        is not visible to the positional-argument check that covers the other projection methods, and its
        return value puts the field's values in the dict keys. It is therefore excluded from the sandbox's
        allowed Manager/QuerySet methods rather than argument-checked.
        """
        user = users_models.User.objects.create_user(username="jinja-in-bulk-testuser")
        users_models.Token.objects.create(user=user)
        context = {"obj": user}
        for strict in (True, False):
            for template_code in [
                "{{ obj.tokens.in_bulk(field_name='key') }}",
                "{{ obj.tokens.all().in_bulk(field_name='key') }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        with self.assertRaises((SecurityError, SensitiveFieldError)):
                            data.render_jinja2(template_code=template_code, context=context)

    def test_render_cannot_retrieve_a_sensitive_field_via_attribute_filters(self):
        """Assert the `attr` and `map` filters cannot read a sensitive field.

        Both call `is_safe_attribute()` directly rather than going through `Environment.getattr()`, so
        they are enforced by a different branch of the sandbox than plain attribute access and would
        regress independently of it.
        """
        user = users_models.User.objects.create_user(username="jinja-attr-filter-testuser")
        users_models.Token.objects.create(user=user)
        context = {"obj": user}
        for strict in (True, False):
            for template_code in [
                "{{ obj.tokens.first()|attr('key') }}",
                "{{ obj.tokens.all()|map(attribute='key')|list }}",
                "{{ obj.tokens.all()|map('attr', 'key')|list }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        with self.assertRaises((SecurityError, SensitiveFieldError)):
                            data.render_jinja2(template_code=template_code, context=context)

    def test_render_cannot_retrieve_a_user_password_hash(self):
        """Assert a template cannot read a viewer's password hash.

        Custom Links and Job Buttons render an author's template against the viewing user's own `User`
        object, so a readable password hash would be disclosed to whoever authored the template.
        """
        user = users_models.User.objects.create_user(
            username="jinja-password-testuser",
            password="probe-password-value",  # noqa: S106
        )
        context = {"user": user, "obj": user}
        for strict in (True, False):
            for template_code in [
                "{{ user.password }}",
                "{{ user.password[:28] }}",
                "{{ user['password'] }}",
                "{{ user|attr('password') }}",
                "{{ [user]|map(attribute='password')|list }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        with self.assertRaises((SecurityError, SensitiveFieldError)):
                            data.render_jinja2(template_code=template_code, context=context)

    def test_render_checks_a_named_projection_against_the_querysets_model(self):
        """Assert the projection check resolves the model from the queryset, not the manager's attribute.

        django-taggit's manager sets its `model` attribute to the model the tags are attached to, while
        its queryset yields `Tag`. Reading the attribute would check `Location.sensitive_fields` for a
        projection that actually selects `Tag` columns, and `Location` has a `description` field of its
        own, so the mismatch would go unnoticed rather than erroring.
        """
        location = dcim_models.Location.objects.first()
        location.tags.add(
            extras_models.Tag.objects.create(name="jinja-projection-model-tag", description="withheld-value")
        )
        context = {"obj": location}
        for template_code in [
            "{{ obj.tags.values('description') | list }}",
            "{{ obj.tags.values_list('description') | list }}",
        ]:
            with self.subTest(template_code=template_code):
                with temporarily_sensitive_fields(extras_models.Tag, "description"):
                    with self.assertRaises((SecurityError, SensitiveFieldError)):
                        data.render_jinja2(template_code=template_code, context=context)

    def test_render_narrows_a_bare_projection_to_non_sensitive_fields(self):
        """Assert a projection naming no fields returns the model's non-sensitive fields and nothing more.

        `values()`/`values_list()` with no field names select every concrete column, so there is no
        argument for the lookup-path check to inspect, and each row comes back as a plain dict or tuple
        rather than a model instance, which is what the attribute check is keyed on.
        """
        location = dcim_models.Location.objects.first()
        tag = extras_models.Tag.objects.create(name="jinja-bare-projection-tag", description="withheld-value")
        location.tags.add(tag)
        context = {"obj": location}
        for strict in (True, False):
            for template_code in [
                "{{ obj.tags.values() | list }}",
                "{{ obj.tags.values_list() | list }}",
                "{{ obj.tags.all().values() | list }}",
                "{{ obj.tags.all().values_list() | list }}",
                # A Nautobot-defined (non-stock) wrapper, so the Manager/QuerySet allowlist passes it through.
                "{{ obj.tags.all().distinct_values_list() | list }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        with temporarily_sensitive_fields(extras_models.Tag, "description"):
                            rendered = data.render_jinja2(template_code=template_code, context=context)
                    self.assertNotIn("withheld-value", rendered)
                    # Narrowed, not emptied: the rest of the row is still projected.
                    self.assertIn(tag.name, rendered)

    def test_render_cannot_retrieve_a_credential_via_a_bare_projection(self):
        """Assert an argument-less projection cannot be used to read an API token or a password hash.

        The same denial as the tests above, stated against the fields that actually hold a credential,
        since those are what a regression here would disclose.
        """
        user = users_models.User.objects.create_user(
            username="jinja-bare-projection-testuser",
            password="probe-password-value",  # noqa: S106  # hardcoded-password-func-arg -- ok as this is test code only
        )
        token = users_models.Token.objects.create(user=user, description="bare projection regression")
        permission = users_models.ObjectPermission.objects.create(
            name="jinja-bare-projection-permission", actions=["view"]
        )
        permission.users.add(user)
        context = {"obj": user}
        for strict in (True, False):
            for template_code in [
                "{{ obj.tokens.values() | list }}",
                "{{ obj.tokens.values_list() | list }}",
                "{{ obj.tokens.all().values() | list }}",
                "{{ obj.tokens.all().values_list() | list }}",
                "{{ obj.tokens.all().distinct_values_list() | list }}",
                # A User queryset, reached by traversing a shared object permission.
                "{{ obj.object_permissions.first().users.values() | list }}",
            ]:
                with self.subTest(strict=strict, template_code=template_code):
                    with override_settings(STRICT_SENSITIVE_FIELDS=strict):
                        rendered = data.render_jinja2(template_code=template_code, context=context)
                    self.assertNotIn(token.key, rendered)
                    self.assertNotIn(user.password, rendered)
                    self.assertNotEqual(rendered.strip(), "")

    def test_render_allows_a_bare_projection_on_a_model_without_sensitive_fields(self):
        """Assert the narrowing is scoped to models that actually declare sensitive fields.

        Almost no model declares any, and bare projections are used routinely by App-authored templates,
        so the overwhelmingly common case has to pass through to Django untouched.
        """
        location = dcim_models.Location.objects.first()
        tag = extras_models.Tag.objects.create(name="jinja-bare-projection-allowed-tag", description="visible-value")
        location.tags.add(tag)
        context = {"obj": location}
        for template_code in [
            "{{ obj.tags.values() | list }}",
            "{{ obj.tags.values_list() | list }}",
            "{{ obj.tags.all().distinct_values_list() | list }}",
        ]:
            with self.subTest(template_code=template_code):
                self.assertIn("visible-value", data.render_jinja2(template_code=template_code, context=context))

    def test_render_allows_filtering_on_a_sensitive_model_field(self):
        """Assert the sensitive-field denial does not over-block: filtering by the field is still allowed.

        The contract is that the value is never returned, not that the column cannot be referenced. A
        filter value is supplied by the template author, so it discloses nothing.
        """
        user = users_models.User.objects.create_user(username="jinja-sensitive-filter-testuser")
        users_models.Token.objects.create(user=user)
        context = {"obj": user}
        for template_code in [
            "{{ obj.tokens.filter(key='not-a-real-key').count() }}",
            "{{ obj.tokens.exclude(key='not-a-real-key').count() }}",
            "{{ obj.tokens.all().count() }}",
            "{{ obj.tokens.values_list('description', flat=True) | list }}",
        ]:
            with self.subTest(template_code=template_code):
                try:
                    data.render_jinja2(template_code=template_code, context=context)
                except (SecurityError, SensitiveFieldError):
                    self.fail(f"Sensitive-field denial over-blocked a safe template render: {template_code}")

    def test_context_call_enforces_callable_safety(self):
        """Assert callables invoked through Context.call are subject to the sandbox's is_safe_callable check."""
        environment = NautobotSandboxedEnvironment()
        context = environment.from_string("").new_context()
        self.assertIsInstance(context, NautobotSandboxedContext)

        location = dcim_models.Location.objects.first()
        # An `alters_data` method must be rejected on this path, not silently invoked.
        with self.assertRaises(SecurityError):
            context.call(location.delete)
        # The object is untouched and ordinary safe callables still work.
        self.assertTrue(dcim_models.Location.objects.filter(pk=location.pk).exists())
        self.assertEqual(context.call(str, location.name), str(location.name))

    def test_expression_guard_ignores_a_class_given_where_an_instance_belongs(self):
        """Assert the expression check passes over a class rather than inspecting it as an instance.

        Only an instance can carry SQL, so a class handed to a queryset method is Django's to reject.
        Inspecting one here would call `get_source_expressions()` unbound and surface a `TypeError` from
        the sandbox for a template that is merely wrong.
        """
        queryset = dcim_models.Location.objects.all()
        # Neither call may raise here. What Django then makes of the class is Django's business; these
        # assert only that the sandbox hands it over rather than failing on it.
        deny_caller_supplied_sql(queryset.order_by, (Count,), {})
        deny_caller_supplied_sql(queryset.annotate, (), {"x": RawSQL})

    def test_render_allows_tree_model_navigation(self):
        """Assert tree models stay usable in templates, including the parts that use raw SQL internally.

        `TreeQuerySet` methods are not stock `QuerySet` attributes, so the Manager/QuerySet allowlist
        passes them through. `max_tree_depth()` matters most here: it calls `extra()` itself
        (`nautobot/core/models/tree_queries.py`), which shows that denying `extra` to templates does not
        reach into Nautobot's own queries.
        """
        location = dcim_models.Location.objects.filter(parent__isnull=False).first()
        context = {"obj": location, "qs": dcim_models.Location.objects.all()}
        for template_code in [
            "{{ obj.ancestors() | list | length }}",
            "{{ obj.descendants() | list | length }}",
            "{{ obj.siblings | list | length }}",
            "{{ obj.parent.name }}",
            "{{ obj.children.all() | list | length }}",
            "{{ qs.with_tree_fields() | list | length }}",
            "{{ qs.ancestors(obj) | list | length }}",
            "{{ qs.max_tree_depth() }}",
            "{% for o in qs.with_tree_fields()[:3] %}{{ o.tree_depth }}{% endfor %}",
        ]:
            with self.subTest(template_code=template_code):
                try:
                    data.render_jinja2(template_code=template_code, context=context)
                except SecurityError:
                    self.fail(f"SecurityError raised on safe tree model render: {template_code}")

        # Reaching for raw SQL stays denied, on a tree queryset as on any other.
        for template_code in [
            "{{ qs.extra(order_by=['-id']) | list }}",
            "{{ qs.with_tree_fields().extra(order_by=['-id']) | list }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

    def test_render_allows_safe_template_helpers(self):
        """Assert the Context.call guard does not break ordinary template helpers such as translation."""
        context = {"obj": dcim_models.Location.objects.first()}
        for template_code, expected in [
            ("{{ _('Search') }}", "Search"),
            ("{{ _('Home') }}", "Home"),
        ]:
            with self.subTest(template_code=template_code):
                try:
                    self.assertEqual(data.render_jinja2(template_code=template_code, context=context), expected)
                except SecurityError:
                    self.fail(f"SecurityError raised on safe template render: {template_code}")

    def test_render_blocks_arbitrary_sql_and_model_pivot(self):
        """Assert the QuerySet.extra() SQL-injection and ContentType model-pivot gadget classes are blocked.

        Regression for GHSA-2v7j-x3g6-qj94 (incomplete fix for GHSA-p99c-c9qx-34fw). Covers the vulnerability
        class, not only the two published PoCs: the ContentType instance-method siblings that reach an
        unrestricted arbitrary-model queryset without ever exposing the model class to the sandbox.
        """
        location = dcim_models.Location.objects.first()
        content_type = ContentType.objects.get_for_model(dcim_models.Location)
        context = {"obj": location, "ct": content_type}

        # Calling or further-traversing a blocked attribute raises SecurityError.
        for template_code in [
            # extra() raw-SQL injection.
            "{{ obj.status.content_types.all().extra(select={'zz': '(SELECT 1)'}).values('zz')[:1]|list }}",
            # model_class() pivot to an arbitrary model's unrestricted manager.
            "{{ obj.status.content_types.all().first().model_class().objects.values('id')[:1]|list }}",
            "{{ obj.status.content_types.all().first().model_class().objects.count() }}",
            # ContentType instance-method pivots: build the model class and its _base_manager internally,
            # so the model-class guard never sees it; must be blocked by name on the ContentType instance.
            "{{ ct.get_all_objects_for_this_type().values('id')[:1]|list }}",
            # `meta` filter routes to a model class / default manager, then onward to a blocked gadget.
            "{{ (obj | meta('model')).objects.count() }}",
            "{{ (obj | meta('default_manager')).all().extra(select={'z': '(SELECT 1)'})|list }}",
            # The `attr`/`map` filters route through is_safe_attribute (CVE-2025-27516) and must not
            # hand back a working `extra`.
            "{{ (obj.tags.all() | attr('extra'))(select={'z': '(SELECT 1)'})|list }}",
            "{{ ([obj.tags.all()] | map('attr', 'extra') | list)[0](select={'z': '(SELECT 1)'})|list }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

        # Terminal access to a blocked attribute yields empty output; the gadget never escapes into the
        # template. These render a bound-method repr (non-empty) before the fix, i.e. the escape is open.
        for template_code in [
            "{{ ct.model_class }}",
            "{{ ct.get_all_objects_for_this_type }}",
            "{{ ct.get_object_for_this_type }}",
            "{{ obj.tags.all().extra }}",
            "{{ obj.tags.all().select_for_update }}",
            "{{ obj.tags.all().using }}",
        ]:
            with self.subTest(template_code=template_code):
                self.assertEqual(data.render_jinja2(template_code=template_code, context=context), "")

    def test_render_allows_custom_manager_methods(self):
        """Assert app/Nautobot custom (non-stock) manager/queryset methods still pass the sandbox.

        The hybrid allowlist gates only stock Django Manager/QuerySet attributes; custom methods such as
        Nautobot's `restrict` and `distinct_values_list` (defined on RestrictedQuerySet) must remain usable.
        """
        location = dcim_models.Location.objects.first()
        user = get_user_model().objects.first() or get_user_model().objects.create(username="jinja-sandbox-test")
        context = {"obj": location, "user": user}
        for template_code in [
            "{{ obj.tags.all().restrict(user) | list }}",
            "{{ obj.tags.all().restrict(user).count() }}",
            "{{ obj.tags.all().distinct_values_list('name', flat=True) | list }}",
        ]:
            with self.subTest(template_code=template_code):
                try:
                    data.render_jinja2(template_code=template_code, context=context)
                except SecurityError:
                    self.fail(f"SecurityError raised on safe custom-method render: {template_code}")

    def test_render_allows_analytics_queryset_methods(self):
        """Assert the read/analytics queryset surface real apps render through the sandbox is not over-blocked."""
        location = dcim_models.Location.objects.first()
        # `Count` mirrors how analytics apps inject expression helpers into their own render context.
        context = {"obj": location, "Count": Count, "Max": Max, "Min": Min}
        for template_code in [
            # Expressions composed from a field reference disclose nothing on their own and stay allowed,
            # unlike one carrying a caller-supplied SQL string.
            "{{ obj.tags.all().annotate(n=Max('name')).values('n') | list }}",
            "{{ obj.tags.all().aggregate(n=Min('name')) }}",
            "{{ obj.tags.all().values('name') | list }}",
            "{{ obj.tags.all().values_list('name', flat=True) | list }}",
            "{{ obj.tags.all().distinct().count() }}",
            "{{ obj.tags.all().exclude(name='does-not-exist').count() }}",
            "{{ obj.tags.all().order_by('name') | list }}",
            "{{ obj.tags.all().exists() }}",
            "{{ obj.tags.all().only('name') | list }}",
            "{{ obj.tags.all().defer('description') | list }}",
            "{{ obj.tags.all().annotate(n=Count('pk')).values('n') | list }}",
            "{{ obj.tags.all().aggregate(n=Count('pk')) }}",
        ]:
            with self.subTest(template_code=template_code):
                try:
                    data.render_jinja2(template_code=template_code, context=context)
                except SecurityError:
                    self.fail(f"SecurityError raised on safe analytics render: {template_code}")

    def test_render_allows_queryset_iterator(self):
        """Assert `iterator()` remains usable in templates, on both querysets and managers."""
        location = dcim_models.Location.objects.first()
        location_ct = ContentType.objects.get_for_model(dcim_models.Location)
        tag = extras_models.Tag.objects.create(name="jinja-sandbox-iterator-probe")
        tag.content_types.add(location_ct)
        location.tags.add(tag)

        queryset = dcim_models.Device.objects.all()
        device_count = queryset.count()
        self.assertNotEqual(device_count, 0)
        tag_count = location.tags.count()
        context = {"obj": location, "queryset": queryset}

        for template_code, expected in [
            # On a QuerySet, as an Export Template receives it.
            ("{{ queryset.iterator() | list | length }}", str(device_count)),
            ("{% for device in queryset.iterator() %}x{% endfor %}", "x" * device_count),
            # On a Manager, which is how every related-object accessor reaches the template.
            ("{{ obj.tags.iterator() | list | length }}", str(tag_count)),
            ("{{ obj.tags.all().iterator() | list | length }}", str(tag_count)),
        ]:
            with self.subTest(template_code=template_code):
                try:
                    rendered = data.render_jinja2(template_code=template_code, context=context)
                except SecurityError:
                    self.fail(f"SecurityError raised on read-only streaming render: {template_code}")
                self.assertEqual(rendered, expected)

    def test_render_allows_readonly_queryset_introspection(self):
        """Assert read-only queryset introspection is not over-blocked."""
        context = {"queryset": dcim_models.Device.objects.order_by("name")}

        # `ordered` is a property, so a denial renders as empty output rather than raising; assert the real value.
        with self.subTest(template_code="{{ queryset.ordered }}"):
            self.assertEqual(data.render_jinja2(template_code="{{ queryset.ordered }}", context=context), "True")

        with self.subTest(template_code="{{ queryset.explain() }}"):
            try:
                explained = data.render_jinja2(template_code="{{ queryset.explain() }}", context=context)
            except SecurityError:
                self.fail("SecurityError raised on read-only render: {{ queryset.explain() }}")
            self.assertNotEqual(explained, "")

    def test_render_denies_stock_queryset_attrs_inventory(self):
        """Lock the denied-on-purpose stock Manager/QuerySet attribute inventory (prevents accidental allowlisting)."""
        # A real RestrictedQuerySet placed directly in context so both stock reads and stock gadgets are present.
        context = {"qs": dcim_models.Location.objects.all()}
        for attr in [
            "extra",
            "using",
            "select_for_update",
            "query",
            "db",
            "model",
            "get_queryset",
            "get_or_create",
            "update_or_create",
        ]:
            template_code = "{{ qs." + attr + " }}"
            with self.subTest(attr=attr):
                self.assertEqual(data.render_jinja2(template_code=template_code, context=context), "")

    def test_render_blocks_tags_manager_writes(self):
        """Assert a user-authored template cannot write to the database through the `tags` manager."""
        location = dcim_models.Location.objects.first()
        location_ct = ContentType.objects.get_for_model(dcim_models.Location)
        tag = extras_models.Tag.objects.create(name="jinja-sandbox-write-probe")
        tag.content_types.add(location_ct)
        location.tags.add(tag)
        baseline_tag_names = set(location.tags.values_list("name", flat=True))
        self.assertIn("jinja-sandbox-write-probe", baseline_tag_names)

        context = {"obj": location}
        for template_code in [
            "{{ obj.tags.clear() }}",
            "{{ obj.tags.remove('jinja-sandbox-write-probe') }}",
            "{{ obj.tags.set([]) }}",
            "{{ obj.tags.add('jinja-sandbox-write-injected') }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

        # The rendered object's data must be untouched by the render.
        self.assertEqual(set(location.tags.values_list("name", flat=True)), baseline_tag_names)
        self.assertFalse(extras_models.Tag.objects.filter(name="jinja-sandbox-write-injected").exists())

    def test_render_allows_dynamic_group_members_object_permission_residual(self):
        """Document that DynamicGroup.members is allowed, and is the accepted object-permission residual."""
        location = dcim_models.Location.objects.first()
        device = dcim_models.Device.objects.first()
        self.assertIsNotNone(device)
        device_ct = ContentType.objects.get_for_model(dcim_models.Device)
        location.status.content_types.add(device_ct)

        device_group = extras_models.DynamicGroup.objects.create(
            name="jinja-sandbox-device-members-probe",
            content_type=device_ct,
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        device_group.add_members([device])

        context = {"obj": location}
        template_code = (
            "{{ obj.status.content_types.filter(app_label='dcim', model='device').first()"
            ".dynamic_groups.get(name='jinja-sandbox-device-members-probe')"
            ".members.values_list('name', flat=True)|list }}"
        )
        try:
            rendered = data.render_jinja2(template_code=template_code, context=context)
        except SecurityError:
            self.fail("DynamicGroup.members should be allowed; this is not a sandbox escape.")
        self.assertIn(device.name, rendered)

    def test_render_blocks_meta_default_manager_unrestricted_manager(self):
        """Assert the `meta` filter cannot hand back an unrestricted manager."""
        context = {"obj": dcim_models.Location.objects.first()}
        for template_code in [
            "{{ (obj | meta('default_manager')).values_list('name', flat=True)|list }}",
            "{{ (obj | meta('base_manager')).values_list('name', flat=True)|list }}",
            "{{ (obj | meta('managers'))|list }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

    def test_render_blocks_meta_managers_map_unrestricted_manager(self):
        """Assert the `meta` filter cannot hand back an unrestricted manager via `_meta.managers_map`."""
        context = {"obj": dcim_models.Location.objects.first()}
        template_code = "{{ (obj | meta('managers_map'))['objects'].values_list('name', flat=True)|list }}"
        with self.assertRaises(SecurityError):
            data.render_jinja2(template_code=template_code, context=context)

    def test_render_blocks_module_and_app_config_traversal(self):
        """Assert a template cannot reach a Python module or an application config object.

        An `AppConfig` is a live handle on an installed app, exposing module objects, a dict of model
        classes and `get_model()`; a module object in turn reaches arbitrary importable code. `_meta`
        exposes an `AppConfig`, and the `meta` filter reads `_meta` in Python rather than through
        `is_safe_attribute`, so both types have to be refused on their own account.
        """
        location = dcim_models.Location.objects.first()
        # Injected directly so each denial is exercised on its own, rather than only through whichever
        # route happens to reach it today.
        context = {
            "obj": location,
            "module": dcim_models,
            "app_config": location._meta.app_config,
        }
        # The `meta` filter raises directly, and traversing or subscripting a blocked value raises too.
        for template_code in [
            "{{ obj | meta('app_config') }}",
            "{{ (obj | meta('app_config')).verbose_name }}",
            "{{ (obj | meta('app_config')).module }}",
            "{{ (obj | meta('app_config')).models_module }}",
            "{{ app_config.models['location'] }}",
            # Traversing onward through a blocked module, which is how the escape reached `django.db.models`.
            "{{ module.devices.models }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)

        # Terminal access to a blocked attribute yields empty output; the object never escapes into the
        # template. These render a module or AppConfig repr (non-empty) before the fix.
        for template_code in [
            "{{ app_config.module }}",
            "{{ app_config.models_module }}",
            # Module-to-module traversal, which no other guard covers: a submodule is not a model class.
            "{{ module.devices }}",
        ]:
            with self.subTest(template_code=template_code):
                self.assertEqual(data.render_jinja2(template_code=template_code, context=context), "")

    def test_render_blocks_caller_supplied_sql_expressions(self):
        """Assert a query expression carrying SQL the template author wrote is refused (GHSA-9fgc-m542-2g84).

        `annotate()` and friends are allowed in templates for composed aggregates, and the argument
        check covers positional field names only, so an expression passed by keyword is otherwise
        evaluated with the application database connection's authority.

        The refusal is on the expression's shape, not its class: Django lets a caller supply the SQL
        format string on many expressions through unrecognized constructor keywords, which `Func` and
        its subclasses, `Case` and `Subquery` all interpolate when generating SQL.
        """
        location = dcim_models.Location.objects.first()
        # Injected directly, for the same reason as the traversal test above: the sink must refuse
        # regardless of whether the attribute policy currently lets a template reach the class.
        context = {
            "obj": location,
            "RawSQL": RawSQL,
            "Coalesce": Coalesce,
            "IntegerField": IntegerField,
            "Count": Count,
            "Sum": Sum,
            "Case": Case,
            "When": When,
            "Value": Value,
            "Subquery": Subquery,
        }
        for template_code in [
            # An expression built from a SQL string outright, constructed at all.
            "{{ RawSQL('(SELECT 1)', []) }}",
            # Passed by keyword, which the positional-argument check does not see.
            "{{ obj.tags.all().annotate(x=RawSQL('(SELECT 1)', [])).values('x') | list }}",
            "{{ obj.tags.all().alias(x=RawSQL('(SELECT 1)', [])) | list }}",
            "{{ obj.tags.all().order_by(RawSQL('(SELECT 1)', [])) | list }}",
            # Nested one level inside another expression, to pin the recursive walk.
            "{{ obj.tags.all().annotate(x=Coalesce(RawSQL('(SELECT 1)', [], output_field=IntegerField()), 1)).values('x') | list }}",
            # An otherwise-permitted aggregate handed the SQL format string it generates.
            "{{ Count('pk', template='(SELECT 1)') }}",
            "{{ obj.tags.all().annotate(x=Count('pk', template='(SELECT 1)')).values('x') | list }}",
            "{{ obj.tags.all().annotate(x=Sum('pk', function='(SELECT 1) -- ')).values('x') | list }}",
            "{{ obj.tags.all().annotate(x=Count('pk', arg_joiner='), (')).values('x') | list }}",
            # The same keyword on the other expression families that interpolate it.
            "{{ obj.tags.all().annotate(x=Case(When(name='zz', then=Value(1)), default=Value(2), template='(SELECT 1)')).values('x') | list }}",
            "{{ obj.tags.all().annotate(x=Subquery(obj.tags.all().values('pk')[:1], template='(SELECT 1)')).values('x') | list }}",
            # Carried in as a filter value rather than a projection.
            "{{ obj.tags.all().filter(pk__in=obj.tags.all().annotate(y=Count('pk', template='(SELECT 1)')).values('y')) | list }}",
        ]:
            with self.subTest(template_code=template_code):
                with self.assertRaises(SecurityError):
                    data.render_jinja2(template_code=template_code, context=context)


class RenderJinja2ForRegexTest(TestCase):
    """Tests for rendering a Jinja2 template whose output is used as a regular expression."""

    def test_interpolated_metacharacters_are_escaped(self):
        rendered = data.render_jinja2_for_regex("^{{ v }}$", {"v": "a.b"})
        self.assertEqual(rendered, r"^a\.b$")

    def test_literal_template_text_is_not_escaped(self):
        """The template author keeps full control of the pattern's own syntax."""
        self.assertEqual(data.render_jinja2_for_regex("^[a-z]+$", {}), "^[a-z]+$")

    def test_interpolated_value_cannot_change_the_pattern_structure(self):
        """A value of `.*` must become a literal, not a wildcard that defeats the rule."""
        rendered = data.render_jinja2_for_regex("^{{ v }}$", {"v": ".*"})
        self.assertEqual(rendered, r"^\.\*$")
        self.assertIsNone(regex.match(rendered, "anything else"))

    def test_interpolated_value_is_not_html_escaped(self):
        rendered = data.render_jinja2_for_regex("^{{ v }}$", {"v": "a&b"})
        self.assertIsNotNone(regex.match(rendered, "a&b"))

    def test_escaping_applies_through_filters_and_safe(self):
        for template_code, expected in [
            ("{{ v|safe }}", r"a\.b"),
            ("{{ v|upper }}", r"A\.B"),
            ("{% set x = v %}{{ x }}", r"a\.b"),
        ]:
            with self.subTest(template_code=template_code):
                self.assertEqual(data.render_jinja2_for_regex(template_code, {"v": "a.b"}), expected)

    def test_non_string_values_are_coerced(self):
        self.assertEqual(data.render_jinja2_for_regex("{{ v }}", {"v": 42}), "42")

    def test_undefined_variables_render_empty(self):
        self.assertEqual(data.render_jinja2_for_regex("{{ nope }}", {}), "")

    def test_context_is_passed_through_to_the_template(self):
        """Regression guard: a mis-wired context would silently render every variable empty."""
        location = dcim_models.Location.objects.first()
        self.assertEqual(data.render_jinja2_for_regex("{{ obj.name }}", {"obj": location}), regex.escape(location.name))

    def test_rendering_is_still_sandboxed(self):
        with self.assertRaises(SecurityError):
            data.render_jinja2_for_regex("{{ ''.__class__.__name__ }}", {})

    def test_registered_filters_are_still_available(self):
        self.assertEqual(data.render_jinja2_for_regex("{{ v|upper }}", {"v": "abc"}), "ABC")

    def test_standard_rendering_is_unaffected(self):
        """The regex environment is an overlay; it must not change `render_jinja2()`."""
        self.assertEqual(data.render_jinja2("{{ v }}", {"v": "a&b"}), "a&amp;b")
