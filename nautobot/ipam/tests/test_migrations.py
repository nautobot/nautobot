from unittest import skipIf

from django.db import connection

from nautobot.core.tests.test_migration import NautobotDataMigrationTest
from nautobot.extras.management import populate_status_choices
from nautobot.core.models.generics import _NautobotTaggableManager
from nautobot.extras import models as extras_models


class AggregateToPrefixMigrationTestCase(NautobotDataMigrationTest):
    migrate_from = [("ipam", "0021_prefix_add_rir_and_date_allocated")]
    migrate_to = [("ipam", "0022_aggregate_to_prefix_data_migration")]

    def _add_tags_to_instance(self, model_class, instance, tags):
        """Workaround for django-taggit manager not working in migrations.
        https://github.com/jazzband/django-taggit/issues/101
        https://github.com/jazzband/django-taggit/issues/454
        """
        instance.tags = _NautobotTaggableManager(
            through=extras_models.TaggedItem, model=model_class, instance=instance, prefetch_cache_name="tags"
        )
        for tag in tags:
            instance.tags.add(tag)

    def populateDataBeforeMigration(self, apps):
        """Populate Aggregate data before migrating to Prefixes"""

        self.aggregate = apps.get_model("ipam", "Aggregate")
        self.computed_field = apps.get_model("extras", "computedfield")
        self.content_type = apps.get_model("contenttypes", "ContentType")
        self.custom_field = apps.get_model("extras", "customfield")
        self.custom_link = apps.get_model("extras", "customlink")
        self.dynamic_group = apps.get_model("extras", "DynamicGroup")
        self.note = apps.get_model("extras", "note")
        self.object_change = apps.get_model("extras", "objectchange")
        self.prefix = apps.get_model("ipam", "prefix")
        self.relationship = apps.get_model("extras", "relationship")
        self.relationship_association = apps.get_model("extras", "relationshipassociation")
        self.rir = apps.get_model("ipam", "RIR")
        self.status = apps.get_model("extras", "status")
        self.tag = apps.get_model("extras", "tag")

        self.aggregate_ct = self.content_type.objects.get_for_model(self.aggregate)
        self.prefix_ct = self.content_type.objects.get_for_model(self.prefix)

        populate_status_choices(verbosity=0)
        self.prefix_status = self.status.objects.get(content_types=self.prefix_ct, slug="active")

        self.rir1 = self.rir.objects.create(name="RFC1918", is_private=True)
        self.rir2 = self.rir.objects.create(name="ARIN")

        # Create 4 prefixes that will be merged into by Aggregates with duplicate network/prefix_length
        self.prefix1 = self.prefix.objects.create(
            network="10.0.0.0", prefix_length=8, status=self.prefix_status, description="PrefixDesc"
        )
        self.prefix2 = self.prefix.objects.create(
            network="172.16.0.0", prefix_length=24, status=self.prefix_status, description="PrefixDesc"
        )
        self.prefix3 = self.prefix.objects.create(network="192.168.0.0", prefix_length=25, status=self.prefix_status)
        self.prefix4 = self.prefix.objects.create(
            network="192.168.100.192", prefix_length=26, status=self.prefix_status
        )
        self.aggregate1 = self.aggregate.objects.create(network="10.0.0.0", rir=self.rir1, prefix_length=8)
        self.aggregate2 = self.aggregate.objects.create(network="172.16.0.0", rir=self.rir1, prefix_length=24)
        self.aggregate3 = self.aggregate.objects.create(
            network="192.168.0.0", rir=self.rir1, prefix_length=25, description="AggregateDesc"
        )
        self.aggregate4 = self.aggregate.objects.create(
            network="192.168.100.192", rir=self.rir1, prefix_length=26, description="AggregateDesc"
        )

        # Create 8 prefixes that are not duplicated by Aggregates and will not be touched by migration
        # self.prefix5(77.77.77.0)
        # ...
        # self.prefix12(77.77.77.72)
        for i in range(8):
            prefix = self.prefix.objects.create(network=f"77.77.77.{i*8}", prefix_length=29, status=self.prefix_status)
            setattr(self, f"prefix{i+5}", prefix)

        # Create 16 aggregates that will be migrated to new Prefixes
        # self.aggregate5(5.5.5.0)
        # ...
        # self.aggregate21(5.5.5.60)
        for i in range(16):
            aggregate = self.aggregate.objects.create(
                network=f"5.5.5.{i*4}", rir=self.rir2, prefix_length=30, description="AggregateDesc"
            )
            setattr(self, f"aggregate{i+5}", aggregate)

        # tags
        self.prefix_tag_a = self.tag.objects.create(name="PrefixTagA", slug="prefixtaga")
        self.prefix_tag_b = self.tag.objects.create(name="PrefixTagB", slug="prefixtagb")
        self.prefix_tag_a.content_types.add(self.prefix_ct)
        self.prefix_tag_b.content_types.add(self.prefix_ct)
        self.aggregate_tag_a = self.tag.objects.create(name="AggregateTagA", slug="aggregatetaga")
        self.aggregate_tag_b = self.tag.objects.create(name="AggregateTagB", slug="aggregatetagb")
        self.aggregate_tag_a.content_types.add(self.aggregate_ct)
        self.aggregate_tag_b.content_types.add(self.aggregate_ct)
        self._add_tags_to_instance(self.prefix, self.prefix1, ["PrefixTagA"])
        self._add_tags_to_instance(self.prefix, self.prefix2, ["PrefixTagA"])
        self._add_tags_to_instance(self.prefix, self.prefix3, ["PrefixTagA"])
        self._add_tags_to_instance(self.prefix, self.prefix4, ["PrefixTagA"])
        self._add_tags_to_instance(self.aggregate, self.aggregate1, ["AggregateTagA", "AggregateTagB"])
        self._add_tags_to_instance(self.aggregate, self.aggregate2, ["AggregateTagA"])
        self._add_tags_to_instance(self.aggregate, self.aggregate3, ["AggregateTagB"])
        self._add_tags_to_instance(self.aggregate, self.aggregate5, ["AggregateTagA", "AggregateTagB"])
        self._add_tags_to_instance(self.aggregate, self.aggregate6, ["AggregateTagB"])

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_aggregate_to_prefix_migration_object_count(self):
        with self.subTest("Test Prefix count"):
            self.assertEqual(self.prefix.objects.count(), 28)
        with self.subTest("Test Aggregate count"):
            self.assertEqual(self.aggregate.objects.count(), 20)

    def test_aggregate_to_prefix_migration_network(self):
        for i in range(16):
            self.assertTrue(
                self.prefix.objects.filter(network=f"5.5.5.{i*4}", prefix_length=30, rir=self.rir2).exists()
            )

    def test_aggregate_to_prefix_migration_rir(self):
        with self.subTest(f"prefix.rir = {self.rir1.name}"):
            self.assertEqual(self.prefix.objects.get(network="10.0.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="172.16.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="192.168.0.0").rir, self.rir1)
            self.assertEqual(self.prefix.objects.get(network="192.168.100.192").rir, self.rir1)
        with self.subTest(f"prefix.rir = {self.rir2.name}"):
            for i in range(16):
                prefix = self.prefix.objects.get(network=f"5.5.5.{i*4}")
                self.assertEqual(prefix.rir, self.rir2)
        with self.subTest("prefix.rir is None"):
            for i in range(8):
                prefix = self.prefix.objects.get(network=f"77.77.77.{i*8}")
                self.assertIsNone(prefix.rir)

    def test_aggregate_to_prefix_migration_description(self):
        self.assertEqual(self.prefix.objects.filter(description="PrefixDesc").count(), 2)
        self.assertEqual(self.prefix.objects.filter(description="").count(), 10)
        self.assertEqual(self.prefix.objects.filter(description="AggregateDesc").count(), 16)

    def test_aggregate_to_prefix_migration_status(self):
        self.assertEqual(self.prefix.objects.filter(status=self.prefix_status).count(), self.prefix.objects.count())

    def test_aggregate_to_prefix_migration_tags(self):
        self.maxDiff = None
        with self.subTest("Prefix content type was added to Aggregate Tags"):
            prefix_tags = self.tag.objects.filter(content_types=self.prefix_ct)
            self.assertIn(self.aggregate_tag_a, prefix_tags)
            self.assertIn(self.aggregate_tag_b, prefix_tags)
        self.assertQuerysetEqual(
            self.prefix1.tags.all(),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA", "AggregateTagB"]),
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.prefix2.tags.all(),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagA"]),
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.prefix3.tags.all(),
            self.tag.objects.filter(name__in=["PrefixTagA", "AggregateTagB"]),
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.prefix4.tags.all(),
            self.tag.objects.filter(name="PrefixTagA"),
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.prefix5.tags.all(),
            self.tag.objects.filter(name__in=["AggregateTagA", "AggregateTagB"]),
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.prefix6.tags.all(),
            self.tag.objects.filter(name="AggregateTagB"),
            ordered=False,
        )
        self.assertQuerysetEqual(self.prefix7.tags.all(), self.tag.objects.none())
