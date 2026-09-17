import types

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.db.models import Count
from django.test import override_settings, TestCase
from jinja2.exceptions import SecurityError, TemplateAssertionError
from netutils.utils import jinja2_convenience_function

from nautobot.core.exceptions import SensitiveFieldError
from nautobot.core.templating import NautobotSandboxedContext, NautobotSandboxedEnvironment
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
        context = {"obj": location, "Count": Count}
        for template_code in [
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
