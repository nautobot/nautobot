from django.contrib.contenttypes.models import ContentType

from nautobot.core.models import BaseModel
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
from nautobot.extras.models import ContactAssociation, Note, ObjectChange
from nautobot.extras.querysets import NotesQuerySet
from nautobot.extras.signals import change_context_state


def get_change_context_state_data():
    change_id = change_context_state.get().change_id
    context = change_context_state.get().context
    context_detail = change_context_state.get().context_detail[:CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL]

    return {
        "change_id": change_id,
        "context": context,
        "context_detail": context_detail,
    }


def handle_change_logging_on_form_bulk_action(objs, user, context_state_data, action):
    """
    Handles the creation of change log entries for bulk actions(delete, update) performed on a queryset,
    and manages the deletion of associated entities for the 'delete' action.

    Args:
        objs: Model instance objects which needs changelog entries created for.
        user: User object.
        context_state_data: A dictionary containing context data for the action, including
                            'change_id', 'context', and 'context_detail'.
        action: Bulk operation action (e.g., ACTION_DELETE, ACTION_UPDATE).
    """
    associations_to_delete = set()
    notes_to_delete = set()
    objectchange_entries = []
    for instance in objs:
        if action == ObjectChangeActionChoices.ACTION_DELETE:
            if isinstance(instance, BaseModel):
                associations = ContactAssociation.objects.filter(
                    associated_object_type=ContentType.objects.get_for_model(type(instance)),
                    associated_object_id=instance.pk,
                ).values_list("pk", flat=True)
                associations_to_delete.update(associations)

            if hasattr(instance, "notes") and isinstance(instance.notes, NotesQuerySet):
                notes = instance.notes.values_list("pk", flat=True)
                notes_to_delete.update(notes)

        objectchange = instance.to_objectchange(action)
        objectchange.user = user
        objectchange.request_id = context_state_data["change_id"]
        objectchange.change_context = context_state_data["context"]
        objectchange.change_context_detail = context_state_data["context_detail"]
        objectchange_entries.append(objectchange)

    if associations_to_delete:
        ContactAssociation.objects.filter(pk__in=associations_to_delete).delete()
    if notes_to_delete:
        Note.objects.filter(pk__in=notes_to_delete).delete()
    ObjectChange.objects.bulk_create(objectchange_entries, batch_size=1000)
