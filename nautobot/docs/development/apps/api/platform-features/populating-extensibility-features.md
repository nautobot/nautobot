# Populating Extensibility Feature And Base Data

In many cases, an app may wish to make use of Nautobot's various extensibility features, such as [custom fields](../../../../user-guide/platform-functionality/customfield.md) or [relationships](../../../../user-guide/platform-functionality/relationship.md). It can be useful for an app to automatically create a custom field definition or relationship definition as a consequence of being installed and activated, so that everyday usage of the app can rely upon these definitions to be present.

Furthermore, sometimes apps might want to create a baseline of available data. This could, for example, be a baseline of circuit providers for a [Single Source of Truth](https://docs.nautobot.com/projects/ssot/en/latest/) integration that synchronizes circuit data or creating new default [statuses](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/status/) and/or [roles](https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/role/), or adding to the allowed content types for existing statuses and roles.

## Using A Signal Handler

+++ 1.2.0

In general, it is recommended to use custom [signal](https://docs.djangoproject.com/en/stable/topics/signals/), `nautobot_database_ready` that apps can register to listen for. This signal is triggered when `nautobot-server migrate` or `nautobot-server post_upgrade` is run after installing an app, and provides an opportunity for the app to make any desired additions to the database at this time.

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

## Advanced

While the signal handler approach works for most use cases, it does have its downsides. Other options for the population of base state are available, each with their own trade-offs. There is no single best option, you have to choose the one has the best properties for your specific need.

- Signal Handlers on `nautobot_database_ready` (see above)
- [Django Onboard Tooling](https://docs.djangoproject.com/en/4.2/howto/initial-data/)
    - [Django Data Migrations](https://docs.djangoproject.com/en/4.2/topics/migrations/#data-migrations)
    - [Django Fixtures](https://docs.djangoproject.com/en/4.2/topics/db/fixtures/#fixtures)
- [Design Builder Jobs](https://docs.nautobot.com/projects/design-builder/en/latest/)
- Creating data in-place where needed

The following table details points that are somewhat easily comparable between the different options.

| Option                                       | Startup Impact                       | Execution | Performance | Re-running | Idempotence | Modifications Possible      | Custom App Needed |
|----------------------------------------------|--------------------------------------|-----------|-------------|------------|-------------|-----------------------------|-------------------|
| Signal Handlers on `nautobot_database_ready` | Exceptions prevent container startup | Automatic | Average     | Possible   | Enforced    | Overwrite/crash on next run | Yes               |
| Django Data Migrations                       | Exceptions prevent container startup | Automatic | Average     | Impossible | N/A         | Yes                         | Yes               |
| Django Fixtures                              | N/A                                  | Manual    | Good        | Possible   | TBD         | Overwrite/Crash on next run | No                |
| Design Builder Jobs                          | N/A                                  | Manual    | Average     | Possible   | Possible    | Overwrite/Crash on next run | No                |
| Creating Data In-place Where Needed          | N/A                                  | Automatic | Average     | Possible   | Possible    | Overwrite/crash on next run | No                |

The following sections detail additional points that weren't possible to fit.

### Signal Handlers On `nautobot_database_ready`

- ➕ Can be updated in-place in later App releases
- Re-runs every time `nautobot-server migrate` or `nautobot-server post_upgrade` is run
    - ➖ Must be idempotent, as such it mustn't introduce duplicate records or errors if run repeatedly
    - ➖ May recreate or revert records that a user intentionally deleted or altered - if this is not desired it has to be accounted for and handled in the code
- ➖ Impacts Nautobot startup and upgrade performance, care needs to be taken

### Django Data Migrations

- ➕ Provide a clean way to delete any associated objects when uninstalling the app
- ➖ Immutable - if you add new objects, you need to add a new migration
- ➖ Can't easily be feature-toggled (if you include settings lookups in your migration and later change those settings, the migrations will _not_ run again)

### Django Fixtures

- ➕ Have good support for usage in unit tests
- ➖ Creating/updating them is not straight-forward, especially for big data sets

### Design Builder Jobs

Another option to easily create data within Nautobot is the [Design Builder App](https://docs.nautobot.com/projects/design-builder/en/latest/).

- ➖ The possibility of later user modifications to data must be accounted for and handled in the design

### Creating Data In-Place Where Needed

This approach means to, for example, use `Status.objects.get_or_create(...)` in the place when you need it, such as a job.

- ➕ Unnecessary/unused records are not created automatically
- ➖ Data is not available in the DB/API/GUI until the process that uses it runs
- ➖ Some care has to be taken to not duplicate information if multiple things depend on this data
- ➖ Later modifications may be error-prone if a given record/set of attributes is created/referenced in many locations
- ➖ User modifications to the data may result in side effects (renaming a status may result in a new status with the original name being recreated next time the code runs, etc.)
