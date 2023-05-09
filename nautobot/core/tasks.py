import logging

from django.conf import settings
from django.core.cache import cache
from packaging import version
import requests

from nautobot.core import celery
from nautobot.core.utils import config

# Get an instance of a logger
logger = logging.getLogger(__name__)


@celery.nautobot_task
def get_releases(pre_releases=False):
    url = config.get_settings_or_config("RELEASE_CHECK_URL")
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    releases = []

    # Check whether this URL has failed recently and shouldn't be retried yet
    if url == cache.get("latest_release_no_retry"):
        logger.info(f"Skipping release check; URL failed recently: {url}")
        return []

    try:
        logger.debug(f"Fetching new releases from {url}")
        response = requests.get(url, headers=headers, proxies=settings.HTTP_PROXIES, timeout=15)
        response.raise_for_status()
        total_releases = len(response.json())

        for release in response.json():
            if "tag_name" not in release:
                continue
            if not pre_releases and (release.get("devrelease") or release.get("prerelease")):
                continue
            releases.append((version.parse(release["tag_name"]), release.get("html_url")))
        logger.debug(f"Found {total_releases} releases; {len(releases)} usable")

    except requests.exceptions.RequestException:
        # The request failed. Set a flag in the cache to disable future checks to this URL for 15 minutes.
        logger.exception(f"Error while fetching {url}. Disabling checks for 15 minutes.")
        cache.set("latest_release_no_retry", url, 900)
        return []

    # Cache the most recent release
    cache.set("latest_release", max(releases), config.get_settings_or_config("RELEASE_CHECK_TIMEOUT"))

    # Since this is a Celery task, we can't return Version objects as they are not JSON serializable.
    return [(str(version), url) for version, url in releases]
