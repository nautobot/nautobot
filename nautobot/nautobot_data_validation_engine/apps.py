from nautobot.core.apps import NautobotConfig
from nautobot.extras.plugins import register_custom_validators
from nautobot.extras.plugins.utils import import_object


class DataValidationEngineConfig(NautobotConfig):
    default = True
    name = "nautobot.nautobot_data_validation_engine"
    verbose_name = "Data Validation Engine"
    searchable_models = []
    custom_validators = "custom_validators.custom_validators"

    def ready(self):
        super().ready()

        validators = import_object("nautobot.nautobot_data_validation_engine.custom_validators.custom_validators")
        if validators is not None:
            register_custom_validators(validators)
