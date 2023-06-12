"""Utilities for handling deprecation of code and features."""

import logging
import traceback
import warnings

from nautobot.core.settings import LOG_DEPRECATION_WARNINGS

logger = logging.getLogger(__name__)


def class_deprecated(message):
    """Decorator to mark a class as deprecated with a custom message about what to do instead of subclassing it."""

    def decorate(cls):
        def init_subclass(new_subclass):
            # Walk the stack up to the class declaration in question.
            stacklevel = 0
            for fs in reversed(traceback.extract_stack()):
                stacklevel += 1
                if new_subclass.__name__ in fs.line:
                    break
            else:
                stacklevel = 1
            warnings.warn(
                f"Class {cls.__name__} is deprecated, and will be removed in a future Nautobot release. "
                f"Instead of deriving {new_subclass.__name__} from {cls.__name__}, {message}.",
                DeprecationWarning,
                stacklevel=stacklevel,
            )
            if LOG_DEPRECATION_WARNINGS:
                # Since DeprecationWarnings are silenced by default, also log a traditional warning.
                logger.warning(
                    f"Class {cls.__name__} is deprecated, and will be removed in a future Nautobot release. "
                    f"Instead of deriving {new_subclass.__name__} from {cls.__name__}, {message}.",
                    stacklevel=stacklevel,
                )

        cls.__init_subclass__ = classmethod(init_subclass)
        return cls

    return decorate


def class_deprecated_in_favor_of(replacement_class):
    """Decorator to mark a class as deprecated and suggest a replacement class if it is subclassed from."""
    return class_deprecated(f"please migrate your code to inherit from class {replacement_class.__name__} instead")
