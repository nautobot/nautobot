from django.core.exceptions import FieldDoesNotExist
from django.db import router, transaction
from django.db.utils import IntegrityError
from social_core.exceptions import AuthAlreadyAssociated

"""
Social Auth Account Takeover Vulnerability Patch
=================================================

This module patches CVE-2025-61783, a medium security vulnerability in social_django that allows
account takeover when using OAuth providers that don't verify email addresses.

VULNERABILITY OVERVIEW
----------------------
The vulnerability exists in social_django.storage.DjangoUserMixin.create_user(),
specifically in how it handles IntegrityError exceptions. When user creation fails due to
a duplicate email or username, the original code catches the IntegrityError and blindly
retrieves an existing user via manager.get(), returning that user without verifying that
a social auth association exists for the provider/UID combination.

PATCHING STRATEGY
-----------------
This implementation patches the `create_user` method on the `user` class property of
DjangoStorage, which is where the vulnerability manifests. The patch changes the behavior
to raise AuthAlreadyAssociated when an IntegrityError occurs, preventing the silent
return of an existing user.

By patching at this level, we:
- Maintain compatibility with custom pipelines
- Don't require changes to user's social auth configuration
- Apply the fix exactly where the vulnerability occurs
- Preserve all other social auth functionality

REMOVAL
-------
Remove this patch when upgrading to social-auth-app-django >= 5.6.0
(version that includes PR #803 merged into the main branch).

To verify if you still need the patch:
    pip show social-auth-app-django
    # Check version against PR #803 merge status

REFERENCES
----------
- Vulnerability Report: https://github.com/python-social-auth/social-app-django/security/advisories/GHSA-wv4w-6qv2-qqfg
- Original Issue: https://github.com/python-social-auth/social-app-django/issues/220
- Official Fix PR: https://github.com/python-social-auth/social-app-django/pull/803

SECURITY NOTICE
---------------
This patch addresses a MEDIUM security vulnerability

Disabling this patch without mitigation will expose your application to account
takeover attacks.

AUTHOR & MAINTENANCE
--------------------
Patch implemented as temporary security measure for Nautobot deployment.
As picking up the latest social_django would require a major version upgrade of Django,
which itself would require a breaking change to the Nautobot configuration, this patch
is intended to be a stopgap until such time as Nautobot can upgrade to a version of
social_django that includes the fix.
"""


def patch_django_storage(original_django_storage):
    """
    Apply security patch to DjangoStorage.user.create_user method.

    This patches the vulnerability in python-social-auth where create_user
    catches IntegrityError and blindly returns an existing user, enabling
    account takeover via unverified OAuth providers.

    Args:
        storage_class (DjangoStorage): The original DjangoStorage class to patch.

    Returns:
        None

    Note:
        The patch is a nearly verbatim copy of the original create_user method
        from social_django.storage.DjangoUserMixin from 5.4.3, except that it
        adopts the fail-closed change described in
        https://github.com/python-social-auth/social-app-django/pull/803

        The modified lines are called out with "Patched logic" comments below.
    """

    def patched_create_user(cls, *args, **kwargs):
        username_field = cls.username_field()
        if "username" in kwargs:
            if username_field not in kwargs:
                kwargs[username_field] = kwargs.pop("username")
            else:
                # If username_field is 'email' and there is no field named "username"
                # then latest should be removed from kwargs.
                try:
                    cls.user_model()._meta.get_field("username")
                except FieldDoesNotExist:
                    kwargs.pop("username")
        try:
            if hasattr(transaction, "atomic"):
                # In Django versions that have an "atomic" transaction decorator / context
                # manager, there's a transaction wrapped around this call.
                # If the create fails below due to an IntegrityError, ensure that the transaction
                # stays undamaged by wrapping the create in an atomic.
                using = router.db_for_write(cls.user_model())
                with transaction.atomic(using=using):
                    user = cls.user_model()._default_manager.create_user(*args, **kwargs)
            else:
                user = cls.user_model()._default_manager.create_user(*args, **kwargs)
        except IntegrityError as exc:
            # ORIGINAL CODE BELOW:
            # # If email comes in as None it won't get found in the get
            # if kwargs.get("email", True) is None:
            #     kwargs["email"] = ""
            # try:
            #     user = cls.user_model()._default_manager.get(*args, **kwargs)
            # except cls.user_model().DoesNotExist:
            #     raise exc

            # BEGIN Patched logic
            raise AuthAlreadyAssociated(None) from exc
            # END Patched logic
        return user

    # Apply the patch to the original DjangoStorage.user.create_user method
    original_django_storage.user.create_user = classmethod(patched_create_user)
