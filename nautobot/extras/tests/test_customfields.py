import time

import django_rq
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status

from nautobot.dcim.filters import SiteFilterSet
from nautobot.dcim.forms import SiteCSVForm
from nautobot.dcim.models import Site, Rack
from nautobot.extras.choices import *
from nautobot.extras.models import CustomField, CustomFieldChoice, Status
from nautobot.utilities.testing import APITestCase, TestCase
from nautobot.virtualization.models import VirtualMachine


class CustomFieldTest(TestCase):
    def setUp(self):

        Site.objects.create(name="Site A", slug="site-a")
        Site.objects.create(name="Site B", slug="site-b")
        Site.objects.create(name="Site C", slug="site-c")

    def test_simple_fields(self):
        DATA = (
            {
                "field_type": CustomFieldTypeChoices.TYPE_TEXT,
                "field_value": "Foobar!",
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_value": 0,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_value": 42,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_value": True,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_value": False,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_DATE,
                "field_value": "2016-06-23",
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_URL,
                "field_value": "http://example.com/",
                "empty_value": "",
            },
        )

        obj_type = ContentType.objects.get_for_model(Site)

        for data in DATA:

            # Create a custom field
            cf = CustomField(type=data["field_type"], name="my_field", required=False)
            cf.save()
            cf.content_types.set([obj_type])

            # Assign a value to the first Site
            site = Site.objects.first()
            site.cf[cf.name] = data["field_value"]
            site.save()

            # Retrieve the stored value
            site.refresh_from_db()
            self.assertEqual(site.cf[cf.name], data["field_value"])

            # Delete the stored value
            site.cf.pop(cf.name)
            site.save()
            site.refresh_from_db()
            self.assertIsNone(site.cf.get(cf.name))

            # Delete the custom field
            cf.delete()

    def test_select_field(self):
        obj_type = ContentType.objects.get_for_model(Site)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name="my_field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(field=cf, value="Option A")
        CustomFieldChoice.objects.create(field=cf, value="Option B")
        CustomFieldChoice.objects.create(field=cf, value="Option C")

        # Assign a value to the first Site
        site = Site.objects.first()
        site.cf[cf.name] = "Option A"
        site.save()

        # Retrieve the stored value
        site.refresh_from_db()
        self.assertEqual(site.cf[cf.name], "Option A")

        # Delete the stored value
        site.cf.pop(cf.name)
        site.save()
        site.refresh_from_db()
        self.assertIsNone(site.cf.get(cf.name))

        # Delete the custom field
        cf.delete()

    def test_multi_select_field(self):
        obj_type = ContentType.objects.get_for_model(Site)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            name="my_field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(field=cf, value="Option A")
        CustomFieldChoice.objects.create(field=cf, value="Option B")
        CustomFieldChoice.objects.create(field=cf, value="Option C")

        # Assign a value to the first Site
        site = Site.objects.first()
        site.cf[cf.name] = ["Option A", "Option B"]
        site.save()

        # Retrieve the stored value
        site.refresh_from_db()
        self.assertEqual(site.cf[cf.name], ["Option A", "Option B"])

        # Delete the stored value
        site.cf.pop(cf.name)
        site.save()
        site.refresh_from_db()
        self.assertIsNone(site.cf.get(cf.name))

        # Delete the custom field
        cf.delete()


class CustomFieldManagerTest(TestCase):
    def setUp(self):
        content_type = ContentType.objects.get_for_model(Site)
        custom_field = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="text_field", default="foo")
        custom_field.save()
        custom_field.content_types.set([content_type])

    def test_get_for_model(self):
        self.assertEqual(CustomField.objects.get_for_model(Site).count(), 1)
        self.assertEqual(CustomField.objects.get_for_model(VirtualMachine).count(), 0)


class CustomFieldAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Site)

        # Text custom field
        cls.cf_text = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="text_field", default="foo")
        cls.cf_text.save()
        cls.cf_text.content_types.set([content_type])

        # Integer custom field
        cls.cf_integer = CustomField(type=CustomFieldTypeChoices.TYPE_INTEGER, name="number_field", default=123)
        cls.cf_integer.save()
        cls.cf_integer.content_types.set([content_type])

        # Boolean custom field
        cls.cf_boolean = CustomField(
            type=CustomFieldTypeChoices.TYPE_BOOLEAN,
            name="boolean_field",
            default=False,
        )
        cls.cf_boolean.save()
        cls.cf_boolean.content_types.set([content_type])

        # Date custom field
        cls.cf_date = CustomField(
            type=CustomFieldTypeChoices.TYPE_DATE,
            name="date_field",
            default="2020-01-01",
        )
        cls.cf_date.save()
        cls.cf_date.content_types.set([content_type])

        # URL custom field
        cls.cf_url = CustomField(
            type=CustomFieldTypeChoices.TYPE_URL,
            name="url_field",
            default="http://example.com/1",
        )
        cls.cf_url.save()
        cls.cf_url.content_types.set([content_type])

        # Select custom field
        cls.cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name="choice_field",
        )
        cls.cf_select.save()
        cls.cf_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(field=cls.cf_select, value="Foo")
        CustomFieldChoice.objects.create(field=cls.cf_select, value="Bar")
        CustomFieldChoice.objects.create(field=cls.cf_select, value="Baz")
        cls.cf_select.default = "Foo"
        cls.cf_select.save()

        # Multi-select custom field
        cls.cf_multi_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            name="multi_choice_field",
        )
        cls.cf_multi_select.save()
        cls.cf_multi_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(field=cls.cf_multi_select, value="Foo")
        CustomFieldChoice.objects.create(field=cls.cf_multi_select, value="Bar")
        CustomFieldChoice.objects.create(field=cls.cf_multi_select, value="Baz")
        cls.cf_multi_select.default = ["Foo", "Bar"]
        cls.cf_multi_select.save()

        statuses = Status.objects.get_for_model(Site)

        # Create some sites
        cls.sites = (
            Site.objects.create(name="Site 1", slug="site-1", status=statuses.get(slug="active")),
            Site.objects.create(name="Site 2", slug="site-2", status=statuses.get(slug="active")),
        )

        # Assign custom field values for site 2
        cls.sites[1]._custom_field_data = {
            cls.cf_text.name: "bar",
            cls.cf_integer.name: 456,
            cls.cf_boolean.name: True,
            cls.cf_date.name: "2020-01-02",
            cls.cf_url.name: "http://example.com/2",
            cls.cf_select.name: "Bar",
            cls.cf_multi_select.name: ["Bar", "Baz"],
        }
        cls.sites[1].save()

    def test_get_single_object_without_custom_field_data(self):
        """
        Validate that custom fields are present on an object even if it has no values defined.
        """
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[0].pk})
        self.add_permissions("dcim.view_site")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["name"], self.sites[0].name)
        self.assertEqual(
            response.data["custom_fields"],
            {
                "text_field": None,
                "number_field": None,
                "boolean_field": None,
                "date_field": None,
                "url_field": None,
                "choice_field": None,
                "multi_choice_field": None,
            },
        )

    def test_get_single_object_with_custom_field_data(self):
        """
        Validate that custom fields are present and correctly set for an object with values defined.
        """
        site2_cfvs = self.sites[1].cf
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[1].pk})
        self.add_permissions("dcim.view_site")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["name"], self.sites[1].name)
        self.assertEqual(response.data["custom_fields"]["text_field"], site2_cfvs["text_field"])
        self.assertEqual(response.data["custom_fields"]["number_field"], site2_cfvs["number_field"])
        self.assertEqual(response.data["custom_fields"]["boolean_field"], site2_cfvs["boolean_field"])
        self.assertEqual(response.data["custom_fields"]["date_field"], site2_cfvs["date_field"])
        self.assertEqual(response.data["custom_fields"]["url_field"], site2_cfvs["url_field"])
        self.assertEqual(response.data["custom_fields"]["choice_field"], site2_cfvs["choice_field"])
        self.assertEqual(response.data["custom_fields"]["multi_choice_field"], site2_cfvs["multi_choice_field"])

    def test_create_single_object_with_defaults(self):
        """
        Create a new site with no specified custom field values and check that it received the default values.
        """
        data = {
            "name": "Site 3",
            "slug": "site-3",
            "status": "active",
        }
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data["custom_fields"]
        self.assertEqual(response_cf["text_field"], self.cf_text.default)
        self.assertEqual(response_cf["number_field"], self.cf_integer.default)
        self.assertEqual(response_cf["boolean_field"], self.cf_boolean.default)
        self.assertEqual(response_cf["date_field"], self.cf_date.default)
        self.assertEqual(response_cf["url_field"], self.cf_url.default)
        self.assertEqual(response_cf["choice_field"], self.cf_select.default)
        self.assertEqual(response_cf["multi_choice_field"], self.cf_multi_select.default)

        # Validate database data
        site = Site.objects.get(pk=response.data["id"])
        self.assertEqual(site.cf["text_field"], self.cf_text.default)
        self.assertEqual(site.cf["number_field"], self.cf_integer.default)
        self.assertEqual(site.cf["boolean_field"], self.cf_boolean.default)
        self.assertEqual(str(site.cf["date_field"]), self.cf_date.default)
        self.assertEqual(site.cf["url_field"], self.cf_url.default)
        self.assertEqual(site.cf["choice_field"], self.cf_select.default)
        self.assertEqual(site.cf["multi_choice_field"], self.cf_multi_select.default)

    def test_create_single_object_with_values(self):
        """
        Create a single new site with a value for each type of custom field.
        """
        data = {
            "name": "Site 3",
            "slug": "site-3",
            "status": "active",
            "custom_fields": {
                "text_field": "bar",
                "number_field": 456,
                "boolean_field": True,
                "date_field": "2020-01-02",
                "url_field": "http://example.com/2",
                "choice_field": "Bar",
                "multi_choice_field": ["Baz"],
            },
        }
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data["custom_fields"]
        data_cf = data["custom_fields"]
        self.assertEqual(response_cf["text_field"], data_cf["text_field"])
        self.assertEqual(response_cf["number_field"], data_cf["number_field"])
        self.assertEqual(response_cf["boolean_field"], data_cf["boolean_field"])
        self.assertEqual(response_cf["date_field"], data_cf["date_field"])
        self.assertEqual(response_cf["url_field"], data_cf["url_field"])
        self.assertEqual(response_cf["choice_field"], data_cf["choice_field"])
        self.assertEqual(response_cf["multi_choice_field"], data_cf["multi_choice_field"])

        # Validate database data
        site = Site.objects.get(pk=response.data["id"])
        self.assertEqual(site.cf["text_field"], data_cf["text_field"])
        self.assertEqual(site.cf["number_field"], data_cf["number_field"])
        self.assertEqual(site.cf["boolean_field"], data_cf["boolean_field"])
        self.assertEqual(str(site.cf["date_field"]), data_cf["date_field"])
        self.assertEqual(site.cf["url_field"], data_cf["url_field"])
        self.assertEqual(site.cf["choice_field"], data_cf["choice_field"])
        self.assertEqual(site.cf["multi_choice_field"], data_cf["multi_choice_field"])

    def test_create_multiple_objects_with_defaults(self):
        """
        Create three news sites with no specified custom field values and check that each received
        the default custom field values.
        """
        data = (
            {
                "name": "Site 3",
                "slug": "site-3",
                "status": "active",
            },
            {
                "name": "Site 4",
                "slug": "site-4",
                "status": "active",
            },
            {
                "name": "Site 5",
                "slug": "site-5",
                "status": "active",
            },
        )
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, obj in enumerate(data):

            # Validate response data
            response_cf = response.data[i]["custom_fields"]
            self.assertEqual(response_cf["text_field"], self.cf_text.default)
            self.assertEqual(response_cf["number_field"], self.cf_integer.default)
            self.assertEqual(response_cf["boolean_field"], self.cf_boolean.default)
            self.assertEqual(response_cf["date_field"], self.cf_date.default)
            self.assertEqual(response_cf["url_field"], self.cf_url.default)
            self.assertEqual(response_cf["choice_field"], self.cf_select.default)
            self.assertEqual(response_cf["multi_choice_field"], self.cf_multi_select.default)

            # Validate database data
            site = Site.objects.get(pk=response.data[i]["id"])
            self.assertEqual(site.cf["text_field"], self.cf_text.default)
            self.assertEqual(site.cf["number_field"], self.cf_integer.default)
            self.assertEqual(site.cf["boolean_field"], self.cf_boolean.default)
            self.assertEqual(str(site.cf["date_field"]), self.cf_date.default)
            self.assertEqual(site.cf["url_field"], self.cf_url.default)
            self.assertEqual(site.cf["choice_field"], self.cf_select.default)
            self.assertEqual(site.cf["multi_choice_field"], self.cf_multi_select.default)

    def test_create_multiple_objects_with_values(self):
        """
        Create a three new sites, each with custom fields defined.
        """
        custom_field_data = {
            "text_field": "bar",
            "number_field": 456,
            "boolean_field": True,
            "date_field": "2020-01-02",
            "url_field": "http://example.com/2",
            "choice_field": "Bar",
            "multi_choice_field": ["Foo", "Bar"],
        }
        data = (
            {
                "name": "Site 3",
                "slug": "site-3",
                "status": "active",
                "custom_fields": custom_field_data,
            },
            {
                "name": "Site 4",
                "slug": "site-4",
                "status": "active",
                "custom_fields": custom_field_data,
            },
            {
                "name": "Site 5",
                "slug": "site-5",
                "status": "active",
                "custom_fields": custom_field_data,
            },
        )
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, obj in enumerate(data):

            # Validate response data
            response_cf = response.data[i]["custom_fields"]
            self.assertEqual(response_cf["text_field"], custom_field_data["text_field"])
            self.assertEqual(response_cf["number_field"], custom_field_data["number_field"])
            self.assertEqual(response_cf["boolean_field"], custom_field_data["boolean_field"])
            self.assertEqual(response_cf["date_field"], custom_field_data["date_field"])
            self.assertEqual(response_cf["url_field"], custom_field_data["url_field"])
            self.assertEqual(response_cf["choice_field"], custom_field_data["choice_field"])
            self.assertEqual(response_cf["multi_choice_field"], custom_field_data["multi_choice_field"])

            # Validate database data
            site = Site.objects.get(pk=response.data[i]["id"])
            self.assertEqual(site.cf["text_field"], custom_field_data["text_field"])
            self.assertEqual(
                site.cf["number_field"],
                custom_field_data["number_field"],
            )
            self.assertEqual(
                site.cf["boolean_field"],
                custom_field_data["boolean_field"],
            )
            self.assertEqual(
                str(site.cf["date_field"]),
                custom_field_data["date_field"],
            )
            self.assertEqual(site.cf["url_field"], custom_field_data["url_field"])
            self.assertEqual(
                site.cf["choice_field"],
                custom_field_data["choice_field"],
            )
            self.assertEqual(
                site.cf["multi_choice_field"],
                custom_field_data["multi_choice_field"],
            )

    def test_update_single_object_with_values(self):
        """
        Update an object with existing custom field values. Ensure that only the updated custom field values are
        modified.
        """
        site = self.sites[1]
        original_cfvs = {**site.cf}
        data = {
            "custom_fields": {
                "text_field": "ABCD",
                "number_field": 1234,
            },
        }
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[1].pk})
        self.add_permissions("dcim.change_site")

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        # Validate response data
        response_cf = response.data["custom_fields"]
        self.assertEqual(response_cf["text_field"], data["custom_fields"]["text_field"])
        self.assertEqual(response_cf["number_field"], data["custom_fields"]["number_field"])
        self.assertEqual(response_cf["boolean_field"], original_cfvs["boolean_field"])
        self.assertEqual(response_cf["date_field"], original_cfvs["date_field"])
        self.assertEqual(response_cf["url_field"], original_cfvs["url_field"])
        self.assertEqual(response_cf["choice_field"], original_cfvs["choice_field"])
        self.assertEqual(response_cf["multi_choice_field"], original_cfvs["multi_choice_field"])

        # Validate database data
        site.refresh_from_db()
        self.assertEqual(site.cf["text_field"], data["custom_fields"]["text_field"])
        self.assertEqual(
            site.cf["number_field"],
            data["custom_fields"]["number_field"],
        )
        self.assertEqual(site.cf["boolean_field"], original_cfvs["boolean_field"])
        self.assertEqual(site.cf["date_field"], original_cfvs["date_field"])
        self.assertEqual(site.cf["url_field"], original_cfvs["url_field"])
        self.assertEqual(site.cf["choice_field"], original_cfvs["choice_field"])
        self.assertEqual(site.cf["multi_choice_field"], original_cfvs["multi_choice_field"])

    def test_minimum_maximum_values_validation(self):
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[1].pk})
        self.add_permissions("dcim.change_site")

        self.cf_integer.validation_minimum = 10
        self.cf_integer.validation_maximum = 20
        self.cf_integer.save()

        data = {"custom_fields": {"number_field": 9}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"number_field": 21}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"number_field": 15}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_regex_validation(self):
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[1].pk})
        self.add_permissions("dcim.change_site")

        self.cf_text.validation_regex = r"^[A-Z]{3}$"  # Three uppercase letters
        self.cf_text.save()

        data = {"custom_fields": {"text_field": "ABC123"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"text_field": "abc"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"text_field": "ABC"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)


class CustomFieldImportTest(TestCase):
    user_permissions = (
        "dcim.view_site",
        "dcim.add_site",
        "extras.view_status",
    )

    @classmethod
    def setUpTestData(cls):

        custom_fields = (
            CustomField(name="text", type=CustomFieldTypeChoices.TYPE_TEXT),
            CustomField(name="integer", type=CustomFieldTypeChoices.TYPE_INTEGER),
            CustomField(name="boolean", type=CustomFieldTypeChoices.TYPE_BOOLEAN),
            CustomField(name="date", type=CustomFieldTypeChoices.TYPE_DATE),
            CustomField(name="url", type=CustomFieldTypeChoices.TYPE_URL),
            CustomField(
                name="select",
                type=CustomFieldTypeChoices.TYPE_SELECT,
            ),
            CustomField(
                name="multiselect",
                type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            ),
        )
        for cf in custom_fields:
            cf.save()
            cf.content_types.set([ContentType.objects.get_for_model(Site)])

        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="select"), value="Choice A")
        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="select"), value="Choice B")
        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="select"), value="Choice C")
        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="multiselect"), value="Choice A")
        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="multiselect"), value="Choice B")
        CustomFieldChoice.objects.create(field=CustomField.objects.get(name="multiselect"), value="Choice C")

    def test_import(self):
        """
        Import a Site in CSV format, including a value for each CustomField.
        """
        data = (
            (
                "name",
                "slug",
                "status",
                "cf_text",
                "cf_integer",
                "cf_boolean",
                "cf_date",
                "cf_url",
                "cf_select",
                "cf_multiselect",
            ),
            (
                "Site 1",
                "site-1",
                "active",
                "ABC",
                "123",
                "True",
                "2020-01-01",
                "http://example.com/1",
                "Choice A",
                "Choice A",
            ),
            (
                "Site 2",
                "site-2",
                "active",
                "DEF",
                "456",
                "False",
                "2020-01-02",
                "http://example.com/2",
                "Choice B",
                '"Choice A,Choice B"',
            ),
            ("Site 3", "site-3", "active", "", "", "", "", "", "", ""),
        )
        csv_data = "\n".join(",".join(row) for row in data)

        response = self.client.post(reverse("dcim:site_import"), {"csv": csv_data})
        self.assertEqual(response.status_code, 200)

        # Validate data for site 1
        site1 = Site.objects.get(name="Site 1")
        self.assertEqual(len(site1.cf), 7)
        self.assertEqual(site1.cf["text"], "ABC")
        self.assertEqual(site1.cf["integer"], 123)
        self.assertEqual(site1.cf["boolean"], True)
        self.assertEqual(site1.cf["date"], "2020-01-01")
        self.assertEqual(site1.cf["url"], "http://example.com/1")
        self.assertEqual(site1.cf["select"], "Choice A")
        self.assertEqual(site1.cf["multiselect"], ["Choice A"])

        # Validate data for site 2
        site2 = Site.objects.get(name="Site 2")
        self.assertEqual(len(site2.cf), 7)
        self.assertEqual(site2.cf["text"], "DEF")
        self.assertEqual(site2.cf["integer"], 456)
        self.assertEqual(site2.cf["boolean"], False)
        self.assertEqual(site2.cf["date"], "2020-01-02")
        self.assertEqual(site2.cf["url"], "http://example.com/2")
        self.assertEqual(site2.cf["select"], "Choice B")
        self.assertEqual(site2.cf["multiselect"], ["Choice A", "Choice B"])

        # No custom field data should be set for site 3
        site3 = Site.objects.get(name="Site 3")
        self.assertFalse(any(site3.cf.values()))

    def test_import_missing_required(self):
        """
        Attempt to import an object missing a required custom field.
        """
        # Set one of our CustomFields to required
        CustomField.objects.filter(name="text").update(required=True)

        form_data = {
            "name": "Site 1",
            "slug": "site-1",
        }

        form = SiteCSVForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("cf_text", form.errors)

    def test_import_invalid_choice(self):
        """
        Attempt to import an object with an invalid choice selection.
        """
        form_data = {"name": "Site 1", "slug": "site-1", "cf_select": "Choice X"}

        form = SiteCSVForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("cf_select", form.errors)


class CustomFieldModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cf1 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="foo")
        cf1.save()
        cf1.content_types.set([ContentType.objects.get_for_model(Site)])

        cf2 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="bar")
        cf2.save()
        cf2.content_types.set([ContentType.objects.get_for_model(Rack)])

    def test_cf_data(self):
        """
        Check that custom field data is present on the instance immediately after being set and after being fetched
        from the database.
        """
        site = Site(name="Test Site", slug="test-site")

        # Check custom field data on new instance
        site.cf["foo"] = "abc"
        self.assertEqual(site.cf["foo"], "abc")

        # Check custom field data from database
        site.save()
        site = Site.objects.get(name="Test Site")
        self.assertEqual(site.cf["foo"], "abc")

    def test_invalid_data(self):
        """
        Setting custom field data for a non-applicable (or non-existent) CustomField should raise a ValidationError.
        """
        site = Site(name="Test Site", slug="test-site")

        # Set custom field data
        site.cf["foo"] = "abc"
        site.cf["bar"] = "def"
        with self.assertRaises(ValidationError):
            site.clean()

        del site.cf["bar"]
        site.clean()

    def test_missing_required_field(self):
        """
        Check that a ValidationError is raised if any required custom fields are not present.
        """
        cf3 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="baz", required=True)
        cf3.save()
        cf3.content_types.set([ContentType.objects.get_for_model(Site)])

        site = Site(name="Test Site", slug="test-site")

        # Set custom field data with a required field omitted
        site.cf["foo"] = "abc"
        with self.assertRaises(ValidationError):
            site.clean()

        site.cf["baz"] = "def"
        site.clean()


