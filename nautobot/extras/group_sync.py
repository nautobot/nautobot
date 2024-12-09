"""Additional functions to process an OAuth2/OIDC user."""

import logging

from django.conf import settings
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)


CLAIMS_GROUP_NAME = getattr(settings, "SSO_CLAIMS_GROUP", "groups")
""" Which claim to look at in the OAuth2/OIDC response

    For Okta you can look at `Okta -> Authorization Servers -> Claims`. And a reasonable
    default is "groups". For Azure a reasonable default is "roles".
"""

SUPERUSER_GROUPS = getattr(settings, "SSO_SUPERUSER_GROUPS", [])
STAFF_GROUPS = getattr(settings, "SSO_STAFF_GROUPS", [])


def group_sync(uid, user=None, response=None, *args, **kwargs):
    """Sync the users groups from OAuth2/OIDC auth and set staff/superuser as appropriate."""
    if user and response and CLAIMS_GROUP_NAME and response.get(CLAIMS_GROUP_NAME, False):
        group_memberships = response.get(CLAIMS_GROUP_NAME)
        is_staff = False
        is_superuser = False
        logger.debug(f"User {uid} is a member of {', '.join(group_memberships)}")
        # Make sure all groups exist in Nautobot
        group_ids = []
        for group in group_memberships:
            if group in SUPERUSER_GROUPS:
                is_superuser = True
            if group in STAFF_GROUPS:
                is_staff = True
            group_ids.append(Group.objects.get_or_create(name=group)[0].id)
        user.groups.set(group_ids)
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        user.save()
    else:
        logger.debug(f"Did not receive groups from OAuth2/OIDC, response: {response}")
