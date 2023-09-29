import uuid

from unittest import skip, skipIf

from django.db import connection

from nautobot.core.models.fields import TagsField
from nautobot.core.models.utils import serialize_object
from nautobot.core.testing.migrations import NautobotDataMigrationTest
from nautobot.extras import choices as extras_choices


@skip("test skipped until base test can be fixed to handle new migrations")
class AggregateToPrefixMigrationTestCase(NautobotDataMigrationTest):
    """Test data migrations removing the Aggregate model and replacing with Prefix in v2.0"""

    migrate_from = [("ipam", "0021_prefix_add_rir_and_date_allocated")]
    migrate_to = [("ipam", "0022_aggregate_to_prefix_data_migration")]

    def _create_objectchange(self, instance, change_context_detail):
        instance.refresh_from_db()
        return self.object_change.objects.create(
            action=extras_choices.ObjectChangeActionChoices.ACTION_UPDATE,
            change_context=extras_choices.ObjectChangeEventContextChoices.CONTEXT_ORM,
            change_context_detail=change_context_detail,
            changed_object_id=instance.pk,
            changed_object_type=self.content_type.objects.get_for_model(instance.__class__),
            object_data=serialize_object(instance),
            object_repr="",
            request_id=uuid.uuid4(),
        )

    def populateDataBeforeMigration(self, apps):
        """Populate Aggregate data before migrating to Prefixes"""

        self.aggregate = apps.get_model("ipam", "Aggregate")
        # Workaround for django-taggit manager not working in migrations.
        # https://github.com/jazzband/django-taggit/issues/101
        # https://github.com/jazzband/django-taggit/issues/454
        self.aggregate.tags = TagsField()
        self.computed_field = apps.get_model("extras", "computedfield")
        self.content_type = apps.get_model("contenttypes", "ContentType")
        self.custom_field = apps.get_model("extras", "customfield")
        self.custom_link = apps.get_model("extras", "customlink")
        self.dynamic_group = apps.get_model("extras", "DynamicGroup")
        self.note = apps.get_model("extras", "note")
        self.object_change = apps.get_model("extras", "objectchange")
        self.object_permission = apps.get_model("users", "objectpermission")
        self.prefix = apps.get_model("ipam", "prefix")
        self.prefix.tags = TagsField()
        self.relationship = apps.get_model("extras", "relationship")
        self.relationship_association = apps.get_model("extras", "relationshipassociation")
        self.rir = apps.get_model("ipam", "RIR")
        self.status = apps.get_model("extras", "status")
        self.tag = apps.get_model("extras", "tag")

        self.aggregate_ct = self.content_type.objects.get_for_model(self.aggregate)
        self.prefix_ct = self.content_type.objects.get_for_model(self.prefix)

        self.prefix_status = self.status.objects.create(name="Active")
        self.prefix_status.content_types.add(self.prefix_ct)

        self.rir1 = self.rir.objects.create(name="RFC1918", is_private=True)
        self.rir2 = self.rir.objects.create(name="ARIN")

        # Create 4 prefixes that will be merged into by Aggregates with duplicate network/prefix_length
        self.prefix1 = self.prefix.objects.create(
            network="10.1.0.0", prefix_length=24, status=self.prefix_status, description="PrefixDesc"
        )
        self.prefix2 = self.prefix.objects.create(
            network="10.2.0.0", prefix_length=25, status=self.prefix_status, description="PrefixDesc"
        )
        self.prefix3 = self.prefix.objects.create(network="10.3.0.0", prefix_length=26, status=self.prefix_status)
        self.prefix4 = self.prefix.objects.create(network="10.4.0.0", prefix_length=27, status=self.prefix_status)
        self.aggregate1 = self.aggregate.objects.create(network="10.1.0.0", rir=self.rir1, prefix_length=24)
        self.aggregate2 = self.aggregate.objects.create(network="10.2.0.0", rir=self.rir1, prefix_length=25)
        self.aggregate3 = self.aggregate.objects.create(
            network="10.3.0.0", rir=self.rir1, prefix_length=26, description="AggregateDesc"
        )
        self.aggregate4 = self.aggregate.objects.create(
            network="10.4.0.0", rir=self.rir1, prefix_length=27, description="AggregateDesc"
        )

        # Create 8 prefixes that are not duplicated by Aggregates and will not be touched by migration
        # self.prefix5(10.5.0.0)
        # ...
        # self.prefix12(10.12.0.0)
        for i in range(8):
            prefix = self.prefix.objects.create(network=f"10.{i+5}.0.0", prefix_length=28, status=self.prefix_status)
            setattr(self, f"prefix{i+5}", prefix)

        # Create 16 aggregates that will be migrated to new Prefixes
        # self.aggregate5(8.5.0.0)
        # ...
        # self.aggregate20(8.20.0.0)
        for i in range(16):
            aggregate = self.aggregate.objects.create(
                network=f"8.{i+5}.0.0", rir=self.rir2, prefix_length=29, description="AggregateDesc"
            )
            setattr(self, f"aggregate{i+5}", aggregate)

        # tags
        self.prefix_tag_a = self.tag.objects.create(name="PrefixTagA")
        self.prefix_tag_b = self.tag.objects.create(name="PrefixTagB")
        self.prefix_tag_a.content_types.add(self.prefix_ct)
        self.prefix_tag_b.content_types.add(self.prefix_ct)
        self.aggregate_tag_a = self.tag.objects.create(name="AggregateTagA")
        self.aggregate_tag_b = self.tag.objects.create(name="AggregateTagB")
        self.aggregate_tag_a.content_types.add(self.aggregate_ct)
        self.aggregate_tag_b.content_types.add(self.aggregate_ct)
        self.prefix1.tags.add("PrefixTagA")
        self.prefix2.tags.add("PrefixTagA")
        self.prefix3.tags.add("PrefixTagA")
        self.prefix4.tags.add("PrefixTagA")
        self.aggregate1.tags.add("AggregateTagA", "AggregateTagB")
        self.aggregate2.tags.add("AggregateTagA")
        self.aggregate3.tags.add("AggregateTagB")
        self.aggregate5.tags.add("AggregateTagA", "AggregateTagB")
        self.aggregate6.tags.add("AggregateTagB")

        # notes
        self.note.objects.create(
            note="Prefix1 test note",
            assigned_object_type=self.prefix_ct,
            assigned_object_id=self.prefix1.id,
        )
        self.note.objects.create(
            note="Prefix2 test note",
            assigned_object_type=self.prefix_ct,
            assigned_object_id=self.prefix2.id,
        )
        self.note.objects.create(
            note="Aggregate1 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate1.id,
        )
        self.note.objects.create(
            note="Aggregate3 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate3.id,
        )
        self.note.objects.create(
            note="Aggregate5 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate5.id,
        )

        # object permissions
        object_permission1 = self.object_permission.objects.create(
            name="Aggregate permission 1", actions=["view", "add", "change", "delete"]
        )
        object_permission2 = self.object_permission.objects.create(
            name="Aggregate permission 2", actions=["add", "delete"], enabled=False
        )
        object_permission1.object_types.add(self.aggregate_ct)
        object_permission2.object_types.add(self.aggregate_ct)

        # object changes
        self._create_objectchange(self.prefix1, "Pre-migration object change for prefix1")
        self._create_objectchange(self.prefix4, "Pre-migration object change for prefix4")
        self._create_objectchange(self.prefix5, "Pre-migration object change for prefix5")
        self._create_objectchange(self.aggregate5, "Pre-migration object change for aggregate5")

        # custom fields
        prefix_cf1 = self.custom_field.objects.create(name="prefixcf1")
        prefix_cf1.content_types.add(self.prefix_ct)
        aggregate_cf1 = self.custom_field.objects.create(name="aggregatecf1")
        aggregate_cf1.content_types.add(self.aggregate_ct)
        prefixaggregate_cf1 = self.custom_field.objects.create(name="prefixaggregatecf1")
        prefixaggregate_cf1.content_types.add(self.aggregate_ct, self.prefix_ct)

        self.prefix1._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix1"
        self.prefix1._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix1"
        self.aggregate1._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate1"

        self.prefix2._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix2"
        self.prefix2._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix2"
        self.aggregate2._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate2"
        self.aggregate2._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate2"

        self.aggregate3._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate3"

        self.prefix5._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix5"
        self.prefix5._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix5"

        self.aggregate5._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate5"
        self.aggregate5._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate5"

        self.aggregate6._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate6"

        self.prefix1.save()
        self.prefix2.save()
        self.prefix3.save()
        self.prefix4.save()
        self.prefix5.save()
        self.aggregate1.save()
        self.aggregate2.save()
        self.aggregate3.save()
        self.aggregate5.save()
        self.aggregate6.save()

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_object_count(self):
        with self.subTest("Test Prefix count"):
            self.assertEqual(self.prefix.objects.count(), 28)
        with self.subTest("Test Aggregate count"):
            self.assertEqual(self.aggregate.objects.count(), 20)

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_network(self):
        for i in range(16):
            self.assertTrue(
                self.prefix.objects.filter(network=f"8.{i+5}.0.0", prefix_length=29, rir=self.rir2).exists()
            )

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_rir(self):
        with self.subTest(f"prefix.rir = {self.rir1.name}"):
            self.assertEqual(self.prefix.objects.get(network="10.1.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="10.2.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="10.3.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="10.4.0.0").rir, self.rir1)
        with self.subTest(f"prefix.rir = {self.rir2.name}"):
            for i in range(16):
                prefix = self.prefix.objects.get(network=f"8.{i+5}.0.0")
                self.assertEqual(prefix.rir, self.rir2)
        with self.subTest("prefix.rir is None"):
            for i in range(8):
                prefix = self.prefix.objects.get(network=f"10.{i+5}.0.0")
                self.assertIsNone(prefix.rir)

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_description(self):
        self.assertEqual(self.prefix.objects.filter(description="PrefixDesc").count(), 2)
        self.assertEqual(self.prefix.objects.filter(description="").count(), 10)
        self.assertEqual(self.prefix.objects.filter(description="AggregateDesc").count(), 16)

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_status(self):
        self.assertEqual(self.prefix.objects.filter(status=self.prefix_status).count(), self.prefix.objects.count())

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_tags(self):
        with self.subTest("Prefix content type was added to Aggregate Tags"):
            prefix_tags = self.tag.objects.filter(content_types=self.prefix_ct)
            self.assertIn(self.aggregate_tag_a, prefix_tags)
            self.assertIn(self.aggregate_tag_b, prefix_tags)

        # assert that tags were migrated to new prefix instances
        # compare list of PKs since tag managers don't work in migrations
        self.assertCountEqual(
            self.prefix.objects.get(network="10.1.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA", "AggregateTagB"]).values_list(
                "id", flat=True
            ),
        )
        self.assertCountEqual(
            self.prefix.objects.get(network="10.2.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA"]).values_list("id", flat=True),
        )
        self.assertCountEqual(
            self.prefix.objects.get(network="10.3.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagB"]).values_list("id", flat=True),
        )
        self.assertCountEqual(
            self.prefix.objects.get(network="10.4.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name="PrefixTagA").values_list("id", flat=True),
        )
        self.assertCountEqual(
            self.prefix.objects.get(network="8.5.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name__in=["AggregateTagA", "AggregateTagB"]).values_list("id", flat=True),
        )
        self.assertCountEqual(
            self.prefix.objects.get(network="8.6.0.0").tags.values_list("id", flat=True),
            self.tag.objects.filter(name="AggregateTagB").values_list("id", flat=True),
        )
        for i in range(7, 21):
            prefix = self.prefix.objects.get(network=f"8.{i}.0.0")
            self.assertCountEqual(prefix.tags.values_list("id", flat=True), [])

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_notes(self):
        # no notes are assigned to aggregates
        self.assertQuerysetEqual(
            self.note.objects.filter(assigned_object_type=self.aggregate_ct), self.note.objects.none()
        )
        # no extra notes were created
        self.assertEqual(self.note.objects.count(), 5)

        # aggregate1 note added on top of existing note on prefix1
        self.assertQuerysetEqual(
            self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=self.prefix1.id),
            self.note.objects.filter(note__in=["Prefix1 test note", "Aggregate1 test note"]),
        )

        # prefix2 note was unchanged
        self.assertQuerysetEqual(
            self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=self.prefix2.id),
            self.note.objects.filter(note="Prefix2 test note"),
        )

        # aggregate3 note was migrated to prefix3
        self.assertQuerysetEqual(
            self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=self.prefix3.id),
            self.note.objects.filter(note="Aggregate3 test note"),
        )

        # no notes for prefix4
        self.assertQuerysetEqual(
            self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=self.prefix4.id),
            self.note.objects.none(),
        )

        # aggregate5 note was migrated to new prefix object
        aggregate5_migrated_prefix = self.prefix.objects.get(network="8.5.0.0")
        self.assertQuerysetEqual(
            self.note.objects.filter(
                assigned_object_type=self.prefix_ct,
                assigned_object_id=aggregate5_migrated_prefix.id,
            ),
            self.note.objects.filter(note="Aggregate5 test note"),
        )

        # no other notes are related to remaining prefixes
        for i in range(5, 13):
            prefix = self.prefix.objects.get(network=f"10.{i}.0.0")
            self.assertQuerysetEqual(
                self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=prefix.id),
                self.note.objects.none(),
            )
        for i in range(6, 21):
            prefix = self.prefix.objects.get(network=f"8.{i}.0.0")
            self.assertQuerysetEqual(
                self.note.objects.filter(assigned_object_type=self.prefix_ct, assigned_object_id=prefix.id),
                self.note.objects.none(),
            )

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_permissions(self):
        self.assertEqual(self.object_permission.objects.count(), 2)

        # assert prefix content type was added to object permission 1
        object_permission1 = self.object_permission.objects.filter(
            name="Aggregate permission 1", actions=["view", "add", "change", "delete"]
        )
        self.assertTrue(object_permission1.exists())
        self.assertTrue(object_permission1.first().object_types.filter(id=self.prefix_ct.id).exists())

        # assert prefix content type was added to object permission 2
        object_permission2 = self.object_permission.objects.filter(
            name="Aggregate permission 2", actions=["add", "delete"], enabled=False
        )
        self.assertTrue(object_permission2.exists())
        self.assertTrue(object_permission2.first().object_types.filter(id=self.prefix_ct.id).exists())

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_object_changes(self):
        self.assertEqual(self.object_change.objects.filter(changed_object_type=self.prefix_ct).count(), 24)
        self.assertEqual(self.object_change.objects.filter(changed_object_type=self.aggregate_ct).count(), 0)

        for prefix in (self.prefix1, self.prefix4, self.prefix.objects.get(network="8.5.0.0")):
            self.assertEqual(
                self.object_change.objects.filter(changed_object_id=prefix.id).count(),
                2,
            )

        for prefix in (self.prefix2, self.prefix3, self.prefix5):
            self.assertEqual(
                self.object_change.objects.filter(changed_object_id=prefix.id).count(),
                1,
            )

        for i in range(6, 13):
            prefix = self.prefix.objects.get(network=f"10.{i}.0.0")
            self.assertEqual(
                self.object_change.objects.filter(changed_object_id=prefix.id).count(),
                0,
            )

        for i in range(6, 21):
            prefix = self.prefix.objects.get(network=f"8.{i}.0.0")
            self.assertEqual(
                self.object_change.objects.filter(changed_object_id=prefix.id).count(),
                1,
            )

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_custom_fields(self):
        # This change is necessary because name attribute is not specified now in example_plugin's signal.py
        self.assertEqual(self.custom_field.objects.exclude(name="").count(), 3)
        self.assertEqual(self.custom_field.objects.filter(content_types=self.prefix_ct).count(), 3)
        self.assertEqual(self.custom_field.objects.filter(content_types=self.aggregate_ct).count(), 2)

        expected = {
            "prefix1": {
                "prefixcf1": "testdata prefixcf1 prefix1",
                "prefixaggregatecf1": "testdata prefixaggregatecf1 prefix1",
                "aggregatecf1": "testdata aggregatecf1 aggregate1",
            },
            "prefix2": {
                "prefixcf1": "testdata prefixcf1 prefix2",
                "prefixaggregatecf1": "testdata prefixaggregatecf1 prefix2",
                "aggregatecf1": "testdata aggregatecf1 aggregate2",
            },
            "prefix3": {
                "aggregatecf1": "testdata aggregatecf1 aggregate3",
            },
            "prefix4": {},
            "prefix5": {
                "prefixcf1": "testdata prefixcf1 prefix5",
                "prefixaggregatecf1": "testdata prefixaggregatecf1 prefix5",
            },
        }

        for i in range(1, 6):
            with self.subTest(f"Custom fields for prefix{i}"):
                prefix = self.prefix.objects.get(network=f"10.{i}.0.0")
                self.assertDictEqual(prefix._custom_field_data, expected[f"prefix{i}"])

        with self.subTest("Custom fields for prefix 8.5.0.0"):
            expected = {
                "prefixaggregatecf1": "testdata prefixaggregatecf1 aggregate5",
                "aggregatecf1": "testdata aggregatecf1 aggregate5",
            }
            prefix = self.prefix.objects.get(network="8.5.0.0")
            self.assertDictEqual(prefix._custom_field_data, expected)

        with self.subTest("Custom fields for prefix 8.6.0.0"):
            expected = {
                "prefixaggregatecf1": "testdata prefixaggregatecf1 aggregate6",
            }
            prefix = self.prefix.objects.get(network="8.6.0.0")
            self.assertDictEqual(prefix._custom_field_data, expected)