class CustomFieldFilterTest(TestCase):
    queryset = Site.objects.all()
    filterset = SiteFilterSet

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        # Integer filtering
        cf = CustomField(name="cf1", type=CustomFieldTypeChoices.TYPE_INTEGER)
        cf.save()
        cf.content_types.set([obj_type])

        # Boolean filtering
        cf = CustomField(name="cf2", type=CustomFieldTypeChoices.TYPE_BOOLEAN)
        cf.save()
        cf.content_types.set([obj_type])

        # Exact text filtering
        cf = CustomField(
            name="cf3",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Loose text filtering
        cf = CustomField(
            name="cf4",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Date filtering
        cf = CustomField(name="cf5", type=CustomFieldTypeChoices.TYPE_DATE)
        cf.save()
        cf.content_types.set([obj_type])

        # Exact URL filtering
        cf = CustomField(
            name="cf6",
            type=CustomFieldTypeChoices.TYPE_URL,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Loose URL filtering
        cf = CustomField(
            name="cf7",
            type=CustomFieldTypeChoices.TYPE_URL,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Selection filtering
        cf = CustomField(
            name="cf8",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(field=cf, value="Foo")
        CustomFieldChoice.objects.create(field=cf, value="Bar")

        # Multi-select filtering
        cf = CustomField(
            name="cf9",
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(field=cf, value="Foo")
        CustomFieldChoice.objects.create(field=cf, value="Bar")

        Site.objects.create(
            name="Site 1",
            slug="site-1",
            _custom_field_data={
                "cf1": 100,
                "cf2": True,
                "cf3": "foo",
                "cf4": "foo",
                "cf5": "2016-06-26",
                "cf6": "http://foo.example.com/",
                "cf7": "http://foo.example.com/",
                "cf8": "Foo",
                "cf9": [],
            },
        )
        Site.objects.create(
            name="Site 2",
            slug="site-2",
            _custom_field_data={
                "cf1": 200,
                "cf2": False,
                "cf3": "foobar",
                "cf4": "foobar",
                "cf5": "2016-06-27",
                "cf6": "http://bar.example.com/",
                "cf7": "http://bar.example.com/",
                "cf8": "Bar",
                "cf9": ["Foo"],
            },
        )
        Site.objects.create(
            name="Site 3",
            slug="site-3",
            _custom_field_data={"cf9": ["Foo", "Bar"]},
        )
        Site.objects.create(name="Site 4", slug="site-4", _custom_field_data={})

    def test_filter_integer(self):
        self.assertEqual(self.filterset({"cf_cf1": 100}, self.queryset).qs.count(), 1)

    def test_filter_boolean(self):
        self.assertEqual(self.filterset({"cf_cf2": True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"cf_cf2": False}, self.queryset).qs.count(), 1)

    def test_filter_text(self):
        self.assertEqual(self.filterset({"cf_cf3": "foo"}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"cf_cf4": "foo"}, self.queryset).qs.count(), 2)

    def test_filter_date(self):
        self.assertEqual(self.filterset({"cf_cf5": "2016-06-26"}, self.queryset).qs.count(), 1)

    def test_filter_url(self):
        self.assertEqual(
            self.filterset({"cf_cf6": "http://foo.example.com/"}, self.queryset).qs.count(),
            1,
        )
        self.assertEqual(self.filterset({"cf_cf7": "example.com"}, self.queryset).qs.count(), 2)

    def test_filter_select(self):
        self.assertEqual(self.filterset({"cf_cf8": "Foo"}, self.queryset).qs.count(), 1)

    def test_filter_multi_select(self):
        self.assertEqual(self.filterset({"cf_cf9": "Foo"}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({"cf_cf9": "Bar"}, self.queryset).qs.count(), 1)


class CustomFieldChoiceTest(TestCase):
    def setUp(self):
        obj_type = ContentType.objects.get_for_model(Site)
        self.cf = CustomField(
            name="cf1",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        self.cf.save()
        self.cf.content_types.set([obj_type])

        self.choice = CustomFieldChoice(field=self.cf, value="Foo")
        self.choice.save()

        self.site = Site(
            name="Site 1",
            slug="site-1",
            _custom_field_data={
                "cf1": "Foo",
            },
        )
        self.site.save()

    def test_default_value_must_be_valid_choice_sad_path(self):
        self.cf.default = "invalid value"
        with self.assertRaises(ValidationError):
            self.cf.full_clean()

    def test_default_value_must_be_valid_choice_happy_path(self):
        self.cf.default = "Foo"
        self.cf.full_clean()
        self.cf.save()
        self.assertEqual(self.cf.default, "Foo")

    def test_active_choice_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.choice.delete()

    def test_custom_choice_deleted_with_field(self):
        self.cf.delete()
        self.assertEqual(CustomField.objects.count(), 0)
        self.assertEqual(CustomFieldChoice.objects.count(), 0)


class CustomFieldBackgroundTasks(TestCase):
    def setUp(self):
        # Clear the queue for each test
        django_rq.get_queue("custom_fields").empty()

    def get_worker(self, queue_name="custom_fields", **kwargs):
        worker = django_rq.get_worker(queue_name, worker_class="rq.worker.SimpleWorker", **kwargs)
        worker.work(burst=True)

    def test_provision_field_task(self):
        site = Site(
            name="Site 1",
            slug="site-1",
        )
        site.save()

        obj_type = ContentType.objects.get_for_model(Site)
        cf = CustomField(name="cf1", type=CustomFieldTypeChoices.TYPE_TEXT, default="Foo")
        cf.save()
        cf.content_types.set([obj_type])

        # Synchronously process all jobs on the queue in this process
        self.get_worker()

        site.refresh_from_db()

        self.assertEqual(site.cf["cf1"], "Foo")

    def test_delete_custom_field_data_task(self):
        obj_type = ContentType.objects.get_for_model(Site)
        cf = CustomField(
            name="cf1",
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Synchronously process all jobs on the queue in this process
        self.get_worker()

        site = Site(name="Site 1", slug="site-1", _custom_field_data={"cf1": "foo"})
        site.save()

        cf.delete()

        # Synchronously process all jobs on the queue in this process
        self.get_worker()

        site.refresh_from_db()

        self.assertTrue("cf1" not in site.cf)

    def test_update_custom_field_choice_data_task(self):
        obj_type = ContentType.objects.get_for_model(Site)
        cf = CustomField(
            name="cf1",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Synchronously process all jobs on the queue in this process
        self.get_worker()

        choice = CustomFieldChoice(field=cf, value="Foo")
        choice.save()

        site = Site(name="Site 1", slug="site-1", _custom_field_data={"cf1": "Foo"})
        site.save()

        choice.value = "Bar"
        choice.save()

        # Synchronously process all jobs on the queue in this process
        self.get_worker()

        site.refresh_from_db()

        self.assertEqual(site.cf["cf1"], "Bar")
