from functools import wraps

from django.contrib.contenttypes.models import ContentType

from nautobot.extras.plugins import PluginCustomValidator
from nautobot.extras.registry import registry
from nautobot.extras.utils import FeatureQuery


def custom_validator_clean(model_clean_func):
    """
    Decorator that wraps a models existing clean method to also execute registered plugin custom validators

    :param model_clean_func: The original model clean method which is to be wrapped
    """

    @wraps(model_clean_func)
    def wrapper(model_instance):
        # Run original model clean method
        model_clean_func(model_instance)

        # Run registered plugin custom validators
        model_name = model_instance._meta.label_lower

        # Note this registry holds instances of PluginCustomValidator registered from plugins
        # which is different than the `custom_validators` model features registry
        custom_validators = registry["plugin_custom_validators"].get(model_name, [])

        for custom_validator in custom_validators:
            # If the class has not overridden the specified method, we can skip it (because we know it
            # will raise NotImplementedError).
            if getattr(custom_validator, "clean") == getattr(PluginCustomValidator, "clean"):
                continue
            custom_validator(model_instance).clean()

    return wrapper


def wrap_model_clean_methods():
    """
    Helper function that wraps plugin model validator registered clean methods for all applicable models
    """
    for model in ContentType.objects.filter(FeatureQuery("custom_validators").get_query()):
        model_class = model.model_class()
        model_class.clean = custom_validator_clean(model_class.clean)
