"""Additional functions to process an SSO (OAuth2/OIDC/SAML) user."""

import logging

from django.conf import settings
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)


CLAIMS_GROUP_NAME = getattr(settings, "SSO_CLAIMS_GROUP", "groups")
""" Which claim to look at in the SSO response

    For Okta you can look at `Okta -> Authorization Servers -> Claims`. And a reasonable
    default is "groups". For Azure a reasonable default is "roles".
"""

SUPERUSER_GROUPS = getattr(settings, "SSO_SUPERUSER_GROUPS", [])
STAFF_GROUPS = getattr(settings, "SSO_STAFF_GROUPS", [])
SYNC_GROUPS = getattr(settings, "SSO_SYNC_GROUPS", [])


def _revoke_group_memberships(user):
    """Remove all group memberships and staff/superuser flags from `user`."""
    user.groups.clear()
    user.is_superuser = False
    user.is_staff = False
    user.save()


def _describe_response(response):
    """Summarize an SSO response for troubleshooting.

    Only the claim *names* are reported. The values are never logged, as the pipeline response also carries
    the backend's token data (`access_token`, `id_token`, ...) alongside the user's claims.
    """
    if not isinstance(response, dict):
        return repr(response)
    description = f"top-level claims {sorted(response)}"
    if isinstance(response.get("attributes"), dict):
        description += f", attributes {sorted(response['attributes'])}"
    return description


def group_sync(uid, user=None, response=None, *args, **kwargs):
    """Sync the users groups from SSO (OAuth2/OIDC/SAML) auth and set staff/superuser as appropriate."""
    group_memberships = None
    # Whether the IdP asserted the claim at all, as distinct from asserting it with an empty value
    claim_present = False
    if user and response and CLAIMS_GROUP_NAME:
        # OAuth2/OIDC responses carry group claims at the top level of the response
        if CLAIMS_GROUP_NAME in response:
            claim_present = True
            group_memberships = response[CLAIMS_GROUP_NAME]
        attributes = response.get("attributes")
        # SAML responses nest the assertion attributes under the "attributes" key
        if not group_memberships and isinstance(attributes, dict) and CLAIMS_GROUP_NAME in attributes:
            claim_present = True
            group_memberships = attributes[CLAIMS_GROUP_NAME]
    if group_memberships:
        logger.debug("User %s is a member of %s", uid, ", ".join(group_memberships))
        # Staff and superuser status reflects the whole claim, whether or not those groups are synced to Nautobot
        is_superuser = any(group in SUPERUSER_GROUPS for group in group_memberships)
        is_staff = any(group in STAFF_GROUPS for group in group_memberships)
        if SYNC_GROUPS:
            allowed_memberships = [group for group in group_memberships if group in SYNC_GROUPS]
            if len(allowed_memberships) != len(group_memberships):
                logger.debug(
                    "Not syncing groups omitted from SSO_SYNC_GROUPS for user %s: %s",
                    uid,
                    ", ".join(sorted(set(group_memberships) - set(allowed_memberships))),
                )
            group_memberships = allowed_memberships
        # Make sure all groups exist in Nautobot
        group_ids = [Group.objects.get_or_create(name=group)[0].id for group in group_memberships]
        user.groups.set(group_ids)
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        user.save()
    elif claim_present:
        # The IdP asserted the claim with an empty value, which authoritatively says "no groups"
        logger.debug(
            "SSO returned an empty %r claim for user %s, revoking all group memberships and staff/superuser status",
            CLAIMS_GROUP_NAME,
            uid,
        )
        _revoke_group_memberships(user)
    else:
        # The claim is missing entirely, which says nothing about the user's entitlements either way, so leave
        # them as they are rather than locking users out over a transient failure to release the claim.
        logger.warning(
            "Did not receive a %r claim from SSO for user %s, so any group memberships and staff/superuser status "
            "previously granted to this user are retained. Response contained %s",
            CLAIMS_GROUP_NAME,
            uid,
            _describe_response(response),
        )
