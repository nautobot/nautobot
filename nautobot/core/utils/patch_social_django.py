from django.core.exceptions import FieldDoesNotExist
from django.db import router, transaction
from django.db.utils import IntegrityError
from social_core.exceptions import AuthAlreadyAssociated

# TODO: Document this patch


def patch_django_storage(original_django_storage):
    print("I am patching")

    def patched_create_user(cls, *args, **kwargs):
        print("I am nachos")
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
            # TODO: Add documentation for what was replaced here
            # BEGIN Nautobot-specific logic
            raise AuthAlreadyAssociated(None) from exc
            # END Nautobot-specific logic
        return user

    original_django_storage.user.create_user = classmethod(patched_create_user)
