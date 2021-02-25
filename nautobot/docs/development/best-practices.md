# Best Practices

While there are many different development interfaces in Nautobot that each expose unique functionality, there are a common set of a best practices that have broad applicability to users and developers alike. This includes elements of writing Jobs, Plugins, and scripts for execution through the `nbshell`.

## Model Validation

Django offers several places and mechanism in which to exert data and model validation. All model specific validation should occur within the model's `clean()` method or field specific validators. This ensures the validation logic runs and is consistent through the various Nautobot interfaces (Web UI, REST API, ORM, etc).

### Consuming Model Validation

Django places specific separation between validation and the saving of an instance and this means it is a common Django pattern to make explicit calls first to a model instance's `clean()`/`full_clean()` methods and then the `save()` method. Calling only the `save()` method **does not** automatically enforce validation and may lead to data integrity issues.

Nautobot provides a convenience method that both enforces model validation and saves the instance in a single call to `validated_save()`. Any model which inherits from `nautobot.core.models.BaseModel` has this method available. This includes all core models and it is recommended that all new Nautobot models and plugin-provided models also inherit from `BaseModel`.

The intended audience for the `validated_save()` convenience method is Job authors and anyone writing scripts for, or interacting with the ORM directly through the `nbshell` command. It is generally not recommended however, to use `validated_save()` as a blanket replacement for the `save()` method in the core of Nautobot.

During execution, should model validation fail, `validated_save()` will raise `django.core.exceptions.ValidationError` in the normal Django fashion.
