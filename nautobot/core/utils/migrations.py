import sys

from django.db import models


def check_for_duplicates_with_natural_key_fields_in_migration(model_class, natural_key_fields):
    """
    Migration helper method to raise a RuntimeError if the existing model_class data contains incorrigible duplicate records.

    Args:
        model_class: Nautobot model class (Device, VirtualChassis and etc)
        natural_key_fields: Names of the fields serving as natural keys for the model_class.
    """
    duplicate_records = (
        model_class.objects.values(*natural_key_fields)
        .order_by()
        .annotate(count=models.Count("pk"))
        .filter(count__gt=1)
    )
    print("\n    Checking for duplicate records ...")
    if duplicate_records.exists():
        if len(natural_key_fields) > 1:
            print(
                f"    Duplicate {model_class.__name__} attributes '{(*natural_key_fields,)}' detected: {list(duplicate_records.values_list(*natural_key_fields))}",
                file=sys.stderr,
            )
        else:
            print(
                f"    Duplicate {model_class.__name__} attribute '{natural_key_fields[0]}' detected: {list(duplicate_records.values_list(natural_key_fields[0], flat=True))}",
                file=sys.stderr,
            )
        print(
            f"    Unable to proceed with migrations; in Nautobot 2.0+ attribute(s) {natural_key_fields} for these records must be unique.",
            file=sys.stderr,
        )
        raise RuntimeError("Duplicate records must be manually resolved before migrating.")


def update_object_change_ct_for_replaced_models(apps, new_app_model, replaced_apps_models, reverse_migration=False):
    """
    Update the ObjectChange content type references for replaced models to their new models' content type.

    Args:
        - apps: An instance of the Django 'apps' object.
        - new_app_model: A dict containing information about the new model, including the 'app_name' and 'model' names.
        - replaced_apps_models: A list of dict, each containing information about a replaced model, including the 'app_name' and 'model' names.
        - reverse_migration: If set to True, reverse the migration by updating references from new models to replaced models.
    """
    ObjectChange = apps.get_model("extras", "ObjectChange")
    NewModel = apps.get_model(new_app_model["app_name"], new_app_model["model"])
    ContentType = apps.get_model("contenttypes", "ContentType")
    new_model_ct = ContentType.objects.get_for_model(NewModel)

    for replaced_model in replaced_apps_models:
        ReplacedModel = apps.get_model(replaced_model["app_name"], replaced_model["model"])
        replaced_model_ct = ContentType.objects.get_for_model(ReplacedModel)

        if reverse_migration:
            ObjectChange.objects.filter(changed_object_type=new_model_ct).update(changed_object_type=replaced_model_ct)
            ObjectChange.objects.filter(related_object_type=new_model_ct).update(related_object_type=replaced_model_ct)
        else:
            ObjectChange.objects.filter(changed_object_type=replaced_model_ct).update(changed_object_type=new_model_ct)
            ObjectChange.objects.filter(related_object_type=replaced_model_ct).update(related_object_type=new_model_ct)


