# Region and Site to Location Migration Guide

In Nautobot 2.0.0, all the `Region` and `Site` related data models are being migrated to use `Location`. Below is a comprehensive guide for Nautobot users and Nautobot App developers to migrate their `Region` and `Site` related models and apps to `Location`.

## Migrate ObjectPermission instances in Nautobot from Region and Site to Location

Nautobot admins need to migrate `Site` and `Region` Related `ObjectPermission` instances to `Location`. The correct way to do it are documented below with practical examples.

### Region Specific ObjectPermission

Replace `Location` ContentType to `object_types` field of the `ObjectPermission` if it is not already present and add `"location_type__name": "Region"` to `constraints` field if the old `ObjectPermission` only allows operations on `Region` instances and not on `Site` instances.

Since `Location` has all the filters that `Region` had and they retain the same functionalities. We **do not** need to modify the `constraints` field of any `Region` specific `ObjectPermission` instances any further.

### Site Specific ObjectPermission

Replace `Location` ContentType to `object_types` field of the `ObjectPermission` if it is not already present and add `location_type__name: "Site"` to `constraints` field if the old `ObjectPermission` only allows operations on `Site` instances and not on `Region` instances.

The old `constraints` field for a `Site` specific `ObjectPermission` instance might look like this:

```json
{
    "name": "AMS01",
    "name__in": ["AMS01", "ATL01", "EDX01"],
    "slug": "ams01",
    "slug__in": ["ams01", "atl01", "edx01"],
    "id": "c12753e5-8f01-49a6-b0cf-bf8b460853a1",
    "id__in": ["c12753e5-8f01-49a6-b0cf-bf8b460853a1", "455038c3-4045-4b78-85f5-17d9f34cb9e8"],
    "region__name": "United States",
    "region__name__in": ["United States", "Greece", "England"],
    "region__slug": "united-states",
    "region__slug__in": ["united-states", "greece", "england"],
    "region__id": "f77f5706-e5b3-49e0-9749-b8f818319c40",
    "region__id__in": ["f77f5706-e5b3-49e0-9749-b8f818319c40", "7df99dc2-283a-4130-8125-60b9ca293131"],
    "region__parent__name": "North America",
    "region__parent__name__in": ["North America", "Europe"],
    "region__parent__slug": "north-america",
    "region__parent__slug__in": ["north-america", "europe"],
    "region__parent__id": "c1a816df-876f-44d4-8ea0-335898998780",
    "region__parent__id__in": ["c1a816df-876f-44d4-8ea0-335898998780", "a68b0838-d7fb-416c-b4ba-a3e464e552ba"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "region" with "parent" in the **Key** portion (before ":") of the data **not Value** (after ":").
    2. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in `...__id` and `...__id__in` Keys.

The updated JSON data might look like this:

```json
{
    "location_type__name": "Site",
    "name": "AMS01",
    "name__in": ["AMS01", "ATL01", "EDX01"],
    "slug": "ams01",
    "slug__in": ["ams01", "atl01", "edx01"],
    "id": "c12753e5-8f01-49a6-b0cf-bf8b460853a1",
    "id__in": ["c12753e5-8f01-49a6-b0cf-bf8b460853a1", "455038c3-4045-4b78-85f5-17d9f34cb9e8"],
    "parent__name": "United States",
    "parent__name__in": ["United States", "Greece", "England"],
    "parent__slug": "united-states",
    "parent__slug__in": ["united-states", "greece", "england"],
    "parent__id":  "f77f5706-e5b3-49e0-9749-b8f818319c40",
    "parent__id__in": ["f77f5706-e5b3-49e0-9749-b8f818319c40", "7df99dc2-283a-4130-8125-60b9ca293131"],
    "parent__parent__name": "North America",
    "parent__parent__name__in": ["North America", "Europe"],
    "parent__parent__slug": "north-america",
    "parent__parent__slug__in": ["north-america", "europe"],
    "parent__parent__id": "c1a816df-876f-44d4-8ea0-335898998780",
    "parent__parent__id__in": ["c1a816df-876f-44d4-8ea0-335898998780", "a68b0838-d7fb-416c-b4ba-a3e464e552ba"]
}
```

### Other Data Model Specific ObjectPermission e.g. Interface

The old `constraints` field for a `Site`/`Region` related data model's (e.g. `Interface`) `ObjectPermission` instance might look like this:

```json
{
    "device__site__name": "AMS01",
    "device__site__name__in": ["AMS01", "ATL01", "ETX02"],
    "device__site__slug": "ams01",
    "device__site__slug__in": ["ams01", "atl01", "etx02"],
    "device__site__id": "0ab47314-2944-45f6-b964-9e009fc48ce0",
    "device__site__id__in": ["0ab47314-2944-45f6-b964-9e009fc48ce0", "b09545d4-6e2b-471e-8f07-27f25ca308f5"],
    "device__site__region__name": "United States",
    "device__site__region__name__in": ["United States", "United Kingdom", "Greece"],
    "device__site__region__slug": "united-states",
    "device__site__region__slug__in": ["united-states", "united-kingdom", "greece"],
    "device__site__region__id": "f1a79a3c-d980-40e1-979d-abdb0f83388e",
    "device__site__region__id__in": ["f1a79a3c-d980-40e1-979d-abdb0f83388e", "6335a61e-503d-463c-99c2-9c87ef8354d9"],
    "device__site__region__parent__name": "North America",
    "device__site__region__parent__name__in": ["North America", "Europe", "South America"],
    "device__site__region__parent__slug": "north-america",
    "device__site__region__parent__slug__in": ["north-america", "europe", "south-america"],
    "device__site__region__parent__id": "6695809c-b33b-4f12-b0de-a4969000434d",
    "device__site__region__parent__id__in": ["6695809c-b33b-4f12-b0de-a4969000434d", "e51d07bb-3fcf-4306-9d87-6b1ff6dd6378"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "site" with "location" in the **Key** portion (before ":") of the data **not Value** (after ":").
    2. Replace all occurrences of "region" with "parent" in the **Key** portion (before ":") of the data **not Value** (after ":").
    3. Add `"device__location__location_type__name": "Site"` if the old `ObjectPermission` only allows operations on `Interfaces` of `Device` instances assigned to `Sites`.
    4. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in `...__id` and `...__id__in` Keys.

The updated JSON data might look like this:

```json
{
    "device__location__location_type__name": "Site",
    "device__location__name": "AMS01",
    "device__location__name__in": ["AMS01", "ATL01", "ETX02"],
    "device__location__slug": "ams01",
    "device__location__slug__in": ["ams01", "atl01", "etx02"],
    "device__location__id": "0ab47314-2944-45f6-b964-9e009fc48ce0",
    "device__location__id__in": ["0ab47314-2944-45f6-b964-9e009fc48ce0", "b09545d4-6e2b-471e-8f07-27f25ca308f5"],
    "device__location__parent__name": "United States",
    "device__location__parent__name__in": ["United States", "United Kingdom", "Greece"],
    "device__location__parent__slug": "united-states",
    "device__location__parent__slug__in": ["united-states", "united-kingdom", "greece"],
    "device__location__parent__id": "f1a79a3c-d980-40e1-979d-abdb0f83388e",
    "device__location__parent__id__in": ["f1a79a3c-d980-40e1-979d-abdb0f83388e", "6335a61e-503d-463c-99c2-9c87ef8354d9"],
    "device__location__parent__parent__name": "North America",
    "device__location__parent__parent__name__in": ["North America", "Europe", "South America"],
    "device__location__parent__parent__slug": "north-america",
    "device__location__parent__parent__slug__in": ["north-america", "europe", "south-america"],
    "device__location__parent__parent__id": "6695809c-b33b-4f12-b0de-a4969000434d",
    "device__location__parent__parent__id__in": ["6695809c-b33b-4f12-b0de-a4969000434d", "e51d07bb-3fcf-4306-9d87-6b1ff6dd6378"]
}
```

### Other Data Model Specific ObjectPermission e.g. Note

The old `constraints` field for a `Site`/`Region` related data model's (e.g. `Note`) `ObjectPermission` instance might look like this:

```json
{
    "assigned_object_type": "dcim.site",
    "assigned_object_id": "932d94ee-5571-40a0-903f-4274fcfbed32",
    "assigned_object_id__in": ["932d94ee-5571-40a0-903f-4274fcfbed32", "e383db9a-dd55-464d-9e56-2f18bc03b32c"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "dcim.site" and/or "dcim.region" with "dcim.location" in the **Value** portion (after ":") of the `assigned_object_type` Key.
    2. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in the `assigned_object_id` and `assigned_object_id__in` Keys.

The updated JSON data might look like this:

```json
{
    "assigned_object_type": "dcim.location",
    "assigned_object_id": "932d94ee-5571-40a0-903f-4274fcfbed32",
    "assigned_object_id__in": ["932d94ee-5571-40a0-903f-4274fcfbed32", "e383db9a-dd55-464d-9e56-2f18bc03b32c"]
}
```

## Region and Site Related Data Model Migration Guide For Existing Nautobot App installations

In Nautobot 2.0.0, all the `Region` and `Site` related data models are being migrated to use `Location`. Below is a comprehensive guide for Nautobot App developers to migrate their `Region` and `Site` related data models to `Location`.

We will be using `ExampleModel` as a relatively simple and hands-on example throughout this guide to better your understanding of the migration process.

### Before you Begin

!!! warning
    You **must** perform these steps before proceeding. Failing to follow them properly could result in data loss. **Always** backup your database before performing any migration steps.  
Before you follow the guide, please make sure that these operations are completed:  

1. Make sure your working Nautobot is on Version 1.5.x with baseline migrations all run.  
2. Stop Nautobot Server.  
3. Create a backup of your Nautobot database. (Check out the [Export Data Guide](../installation/migrating-from-postgresql.md#export-data-from-postgresql) for this operation)
4. Update installed version of Nautobot to 2.0.0.  
5. Run `nautobot-server migrate dcim 0030_migrate_region_and_site_data_to_locations`. (This operation will ensure that `("dcim", "0030_migrate_region_and_site_data_to_locations")` is the latest migration applied to your Nautobot instance and that `("dcim", "0034_remove_region_and_site")` is **not** applied. **Failure to complete this step will result in data loss**)  

After you complete those operations, follow the guide below for each of your installed apps to:  

1. Make all necessary migration files for each app.  
2. Run `nautobot-server migrate [app_name]` to apply those migration files to each app.  
3. Finally, Start Nautobot Server after **all** the migration files are applied and **all** your affected apps are updated.  

### Add Location Fields to Site and Region Related Data Models

If the `ExampleModel` currently has a `site` ForeignKey field but it does not have a `location` ForeignKey field, you will need to add the `location` field before any other migrations in this guide.

!!! note
    You can skip this step only if your data models already have both a `site` (or `region`) field and a `location` field.

```python
# models.py

class ExampleModel(OrganizationalModel):
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=20, help_text="The name of this Example.")
...
```

**DO NOT** delete the `site` ForeignKey field yet. As a first step, just add a `ForeignKey` to `dcim.Location` with all other arguments identical to the existing `dcim.Site` `ForeignKey`:

```python
# models.py

class ExampleModel(OrganizationalModel):
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=20, help_text="The name of this Example.")
...
```

Make the migration file by running `nautobot-server makemigrations [app_name] -n [migration_name]`, for example:

```shell
nautobot-server makemigrations example_app -n add_location_field_to_example_model
```

### Create an Empty Migration File and Write the Data Migration

After you make sure that all `Site`/`Region` related models have `location` fields on them, it is time to migrate `Site`/`Region` references in your data to `Location`.

Django doesn't automatically know how to do this; we have to create an empty migration file and write the migration script ourselves. This is also known as a [data migration](https://docs.djangoproject.com/en/3.2/topics/migrations/#data-migrations).

Create a migration file first by running `nautobot-server makemigrations [app_name] -n [migration_file_name] --empty`, for example:

```shell
nautobot-server makemigrations example_app -n migrate_app_data_from_site_to_location --empty
```

The empty migration file will look like this with the only dependency being our previous migration that added a `location` ForeignKey field to our `ExampleModel`:

```python
# Generated by Django 3.2.17 on 2023-02-22 15:38
# 0008_migrate_example_model_data_from_site_to_location

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("example_app", "0007_add_location_field_to_example_model"),
    ]
    operations = []
