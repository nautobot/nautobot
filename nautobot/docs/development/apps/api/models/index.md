# Adding Database Models

If your app introduces a new type of object in Nautobot, you'll probably want to create a [Django model](https://docs.djangoproject.com/en/stable/topics/db/models/) for it. A model is essentially a Python representation of a database table, with attributes that represent individual columns. Model instances can be created, manipulated, and deleted using [queries](https://docs.djangoproject.com/en/stable/topics/db/queries/). Models must be defined within a file named `models.py`.

It is highly recommended to have app models inherit from at least `nautobot.apps.models.BaseModel` which provides base functionality and convenience methods common to all models.

For more advanced usage, you may want to instead inherit from one of Nautobot's "generic" models derived from `BaseModel` -- `nautobot.apps.models.OrganizationalModel` or `nautobot.apps.models.PrimaryModel`. The inherent capabilities provided by inheriting from these various parent models differ as follows:

| Feature | `django.db.models.Model` | `BaseModel` | `OrganizationalModel` | `PrimaryModel` |
| ------- | --------------------- | ----------- | --------------------- | -------------- |
| UUID primary key | ❌ | ✅ | ✅ | ✅ |
| [Natural keys](../../../core/natural-keys.md) | ❌ | ✅ | ✅ | ✅ |
| [Object permissions](../../../../user-guide/administration/guides/permissions.md) | ❌ | ✅ | ✅ | ✅ |
| [`validated_save()`](../../../core/best-practices.md#model-validation) | ❌ | ✅ | ✅ | ✅ |
| [Object Metadata](../../../../user-guide/platform-functionality/objectmetadata.md) | ❌ | ✅ | ✅ | ✅ |
| [Change logging](../../../../user-guide/platform-functionality/change-logging.md) | ❌ | ❌ | ✅ | ✅ |
| [Contacts](../../../../user-guide/core-data-model/extras/contact.md) and [Teams](../../../../user-guide/core-data-model/extras/team.md) | ❌ | ❌ | ✅ | ✅ |
| [Custom fields](../../../../user-guide/platform-functionality/customfield.md) | ❌ | ❌ | ✅ | ✅ |
| [Dynamic Groups](../../../../user-guide/platform-functionality/dynamicgroup.md) | ❌ | ❌ | ✅ | ✅ |
| [Notes](../../../../user-guide/platform-functionality/note.md) | ❌ | ❌ | ✅ | ✅ |
| [Relationships](../../../../user-guide/platform-functionality/relationship.md) | ❌ | ❌ | ✅ | ✅ |
| [Saved Views](../../../../user-guide/platform-functionality/user-interface/savedview.md) | ❌ | ❌ | ✅ | ✅ |
| [Data Compliance](../../../../user-guide/feature-guides/data-compliance.md) | ❌ | ❌ | ✅ | ✅ |
| [Tags](../../../../user-guide/platform-functionality/tag.md) | ❌ | ❌ | ❌ | ✅ |

+++ 2.2.0 "Support for Contact and Team assignment on all models"
    Support for Contact and Team assignment to all Nautobot model types was added.

+++ 2.3.0 "Support for Object Metadata assignment on all models"
    Support for assigning Object Metadata was added to `BaseModel` (and therefore also `OrganizationalModel` and `PrimaryModel`) subclasses. If a specific model should not support assignment of metadata to its records (for example, a many-to-many "through" table model such as `CloudNetworkPrefixAssignment`), the model author can define the class attribute `is_metadata_associable_model = False` to opt it out from this feature.

+/- 2.3.0 "Support for Contact and Team assignment on OrganizationalModel and PrimaryModel only"
    Default support for Contact and Team assignment was removed from `django.db.models.Model` and `BaseModel`. The mixin class `ContactMixin` has been added to be used by `BaseModel` subclasses that want to be assignable to Contacts and Teams. All subclasses of `OrganizationalModel` and `PrimaryModel` include this mixin and therefore default to supporting Contact and Team assignment. Models can opt out of this feature by declaring the class attribute `is_contact_associable_model = False`.

+++ 2.3.0 "Support for Dynamic Groups and Saved Views on OrganizationalModel and PrimaryModel"
    Support for Dynamic Groups and Saved Views was added to `OrganizationalModel` and `PrimaryModel`. The mixin classes `DynamicGroupsModelMixin` and `SavedViewMixin` (included in both of those base classes) have been added to be used by `BaseModel` subclasses that want to be assignable to Dynamic Groups and/or to be Saved View capable. Models can opt out of either of these features by declaring `is_dynamic_group_associable_model = False` and/or `is_saved_view_model = False` as applicable.

+/- 2.3.0 "Replacement of DynamicGroupMixin with DynamicGroupsModelMixin"
    In previous Nautobot releases, a model could opt in to support of Dynamic Groups by including the `DynamicGroupMixin` mixin class. This class is now deprecated, and models should use the newly added `DynamicGroupsModelMixin` mixin class in its place.

+++ 3.0.0 "Support for Data Compliance on OrganizationalModel and PrimaryModel"
    Support for Data Compliance was added to `OrganizationalModel` and `PrimaryModel` through the `DataComplianceMixin` mixin class. Models can opt out of this feature by setting the class attribute `is_data_compliance_model = False`. This primarily controls whether the Data Compliance tab appears in the model's detail view. The feature works in conjunction with the `ObjectDataComplianceViewMixin` and its associated HTML template, which is generally used with `NautobotUIViewSet`.

Below is an example `models.py` file containing a basic model with two character fields:

```python
# models.py
from django.db import models

from nautobot.apps.models import BaseModel


class Animal(BaseModel):
    """Base model for animals."""

    name = models.CharField(max_length=50)
    sound = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [["name", "sound"]]
```

Once you have defined the model(s) for your app, you'll need to create the database schema migrations. A migration file is essentially a set of instructions for manipulating the database to support your new model, or to alter existing models.

Creating migrations can be done automatically using the `nautobot-server makemigrations <app_name>` management command, where `<app_name>` is the name of the Python package for your app (e.g. `nautobot_animal_sounds`):

```no-highlight
nautobot-server makemigrations nautobot_animal_sounds
```

!!! note
    An app must be installed before it can be used with Django management commands. If you skipped this step above, run `poetry install` from the app's root directory.

```no-highlight
nautobot-server makemigrations nautobot_animal_sounds
```

Example output:

```no-highlight
Migrations for 'nautobot_animal_sounds':
  /home/bjones/animal_sounds/nautobot_animal_sounds/migrations/0001_initial.py
    - Create model Animal
```

Next, apply the migration to the database with the `nautobot-server migrate <app_name>` command:

```no-highlight
nautobot-server migrate nautobot_animal_sounds
```

Example output:

```no-highlight
Operations to perform:
  Apply all migrations: nautobot_animal_sounds
Running migrations:
  Applying nautobot_animal_sounds.0001_initial... OK
```

For more background on schema migrations, see the [Django documentation](https://docs.djangoproject.com/en/stable/topics/migrations/).
