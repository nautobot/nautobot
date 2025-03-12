# Implementing Custom Validators

Apps can register custom validator classes which implement model validation logic to be executed during a model's `clean()` method. Like template extensions, custom validators are registered to a single model and offer a method which app authors override to implement their validation logic. This is accomplished by subclassing `CustomValidator` and implementing the `clean()` method.

App authors must raise `django.core.exceptions.ValidationError` within the `clean()` method to trigger validation error messages which are propagated to the user and prevent saving of the model instance. A convenience method `validation_error()` may be used to simplify this process. Raising a `ValidationError` is no different than vanilla Django, and the convenience method will simply pass the provided message through to the exception.

When a CustomValidator is instantiated, the model instance is assigned to context dictionary using the `object` key, much like TemplateExtension. E.g. `self.context['object']`. The context is also populated with the current request user object. E.g. `self.context['user']`.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `custom_validators` within a `custom_validators.py` file. (This can be overridden by setting `custom_validators` to a custom value on the app's `NautobotAppConfig`.) An example is below.

```python
# custom_validators.py
from nautobot.apps.models import CustomValidator


class LocationValidator(CustomValidator):
    """Custom validator for Locations to enforce that they must have a Tenant."""

    model = 'dcim.location'

    def clean(self):
        if self.context['object'].tenant is None:
            # Enforce that all locations must have a tenant
            self.validation_error({
                "tenant": "All locations must have a tenant"
            })


custom_validators = [LocationValidator]
```

## User Context

+++ 2.4.4

Custom validators have access to the current user via `self.context['user']` whenever the custom validator is invoked within a web request context. This is true for any Web UI, REST API request, Job execution, and anytime the `web_request_context` context manager is used in `nbshell` or a out of band script. In the event a custom validator is run outside of a web request context, `self.context['user']` will be populated with an instance of `AnonymousUser` from `django.contrib.auth`. This allows a custom validator author to write code that is durable to cases where a real user is not available.

With the user object, you can inspect the groups and permissions that the user has, allowing more granular access related validation.

This example shows a custom validator that only allows users in the group "Tenant Managers" to change the tenant of a location:

```python
# custom_validators.py
from nautobot.apps.models import CustomValidator


class LocationTenantValidator(CustomValidator):
    """Custom validator for Locations to enforce that only some users can update the Tenant."""

    model = 'dcim.location'

    def clean(self):
        new_object_state = self.context["object"]
        if not new_object_state.present_in_database:
            # This is a brand new Location, so skip the rest of the checks here
            return

        # Get a copy of the object as it currently exists in the database
        current_object_state = new_object_state._meta.model.objects.get(id=new_object_state.id)

        # Compare the tenant values between the two states
        if new_object_state.tenant != current_object_state.tenant:

            # Check if the user has permission to change the tenant, via being a member of "Tenant Managers"
            if not self.context["user"].groups.filter(name="Tenant Managers").exists():
                self.validation_error({
                    "tenant": "You do not have permission to change the tenant"
                })


custom_validators = [LocationTenantValidator]
```
