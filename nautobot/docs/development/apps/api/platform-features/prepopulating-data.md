# Prepopulating Data

In many cases, an app may wish to make use of Nautobot's various extensibility features, such as [custom fields](../../../../user-guide/platform-functionality/customfield.md) or [relationships](../../../../user-guide/platform-functionality/relationship.md). It can be useful for an app to automatically create a custom field definition or relationship definition as a consequence of being installed and activated, so that everyday usage of the app can rely upon these definitions to be present.

Furthermore, sometimes apps might want to create a baseline of available data. This could, for example, be a baseline of circuit providers for a [Single Source of Truth](https://docs.nautobot.com/projects/ssot/en/latest/) integration that synchronizes circuit data or creating new default [statuses](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/status/) and/or [roles](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/role/), or adding to the allowed content types for existing statuses and roles.

## Comparison of Options

Multiple options for the population of base state are available, each with their own trade-offs. There is no single best option, you have to choose the one has the best properties for your specific need.

- Signal handlers on `nautobot_database_ready`
- Django built-in features:
    - Django Data Migrations
    - Django Fixtures
- Jobs using the Nautobot Design Builder App
- Creating data in-place where needed

The below table provides a comparison between these options on a number of factors; additional factors are detailed in the following subsections.

|                                  | `nautobot_database_ready` Signal Handler         | Data Migration                                    | Django Fixture                 | Design Builder Job            | Creating Data In-Place         |
|----------------------------------|--------------------------------------------------|---------------------------------------------------|--------------------------------|-------------------------------|--------------------------------|
| **Startup Impact**               | ⚠️ Exceptions can occur after database migrations | ⚠️ Exceptions can occur during database migrations | ✅ None                        | ✅ None                       | ✅ None                        |
| **Execution**                    | ✅ Automatic                                     | ✅ Automatic                                      | ⚠️ Manual                       | ⚠️ Manual                      | ✅ Automatic                   |
| **Performance Impact**           | ⚠️ Each time migrations are run                   | ✅ Once when migrations are first run             | ✅ Once when fixture is loaded | ⚠️ Each time design job is run | ⚠️ Each time the data is needed |
| **Re-running / Idempotence**     | ⚠️ Required¹                                      | ⚠️ One-time only                                   | ✅ Possible¹                   | ✅ Possible¹                  | ✅ Possible¹                   |
| **App Required**                 | ⚠️ Yes                                            | ⚠️ Yes                                             | ✅ No                          | ✅ No                         | ✅ No                          |
| **Ongoing Maintenance Required** | ⚠️ Moderate                                       | ✅ None                                           | ⚠️ Moderate                     | ⚠️ Moderate                    | ⚠️ High                         |

<!-- pyml disable-next-line no-inline-html -->
<ul>
    <li style="list-style-type: '¹'">Rerunning needs to account for the possibility of user modification of the data in the interim in order to avoid errors or inadvertent overwriting of user-modified data.</li>
</ul>

### Signal Handlers On `nautobot_database_ready`

<!-- pyml disable-num-lines 10 no-inline-html,proper-names -->
<ul>
    <li style="list-style-type: '✅'">Can be updated in-place in later App releases</li>
    <li style="list-style-type: '⚠️'">Re-runs every time <code>nautobot-server migrate</code> or <code>nautobot-server post_upgrade</code> is run
        <ul>
            <li style="list-style-type: '⚠️'">Must be idempotent, as such it mustn't introduce duplicate records or errors if run repeatedly</li>
            <li style="list-style-type: '⚠️'">May recreate or revert records that a user intentionally deleted or altered - if this is not desired it has to be accounted for and handled in the code</li>
        </ul>
    </li>
    <li style="list-style-type: '⚠️'">Impacts Nautobot startup and upgrade performance, care needs to be taken
</ul>

Refer to the [implementation guide below](#writing-a-nautobot_database_ready-signal-handler) if you choose to proceed with this option.

### Django Data Migrations

<!-- pyml disable-next-line no-inline-html -->
<ul>
    <li style="list-style-type: '✅'">Provides a clean way to delete any associated objects when uninstalling the app</li>
    <li style="list-style-type: '⚠️'">Immutable - if you later need to add new objects, you need to add a new migration</li>
    <li style="list-style-type: '⚠️'">Can't easily be feature-toggled (if you include settings lookups in your migration and later change those settings, the migrations will _not_ run again)</li>
</ul>

Refer to the [implementation guide below](#writing-data-migrations) if you choose to proceed with this option.

### Django Fixtures

<!-- pyml disable-next-line no-inline-html -->
<ul>
    <li style="list-style-type: '✅'">Have good support for usage in unit tests</li>
    <li style="list-style-type: '⚠️'">Creating/updating them is not straight-forward, especially for big data sets</li>
</ul>

Refer to the [Django documentation](https://docs.djangoproject.com/en/4.2/topics/db/fixtures/#fixtures) if you choose to proceed with this option.

### Nautobot Design Builder Jobs

<!-- pyml disable-next-line no-inline-html -->
<ul>
    <li style="list-style-type: '⚠️'"> The possibility of later user modifications to data must be accounted for and handled in the design</li>
</ul>

Refer to the [Nautobot Design Builder App documentation](https://docs.nautobot.com/projects/design-builder/en/latest/) if you choose to proceed with this option.

### Creating Data In-Place Where Needed

This approach means to, for example, use `Status.objects.get_or_create(...)` in the place when you need it, such as a job.

<!-- pyml disable-next-line no-inline-html -->
<ul>
    <li style="list-style-type: '✅'">Unnecessary/unused records are not created automatically</li>
    <li style="list-style-type: '⚠️'">Data is not available in the DB/API/GUI until the process that uses it runs</li>
    <li style="list-style-type: '⚠️'">Some care has to be taken to not duplicate information if multiple things depend on this data</li>
    <li style="list-style-type: '⚠️'">Later modifications may be error-prone if a given record/set of attributes is created/referenced in many locations</li>
    <li style="list-style-type: '⚠️'">User modifications to the data may result in side effects (renaming a status may result in a new status with the original name being recreated next time the code runs, etc.)</li>
</ul>

## Implementation Guides

The following sections highlight how to implement some of these approaches.

### Writing a `nautobot_database_ready` Signal Handler

+++ 1.2.0

You can implement custom [signal](https://docs.djangoproject.com/en/stable/topics/signals/) handlers listening to the `nautobot_database_ready` signal. This signal is triggered when `nautobot-server migrate` or `nautobot-server post_upgrade` is run after installing an app, and provides an opportunity for the app to make any desired additions to the database at this time.

For example, maybe we want our app to make use of a Relationship allowing each Location to be linked to our Animal model. We would define our callback function that makes sure this Relationship exists, by convention in a `signals.py` file:

```python
# signals.py

from nautobot.extras.choices import RelationshipTypeChoices

def create_location_to_animal_relationship(sender, apps, **kwargs):
    """Create a Location-to-Animal Relationship if it doesn't already exist."""
    # Use apps.get_model to look up Nautobot core models
    ContentType = apps.get_model("contenttypes", "ContentType")
    Relationship = apps.get_model("extras", "Relationship")
    Location = apps.get_model("dcim", "Location")
    # Use sender.get_model to look up models from this app
    Animal = sender.get_model("Animal")

    # Ensure that the Relationship exists
    Relationship.objects.update_or_create(
        key="location_favorite_animal",
        defaults={
            "label": "Location's Favorite Animal",
            "type": RelationshipTypeChoices.TYPE_ONE_TO_MANY,
            "source_type": ContentType.objects.get_for_model(Animal),
            "source_label": "Locations that love this Animal",
            "destination_type": ContentType.objects.get_for_model(Location),
            "destination_label": "Favorite Animal",
        },
    )
```

Then, in the `NautobotAppConfig` `ready()` function, we connect this callback function to the `nautobot_database_ready` signal:

```python
# __init__.py

from nautobot.apps import nautobot_database_ready, NautobotAppConfig

from .signals import create_location_to_animal_relationship

class AnimalSoundsConfig(NautobotAppConfig):
    # ...

    def ready(self):
        super().ready()
        nautobot_database_ready.connect(create_location_to_animal_relationship, sender=self)

config = AnimalSoundsConfig
```

!!! warning
    It is crucial that you add the `sender=self` parameter to the `connect` method call - otherwise your signal handler will run as many times as the `NautobotAppConfig.ready` method is called, which may be a lot of times.

After writing this code, run `nautobot-server migrate` or `nautobot-server post_upgrade`, then restart the Nautobot server, and you should see that this custom Relationship has now been automatically created.

### Writing Data Migrations

Generally, documentation on this approach can be found in [the corresponding docs section of Django](https://docs.djangoproject.com/en/4.2/topics/migrations/#data-migrations).

There are, however, some specifics to adhere to in the Nautobot ecosystem. For every migration you write in a Nautobot app, you should also implement the `reverse_code` argument of `migrations.RunPython`. This is because the official uninstallation instructions for Nautobot apps require you to first run the migrations for that app in reverse to remove the app's data from the database.

The following is a simple example of a migration that adds the content types from two custom models in your Nautobot app to a default Nautobot status.

```python
# your_nautobot_app/migrations/0002_custom_status.py

from django.db import migrations

status_content_type_mapping = {
    "your_nautobot_app.custom_model_a": ["Active", "Decommissioned"],
    "your_nautobot_app.custom_model_b": ["Active", "Down", "Failed"],
}

def add_content_types_to_default_statuses(apps, schema_editor):
    """Adds additional content types to default statuses."""
    Status = apps.get_model("extras.Status")
    ContentType = apps.get_model("contenttypes.ContentType")
    for model, statuses in status_content_type_mapping.items():
        model_class = apps.get_model(model)
        for status in statuses:
            status_record, _ = Status.objects.get_or_create(name=status)
            status_record.content_types.add(
                ContentType.objects.get_for_model(model_class)
            )

def remove_content_types_from_default_statuses(apps, schema_editor):
    """Removes additional content types from default statuses."""
    Status = apps.get_model("extras.Status")
    ContentType = apps.get_model("contenttypes.ContentType")
    for model, statuses in status_content_type_mapping.items():
        model_class = apps.get_model(model)
        for status in statuses:
            status_record, _ = Status.objects.get_or_create(name=status)
            status_record.content_types.remove(
                ContentType.objects.get_for_model(model_class)
            )

class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0033_add__optimized_indexing"),
        ("your_nautobot_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=add_content_types_to_default_statuses, reverse_code=remove_content_types_from_default_statuses
        )
    ]
```
