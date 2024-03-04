# Adding Database Models

If your app introduces a new type of object in Nautobot, you'll probably want to create a [Django model](https://docs.djangoproject.com/en/stable/topics/db/core-data-model/) for it. A model is essentially a Python representation of a database table, with attributes that represent individual columns. Model instances can be created, manipulated, and deleted using [queries](https://docs.djangoproject.com/en/stable/topics/db/queries/). Models must be defined within a file named `models.py`.

It is highly recommended to have app models inherit from at least `nautobot.apps.models.BaseModel` which provides base functionality and convenience methods common to all models.

For more advanced usage, you may want to instead inherit from one of Nautobot's "generic" models derived from `BaseModel` -- `nautobot.apps.models.OrganizationalModel` or `nautobot.apps.models.PrimaryModel`. The inherent capabilities provided by inheriting from these various parent models differ as follows:

| Feature | `django.db.models.Model` | `BaseModel` | `OrganizationalModel` | `PrimaryModel` |
| ------- | --------------------- | ----------- | --------------------- | -------------- |
| UUID primary key | ❌ | ✅ | ✅ | ✅ |
| [Natural keys](../../../core/natural-keys.md) | ❌ | ✅ | ✅ | ✅ |
| [Object permissions](../../../../user-guide/administration/guides/permissions.md) | ❌ | ✅ | ✅ | ✅ |
| [`validated_save()`](../../../core/best-practices.md#model-validation) | ❌ | ✅ | ✅ | ✅ |
| [Change logging](../../../../user-guide/platform-functionality/change-logging.md) | ❌ | ❌ | ✅ | ✅ |
| [Custom fields](../../../../user-guide/platform-functionality/customfield.md) | ❌ | ❌ | ✅ | ✅ |
| [Relationships](../../../../user-guide/platform-functionality/relationship.md) | ❌ | ❌ | ✅ | ✅ |
| [Note](../../../../user-guide/platform-functionality/note.md) | ❌ | ❌ | ✅ | ✅ |
| [Tags](../../../../user-guide/platform-functionality/tag.md) | ❌ | ❌ | ❌ | ✅ |

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
