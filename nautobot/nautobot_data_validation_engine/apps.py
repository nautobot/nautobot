from nautobot.core.apps import NautobotConfig


class DataValidationEngineConfig(NautobotConfig):
    default = True
    name = "nautobot.nautobot_data_validation_engine"
    verbose_name = "Data Validation Engine"
    searchable_models = []
