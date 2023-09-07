import uuid
from unittest import skip, skipIf

from django.db import connection

from nautobot.core.models.fields import TagsField
from nautobot.core.testing.migrations import NautobotDataMigrationTest
from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.extras.choices import CustomFieldTypeChoices, ObjectChangeActionChoices, RelationshipTypeChoices


# https://github.com/nautobot/nautobot/issues/3435
@skip("test skipped until base test can be fixed to handle new migrations")
class SiteAndRegionDataMigrationToLocation(NautobotDataMigrationTest):
    migrate_from = [("dcim", "0029_add_tree_managers_and_foreign_keys_pre_data_migration")]
    migrate_to = [("dcim", "0034_migrate_region_and_site_data_to_locations")]

    def populateDataBeforeMigration(self, installed_apps):
        """Populate Site/Site-related and Region/Region-related Data before migrating them to Locations"""
        # Needed models
        apps = installed_apps
        self.content_type = apps.get_model("contenttypes", "ContentType")
        self.region = apps.get_model("dcim", "region")
        self.site = apps.get_model("dcim", "site")
        self.site.tags = TagsField()
        self.location_type = apps.get_model("dcim", "locationtype")
        self.location = apps.get_model("dcim", "location")
        self.location.tags = TagsField()
        self.provider = apps.get_model("circuits", "provider")
        self.circuit_type = apps.get_model("circuits", "circuittype")
        self.circuit = apps.get_model("circuits", "circuit")
        self.circuit_termination = apps.get_model("circuits", "circuittermination")
        self.manufacturer = apps.get_model("dcim", "manufacturer")
        self.device_type = apps.get_model("dcim", "devicetype")
        self.device = apps.get_model("dcim", "device")
        self.power_panel = apps.get_model("dcim", "powerpanel")
        self.rack_group = apps.get_model("dcim", "rackgroup")
        self.rack = apps.get_model("dcim", "rack")
        self.computed_field = apps.get_model("extras", "computedfield")
        self.config_context = apps.get_model("extras", "configcontext")
        self.custom_field = apps.get_model("extras", "customfield")
        self.custom_link = apps.get_model("extras", "customlink")
        self.dynamic_group = apps.get_model("extras", "DynamicGroup")
        self.export_template = apps.get_model("extras", "exporttemplate")
        self.image_attachment = apps.get_model("extras", "imageattachment")
        self.job = apps.get_model("extras", "job")
        self.job_hook = apps.get_model("extras", "jobhook")
        self.note = apps.get_model("extras", "note")
        self.object_change = apps.get_model("extras", "objectchange")
        self.relationship = apps.get_model("extras", "relationship")
        self.relationship_association = apps.get_model("extras", "relationshipassociation")
        self.web_hook = apps.get_model("extras", "webhook")
        self.prefix = apps.get_model("ipam", "prefix")
        self.vlan_group = apps.get_model("ipam", "vlangroup")
        self.vlan = apps.get_model("ipam", "vlan")
        self.cluster_type = apps.get_model("virtualization", "clustertype")
        self.object_permission = apps.get_model("users", "objectpermission")
        self.cluster = apps.get_model("virtualization", "cluster")
        self.status = apps.get_model("extras", "status")
        self.tag = apps.get_model("extras", "tag")
        self.user = apps.get_model("users", "user")

        self.region_ct = self.content_type.objects.get_for_model(self.region)
        self.site_ct = self.content_type.objects.get_for_model(self.site)
        self.location_ct = self.content_type.objects.get_for_model(self.location)
        self.location_type_ct = self.content_type.objects.get_for_model(self.location_type)
        self.device_ct = self.content_type.objects.get_for_model(self.device)

        self.statuses = (
            self.status.objects.create(name="Active", slug="active"),
            self.status.objects.create(name="Planned", slug="planned"),
            self.status.objects.create(name="Failed", slug="failed"),
        )
        for status in self.statuses:
            status.content_types.add(self.site_ct)
            status.content_types.add(self.region_ct)

        self.tags = (
            self.tag.objects.create(name="Tag 1", slug="tag-1"),
            self.tag.objects.create(name="Tag 2", slug="tag-2"),
            self.tag.objects.create(name="Tag 3", slug="tag-3"),
        )
        for tag in self.tags:
            tag.content_types.add(self.site_ct)
            tag.content_types.add(self.region_ct)

        regions = []
        for i in range(10):
            regions.append(self.region(name=f"Test Region {i}"))
        self.region.objects.bulk_create(regions, batch_size=10)
        # Nested Regions
        region_2 = self.region.objects.get(name="Test Region 2")
        region_2.parent = self.region.objects.get(name="Test Region 1")
        region_2.save()
        region_4 = self.region.objects.get(name="Test Region 4")
        region_4.parent = self.region.objects.get(name="Test Region 3")
        region_4.save()
        region_5 = self.region.objects.get(name="Test Region 5")
        region_5.parent = self.region.objects.get(name="Test Region 4")
        region_5.save()

        sites = []
        for i in range(10):
            sites.append(self.site(name=f"Test Site {i}"))
        self.sites = self.site.objects.bulk_create(sites, batch_size=10)
        # Sites with Regions
        site_2 = self.site.objects.get(name="Test Site 2")
        site_2.region = self.region.objects.get(name="Test Region 1")
        site_2.save()
        site_2.tags.add("Tag 1")
        site_2.tags.add("Tag 2")
        site_2.tags.add("Tag 3")
        site_4 = self.site.objects.get(name="Test Site 4")
        site_4.region = self.region.objects.get(name="Test Region 2")
        site_4.save()
        site_4.tags.add("Tag 2")
        site_4.tags.add("Tag 3")
        site_6 = self.site.objects.get(name="Test Site 6")
        site_6.region = self.region.objects.get(name="Test Region 3")
        site_6.save()
        site_6.tags.add("Tag 1")
        site_6.tags.add("Tag 3")

        location_types = []
        for i in range(5):
            location_types.append(self.location_type(name=f"Test Location Type {i}"))
        self.location_type.objects.bulk_create(location_types, batch_size=10)
        for i in range(5):
            if i == 0 or i == 1:
                continue
            location_type = self.location_type.objects.get(name=f"Test Location Type {i}")
            location_type.parent = self.location_type.objects.get(name=f"Test Location Type {i - 1}")
            location_type.save()

        locations = []
        for i in range(15):
            location_type = self.location_type.objects.get(name=f"Test Location Type {i % 5}")
            locations.append(self.location(name=f"Test Location {i}", location_type=location_type))
        self.locations = self.location.objects.bulk_create(locations, batch_size=15)

        for i in range(15):
            if i % 5 == 0 or i % 5 == 1:
                location = self.location.objects.get(name=f"Test Location {i}")
                location.site = self.site.objects.get(name=f"Test Site {i % 5}")
                location.save()
            else:
                location = self.location.objects.get(name=f"Test Location {i}")
                location.parent = self.location.objects.get(name=f"Test Location {i - 1}")
                location.save()
        # sites, regions, and locations for assignment purposes
        sites = [
            self.site.objects.get(name="Test Site 0"),
            self.site.objects.get(name="Test Site 1"),
            self.site.objects.get(name="Test Site 2"),
            self.site.objects.get(name="Test Site 3"),
        ]
        regions = [
            self.region.objects.get(name="Test Region 0"),
            self.region.objects.get(name="Test Region 1"),
            self.region.objects.get(name="Test Region 2"),
            self.region.objects.get(name="Test Region 3"),
        ]
        locations = [
            self.location.objects.get(name="Test Location 0"),
            self.location.objects.get(name="Test Location 1"),
            self.location.objects.get(name="Test Location 2"),
            self.location.objects.get(name="Test Location 3"),
        ]

        provider = self.provider.objects.create(name="Provider 1", slug="provider-1")
        circuit_type = self.circuit_type.objects.create(name="Circuit Type 1", slug="circuit-type-1")

        self.circuits = (
            self.circuit.objects.create(cid="Circuit 1", provider=provider, type=circuit_type),
            self.circuit.objects.create(cid="Circuit 2", provider=provider, type=circuit_type),
            self.circuit.objects.create(cid="Circuit 3", provider=provider, type=circuit_type),
        )
        SIDE_A = CircuitTerminationSideChoices.SIDE_A
        SIDE_Z = CircuitTerminationSideChoices.SIDE_Z
        self.cts = (
            self.circuit_termination.objects.create(circuit=self.circuits[0], site=sites[0], term_side=SIDE_A),
            self.circuit_termination.objects.create(circuit=self.circuits[0], site=sites[1], term_side=SIDE_Z),
            self.circuit_termination.objects.create(circuit=self.circuits[1], site=sites[0], term_side=SIDE_A),
            self.circuit_termination.objects.create(circuit=self.circuits[1], site=sites[1], term_side=SIDE_Z),
        )

        manufacturer = self.manufacturer.objects.create(name="Manufacturer 1")
        device_type = self.device_type.objects.create(
            comments="Device type 1",
            model="Model 1",
            slug="model-1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
            manufacturer=manufacturer,
        )

        self.device.objects.create(
            device_type=device_type,
            name="Device 1",
            site=sites[0],
            location=locations[0],
        )
        self.device.objects.create(
            device_type=device_type,
            name="Device 2",
            site=sites[1],
            location=locations[1],
        )
        self.device.objects.create(
            device_type=device_type,
            name="Device 3",
            site=sites[3],
        )
        self.power_panels = [
            self.power_panel.objects.create(name="site1-powerpanel1", site=sites[1]),
            self.power_panel.objects.create(name="site1-powerpanel2", site=sites[1]),
            self.power_panel.objects.create(name="site1-powerpanel3", site=sites[1], location=locations[2]),
        ]
        self.rack_groups = [
            self.rack_group.objects.create(site=sites[1], name="Rack Group 1", slug="rack-group-1"),
            self.rack_group.objects.create(site=sites[2], name="Rack Group 2", slug="rack-group-2"),
            self.rack_group.objects.create(
                site=sites[3], name="Rack Group 3", slug="rack-group-3", location=locations[3]
            ),
        ]
        self.racks = [
            self.rack.objects.create(site=sites[1], name="Rack 1"),
            self.rack.objects.create(site=sites[2], name="Rack 2"),
            self.rack.objects.create(site=sites[3], name="Rack 3", location=locations[3]),
        ]

        self.prefixes = [
            self.prefix.objects.create(
                network="1.1.1.0", broadcast="172.31.255.255", prefix_length=25, site=sites[1], type="container"
            ),
            self.prefix.objects.create(
                network="1.1.1.1", broadcast="172.31.255.255", prefix_length=25, site=sites[2], type="container"
            ),
            self.prefix.objects.create(
                network="1.1.1.2",
                broadcast="172.31.255.255",
                prefix_length=25,
                site=sites[3],
                location=locations[2],
                type="container",
            ),
        ]

        self.vlan_groups = [
            self.vlan_group.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=sites[1], description="A"),
            self.vlan_group.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=sites[2], description="B"),
            self.vlan_group.objects.create(
                name="VLAN Group 3", slug="vlan-group-3", site=sites[3], location=locations[2], description="C"
            ),
        ]

        self.vlans = [
            self.vlan.objects.create(name="VLAN 1", vid=1, site=sites[1]),
            self.vlan.objects.create(name="VLAN 2", vid=2, site=sites[2]),
            self.vlan.objects.create(name="VLAN 3", vid=3, site=sites[3], location=locations[2]),
        ]

        self.computed_field.objects.create(
            slug="cpf1",
            label="Computed Field One",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=self.region_ct,
        )
        self.computed_field.objects.create(
            slug="cpf2",
            label="Computed Field Two",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=self.site_ct,
        )
        self.computed_field.objects.create(
            slug="cpf3",
            label="Computed Field Three",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=self.location_ct,
        )
        custom_fields = [
            self.custom_field.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, name="field_1", default="value_1"),
            self.custom_field.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, name="field_2", default="value_2"),
            self.custom_field.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, name="field_3", default="value_3"),
        ]
        for custom_field in custom_fields:
            custom_field.content_types.set(
                [
                    self.content_type.objects.get_for_model(self.site),
                    self.content_type.objects.get_for_model(self.region),
                ]
            )
        sites[0]._custom_field_data = {"field_1": "ABC", "field_2": "Bar"}
        sites[0].save()
        sites[1]._custom_field_data = {"field_1": "abc", "field_2": "foo"}
        sites[1].save()
        regions[0]._custom_field_data = {"field_1": "DEF", "field_2": "Bar"}
        regions[0].save()
        regions[1]._custom_field_data = {"field_1": "def", "field_2": "foo"}
        regions[1].save()

        self.configcontexts = (
            self.config_context.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777}),
            self.config_context.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789}),
            self.config_context.objects.create(name="context 3", weight=99, data={"d": 1}),
        )
        self.configcontexts[0].regions.add(regions[0], regions[1])
        self.configcontexts[0].sites.add(sites[0], sites[1])
        self.configcontexts[1].regions.add(regions[2], regions[3])
        self.configcontexts[1].locations.add(locations[0])
        self.configcontexts[2].sites.add(sites[2], sites[3])
        self.configcontexts[2].locations.add(locations[1])

        self.custom_link.objects.create(
            content_type=self.site_ct,
            name="CL-1",
            text="customlink text 1",
            target_url="http://test-1.com/test1",
            weight=100,
            new_window=False,
        )
        self.custom_link.objects.create(
            content_type=self.site_ct,
            name="CL-2",
            text="customlink text 2",
            target_url="http://test-2.com/test2",
            weight=100,
            new_window=False,
        )
        self.custom_link.objects.create(
            content_type=self.location_ct,
            name="CL-3",
            text="customlink text 3",
            target_url="http://test-3.com/test3",
            weight=100,
            new_window=False,
        )
        self.dynamic_group.objects.create(
            name="DG-1",
            slug="dg-1",
            filter={"region": ["test-region-0", "test-region-1"]},
            content_type=self.device_ct,
        )
        self.dynamic_group.objects.create(
            name="DG-2",
            slug="dg-2",
            filter={"site": ["test-site-0", "test-site-1"], "region": ["test-region-2", "test-region-3"]},
            content_type=self.device_ct,
        )
        self.dynamic_group.objects.create(
            name="DG-3",
            slug="dg-3",
            filter={"location": ["test-location-0", "test-location-1"]},
            content_type=self.device_ct,
        )
        self.export_template.objects.create(
            name="Export Template 1",
            content_type=self.region_ct,
            template_code="TESTING",
        )
        self.export_template.objects.create(
            name="Export Template 2",
            content_type=self.site_ct,
            template_code="TESTING",
        )
        self.export_template.objects.create(
            name="Export Template 3",
            content_type=self.location_ct,
            template_code="TESTING",
        )
        self.image_attachment.objects.create(
            content_type=self.site_ct,
            object_id=sites[0].pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        self.image_attachment.objects.create(
            content_type=self.site_ct,
            object_id=sites[1].pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        )
        self.image_attachment.objects.create(
            content_type=self.location_ct,
            object_id=locations[0].pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        )
        jh_1 = self.job_hook.objects.create(
            name="JobHook1",
            job=self.job.objects.get(job_class_name="TestJobHookReceiverLog"),
            type_create=True,
            type_update=True,
            type_delete=True,
        )
        jh_1.content_types.set([self.region_ct])
        jh_2 = self.job_hook.objects.create(
            name="JobHook2",
            job=self.job.objects.get(job_class_name="TestJobHookReceiverChange"),
            type_create=True,
            type_update=True,
            type_delete=False,
        )
        jh_2.content_types.set([self.site_ct])
        jh_3 = self.job_hook.objects.create(
            name="JobHook3",
            enabled=False,
            job=self.job.objects.get(job_class_name="TestJobHookReceiverFail"),
            type_delete=True,
        )
        jh_3.content_types.set([self.location_ct])
        self.note.objects.create(
            note="Location has been placed on maintenance.",
            assigned_object_type=self.region_ct,
            assigned_object_id=regions[0].pk,
        )
        self.note.objects.create(
            note="Location maintenance has ended.",
            assigned_object_type=self.site_ct,
            assigned_object_id=sites[0].pk,
        )
        self.note.objects.create(
            note="Location is under duress.",
            assigned_object_type=self.location_ct,
            assigned_object_id=locations[1].pk,
        )
        user = self.user.objects.create(username="user1")
        self.object_change.objects.create(
            user=user,
            user_name=user.username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_CREATE,
            changed_object_type=self.site_ct,
            changed_object_id=sites[0].id,
            object_repr=str(sites[0]),
            object_data={"name": sites[0].name, "slug": sites[0].slug},
        )
        self.object_change.objects.create(
            user=user,
            user_name=user.username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object_type=self.region_ct,
            changed_object_id=regions[0].id,
            object_repr=str(regions[0]),
            object_data={"name": regions[0].name, "slug": regions[0].slug},
        )
        self.object_change.objects.create(
            user=user,
            user_name=user.username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object_type=self.site_ct,
            changed_object_id=sites[0].id,
            object_repr=str(sites[0]),
            object_data={"name": sites[0].name, "slug": sites[0].slug},
            related_object_type=self.region_ct,
            related_object_id=regions[0].id,
        )
        o2m = self.relationship.objects.create(
            label="Site to Location o2m",
            slug="site-to-location-o2m",
            source_type=self.site_ct,
            destination_type=self.location_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        self.relationship_association.objects.create(
            relationship=o2m,
            source_id=sites[0].id,
            source_type_id=self.site_ct.id,
            destination_id=self.location.objects.get(name="Test Location 0").id,
            destination_type_id=self.location_ct.id,
        )
        self.relationship_association.objects.create(
            relationship=o2m,
            source_id=sites[0].id,
            source_type_id=self.site_ct.id,
            destination_id=self.location.objects.get(name="Test Location 1").id,
            destination_type_id=self.location_ct.id,
        )
        m2m = self.relationship.objects.create(
            label="Region to Site m2m",
            slug="region-to-site-m2m",
            source_type=self.region_ct,
            destination_type=self.site_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.relationship_association.objects.create(
            relationship=m2m,
            source_id=regions[0].id,
            source_type_id=self.region_ct.id,
            destination_id=sites[0].id,
            destination_type_id=self.site_ct.id,
        )
        self.relationship_association.objects.create(
            relationship=m2m,
            source_id=self.region.objects.get(name="Test Region 1").id,
            source_type_id=self.region_ct.id,
            destination_id=self.site.objects.get(name="Test Site 1").id,
            destination_type_id=self.site_ct.id,
        )
        o2o = self.relationship.objects.create(
            label="Region to Location o2o",
            slug="region-to-location-o2o",
            source_type=self.region_ct,
            destination_type=self.location_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        self.relationship_association.objects.create(
            relationship=o2o,
            source_id=self.region.objects.get(name="Test Region 2").id,
            source_type_id=self.region_ct.id,
            destination_id=self.location.objects.get(name="Test Location 2").id,
            destination_type_id=self.location_ct.id,
        )
        self.relationship_association.objects.create(
            relationship=o2o,
            source_id=self.region.objects.get(name="Test Region 3").id,
            source_type_id=self.region_ct.id,
            destination_id=self.location.objects.get(name="Test Location 3").id,
            destination_type_id=self.location_ct.id,
        )
        self.webhooks = (
            self.web_hook(
                name="test-1",
                type_create=True,
                payload_url="http://example.com/test1",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            self.web_hook(
                name="test-2",
                type_update=True,
                payload_url="http://example.com/test2",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            self.web_hook(
                name="test-3",
                type_delete=True,
                payload_url="http://example.com/test3",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
        )

        for webhook in self.webhooks:
            webhook.save()
            webhook.content_types.set([self.site_ct, self.region_ct])

        cluster_type = self.cluster_type.objects.create(name="Cluster Type 1", slug="cluster-type-1")

        self.clusters = (
            self.cluster.objects.create(name="Cluster 1", cluster_type=cluster_type, site=sites[0]),
            self.cluster.objects.create(
                name="Cluster 2", cluster_type=cluster_type, site=self.site.objects.get(name="Test Site 1")
            ),
            self.cluster.objects.create(
                name="Cluster 3",
                cluster_type=cluster_type,
                site=sites[0],
                location=self.location.objects.get(name="Test Location 0"),
            ),
            self.cluster.objects.create(
                name="Cluster 4",
                cluster_type=cluster_type,
                site=sites[0],
                location=self.location.objects.get(name="Test Location 0"),
            ),
        )

        self.object_permissions = (
            self.object_permission.objects.create(
                name="Test Region Permission 1",
                actions=["view"],
            ),
            self.object_permission.objects.create(
                name="Test Region Permission 2",
                actions=["view", "add", "change"],
            ),
            self.object_permission.objects.create(
                name="Test Site Permission 1",
                actions=["view"],
            ),
            self.object_permission.objects.create(
                name="Test Site Permission 2",
                actions=["view", "delete"],
            ),
        )
        self.object_permissions[0].object_types.add(self.region_ct)
        self.object_permissions[1].object_types.add(self.region_ct)
        self.object_permissions[2].object_types.add(self.site_ct)
        self.object_permissions[3].object_types.add(self.site_ct)

    @skipIf(
        connection.vendor != "postgresql",
        "mysql does not support rollbacks",
    )
    def test_region_and_site_data_migration(self):
        with self.subTest("Testing Region and Site correctly migrate to Locations"):
            # Test Location Types are created and the hierarchy is correct
            self.assertEqual(len(self.location_type.objects.filter(name="Region")), 1)
            self.assertEqual(len(self.location_type.objects.filter(name="Site")), 1)
            self.assertEqual(
                self.location_type.objects.get(name="Site").parent, self.location_type.objects.get(name="Region")
            )
            self.assertEqual(
                self.location_type.objects.get(name="Test Location Type 0").parent,
                self.location_type.objects.get(name="Site"),
            )
            self.assertEqual(
                self.location_type.objects.get(name="Test Location Type 1").parent,
                self.location_type.objects.get(name="Site"),
            )
            # Global Region is created
            self.assertEqual(
                len(
                    self.location.objects.filter(
                        name="Global Region", location_type=self.location_type.objects.get(name="Region")
                    )
                ),
                1,
            )

            # For each region, a new location of LocationType "Region" is created
            for i in range(10):
                region_locations = self.location.objects.filter(
                    name=f"Test Region {i}",
                    location_type=self.location_type.objects.get(name="Region"),
                )
                old_region = self.region.objects.get(name=f"Test Region {i}")
                self.assertEqual(len(region_locations), 1)
                # Check if the migrated_location field is correctly populated by the data migration.
                self.assertEqual(old_region.migrated_location, region_locations[0])
                # Check if the migrated_location has the same pk as the old region
                self.assertEqual(old_region.migrated_location.pk, old_region.pk)

            # For each site, a new location of LocationType "Site" is created and its parent, if not None, is
            # mapped to a Region LocationType location with the same name as its assigned Region.
            for i in range(10):
                site_locations = self.location.objects.filter(
                    name=f"Test Site {i}", location_type=self.location_type.objects.get(name="Site")
                )
                old_site = self.site.objects.get(name=f"Test Site {i}")
                self.assertEqual(len(site_locations), 1)
                # Check if the migrated_location field is correctly populated by the data migration.
                self.assertEqual(old_site.migrated_location, site_locations[0])
                # Check if the migrated_location has the same pk as the old site
                self.assertEqual(old_site.migrated_location.pk, old_site.pk)
                if old_site.region:
                    self.assertEqual(site_locations.first().parent.name, old_site.region.name)

            # Check that top level locations have Site locations as their parent, and they are matching up correctly
            old_top_level_locations = self.location.objects.filter(site__isnull=False)
            for location in old_top_level_locations:
                self.assertEqual(location.parent.name, location.site.name)

        with self.subTest("Testing Circuits app model migration"):
            cts = self.circuit_termination.objects.all().select_related("site", "location")
            for ct in cts:
                self.assertEqual(ct.site.migrated_location, ct.location)
                self.assertEqual(ct.site.name, ct.location.name)

        with self.subTest("Testing DCIM app model migration"):
            device_1 = self.device.objects.get(name="Device 1")
            self.assertEqual(device_1.location.name, "Test Location 0")
            device_2 = self.device.objects.get(name="Device 2")
            self.assertEqual(device_2.location.name, "Test Location 1")
            device_3 = self.device.objects.get(name="Device 3")
            self.assertEqual(device_3.location.name, "Test Site 3")
            self.assertEqual(device_3.location.location_type.name, "Site")
            powerpanel_1 = self.power_panel.objects.get(name="site1-powerpanel1")
            self.assertEqual(powerpanel_1.location.name, "Test Site 1")
            self.assertEqual(powerpanel_1.location.location_type.name, "Site")
            powerpanel_2 = self.power_panel.objects.get(name="site1-powerpanel2")
            self.assertEqual(powerpanel_2.location.name, "Test Site 1")
            self.assertEqual(powerpanel_2.location.location_type.name, "Site")
            powerpanel_3 = self.power_panel.objects.get(name="site1-powerpanel3")
            self.assertEqual(powerpanel_3.location.name, "Test Location 2")
            self.assertEqual(powerpanel_3.location.location_type.name, "Test Location Type 2")
            rackgroup_1 = self.rack_group.objects.get(name="Rack Group 1")
            self.assertEqual(rackgroup_1.location.name, "Test Site 1")
            self.assertEqual(rackgroup_1.location.location_type.name, "Site")
            rackgroup_2 = self.rack_group.objects.get(name="Rack Group 2")
            self.assertEqual(rackgroup_2.location.name, "Test Site 2")
            self.assertEqual(rackgroup_2.location.location_type.name, "Site")
            rackgroup_3 = self.rack_group.objects.get(name="Rack Group 3")
            self.assertEqual(rackgroup_3.location.name, "Test Location 3")
            self.assertEqual(rackgroup_3.location.location_type.name, "Test Location Type 3")
            rack_1 = self.rack.objects.get(name="Rack 1")
            self.assertEqual(rack_1.location.name, "Test Site 1")
            self.assertEqual(rack_1.location.location_type.name, "Site")
            rack_2 = self.rack.objects.get(name="Rack 2")
            self.assertEqual(rack_2.location.name, "Test Site 2")
            self.assertEqual(rack_2.location.location_type.name, "Site")
            rack_3 = self.rack.objects.get(name="Rack 3")
            self.assertEqual(rack_3.location.name, "Test Location 3")
            self.assertEqual(rack_3.location.location_type.name, "Test Location Type 3")

        with self.subTest("Testing Extras app model migration"):
            cpf_1 = self.computed_field.objects.get(slug="cpf1")
            self.assertEqual(cpf_1.content_type.model, self.location_ct.model)
            cpf_2 = self.computed_field.objects.get(slug="cpf2")
            self.assertEqual(cpf_2.content_type.model, self.location_ct.model)
            cpf_3 = self.computed_field.objects.get(slug="cpf3")
            self.assertEqual(cpf_3.content_type.model, self.location_ct.model)
            cf_loc_1 = self.location.objects.get(name="Test Site 0")
            self.assertEqual(cf_loc_1._custom_field_data, {"field_1": "ABC", "field_2": "Bar"})
            cf_loc_2 = self.location.objects.get(name="Test Site 1")
            self.assertEqual(cf_loc_2._custom_field_data, {"field_1": "abc", "field_2": "foo"})
            cf_loc_3 = self.location.objects.get(name="Test Region 0")
            self.assertEqual(cf_loc_3._custom_field_data, {"field_1": "DEF", "field_2": "Bar"})
            cf_loc_4 = self.location.objects.get(name="Test Region 1")
            self.assertEqual(cf_loc_4._custom_field_data, {"field_1": "def", "field_2": "foo"})
            cc_1 = self.config_context.objects.get(name="context 1")
            self.assertIn(self.location.objects.get(name="Test Region 0"), cc_1.locations.all())
            self.assertIn(self.location.objects.get(name="Test Region 1"), cc_1.locations.all())
            self.assertIn(self.location.objects.get(name="Test Site 0"), cc_1.locations.all())
            self.assertIn(self.location.objects.get(name="Test Site 1"), cc_1.locations.all())
            cc_2 = self.config_context.objects.get(name="context 2")
            self.assertIn(self.location.objects.get(name="Test Region 2"), cc_2.locations.all())
            self.assertIn(self.location.objects.get(name="Test Region 3"), cc_2.locations.all())
            self.assertIn(self.location.objects.get(name="Test Location 0"), cc_2.locations.all())
            cc_3 = self.config_context.objects.get(name="context 3")
            self.assertIn(self.location.objects.get(name="Test Site 2"), cc_3.locations.all())
            self.assertIn(self.location.objects.get(name="Test Site 3"), cc_3.locations.all())
            self.assertIn(self.location.objects.get(name="Test Location 1"), cc_3.locations.all())
            cl_1 = self.custom_link.objects.get(name="CL-1")
            self.assertEqual(cl_1.content_type.model, self.location_ct.model)
            cl_2 = self.custom_link.objects.get(name="CL-2")
            self.assertEqual(cl_2.content_type.model, self.location_ct.model)
            cl_3 = self.custom_link.objects.get(name="CL-3")
            self.assertEqual(cl_3.content_type.model, self.location_ct.model)
            dg_1 = self.dynamic_group.objects.get(name="DG-1")
            self.assertEqual(dg_1.filter, {"location": ["test-region-0", "test-region-1"]})
            dg_2 = self.dynamic_group.objects.get(name="DG-2")
            self.assertEqual(
                dg_2.filter, {"location": ["test-region-2", "test-region-3", "test-site-0", "test-site-1"]}
            )
            dg_3 = self.dynamic_group.objects.get(name="DG-3")
            self.assertEqual(dg_3.filter, {"location": ["test-location-0", "test-location-1"]})
            et_1 = self.export_template.objects.get(name="Export Template 1")
            self.assertEqual(et_1.content_type.model, self.location_ct.model)
            et_2 = self.export_template.objects.get(name="Export Template 2")
            self.assertEqual(et_2.content_type.model, self.location_ct.model)
            et_3 = self.export_template.objects.get(name="Export Template 3")
            self.assertEqual(et_3.content_type.model, self.location_ct.model)
            ia_1 = self.image_attachment.objects.get(name="Image Attachment 1")
            image_location_1 = self.location.objects.get(id=ia_1.object_id)
            self.assertEqual(ia_1.content_type.model, self.location_ct.model)
            self.assertEqual(image_location_1.location_type.name, "Site")
            self.assertEqual(image_location_1.name, "Test Site 0")
            ia_2 = self.image_attachment.objects.get(name="Image Attachment 2")
            image_location_2 = self.location.objects.get(id=ia_2.object_id)
            self.assertEqual(ia_2.content_type.model, self.location_ct.model)
            self.assertEqual(image_location_2.location_type.name, "Site")
            self.assertEqual(image_location_2.name, "Test Site 1")
            ia_3 = self.image_attachment.objects.get(name="Image Attachment 3")
            image_location_3 = self.location.objects.get(id=ia_3.object_id)
            self.assertEqual(ia_3.content_type.model, self.location_ct.model)
            self.assertEqual(image_location_3.location_type.name, "Test Location Type 0")
            self.assertEqual(image_location_3.name, "Test Location 0")
            jh_1 = self.job_hook.objects.get(name="JobHook1")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model],
                sorted(list(jh_1.content_types.values_list("model", flat=True))),
            )
            jh_2 = self.job_hook.objects.get(name="JobHook2")
            self.assertEqual(
                [self.location_ct.model, self.site_ct.model],
                sorted(list(jh_2.content_types.values_list("model", flat=True))),
            )
            jh_3 = self.job_hook.objects.get(name="JobHook3")
            self.assertEqual([self.location_ct.model], sorted(list(jh_3.content_types.values_list("model", flat=True))))
            nt_1 = self.note.objects.get(note="Location has been placed on maintenance.")
            note_location_1 = self.location.objects.get(id=nt_1.assigned_object_id)
            self.assertEqual(nt_1.assigned_object_type.model, self.location_ct.model)
            self.assertEqual(note_location_1.location_type.name, "Region")
            self.assertEqual(note_location_1.name, "Test Region 0")
            nt_2 = self.note.objects.get(note="Location maintenance has ended.")
            self.assertEqual(nt_2.assigned_object_type.model, self.location_ct.model)
            note_location_2 = self.location.objects.get(id=nt_2.assigned_object_id)
            self.assertEqual(note_location_2.location_type.name, "Site")
            self.assertEqual(note_location_2.name, "Test Site 0")
            nt_3 = self.note.objects.get(note="Location is under duress.")
            note_location_3 = self.location.objects.get(id=nt_3.assigned_object_id)
            self.assertEqual(nt_3.assigned_object_type.model, self.location_ct.model)
            self.assertEqual(note_location_3.location_type.name, "Test Location Type 1")
            self.assertEqual(note_location_3.name, "Test Location 1")

            oc_1 = self.object_change.objects.get(action=ObjectChangeActionChoices.ACTION_CREATE, user__isnull=False)
            self.assertEqual(oc_1.changed_object_type.model, self.location_ct.model)
            self.assertEqual(oc_1.changed_object_id, self.location.objects.get(name="Test Site 0").id)
            oc_2 = self.object_change.objects.get(action=ObjectChangeActionChoices.ACTION_UPDATE, user__isnull=False)
            self.assertEqual(oc_2.changed_object_type.model, self.location_ct.model)
            self.assertEqual(oc_2.changed_object_id, self.location.objects.get(name="Test Region 0").id)
            oc_3 = self.object_change.objects.get(action=ObjectChangeActionChoices.ACTION_DELETE, user__isnull=False)
            self.assertEqual(oc_3.changed_object_type.model, self.location_ct.model)
            self.assertEqual(oc_3.changed_object_id, self.location.objects.get(name="Test Site 0").id)
            self.assertEqual(oc_3.related_object_type.model, self.location_ct.model)
            self.assertEqual(oc_3.related_object_id, self.location.objects.get(name="Test Region 0").id)

            # Assert that the new ObjectChange instances also exist and has the right data
            region_object_changes = self.object_change.objects.filter(change_context_detail="Migrated from Region")
            # Assert that for every new Region LocationType location created, there is a new object change documenting the migration
            self.assertEqual(
                len(region_object_changes),
                len(
                    self.location.objects.filter(location_type=self.location_type.objects.get(name="Region")).exclude(
                        name="Global Region"
                    )
                ),
            )
            for object_change in region_object_changes:
                self.assertEqual(object_change.changed_object_type.model, self.location_ct.model)
                self.assertEqual(
                    object_change.object_data["name"],
                    self.location.objects.get(id=object_change.changed_object_id).name,
                )
                self.assertEqual(
                    object_change.object_data["location_type"],
                    str(self.location.objects.get(id=object_change.changed_object_id).location_type.id),
                )

            site_object_changes = self.object_change.objects.filter(change_context_detail="Migrated from Site")
            # Assert that for every new Site LocationType location created, there is a new object change documenting the migration
            self.assertEqual(
                len(site_object_changes),
                len(self.location.objects.filter(location_type=self.location_type.objects.get(name="Site"))),
            )
            for object_change in site_object_changes:
                self.assertEqual(object_change.changed_object_type.model, self.location_ct.model)
                self.assertEqual(
                    object_change.object_data["name"],
                    self.location.objects.get(id=object_change.changed_object_id).name,
                )
                self.assertEqual(
                    object_change.object_data["location_type"],
                    str(self.location.objects.get(id=object_change.changed_object_id).location_type.id),
                )

            o2m = self.relationship.objects.get(name="Site to Location o2m")
            self.assertEqual(o2m.source_type.model, self.location_ct.model)
            self.assertEqual(o2m.destination_type.model, self.location_ct.model)
            o2m_rs_1 = self.relationship_association.objects.get(
                relationship=o2m, destination_id=self.location.objects.get(name="Test Location 0").id
            )
            o2m_rs_2 = self.relationship_association.objects.get(
                relationship=o2m, destination_id=self.location.objects.get(name="Test Location 1").id
            )
            self.assertEqual(o2m_rs_1.source_id, self.location.objects.get(name="Test Site 0").id)
            self.assertEqual(o2m_rs_2.destination_id, self.location.objects.get(name="Test Location 1").id)

            m2m = self.relationship.objects.get(name="Region to Site m2m")
            self.assertEqual(m2m.source_type.model, self.location_ct.model)
            self.assertEqual(m2m.destination_type.model, self.location_ct.model)
            m2m_rs_1 = self.relationship_association.objects.get(
                relationship=m2m, source_id=self.location.objects.get(name="Test Region 0").id
            )
            m2m_rs_2 = self.relationship_association.objects.get(
                relationship=m2m, source_id=self.location.objects.get(name="Test Region 1").id
            )
            self.assertEqual(m2m_rs_1.source_id, self.location.objects.get(name="Test Region 0").id)
            self.assertEqual(m2m_rs_1.destination_id, self.location.objects.get(name="Test Site 0").id)
            self.assertEqual(m2m_rs_2.source_id, self.location.objects.get(name="Test Region 1").id)
            self.assertEqual(m2m_rs_2.destination_id, self.location.objects.get(name="Test Site 1").id)

            o2o = self.relationship.objects.get(name="Region to Location o2o")
            self.assertEqual(o2o.source_type.model, self.location_ct.model)
            self.assertEqual(o2o.destination_type.model, self.location_ct.model)
            o2o_rs_1 = self.relationship_association.objects.get(
                relationship=o2o, source_id=self.location.objects.get(name="Test Region 2").id
            )
            o2o_rs_2 = self.relationship_association.objects.get(
                relationship=o2o, source_id=self.location.objects.get(name="Test Region 3").id
            )
            self.assertEqual(o2o_rs_1.source_id, self.location.objects.get(name="Test Region 2").id)
            self.assertEqual(o2o_rs_1.destination_id, self.location.objects.get(name="Test Location 2").id)
            self.assertEqual(o2o_rs_2.source_id, self.location.objects.get(name="Test Region 3").id)
            self.assertEqual(o2o_rs_2.destination_id, self.location.objects.get(name="Test Location 3").id)

            status_1 = self.status.objects.get(name="Active")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(status_1.content_types.values_list("model", flat=True))),
            )
            status_2 = self.status.objects.get(name="Planned")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(status_2.content_types.values_list("model", flat=True))),
            )
            status_3 = self.status.objects.get(name="Failed")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(status_3.content_types.values_list("model", flat=True))),
            )

            tag_1 = self.tag.objects.get(name="Tag 1")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(tag_1.content_types.values_list("model", flat=True))),
            )
            tag_2 = self.tag.objects.get(name="Tag 2")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(tag_2.content_types.values_list("model", flat=True))),
            )
            tag_3 = self.tag.objects.get(name="Tag 3")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(tag_3.content_types.values_list("model", flat=True))),
            )
            # Check if the tags from Sites are properly transferred to Locations
            self.assertCountEqual(
                self.location.objects.get(name="Test Site 2").tags.values_list("id", flat=True),
                self.tag.objects.filter(name__in=["Tag 1", "Tag 2", "Tag 3"]).values_list("id", flat=True),
            )
            self.assertCountEqual(
                self.location.objects.get(name="Test Site 4").tags.values_list("id", flat=True),
                self.tag.objects.filter(name__in=["Tag 2", "Tag 3"]).values_list("id", flat=True),
            )
            self.assertCountEqual(
                self.location.objects.get(name="Test Site 6").tags.values_list("id", flat=True),
                self.tag.objects.filter(name__in=["Tag 1", "Tag 3"]).values_list("id", flat=True),
            )
            wb_1 = self.web_hook.objects.get(name="test-1")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(wb_1.content_types.values_list("model", flat=True))),
            )
            wb_2 = self.web_hook.objects.get(name="test-2")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(wb_2.content_types.values_list("model", flat=True))),
            )
            wb_3 = self.web_hook.objects.get(name="test-3")
            self.assertEqual(
                [self.location_ct.model, self.region_ct.model, self.site_ct.model],
                sorted(list(wb_3.content_types.values_list("model", flat=True))),
            )

        with self.subTest("Testing IPAM app model migration"):
            prefix_1 = self.prefix.objects.get(network="1.1.1.0")
            self.assertEqual(prefix_1.location.name, "Test Site 1")
            self.assertEqual(prefix_1.location.location_type.name, "Site")
            prefix_2 = self.prefix.objects.get(network="1.1.1.1")
            self.assertEqual(prefix_2.location.name, "Test Site 2")
            self.assertEqual(prefix_2.location.location_type.name, "Site")
            prefix_3 = self.prefix.objects.get(network="1.1.1.2")
            self.assertEqual(prefix_3.location.name, "Test Location 2")
            self.assertEqual(prefix_3.location.location_type.name, "Test Location Type 2")
            vlangroup_1 = self.vlan_group.objects.get(name="VLAN Group 1")
            self.assertEqual(vlangroup_1.location.name, "Test Site 1")
            self.assertEqual(vlangroup_1.location.location_type.name, "Site")
            vlangroup_2 = self.vlan_group.objects.get(name="VLAN Group 2")
            self.assertEqual(vlangroup_2.location.name, "Test Site 2")
            self.assertEqual(vlangroup_2.location.location_type.name, "Site")
            vlangroup_3 = self.vlan_group.objects.get(name="VLAN Group 3")
            self.assertEqual(vlangroup_3.location.name, "Test Location 2")
            self.assertEqual(vlangroup_3.location.location_type.name, "Test Location Type 2")
            vlan_1 = self.vlan.objects.get(name="VLAN 1")
            self.assertEqual(vlan_1.location.name, "Test Site 1")
            self.assertEqual(vlan_1.location.location_type.name, "Site")
            vlan_2 = self.vlan.objects.get(name="VLAN 2")
            self.assertEqual(vlan_2.location.name, "Test Site 2")
            self.assertEqual(vlan_2.location.location_type.name, "Site")
            vlan_3 = self.vlan.objects.get(name="VLAN 3")
            self.assertEqual(vlan_3.location.name, "Test Location 2")
            self.assertEqual(vlan_3.location.location_type.name, "Test Location Type 2")

        with self.subTest("Testing Virtualization app model migration"):
            site_clusters = self.cluster.objects.filter(name__in=["Cluster 1", "Cluster 2"])
            self.assertEqual(site_clusters[0].site.name, site_clusters[0].location.name)
            self.assertEqual(site_clusters[1].site.name, site_clusters[1].location.name)

            loc_clusters = self.cluster.objects.filter(name__in=["Cluster 3", "Cluster 4"])
            self.assertEqual(loc_clusters[0].location.name, "Test Location 0")
            self.assertEqual(loc_clusters[1].location.name, "Test Location 0")

        with self.subTest("Testing Users app model migration"):
            region_permissions = self.object_permission.objects.filter(
                name__in=["Test Region Permission 1", "Test Region Permission 2"]
            )
            self.assertEqual(
                [self.location_ct.model, self.location_type_ct.model, self.region_ct.model],
                sorted(list(region_permissions[0].object_types.values_list("model", flat=True))),
            )
            self.assertEqual(
                [self.location_ct.model, self.location_type_ct.model, self.region_ct.model],
                sorted(list(region_permissions[1].object_types.values_list("model", flat=True))),
            )
            site_permissions = self.object_permission.objects.filter(
                name__in=["Test Site Permission 1", "Test Site Permission 2"]
            )
            self.assertEqual(
                [self.location_ct.model, self.location_type_ct.model, self.site_ct.model],
                sorted(list(site_permissions[0].object_types.values_list("model", flat=True))),
            )
            self.assertEqual(
                [self.location_ct.model, self.location_type_ct.model, self.site_ct.model],
                sorted(list(site_permissions[1].object_types.values_list("model", flat=True))),
            )