```

!!! warning
    First we need to add a mandatory dependency to a Nautobot 2.0 migration file, namely `("dcim", "0030_migrate_region_and_site_data_to_locations")`. This dependent migration is very important as it creates the `Location` and `LocationType` records corresponding to the existing `Site`/`Region` records, which you will need to reference to migrate your data.
    **Without it, your data migration might not work!**

```python
    dependencies = [
        # The dcim migration creates the Site Type and Region Type Locations that
        # your data models are migrating to. It has to be run **before** this migration.
        ("dcim", "0030_migrate_region_and_site_data_to_locations"),
        ("example_app", "0007_add_location_field_to_example_model"),
    ]
```

Before we write the function that will perform the data migration, please note that Nautobot's `dcim` `0029` migration helpfully added and populated a Foreign Key called `migrated_location` on all `Region` and `Site` records. `migrated_location` stores the new location records that have the same names and other attributes as their respective `Sites`. That means all you need to do is query `ExampleModel` instances that have non-null `site` fields and null `location` fields and point the `location` field on your object to the site's `migrated_location` attribute, for example:

```python
example_model.location = example_model.site.migrated_location
```

Below is what the function might look like:

```python
def migrate_example_model_data_to_locations(apps, schema_editor):
    # Always use the provided `apps` to look up models
    # rather than importing them directly!
    ExampleModel = apps.get_model("example_app", "examplemodel")
    LocationType = apps.get_model("dcim", "locationtype")
    Location = apps.get_model("dcim", "location")

    # Query ExampleModel instances with non-null site field
    example_models = ExampleModel.objects.filter(
        site__isnull=False, location__isnull=True
    ).select_related("site", "location")
    for example_model in example_models:
        # Point the location field to the corresponding
        # "Site" LocationType Location stored in migrate_location
        example_model.location = example_model.site.migrated_location
    ExampleModel.objects.bulk_update(example_models, ["location"], 1000)
