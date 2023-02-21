from nautobot.core.tests.test_migration import NautobotDataMigrationTest
from nautobot.circuits.choices import CircuitTerminationSideChoices
from netaddr import IPNetwork


class SiteAndRegionDataMigrationToLocation(NautobotDataMigrationTest):
    migrate_from = [("dcim", "0029_change_tree_manager_on_tree_models")]
    migrate_to = [("dcim", "0030_migrate_region_and_site_data_to_locations")]

    def populateDataBeforeMigration(self, apps):
        """Populate Site/Site-related and Region/Region-related Data before migrating them to Locations"""
        # Needed models
        ContentType = apps.get_model("contenttypes", "ContentType")
        Region = apps.get_model("dcim", "region")
        Site = apps.get_model("dcim", "site")
        LocationType = apps.get_model("dcim", "locationtype")
        Location = apps.get_model("dcim", "location")
        Provider = apps.get_model("circuits", "provider")
        CircuitType = apps.get_model("circuits", "circuittype")
        Circuit = apps.get_model("circuits", "circuit")
        CircuitTermination = apps.get_model("circuits", "circuittermination")
        Manufacturer = apps.get_model("dcim", "manufacturer")
        DeviceType = apps.get_model("dcim", "devicetype")
        Device = apps.get_model("dcim", "device")
        PowerPanel = apps.get_model("dcim", "powerpanel")
        RackGroup = apps.get_model("dcim", "rackgroup")
        Rack = apps.get_model("dcim", "rack")
        ComputedField = apps.get_model("extras", "computedfield")
        ConfigContext = apps.get_model("extras", "configcontext")
        CustomField = apps.get_model("extras", "customfield")
        CustomLink = apps.get_model("extras", "customlink")
        DynamicGroup = apps.get_model("extras", "DynamicGroup")
        ExportTemplate = apps.get_model("extras", "exporttemplate")
        ImageAttachment = apps.get_model("extras", "imageattachment")
        JobHook = apps.get_model("extras", "jobhook")
        Note = apps.get_model("extras", "note")
        WebHook = apps.get_model("extras", "webhook")
        Relationship = apps.get_model("extras", "relationship")
        RelationshipAssociation = apps.get_model("extras", "relationshipassociation")
        Prefix = apps.get_model("ipam", "prefix")
        VLANGroup = apps.get_model("ipam", "vlangroup")
        VLAN = apps.get_model("ipam", "vlan")
        ClusterType = apps.get_model("virtualization", "clustertype")
        Cluster = apps.get_model("virtualization", "cluster")
        Status = apps.get_model("extras", "status")
        Tag = apps.get_model("extras", "tag")

        region_ct = ContentType.objects.get_for_model(Region)
        site_ct = ContentType.objects.get_for_model(Site)
        location_ct = ContentType.objects.get_for_model(Location)

        regions = []
        for i in range(10):
            regions.append(Region(name=f"Test Region {i}"))
        Region.objects.bulk_create(regions, batch_size=10)
        # Nested Regions
        region_2 = Region.objects.get(name="Test Region 2")
        region_2.parent = Region.objects.get(name="Test Region 1")
        region_2.save()
        region_4 = Region.objects.get(name="Test Region 4")
        region_4.parent = Region.objects.get(name="Test Region 3")
        region_4.save()
        region_5 = Region.objects.get(name="Test Region 5")
        region_5.parent = Region.objects.get(name="Test Region 4")
        region_5.save()

        sites = []
        for i in range(10):
            sites.append(Site(name=f"Test Site {i}"))
        self.sites = Site.objects.bulk_create(sites, batch_size=10)
        # Sites with Regions
        site_2 = Site.objects.get(name="Test Site 2")
        site_2.region = Region.objects.get(name="Test Region 1")
        site_2.save()
        site_4 = Site.objects.get(name="Test Site 4")
        site_4.region = Region.objects.get(name="Test Region 2")
        site_4.save()
        site_6 = Site.objects.get(name="Test Site 6")
        site_6.region = Region.objects.get(name="Test Region 3")
        site_6.save()

        location_types = []
        for i in range(5):
            location_types.append(LocationType(name=f"Test Location Type {i}"))
        LocationType.objects.bulk_create(location_types, batch_size=10)
        for i in range(5):
            if i == 0 or i == 1:
                continue
            location_type = LocationType.objects.get(name=f"Test Location Type {i}")
            location_type.parent = LocationType.objects.get(name=f"Test Location Type {i - 1}")
            location_type.save()

        locations = []
        for i in range(15):
            location_type = LocationType.objects.get(name=f"Test Location Type {i % 5}")
            locations.append(Location(name=f"Test Location {i}", location_type=location_type))
        self.locations = Location.objects.bulk_create(locations, batch_size=15)

        for i in range(15):
            if i % 5 == 0 or i % 5 == 1:
                location = Location.objects.get(name=f"Test Location {i}")
                location.site = Site.objects.get(name=f"Test Site {i % 5}")
                location.save()
            else:
                location = Location.objects.get(name=f"Test Location {i}")
                location.parent = Location.objects.get(name=f"Test Location {i - 1}")
                location.save()

        provider = Provider.objects.create(name="Provider 1", slug="provider-1")
        circuit_type = CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")

        self.circuits = (
            Circuit.objects.create(cid="Circuit 1", provider=provider, type=circuit_type),
            Circuit.objects.create(cid="Circuit 2", provider=provider, type=circuit_type),
            Circuit.objects.create(cid="Circuit 3", provider=provider, type=circuit_type),
        )
        SIDE_A = CircuitTerminationSideChoices.SIDE_A
        SIDE_Z = CircuitTerminationSideChoices.SIDE_Z
        self.cts = (
            CircuitTermination.objects.create(
                circuit=self.circuits[0], site=Site.objects.get(name="Test Site 0"), term_side=SIDE_A
            ),
            CircuitTermination.objects.create(
                circuit=self.circuits[0], site=Site.objects.get(name="Test Site 1"), term_side=SIDE_Z
            ),
            CircuitTermination.objects.create(
                circuit=self.circuits[1], site=Site.objects.get(name="Test Site 0"), term_side=SIDE_A
            ),
            CircuitTermination.objects.create(
                circuit=self.circuits[1], site=Site.objects.get(name="Test Site 1"), term_side=SIDE_Z
            ),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        device_type = DeviceType.objects.create(
            comments="Device type 1",
            model="Model 1",
            slug="model-1",
            part_number="Part Number 1",
            u_height=1,
            is_full_depth=True,
            manufacturer=manufacturer,
        )
        site_0 = Site.objects.get(name="Test Site 0")
        site_1 = Site.objects.get(name="Test Site 1")
        site_2 = Site.objects.get(name="Test Site 2")
        site_3 = Site.objects.get(name="Test Site 3")
        site_4 = Site.objects.get(name="Test Site 4")
        site_5 = Site.objects.get(name="Test Site 5")
        location_0 = Location.objects.get(name="Test Location 0")
        location_1 = Location.objects.get(name="Test Location 1")
        location_2 = Location.objects.get(name="Test Location 2")
        location_3 = Location.objects.get(name="Test Location 3")

        Device.objects.create(
            device_type=device_type,
            name="Device 1",
            site=site_0,
            location=location_0,
        )
        Device.objects.create(
            device_type=device_type,
            name="Device 2",
            site=site_1,
            location=location_1,
        )
        Device.objects.create(
            device_type=device_type,
            name="Device 3",
            site=site_5,
        )
        self.power_panels = [
            PowerPanel.objects.create(name="site1-powerpanel1", site=site_1),
            PowerPanel.objects.create(name="site1-powerpanel2", site=site_1),
            PowerPanel.objects.create(name="site1-powerpanel3", site=site_1, location=location_2),
        ]
        self.rack_groups = [
            RackGroup.objects.create(site=site_1, name="Rack Group 1", slug="rack-group-1"),
            RackGroup.objects.create(site=site_2, name="Rack Group 2", slug="rack-group-2"),
            RackGroup.objects.create(site=site_3, name="Rack Group 3", slug="rack-group-3", location=location_3),
        ]
        self.racks = [
            Rack.objects.create(site=site_1, name="Rack 1"),
            Rack.objects.create(site=site_2, name="Rack 2"),
            Rack.objects.create(site=site_3, name="Rack 3", location=location_3),
        ]

        self.prefixes = [
            Prefix.objects.create(
                network="1.1.1.0", broadcast="172.31.255.255", prefix_length=25, site=site_1, type="container"
            ),
            Prefix.objects.create(
                network="1.1.1.1", broadcast="172.31.255.255", prefix_length=25, site=site_2, type="container"
            ),
            Prefix.objects.create(
                network="1.1.1.2",
                broadcast="172.31.255.255",
                prefix_length=25,
                site=site_3,
                location=location_2,
                type="container",
            ),
        ]

        self.vlan_groups = [
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=site_1, description="A"),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=site_2, description="B"),
            VLANGroup.objects.create(
                name="VLAN Group 3", slug="vlan-group-3", site=site_3, location=location_2, description="C"
            ),
        ]

        self.vlans = [
            VLAN.objects.create(name="VLAN 1", vid=1, site=site_1),
            VLAN.objects.create(name="VLAN 2", vid=2, site=site_2),
            VLAN.objects.create(name="VLAN 3", vid=3, site=site_3, location=location_2),
        ]

        cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")

        self.clusters = (
            Cluster.objects.create(
                name="Cluster 1", cluster_type=cluster_type, site=Site.objects.get(name="Test Site 0")
            ),
            Cluster.objects.create(
                name="Cluster 2", cluster_type=cluster_type, site=Site.objects.get(name="Test Site 1")
            ),
            Cluster.objects.create(
                name="Cluster 3",
                cluster_type=cluster_type,
                site=Site.objects.get(name="Test Site 0"),
                location=Location.objects.get(name="Test Location 0"),
            ),
            Cluster.objects.create(
                name="Cluster 4",
                cluster_type=cluster_type,
                site=Site.objects.get(name="Test Site 0"),
                location=Location.objects.get(name="Test Location 0"),
            ),
        )

    def test_region_and_site_data_migration(self):

        with self.subTest("Testing Region and Site correctly migrate to Locations"):
            Site = self.apps.get_model("dcim", "site")
            LocationType = self.apps.get_model("dcim", "locationtype")
            Location = self.apps.get_model("dcim", "location")

            # Test Location Types are created and the hierarchy is correct
            self.assertEquals(len(LocationType.objects.filter(name="Region")), 1)
            self.assertEquals(len(LocationType.objects.filter(name="Site")), 1)
            self.assertEquals(LocationType.objects.get(name="Site").parent, LocationType.objects.get(name="Region"))
            self.assertEquals(
                LocationType.objects.get(name="Test Location Type 0").parent, LocationType.objects.get(name="Site")
            )
            self.assertEquals(
                LocationType.objects.get(name="Test Location Type 1").parent, LocationType.objects.get(name="Site")
            )
            # Global Region is created
            self.assertEquals(
                len(
                    Location.objects.filter(name="Global Region", location_type=LocationType.objects.get(name="Region"))
                ),
                1,
            )

            # For each region, a new location of LocationType "Region" is created
            for i in range(10):
                self.assertEquals(
                    len(
                        Location.objects.filter(
                            name=f"Test Region {i}", location_type=LocationType.objects.get(name="Region")
                        )
                    ),
                    1,
                )
            # For each site, a new location of LocationType "Site" is created and its parent, if not None, is
            # mapped to a Region LocationType location with the same name as its assigned Region.
            for i in range(10):
                site_locations = Location.objects.filter(
                    name=f"Test Site {i}", location_type=LocationType.objects.get(name="Site")
                )
                old_site = Site.objects.get(name=f"Test Site {i}")
                self.assertEquals(len(site_locations), 1)
                if old_site.region:
                    self.assertEquals(site_locations.first().parent.name, old_site.region.name)

            # Check that top level locations have Site locations as their parent, and they are matching up correctly
            old_top_level_locations = Location.objects.filter(site__isnull=False)
            for location in old_top_level_locations:
                self.assertEquals(location.parent.name, location.site.name)

        with self.subTest("Testing Circuits app model migration"):
            CircuitTermination = self.apps.get_model("circuits", "circuittermination")
            cts = CircuitTermination.objects.all().select_related("site", "location")
            for ct in cts:
                self.assertEquals(ct.site.name, ct.location.name)

        with self.subTest("Testing DCIM app model migration"):
            Device = self.apps.get_model("dcim", "device")
            PowerPanel = self.apps.get_model("dcim", "powerpanel")
            RackGroup = self.apps.get_model("dcim", "rackgroup")
            Rack = self.apps.get_model("dcim", "rack")
            device_1 = Device.objects.get(name="Device 1")
            self.assertEquals(device_1.location.name, "Test Location 0")
            device_2 = Device.objects.get(name="Device 2")
            self.assertEquals(device_2.location.name, "Test Location 1")
            device_3 = Device.objects.get(name="Device 3")
            self.assertEquals(device_3.location.name, "Test Site 5")
            self.assertEquals(device_3.location.location_type.name, "Site")
            powerpanel_1 = PowerPanel.objects.get(name="site1-powerpanel1")
            self.assertEquals(powerpanel_1.location.name, "Test Site 1")
            self.assertEquals(powerpanel_1.location.location_type.name, "Site")
            powerpanel_2 = PowerPanel.objects.get(name="site1-powerpanel2")
            self.assertEquals(powerpanel_2.location.name, "Test Site 1")
            self.assertEquals(powerpanel_2.location.location_type.name, "Site")
            powerpanel_3 = PowerPanel.objects.get(name="site1-powerpanel3")
            self.assertEquals(powerpanel_3.location.name, "Test Location 2")
            self.assertEquals(powerpanel_3.location.location_type.name, "Test Location Type 2")
            rackgroup_1 = RackGroup.objects.get(name="Rack Group 1")
            self.assertEquals(rackgroup_1.location.name, "Test Site 1")
            self.assertEquals(rackgroup_1.location.location_type.name, "Site")
            rackgroup_2 = RackGroup.objects.get(name="Rack Group 2")
            self.assertEquals(rackgroup_2.location.name, "Test Site 2")
            self.assertEquals(rackgroup_2.location.location_type.name, "Site")
            rackgroup_3 = RackGroup.objects.get(name="Rack Group 3")
            self.assertEquals(rackgroup_3.location.name, "Test Location 3")
            self.assertEquals(rackgroup_3.location.location_type.name, "Test Location Type 3")
            rack_1 = Rack.objects.get(name="Rack 1")
            self.assertEquals(rack_1.location.name, "Test Site 1")
            self.assertEquals(rack_1.location.location_type.name, "Site")
            rack_2 = Rack.objects.get(name="Rack 2")
            self.assertEquals(rack_2.location.name, "Test Site 2")
            self.assertEquals(rack_2.location.location_type.name, "Site")
            rack_3 = Rack.objects.get(name="Rack 3")
            self.assertEquals(rack_3.location.name, "Test Location 3")
            self.assertEquals(rack_3.location.location_type.name, "Test Location Type 3")

        with self.subTest("Testing Extras app model migration"):
            pass

        with self.subTest("Testing IPAM app model migration"):
            Prefix = self.apps.get_model("ipam", "prefix")
            VLANGroup = self.apps.get_model("ipam", "vlangroup")
            VLAN = self.apps.get_model("ipam", "vlan")
            prefix_1 = Prefix.objects.get(network="1.1.1.0")
            self.assertEquals(prefix_1.location.name, "Test Site 1")
            self.assertEquals(prefix_1.location.location_type.name, "Site")
            prefix_2 = Prefix.objects.get(network="1.1.1.1")
            self.assertEquals(prefix_2.location.name, "Test Site 2")
            self.assertEquals(prefix_2.location.location_type.name, "Site")
            prefix_3 = Prefix.objects.get(network="1.1.1.2")
            self.assertEquals(prefix_3.location.name, "Test Location 2")
            self.assertEquals(prefix_3.location.location_type.name, "Test Location Type 2")
            vlangroup_1 = VLANGroup.objects.get(name="VLAN Group 1")
            self.assertEquals(vlangroup_1.location.name, "Test Site 1")
            self.assertEquals(vlangroup_1.location.location_type.name, "Site")
            vlangroup_2 = VLANGroup.objects.get(name="VLAN Group 2")
            self.assertEquals(vlangroup_2.location.name, "Test Site 2")
            self.assertEquals(vlangroup_2.location.location_type.name, "Site")
            vlangroup_3 = VLANGroup.objects.get(name="VLAN Group 3")
            self.assertEquals(vlangroup_3.location.name, "Test Location 2")
            self.assertEquals(vlangroup_3.location.location_type.name, "Test Location Type 2")
            vlan_1 = VLAN.objects.get(name="VLAN 1")
            self.assertEquals(vlan_1.location.name, "Test Site 1")
            self.assertEquals(vlan_1.location.location_type.name, "Site")
            vlan_2 = VLAN.objects.get(name="VLAN 2")
            self.assertEquals(vlan_2.location.name, "Test Site 2")
            self.assertEquals(vlan_2.location.location_type.name, "Site")
            vlan_3 = VLAN.objects.get(name="VLAN 3")
            self.assertEquals(vlan_3.location.name, "Test Location 2")
            self.assertEquals(vlan_3.location.location_type.name, "Test Location Type 2")

        with self.subTest("Testing Virtualization app model migration"):
            Cluster = self.apps.get_model("virtualization", "cluster")
            clusters = Cluster.objects.filter(name__in=["Cluster 1", "Cluster 2"]).select_related("site", "location")
            for cluster in clusters:
                self.assertEquals(cluster.site.name, cluster.location.name)

            clusters = Cluster.objects.filter(name__in=["Cluster 3", "Cluster 4"]).select_related("site", "location")
            for cluster in clusters:
                self.assertEquals(
                    cluster.location.name,
                    "Test Location 0",
                )
