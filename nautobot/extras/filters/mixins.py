from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import django_filters
from django_filters.utils import verbose_lookup_expr

from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    RelationshipSideChoices,
)
from nautobot.extras.filters.customfields import (
    CustomFieldBooleanFilter,
    CustomFieldCharFilter,
    CustomFieldDateFilter,
    CustomFieldJSONFilter,
    CustomFieldMultiSelectFilter,
    CustomFieldMultiValueCharFilter,
    CustomFieldMultiValueDateFilter,
    CustomFieldMultiValueNumberFilter,
    CustomFieldNumberFilter,
)
from nautobot.extras.models import (
    ConfigContextSchema,
    CustomField,
    Relationship,
    RelationshipAssociation,
    Status,
)
from nautobot.utilities.constants import (
    FILTER_CHAR_BASED_LOOKUP_MAP,
    FILTER_NUMERIC_BASED_LOOKUP_MAP,
)


class CustomFieldModelFilterSetMixin(django_filters.FilterSet):
    """
    Dynamically add a Filter for each CustomField applicable to the parent model. Add filters for
    extra lookup expressions on supported CustomField types.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        custom_field_filter_classes = {
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldDateFilter,
            CustomFieldTypeChoices.TYPE_BOOLEAN: CustomFieldBooleanFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldNumberFilter,
            CustomFieldTypeChoices.TYPE_JSON: CustomFieldJSONFilter,
            CustomFieldTypeChoices.TYPE_MULTISELECT: CustomFieldMultiSelectFilter,
        }

        custom_fields = CustomField.objects.filter(
            content_types=ContentType.objects.get_for_model(self._meta.model)
        ).exclude(filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED)
        for cf in custom_fields:
            # Determine filter class for this CustomField type, default to CustomFieldBaseFilter
            # 2.0 TODO: #824 use cf.slug instead
            new_filter_name = f"cf_{cf.name}"
            filter_class = custom_field_filter_classes.get(cf.type, CustomFieldCharFilter)
            new_filter_field = filter_class(field_name=cf.name, custom_field=cf)
            new_filter_field.label = f"{cf.label}"

            # Create base filter (cf_customfieldname)
            self.filters[new_filter_name] = new_filter_field

            # Create extra lookup expression filters (cf_customfieldname__lookup_expr)
            self.filters.update(
                self._generate_custom_field_lookup_expression_filters(filter_name=new_filter_name, custom_field=cf)
            )

    @staticmethod
    def _get_custom_field_filter_lookup_dict(filter_type):
        # Choose the lookup expression map based on the filter type
        if issubclass(filter_type, (CustomFieldMultiValueNumberFilter, CustomFieldMultiValueDateFilter)):
            lookup_map = FILTER_NUMERIC_BASED_LOOKUP_MAP
        else:
            lookup_map = FILTER_CHAR_BASED_LOOKUP_MAP

        return lookup_map

    # TODO 2.0: Transition CustomField filters to nautobot.utilities.filters.MultiValue* filters and
    # leverage BaseFilterSet to add dynamic lookup expression filters. Remove CustomField.filter_logic field
    @classmethod
    def _generate_custom_field_lookup_expression_filters(cls, filter_name, custom_field):
        """
        For specific filter types, new filters are created based on defined lookup expressions in
        the form `<field_name>__<lookup_expr>`. Copied from nautobot.utilities.filters.BaseFilterSet
        and updated to work with custom fields.
        """
        magic_filters = {}
        custom_field_type_to_filter_map = {
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldMultiValueDateFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldMultiValueNumberFilter,
            CustomFieldTypeChoices.TYPE_SELECT: CustomFieldMultiValueCharFilter,
            CustomFieldTypeChoices.TYPE_TEXT: CustomFieldMultiValueCharFilter,
            CustomFieldTypeChoices.TYPE_URL: CustomFieldMultiValueCharFilter,
        }

        if custom_field.type in custom_field_type_to_filter_map:
            filter_type = custom_field_type_to_filter_map[custom_field.type]
        else:
            return magic_filters

        # Choose the lookup expression map based on the filter type
        lookup_map = cls._get_custom_field_filter_lookup_dict(filter_type)

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = f"{filter_name}__{lookup_name}"
            new_filter = filter_type(
                field_name=custom_field.name,
                lookup_expr=lookup_expr,
                custom_field=custom_field,
                label=f"{custom_field.label} ({verbose_lookup_expr(lookup_expr)})",
                exclude=lookup_name.startswith("n"),
            )

            magic_filters[new_filter_name] = new_filter

        return magic_filters


class CreatedUpdatedModelFilterSetMixin(django_filters.FilterSet):
    created = django_filters.DateFilter()
    created__gte = django_filters.DateFilter(field_name="created", lookup_expr="gte")
    created__lte = django_filters.DateFilter(field_name="created", lookup_expr="lte")
    last_updated = django_filters.DateTimeFilter()
    last_updated__gte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="gte")
    last_updated__lte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="lte")


class LocalContextModelFilterSetMixin(django_filters.FilterSet):
    local_context_data = django_filters.BooleanFilter(
        method="_local_context_data",
        label="Has local config context data",
    )
    local_context_schema_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ConfigContextSchema.objects.all(),
        label="Schema (ID)",
    )
    local_context_schema = django_filters.ModelMultipleChoiceFilter(
        field_name="local_context_schema__slug",
        queryset=ConfigContextSchema.objects.all(),
        to_field_name="slug",
        label="Schema (slug)",
    )

    def _local_context_data(self, queryset, name, value):
        return queryset.exclude(local_context_data__isnull=value)


class RelationshipFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter objects by the presence of associations on a given Relationship.
    """

    def __init__(self, side, relationship=None, queryset=None, qs=None, *args, **kwargs):
        self.relationship = relationship
        self.qs = qs
        self.side = side
        super().__init__(queryset=queryset, *args, **kwargs)

    def filter(self, qs, value):
        value = [entry.id for entry in value]
        # Check if value is empty or a DynamicChoiceField that is empty.
        if not value or "" in value:
            # if value is empty we return the entire unmodified queryset
            return qs
        else:
            if self.side == "source":
                values = RelationshipAssociation.objects.filter(
                    destination_id__in=value,
                    source_type=self.relationship.source_type,
                    relationship=self.relationship,
                ).values_list("source_id", flat=True)
            elif self.side == "destination":
                values = RelationshipAssociation.objects.filter(
                    source_id__in=value,
                    destination_type=self.relationship.destination_type,
                    relationship=self.relationship,
                ).values_list("destination_id", flat=True)
            else:
                destinations = RelationshipAssociation.objects.filter(
                    source_id__in=value,
                    destination_type=self.relationship.destination_type,
                    relationship=self.relationship,
                ).values_list("destination_id", flat=True)

                sources = RelationshipAssociation.objects.filter(
                    destination_id__in=value,
                    source_type=self.relationship.source_type,
                    relationship=self.relationship,
                ).values_list("source_id", flat=True)

                values = list(destinations) + list(sources)
            qs &= self.get_method(self.qs)(Q(**{"id__in": values}))
            return qs


