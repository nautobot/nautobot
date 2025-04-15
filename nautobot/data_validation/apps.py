from nautobot.core.apps import NautobotConfig
from nautobot.extras.plugins import register_custom_validators, register_template_extensions


class DataValidationEngineConfig(NautobotConfig):
    default = True
    name = "nautobot.data_validation"
    verbose_name = "Data Validation Engine"
    searchable_models = []
    base_url = "data-validation"  # used in generate_performance_test_endpoints

    def ready(self):
        super().ready()

        from nautobot.data_validation.custom_validators import custom_validators

        register_custom_validators(custom_validators)

        from nautobot.data_validation.template_content import template_extensions

        register_template_extensions(template_extensions)
