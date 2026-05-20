from django.contrib.contenttypes.models import ContentType


def resolve_for_concrete_model(model_or_instance, for_concrete_model=None):
    """
    Resolve ContentType behavior from explicit override or model class policy.

    Args:
        model_or_instance: Django model class or model instance.
        for_concrete_model (bool | None): Optional explicit override.
    """
    if for_concrete_model is not None:
        return for_concrete_model

    model = model_or_instance if isinstance(model_or_instance, type) else model_or_instance.__class__
    return getattr(model, "for_concrete_model", True)


def get_content_type_for_model(model_or_instance, for_concrete_model=None):
    """
    Resolve ContentType using model policy with optional override.
    """
    model = model_or_instance if isinstance(model_or_instance, type) else model_or_instance.__class__
    return ContentType.objects.get_for_model(
        model,
        for_concrete_model=resolve_for_concrete_model(model, for_concrete_model=for_concrete_model),
    )
