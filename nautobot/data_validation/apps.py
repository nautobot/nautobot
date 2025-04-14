from nautobot.core.apps import NautobotConfig
from nautobot.extras.plugins import register_custom_validators


class DataValidationEngineConfig(NautobotConfig):
    default = True
    name = "nautobot.nautobot_data_validation_engine"
    verbose_name = "Data Validation Engine"
    searchable_models = []
    custom_validators = "custom_validators.custom_validators"

    def ready(self):
        super().ready()

        from nautobot.nautobot_data_validation_engine.custom_validators import custom_validators

        register_custom_validators(custom_validators)
