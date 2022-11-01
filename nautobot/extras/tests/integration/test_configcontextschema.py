from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import ConfigContext, ConfigContextSchema, Status
from nautobot.utilities.testing.integration import SeleniumTestCase
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


class ConfigContextSchemaTestCase(SeleniumTestCase):
    """
    Integration tests for the ConfigContextSchema model
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_create_valid_config_context_schema(self):
        """
        Given a clean slate, navigate to and fill out the form for a valid schema object
        Assert the object is successfully created
        And the user is redirected to the detail page for the new object
        """
        # Navigate to ConfigContextSchema list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("Extensibility").click()
        self.browser.links.find_by_partial_text("Config Context Schemas").click()

        # Click add button
        # Need to be a bit clever in our search here to avoid accidentally hitting "IP Addresses -> Add" in the nav
        self.browser.find_by_xpath("//div[contains(@class, 'wrapper')]//a[contains(., 'Add')]").click()

        # Fill out form
        self.browser.fill("name", "Integration Schema 1")
        self.browser.fill("description", "Description")
        self.browser.fill("data_schema", '{"type": "object", "properties": {"a": {"type": "string"}}}')
        self.browser.find_by_text("Create").click()

        # Verify form redirect
        self.assertTrue(self.browser.is_text_present("Created config context schema Integration Schema 1"))
        self.assertTrue(self.browser.is_text_present("Edit"))

    def test_create_invalid_config_context_schema(self):
        """
        Given a clean slate, navigate to and fill out the form for an invalid schema object
        Provide normal details and an invalid JSON schema
        Assert a validation error is raised
        And the user is returned to the form
        And the error details are listed
        And the form is populated with the user's previous input
        """
        # Navigate to ConfigContextSchema list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("Extensibility").click()
        self.browser.links.find_by_partial_text("Config Context Schemas").click()

        # Click add button
        # Need to be a bit clever in our search here to avoid accidentally hitting "IP Addresses -> Add" in the nav
        self.browser.find_by_xpath("//div[contains(@class, 'wrapper')]//a[contains(., 'Add')]").click()

        # Fill out form
        self.browser.fill("name", "Integration Schema 2")
        self.browser.fill("description", "Description")
        self.browser.fill("data_schema", '{"type": "object", "properties": {"a": {"type": "not a valid type"}}}')
        self.browser.find_by_text("Create").click()

        # Verify validation error raised to user within form
        self.assertTrue(self.browser.is_text_present("'not a valid type' is not valid under any of the given schemas"))
        self.assertTrue(self.browser.is_text_present("Add a new config context schema"))
        self.assertEqual(self.browser.find_by_name("name").first.value, "Integration Schema 2")

    def test_validation_tab(self):
        """
        Given a config context schema that is assigned to a config context, and device, and a VM with valid context data

        Navigate to the Validation tab
        Assert all three objects have a green checkmark in the `Validation state` column
        Then navigate to the schema edit view and modify the schema
        Then navigate back to the Validation tab
        Assert all three objects have a red x in the `Validation state` column with an error message
        Then click on the edit button on the device record
        And update the device's local context data to be valid for the schema and click Update
        Asset the device record has green checkmark in the `Validation state` column and all other still have a red x
        """
        context_data = {"a": 123, "b": 456, "c": 777}

        # Schemas
        schema = ConfigContextSchema.objects.create(
            name="schema",
            slug="schema",
            data_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}, "c": {"type": "integer"}},
            },
        )

        # ConfigContext
        ConfigContext.objects.create(name="context 1", weight=101, data=context_data, schema=schema)

        # Device
        site = Site.objects.create(name="site", slug="site", status=Status.objects.get_for_model(Site).first())
        manufacturer = Manufacturer.objects.create(name="manufacturer", slug="manufacturer")
        device_type = DeviceType.objects.create(model="device_type", manufacturer=manufacturer)
        device_role = DeviceRole.objects.create(name="device_role", slug="device-role", color="ffffff")
        Device.objects.create(
            name="device",
            site=site,
            device_type=device_type,
            device_role=device_role,
            status=Status.objects.get_for_model(Device).first(),
            local_context_data=context_data,
            local_context_schema=schema,
        )

        # Virtual Machine
        cluster_type = ClusterType.objects.create(name="cluster_type", slug="cluster-type")
        cluster = Cluster.objects.create(name="cluster", type=cluster_type)
        VirtualMachine.objects.create(
            name="virtual_machine",
            cluster=cluster,
            status=Status.objects.get_for_model(VirtualMachine).first(),
            local_context_data=context_data,
            local_context_schema=schema,
        )

        # Navigate to ConfigContextSchema Validation tab
        self.browser.visit(f"{self.live_server_url}/extras/config-context-schemas/{schema.slug}/")
        self.browser.links.find_by_text("Validation").click()

        # Assert Validation states
        self.assertEqual(
            len(self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")), 3
        )  # 3 rows (config context, device, virtual machine)
        for row in self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr"):
            self.assertEqual(
                row.find_by_tag("td")[-2].html,
                '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>',
            )

        # Edit the schema
        self.browser.links.find_by_partial_text("Edit").click()
        # Change property "a" to be type string
        self.browser.fill(
            "data_schema",
            '{"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "integer"}, "c": {"type": "integer"}}, "additionalProperties": false}',
        )
        self.browser.find_by_text("Update").click()

        # Navigate to ConfigContextSchema Validation tab
        self.browser.links.find_by_text("Validation").click()

        # Assert Validation states
        self.assertEqual(
            len(self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")), 3
        )  # 3 rows (config context, device, virtual machine)
        for row in self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr"):
            self.assertEqual(
                row.find_by_tag("td")[-2].html,
                '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span><span class="text-danger">123 is not of type \'string\'</span>',
            )

        # Edit the device local context data and redirect back to the validation tab
        self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")[1].find_by_tag("td")[
            -1
        ].find_by_tag("a").click()
        # Update the property "a" to be a string
        self.browser.fill("local_context_data", '{"a": "foo", "b": 456, "c": 777}')
        self.browser.find_by_text("Update").click()

        # Assert Validation states
        self.assertEqual(
            len(self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")), 3
        )  # 3 rows (config context, device, virtual machine)
        # Config context still fails
        self.assertEqual(
            self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")[0].find_by_tag("td")[-2].html,
            '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span><span class="text-danger">123 is not of type \'string\'</span>',
        )
        # Device now passes
        self.assertEqual(
            self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")[1].find_by_tag("td")[-2].html,
            '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>',
        )
        # Virtual machine still fails
        self.assertEqual(
            self.browser.find_by_xpath("//div[@class[contains(., 'panel')]]//tbody/tr")[2].find_by_tag("td")[-2].html,
            '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span><span class="text-danger">123 is not of type \'string\'</span>',
        )
