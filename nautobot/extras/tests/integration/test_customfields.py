from nautobot.utilities.testing.integration import SplinterTestCase


class CustomFieldTestCase(SplinterTestCase):
    """
    Integration tests for the CustomField and CustomFieldChoice models.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def _create_custom_field(self, field_name, field_type, choices=None, call_before_create=None):
        """
        Repeatable method for creating custom fields.

        Args:
            field_name (str):
                Name of the field to create
            field_type (str):
                Type of the field to create (must match valid options)
            choices (list):
                List of custom field choices to create
            call_before_create (callable):
                If set, this will be called before the "Create" button is clicked.
        """

        if choices is None:
            choices = []

        # Navigate to CustomFields list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("Extensibility").click()
        self.browser.links.find_by_partial_text("Custom Fields").click()

        # Click add button
        self.browser.find_by_id("add-button").click()

        # Fill out form
        self.browser.select("type", field_type)
        self.browser.fill("name", field_name)

        # Find the "content_types" dynamic multi-select and type into it.
        # See: https://splinter.readthedocs.io/en/latest/elements-in-the-page.html#interacting-with-forms
        ct = self.browser.find_by_css(".select2-search__field")
        for _ in ct.first.type("dev\n", slowly=True):
            pass

        # Enumerate and set the choices (if any)
        for idx, choice in enumerate(choices):
            self.browser.fill(f"choices-{idx}-value", choice)

        # Do the pre-create stuff
        if callable(call_before_create):
            call_before_create()

        # Click that "Create" button
        self.browser.find_by_text("Create").click()

        # Verify form redirect
        self.assertTrue(self.browser.is_text_present(f"Created custom field {field_name.capitalize()}"))
        self.assertTrue(self.browser.is_text_present("Edit"))

    def test_create_type_select_with_choices(self):
        """Test pass create type=select/multi-select with choices."""
        choices = ["choice1", "choice2"]
        # pass create type=select w/ choices
        self._create_custom_field(field_name="test-select", field_type="select", choices=choices)
        # pass create type=multi-select w/ choices
        self._create_custom_field(field_name="test-multi-select", field_type="multi-select", choices=choices)

    def test_create_type_select_without_choices(self):
        """Test pass create type=select/multi-select without choices."""
        # pass create type=select w/out choices
        self._create_custom_field(field_name="test-select", field_type="select")
        # pass create type=multi-select w/out choices
        self._create_custom_field(field_name="test-multi-select", field_type="multi-select")

    def test_fail_create_invalid_type_with_choices(self):
        """Test fail type!=select with choices."""
        with self.assertRaises(AssertionError):
            self._create_custom_field(field_name="test-text", field_type="text", choices=["bad1"])

        # Assert error state
        self.assertTrue(self.browser.is_text_present("Editing custom field"))
        self.assertTrue(self.browser.is_text_present("Errors encountered when saving custom field choices"))
        self.assertTrue(self.browser.is_text_present("Custom field choices can only be assigned to selection fields"))

    def test_create_type_select_with_choices_adding_dynamic_row(self):
        """Test pass create type=select adding w/ dynamic row."""
        choices = ["choice1", "choice2"]

        def call_before_create():
            """Do this stuff before "Create" button is clicked."""
            table = self.browser.find_by_id("custom-field-choices")

            # Assert that there are 5 choice rows before
            self.assertEquals(len(table.find_by_css(".formset_row-choices")), 5)

            # And 6 after clicking "Add another..."
            self.browser.find_by_css(".add-row").click()
            rows = table.find_by_css(".formset_row-choices")
            self.assertEquals(len(rows), 6)
            self.browser.fill("choices-5-value", "choice3")

            # Make sure it the new row has default values while we're at it.
            self.assertEquals(rows.last.find_by_name("choices-5-weight").value, "100")

        self._create_custom_field(
            field_name="test-select", field_type="select", choices=choices, call_before_create=call_before_create
        )

    def test_update_type_select_with_choices_editing_existing_choice(self):
        """Test edit of existing field and existing choices."""
        choices = ["replace_me"]

        # Create the field
        self._create_custom_field(field_name="test-select", field_type="select", choices=choices)
        detail_url = self.browser.url

        #
        # Fail editing dynamic row (nullify value of existing choice)
        #

        # Edit it
        self.browser.find_by_id("edit-button").click()
        self.assertIn("edit", self.browser.url)

        # Null out the first choice, click "Update", expect it to fail.
        self.browser.fill("choices-0-value", "")
        self.assertEquals(self.browser.find_by_name("choices-0-value").value, "")
        self.browser.find_by_text("Update").click()
        self.assertTrue(self.browser.is_text_present("Errors encountered when saving custom field choices"))

        #
        # Pass updating existing choice (changing value of existing choice)
        #

        # Fix it, save it, assert correctness.
        self.browser.fill("choices-0-value", "new_choice")
        self.browser.find_by_text("Update").click()
        self.assertEquals(self.browser.url, detail_url)
        self.assertTrue(self.browser.is_text_present("Modified custom field"))
        self.assertTrue(self.browser.is_text_present("new_choice"))

    def test_update_type_select_create_delete_choices(self):
        """
        Test edit existing field, deleting first choice, adding a new row and
        saving that as a new choice.
        """
        # pass edit type=select create/delete row @ same time
        choices = ["delete_me"]

        # Create the field and then click the "Edit" button
        self._create_custom_field(field_name="test-select", field_type="select", choices=choices)
        detail_url = self.browser.url
        self.browser.find_by_id("edit-button").click()

        # Gather the rows, delete the first one, add a new one.
        table = self.browser.find_by_id("custom-field-choices")
        self.browser.find_by_css(".add-row").click()  # Add a new row
        rows = table.find_by_css(".formset_row-choices")
        rows.first.find_by_css(".delete-row").click()  # Delete first row

        # Fill the new row, save it, assert correctness.
        self.browser.fill("choices-5-value", "new_choice")  # Fill the last row
        self.browser.find_by_text("Update").click()
        self.assertEquals(self.browser.url, detail_url)
        self.assertTrue(self.browser.is_text_present("Modified custom field"))
        self.assertTrue(self.browser.is_text_present("new_choice"))
