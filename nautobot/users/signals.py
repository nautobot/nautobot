"""Signal receivers for nautobot.users."""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from nautobot.core.authentication import (
    assign_groups_to_user,
    assign_permissions_to_user,
)
from nautobot.users.models import AdminUser

logger = logging.getLogger("nautobot.users.signals")


# By default social auth with automatically create users, if you need to change this you will need
# to modify the social auth pipeline https://python-social-auth.readthedocs.io/en/latest/pipeline.html
@receiver(post_save, sender=User)
@receiver(post_save, sender=AdminUser)
def setup_new_user(sender, instance, created, **kwargs):
    """Adds a newly created user to default groups and assigns default permissions."""
    if not created or not settings.SOCIAL_AUTH_ENABLED:
        return

    user = instance

    if settings.SOCIAL_AUTH_DEFAULT_SUPERUSER:
        logger.debug(f"Creating user {user.username} as superuser")
        user.is_superuser = True
        user.save()

    if settings.SOCIAL_AUTH_DEFAULT_STAFF:
        logger.debug(f"Creating user {user.username} as staff")
        user.is_staff = True
        user.save()

    if settings.REMOTE_AUTH_DEFAULT_GROUPS:
        # Assign default groups to the user
        assign_groups_to_user(user, settings.REMOTE_AUTH_DEFAULT_GROUPS)

    if settings.REMOTE_AUTH_DEFAULT_PERMISSIONS:
        # Assign default object permissions to the user
        assign_permissions_to_user(user, settings.REMOTE_AUTH_DEFAULT_PERMISSIONS)
