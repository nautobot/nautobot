# Populating Extensibility Feature And Base Data

In many cases, an app may wish to make use of Nautobot's various extensibility features, such as [custom fields](../../../../user-guide/platform-functionality/customfield.md) or [relationships](../../../../user-guide/platform-functionality/relationship.md). It can be useful for an app to automatically create a custom field definition or relationship definition as a consequence of being installed and activated, so that everyday usage of the app can rely upon these definitions to be present.

Furthermore, sometimes apps might want to create a baseline of available data. This could, for example, be a baseline of circuit providers for an SSoT app that synchronizes circuit data.

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

While the signal handler approach works for most use cases, it does have its downsides. Other options for the population of base state are available, each with their own trade-offs:

- Signal Handlers on `nautobot_database_ready` (see above)
- [Django Onboard Tooling](https://docs.djangoproject.com/en/4.2/howto/initial-data/)
    - [Django Data Migrations](https://docs.djangoproject.com/en/4.2/topics/migrations/#data-migrations)
    - [Django Fixtures](https://docs.djangoproject.com/en/4.2/topics/db/fixtures/#fixtures)
- [Design Builder Jobs](https://docs.nautobot.com/projects/design-builder/en/latest/)
- Creating data in-place where needed

### Signal Handlers On `nautobot_database_ready`

**Pro**:

- Execution: Automatic
- Implementation: Easy

**Con**:

- Prevent Nautobot from starting when there are errors

### Django Data Migrations

**Pro**:

- Execution: Automatic
- Provide a clean way to delete any associated objects when uninstalling the app

**Con**:

- Implementation: Medium
- Prevent Nautobot from starting when there are errors
- Immutable—if you add new objects, you need to add a new migration
- Can't easily be feature-toggled (if you include settings lookups in your migration and later change those settings, the migrations will _not_ run again)

### Django Fixtures

**Pro**:

- Have good support for usage in unit tests
- Have good performance

**Con**:

- Execution: Manual
- Implementation: Medium
- Creating/updating them is not straight-forward, especially for big data sets

### Design Builder Jobs

**Pro**:

- Implementation: Easy

**Con**:

- Execution: Manual

### Creating Data In-Place Where Needed

This approach means to, for example, use `Status.objects.create(...)` in the place when you need it, such as a job.

**Pro**:

- Execution: Automatic
- Implementation: Easy

**Con**:

- Data is not available in the DB/API/GUI until the process that uses it runs
- Some care has to be taken to not duplicate information if multiple things depend on this data
