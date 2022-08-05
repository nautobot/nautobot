"""Utilities for handling deprecation of code and features."""

import warnings


class DeprecatedClassMixin:
    """Mixin to mark a class as deprecated in favor of another, raising a DeprecationWarning when subclassed.

    **Must** be the first mixin in the deprecated class, that is:

    >>> class ObsoleteClass(DeprecatedClassMixin, ReplacementClass):

    and not:

    >>> class ObsoleteClass(ReplacementClass, DeprecatedClassMixin):
    """

    def __init_subclass__(cls):
        # For a class mixing in this mixin correctly, as defined above,
        # cls.__mro__ = [ObsoleteClass, DeprecatedClassMixin, ReplacementClass, object]
        # And a subclass of that class will be:
        # cls.__mro__ = [ChildClass, ObsoleteClass, DeprecatedClassMixin, ReplacementClass, object]
        # We don't want to warn when declaring ObsoleteClass, but we do want to warn on ChildClass or its descendants
        mro_names = [klass.__name__ for klass in cls.__mro__]
        mixin_index = mro_names.index("DeprecatedClassMixin")
        if mixin_index > 1:
            warnings.warn(
                f"Class {mro_names[mixin_index-1]} is deprecated, and will be removed in a future Nautobot release. "
                f"For future compatibility, please inherit from class {mro_names[mixin_index+1]} instead.",
                DeprecationWarning,
                stacklevel=2,  # warn from `class ChildClass(ObsoleteClass):`, not from __init_subclass__
            )
