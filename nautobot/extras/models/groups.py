"""Dynamic Groups Models."""

import logging
from typing import Optional

from django import forms
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import pre_delete
from django.utils.functional import cached_property
import django_filters

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.forms.fields import DynamicModelChoiceField
from nautobot.core.forms.widgets import StaticSelect2
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.data import is_uuid
from nautobot.core.utils.deprecation import method_deprecated, method_deprecated_in_favor_of
from nautobot.core.utils.lookup import get_filterset_for_model, get_form_for_model
from nautobot.extras.choices import DynamicGroupOperatorChoices, DynamicGroupTypeChoices
from nautobot.extras.querysets import DynamicGroupMembershipQuerySet, DynamicGroupQuerySet
from nautobot.extras.utils import extras_features, FeatureQuery

logger = logging.getLogger(__name__)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class DynamicGroup(PrimaryModel):
    """A group of related objects sharing a common content-type."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    group_type = models.CharField(
        choices=DynamicGroupTypeChoices.CHOICES, max_length=16, default=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER
    )
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        verbose_name="Object Type",
        help_text="The type of object contained in this group.",
        related_name="dynamic_groups",
        limit_choices_to=FeatureQuery("dynamic_groups"),
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="managed_dynamic_groups",  # "dynamic_groups" clash with Tenant.dynamic_groups property
        blank=True,
        null=True,
    )
    filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        editable=False,
        default=dict,
        help_text="A JSON-encoded dictionary of filter parameters defining membership of this group",
    )
    children = models.ManyToManyField(
        "extras.DynamicGroup",
        help_text='"Child" groups that are combined together to define membership of this group',
        through="extras.DynamicGroupMembership",
        through_fields=("parent_group", "group"),
        related_name="parents",
    )

    objects = BaseManager.from_queryset(DynamicGroupQuerySet)()
    is_dynamic_group_associable_model = False

    clone_fields = ["content_type", "group_type", "filter", "tenant"]

    # This is used as a `startswith` check on field names, so these can be explicit fields or just
    # substrings.
    #
    # Currently this means skipping "computed fields" and "comments".
    #
    # - Computed fields are skipped because they are generated at call time and
    #   therefore cannot be queried
    # - Comments are skipped because they are TextFields that require an exact
    #   match and are better covered by the search (`q`) field.
    #
    # Type: tuple
    exclude_filter_fields = ("cpf_", "comments")  # Must be a tuple

    class Meta:
        ordering = ["content_type", "name"]

    def __str__(self):
        return self.name

    @property
    def model(self):
        """
        Access to the underlying Model class for this group's `content_type`.

        This class object is cached on the instance after the first time it is accessed.
        """

        if getattr(self, "_model", None) is None:
            try:
                model = self.content_type.model_class()
            except models.ObjectDoesNotExist:
                model = None

            self._model = model

        return self._model

    @property
    def filterset_class(self) -> Optional[type[django_filters.FilterSet]]:
        if getattr(self, "_filterset_class", None) is None:
            try:
                self._filterset_class = get_filterset_for_model(self.model)
            except TypeError:
                self._filterset_class = None
        return self._filterset_class

    @property
    def filterform_class(self) -> Optional[type[forms.Form]]:
        if getattr(self, "_filterform_class", None) is None:
            try:
                self._filterform_class = get_form_for_model(self.model, form_prefix="Filter")
            except TypeError:
                self._filterform_class = None
        return self._filterform_class

    @property
    def form_class(self) -> Optional[type[forms.Form]]:
        if getattr(self, "_form_class", None) is None:
            try:
                self._form_class = get_form_for_model(self.model)
            except TypeError:
                self._form_class = None
        return self._form_class

    @cached_property
    def _map_filter_fields(self):
        """Return all FilterForm fields in a dictionary."""

        # Fail gracefully with an empty dict if nothing is working yet.
        if self.form_class is None or self.filterform_class is None or self.filterset_class is None:
            return {}

        # Get model form and fields
        modelform = self.form_class()  # pylint: disable=not-callable
        modelform_fields = modelform.fields

        # Get filter form and fields
        filterform = self.filterform_class()  # pylint: disable=not-callable
        filterform_fields = filterform.fields

        # Get filterset and fields
        filterset = self.filterset_class()  # pylint: disable=not-callable
        filterset_fields = filterset.filters

        # Get dynamic group filter field mappings (if any)
        dynamic_group_filter_fields = getattr(self.model, "dynamic_group_filter_fields", {})

        # Whether or not to add missing form fields that aren't on the filter form.
        skip_missing_fields = getattr(self.model, "dynamic_group_skip_missing_fields", False)

        # 2.0 TODO(jathan): v1.4.0 hard-codes skipping method fields by default for now. Revisit as we
        # head to v2 and groom individual method filters on existing filtersets. Lower down inside
        # of `generate_query()` there is a test as to whether a method filter also has a
        # `generate_query_{filter_method}()` method on the filterset and processes it accordingly.
        skip_method_filters = True

        # Model form fields that aren't on the filter form.
        if not skip_missing_fields:
            missing_fields = set(modelform_fields).difference(filterform_fields)
        else:
            logger.debug("Will not add missing form fields due to model %s meta option.", self.model)
            missing_fields = set()

        # Try a few ways to see if a missing field can be added to the filter fields.
        for missing_field in missing_fields:
            # Skip excluded fields
            if missing_field.startswith(self.exclude_filter_fields):
                logger.debug("Skipping excluded form field: %s", missing_field)
                continue

            # In some cases, fields exist in the model form AND by another name in the filter form
            # (e.g. model form: `cluster` -> filterset: `cluster_id`) yet are omitted from the
            # filter form (e.g. filter form has "cluster_id" but not "cluster"). We only want to add
            # them if-and-only-if they aren't already in `filterform_fields`.
            if missing_field in dynamic_group_filter_fields:
                mapped_field = dynamic_group_filter_fields[missing_field]
                if mapped_field in filterform_fields:
                    logger.debug(
                        "Skipping missing form field %s; mapped to %s filter field", missing_field, mapped_field
                    )
                    continue

            # If the missing field isn't even in the filterset, move on.
            try:
                filterset_field = filterset_fields[missing_field]
            except KeyError:
                logger.debug("Skipping %s: doesn't have a filterset field", missing_field)
                continue

            # Get the missing model form field so we can use it to add to the filterform_fields.
            modelform_field = modelform_fields[missing_field]

            # Use filterset_field to generate the correct filterform_field for CharField.
            # Which is `MultiValueCharField`.
            if isinstance(modelform_field, forms.CharField):
                new_modelform_field = filterset_field.field
                modelform_field = new_modelform_field

            # For boolean fields, we want them to be nullable.
            if isinstance(modelform_field, forms.BooleanField):
                # Get ready to replace the form field w/ correct widget.
                new_modelform_field = filterset_field.field
                new_modelform_field.widget = modelform_field.widget
                modelform_field = new_modelform_field

            # FIXME(jathan); Figure out how we can do this autoamtically from the FilterSet so we
            # don't have to munge it here.
            # Null boolean fields need a special widget that doesn't save `False` when unchecked.
            if isinstance(modelform_field, forms.NullBooleanField):
                modelform_field.widget = StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)

            if isinstance(modelform_field, DynamicModelChoiceField):
                modelform_field = filterset_field.field

            # Filter fields should never be required!
            modelform_field.required = False
            modelform_field.widget.attrs.pop("required", None)

            # And initial values should also be ignored.
            modelform_field.initial = None

            # Carry over the `to_field_name` to the modelform_field.
            to_field_name = filterset_field.extra.get("to_field_name")
            if to_field_name is not None:
                modelform_field.to_field_name = to_field_name

            logger.debug("Added %s (%s) to filter fields", missing_field, modelform_field.__class__.__name__)
            filterform_fields[missing_field] = modelform_field

        # Filter out unwanted fields from the filterform
        for filterset_field_name, filterset_field in filterset_fields.items():
            # Skip filter fields that have methods defined. They are not reversible.
            if skip_method_filters and filterset_field.method is not None:
                # Don't skip method fields that also have a "generate_query_" method
                query_attr = (
                    filterset_field.method.__name__ if callable(filterset_field.method) else filterset_field.method
                )
                if hasattr(filterset, f"generate_query_{query_attr}"):
                    logger.debug(
                        "Keeping %s for filterform: has a `generate_query_` filter method", filterset_field_name
                    )
                    continue

                # Otherwise pop the method filter from the filter form.
                filterform_fields.pop(filterset_field_name, None)
                logger.debug("Deleting %s from filterform: has a filter method", filterset_field_name)

        # Reduce down to a final dict of desired fields.
        return_fields = {}
        for field_name, filter_field in filterform_fields.items():
            # Skip excluded fields
            if field_name.startswith(self.exclude_filter_fields):
                logger.debug("Skipping excluded filter field: %s", field_name)
                continue

            # Skip fields that were removed from the filterset fields
            if field_name not in filterset_fields:
                logger.debug("Skipping removed filterset field: %s", field_name)
                continue

            return_fields[field_name] = filter_field

        return return_fields

    def get_filter_fields(self):
        """Return a mapping of `{field_name: filter_field}` for this group's `content_type`."""
        # Fail cleanly until the object has been created.
        if self.model is None:
            return {}

        if not self.present_in_database:
            return {}

        return self._map_filter_fields

    @property
    def members(self):
        """
        Return the (cached) member objects for this group.

        If up-to-the-minute accuracy is needed, call `update_cached_members()` instead.
        """
        # Since associated_object is a GenericForeignKey, we can't just do:
        #     return self.static_group_associations.values_list("associated_object", flat=True)
        return self.model.objects.filter(
            # pylint: disable=no-member  # false positive about self.static_group_associations
            pk__in=self.static_group_associations(manager="all_objects").values_list("associated_object_id", flat=True)
        )

    @members.setter
    def members(self, value):
        """Set the member objects (QuerySet or list of records) for this staticly defined group."""
        if self.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
            raise ValidationError(
                f"Group {self} is not staticly defined, setting its members directly is not permitted."
            )
        return self._set_members(value)

    def _set_members(self, value):
        """Internal API for updating the static/cached members of this group."""
        if isinstance(value, models.QuerySet):
            if value.model != self.model:
                raise TypeError(f"QuerySet does not contain {self.model._meta.label_lower} objects")
            to_remove = self.members.only("id").difference(value.only("id"))
            self._remove_members(to_remove)
            to_add = value.only("id").difference(self.members.only("id"))
            self._add_members(to_add)
        else:
            for obj in value:
                if not isinstance(obj, self.model):
                    raise TypeError(f"{obj} is not a {self.model._meta.label_lower}")
            existing_members = self.members
            to_remove = [obj for obj in existing_members if obj not in value]
            self._remove_members(to_remove)
            to_add = [obj for obj in value if obj not in existing_members]
            self._add_members(to_add)

        return self.members

    _set_members.alters_data = True

    def add_members(self, objects_to_add):
        """Add the given list or QuerySet of objects to this staticly defined group."""
        if self.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
            raise ValidationError(f"Group {self} is not staticly defined, adding members directly is not permitted.")
        if isinstance(objects_to_add, models.QuerySet):
            if objects_to_add.model != self.model:
                raise TypeError(f"QuerySet does not contain {self.model._meta.label_lower} objects")
            objects_to_add = objects_to_add.only("id").difference(self.members.only("id"))
        else:
            for obj in objects_to_add:
                if not isinstance(obj, self.model):
                    raise TypeError(f"{obj} is not a {self.model._meta.label_lower}")
            existing_members = self.members
            objects_to_add = [obj for obj in objects_to_add if obj not in existing_members]
        return self._add_members(objects_to_add)

    add_members.alters_data = True

    def _add_members(self, objects_to_add):
        """
        Internal API for adding the given list or QuerySet of objects to the cached/static members of this group.

        Assumes that objects_to_add has already been filtered to exclude any existing member objects.
        """
        if self.group_type == DynamicGroupTypeChoices.TYPE_STATIC:
            for obj in objects_to_add:
                # We don't use `.bulk_create()` currently because we want change logging for these creates.
                # Might be a good future performance improvement though.
                StaticGroupAssociation.all_objects.create(
                    dynamic_group=self, associated_object_type=self.content_type, associated_object_id=obj.pk
                )
        else:
            # Cached/hidden static group associations, so we can use bulk-create to bypass change logging.
            sgas = [
                StaticGroupAssociation(
                    dynamic_group=self, associated_object_type=self.content_type, associated_object_id=obj.pk
                )
                for obj in objects_to_add
            ]
            StaticGroupAssociation.all_objects.bulk_create(sgas, batch_size=1000)

    _add_members.alters_data = True

    def remove_members(self, objects_to_remove):
        """Remove the given list or QuerySet of objects from this staticly defined group."""
        if self.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
            raise ValidationError(f"Group {self} is not staticly defined, removing members directly is not permitted.")
        if isinstance(objects_to_remove, models.QuerySet):
            if objects_to_remove.model != self.model:
                raise TypeError(f"QuerySet does not contain {self.model._meta.label_lower} objects")
        else:
            for obj in objects_to_remove:
                if not isinstance(obj, self.model):
                    raise TypeError(f"{obj} is not a {self.model._meta.label_lower}")
        return self._remove_members(objects_to_remove)

    remove_members.alters_data = True

    def _remove_members(self, objects_to_remove):
        """Internal API for removing the given list or QuerySet from the cached/static members of this Group."""
        from nautobot.extras.signals import _handle_deleted_object  # avoid circular import

        # For non-static groups, we aren't going to change log the StaticGroupAssociation deletes anyway,
        # so save some performance on signals -- important especially when we're dealing with thousands of records
        if self.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
            logger.debug("Temporarily disconnecting the _handle_deleted_object signal for performance")
            pre_delete.disconnect(_handle_deleted_object)
        try:
            if isinstance(objects_to_remove, models.QuerySet):
                StaticGroupAssociation.all_objects.filter(
                    dynamic_group=self,
                    associated_object_type=self.content_type,
                    associated_object_id__in=objects_to_remove.values_list("id", flat=True),
                ).delete()
            else:
                pks_to_remove = [obj.id for obj in objects_to_remove]
                StaticGroupAssociation.all_objects.filter(
                    dynamic_group=self,
                    associated_object_type=self.content_type,
                    associated_object_id__in=pks_to_remove,
                ).delete()
        finally:
            if self.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
                logger.debug("Re-connecting the _handle_deleted_object signal")
                pre_delete.connect(_handle_deleted_object)

    _remove_members.alters_data = True

    @property
    @method_deprecated("Members are now cached in the database via StaticGroupAssociations rather than in Redis.")
    def members_cache_key(self):
        """Obsolete cache key for this group's members."""
        return f"nautobot.extras.dynamicgroup.{self.id}.members_cached"

    @property
    @method_deprecated_in_favor_of(members.fget)
    def members_cached(self):
        """Deprecated  - use `members()` instead."""
        return self.members

    def update_cached_members(self, members=None):
        """
        Update the cached members of this group and return the resulting members.
        """
        if members is None:
            if self.group_type in (
                DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
                DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
            ):
                members = self._get_group_queryset()
            elif self.group_type == DynamicGroupTypeChoices.TYPE_STATIC:
                return self.members  # nothing to do
            else:
                raise RuntimeError(f"Unknown/invalid group_type {self.group_type}")

        logger.debug("Refreshing members cache for %s", self)
        self._set_members(members)
        logger.debug("Refreshed cache for %s, now with %d members", self, self.count)

        return members

    update_cached_members.alters_data = True

    def has_member(self, obj, use_cache=False):
        """
        Return True if the given object is a member of this group.

        Does check if object's content type matches this group's content type.

        Args:
            obj (django.db.models.Model): The object to check for membership.
            use_cache (bool, optional): Obsolete; cache is now always used.

        Returns:
            bool: True if the object is a member of this group, otherwise False.
        """

        # Object's class may have content type cached, so check that first.
        try:
            if type(obj)._content_type.id != self.content_type_id:
                return False
        except AttributeError:
            # Object did not have `_content_type` even though we wanted to use it.
            if ContentType.objects.get_for_model(obj).id != self.content_type_id:
                return False

        return self.members.filter(pk=obj.pk).exists()

    @property
    def count(self):
        """Return the (cached) number of member objects in this group."""
        return self.members.count()

    def get_group_members_url(self):
        """Get URL to group members."""
        if self.model is None:
            return ""

        return self.get_absolute_url() + "?tab=members"

    def set_filter(self, form_data):
        """
        Set all desired fields from `form_data` into `filter` dict.

        Args:
            form_data (dict): Dict of filter parameters, generally from a filter form's `cleaned_data`
        """
        if self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
            raise ValidationError(f"Group {self} is not a filter-defined group (instead, group_type {self.group_type})")

        # Get the authoritative source of filter fields we want to keep.
        filter_fields = self.get_filter_fields()

        # Check for potential legacy filters from v1.x that is no longer valid in v2.x.
        # Raise the validation error in DynamicGroup form handling.
        error_message = ""
        invalid_filter_exist = False
        for key, value in self.filter.items():
            if key not in filter_fields:
                invalid_filter_exist = True
                error_message += f"Invalid filter '{key}' detected with value {value}\n"
        if invalid_filter_exist:
            raise ValidationError(error_message)

        # Populate the filterset from the incoming `form_data`. The filterset's internal form is
        # used for validation, will be used by us to extract cleaned data for final processing.
        filterset_class = self.filterset_class
        filterset_class.form_prefix = "filter"
        filterset = filterset_class(form_data)

        # Use the auto-generated filterset form perform creation of the filter dictionary.
        filterset_form = filterset.form

        # Get the declared form for any overloaded form field definitions.
        declared_form = get_form_for_model(filterset._meta.model, form_prefix="Filter")

        # It's expected that the incoming data has already been cleaned by a form. This `is_valid()`
        # call is primarily to reduce the fields down to be able to work with the `cleaned_data` from the
        # filterset form, but will also catch errors in case a user-created dict is provided instead.
        if not filterset_form.is_valid():
            raise ValidationError(filterset_form.errors)

        # Perform some type coercions so that they are URL-friendly and reversible, excluding any
        # empty/null value fields.
        new_filter = {}
        for field_name in filter_fields:
            field = declared_form.declared_fields.get(field_name, filterset_form.fields[field_name])
            field_value = filterset_form.cleaned_data[field_name]

            # TODO: This could/should check for both "convenience" FilterForm fields (ex: DynamicModelMultipleChoiceField)
            # and literal FilterSet fields (ex: MultiValueCharFilter).
            if isinstance(field, forms.ModelMultipleChoiceField):
                field_to_query = field.to_field_name or "pk"
                new_value = [getattr(item, field_to_query) for item in field_value]

            elif isinstance(field, forms.ModelChoiceField):
                field_to_query = field.to_field_name or "pk"
                new_value = getattr(field_value, field_to_query, None)

            else:
                new_value = field_value

            # Don't store empty values like `None`, [], etc.
            if new_value in (None, "", [], {}):
                logger.debug("[%s] Not storing empty value (%s) for %s", self.name, field_value, field_name)
                continue

            logger.debug("[%s] Setting filter field {%s: %s}", self.name, field_name, field_value)
            new_filter[field_name] = new_value

        self.filter = new_filter

    set_filter.alters_data = True

    def get_initial(self):
        """
        Return a form-friendly version of `self.filter` for initial form data.

        This is intended for use to populate the dynamically-generated filter form created by
        `generate_filter_form()`.
        """
        initial_data = self.filter.copy()

        return initial_data

    # TODO: Rip this out once the dynamic filter form helper replaces this in the web UI.
    def generate_filter_form(self):
        """
        Generate a `FilterForm` class for use in `DynamicGroup` edit view.

        This form is used to popoulate and validate the filter dictionary.

        If a form cannot be created for some reason (such as on a new instance when rendering the UI
        "add" view), this will return `None`.
        """
        filter_fields = self.get_filter_fields()

        try:

            class FilterForm(self.filterform_class):
                prefix = "filter"

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.fields = filter_fields

        except (AttributeError, TypeError):
            return None

        return FilterForm

    def clean_filter(self):
        """Clean for `self.filter` that uses the filterset_class to validate."""
        if not isinstance(self.filter, dict):
            raise ValidationError({"filter": "Filter must be a dict"})

        # Accessing `self.model` will determine if the `content_type` is not correctly set, blocking validation.
        if self.model is None:
            raise ValidationError({"filter": "Filter requires a `content_type` to be set"})
        if self.filterset_class is None:
            raise ValidationError({"filter": "Unable to locate the FilterSet class for this model."})

        if self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
            if self.filter:
                raise ValidationError({"filter": "Filter can only be set for groups of type `dynamic-filter`."})
        else:
            # Validate against the filterset's internal form validation.
            filterset = self.filterset_class(self.filter)  # pylint: disable=not-callable
            if not filterset.is_valid():
                raise ValidationError(filterset.errors)

    def delete(self, *args, **kwargs):
        """Check if we're a child and attempt to block delete if we are."""
        if self.parents.exists():
            raise models.ProtectedError(
                msg="Cannot delete DynamicGroup while child of other DynamicGroups.",
                protected_objects=set(self.parents.all()),
            )
        return super().delete(*args, **kwargs)

    def clean_fields(self, exclude=None):
        if exclude is None:
            exclude = []

        if "filter" not in exclude:
            self.clean_filter()

        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)

            if self.content_type != database_object.content_type:
                raise ValidationError({"content_type": "ContentType cannot be changed once created"})

            # TODO limit most changes to self.group_type as well.

    def _generate_query_for_filter(self, filter_field, value):
        """
        Return a `Q` object generated from a `filter_field` and `value`.

        Helper to `_generate_filter_based_query()`.

        Args:
            filter_field (Filter): filterset filter field instance
            value (Any): value passed to the filter
        """
        query = models.Q()
        if filter_field is None:
            logger.warning(f"Filter data is not valid for DynamicGroup {self}")
            return query

        field_name = filter_field.field_name

        # Attempt to account for `ModelChoiceFilter` where `to_field_name` MAY be set.
        to_field_name = getattr(filter_field.field, "to_field_name", None)
        if to_field_name is not None:
            field_name = f"{field_name}__{to_field_name}"

        lookup = f"{field_name}__{filter_field.lookup_expr}"
        # has_{field_name} boolean filters uses `isnull` lookup expressions
        # so when we generate queries for those filters we need to negate the value entered
        # e.g (has_interfaces: True) == (interfaces__isnull: False)
        if filter_field.lookup_expr == "isnull":
            value = not value

        # Explicitly call generate_query_{filter_method} for a method filter.
        if filter_field.method is not None and hasattr(filter_field.parent, "generate_query_" + filter_field.method):
            filter_method = getattr(filter_field.parent, "generate_query_" + filter_field.method)
            query |= filter_method(value)

        # Explicitly call `filter_field.generate_query` for a reversible filter.
        elif hasattr(filter_field, "generate_query"):
            # Is this a list of strings? Well let's resolve it to related model objects so we can
            # pass it to `generate_query` to get a correct Q object back out. When values are being
            # reconstructed from saved filters, lists of names are common e.g. (`{"location": ["ams01",
            # "ams02"]}`, the value being a list of location names (`["ams01", "ams02"]`).
            if value and isinstance(value, list) and isinstance(value[0], str) and not is_uuid(value[0]):
                model_field = django_filters.utils.get_model_field(self._model, filter_field.field_name)
                related_model = model_field.related_model
                lookup_kwargs = {f"{to_field_name}__in": value}
                gq_value = related_model.objects.filter(**lookup_kwargs)
            else:
                gq_value = value
            query |= filter_field.generate_query(gq_value)

        # For vanilla multiple-choice filters, we want all values in a set union (boolean OR)
        # because we want ANY of the filter values to match. Unless the filter field is explicitly
        # conjoining the values, in which case we want a set intersection (boolean AND). We know this isn't right
        # since the resulting query actually does tag.name == tag_1 AND tag.name == tag_2, but django_filter does
        # not use Q evaluation for conjoined filters. This function is only used for the display, and the display
        # is good enough to get the point across.
        elif isinstance(filter_field, django_filters.MultipleChoiceFilter):
            for v in value:
                if filter_field.conjoined:
                    query &= models.Q(**filter_field.get_filter_predicate(v))
                else:
                    query |= models.Q(**filter_field.get_filter_predicate(v))

        # The method `get_filter_predicate()` is only available on instances or subclasses
        # of `MultipleChoiceFilter`, so we must construct a lookup if a filter is not
        # multiple-choice. This is safe for singular filters except `ModelChoiceFilter`, because they
        # do not support `to_field_name`.
        else:
            query |= models.Q(**{lookup: value})

        return query

    def _generate_filter_based_query(self):
        """
        Return a `Q` object generated from this group's filters.

        Helper to `generate_query()`.
        """
        if self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
            raise RuntimeError(f"{self} is not a dynamic-filter group")

        filterset = self.filterset_class(self.filter, self.model.objects.all())  # pylint: disable=not-callable
        query = models.Q()

        # In this case we want all filters for a group's filter dict in a set intersection (boolean
        # AND) because ALL filter conditions must match for the filter parameters to be valid.
        for field_name, value in filterset.data.items():
            filter_field = filterset.filters.get(field_name)
            query &= self._generate_query_for_filter(filter_field, value)

        return query

    def _perform_membership_set_operation(self, operator, query, next_set):
        """
        Perform set operation for a group membership.

        The `operator` and `next_set` are used to decide the appropriate action to take on the `query`.

        Args:
            operator (str): DynamicGroupOperatorChoices choice
            query (Q): Query so far
            next_set (Q): Additional query to apply based on the operator.

        Returns:
            Q: updated query object
        """
        if operator == "union":
            query |= next_set
        elif operator == "difference":
            query &= ~next_set
        elif operator == "intersection":
            query &= next_set

        return query

    def generate_query(self):
        """
        Return a `Q` object generated recursively from this dynamic group.
        """
        if self.group_type == DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
            return self._generate_filter_based_query()

        if self.group_type == DynamicGroupTypeChoices.TYPE_DYNAMIC_SET:
            query = models.Q()
            memberships = self.dynamic_group_memberships.all()
            # Enumerate the filters for each child group, trusting that they handle their own children.
            for membership in memberships:
                group = membership.group
                operator = membership.operator
                logger.debug("Processing group %s...", group)

                if group.group_type == DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
                    logger.debug("Query: %s -> %s -> %s", group, group.filter, operator)

                next_set = group.generate_query()
                query = self._perform_membership_set_operation(operator, query, next_set)

            return query

        # TODO? if self.group_type == DynamicGroupTypeChoices.TYPE_STATIC:

        raise RuntimeError(f"generate_query not implemented for group_type {self.group_type}")

    def _get_group_queryset(self):
        """Construct the queryset representing dynamic membership of this group."""
        query = self.generate_query()
        return self.model.objects.filter(query)

    # TODO: unused in core
    def add_child(self, child, operator, weight):
        """
        Add a child group including `operator` and `weight`.

        Args:
            child (DynamicGroup): child group to add
            operator (str): DynamicGroupOperatorChoices choice value used to dictate filtering behavior
            weight (int): Integer weight used to order filtering
        """
        if self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_SET:
            if self.filter or self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
                raise ValidationError(f"{self} is not a dynamic-set group.")
            else:
                # For backwards compatibility
                self.group_type = DynamicGroupTypeChoices.TYPE_DYNAMIC_SET
                self.validated_save()

        instance = self.children.through(parent_group=self, group=child, operator=operator, weight=weight)
        return instance.validated_save()

    add_child.alters_data = True

    # TODO: unused in core
    def remove_child(self, child):
        """
        Remove a child group.

        Args:
            child (DynamicGroup): child group to remove
        """
        if self.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_SET:
            raise ValidationError(f"{self} is not a dynamic-set group.")

        instance = self.children.through.objects.get(parent_group=self, group=child)
        return instance.delete()

    remove_child.alters_data = True

    def get_descendants(self, group=None):
        """
        Recursively return a list of the children of all child groups.

        Args:
            group (DynamicGroup): parent group to traverse from. If not set, this group (self) is used.
        """
        if group is None:
            group = self

        descendants = []
        for child_group in group.children.all():
            logger.debug("Processing group %s...", child_group)
            descendants.append(child_group)
            if child_group.children.exists():
                descendants.extend(child_group.get_descendants())

        return descendants

    def get_ancestors(self, group=None):
        """
        Recursively return a list of the parents of all parent groups.

        Args:
            group (DynamicGroup): child group to traverse from. If not set, this group (self) is used.
        """
        if group is None:
            group = self

        ancestors = []
        for parent_group in group.parents.all():
            logger.debug("Processing group %s...", parent_group)
            ancestors.append(parent_group)
            if parent_group.parents.exists():
                ancestors.extend(parent_group.get_ancestors())

        return ancestors

    # TODO: unused in core
    def get_siblings(self, include_self=False):
        """Return groups that share the same parents."""
        siblings = DynamicGroup.objects.filter(parents__in=self.parents.all())
        if include_self:
            return siblings

        return siblings.exclude(pk=self.pk)

    # TODO: this is an interesting definition of "root node", as a node with no children has is_root() = False??
    # TODO: unused in core
    def is_root(self):
        """Return whether this is a root node (has children, but no parents)."""
        return self.children.exists() and not self.parents.exists()

    # TODO: this is an interesting definition of "leaf node", as a node with no parents has is_leaf() = False??
    # TODO: unused in core
    def is_leaf(self):
        """Return whether this is a leaf node (has parents, but no children)."""
        return self.parents.exists() and not self.children.exists()

    # TODO: unused in core
    def get_ancestors_queryset(self):
        """Return a queryset of all ancestors."""
        pks = [obj.pk for obj in self.get_ancestors()]
        return self.ordered_queryset_from_pks(pks)

    # TODO: unused in core
    def get_descendants_queryset(self):
        """Return a queryset of all descendants."""
        pks = [obj.pk for obj in self.get_descendants()]
        return self.ordered_queryset_from_pks(pks)

    def ancestors_tree(self):
        """
        Return a nested mapping of ancestors with the following structure:

            {
                parent_1: {
                    grandparent_1: {},
                    grandparent_2: {},
                },
                parent_2: {
                    grandparent_3: {
                        greatgrandparent_1: {},
                    },
                    grandparent_4: {},
                }
            }

        Each key is a `DynamicGroup` instance.
        """
        tree = {}
        for f in self.parents.all():
            tree[f] = f.ancestors_tree()

        return tree

    def flatten_ancestors_tree(self, tree):
        """
        Recursively flatten a tree mapping of ancestors to a list, adding a `depth` attribute to each
        instance in the list that can be used for visualizing tree depth.

        Args:
            tree (dict): Output from `ancestors_tree()`
        """
        return self._flatten_tree(tree)

    # TODO: unused in core
    def descendants_tree(self):
        """
        Return a nested mapping of descendants with the following structure:

        {
            child_1: {
                grandchild_1: {},
                grandchild_2: {},
            },
            child_2: {
                grandchild_3: {
                     great_grand_child_1: {},
                }
            }
        }

        Each key is a `DynamicGroup` instance.
        """
        tree = {}
        for f in self.children.all():
            tree[f] = f.descendants_tree()

        return tree

    # TODO: unused in core
    def flatten_descendants_tree(self, tree):
        """
        Recursively flatten a tree mapping of descendants to a list, adding a `depth` attribute to each
        instance in the list that can be used for visualizing tree depth.

        Args:
            tree (dict): Output from `descendants_tree()`
        """
        return self._flatten_tree(tree)

    def _flatten_tree(self, tree, nodes=None, depth=1):
        """
        Recursively flatten a tree mapping to a list, adding a `depth` attribute to each instance in
        the list that can be used for visualizing tree depth.

        Args:
            tree (dict): Output from `ancestors_tree()` or `descendants_tree()`
            nodes (list): Used in recursion, will contain the flattened nodes.
            depth (int): Used in recursion, the tree traversal depth.
        """

        if nodes is None:
            nodes = []

        for item in tree:
            item.depth = depth
            nodes.append(item)
            self._flatten_tree(tree[item], nodes=nodes, depth=depth + 1)

        return nodes

    def membership_tree(self, depth=1):
        """
        Recursively return a list of group memberships, adding a `depth` attribute to each instance
        in the list that can be used for visualizing tree depth.
        """

        tree = []
        memberships = DynamicGroupMembership.objects.filter(parent_group=self)
        for membership in memberships:
            membership.depth = depth
            tree.append(membership)
            tree.extend(membership.group.membership_tree(depth=depth + 1))

        return tree

    # TODO: unused in core
    def _ordered_filter(self, queryset, field_names, values):
        """
        Filters the provided `queryset` using `{field_name}__in` expressions for each field_name in the
        list of `field_names`. The query constructed by this method explicitly orders the results in
        the same order as the provided `values` using their list index. This is ideal for
        maintaining ordering of topologically sorted nodes.

        For example, the following would return an ordered queryset following the order in the list
        of "pk" values:

            self._ordered_filter(self.__class__.objects, ["pk"], pk_list)

        :param queryset:
            QuerySet object
        :param field_names:
            List of field names
        :param values:
            Ordered list of values corresponding values used to establish the queryset
        """
        if not isinstance(field_names, list):
            raise TypeError("Field names must be a list")

        case = []

        # This is queryset magic to build a query that explicitly orders the items in the list of
        # values based on their index value (idx). It's how we can get an explicitly ordered
        # queryset that can be used for topological sort, but also supports queryset filtering.
        for idx, value in enumerate(values):
            when_condition = {field_names[0]: value, "then": idx}
            case.append(models.When(**when_condition))

        order_by = models.Case(*case)
        filter_condition = {field_name + "__in": values for field_name in field_names}

        return queryset.filter(**filter_condition).order_by(order_by)

    # TODO: unused in core
    def ordered_queryset_from_pks(self, pk_list):
        """
        Generates a queryset ordered by the provided list of primary keys.

        :param pk_list:
            Ordered list of primary keys
        """
        return self._ordered_filter(self.__class__.objects, ["pk"], pk_list)


