from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q
from django.utils.encoding import force_str
from django.utils.text import capfirst
import django_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.utils import verbose_lookup_expr

from nautobot.core.constants import (
    FILTER_CHAR_BASED_LOOKUP_MAP,
    FILTER_NEGATION_LOOKUP_MAP,
    FILTER_NUMERIC_BASED_LOOKUP_MAP,
)
from nautobot.core.filters import (
    MultiValueDateTimeFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
)
from nautobot.dcim.models import Device
from nautobot.extras.choices import (
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
    CustomFieldSelectFilter,
)
from nautobot.extras.models import (
    ConfigContextSchema,
    CustomField,
    Relationship,
    Role,
    Status,
)
from nautobot.virtualization.models import VirtualMachine


class ConfigContextRoleFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """Limit role choices to the available role choices for Device and VM"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("field_name", "roles")
        kwargs.setdefault("queryset", Role.objects.get_for_models([Device, VirtualMachine]))
        kwargs.setdefault("label", "Role (name or ID)")
        kwargs.setdefault("to_field_name", "name")

        super().__init__(*args, **kwargs)


class CustomFieldModelFilterSetMixin(django_filters.FilterSet):
    """
    Dynamically add a Filter for each CustomField applicable to the parent model. Add filters for
    extra lookup expressions on supported CustomField types.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        custom_field_filter_classes = {
            # Here, for the "base" filters for each custom field, for backwards compatibility, use single-value filters.
            # For the "extended" filters, see below, we use multi-value filters.
            # 3.0 TODO: switch the "base" filters to multi-value filters as well.
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldDateFilter,
            CustomFieldTypeChoices.TYPE_BOOLEAN: CustomFieldBooleanFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldNumberFilter,
            CustomFieldTypeChoices.TYPE_JSON: CustomFieldJSONFilter,
            # The below are multi-value filters already:
            CustomFieldTypeChoices.TYPE_MULTISELECT: CustomFieldMultiSelectFilter,
            CustomFieldTypeChoices.TYPE_SELECT: CustomFieldSelectFilter,
        }

        custom_fields = CustomField.objects.get_for_model(
            self._meta.model, exclude_filter_disabled=True, get_queryset=False
        )
        for cf in custom_fields:
            # Determine filter class for this CustomField type, default to CustomFieldCharFilter
            new_filter_name = cf.add_prefix_to_cf_key()
            filter_class = custom_field_filter_classes.get(cf.type, CustomFieldCharFilter)
            new_filter = filter_class(field_name=cf.key, custom_field=cf)
            new_filter.label = f"{cf.label}"
            # Create base filter (cf_customfieldname)
            self.filters[new_filter_name] = new_filter

            # Create extra lookup expression filters (cf_customfieldname__lookup_expr)
            self.filters.update(
                self._generate_custom_field_lookup_expression_filters(filter_name=new_filter_name, custom_field=cf)
            )

    @staticmethod
    def _get_custom_field_filter_lookup_dict(filter_type):
        # Choose the lookup expression map based on the filter type
        if issubclass(filter_type, (CustomFieldMultiValueNumberFilter, CustomFieldMultiValueDateFilter)):
            return FILTER_NUMERIC_BASED_LOOKUP_MAP
        elif issubclass(filter_type, CustomFieldMultiSelectFilter):
            return FILTER_NEGATION_LOOKUP_MAP
        else:
            return FILTER_CHAR_BASED_LOOKUP_MAP

    # TODO 2.0: Transition CustomField filters to nautobot.core.filters.MultiValue* filters and
    # leverage BaseFilterSet to add dynamic lookup expression filters. Remove CustomField.filter_logic field
    @classmethod
    def _generate_custom_field_lookup_expression_filters(cls, filter_name, custom_field):
        """
        For specific filter types, new filters are created based on defined lookup expressions in
        the form `<field_name>__<lookup_expr>`. Copied from nautobot.core.filters.BaseFilterSet
        and updated to work with custom fields.
        """
        magic_filters = {}
        custom_field_type_to_filter_map = {
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldMultiValueDateFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldMultiValueNumberFilter,
            CustomFieldTypeChoices.TYPE_SELECT: CustomFieldMultiValueCharFilter,
            CustomFieldTypeChoices.TYPE_MULTISELECT: CustomFieldMultiSelectFilter,
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

            # Based on logic in BaseFilterSet._generate_lookup_expression_filters
            verbose_expression = (
                ["exclude", custom_field.label] if lookup_name.startswith("n") else [custom_field.label]
            )
            if isinstance(lookup_expr, str):
                verbose_expression.append(verbose_lookup_expr(lookup_expr))
            verbose_expression = [force_str(part) for part in verbose_expression if part]
            label = capfirst(" ".join(verbose_expression))

            new_filter = filter_type(
                field_name=custom_field.key,
                lookup_expr=lookup_expr,
                custom_field=custom_field,
                label=label,
                exclude=lookup_name.startswith("n"),
            )

            magic_filters[new_filter_name] = new_filter

        return magic_filters


class CreatedUpdatedModelFilterSetMixin(django_filters.FilterSet):
    created = MultiValueDateTimeFilter()
    last_updated = MultiValueDateTimeFilter()


class LocalContextModelFilterSetMixin(django_filters.FilterSet):
    local_config_context_data = django_filters.BooleanFilter(
        method="_local_config_context_data",
        label="Has local config context data",
    )
    local_config_context_schema_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ConfigContextSchema.objects.all(),
        label="Schema (ID) - Deprecated (use local_context_schema filter)",
    )
    local_config_context_schema = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ConfigContextSchema.objects.all(),
        to_field_name="name",
        label="Schema (ID or name)",
    )

    def _local_config_context_data(self, queryset, name, value):
        return queryset.exclude(local_config_context_data__isnull=value)


class RelationshipFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter objects by the presence of associations on a given Relationship.
    """

    def __init__(self, side, relationship=None, queryset=None, qs=None, *args, **kwargs):
        self.relationship = relationship
        self.qs = qs
        self.side = side
        super().__init__(queryset=queryset, *args, **kwargs)

    def generate_query(self, value, **kwargs):
        query = Q()

        value = [v.pk if isinstance(v, Model) else v for v in value]

        if self.side in (RelationshipSideChoices.SIDE_SOURCE, RelationshipSideChoices.SIDE_PEER):
            query |= Q(
                source_for_associations__relationship=self.relationship.id,
                source_for_associations__destination_id__in=value,
            )
        if self.side in (RelationshipSideChoices.SIDE_DESTINATION, RelationshipSideChoices.SIDE_PEER):
            query |= Q(
                destination_for_associations__relationship=self.relationship.id,
                destination_for_associations__source_id__in=value,
            )
        return query

    def filter(self, qs, value):
        if not value or any(v in EMPTY_VALUES for v in value):
            return qs

        query = self.generate_query(value)
        result = self.get_method(qs)(query)
        if self.distinct:
            result = result.distinct()
        return result


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
        src_relationships, dst_relationships = Relationship.objects.get_for_model(
            model=model, hidden=False, get_queryset=False
        )

        self._append_relationships_side(src_relationships, RelationshipSideChoices.SIDE_SOURCE, model)

        self._append_relationships_side(dst_relationships, RelationshipSideChoices.SIDE_DESTINATION, model)

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
            # "cr_<relationship_key>__destination" since it's used to pick the destination object(s).
            # If we're on the "destination" side, the field will be "cr_<relationship_key>__source".
            # For a symmetric relationship, both sides are "peer", so the field will be "cr_<relationship_key>__peer"
            field_name = f"cr_{relationship.key}__{peer_side}"

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


#
# Role
#


class RoleFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """Filter field used for filtering Role fields."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("queryset", Role.objects.all())
        kwargs.setdefault("label", "Role (name or ID)")
        super().__init__(*args, **kwargs)


class RoleModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `role` filter field to a FilterSet.
    """

    @classmethod
    def get_filters(cls):
        filters = super().get_filters()

        if cls._meta.model is not None:
            filters["role"] = RoleFilter(
                field_name="role",
                query_params={"content_types": [cls._meta.model._meta.label_lower]},
            )
            cls.declared_filters["role"] = filters["role"]  # pylint: disable=no-member

        return filters


class StatusFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """
    Filter field used for filtering Status fields.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("queryset", Status.objects.all())
        kwargs.setdefault("label", "Status (name or ID)")
        super().__init__(*args, **kwargs)


class StatusModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `status` filter field to a FilterSet.
    """

    @classmethod
    def get_filters(cls):
        filters = super().get_filters()

        if cls._meta.model is not None:
            filters["status"] = StatusFilter(
                field_name="status",
                query_params={"content_types": [cls._meta.model._meta.label_lower]},
            )
            cls.declared_filters["status"] = filters["status"]  # pylint: disable=no-member

        return filters
