"""Radio profile bulk edit: select rows on the list, change a field, and confirm the change on the list."""

import pytest

from nautobot.wireless.tests.integration.pages.radio_profiles_page import RadioProfilesPage

# The bulk edit form offers the label; the list renders the label; the REST API returns the value.
FREQUENCY_LABEL = "5 GHz"
FREQUENCY_VALUE = "5GHz"
# The list renders an unset frequency as a dash, and the REST API returns an empty string.
EMPTY_CELL = "—"


class RadioProfileTestCase:
    """Playwright port of ``wireless/tests/selenium/test_radio_profile.py::RadioProfileTestCase``."""

    @pytest.mark.behavioral
    def test_radio_profile_bulk_edit(self, auth_page, base_url, api, wait_for_job_result, created_radio_profiles):
        """Bulk editing two of three radio profiles sets the frequency on those two and leaves the third unset."""
        prefix = created_radio_profiles["prefix"]
        *selected, unselected = created_radio_profiles["profiles"]
        radio_profiles = RadioProfilesPage(auth_page, base_url)
        radio_profiles.navigate(q=prefix)
        radio_profiles.expect_row_count(3)

        for profile in selected:
            radio_profiles.select_row(profile["name"])
        radio_profiles.click_edit_selected()

        radio_profiles.expect_bulk_edit_count(len(selected))
        assert sorted(radio_profiles.get_bulk_edit_pks()) == sorted(profile["id"] for profile in selected), (
            "The bulk edit form should carry exactly the ids of the selected rows"
        )
        radio_profiles.set_bulk_edit_field("frequency", FREQUENCY_LABEL)
        job_result_id = radio_profiles.apply_bulk_edit()

        job_result = wait_for_job_result(job_result_id)
        assert job_result["name"] == "Bulk Edit Objects", f"Apply redirected to a {job_result['name']!r} job result"
        assert job_result["status"]["value"] == "SUCCESS", (
            f"Bulk edit job finished as {job_result['status']['value']}: {job_result.get('traceback')}"
        )

        radio_profiles.navigate(q=prefix)
        radio_profiles.expect_row_count(3)
        frequencies = dict(
            zip(
                radio_profiles.get_column_values_by_header("Name"),
                radio_profiles.get_column_values_by_header("Frequency"),
            )
        )
        expected = {profile["name"]: FREQUENCY_LABEL for profile in selected}
        expected[unselected["name"]] = EMPTY_CELL
        assert frequencies == expected, "The list should show the new frequency on the selected rows only"

        records = api.get("/api/wireless/radio-profiles/", params={"q": prefix}).json()["results"]
        stored = {record["name"]: record["frequency"] for record in records}
        expected_stored = {profile["name"]: FREQUENCY_VALUE for profile in selected}
        expected_stored[unselected["name"]] = ""
        assert stored == expected_stored, "The API should store the new frequency on the selected profiles only"
