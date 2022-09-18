import logging

import requests
from cacheops.simple import cache, CacheMiss
from django.conf import settings
from packaging import version

from nautobot.core.celery import nautobot_task
from nautobot.utilities.config import get_settings_or_config

# Get an instance of a logger
logger = logging.getLogger("nautobot.releases")


@nautobot_task
def get_releases(pre_releases=False):
    url = get_settings_or_config("RELEASE_CHECK_URL")
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    releases = []

    # Check whether this URL has failed recently and shouldn't be retried yet
    try:
        if url == cache.get("latest_release_no_retry"):
            logger.info(f"Skipping release check; URL failed recently: {url}")
            return []
    except CacheMiss:
        pass

    try:
        logger.debug(f"Fetching new releases from {url}")
        response = requests.get(url, headers=headers, proxies=settings.HTTP_PROXIES)
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
    cache.set("latest_release", max(releases), get_settings_or_config("RELEASE_CHECK_TIMEOUT"))

    # Since this is a Celery task, we can't return Version objects as they are not JSON serializable.
    return [(str(version), url) for version, url in releases]
