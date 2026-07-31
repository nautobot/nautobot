"""Additional functions to process an OAuth2/OIDC user."""

import logging

from django.conf import settings
from django.contrib.auth.models import Group
import jwt
from jwt.exceptions import DecodeError
from social_django.models import UserSocialAuth

logger = logging.getLogger(__name__)


CLAIMS_GROUP_NAME = getattr(settings, "SSO_CLAIMS_GROUP", "groups")
""" Which claim to look at in the OAuth2/OIDC response

    For Okta you can look at `Okta -> Authorization Servers -> Claims`. And a reasonable
    default is "groups". For Azure a reasonable default is "roles".
"""

SUPERUSER_GROUPS = getattr(settings, "SSO_SUPERUSER_GROUPS", [])
STAFF_GROUPS = getattr(settings, "SSO_STAFF_GROUPS", [])
GROUPS_SCOPE = getattr(settings, "SSO_GROUPS_FILTER", [])


def sync_user(user, group_memberships):
    logger.debug(f"Adding user {user.id} as a member of {', '.join(group_memberships)}")
    # Make sure all groups exist in Nautobot
    is_staff = False
    is_superuser = False
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


def group_sync(uid, user=None, response=None, *args, **kwargs):
    """Sync the users groups from OAuth2/OIDC auth and set staff/superuser as appropriate."""
    if user and response and CLAIMS_GROUP_NAME and response.get(CLAIMS_GROUP_NAME, False):
        sso_memberships = response.get(CLAIMS_GROUP_NAME)
        if GROUPS_SCOPE:
            group_memberships = [x for x in sso_memberships if x in GROUPS_SCOPE]
        else:
            group_memberships = sso_memberships
        sync_user(user, group_memberships)
    # if groups are not coming via userinfo, try to fetch from JWT id_token claim
    elif user and response and CLAIMS_GROUP_NAME and not response.get(CLAIMS_GROUP_NAME, False):
        sso_user = UserSocialAuth.objects.filter(user=user).first()
        try:
            id_token = sso_user.extra_data.get("id_token", False)
            provider = user.social_auth.values()[0].get("provider").upper()
        except AttributeError:
            logger.debug(f"User {uid} not synced from SSO or extra_data not present.")
        except IndexError:
            logger.debug(f"User {uid} is a local or non-existent user")
        verify_ssl = getattr(settings, f"SOCIAL_AUTH_{provider}_VERIFY_SSL", True)
        try:
            decoded_id_token = jwt.decode(id_token, options={"verify_signature": verify_ssl})
        except DecodeError as err:
            logger.debug(f"Unable to decode User {uid} JWT Id Token, {err}")
        sso_memberships = decoded_id_token.get(CLAIMS_GROUP_NAME, False)
        if not sso_memberships:
            logger.debug(f"Did not receive groups from OAuth2/OIDC, id_token: {id_token}")
            return
        if GROUPS_SCOPE:
            group_memberships = [x for x in sso_memberships if x in GROUPS_SCOPE]
        else:
            group_memberships = sso_memberships
        sync_user(user, group_memberships)
    else:
        logger.debug(f"Did not receive groups from OAuth2/OIDC, response: {response}")
