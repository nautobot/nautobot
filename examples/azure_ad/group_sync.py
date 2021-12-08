"""Additional functions to process an Azure user."""
import logging
from django.contrib.auth.models import Group

logger = logging.getLogger("auth.Azure")
ROLES_GROUP_NAME = "roles"
SUPERUSER_GROUPS = ["Admin"]
STAFF_GROUPS = ["Admin"]


def group_sync(
    uid, user=None, response=None, *args, **kwargs
):  # pylint: disable=keyword-arg-before-vararg, unused-argument
    """Sync the users groups from Azure and set staff/superuser as appropriate."""
    if user and response and response.get(ROLES_GROUP_NAME, False):
        group_memberships = response.get(ROLES_GROUP_NAME)
        is_staff = False
        is_superuser = False
        logger.debug("User %s is a member of %s", uid, {", ".join(group_memberships)})
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
        logger.debug("Did not receive roles from Azure, response: %s", response)
