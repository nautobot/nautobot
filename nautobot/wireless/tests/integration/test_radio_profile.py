"""Radio profile bulk edit: select a row on the list and submit the bulk edit job."""

import pytest

from nautobot.wireless.tests.integration.pages.radio_profiles_page import RadioProfilesPage


class RadioProfileTestCase:
    """Bulk edit of radio profiles from the list view."""

    @pytest.mark.behavioral
    def test_radio_profile_bulk_edit(self, auth_page, base_url, wait_for_job_result, created_radio_profile):
        """Bulk editing the selected radio profile runs a Bulk Edit Objects job that succeeds."""
        radio_profiles = RadioProfilesPage(auth_page, base_url)
        radio_profiles.navigate(q=created_radio_profile["name"])
        radio_profiles.expect_row_count(1)

        radio_profiles.select_row(created_radio_profile["name"])
        radio_profiles.click_edit_selected()

        radio_profiles.expect_bulk_edit_count(1)
        assert radio_profiles.get_bulk_edit_pks() == [created_radio_profile["id"]], (
            "The bulk edit form should list the id of the selected row"
        )
        # Submit bulk edit form without any changes
        job_result = wait_for_job_result(radio_profiles.apply_bulk_edit())

        assert job_result["name"] == "Bulk Edit Objects", f"Apply redirected to a {job_result['name']!r} job result"
        status = job_result["status"]["value"]
        assert status == "SUCCESS", f"The Bulk Edit Objects job ended as {status}"
