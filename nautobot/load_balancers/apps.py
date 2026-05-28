from nautobot.core.apps import NautobotConfig


class LoadBalancersConfig(NautobotConfig):
    """App configuration for the nautobot_load_balancer_models app."""

    default = True
    name = "nautobot.load_balancers"
    verbose_name = "Load Balancers"
    base_url = "load-balancers"
    searchable_models = [
        "virtualserver",
        "loadbalancerpool",
        "loadbalancerpoolmember",
        "healthcheckmonitor",
        "certificateprofile",
    ]