```

Finally, we need to add `migrations.RunPython` to the `operations` attribute in the migration class to execute this function when the migration is applied:

```python
    operations = [
        migrations.RunPython(
            # Execute the function
            code=migrate_example_model_data_to_locations,
            reverse_code=migrations.operations.special.RunPython.noop,
        )
    ]

```

The final migration file might look like this:

```python
# Generated by Django 3.2.17 on 2023-02-22 15:38
# 0008_migrate_example_model_data_from_site_to_location

from django.db import migrations

def migrate_example_model_data_to_locations(apps, schema_editor):

    ExampleModel = apps.get_model("example_app", "examplemodel")
    LocationType = apps.get_model("dcim", "locationtype")
    Location = apps.get_model("dcim", "location")
    # Get "Site" LocationType
    site_location_type = LocationType.objects.get(name="Site")

    # Query ExampleModel instances with non-null site field
    example_models = ExampleModel.objects.filter(
        site__isnull=False, location__isnull=True
    ).select_related("site", "location")
    for example_model in example_models:
        # Point the location field to the corresponding "Site" LocationType Location
        # with the same name.
        example_model.location = example_model.site.migrated_location
    ExampleModel.objects.bulk_update(example_models, ["location"], 1000)

class Migration(migrations.Migration):
    dependencies = [
        # The dcim migration creates the Site Type and Region Type Locations that
        # your data models are migrating to.
        # Therefore, It has to be run **before** this migration.
        ("dcim", "0030_migrate_region_and_site_data_to_locations"),
        ("example_app", "0007_add_location_field_to_example_model"),
    ]
    operations = [
        migrations.RunPython(
            # Execute the function
            code=migrate_example_model_data_to_locations,
            reverse_code=migrations.operations.special.RunPython.noop,
        )
    ]
