import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q

from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    RelationshipSideChoices,
    RelationshipTypeChoices,
)
from nautobot.extras.models import (
    CustomField,
    Note,
    Relationship,
    RelationshipAssociation,
    Status,
    Tag,
)
from nautobot.utilities.deprecation import class_deprecated_in_favor_of
from nautobot.utilities.forms import (
    BulkEditForm,
    CommentField,
    CSVModelChoiceField,
    CSVModelForm,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)

logger = logging.getLogger(__name__)


__all__ = (
    "CustomFieldModelBulkEditFormMixin",
    "CustomFieldModelFilterFormMixin",
    "CustomFieldModelFormMixin",
    "NoteModelBulkEditFormMixin",
    "NoteModelFormMixin",
    "RelationshipModelBulkEditFormMixin",
    "RelationshipModelFilterFormMixin",
    "RelationshipModelFormMixin",
    "StatusModelBulkEditFormMixin",
    "StatusModelFilterFormMixin",
    "StatusModelCSVFormMixin",
    "TagsBulkEditFormMixin",
    # 2.0 TODO: remove the below deprecated aliases
    "AddRemoveTagsForm",
    "CustomFieldBulkEditForm",
    "CustomFieldFilterForm",
    "CustomFieldModelForm",
    "RelationshipModelForm",
    "StatusBulkEditFormMixin",
    "StatusFilterFormMixin",
)


#
# Form mixins
#


class CustomFieldModelFilterFormMixin(forms.Form):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self.model)

        super().__init__(*args, **kwargs)

        custom_fields = CustomField.objects.filter(content_types=self.obj_type).exclude(
            filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED
        )
        for cf in custom_fields:
            # 2.0 TODO: #824 cf.name to cf.slug throughout
            field_name = f"cf_{cf.name}"
            if cf.type == "json":
                self.fields[field_name] = cf.to_form_field(
                    set_initial=False, enforce_required=False, simple_json_filter=True
                )
            else:
                self.fields[field_name] = cf.to_form_field(set_initial=False, enforce_required=False)


class CustomFieldModelFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        self.custom_fields = []

        super().__init__(*args, **kwargs)

        self._append_customfield_fields()

    def _append_customfield_fields(self):
        """
        Append form fields for all CustomFields assigned to this model.
        """
        # Append form fields; assign initial values if modifying and existing object
        for cf in CustomField.objects.filter(content_types=self.obj_type):
            field_name = f"cf_{cf.slug}"
            if self.instance.present_in_database:
                self.fields[field_name] = cf.to_form_field(set_initial=False)
                # 2.0 TODO: #824 self.instance.cf.get(cf.slug)
                self.fields[field_name].initial = self.instance.cf.get(cf.name)
            else:
                self.fields[field_name] = cf.to_form_field()

            # Annotate the field in the list of CustomField form fields
            self.custom_fields.append(field_name)

    def clean(self):

        # Save custom field data on instance
        for field_name in self.custom_fields:
            # 2.0 TODO: #824 will let us just do:
            # self.instance.cf[field_name[3:]] = self.cleaned_data.get(field_name)
            # but for now we need:
            cf = CustomField.objects.get(slug=field_name[3:])
            self.instance.cf[cf.name] = self.cleaned_data.get(field_name)

        return super().clean()


class CustomFieldModelBulkEditFormMixin(BulkEditForm):
    # Note that this is a form mixin for bulk-editing custom-field-having models, not for the CustomField model itself!
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.custom_fields = []
        self.obj_type = ContentType.objects.get_for_model(self.model)

        # Add all applicable CustomFields to the form
        custom_fields = CustomField.objects.filter(content_types=self.obj_type)
        for cf in custom_fields:
            field_name = f"cf_{cf.slug}"
            # Annotate non-required custom fields as nullable
            if not cf.required:
                self.nullable_fields.append(field_name)
            self.fields[field_name] = cf.to_form_field(set_initial=False, enforce_required=False)
            # Annotate this as a custom field
            self.custom_fields.append(field_name)


