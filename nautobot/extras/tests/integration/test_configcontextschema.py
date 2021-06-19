from nautobot.utilities.testing.integration import SplinterTestCase


class ConfigContextSchemaTestCase(SplinterTestCase):
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
        self.browser.links.find_by_text("Config Context Schemas").click()

        # Click add add button
        self.browser.find_by_xpath("/html/body/div/div[1]/a").click()

        # Fill out form
        self.browser.fill("name", "Integration Schema 1")
        self.browser.fill("description", "Description")
        self.browser.fill("data_schema", '{"type": "object", "properties": {"a": {"type": "string"}}}')
        self.browser.find_by_text("Create").click()

        # Verify form redirect
        self.assertTrue(self.browser.is_text_present("Created config context schema Integration Schema 1"))
        self.assertTrue(self.browser.is_text_present("Clone"))

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
        self.browser.links.find_by_text("Config Context Schemas").click()

        # Click add add button
        self.browser.find_by_xpath("/html/body/div/div[1]/a").click()

        # Fill out form
        self.browser.fill("name", "Integration Schema 2")
        self.browser.fill("description", "Description")
        self.browser.fill("data_schema", '{"type": "object", "properties": {"a": {"type": "not a valid type"}}}')
        self.browser.find_by_text("Create").click()

        # Verify validation error raised to user within form
        self.assertTrue(self.browser.is_text_present("'not a valid type' is not valid under any of the given schemas"))
        self.assertTrue(self.browser.is_text_present("Add a new config context schema"))
        self.assertEqual(self.browser.find_by_name("name").first.value, "Integration Schema 2")