```

### Remove Site/Region Related Fields from Migrated Data Models

After the data migration is successful, we need to remove the `site`/`region` fields from your data model so that Nautobot will be able to remove the `Site` and `Region` models. Note that we need to remove those attributes in a separate migration file from the previous one, as it's never a good practice to combine data migrations and schema migrations in the same file. You can do this by simply removing the `site`/`region` attributes from your model class:

```python
# models.py
class ExampleModel(OrganizationalModel):
    # note that site field is gone
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=20, help_text="The name of this Example.")
...
```

After removing the `site` attribute, make the migration file by running `nautobot-server makemigrations [app_name] -n [migration_name]`, for example:

```shell
nautobot-server makemigrations example_app -n remove_site_field_from_example_model
```

The migration file might look like this:

```python
# Generated by Django 3.2.17 on 2023-02-22 17:09
# 0009_remove_site_field_from_example_model.py

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('example_app', '0008_migrate_example_model_data_from_site_to_location'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='examplemodel',
            name='site',
        ),
    ]
```

!!! important
    Before you apply this migration, you have to add a `run_before` attribute in this migration file to make sure that you remove `site`/`region` fields before `Site` and `Region` models themselves are removed. **Without it, your migration files might be out of order and your app will not start**.

```python
    # Ensure this migration is run before the migration that removes Region and Site Models
    run_before = [
        # TODO we need to change the name when PR #3313 is merged and migrations files are reordered.
        ("dcim", "0034_remove_region_and_site"),
    ]
```

The final migration file might look like this:

```python
# Generated by Django 3.2.17 on 2023-02-22 17:09
# 0009_remove_site_field_from_example_model.py

from django.db import migrations

class Migration(migrations.Migration):
    
    # Ensure this migration is run before the migration that removes Region and Site Models
    run_before = [
        # TODO we need to change the name when PR #3313 is merged and migrations files are reordered.
        ("dcim", "0034_remove_region_and_site"),
    ]
    dependencies = [
        ("example_app", "0008_migrate_example_model_data_from_site_to_location"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="examplemodel",
            name="site",
        ),
    ]
```

Apply the migration files by running `nautobot-server migrate [app_name]`, for example:

```shell
nautobot-server migrate example_app
```

## Region and Site Related Data Model Migration Guide For New Nautobot App installations in an Existing Nautobot 2.0 Environment