class RelationshipModelFilterSetMixin(django_filters.FilterSet):
    """
    Filterset for relationships applicable to the parent model.
    """

    def __init__(self, *args, **kwargs):
        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        super().__init__(*args, **kwargs)
        self.relationships = []
        self._append_relationships(model=self._meta.model)

    def _append_relationships(self, model):
        """
        Append form fields for all Relationships assigned to this model.
        """
        source_relationships = Relationship.objects.filter(source_type=self.obj_type, source_hidden=False)
        self._append_relationships_side(source_relationships, RelationshipSideChoices.SIDE_SOURCE, model)

        dest_relationships = Relationship.objects.filter(destination_type=self.obj_type, destination_hidden=False)
        self._append_relationships_side(dest_relationships, RelationshipSideChoices.SIDE_DESTINATION, model)

    def _append_relationships_side(self, relationships, initial_side, model):
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
            if peer_side == "source":
                choice_model = relationship.source_type.model_class()
            elif peer_side == "destination":
                choice_model = relationship.destination_type.model_class()
            else:
                choice_model = model
            # Check for invalid_relationship unit test
            if choice_model:
                self.filters[field_name] = RelationshipFilter(
                    relationship=relationship,
                    side=side,
                    field_name=field_name,
                    queryset=choice_model.objects.all(),
                    qs=model.objects.all(),
                )
            self.relationships.append(field_name)


class StatusFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter field used for filtering Status fields.

    Explicitly sets `to_field_name='value'` and dynamically sets queryset to
    retrieve choices for the corresponding model & field name bound to the
    filterset.
    """

    def __init__(self, *args, **kwargs):
        kwargs["to_field_name"] = "slug"
        super().__init__(*args, **kwargs)

    def get_queryset(self, request):
        self.queryset = Status.objects.all()
        return super().get_queryset(request)

    def get_filter_predicate(self, value):
        """Always use the field's name and the `to_field_name` attribute as predicate."""
        # e.g. `status__slug`
        to_field_name = self.field.to_field_name
        name = f"{self.field_name}__{to_field_name}"
        # Sometimes the incoming value is an instance. This block of logic comes from the base
        # `get_filter_predicate()` and was added here to support this.
        try:
            return {name: getattr(value, to_field_name)}
        except (AttributeError, TypeError):
            return {name: value}


class StatusModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `status` filter field to a FilterSet.
    """

    status = StatusFilter()