class DynamicGroupMembership(BaseModel):
    """Intermediate model for associating filters to groups."""

    group = models.ForeignKey("extras.DynamicGroup", on_delete=models.CASCADE, related_name="+")
    parent_group = models.ForeignKey(
        "extras.DynamicGroup", on_delete=models.CASCADE, related_name="dynamic_group_memberships"
    )
    operator = models.CharField(choices=DynamicGroupOperatorChoices.CHOICES, max_length=12)
    weight = models.PositiveSmallIntegerField()

    objects = BaseManager.from_queryset(DynamicGroupMembershipQuerySet)()

    documentation_static_path = "docs/user-guide/platform-functionality/dynamicgroup.html"
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["group", "parent_group", "operator", "weight"]
        ordering = ["parent_group", "weight", "group"]

    def __str__(self):
        return f"{self.parent_group} > {self.operator} ({self.weight}) > {self.group}"

    @property
    def name(self):
        """Return the group name."""
        return self.group.name

    @property
    def filter(self):
        """Return the group filter."""
        return self.group.filter

    # TODO: unused in core
    @property
    def members(self):
        """Return the group members."""
        return self.group.members

    # TODO: unused in core
    @property
    def count(self):
        """Return the group count."""
        return self.group.count

    def get_absolute_url(self, api=False):
        """Return the group's absolute URL."""
        # TODO: we should be able to have an absolute UI URL for this model in the new UI
        if not api:
            return self.group.get_absolute_url(api=api)
        return super().get_absolute_url(api=api)

    # TODO: unused in core
    def get_group_members_url(self):
        """Return the group members URL."""
        return self.group.get_group_members_url()

    # TODO: unused in core
    def get_siblings(self, include_self=False):
        """Return group memberships that share the same parent group."""
        siblings = DynamicGroupMembership.objects.filter(parent_group=self.parent_group)
        if include_self:
            return siblings

        return siblings.exclude(pk=self.pk)

    # TODO: unused in core
    def generate_query(self):
        return self.group.generate_query()

    def clean(self):
        super().clean()

        # Enforce group types
        if self.parent_group.group_type != DynamicGroupTypeChoices.TYPE_DYNAMIC_SET and self.parent_group.filter:
            raise ValidationError({"parent_group": 'A parent group must be of `group_type` `"dynamic-set"`.'})

        if self.group.group_type == DynamicGroupTypeChoices.TYPE_STATIC:
            raise ValidationError({"group": 'Groups of `group_type` `"static"` may not be child groups at this time.'})

        # Enforce matching content_type
        if self.parent_group.content_type != self.group.content_type:
            raise ValidationError({"group": "ContentType for group and parent_group must match"})

        # Assert that loops cannot be created (such as adding root parent as a nested child).
        if self.parent_group == self.group:
            raise ValidationError({"group": "Cannot add group as a child of itself"})

        if self.group in self.parent_group.get_ancestors():
            raise ValidationError({"group": "Cannot add ancestor as a child"})

    def save(self, *args, **kwargs):
        # For backwards compatibility
        if self.parent_group.group_type == DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER and not self.parent_group.filter:
            self.parent_group.group_type = DynamicGroupTypeChoices.TYPE_DYNAMIC_SET
            self.parent_group.save()
        return super().save(*args, **kwargs)


class StaticGroupAssociationManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True


class StaticGroupAssociationDefaultManager(StaticGroupAssociationManager):
    """Subclass of StaticGroupAssociationManager that automatically filters out cached/hidden associations."""

    def get_queryset(self):
        return super().get_queryset().filter(dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC)


@extras_features(
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class StaticGroupAssociation(OrganizationalModel):
    """Intermediary model for associating an object statically to a DynamicGroup of group_type `static`."""

    dynamic_group = models.ForeignKey(
        to=DynamicGroup, on_delete=models.CASCADE, related_name="static_group_associations"
    )
    associated_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="static_group_associations",
        limit_choices_to=FeatureQuery("dynamic_groups"),
    )
    associated_object_id = models.UUIDField(db_index=True)
    associated_object = GenericForeignKey(ct_field="associated_object_type", fk_field="associated_object_id")

    objects = StaticGroupAssociationDefaultManager()
    all_objects = StaticGroupAssociationManager()

    is_contact_associable_model = False
    is_dynamic_group_associable_model = False
    is_saved_view_model = False

    class Meta:
        unique_together = [["dynamic_group", "associated_object_type", "associated_object_id"]]
        ordering = ["dynamic_group", "associated_object_type", "associated_object_id"]
        indexes = [
            models.Index(
                name="extras_sga_double",
                fields=["dynamic_group", "associated_object_id"],
            ),
            models.Index(
                name="extras_sga_associated_object",
                fields=["associated_object_type_id", "associated_object_id"],
            ),
        ]

    def __str__(self):
        return f"{self.associated_object} as a member of {self.dynamic_group}"

    def clean(self):
        super().clean()

        if self.associated_object_type != self.dynamic_group.content_type:
            raise ValidationError({"associated_object_type": "Must match the dynamic_group.content_type"})

    def to_objectchange(self, *args, **kwargs):
        """Change log StaticGroupAssociations belonging to a "static" group; all others are an implementation detail."""
        if self.dynamic_group.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
            return None
        return super().to_objectchange(*args, **kwargs)
