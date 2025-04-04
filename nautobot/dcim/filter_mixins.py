# TODO: remove this entire file in 2.2
# for backwards compatibility with Nautobot 1.4 - avoid importing this file if at all possible!
from nautobot.dcim.filters.mixins import LocatableModelFilterSetMixin

__all__ = ("LocatableModelFilterSetMixin",)
