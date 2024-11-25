from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    PermissionDenied,
)
from django.db.models import ProtectedError

from nautobot.core.utils.lookup import get_filterset_for_model, get_form_for_model
from nautobot.extras.jobs import (
    BooleanVar,
    Job,
    JSONVar,
    ObjectVar,
    RunJobTaskFailed,
)
from nautobot.extras.utils import bulk_delete_with_bulk_change_logging


class BulkDeleteObjects(Job):
    """
    System job to bulk delete objs`.
    """

    content_type = ObjectVar(
        model=ContentType,
        description="Type of objects to import",
    )
    pk_list = JSONVar(description="PK List of objects to delete", required=False)
    delete_all = BooleanVar(description="Bulk Delete all object / all filtered objects", required=False)
    filter_query_params = JSONVar(label="Filter Query Params", required=False)

    class Meta:
        name = "Bulk Delete Objects"
        description = "Bulk delete objects."
        has_sensitive_variables = False
        soft_time_limit = 1800
        time_limit = 2000

    def run(self, *, content_type, pk_list=None, delete_all=False, filter_query_params=None):
        if not self.user.has_perm(f"{content_type.app_label}.delete_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to delete %s objects', self.user, content_type.model)
            raise PermissionDenied("User does not have delete permissions on the requested content-type")

        model = content_type.model_class()
        if model is None:
            self.logger.error(
                'Could not find the "%s.%s" data model. Perhaps an app is uninstalled?',
                content_type.app_label,
                content_type.model,
            )
            raise RunJobTaskFailed("Model not found")

        filterset_cls = get_filterset_for_model(model)
        if delete_all:
            if filterset_cls:
                queryset = filterset_cls(filter_query_params).qs.restrict(self.user, "delete")
                # We take this approach because filterset.qs has already applied .distinct(),
                # and performing a .delete directly on a queryset with .distinct applied is not allowed.
                queryset = model.objects.filter(pk__in=queryset)
            else:
                queryset = model.objects.restrict(self.user, "delete")
        else:
            queryset = model.objects.restrict(self.user, "delete").filter(pk__in=pk_list)

        verbose_name_plural = model._meta.verbose_name_plural

        # Currently the only purpose of a bulk delete form is to perform a `pre_delete` operation
        if form_cls := get_form_for_model(model, form_prefix="BulkDelete"):
            form = form_cls(model, {"pk": pk_list}, delete_all=delete_all)
            if hasattr(form, "perform_pre_delete"):
                form.perform_pre_delete(queryset)

        try:
            self.logger.info(f"Deleting {queryset.count()} {verbose_name_plural}...")
            _, deleted_info = bulk_delete_with_bulk_change_logging(queryset)
            deleted_count = deleted_info[model._meta.label]
        except ProtectedError:
            self.logger.info("Caught ProtectedError while attempting to delete objects")
            raise RunJobTaskFailed("Caught ProtectedError while attempting to delete objects")
        msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
        self.logger.info(msg)
