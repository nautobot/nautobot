from io import BytesIO
from logging import ERROR
from unittest.mock import Mock, patch

import requests
from cacheops import CacheMiss, RedisCache
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from packaging import version
from requests import Response

from nautobot.utilities.tasks import get_releases


def successful_github_response(url, *_args, **_kwargs):
    r = Response()
    r.url = url
    r.status_code = 200
    r.reason = "OK"
    r.headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    r.raw = BytesIO(
        b"""[
        {
            "html_url": "https://github.com/nautobot/nautobot/releases/tag/v2.7.8",
            "tag_name": "v2.7.8",
            "prerelease": false
        },
        {
            "html_url": "https://github.com/nautobot/nautobot/releases/tag/v2.6-beta1",
            "tag_name": "v2.6-beta1",
            "prerelease": true
        },
        {
            "html_url": "https://github.com/nautobot/nautobot/releases/tag/v2.5.9",
            "tag_name": "v2.5.9",
            "prerelease": false
        }
    ]
    """
    )
    return r


def unsuccessful_github_response(url, *_args, **_kwargs):
    r = Response()
    r.url = url
    r.status_code = 404
    r.reason = "Not Found"
    r.headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    r.raw = BytesIO(
        b"""{
        "message": "Not Found",
        "documentation_url": "https://developer.github.com/v3/repos/releases/#list-releases-for-a-repository"
    }
    """
    )
    return r


@override_settings(
    RELEASE_CHECK_URL="https://localhost/unittest/releases",
    RELEASE_CHECK_TIMEOUT=160876,
)
class GetReleasesTestCase(SimpleTestCase):
    @patch.object(requests, "get")
    @patch.object(RedisCache, "set")
    @patch.object(RedisCache, "get")
    def test_pre_releases(self, mock_cache_get: Mock, mock_cache_set: Mock, mock_request_get: Mock):
        mock_cache_get.side_effect = CacheMiss()
        mock_request_get.side_effect = successful_github_response

        releases = get_releases(pre_releases=True)

        # Check result
        self.assertListEqual(
            releases,
            [
                (
                    "2.7.8",
                    "https://github.com/nautobot/nautobot/releases/tag/v2.7.8",
                ),
                (
                    "2.6b1",
                    "https://github.com/nautobot/nautobot/releases/tag/v2.6-beta1",
                ),
                (
                    "2.5.9",
                    "https://github.com/nautobot/nautobot/releases/tag/v2.5.9",
                ),
            ],
        )

        # Check if correct request is made
        mock_request_get.assert_called_once_with(
            "https://localhost/unittest/releases",
            headers={"Accept": "application/vnd.github.v3+json"},
            proxies=settings.HTTP_PROXIES,
        )

        # Check if result is put in cache
        expected_version_str, expected_url = max(releases)
        expected_version = version.parse(expected_version_str)
        mock_cache_set.assert_called_once_with("latest_release", (expected_version, expected_url), 160876)

    @patch.object(requests, "get")
    @patch.object(RedisCache, "set")
    @patch.object(RedisCache, "get")
    def test_no_pre_releases(self, mock_cache_get: Mock, mock_cache_set: Mock, mock_request_get: Mock):
        mock_cache_get.side_effect = CacheMiss()
        mock_request_get.side_effect = successful_github_response

        releases = get_releases(pre_releases=False)

        # Check result
        self.assertListEqual(
            releases,
            [
                (
                    "2.7.8",
                    "https://github.com/nautobot/nautobot/releases/tag/v2.7.8",
                ),
                (
                    "2.5.9",
                    "https://github.com/nautobot/nautobot/releases/tag/v2.5.9",
                ),
            ],
        )

        # Check if correct request is made
        mock_request_get.assert_called_once_with(
            "https://localhost/unittest/releases",
            headers={"Accept": "application/vnd.github.v3+json"},
            proxies=settings.HTTP_PROXIES,
        )

        # Check if result is put in cache
        expected_version_str, expected_url = max(releases)
        expected_version = version.parse(expected_version_str)
        mock_cache_set.assert_called_once_with("latest_release", (expected_version, expected_url), 160876)

    @patch.object(requests, "get")
    @patch.object(RedisCache, "set")
    @patch.object(RedisCache, "get")
    def test_failed_request(self, mock_cache_get: Mock, mock_cache_set: Mock, mock_request_get: Mock):
        mock_cache_get.side_effect = CacheMiss()
        mock_request_get.side_effect = unsuccessful_github_response

        with self.assertLogs(level=ERROR) as cm:
            releases = get_releases()

        # Check log entry
        self.assertEqual(len(cm.output), 1)
        log_output = cm.output[0]
        last_log_line = log_output.split("\n")[-1]
        self.assertRegex(last_log_line, "404 .* Not Found")

        # Check result
        self.assertListEqual(releases, [])

        # Check if correct request is made
        mock_request_get.assert_called_once_with(
            "https://localhost/unittest/releases",
            headers={"Accept": "application/vnd.github.v3+json"},
            proxies=settings.HTTP_PROXIES,
        )

        # Check if failure is put in cache
        mock_cache_set.assert_called_once_with("latest_release_no_retry", "https://localhost/unittest/releases", 900)

    @patch.object(requests, "get")
    @patch.object(RedisCache, "set")
    @patch.object(RedisCache, "get")
    def test_blocked_retry(self, mock_cache_get: Mock, mock_cache_set: Mock, mock_request_get: Mock):
        mock_cache_get.return_value = "https://localhost/unittest/releases"
        mock_request_get.side_effect = successful_github_response

        releases = get_releases()

        # Check result
        self.assertListEqual(releases, [])

        # Check if request is NOT made
        mock_request_get.assert_not_called()

        # Check if cache is not updated
        mock_cache_set.assert_not_called()
