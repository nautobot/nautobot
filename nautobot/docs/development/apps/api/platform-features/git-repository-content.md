# Loading Data from a Git Repository

It's possible for an app to register additional types of data that can be provided by a [Git repository](../../../../user-guide/platform-functionality/gitrepository.md) and be automatically notified when such a repository is refreshed with new data. By default, Nautobot looks for an iterable named `datasource_contents` within a `datasources.py` file. (This can be overridden by setting `datasource_contents` to a custom value on the app's `NautobotAppConfig`.) An example is below.

```python
# datasources.py
import yaml
import os

from nautobot.extras.choices import LogLevelChoices
from nautobot.apps.datasources import DatasourceContent

from .models import Animal


def refresh_git_animals(repository_record, job_result, delete=False):
    """Callback for GitRepository updates - refresh Animals managed by it."""
    if 'nautobot_animal_sounds.Animal' not in repository_record.provided_contents or delete:
        # This repository is defined not to provide Animal records.
        # In a more complete worked example, we might want to iterate over any
        # Animals that might have been previously created by this GitRepository
        # and ensure their deletion, but for now this is a no-op.
        return

    # We have decided that a Git repository can provide YAML files in a
    # /animals/ directory at the repository root.
    animal_path = os.path.join(repository_record.filesystem_path, 'animals')
    for filename in os.listdir(animal_path):
        with open(os.path.join(animal_path, filename)) as fd:
            animal_data = yaml.safe_load(fd)

        # Create or update an Animal record based on the provided data
        animal_record, created = Animal.objects.update_or_create(
            name=animal_data['name'],
            defaults={'sound': animal_data['sound']}
        )

        # Record the outcome in the JobResult record
        job_result.log(
            "Successfully created/updated animal",
            obj=animal_record,
            level_choice=LogLevelChoices.LOG_INFO,
            grouping="animals",
        )


# Register that Animal records can be loaded from a Git repository,
# and register the callback function used to do so
datasource_contents = [
    (
        'extras.gitrepository',                                  # datasource class we are registering for
        DatasourceContent(
            name='animals',                                      # human-readable name to display in the UI
            content_identifier='nautobot_animal_sounds.animal',  # internal slug to identify the data type
            icon='mdi-paw',                                      # Material Design Icons icon to use in UI
            callback=refresh_git_animals,                        # callback function on GitRepository refresh
        )
    )
]
```

With this code, once your app is installed, the Git repository creation/editing UI will now include "Animals" as an option for the type(s) of data that a given repository may provide. If this option is selected for a given Git repository, your `refresh_git_animals` function will be automatically called when the repository is synced.
