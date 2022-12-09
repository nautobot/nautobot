import logging

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django_tables2 import RequestConfig

from nautobot.core import filters, forms, models, tables
from nautobot.core.models.dynamic_groups import DynamicGroup
from nautobot.core.views import generic
from nautobot.utilities.forms import restrict_form_fields
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import get_table_for_model, pretty_print_query


logger = logging.getLogger(__name__)


#
# Dynamic Groups
#


class DynamicGroupListView(generic.ObjectListView):
    queryset = DynamicGroup.objects.all()
    table = tables.DynamicGroupTable
    filterset = filters.DynamicGroupFilterSet
    filterset_form = forms.DynamicGroupFilterForm
    action_buttons = ("add",)


class DynamicGroupView(generic.ObjectView):
    queryset = DynamicGroup.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        model = instance.content_type.model_class()
        table_class = get_table_for_model(model)

        if table_class is not None:
            # Members table (for display on Members nav tab)
            members_table = table_class(instance.members, orderable=False)
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(members_table)

            # Descendants table
            descendants_memberships = instance.membership_tree()
            descendants_table = tables.NestedDynamicGroupDescendantsTable(
                descendants_memberships,
                orderable=False,
            )
            descendants_tree = {m.pk: m.depth for m in descendants_memberships}

            # Ancestors table
            ancestors = instance.get_ancestors()
            ancestors_table = tables.NestedDynamicGroupAncestorsTable(ancestors, orderable=False)
            ancestors_tree = instance.flatten_ancestors_tree(instance.ancestors_tree())

            context["raw_query"] = pretty_print_query(instance.generate_query())
            context["members_table"] = members_table
            context["ancestors_table"] = ancestors_table
            context["ancestors_tree"] = ancestors_tree
            context["descendants_table"] = descendants_table
            context["descendants_tree"] = descendants_tree

        return context


class DynamicGroupEditView(generic.ObjectEditView):
    queryset = DynamicGroup.objects.all()
    model_form = forms.DynamicGroupForm
    template_name = "core/dynamicgroup_edit.html"

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)

        filterform_class = instance.generate_filter_form()

        if filterform_class is None:
            filter_form = None
        elif request.POST:
            filter_form = filterform_class(data=request.POST)
        else:
            initial = instance.get_initial()
            filter_form = filterform_class(initial=initial)

        ctx["filter_form"] = filter_form

        formset_kwargs = {"instance": instance}
        if request.POST:
            formset_kwargs["data"] = request.POST

        ctx["children"] = forms.DynamicGroupMembershipFormSet(**formset_kwargs)

        return ctx

    def post(self, request, *args, **kwargs):
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)
        form = self.model_form(data=request.POST, files=request.FILES, instance=obj)
        restrict_form_fields(form, request.user)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic():
                    object_created = not form.instance.present_in_database
                    # Obtain the instance, but do not yet `save()` it to the database.
                    obj = form.save(commit=False)

                    # Process the filter form and save the query filters to `obj.filter`.
                    ctx = self.get_extra_context(request, obj)
                    filter_form = ctx["filter_form"]
                    if filter_form.is_valid():
                        obj.set_filter(filter_form.cleaned_data)
                    else:
                        raise RuntimeError(filter_form.errors)

                    # After filters have been set, now we save the object to the database.
                    obj.save()
                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)

                    # Process the formsets for children
                    children = ctx["children"]
                    if children.is_valid():
                        children.save()
                    else:
                        raise RuntimeError(children.errors)
                verb = "Created" if object_created else "Modified"
                msg = f"{verb} {self.queryset.model._meta.verbose_name}"
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                if hasattr(obj, "get_absolute_url"):
                    msg = f'{msg} <a href="{obj.get_absolute_url()}">{escape(obj)}</a>'
                else:
                    msg = f"{msg} {escape(obj)}"
                messages.success(request, mark_safe(msg))

                if "_addanother" in request.POST:

                    # If the object has clone_fields, pre-populate a new instance of the form
                    if hasattr(obj, "clone_fields"):
                        url = f"{request.path}?{prepare_cloned_fields(obj)}"
                        return redirect(url)

                    return redirect(request.get_full_path())

                return_url = form.cleaned_data.get("return_url")
                if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                    return redirect(return_url)
                else:
                    return redirect(self.get_return_url(request, obj))

            except ObjectDoesNotExist:
                msg = "Object save failed due to object-level permissions violation."
                logger.debug(msg)
                form.add_error(None, msg)
            except RuntimeError:
                msg = "Errors encountered when saving Dynamic Group associations. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a something that is in use.
                err_msg = err.args[0]
                protected_obj = err.protected_objects[0]
                msg = f"{protected_obj.value}: {err_msg} Please cancel this edit and start again."
                logger.debug(msg)
                form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "editing": obj.present_in_database,
                **self.get_extra_context(request, obj),
            },
        )


class DynamicGroupDeleteView(generic.ObjectDeleteView):
    queryset = DynamicGroup.objects.all()


class DynamicGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = DynamicGroup.objects.all()
    table = tables.DynamicGroupTable
