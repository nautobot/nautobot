# Implementing Custom Validators

Apps can register custom validator classes which implement model validation logic to be executed during a model's `clean()` method. Like template extensions, custom validators are registered to a single model and offer a method which app authors override to implement their validation logic. This is accomplished by subclassing `CustomValidator` and implementing the `clean()` method.

App authors must raise `django.core.exceptions.ValidationError` within the `clean()` method to trigger validation error messages which are propagated to the user and prevent saving of the model instance. A convenience method `validation_error()` may be used to simplify this process. Raising a `ValidationError` is no different than vanilla Django, and the convenience method will simply pass the provided message through to the exception.

When a CustomValidator is instantiated, the model instance is assigned to context dictionary using the `object` key, much like TemplateExtension. E.g. `self.context['object']`.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `custom_validators` within a `custom_validators.py` file. (This can be overridden by setting `custom_validators` to a custom value on the app's `NautobotAppConfig`.) An example is below.

```python
# custom_validators.py
from nautobot.apps.models import CustomValidator


class SiteValidator(CustomValidator):
    """Custom validator for Sites to enforce that they must have a Region."""

    model = 'dcim.site'

    def clean(self):
        if self.context['object'].region is None:
            # Enforce that all sites must be assigned to a region
            self.validation_error({
                "region": "All sites must be assigned to a region"
            })


custom_validators = [SiteValidator]
```
