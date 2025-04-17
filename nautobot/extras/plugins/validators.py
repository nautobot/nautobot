from functools import wraps

from django.apps import apps

from nautobot.extras.plugins import CustomValidator
from nautobot.extras.registry import registry
from nautobot.extras.utils import FeatureQuery


def custom_validator_clean(model_class):
    """
    Decorator that wraps a models existing clean method to also execute registered plugin custom validators

    Args:
        model_class: The model class whose clean function is to be wrapped
    """

    model_clean_func = model_class.clean
    model_name = model_class._meta.label_lower

    @wraps(model_clean_func)
    def wrapper(model_instance):
        # Run original model clean method
        model_clean_func(model_instance)

        # Run App registered custom validators
        # Note this registry holds instances of CustomValidator registered from plugins
        # which is different than the `custom_validators` model features registry
        for custom_validator in registry["plugin_custom_validators"][model_name]:
            # If the class has not overridden the specified method, we can skip it (because we know it
            # will raise NotImplementedError).
            if getattr(custom_validator, "clean") == getattr(CustomValidator, "clean"):
                continue
            custom_validator(model_instance).clean()

    return wrapper


def wrap_model_clean_methods():
    """
    Helper function that wraps plugin model validator registered clean methods for all applicable models
    """
    for app_label, models in FeatureQuery("custom_validators").as_dict():
        for model in models:
            model_class = apps.get_model(app_label=app_label, model_name=model)
            model_class.clean = custom_validator_clean(model_class)
