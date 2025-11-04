"""App declaration for nautobot_load_balancer_models."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotLoadBalancerModelsConfig(NautobotAppConfig):
    """App configuration for the nautobot_load_balancer_models app."""

    name = "nautobot_load_balancer_models"
    verbose_name = "Load Balancer Models"
    version = __version__
    author = "Network to Code, LLC"
    description = "Load Balancer Models."
    base_url = "load-balancer-models"
    required_settings = []
    default_settings = {}
    constance_config = {}
    searchable_models = [
        "virtualserver",
        "loadbalancerpool",
        "loadbalancerpoolmember",
        "healthcheckmonitor",
        "certificateprofile",
    ]
    docs_view_name = "plugins:nautobot_load_balancer_models:docs"


config = NautobotLoadBalancerModelsConfig  # pylint:disable=invalid-name
