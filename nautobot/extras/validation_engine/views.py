from nautobot.extras.validation_engine import models, serializers, tables, filters
from nautobot.apps.views import ObjectListViewMixin
from nautobot.core.views.generic import ObjectView
from django.contrib.contenttypes.models import ContentType
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from django_tables2 import RequestConfig

class AllValidationsListView(ObjectListViewMixin):
    lookup_field = "pk"
    queryset = models.ValidationResult.objects.all()
    table_class = tables.AllValidationsResultTable
    filterset_class = filters.ValidationResultFilterSet
    serializer_class = serializers.ValidationResultSerializer
    action_buttons = ()

class ObjectValidationView(ObjectView):
    template_name = "extras/validationresult.html"

    def get_extra_context(self, request, instance):
        validations = (
            models.ValidationResult.objects.filter(content_type=ContentType.objects.get_for_model(instance), object_id=instance.id)
        )
        validation_table = tables.ObjectValidationResultTable(validations)
        paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        RequestConfig(request, paginate).configure(validation_table)
        return {
            "active_tab": "validation_engine:1", 
            "table": validation_table
        }
