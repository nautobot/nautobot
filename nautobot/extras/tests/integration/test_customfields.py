from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from selenium.webdriver.common.keys import Keys

from nautobot.dcim.models import Device
from nautobot.extras.models import CustomField, CustomFieldChoice
from nautobot.utilities.testing.integration import SeleniumTestCase

from . import create_test_device


class CustomFieldTestCase(SeleniumTestCase):
    """
    Integration tests for the CustomField and CustomFieldChoice models.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        self.device = create_test_device()

    def tearDown(self):
        self.logout()
        super().tearDown()

    def _create_custom_field(self, field_label, field_type, choices=None, call_before_create=None):
        """
        Repeatable method for creating custom fields.

        Args:
            field_label (str):
                Label of the field to create
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
        self.browser.fill("label", field_label)
        # Slug field should be auto-populated based on the provided label

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

        # Verify form redirect and presence of choices
        self.assertTrue(self.browser.is_text_present(f"Created custom field {field_label}"))
        self.assertTrue(self.browser.is_text_present("Edit"))
        for choice in choices:
            self.assertTrue(self.browser.is_text_present(choice))

    def test_create_type_select_with_choices(self):
        """Test pass create type=select/multi-select with choices."""
        choices = ["choice1", "choice2"]
        # pass create type=select w/ choices
        self._create_custom_field(field_label="Test Select", field_type="select", choices=choices)
        # pass create type=multi-select w/ choices
        self._create_custom_field(field_label="Test Multi-select", field_type="multi-select", choices=choices)

    def test_create_type_select_without_choices(self):
        """Test pass create type=select/multi-select without choices."""
        # pass create type=select w/out choices
        self._create_custom_field(field_label="Test Select", field_type="select")
        # pass create type=multi-select w/out choices
        self._create_custom_field(field_label="Test Multi-select", field_type="multi-select")

    def test_fail_create_invalid_type_with_choices(self):
        """Test fail type!=select with choices."""
        with self.assertRaises(AssertionError):
            self._create_custom_field(field_label="Test Text", field_type="text", choices=["bad1"])

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
            self.assertEqual(len(table.find_by_css(".formset_row-choices")), 5)

            # And 6 after clicking "Add another..."
            self.browser.find_by_css(".add-row").click()
            rows = table.find_by_css(".formset_row-choices")
            self.assertEqual(len(rows), 6)
            self.browser.fill("choices-5-value", "choice3")

            # Make sure it the new row has default values while we're at it.
            self.assertEqual(rows.last.find_by_name("choices-5-weight").value, "100")

        self._create_custom_field(
            field_label="Test Select", field_type="select", choices=choices, call_before_create=call_before_create
        )

    def test_update_type_select_with_choices_editing_existing_choice(self):
        """Test edit of existing field and existing choices."""
        choices = ["replace_me"]

        # Create the field
        self._create_custom_field(field_label="Test Select", field_type="select", choices=choices)
        detail_url = self.browser.url

        #
        # Fail editing dynamic row (nullify value of existing choice)
        #

        # Edit it
        self.browser.find_by_id("edit-button").click()
        self.assertIn("edit", self.browser.url)

        # Null out the first choice, click "Update", expect it to fail.
        self.browser.fill("choices-0-value", "")
        self.assertEqual(self.browser.find_by_name("choices-0-value").value, "")
        self.browser.find_by_text("Update").click()
        self.assertTrue(self.browser.is_text_present("Errors encountered when saving custom field choices"))

        #
        # Pass updating existing choice (changing value of existing choice)
        #

        # Fix it, save it, assert correctness.
        self.browser.fill("choices-0-value", "new_choice")
        self.browser.find_by_text("Update").click()
        self.assertEqual(self.browser.url, detail_url)
        self.assertTrue(self.browser.is_text_present("Modified custom field"))
        self.assertTrue(self.browser.is_text_present("new_choice"))

    def test_update_type_select_create_delete_choices(self):
        """
        Test edit existing field, deleting first choice, adding a new row and saving that as a new choice.
        """
        # pass edit type=select create/delete row @ same time
        choices = ["delete_me"]

        # Create the field and then click the "Edit" button
        self._create_custom_field(field_label="Test Select", field_type="select", choices=choices)
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
        self.assertEqual(self.browser.url, detail_url)
        self.assertTrue(self.browser.is_text_present("Modified custom field"))
        self.assertTrue(self.browser.is_text_present("new_choice"))

    def test_custom_field_advanced_ui(self):
        """
        This test creates a custom field with a type of "text".

        It first leaves the custom field advanced_ui default of False to be show on the primary information
        tab in the UI and checks it is there.
        It secondly sets the custom field to be shown only in the "Advanced" tab in the UI
        and checks it appears ONLY there!.
        """
        device = self.device
        custom_field = CustomField(
            type="text",
            label="Device Custom Field",
            name="test_custom_field",
            slug="test_custom_field",
            required=False,
        )
        custom_field.save()
        device_content_type = ContentType.objects.get_for_model(Device)
        custom_field.content_types.set([device_content_type])
        # 2.0 TODO: #824 replace custom_field.name with custom_field.slug
        device.cf[custom_field.name] = "This is some testing text"
        device.validated_save()
        # Visit the device detail page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device", kwargs={"pk": device.pk})}')
        # Check the custom field appears in the primary information tab
        self.assertTrue(self.browser.is_text_present("Device Custom Field"))
        self.assertTrue(self.browser.is_text_present("This is some testing text"))
        # Check the custom field does NOT appear in the advanced tab
        self.browser.links.find_by_partial_text("Advanced")[0].click()
        self.assertFalse(self.browser.is_text_present("Device Custom Field"))
        self.assertFalse(self.browser.is_text_present("This is some testing text"))
        # Set the custom_field to only show in the advanced tab
        custom_field.advanced_ui = True
        custom_field.save()
        # Visit the device detail page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device", kwargs={"pk": device.pk})}')
        # Check the custom field does NOT appear in the primary information tab
        self.assertFalse(self.browser.is_text_present("Device Custom Field"))
        self.assertFalse(self.browser.is_text_present("This is some testing text"))
        # Check the custom field appears in the advanced tab
        self.browser.links.find_by_partial_text("Advanced")[0].click()
        self.assertTrue(self.browser.is_text_present("Device Custom Field"))
        self.assertTrue(self.browser.is_text_present("This is some testing text"))

    def test_json_type_with_valid_json(self):
        """
        This test creates a custom field with a type of "json".

        It then edits the value of the custom field by adding valid JSON.
        """
        custom_field = CustomField(
            type="json",
            label="Device Valid JSON Field",
            name="test_valid_json_field",
            slug="test_valid_json_field",
            required=False,
        )
        custom_field.save()
        device_content_type = ContentType.objects.get_for_model(Device)
        custom_field.content_types.set([device_content_type])
        # Visit the device edit page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device_edit", kwargs={"pk": self.device.pk})}')
        self.browser.find_by_id("id_cf_test_valid_json_field").first.type("test")
        active_web_element = self.browser.driver.switch_to.active_element
        # Type invalid JSON data into the form
        active_web_element.send_keys('{"test_json_key": "Test JSON Value"}')
        self.browser.find_by_xpath(".//button[contains(text(), 'Update')]").click()
        self.assertTrue(self.browser.is_text_present("Test Device"))
        # Confirm the JSON data is visible
        self.assertTrue(self.browser.is_text_present("Test JSON Value"))

    def test_json_type_with_invalid_json(self):
        """
        This test creates a custom field with a type of "json".

        It then edits the value of the custom field by adding invalid JSON.
        """
        custom_field = CustomField(
            type="json",
            label="Device Invalid JSON Field",
            name="test_invalid_json_field",
            slug="test_invalid_json_field",
            required=False,
        )
        custom_field.save()
        device_content_type = ContentType.objects.get_for_model(Device)
        custom_field.content_types.set([device_content_type])
        # Visit the device edit page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device_edit", kwargs={"pk": self.device.pk})}')
        self.browser.find_by_id("id_cf_test_invalid_json_field").first.type("test")
        active_web_element = self.browser.driver.switch_to.active_element
        # Type invalid JSON data into the form
        active_web_element.send_keys('{test_json_key: "Test Invalid JSON Value"}')
        self.browser.find_by_xpath(".//button[contains(text(), 'Update')]").click()
        self.assertTrue(self.browser.is_text_present("Enter a valid JSON"))

    def test_saving_object_after_its_custom_field_deleted(self):
        """
        This test creates a custom field with type Selection for the Device content type.

        It then adds a value for the new custom field to self.device.
        It then deletes the custom field.
        It then visits self.object's edit page and clicks the Update button.
        It then checks that page is now on the self.device object's page (without any validation error after updating).
        """
        device = self.device
        custom_field = CustomField(
            type="select",
            label="Device Selection Field",
            name="test_selection_field",
            slug="test_selection_field",
            required=False,
        )
        custom_field.save()
        # Add a choice for the custom field selection
        custom_field_choice = CustomFieldChoice(field=custom_field, value="SelectionChoice")
        custom_field_choice.save()
        # Set content type of custom field
        device_content_type = ContentType.objects.get_for_model(Device)
        custom_field.content_types.set([device_content_type])
        # Visit the device edit page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device_edit", kwargs={"pk": device.pk})}')
        # Get the first item selected on the custom field
        self.browser.find_by_xpath(".//label[contains(text(), 'Device Selection Field')]").click()
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        active_web_element.send_keys(Keys.ENTER)
        # Click update button
        self.browser.find_by_xpath(".//button[contains(text(), 'Update')]").click()
        # Check successful redirect to device object page
        self.assertTrue(self.browser.is_text_present("Modified device"))
        self.assertTrue(self.browser.is_text_present("SelectionChoice"))

        # Delete the custom field
        self.browser.links.find_by_partial_text("Extensibility").click()
        self.browser.links.find_by_partial_text("Custom Fields").click()
        self.browser.links.find_by_partial_text("Device Selection Field").click()
        self.browser.links.find_by_partial_text("Delete").click()
        self.browser.find_by_xpath(".//button[contains(text(), 'Confirm')]").click()

        # Visit the device edit page
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device_edit", kwargs={"pk": device.pk})}')
        # Click update button
        self.browser.find_by_xpath(".//button[contains(text(), 'Update')]").click()
        # Check successful redirect to device object page
        self.assertTrue(self.browser.is_text_present("Modified device"))
        # Check custom field is no longer present
        self.assertFalse(self.browser.is_text_present("SelectionChoice"))
