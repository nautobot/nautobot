# Best Practices

While there are many different development interfaces in Nautobot that each expose unique functionality, there are a common set of a best practices that have broad applicability to users and developers alike. This includes elements of writing Jobs, Plugins, and scripts for execution through the `nbshell`.

## Model Existence in the Database

A common Django pattern is to check whether an model instance's primary key (`pk`) field is set as a proxy for whether the instance has been written to the database or whether it exists only in memory.
Because of the way Nautobot's UUID primary keys are implemented, **this check will not work as expected** because model instances are assigned a UUID in memory *at instance creation time*, not at the time they are written to the database (when the model's `save()` method is called).
Instead, for any model which inherits from `nautobot.core.models.BaseModel`, you should check an instance's `present_in_database` property which will be either `True` or `False`.

Wrong:

```python
if instance.pk:
    # Are we working with an existing instance in the database?
    # Actually, the above check doesn't tell us one way or the other!
    ...
else:
    # Will never be reached!
    ...
```

Right:

```python
if instance.present_in_database:
    # We're working with an existing instance in the database!
    ...
else:
    # We're working with a newly created instance not yet written to the database!
    ...
```

!!! note
    There is one case where a model instance *will* have a null primary key, and that is the case where it has been removed from the database and is in the process of being deleted.
    For most purposes, this is not the case you are intending to check!

## Model Validation

Django offers several places and mechanism in which to exert data and model validation. All model specific validation should occur within the model's `clean()` method or field specific validators. This ensures the validation logic runs and is consistent through the various Nautobot interfaces (Web UI, REST API, ORM, etc).

### Consuming Model Validation

Django places specific separation between validation and the saving of an instance and this means it is a common Django pattern to make explicit calls first to a model instance's `clean()`/`full_clean()` methods and then the `save()` method. Calling only the `save()` method **does not** automatically enforce validation and may lead to data integrity issues.

Nautobot provides a convenience method that both enforces model validation and saves the instance in a single call to `validated_save()`. Any model which inherits from `nautobot.core.models.BaseModel` has this method available. This includes all core models and it is recommended that all new Nautobot models and plugin-provided models also inherit from `BaseModel`.

The intended audience for the `validated_save()` convenience method is Job authors and anyone writing scripts for, or interacting with the ORM directly through the `nbshell` command. It is generally not recommended however, to use `validated_save()` as a blanket replacement for the `save()` method in the core of Nautobot.

During execution, should model validation fail, `validated_save()` will raise `django.core.exceptions.ValidationError` in the normal Django fashion.
