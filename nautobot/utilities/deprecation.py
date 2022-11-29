"""Utilities for handling deprecation of code and features."""

import logging
import sys
import traceback
import warnings

from nautobot.core.settings import LOG_DEPRECATION_WARNINGS


logger = logging.getLogger(__name__)


def class_deprecated_in_favor_of(replacement_class):
    """Decorator to mark a class as deprecated and suggest a replacement class if it is subclassed from."""

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
                f"Instead of deriving {new_subclass.__name__} from {cls.__name__}, "
                f"please migrate your code to inherit from class {replacement_class.__name__} instead.",
                DeprecationWarning,
                stacklevel=stacklevel,
            )
            if LOG_DEPRECATION_WARNINGS:
                # Since DeprecationWarnings are silenced by default, also log a traditional warning.
                # Note: logger.warning() only supports a `stacklevel` parameter in Python 3.8 and later
                if sys.version_info >= (3, 8):
                    logger.warning(
                        f"Class {cls.__name__} is deprecated, and will be removed in a future Nautobot release. "
                        f"Instead of deriving {new_subclass.__name__} from {cls.__name__}, "
                        f"please migrate your code to inherit from class {replacement_class.__name__} instead.",
                        stacklevel=stacklevel,
                    )
                else:
                    # TODO: remove this case when we drop Python 3.7 support
                    logger.warning(
                        f"Class {cls.__name__} is deprecated, and will be removed in a future Nautobot release. "
                        f"Instead of deriving {new_subclass.__name__} from {cls.__name__}, "
                        f"please migrate your code to inherit from class {replacement_class.__name__} instead.",
                    )

        cls.__init_subclass__ = classmethod(init_subclass)
        return cls

    return decorate
