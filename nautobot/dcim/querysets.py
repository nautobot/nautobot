from nautobot.core.models.querysets import ClusterToClustersQuerySetMixin
from nautobot.extras.querysets import ConfigContextModelQuerySet


class DeviceQuerySet(ClusterToClustersQuerySetMixin, ConfigContextModelQuerySet):
    pass