def migrate_content_type_references_to_new_model(apps, old_ct, new_ct):
    """When replacing a model, this will update references to the content type on related models such as tags and object changes.

    Since this only updates the content type and not the primary key, this is typically only useful when migrating to a new model
    and preserving the old instance's primary key.

    This will replace the old content type with the new content type on the following models:
        - ComputedField.content_type
        - CustomLink.content_type
        - ExportTemplate.content_type
        - Note.assigned_object_type
        - ObjectChange.changed_object_type
        - Relationship.source_type
        - Relationship.destination_type
        - RelationshipAssociation.source_type
        - RelationshipAssociation.destination_type
        - TaggedItem.content_type

    For these one-to-many and many-to-many relationships, the new content type is added
    to the related model's content type list, but the old content type is not removed:
        - CustomField.content_types
        - JobButton.content_types
        - JobHook.content_types
        - ObjectPermission.object_types
        - Status.content_types
        - Tag.content_types
        - WebHook.content_types

    This will also fix tags that were not properly enforced by adding the new model's content type to the tag's
    content types if an instance of the new model is using the tag.

    Args:
        apps (obj): An instance of the Django 'apps' object.
        old_ct (obj): An instance of ContentType for the old model.
        new_ct (obj): An instance of ContentType for the new model.

    """
    ComputedField = apps.get_model("extras", "ComputedField")
    CustomField = apps.get_model("extras", "CustomField")
    CustomLink = apps.get_model("extras", "CustomLink")
    ExportTemplate = apps.get_model("extras", "ExportTemplate")
    JobButton = apps.get_model("extras", "JobButton")
    JobHook = apps.get_model("extras", "JobHook")
    Note = apps.get_model("extras", "Note")
    ObjectChange = apps.get_model("extras", "ObjectChange")
    ObjectPermission = apps.get_model("users", "ObjectPermission")
    Relationship = apps.get_model("extras", "Relationship")
    RelationshipAssociation = apps.get_model("extras", "RelationshipAssociation")
    Status = apps.get_model("extras", "Status")
    Tag = apps.get_model("extras", "Tag")
    TaggedItem = apps.get_model("extras", "TaggedItem")
    WebHook = apps.get_model("extras", "WebHook")

    # Migrate ComputedField content type
    ComputedField.objects.filter(content_type=old_ct).update(content_type=new_ct)

    # Migrate CustomField content type
    for cf in CustomField.objects.filter(content_types=old_ct):
        cf.content_types.add(new_ct)

    # Migrate CustomLink content type
    CustomLink.objects.filter(content_type=old_ct).update(content_type=new_ct)

    # Migrate ExportTemplate content type - skip git export templates
    ExportTemplate.objects.filter(content_type=old_ct, owner_content_type=None).update(content_type=new_ct)

    # Migrate JobButton content type
    for job_button in JobButton.objects.filter(content_types=old_ct):
        job_button.content_types.add(new_ct)

    # Migrate JobHook content type
    for job_hook in JobHook.objects.filter(content_types=old_ct):
        job_hook.content_types.add(new_ct)

    # Migrate Note content type
    Note.objects.filter(assigned_object_type=old_ct).update(assigned_object_type=new_ct)

    # Migrate ObjectChange content type
    ObjectChange.objects.filter(changed_object_type=old_ct).update(changed_object_type=new_ct)

    # Migrate ObjectPermission content type
    for object_permission in ObjectPermission.objects.filter(object_types=old_ct):
        object_permission.object_types.add(new_ct)

    # Migrate Relationship content type
    Relationship.objects.filter(source_type=old_ct).update(source_type=new_ct)
    Relationship.objects.filter(destination_type=old_ct).update(destination_type=new_ct)

    # Migration RelationshipAssociation content type
    RelationshipAssociation.objects.filter(source_type=old_ct).update(source_type=new_ct)
    RelationshipAssociation.objects.filter(destination_type=old_ct).update(destination_type=new_ct)

    # Migrate Status content type
    for status in Status.objects.filter(content_types=old_ct):
        status.content_types.add(new_ct)

    # Migrate Tag content type
    for tag in Tag.objects.filter(content_types=old_ct):
        tag.content_types.add(new_ct)

    # Migrate TaggedItem content type
    TaggedItem.objects.filter(content_type=old_ct).update(content_type=new_ct)

    # Fix tags that were implemented incorrectly and didn't enforce content type
    # If a tag is related to an instance of a model, make sure the content type for that model exists on the tag object
    for tag_id in TaggedItem.objects.filter(content_type=new_ct).values_list("tag_id", flat=True).distinct():
        try:
            tag = Tag.objects.get(id=tag_id)
            if not tag.content_types.filter(id=new_ct.id).exists():
                tag.content_types.add(new_ct)
        except Tag.DoesNotExist:
            pass

    # Migrate WebHook content type
    for web_hook in WebHook.objects.filter(content_types=old_ct):
        web_hook.content_types.add(new_ct)
