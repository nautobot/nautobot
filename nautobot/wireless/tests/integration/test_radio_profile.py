"""Radio profile bulk edit: select a row on the list and submit the bulk edit job."""

import pytest

from nautobot.wireless.tests.integration.pages.radio_profiles_page import RadioProfilesPage


class RadioProfileTestCase:
    """Playwright port of ``wireless/tests/selenium/test_radio_profile.py::RadioProfileTestCase``."""

    @pytest.mark.behavioral
    def test_radio_profile_bulk_edit(self, auth_page, base_url, api, created_radio_profile):
        """Bulk editing the selected radio profile starts a Bulk Edit Objects job for that profile."""
        radio_profiles = RadioProfilesPage(auth_page, base_url)
        radio_profiles.navigate(q=created_radio_profile["name"])
        radio_profiles.expect_row_count(1)

        radio_profiles.select_row(created_radio_profile["name"])
        radio_profiles.click_edit_selected()

        radio_profiles.expect_bulk_edit_count(1)
        assert radio_profiles.get_bulk_edit_pks() == [created_radio_profile["id"]], (
            "The bulk edit form should carry the id of the selected row"
        )
        # Submit bulk edit form without any changes
        job_result_id = radio_profiles.apply_bulk_edit()

        # The job is not awaited: the CI job runs no Celery worker, so it stays pending there.
        job_result = api.get(f"/api/extras/job-results/{job_result_id}/").json()
        assert job_result["name"] == "Bulk Edit Objects", f"Apply redirected to a {job_result['name']!r} job result"
