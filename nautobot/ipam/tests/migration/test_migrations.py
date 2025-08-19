import uuid

from django_test_migrations.contrib.unittest_case import MigratorTestCase
import netaddr

from nautobot.core.models.utils import serialize_object
from nautobot.extras import choices as extras_choices
from nautobot.ipam.utils.testing import create_prefixes_and_ips


class AggregateToPrefixMigrationTestCase(MigratorTestCase):
    """Test data migrations removing the Aggregate model and replacing with Prefix in v2.0"""

    migrate_from = ("ipam", "0021_prefix_add_rir_and_date_allocated")
    migrate_to = ("ipam", "0022_aggregate_to_prefix_data_migration")

    def _create_objectchange(self, instance, change_context_detail):
        ContentType = self.old_state.apps.get_model("contenttypes", "contenttype")
        ObjectChange = self.old_state.apps.get_model("extras", "objectchange")

        instance.refresh_from_db()
        return ObjectChange.objects.create(
            action=extras_choices.ObjectChangeActionChoices.ACTION_UPDATE,
            change_context=extras_choices.ObjectChangeEventContextChoices.CONTEXT_ORM,
            change_context_detail=change_context_detail,
            changed_object_id=instance.pk,
            changed_object_type=ContentType.objects.get_for_model(instance.__class__),
            object_data=serialize_object(instance),
            object_repr="",
            request_id=uuid.uuid4(),
        )

    def prepare(self):
        """Populate Aggregate data before migrating to Prefixes"""

        Aggregate = self.old_state.apps.get_model("ipam", "Aggregate")
        ContentType = self.old_state.apps.get_model("contenttypes", "ContentType")
        CustomField = self.old_state.apps.get_model("extras", "customfield")
        Note = self.old_state.apps.get_model("extras", "note")
        ObjectPermission = self.old_state.apps.get_model("users", "objectpermission")
        Prefix = self.old_state.apps.get_model("ipam", "prefix")
        RIR = self.old_state.apps.get_model("ipam", "RIR")
        Status = self.old_state.apps.get_model("extras", "status")
        Tag = self.old_state.apps.get_model("extras", "tag")
        TaggedItem = self.old_state.apps.get_model("extras", "TaggedItem")

        self.aggregate_ct = ContentType.objects.get_for_model(Aggregate)
        self.prefix_ct = ContentType.objects.get_for_model(Prefix)

        self.prefix_status, _ = Status.objects.get_or_create(name="Active")
        self.prefix_status.content_types.add(self.prefix_ct)

        self.rir1 = RIR.objects.create(name="RFC1918", is_private=True)
        self.rir2 = RIR.objects.create(name="ARIN")

        # Create 4 prefixes that will be merged into by Aggregates with duplicate network/prefix_length
        self.prefix1 = Prefix.objects.create(
            network="10.1.0.0",
            broadcast="10.1.0.255",
            prefix_length=24,
            status=self.prefix_status,
            description="PrefixDesc",
        )
        self.prefix2 = Prefix.objects.create(
            network="10.2.0.0",
            broadcast="10.2.0.127",
            prefix_length=25,
            status=self.prefix_status,
            description="PrefixDesc",
        )
        self.prefix3 = Prefix.objects.create(
            network="10.3.0.0", broadcast="10.3.0.63", prefix_length=26, status=self.prefix_status
        )
        self.prefix4 = Prefix.objects.create(
            network="10.4.0.0", broadcast="10.4.0.31", prefix_length=27, status=self.prefix_status
        )
        self.aggregate1 = Aggregate.objects.create(
            network="10.1.0.0", broadcast="10.1.0.255", rir=self.rir1, prefix_length=24
        )
        self.aggregate2 = Aggregate.objects.create(
            network="10.2.0.0", broadcast="10.2.0.127", rir=self.rir1, prefix_length=25
        )
        self.aggregate3 = Aggregate.objects.create(
            network="10.3.0.0", broadcast="10.3.0.63", rir=self.rir1, prefix_length=26, description="AggregateDesc"
        )
        self.aggregate4 = Aggregate.objects.create(
            network="10.4.0.0", broadcast="10.4.0.31", rir=self.rir1, prefix_length=27, description="AggregateDesc"
        )

        # Create 8 prefixes that are not duplicated by Aggregates and will not be touched by migration
        # self.prefix5(10.5.0.0)
        # ...
        # self.prefix12(10.12.0.0)
        for i in range(8):
            prefix = Prefix.objects.create(
                network=f"10.{i + 5}.0.0", broadcast=f"10.{i + 5}.0.15", prefix_length=28, status=self.prefix_status
            )
            setattr(self, f"prefix{i + 5}", prefix)

        # Create 16 aggregates that will be migrated to new Prefixes
        # self.aggregate5(8.5.0.0)
        # ...
        # self.aggregate20(8.20.0.0)
        for i in range(16):
            aggregate = Aggregate.objects.create(
                network=f"8.{i + 5}.0.0",
                broadcast=f"8.{i + 5}.0.7",
                rir=self.rir2,
                prefix_length=29,
                description="AggregateDesc",
            )
            setattr(self, f"aggregate{i + 5}", aggregate)

        # tags
        self.prefix_tag_a = Tag.objects.create(name="PrefixTagA", slug="prefixtaga")
        self.prefix_tag_b = Tag.objects.create(name="PrefixTagB", slug="prefixtagb")
        self.prefix_tag_a.content_types.add(self.prefix_ct)
        self.prefix_tag_b.content_types.add(self.prefix_ct)
        self.aggregate_tag_a = Tag.objects.create(name="AggregateTagA", slug="aggregatetaga")
        self.aggregate_tag_b = Tag.objects.create(name="AggregateTagB", slug="aggregatetagb")
        self.aggregate_tag_a.content_types.add(self.aggregate_ct)
        self.aggregate_tag_b.content_types.add(self.aggregate_ct)
        TaggedItem.objects.create(tag=self.prefix_tag_a, content_type=self.prefix_ct, object_id=self.prefix1.id)
        TaggedItem.objects.create(tag=self.prefix_tag_a, content_type=self.prefix_ct, object_id=self.prefix2.id)
        TaggedItem.objects.create(tag=self.prefix_tag_a, content_type=self.prefix_ct, object_id=self.prefix3.id)
        TaggedItem.objects.create(tag=self.prefix_tag_a, content_type=self.prefix_ct, object_id=self.prefix4.id)
        TaggedItem.objects.create(
            tag=self.aggregate_tag_a, content_type=self.aggregate_ct, object_id=self.aggregate1.id
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_b, content_type=self.aggregate_ct, object_id=self.aggregate1.id
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_a, content_type=self.aggregate_ct, object_id=self.aggregate2.id
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_b, content_type=self.aggregate_ct, object_id=self.aggregate3.id
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_a,
            content_type=self.aggregate_ct,
            object_id=self.aggregate5.id,  # pylint: disable=no-member
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_b,
            content_type=self.aggregate_ct,
            object_id=self.aggregate5.id,  # pylint: disable=no-member
        )
        TaggedItem.objects.create(
            tag=self.aggregate_tag_b,
            content_type=self.aggregate_ct,
            object_id=self.aggregate6.id,  # pylint: disable=no-member
        )

        # notes
        Note.objects.create(
            note="Prefix1 test note",
            assigned_object_type=self.prefix_ct,
            assigned_object_id=self.prefix1.id,
        )
        Note.objects.create(
            note="Prefix2 test note",
            assigned_object_type=self.prefix_ct,
            assigned_object_id=self.prefix2.id,
        )
        Note.objects.create(
            note="Aggregate1 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate1.id,
        )
        Note.objects.create(
            note="Aggregate3 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate3.id,
        )
        Note.objects.create(
            note="Aggregate5 test note",
            assigned_object_type=self.aggregate_ct,
            assigned_object_id=self.aggregate5.id,  # pylint: disable=no-member
        )

        # object permissions
        object_permission1 = ObjectPermission.objects.create(
            name="Aggregate permission 1", actions=["view", "add", "change", "delete"]
        )
        object_permission2 = ObjectPermission.objects.create(
            name="Aggregate permission 2", actions=["add", "delete"], enabled=False
        )
        object_permission1.object_types.add(self.aggregate_ct)
        object_permission2.object_types.add(self.aggregate_ct)

        # object changes
        self._create_objectchange(self.prefix1, "Pre-migration object change for prefix1")
        self._create_objectchange(self.prefix4, "Pre-migration object change for prefix4")
        self._create_objectchange(self.prefix5, "Pre-migration object change for prefix5")  # pylint: disable=no-member
        self._create_objectchange(self.aggregate5, "Pre-migration object change for aggregate5")  # pylint: disable=no-member

        # custom fields
        prefix_cf1 = CustomField.objects.create(name="prefixcf1", slug="prefixcf1")
        prefix_cf1.content_types.add(self.prefix_ct)
        aggregate_cf1 = CustomField.objects.create(name="aggregatecf1", slug="aggregatecf1")
        aggregate_cf1.content_types.add(self.aggregate_ct)
        prefixaggregate_cf1 = CustomField.objects.create(name="prefixaggregatecf1", slug="prefixaggregatecf1")
        prefixaggregate_cf1.content_types.add(self.aggregate_ct, self.prefix_ct)

        self.prefix1._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix1"
        self.prefix1._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix1"
        self.aggregate1._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate1"

        self.prefix2._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix2"
        self.prefix2._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix2"
        self.aggregate2._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate2"
        self.aggregate2._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate2"

        self.aggregate3._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate3"

        self.prefix5._custom_field_data["prefixcf1"] = "testdata prefixcf1 prefix5"  # pylint: disable=no-member
        self.prefix5._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 prefix5"  # pylint: disable=no-member

        self.aggregate5._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate5"  # pylint: disable=no-member
        self.aggregate5._custom_field_data["aggregatecf1"] = "testdata aggregatecf1 aggregate5"  # pylint: disable=no-member

        self.aggregate6._custom_field_data["prefixaggregatecf1"] = "testdata prefixaggregatecf1 aggregate6"  # pylint: disable=no-member

        self.prefix1.save()
        self.prefix2.save()
        self.prefix3.save()
        self.prefix4.save()
        self.prefix5.save()  # pylint: disable=no-member
        self.aggregate1.save()
        self.aggregate2.save()
        self.aggregate3.save()
        self.aggregate5.save()  # pylint: disable=no-member
        self.aggregate6.save()  # pylint: disable=no-member

    def test_validate_data(self):
        Aggregate = self.new_state.apps.get_model("ipam", "Aggregate")
        ContentType = self.new_state.apps.get_model("contenttypes", "ContentType")
        CustomField = self.new_state.apps.get_model("extras", "customfield")
        Note = self.new_state.apps.get_model("extras", "Note")
        ObjectChange = self.new_state.apps.get_model("extras", "objectchange")
        ObjectPermission = self.new_state.apps.get_model("users", "objectpermission")
        Prefix = self.new_state.apps.get_model("ipam", "Prefix")
        Tag = self.new_state.apps.get_model("extras", "Tag")
        TaggedItem = self.new_state.apps.get_model("extras", "TaggedItem")

        prefix_ct = ContentType.objects.get_for_model(Prefix)

        with self.subTest("object count"):
            with self.subTest("Test Prefix count"):
                self.assertEqual(Prefix.objects.count(), 28)
            with self.subTest("Test Aggregate count"):
                self.assertEqual(Aggregate.objects.count(), 20)

        with self.subTest("network"):
            for i in range(16):
                self.assertTrue(
                    Prefix.objects.filter(network=f"8.{i + 5}.0.0", prefix_length=29, rir_id=self.rir2.id).exists()
                )

        with self.subTest("rir"):
            with self.subTest(f"prefix.rir = {self.rir1.name}"):
                self.assertEqual(Prefix.objects.get(network="10.1.0.0").rir_id, self.rir1.id)
                self.assertEqual(Prefix.objects.get(network="10.2.0.0").rir_id, self.rir1.id)
                self.assertEqual(Prefix.objects.get(network="10.3.0.0").rir_id, self.rir1.id)
                self.assertEqual(Prefix.objects.get(network="10.4.0.0").rir_id, self.rir1.id)
            with self.subTest(f"prefix.rir = {self.rir2.name}"):
                for i in range(16):
                    prefix = Prefix.objects.get(network=f"8.{i + 5}.0.0")
                    self.assertEqual(prefix.rir_id, self.rir2.id)
            with self.subTest("prefix.rir is None"):
                for i in range(8):
                    prefix = Prefix.objects.get(network=f"10.{i + 5}.0.0")
                    self.assertIsNone(prefix.rir_id)

        with self.subTest("description"):
            self.assertEqual(Prefix.objects.filter(description="PrefixDesc").count(), 2)
            self.assertEqual(Prefix.objects.filter(description="").count(), 10)
            self.assertEqual(Prefix.objects.filter(description="AggregateDesc").count(), 16)

        with self.subTest("status"):
            self.assertEqual(Prefix.objects.filter(status__name="Active").count(), Prefix.objects.count())

        with self.subTest("tags"):
            with self.subTest("Prefix content type was added to Aggregate Tags"):
                prefix_tags = Tag.objects.filter(content_types=ContentType.objects.get_for_model(Prefix)).values_list(
                    "name", flat=True
                )
                self.assertIn("AggregateTagA", prefix_tags)
                self.assertIn("AggregateTagB", prefix_tags)

            # assert that tags were migrated to new prefix instances
            # compare list of PKs since tag managers don't work in migrations
            prefix = Prefix.objects.get(network="10.1.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA", "AggregateTagB"]).values_list(
                    "id", flat=True
                ),
            )
            prefix = Prefix.objects.get(network="10.2.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA"]).values_list("id", flat=True),
            )
            prefix = Prefix.objects.get(network="10.3.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name__in=["PrefixTagA", "AggregateTagB"]).values_list("id", flat=True),
            )
            prefix = Prefix.objects.get(network="10.4.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name="PrefixTagA").values_list("id", flat=True),
            )
            prefix = Prefix.objects.get(network="8.5.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name__in=["AggregateTagA", "AggregateTagB"]).values_list("id", flat=True),
            )
            prefix = Prefix.objects.get(network="8.6.0.0")
            self.assertCountEqual(
                TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list("tag_id", flat=True),
                Tag.objects.filter(name="AggregateTagB").values_list("id", flat=True),
            )
            for i in range(7, 21):
                prefix = Prefix.objects.get(network=f"8.{i}.0.0")
                self.assertCountEqual(
                    TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix.id).values_list(
                        "tag_id", flat=True
                    ),
                    [],
                )

        with self.subTest("notes"):
            # no notes are assigned to aggregates
            self.assertQuerysetEqual(
                Note.objects.filter(assigned_object_type=ContentType.objects.get_for_model(Aggregate)),
                Note.objects.none(),
            )
            # no extra notes were created
            self.assertEqual(Note.objects.count(), 5)

            # aggregate1 note added on top of existing note on prefix1
            self.assertQuerysetEqual(
                Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=self.prefix1.id),
                Note.objects.filter(note__in=["Prefix1 test note", "Aggregate1 test note"]),
            )

            # prefix2 note was unchanged
            self.assertQuerysetEqual(
                Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=self.prefix2.id),
                Note.objects.filter(note="Prefix2 test note"),
            )

            # aggregate3 note was migrated to prefix3
            self.assertQuerysetEqual(
                Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=self.prefix3.id),
                Note.objects.filter(note="Aggregate3 test note"),
            )

            # no notes for prefix4
            self.assertQuerysetEqual(
                Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=self.prefix4.id),
                Note.objects.none(),
            )

            # aggregate5 note was migrated to new prefix object
            aggregate5_migrated_prefix = Prefix.objects.get(network="8.5.0.0")
            self.assertQuerysetEqual(
                Note.objects.filter(
                    assigned_object_type=prefix_ct,
                    assigned_object_id=aggregate5_migrated_prefix.id,
                ),
                Note.objects.filter(note="Aggregate5 test note"),
            )

            # no other notes are related to remaining prefixes
            for i in range(5, 13):
                prefix = Prefix.objects.get(network=f"10.{i}.0.0")
                self.assertQuerysetEqual(
                    Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=prefix.id),
                    Note.objects.none(),
                )
            for i in range(6, 21):
                prefix = Prefix.objects.get(network=f"8.{i}.0.0")
                self.assertQuerysetEqual(
                    Note.objects.filter(assigned_object_type=prefix_ct, assigned_object_id=prefix.id),
                    Note.objects.none(),
                )

        with self.subTest("permissions"):
            self.assertEqual(ObjectPermission.objects.count(), 2)

            # assert prefix content type was added to object permission 1
            object_permission1 = ObjectPermission.objects.filter(
                name="Aggregate permission 1", actions=["view", "add", "change", "delete"]
            )
            self.assertTrue(object_permission1.exists())
            self.assertTrue(object_permission1.first().object_types.filter(id=prefix_ct.id).exists())

            # assert prefix content type was added to object permission 2
            object_permission2 = ObjectPermission.objects.filter(
                name="Aggregate permission 2", actions=["add", "delete"], enabled=False
            )
            self.assertTrue(object_permission2.exists())
            self.assertTrue(object_permission2.first().object_types.filter(id=prefix_ct.id).exists())

        with self.subTest("object changes"):
            self.assertEqual(
                ObjectChange.objects.filter(changed_object_type=ContentType.objects.get_for_model(Prefix)).count(), 24
            )
            self.assertEqual(
                ObjectChange.objects.filter(changed_object_type=ContentType.objects.get_for_model(Aggregate)).count(), 0
            )

            for prefix in (self.prefix1, self.prefix4, Prefix.objects.get(network="8.5.0.0")):
                self.assertEqual(
                    ObjectChange.objects.filter(changed_object_id=prefix.id).count(),
                    2,
                )

            for prefix in (self.prefix2, self.prefix3, self.prefix5):  # pylint: disable=no-member
                self.assertEqual(
                    ObjectChange.objects.filter(changed_object_id=prefix.id).count(),
                    1,
                )

            for i in range(6, 13):
                prefix = Prefix.objects.get(network=f"10.{i}.0.0")
                self.assertEqual(
                    ObjectChange.objects.filter(changed_object_id=prefix.id).count(),
                    0,
                )

            for i in range(6, 21):
                prefix = Prefix.objects.get(network=f"8.{i}.0.0")
                self.assertEqual(
                    ObjectChange.objects.filter(changed_object_id=prefix.id).count(),
                    1,
                )

        with self.subTest("custom fields"):
            # This change is necessary because name attribute is not specified now in example_app's signal.py
            self.assertEqual(CustomField.objects.exclude(name="").count(), 3)
            self.assertEqual(
                CustomField.objects.filter(content_types=ContentType.objects.get_for_model(Prefix)).count(), 3
            )
            self.assertEqual(
                CustomField.objects.filter(content_types=ContentType.objects.get_for_model(Aggregate)).count(), 2
            )

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
                    prefix = Prefix.objects.get(network=f"10.{i}.0.0")
                    self.assertDictEqual(prefix._custom_field_data, expected[f"prefix{i}"])

            with self.subTest("Custom fields for prefix 8.5.0.0"):
                expected = {
                    "prefixaggregatecf1": "testdata prefixaggregatecf1 aggregate5",
                    "aggregatecf1": "testdata aggregatecf1 aggregate5",
                }
                prefix = Prefix.objects.get(network="8.5.0.0")
                self.assertDictEqual(prefix._custom_field_data, expected)

            with self.subTest("Custom fields for prefix 8.6.0.0"):
                expected = {
                    "prefixaggregatecf1": "testdata prefixaggregatecf1 aggregate6",
                }
                prefix = Prefix.objects.get(network="8.6.0.0")
                self.assertDictEqual(prefix._custom_field_data, expected)


class IPAMDataMigration0031TestCase(MigratorTestCase):
    migrate_from = ("ipam", "0030_ipam__namespaces")
    migrate_to = ("ipam", "0032_ipam__namespaces_finish")

    def prepare(self):
        # Create an arbitrary set of prefixes and IPs mostly subdividing and consuming the given subnet, including dupes
        create_prefixes_and_ips("10.0.0.0/14", apps=self.old_state.apps)

    def test_validate_data(self):
        IPAddress = self.new_state.apps.get_model("ipam", "IPAddress")

        with self.subTest("Verify that all IPAddresses now have a valid parent"):
            self.assertQuerysetEqual(IPAddress.objects.filter(parent__isnull=True), IPAddress.objects.none())
            for ip in IPAddress.objects.iterator():
                self.assertLessEqual(netaddr.IPAddress(ip.parent.network), netaddr.IPAddress(ip.host))
                self.assertGreaterEqual(netaddr.IPAddress(ip.parent.broadcast), netaddr.IPAddress(ip.host))
