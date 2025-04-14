from nautobot.core.apps import NautobotConfig
from nautobot.extras.plugins import register_custom_validators


class DataValidationEngineConfig(NautobotConfig):
    default = True
    name = "nautobot.data_validation"
    verbose_name = "Data Validation Engine"
    searchable_models = []

    def ready(self):
        super().ready()

        from nautobot.data_validation.custom_validators import custom_validators

        register_custom_validators(custom_validators)
