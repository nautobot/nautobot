"""Embedded create and embedded search on an object create form, driven from the Device form's related fields."""

import pytest

from nautobot.core.tests.integration.pages.device_form_page import DeviceFormPage
from nautobot.core.tests.integration.pages.embedded_modal import EmbeddedModal
from nautobot.playwright.helpers import unique_name

# The option label of the Device content type in content type selects.
DEVICE_CONTENT_TYPE = "DCIM | device"


def open_device_form(auth_page, base_url):
    """Open an empty Device create form and return its embedded-action modal."""
    form = DeviceFormPage(auth_page, base_url)
    form.navigate()
    return EmbeddedModal(form)


def find_one(api, endpoint, **filters):
    """The one API record at *endpoint* matching *filters*."""
    results = api.get(f"/api/{endpoint}", params=filters).json()["results"]
    assert len(results) == 1, f"Expected one record at /api/{endpoint} matching {filters}, found {len(results)}"
    return results[0]


class ObjectEditTestCase:
    """The embedded create and search modals, opened from the related fields of the Device create form."""

    # -------------------------------------------------------------------------
    # Embedded create: the Tenant field
    # -------------------------------------------------------------------------

    def test_embedded_create_opens_an_empty_form(self, auth_page, base_url):
        """The "Add a new tenant" button opens the Tenant create form in the modal, with an empty name."""
        modal = open_device_form(auth_page, base_url)
        modal.open_create("tenant")

        modal.expect_title("Add a new tenant")
        modal.field("name").wait_for()
        assert modal.field("name").input_value() == ""

    @pytest.mark.behavioral
    def test_embedded_create_selects_the_new_object(self, auth_page, base_url, api, create_object):
        """Creating a tenant in the modal saves it, closes the modal and selects it in the Tenant field."""
        name = unique_name()
        create_object.track("tenancy/tenants/", name=name)
        modal = open_device_form(auth_page, base_url)
        modal.open_create("tenant")
        modal.fill("name", name)
        modal.submit_create()

        modal.expect_closed()
        tenant = find_one(api, "tenancy/tenants/", name=name)
        modal.expect_parent_field("tenant", tenant["id"], name)

    @pytest.mark.behavioral
    def test_embedded_create_shows_a_success_message(self, auth_page, base_url, create_object):
        """Creating a tenant in the modal shows the same success message as the full create form."""
        name = unique_name()
        create_object.track("tenancy/tenants/", name=name)
        modal = open_device_form(auth_page, base_url)
        modal.open_create("tenant")
        modal.fill("name", name)
        modal.submit_create()

        modal.form.expect_flash_message(f"Created tenant {name}")

    # -------------------------------------------------------------------------
    # Embedded create with a prefilled content type: the Dynamic groups and Role fields
    # -------------------------------------------------------------------------

    def test_embedded_create_prefills_the_dynamic_group_content_type(self, auth_page, base_url):
        """The "Add a new dynamic group" button opens the form with the Device content type already selected."""
        modal = open_device_form(auth_page, base_url)
        modal.open_create("dynamic group")

        modal.expect_prefilled("content_type", DEVICE_CONTENT_TYPE)

    def test_embedded_create_prefills_the_role_content_types(self, auth_page, base_url):
        """The "Add a new role" button opens the form with only the Device content type selected."""
        modal = open_device_form(auth_page, base_url)
        modal.open_create("role")

        modal.expect_prefilled("content_types", DEVICE_CONTENT_TYPE)

    @pytest.mark.behavioral
    def test_embedded_create_with_prefilled_content_type_selects_the_new_object(
        self, auth_page, base_url, api, create_object
    ):
        """A role created with the prefilled content type is saved for devices and selected in the Role field."""
        name = unique_name()
        create_object.track("extras/roles/", name=name)
        modal = open_device_form(auth_page, base_url)
        modal.open_create("role")
        modal.fill("name", name)
        modal.submit_create()

        modal.expect_closed()
        role = find_one(api, "extras/roles/", name=name)
        assert role["content_types"] == ["dcim.device"]
        modal.expect_parent_field("role", role["id"], name)

    # -------------------------------------------------------------------------
    # Embedded search: the Tenant field
    # -------------------------------------------------------------------------

    def test_embedded_search_opens_the_search_form(self, auth_page, base_url):
        """The "Search tenants" button opens the Tenant filter form in the modal, with no tenant group filter set."""
        modal = open_device_form(auth_page, base_url)
        modal.open_search("tenants")

        modal.expect_title("Search tenants")
        modal.expect_prefilled("tenant_group")

    @pytest.mark.behavioral
    def test_embedded_search_filters_the_results(self, auth_page, base_url, created_grouped_tenant):
        """Searching by tenant group lists the tenant in that group and not the one outside it."""
        group, tenant, other = (created_grouped_tenant[key] for key in ("group", "tenant", "other"))
        modal = open_device_form(auth_page, base_url)
        modal.open_search("tenants")
        modal.search(tenant_group=group["name"])

        modal.expect_result_total(1)
        assert modal.result_rows(tenant["name"]).count() == 1
        assert modal.result_rows(other["name"]).count() == 0

    @pytest.mark.behavioral
    def test_embedded_search_selects_the_picked_object(self, auth_page, base_url, created_grouped_tenant):
        """Picking a search result closes the modal and selects that tenant in the Tenant field."""
        group, tenant = created_grouped_tenant["group"], created_grouped_tenant["tenant"]
        modal = open_device_form(auth_page, base_url)
        modal.open_search("tenants")
        modal.search(tenant_group=group["name"])
        modal.select_result(tenant["name"])

        modal.expect_closed()
        modal.expect_parent_field("tenant", tenant["id"], tenant["name"])

    # -------------------------------------------------------------------------
    # Embedded search with a prefilled content type: the Dynamic groups and Role fields
    # -------------------------------------------------------------------------

    def test_embedded_search_prefills_the_dynamic_group_content_type(self, auth_page, base_url):
        """The "Search dynamic groups" button opens the filter form with the Device content type already selected."""
        modal = open_device_form(auth_page, base_url)
        modal.open_search("dynamic groups")

        modal.expect_prefilled("content_type", DEVICE_CONTENT_TYPE)

    @pytest.mark.behavioral
    def test_embedded_search_with_prefilled_content_type_scopes_the_results(
        self, auth_page, base_url, api_count, create_object
    ):
        """The "Search roles" button lists only device roles, as many as the API counts, leaving out a rack role."""
        create_object("extras/roles/", name=unique_name(), content_types=["dcim.device"])
        create_object("extras/roles/", name=unique_name(), content_types=["dcim.rack"])
        device_roles = api_count("extras/roles/", content_types="dcim.device")
        assert device_roles < api_count("extras/roles/"), "The rack role should leave some roles out"

        modal = open_device_form(auth_page, base_url)
        modal.open_search("roles")

        modal.expect_prefilled("content_types", DEVICE_CONTENT_TYPE)
        modal.expect_result_total(device_roles)
