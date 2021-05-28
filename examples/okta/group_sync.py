"""Additional functions to process an OKTA user."""
import logging
from django.contrib.auth.models import Group

logger = logging.getLogger("auth.okta")
CLAIMS_GROUP_NAME = "groups"  # As in `Okta -> Authorization Servers -> Claims`
SUPERUSER_GROUPS = ["Nautobot Admins"]
STAFF_GROUPS = ["Nautobot Admins"]


def group_sync(uid, user=None, response=None, *args, **kwargs):
    """Sync the users groups from Okta and set staff/superuser as appropriate."""
    if user and response and response.get(CLAIMS_GROUP_NAME, False):
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
        logger.debug(f"Did not receive groups from Okta, okta response: {response}")
