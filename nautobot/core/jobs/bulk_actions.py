from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    FieldDoesNotExist,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.db.models import ManyToManyField, ProtectedError

from nautobot.core.forms.utils import restrict_form_fields
from nautobot.core.utils.lookup import get_form_for_model
from nautobot.core.views.utils import get_bulk_queryset_from_view
from nautobot.extras.context_managers import deferred_change_logging_for_bulk_operation
from nautobot.extras.jobs import (
    BooleanVar,
    Job,
    JSONVar,
    ObjectVar,
    RunJobTaskFailed,
)
from nautobot.extras.models import SavedView
from nautobot.extras.utils import bulk_delete_with_bulk_change_logging, remove_prefix_from_cf_key

name = "System Jobs"


class BulkEditObjects(Job):
    """System Job to bulk Edit objects."""

    content_type = ObjectVar(
        model=ContentType,
        description="Type of objects to update",
    )
    # The names of the job inputs must match the parameters of `key_params` and get_bulk_queryset_from_view
    # This may be confusing for the saved_view_id since the job input is an ObjectVar but the key_param is a PK
    # But it is the lesser of two evils.
    form_data = JSONVar(description="BulkEditForm data")
    pk_list = JSONVar(description="List of objects pks to edit", required=False)
    edit_all = BooleanVar(description="Bulk Edit all object / all filtered objects", required=False)
    filter_query_params = JSONVar(label="Filter Query Params", required=False)
    saved_view_id = ObjectVar(model=SavedView, required=False)

    class Meta:
        name = "Bulk Edit Objects"
        description = "Bulk edit objects."
        has_sensitive_variables = False
        soft_time_limit = 1800
        time_limit = 2000
        hidden = True

    def _update_objects(self, model, form, filter_query_params, pk_list, edit_all, nullified_fields, saved_view_id):
        base_queryset = model.objects.restrict(self.user, "change")
        queryset = get_bulk_queryset_from_view(user=self.user, action="change", log=self.logger, **self.key_params)

        with deferred_change_logging_for_bulk_operation():
            updated_objects_pk = []
            form_custom_fields = getattr(form, "custom_fields", [])
            form_relationships = getattr(form, "relationships", [])
            standard_fields = [
                field
                for field in form.fields
                if field not in form_custom_fields + form_relationships + ["pk"] + ["object_note"]
            ]

            self.logger.debug(f"Performing update on {queryset.count()} {model._meta.verbose_name_plural}")
            for obj in queryset.iterator():
                # Update standard fields. If a field is listed in _nullify, delete its value.
                for field_name in standard_fields:
                    try:
                        model_field = model._meta.get_field(field_name)
                    except FieldDoesNotExist:
                        # This form field is used to modify a field rather than set its value directly
                        model_field = None

                    # Handle nullification
                    if nullified_fields and field_name in nullified_fields and field_name in form.nullable_fields:
                        if isinstance(model_field, ManyToManyField):
                            getattr(obj, field_name).set([])
                        else:
                            setattr(obj, field_name, None if model_field is not None and model_field.null else "")

                    # ManyToManyFields
                    elif isinstance(model_field, ManyToManyField):
                        if form.cleaned_data[field_name]:
                            getattr(obj, field_name).set(form.cleaned_data[field_name])
                    # Normal fields
                    elif form.cleaned_data[field_name] not in (None, "", []):
                        if hasattr(obj, field_name):
                            setattr(obj, field_name, form.cleaned_data[field_name])

                # Update custom fields
                for field_name in form_custom_fields:
                    if field_name in form.nullable_fields and nullified_fields and field_name in nullified_fields:
                        obj.cf[remove_prefix_from_cf_key(field_name)] = None
                    elif form.cleaned_data.get(field_name) not in (None, "", []):
                        obj.cf[remove_prefix_from_cf_key(field_name)] = form.cleaned_data[field_name]

                obj.full_clean()
                obj.save()
                updated_objects_pk.append(obj.pk)
                form.post_save(obj)  # handles M2M add_* and remove_* form fields

                if hasattr(form, "save_relationships") and callable(form.save_relationships):
                    # Add/remove relationship associations
                    form.save_relationships(instance=obj, nullified_fields=nullified_fields)

                if hasattr(form, "save_note") and callable(form.save_note):
                    form.save_note(instance=obj, user=self.user)
            total_updated_objs = len(updated_objects_pk)
            # Enforce object-level permissions. This works because we used .restrict() above and if the user
            # doesn't have permission to change one of the objects after the change, it won't be in base_queryset
            # filtered to the pks of the objects we just changed.
            if base_queryset.filter(pk__in=updated_objects_pk).count() != total_updated_objs:
                raise ObjectDoesNotExist
            return total_updated_objs

    def _process_valid_form(self, model, form, filter_query_params, pk_list, edit_all, nullified_fields, saved_view_id):
        try:
            total_updated_objs = self._update_objects(
                model, form, filter_query_params, pk_list, edit_all, nullified_fields, saved_view_id
            )
            msg = f"Updated {total_updated_objs} {model._meta.verbose_name_plural}"
            self.logger.info(msg)
            return msg
        except ValidationError as e:
            self.logger.error(str(e))
        except ObjectDoesNotExist:
            msg = "Object update failed due to object-level permissions violation"
            self.logger.error(msg)
        raise RunJobTaskFailed("Bulk Edit not fully successful, see logs")

    def run(  # pylint: disable=arguments-differ
        self, *, content_type, form_data, pk_list=None, edit_all=False, filter_query_params=None, saved_view_id=None
    ):
        saved_view_id = saved_view_id.pk if saved_view_id is not None else None
        if not filter_query_params:
            filter_query_params = {}

        if not self.user.has_perm(f"{content_type.app_label}.change_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to update %s objects', self.user, content_type.model)
            raise PermissionDenied("User does not have change permissions on the requested content-type")

        self.key_params = {
            "content_type": content_type,
            "edit_all": edit_all,
            "filter_query_params": filter_query_params,
            "pk_list": pk_list,
            "saved_view_id": saved_view_id,
        }

        model = content_type.model_class()
        if model is None:
            self.logger.error(
                'Could not find the "%s.%s" data model. Perhaps an app is uninstalled?',
                content_type.app_label,
                content_type.model,
            )
            raise RunJobTaskFailed("Model not found")
        try:
            form_cls = get_form_for_model(model, form_prefix="BulkEdit")
        except Exception:
            self.logger.debug(
                'Could not find the "%s.%s" data bulk edit form. Unable to process Bulk Edit for this model.',
                content_type.app_label,
                content_type.model,
            )
            raise
        form = form_cls(model, form_data, edit_all=edit_all)
        restrict_form_fields(form, self.user)

        if form.is_valid():
            self.logger.debug("Form validation was successful")
            nullified_fields = form_data.get("_nullify")
            return self._process_valid_form(
                model, form, filter_query_params, pk_list, edit_all, nullified_fields, saved_view_id
            )
        else:
            self.logger.error(f"Form validation unsuccessful: {form.errors.as_json()}")

        raise RunJobTaskFailed("Updating Jobs Failed")


class BulkDeleteObjects(Job):
    """
    System job to bulk delete objects.
    """

    content_type = ObjectVar(
        model=ContentType,
        description="Type of objects to delete",
    )
    # The names of the job inputs must match the parameters of `key_params` and get_bulk_queryset_from_view
    # This may be confusing for the saved_view_id since the job input is an ObjectVar but the key_param is a PK
    # But it is the lesser of two evils.
    pk_list = JSONVar(description="List of objects pks to delete", required=False)
    delete_all = BooleanVar(description="Delete all (filtered) objects instead of a list of PKs", required=False)
    filter_query_params = JSONVar(label="Filter Query Params", required=False)
    saved_view_id = ObjectVar(model=SavedView, required=False)

    class Meta:
        name = "Bulk Delete Objects"
        description = "Bulk delete objects."
        has_sensitive_variables = False
        soft_time_limit = 1800
        time_limit = 2000
        hidden = True

    def run(  # pylint: disable=arguments-differ
        self, *, content_type, pk_list=None, delete_all=False, filter_query_params=None, saved_view_id=None
    ):
        saved_view_id = saved_view_id.pk if saved_view_id is not None else None
        if not filter_query_params:
            filter_query_params = {}
        if not self.user.has_perm(f"{content_type.app_label}.delete_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to delete %s objects', self.user, content_type.model)
            raise PermissionDenied("User does not have delete permissions on the requested content-type")

        key_params = {
            "content_type": content_type,
            "delete_all": delete_all,
            "filter_query_params": filter_query_params,
            "pk_list": pk_list,
            "saved_view_id": saved_view_id,
        }

        model = content_type.model_class()
        if model is None:
            self.logger.error(
                'Could not find the "%s.%s" data model. Perhaps an app is uninstalled?',
                content_type.app_label,
                content_type.model,
            )
            raise RunJobTaskFailed("Model not found")

        queryset = get_bulk_queryset_from_view(user=self.user, action="delete", log=self.logger, **key_params)

        verbose_name_plural = model._meta.verbose_name_plural

        # Currently the only purpose of a bulk delete form is to perform a `pre_delete` operation
        if form_cls := get_form_for_model(model, form_prefix="BulkDelete"):
            form = form_cls(model, {"pk": pk_list}, delete_all=delete_all)
            if hasattr(form, "perform_pre_delete"):
                form.perform_pre_delete(queryset)

        try:
            self.logger.info(f"Deleting {queryset.count()} {verbose_name_plural}...")
            _, deleted_info = bulk_delete_with_bulk_change_logging(queryset)
            deleted_count = deleted_info.get(model._meta.label, 0)
        except ProtectedError as err:
            # TODO this error message needs to be cleaner, ideally using a variant of handle_protectederror
            self.logger.error(f"Caught ProtectedError while attempting to delete objects: `{err}`")
            raise RunJobTaskFailed("Caught ProtectedError while attempting to delete objects")
        msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
        self.logger.info(msg)
