from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import override_settings

from nautobot.core.testing import TestCase
from nautobot.core.utils.cache import construct_cache_key
from nautobot.data_validation.models import MinMaxValidationRule
from nautobot.dcim.models import Device, Location, Rack
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    MetadataTypeDataTypeChoices,
    RelationshipTypeChoices,
)
from nautobot.extras.models import (
    ComputedField,
    CustomField,
    CustomFieldChoice,
    GitRepository,
    MetadataType,
    Relationship,
)
from nautobot.tenancy.models import TenantGroup


class PersistentCacheTest(TestCase):
    """
    Validate the caches that never expire by default and are instead invalidated when their underlying data changes.

    A request that misses one of these caches while another request is still committing a change reads the old data
    from the database and re-caches it. Once the change commits, that stale entry must be discarded; otherwise, for
    example, the REST API would keep omitting a newly created custom field and silently dropping its values on write
    until the next custom field change.
    """

    def setUp(self):
        super().setUp()
        self.location_ct = ContentType.objects.get_for_model(Location)
        self.select_custom_field = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT, label="Persistent Cache Select Field"
        )
        self.select_custom_field.validated_save()
        self.tenant_group = TenantGroup(name="Persistent Cache Root Group")
        self.tenant_group.validated_save()
        self.counter = 0

    def _next_name(self, prefix):
        self.counter += 1
        return f"{prefix} {self.counter}"

    # Changes to the underlying data of each cache

    def _create_custom_field(self):
        custom_field = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label=self._next_name("Persistent Cache CF"))
        custom_field.validated_save()
        custom_field.content_types.set([self.location_ct])

    def _create_custom_field_choice(self):
        CustomFieldChoice(
            custom_field=self.select_custom_field, value=self._next_name("Persistent Cache Choice")
        ).validated_save()

    def _create_computed_field(self):
        label = self._next_name("Persistent Cache Computed Field")
        ComputedField(
            content_type=self.location_ct,
            key=label.lower().replace(" ", "_"),
            label=label,
            template="{{ obj.name }}",
        ).validated_save()

    def _create_metadata_type(self):
        metadata_type = MetadataType(
            name=self._next_name("Persistent Cache Metadata Type"), data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        metadata_type.validated_save()
        metadata_type.content_types.set([self.location_ct])

    def _create_relationship(self):
        Relationship(
            label=self._next_name("Persistent Cache Relationship"),
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
            source_type=self.location_ct,
            destination_type=ContentType.objects.get_for_model(Rack),
        ).validated_save()

    def _create_reverse_relationship(self):
        Relationship(
            label=self._next_name("Persistent Cache Relationship"),
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
            source_type=ContentType.objects.get_for_model(Rack),
            destination_type=self.location_ct,
        ).validated_save()

    def _create_git_repository(self):
        GitRepository(
            name=self._next_name("Persistent Cache Repository"),
            remote_url="http://localhost/git.git",
            provided_contents=["extras.configcontext"],
        ).validated_save()

    def _create_validation_rule(self):
        # Only one MinMaxValidationRule is allowed per content type and field.
        unused_field = next(
            field
            for field in ("position", "vc_position", "vc_priority")
            if not MinMaxValidationRule.objects.filter(content_type__model="device", field=field).exists()
        )
        MinMaxValidationRule(
            name=self._next_name("Persistent Cache Rule"),
            content_type=ContentType.objects.get_for_model(Device),
            field=unused_field,
            min=1,
        ).validated_save()

    def _deepen_tenant_group_tree(self):
        """Hang a chain of only-children off a new root, one level deeper than the current tree."""
        parent = None
        for _ in range(TenantGroup.objects.max_tree_depth() + 2):
            parent = TenantGroup(name=self._next_name("Persistent Cache Group"), parent=parent)
            parent.validated_save()

    def _create_tenant_group_child(self):
        TenantGroup(name=self._next_name("Persistent Cache Child Group"), parent=self.tenant_group).validated_save()

    # The caches themselves

    def get_cases(self):
        """
        Return one entry per persistent cache.

        Each entry gives the cache `keys` that `read()` populates, a `write()` that changes the cached data (or None if
        the cache is only populated in bulk), and whether the cache follows `PERSISTENT_CACHE_TIMEOUT`.
        """

        def pks(objects):
            return {obj.pk for obj in objects}

        def key(manager_or_instance, method_name, **params):
            return construct_cache_key(manager_or_instance, method_name=method_name, branch_aware=True, **params)

        location = "dcim.location"
        return [
            {
                "name": "CustomField.objects.get_for_model()",
                "keys": [key(CustomField.objects, "get_for_model", model=location, exclude_filter_disabled=False)],
                "read": lambda: pks(CustomField.objects.get_for_model(Location)),
                "write": self._create_custom_field,
                "ttl": True,
            },
            {
                "name": "CustomField.objects.get_for_model(get_queryset=False)",
                "keys": [
                    key(
                        CustomField.objects,
                        "get_for_model",
                        model=location,
                        exclude_filter_disabled=False,
                        listing=True,
                    )
                ],
                "read": lambda: pks(CustomField.objects.get_for_model(Location, get_queryset=False)),
                "write": self._create_custom_field,
                "ttl": True,
            },
            {
                "name": "CustomField.objects.keys_for_model()",
                "keys": [key(CustomField.objects, "keys_for_model", model=location)],
                "read": lambda: set(CustomField.objects.keys_for_model(Location)),
                "write": self._create_custom_field,
                "ttl": True,
            },
            {
                "name": "CustomField.objects.populate_list_caches()",
                "keys": [
                    key(
                        CustomField.objects,
                        "get_for_model",
                        model=location,
                        exclude_filter_disabled=False,
                        listing=True,
                    ),
                    key(CustomField.objects, "keys_for_model", model=location),
                ],
                "read": CustomField.objects.populate_list_caches,
                "write": None,
                "ttl": True,
            },
            {
                "name": "CustomField.choices",
                "keys": [key(self.select_custom_field, "choices")],
                "read": lambda: set(self.select_custom_field.choices),
                "write": self._create_custom_field_choice,
                "ttl": True,
            },
            {
                "name": "ComputedField.objects.get_for_model()",
                "keys": [key(ComputedField.objects, "get_for_model", model=location)],
                "read": lambda: pks(ComputedField.objects.get_for_model(Location)),
                "write": self._create_computed_field,
                "ttl": True,
            },
            {
                "name": "ComputedField.objects.get_for_model(get_queryset=False)",
                "keys": [key(ComputedField.objects, "get_for_model", model=location, listing=True)],
                "read": lambda: pks(ComputedField.objects.get_for_model(Location, get_queryset=False)),
                "write": self._create_computed_field,
                "ttl": True,
            },
            {
                "name": "ComputedField.objects.populate_list_caches()",
                "keys": [key(ComputedField.objects, "get_for_model", model=location, listing=True)],
                "read": ComputedField.objects.populate_list_caches,
                "write": None,
                "ttl": True,
            },
            {
                "name": "MetadataType.objects.get_for_model()",
                "keys": [key(MetadataType.objects, "get_for_model", model=location)],
                "read": lambda: pks(MetadataType.objects.get_for_model(Location)),
                "write": self._create_metadata_type,
                "ttl": True,
            },
            {
                "name": "Relationship.objects.get_for_model_source()",
                "keys": [key(Relationship.objects, "get_for_model_source", model=location, hidden=None)],
                "read": lambda: pks(Relationship.objects.get_for_model_source(Location)),
                "write": self._create_relationship,
                "ttl": True,
            },
            {
                "name": "Relationship.objects.get_for_model_source(get_queryset=False)",
                "keys": [key(Relationship.objects, "get_for_model_source", model=location, hidden=None, listing=True)],
                "read": lambda: pks(Relationship.objects.get_for_model_source(Location, get_queryset=False)),
                "write": self._create_relationship,
                "ttl": True,
            },
            {
                "name": "Relationship.objects.get_for_model_destination()",
                "keys": [key(Relationship.objects, "get_for_model_destination", model=location, hidden=None)],
                "read": lambda: pks(Relationship.objects.get_for_model_destination(Location)),
                "write": self._create_reverse_relationship,
                "ttl": True,
            },
            {
                "name": "Relationship.objects.get_for_model_destination(get_queryset=False)",
                "keys": [
                    key(Relationship.objects, "get_for_model_destination", model=location, hidden=None, listing=True)
                ],
                "read": lambda: pks(Relationship.objects.get_for_model_destination(Location, get_queryset=False)),
                "write": self._create_reverse_relationship,
                "ttl": True,
            },
            {
                "name": "Relationship.objects.populate_list_caches()",
                "keys": [
                    key(Relationship.objects, "get_for_model_source", model=location, hidden=None, listing=True),
                    key(Relationship.objects, "get_for_model_destination", model=location, hidden=None, listing=True),
                ],
                "read": Relationship.objects.populate_list_caches,
                "write": None,
                "ttl": True,
            },
            {
                "name": "GitRepository.objects.get_for_provided_contents()",
                "keys": [
                    key(
                        GitRepository.objects,
                        "get_for_provided_contents",
                        provided_contents_type="extras.configcontext",
                    )
                ],
                "read": lambda: pks(GitRepository.objects.get_for_provided_contents("extras.configcontext")),
                "write": self._create_git_repository,
                "ttl": True,
            },
            {
                "name": "MinMaxValidationRule.objects.get_for_model()",
                "keys": [key(MinMaxValidationRule.objects, "get_for_model", content_type="dcim.device")],
                "read": lambda: pks(MinMaxValidationRule.objects.get_for_model("dcim.device")),
                "write": self._create_validation_rule,
                "ttl": True,
            },
            {
                "name": "MinMaxValidationRule.objects.get_enabled_for_model()",
                "keys": [key(MinMaxValidationRule.objects, "get_enabled_for_model", content_type="dcim.device")],
                "read": lambda: pks(MinMaxValidationRule.objects.get_enabled_for_model("dcim.device")),
                "write": self._create_validation_rule,
                "ttl": True,
            },
            {
                "name": "TreeManager.max_depth",
                "keys": [TenantGroup.objects.max_depth_cache_key],
                "read": lambda: TenantGroup.objects.max_depth,
                "write": self._deepen_tenant_group_tree,
                "ttl": True,
            },
            {
                # Bounded by the default `CACHES` timeout instead, since it is a per-instance cache.
                "name": "TreeModel.cacheable_descendants_pks()",
                "keys": [
                    key(self.tenant_group, "cacheable_descendants_pks", restrict_to_user=None, include_self=False)
                ],
                "read": lambda: set(self.tenant_group.cacheable_descendants_pks()),
                "write": self._create_tenant_group_child,
                "ttl": False,
            },
        ]

    def test_stale_entries_cached_during_a_change_are_discarded_on_commit(self):
        for case in self.get_cases():
            if case["write"] is None:
                continue
            with self.subTest(case["name"]):
                value_before_change = case["read"]()
                stale_entries = {cache_key: cache.get(cache_key) for cache_key in case["keys"]}
                self.assertNotIn(None, stale_entries.values(), "read() did not populate the expected cache keys")

                with self.captureOnCommitCallbacks(execute=True):
                    case["write"]()
                    # A concurrent request that read the database before this transaction commits re-caches old data.
                    cache.set_many(stale_entries)
                    self.assertEqual(case["read"](), value_before_change)

                self.assertNotEqual(case["read"](), value_before_change)

    def test_openapi_schema_entries_cached_during_a_change_are_discarded_on_commit(self):
        schema_cache_key = f"openapi_schema_cache_v1_{settings.VERSION}"
        self.addCleanup(cache.delete, schema_cache_key)

        with self.captureOnCommitCallbacks(execute=True):
            self._create_custom_field()
            # A concurrent request that rendered the schema before this transaction commits re-caches the old schema.
            cache.set(schema_cache_key, "stale schema")

        self.assertIsNone(cache.get(schema_cache_key))

    def test_expiry_follows_persistent_cache_timeout(self):
        for case in self.get_cases():
            if not case["ttl"]:
                continue
            with self.subTest(case["name"], timeout=None):
                cache.delete_many(case["keys"])
                case["read"]()
                for cache_key in case["keys"]:
                    self.assertIsNone(cache.ttl(cache_key), cache_key)

            with self.subTest(case["name"], timeout=60), override_settings(PERSISTENT_CACHE_TIMEOUT=60):
                cache.delete_many(case["keys"])
                case["read"]()
                for cache_key in case["keys"]:
                    self.assertGreater(cache.ttl(cache_key), 0, cache_key)
                    self.assertLessEqual(cache.ttl(cache_key), 60, cache_key)