class NoteFormBase(forms.Form):
    """Base fore the NoteModelFormMixin and NoteModelBulkEditFormMixin."""

    object_note = CommentField(label="Note")

    def save_note(self, *, instance, user):
        value = self.cleaned_data.get("object_note", "").strip()
        if value:
            note = Note.objects.create(
                note=value,
                assigned_object_type=self.obj_type,
                assigned_object_id=instance.pk,
                user=user,
            )
            logger.debug("Created %s", note)


class NoteModelBulkEditFormMixin(BulkEditForm, NoteFormBase):
    """Bulk-edit form mixin for models that support Notes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_type = ContentType.objects.get_for_model(self.model)


class NoteModelFormMixin(forms.ModelForm, NoteFormBase):
    def __init__(self, *args, **kwargs):
        self.obj_type = ContentType.objects.get_for_model(self._meta.model)

        super().__init__(*args, **kwargs)


class RelationshipModelBulkEditFormMixin(BulkEditForm):
    """Bulk-edit form mixin for models that support Relationships."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.obj_type = ContentType.objects.get_for_model(self.model)
        self.relationships = []

        self._append_relationships()

    def _append_relationships(self):
        """
        Append form fields for all Relationships assigned to this model.
        """
        source_relationships = Relationship.objects.filter(source_type=self.obj_type, source_hidden=False)
        self._append_relationships_side(source_relationships, RelationshipSideChoices.SIDE_SOURCE)

        dest_relationships = Relationship.objects.filter(destination_type=self.obj_type, destination_hidden=False)
        self._append_relationships_side(dest_relationships, RelationshipSideChoices.SIDE_DESTINATION)

    def _append_relationships_side(self, relationships, initial_side):
        """
        Helper method to _append_relationships, for processing one "side" of the relationships for this model.

        For different relationship types there are different expectations of the UI:

        - For one-to-one (symmetric or non-symmetric) it doesn't make sense to bulk-set this relationship,
          but we want it to be clearable/nullable.
        - For one-to-many (from the source, "one", side) we likewise want it clearable/nullable but not settable.
        - For one-to-many (from the destination, "many", side) a single value can be set, or it can be nulled.
        - For many-to-many (symmetric or non-symmetric) we provide "add" and "remove" multi-select fields,
          similar to the TagsBulkEditFormMixin behavior. No nullability is provided here.
        """
        for relationship in relationships:
            if relationship.symmetric:
                side = RelationshipSideChoices.SIDE_PEER
            else:
                side = initial_side
            peer_side = RelationshipSideChoices.OPPOSITE[side]

            # If this model is on the "source" side of the relationship, then the field will be named
            # "cr_<relationship-slug>__destination" since it's used to pick the destination object(s).
            # If we're on the "destination" side, the field will be "cr_<relationship-slug>__source".
            # For a symmetric relationship, both sides are "peer", so the field will be "cr_<relationship-slug>__peer"
            field_name = f"cr_{relationship.slug}__{peer_side}"

            if field_name in self.relationships:
                # This is a symmetric relationship that we already processed from the opposing "initial_side".
                # No need to process it a second time!
                continue

            if relationship.has_many(side):
                if relationship.type == RelationshipTypeChoices.TYPE_ONE_TO_MANY:
                    # Destination side of a one-to-many field - provide a standard form field for selecting the "one",
                    # as well as making this field nullable.
                    self.fields[field_name] = relationship.to_form_field(side=side)
                    self.nullable_fields.append(field_name)
                else:
                    # Many-to-many field - provide "add" and "remove" form fields like with tags, no nullable option.
                    self.fields[f"add_{field_name}"] = relationship.to_form_field(side=side)
                    self.fields[f"add_{field_name}"].label = "Add " + self.fields[f"add_{field_name}"].label
                    self.fields[f"remove_{field_name}"] = relationship.to_form_field(side=side)
                    self.fields[f"remove_{field_name}"].label = "Remove " + self.fields[f"remove_{field_name}"].label
            else:
                # The "one" side of a one-to-one or one-to-many relationship.
                # In this case, the only valid bulk-edit operation is nulling/clearing the relationship,
                # but the "Set null" checkbox only appears if we have a form field for the the relationship itself.
                # This could probably be refined, but for now we just add the field and disable it.
                self.fields[field_name] = relationship.to_form_field(side=side)
                self.fields[field_name].disabled = True
                self.nullable_fields.append(field_name)

            self.relationships.append(field_name)

    def save_relationships(self, *, instance, nullified_fields):
        """Helper method to be called from BulkEditView.post()."""
        # The below may seem inefficient as it re-loads the Relationship objects afresh for each instance;
        # however this is necessary as it applies the source/destination filters (if any) to determine
        # whether each relationship actually applies to the given instance.
        instance_relationships = instance.get_relationships(include_hidden=True)

        for side, relationships_data in instance_relationships.items():
            peer_side = RelationshipSideChoices.OPPOSITE[side]
            for relationship, relationshipassociation_queryset in relationships_data.items():
                field_name = f"cr_{relationship.slug}__{peer_side}"
                logger.debug(
                    "Processing relationship %s %s (field %s) for instance %s",
                    relationship,
                    side,
                    field_name,
                    instance,
                )
                if field_name in self.nullable_fields and field_name in nullified_fields:
                    logger.debug("Deleting existing relationship associations for %s on %s", relationship, instance)
                    relationshipassociation_queryset.delete()
                elif field_name in self.cleaned_data:
                    value = self.cleaned_data.get(field_name)
                    if value and not relationship.has_many(peer_side):
                        ra, created = RelationshipAssociation.objects.update_or_create(
                            relationship=relationship,
                            source_type=relationship.source_type,
                            destination_type=relationship.destination_type,
                            defaults={f"{peer_side}_id": value.pk},
                            **{f"{side}_id": instance.pk},
                        )
                        if created:
                            logger.debug("Created %s", ra)
                        else:
                            logger.debug("Updated %s", ra)
                else:
                    if f"add_{field_name}" in self.cleaned_data:
                        added = self.cleaned_data.get(f"add_{field_name}")
                        for target in added:
                            if peer_side != RelationshipSideChoices.SIDE_PEER:
                                ra, created = RelationshipAssociation.objects.get_or_create(
                                    relationship=relationship,
                                    source_type=relationship.source_type,
                                    destination_type=relationship.destination_type,
                                    **{
                                        f"{side}_id": instance.pk,
                                        f"{peer_side}_id": target.pk,
                                    },
                                )
                            else:
                                if (
                                    RelationshipAssociation.objects.filter(
                                        relationship=relationship,
                                        source_id=instance.pk,
                                        destination_id=target.pk,
                                    ).exists()
                                    or RelationshipAssociation.objects.filter(
                                        relationship=relationship,
                                        source_id=target.pk,
                                        destination_id=instance.pk,
                                    ).exists()
                                ):
                                    ra = None
                                    created = False
                                else:
                                    ra = RelationshipAssociation.objects.create(
                                        relationship=relationship,
                                        source_type=relationship.source_type,
                                        source_id=instance.pk,
                                        destination_type=relationship.destination_type,
                                        destination_id=target.pk,
                                    )
                                    created = True

                            if created:
                                ra.validated_save()
                                logger.debug("Created %s", ra)

                    if f"remove_{field_name}" in self.cleaned_data:
                        removed = self.cleaned_data.get(f"remove_{field_name}")

                        source_count = 0
                        destination_count = 0
                        if side in [RelationshipSideChoices.SIDE_SOURCE, RelationshipSideChoices.SIDE_PEER]:
                            source_count, _ = RelationshipAssociation.objects.filter(
                                relationship=relationship,
                                source_id=instance.pk,
                                destination_id__in=[target.pk for target in removed],
                            ).delete()
                        if side in [RelationshipSideChoices.SIDE_DESTINATION, RelationshipSideChoices.SIDE_PEER]:
                            destination_count, _ = RelationshipAssociation.objects.filter(
                                relationship=relationship,
                                source_id__in=[target.pk for target in removed],
                                destination_id=instance.pk,
                            ).delete()
                        logger.debug("Deleted %s RelationshipAssociation(s)", source_count + destination_count)


class RelationshipModelFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        self.relationships = []
        super().__init__(*args, **kwargs)

        self._append_relationships()

    def _append_relationships(self):
        """
        Append form fields for all Relationships assigned to this model.
        One form field per side will be added to the list.
        """
        for side, relationships in self.instance.get_relationships().items():
            for relationship, queryset in relationships.items():
                peer_side = RelationshipSideChoices.OPPOSITE[side]
                # If this model is on the "source" side of the relationship, then the field will be named
                # cr_<relationship-slug>__destination since it's used to pick the destination object(s).
                # If we're on the "destination" side, the field will be cr_<relationship-slug>__source.
                # For a symmetric relationship, both sides are "peer", so the field will be cr_<relationship-slug>__peer
                field_name = f"cr_{relationship.slug}__{peer_side}"
                self.fields[field_name] = relationship.to_form_field(side=side)

                # HTML5 validation for required relationship field:
                if relationship.required_on == side:
                    self.fields[field_name].required = True

                # if the object already exists, populate the field with existing values
                if self.instance.present_in_database:
                    if relationship.has_many(peer_side):
                        initial = [association.get_peer(self.instance) for association in queryset.all()]
                        self.fields[field_name].initial = initial
                    else:
                        association = queryset.first()
                        if association:
                            self.fields[field_name].initial = association.get_peer(self.instance)

                # Annotate the field in the list of Relationship form fields
                self.relationships.append(field_name)

    def clean(self):
        """
        First check for any required relationships errors and if there are any, add them via form field errors.
        Then verify that any requested RelationshipAssociations do not violate relationship cardinality restrictions.

        - For TYPE_ONE_TO_MANY and TYPE_ONE_TO_ONE relations, if the form's object is on the "source" side of
          the relationship, verify that the requested "destination" object(s) do not already have any existing
          RelationshipAssociation to a different source object.
        - For TYPE_ONE_TO_ONE relations, if the form's object is on the "destination" side of the relationship,
          verify that the requested "source" object does not have an existing RelationshipAssociation to
          a different destination object.
        """
        required_relationships_errors = self.Meta().model.required_related_objects_errors(
            output_for="ui", initial_data=self.cleaned_data, instance=self.instance
        )
        for error_dict in required_relationships_errors:
            for field, errors in error_dict.items():
                self.add_error(field, errors)

        for side, relationships in self.instance.get_relationships().items():
            for relationship in relationships:
                # The form field name reflects what it provides, i.e. the peer object(s) to link via this relationship.
                peer_side = RelationshipSideChoices.OPPOSITE[side]
                field_name = f"cr_{relationship.slug}__{peer_side}"

                # Is the form trying to set this field (create/update a RelationshipAssociation(s))?
                # If not (that is, clearing the field / deleting RelationshipAssociation(s)), we don't need to check.
                if field_name not in self.cleaned_data or not self.cleaned_data[field_name]:
                    continue

                # Are any of the objects we want a relationship with already entangled with another object?
                if relationship.has_many(peer_side):
                    target_peers = list(self.cleaned_data[field_name])
                else:
                    target_peers = [self.cleaned_data[field_name]]

                for target_peer in target_peers:
                    if target_peer.pk == self.instance.pk:
                        raise ValidationError(
                            {field_name: f"Object {self.instance} cannot form a relationship to itself!"}
                        )

                    if relationship.has_many(side):
                        # No need to check for existing RelationshipAssociations since this is a "many" relationship
                        continue

                    if not relationship.symmetric:
                        existing_peer_associations = RelationshipAssociation.objects.filter(
                            relationship=relationship,
                            **{
                                f"{peer_side}_id": target_peer.pk,
                            },
                        ).exclude(**{f"{side}_id": self.instance.pk})
                    else:
                        existing_peer_associations = RelationshipAssociation.objects.filter(
                            (
                                (Q(source_id=target_peer.pk) & ~Q(destination_id=self.instance.pk))
                                | (Q(destination_id=target_peer.pk) & ~Q(source_id=self.instance.pk))
                            ),
                            relationship=relationship,
                        )

                    if existing_peer_associations.exists():
                        raise ValidationError(
                            {field_name: f"{target_peer} is already involved in a {relationship} relationship"}
                        )

        super().clean()

    def _save_relationships(self):
        """Update RelationshipAssociations for all Relationships on form save."""

        for field_name in self.relationships:
            # The field name tells us the side of the relationship that it is providing peer objects(s) to link into.
            peer_side = field_name.split("__")[-1]
            # Based on the side of the relationship that our local object represents,
            # find the list of existing RelationshipAssociations it already has for this Relationship.
            side = RelationshipSideChoices.OPPOSITE[peer_side]
            filters = {
                "relationship": self.fields[field_name].model,
            }
            if side != RelationshipSideChoices.SIDE_PEER:
                filters.update({f"{side}_type": self.obj_type, f"{side}_id": self.instance.pk})
                existing_associations = RelationshipAssociation.objects.filter(**filters)
            else:
                existing_associations = RelationshipAssociation.objects.filter(
                    (
                        Q(source_type=self.obj_type, source_id=self.instance.pk)
                        | Q(destination_type=self.obj_type, destination_id=self.instance.pk)
                    ),
                    **filters,
                )

            # Get the list of target peer ids (PKs) that are specified in the form
            target_peer_ids = []
            if hasattr(self.cleaned_data[field_name], "__iter__"):
                # One-to-many or many-to-many association
                target_peer_ids = [item.pk for item in self.cleaned_data[field_name]]
            elif self.cleaned_data[field_name]:
                # Many-to-one or one-to-one association
                target_peer_ids = [self.cleaned_data[field_name].pk]
            else:
                # Unset/delete case
                target_peer_ids = []

            # Create/delete RelationshipAssociations as needed to match the target_peer_ids list

            # First, for each existing association, if it's one that's already in target_peer_ids,
            # we can discard it from target_peer_ids (no update needed to this association).
            # Conversely, if it's *not* in target_peer_ids, we should delete it.
            for association in existing_associations:
                for peer_id in target_peer_ids:
                    if peer_side != RelationshipSideChoices.SIDE_PEER:
                        if peer_id == getattr(association, f"{peer_side}_id"):
                            # This association already exists, so we can ignore it
                            target_peer_ids.remove(peer_id)
                            break
                    else:
                        if peer_id == association.source_id or peer_id == association.destination_id:
                            # This association already exists, so we can ignore it
                            target_peer_ids.remove(peer_id)
                            break
                else:
                    # This association is not in target_peer_ids, so delete it
                    association.delete()

            # Anything remaining in target_peer_ids now does not exist yet and needs to be created.
            for peer_id in target_peer_ids:
                relationship = self.fields[field_name].model
                if not relationship.symmetric:
                    association = RelationshipAssociation(
                        relationship=relationship,
                        **{
                            f"{side}_type": self.obj_type,
                            f"{side}_id": self.instance.pk,
                            f"{peer_side}_type": getattr(relationship, f"{peer_side}_type"),
                            f"{peer_side}_id": peer_id,
                        },
                    )
                else:
                    # Symmetric association - source/destination are interchangeable
                    association = RelationshipAssociation(
                        relationship=relationship,
                        source_type=self.obj_type,
                        source_id=self.instance.pk,
                        destination_type=self.obj_type,  # since this is a symmetric relationship this is OK
                        destination_id=peer_id,
                    )

                association.clean()
                association.save()

    def save(self, commit=True):

        obj = super().save(commit)
        if commit:
            self._save_relationships()

        return obj


class RelationshipModelFilterFormMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relationships = []
        self.obj_type = ContentType.objects.get_for_model(self.model)
        self._append_relationships()

    def _append_relationships(self):
        """
        Append form fields for all Relationships assigned to this model.
        """
        source_relationships = Relationship.objects.filter(source_type=self.obj_type, source_hidden=False)
        self._append_relationships_side(source_relationships, RelationshipSideChoices.SIDE_SOURCE)

        dest_relationships = Relationship.objects.filter(destination_type=self.obj_type, destination_hidden=False)
        self._append_relationships_side(dest_relationships, RelationshipSideChoices.SIDE_DESTINATION)

    def _append_relationships_side(self, relationships, initial_side):
        """
        Helper method to _append_relationships, for processing one "side" of the relationships for this model.
        """
        for relationship in relationships:
            if relationship.symmetric:
                side = RelationshipSideChoices.SIDE_PEER
            else:
                side = initial_side
            peer_side = RelationshipSideChoices.OPPOSITE[side]

            # If this model is on the "source" side of the relationship, then the field will be named
            # "cr_<relationship-slug>__destination" since it's used to pick the destination object(s).
            # If we're on the "destination" side, the field will be "cr_<relationship-slug>__source".
            # For a symmetric relationship, both sides are "peer", so the field will be "cr_<relationship-slug>__peer"
            field_name = f"cr_{relationship.slug}__{peer_side}"

            if field_name in self.relationships:
                # This is a symmetric relationship that we already processed from the opposing "initial_side".
                # No need to process it a second time!
                continue
            self.fields[field_name] = relationship.to_form_field(side=side)
            self.fields[field_name].empty_label = None
            self.relationships.append(field_name)


