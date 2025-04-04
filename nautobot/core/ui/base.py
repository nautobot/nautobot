"""Common base classes and utilities for defining the Nautobot UI."""


class PermissionsMixin:
    """Ensure permissions through init."""

    def __init__(self, permissions=None):
        """Ensure permissions."""
        if permissions is not None and not isinstance(permissions, (list, tuple)):
            raise TypeError("Permissions must be passed as a tuple or list.")
        self.permissions = set(permissions) if permissions else None