class StatusModelBulkEditFormMixin(forms.Form):
    """Mixin to add non-required `status` choice field to forms."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"] = DynamicModelChoiceField(
            required=False,
            queryset=Status.objects.all(),
            query_params={"content_types": self.model._meta.label_lower},
        )
        self.order_fields(self.field_order)  # Reorder fields again


class StatusModelFilterFormMixin(forms.Form):
    """
    Mixin to add non-required `status` multiple-choice field to filter forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"] = DynamicModelMultipleChoiceField(
            required=False,
            queryset=Status.objects.all(),
            query_params={"content_types": self.model._meta.label_lower},
            to_field_name="slug",
        )
        self.order_fields(self.field_order)  # Reorder fields again


class StatusModelCSVFormMixin(CSVModelForm):
    """Mixin to add a required `status` choice field to CSV import forms."""

    status = CSVModelChoiceField(
        queryset=Status.objects.all(),
        to_field_name="slug",
        help_text="Operational status",
    )


class TagsBulkEditFormMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add add/remove tags fields
        self.fields["add_tags"] = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
        self.fields["remove_tags"] = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)


# 2.0 TODO: Names below are only for backward compatibility with Nautobot 1.3 and earlier. Remove in 2.0


@class_deprecated_in_favor_of(TagsBulkEditFormMixin)
class AddRemoveTagsForm(TagsBulkEditFormMixin):
    pass


@class_deprecated_in_favor_of(CustomFieldModelBulkEditFormMixin)
class CustomFieldBulkEditForm(CustomFieldModelBulkEditFormMixin):
    pass


@class_deprecated_in_favor_of(CustomFieldModelFilterFormMixin)
class CustomFieldFilterForm(CustomFieldModelFilterFormMixin):
    pass


@class_deprecated_in_favor_of(CustomFieldModelFormMixin)
class CustomFieldModelForm(CustomFieldModelFormMixin):
    pass


@class_deprecated_in_favor_of(RelationshipModelFormMixin)
class RelationshipModelForm(RelationshipModelFormMixin):
    pass


@class_deprecated_in_favor_of(StatusModelBulkEditFormMixin)
class StatusBulkEditFormMixin(StatusModelBulkEditFormMixin):
    pass


@class_deprecated_in_favor_of(StatusModelFilterFormMixin)
class StatusFilterFormMixin(StatusModelFilterFormMixin):
    pass
