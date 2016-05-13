from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator

from dcim.models import Device
from utilities.views import BulkEditView, BulkDeleteView, ObjectListView, ObjectDeleteView

from .decorators import userkey_required
from .filters import SecretFilter
from .forms import SecretForm, SecretImportForm, SecretBulkEditForm, SecretBulkDeleteForm, SecretFilterForm
from .models import Secret, UserKey
from .tables import SecretTable


#
# Secrets
#

@method_decorator(login_required, name='dispatch')
class SecretListView(ObjectListView):
    queryset = Secret.objects.select_related('role').prefetch_related('device')
    filter = SecretFilter
    filter_form = SecretFilterForm
    table = SecretTable
    edit_permissions = ['secrets.change_secret', 'secrets.delete_secret']
    template_name = 'secrets/secret_list.html'


@login_required
def secret(request, pk):

    secret = get_object_or_404(Secret, pk=pk)

    return render(request, 'secrets/secret.html', {
        'secret': secret,
    })


@permission_required('secrets.add_secret')
@userkey_required()
def secret_add(request, pk):

    # Retrieve device
    device = get_object_or_404(Device, pk=pk)

    secret = Secret(device=device)
    uk = UserKey.objects.get(user=request.user)

    if request.method == 'POST':
        form = SecretForm(request.POST, instance=secret)
        if form.is_valid():

            # Retrieve the master key from the current user's UserKey
            master_key = uk.get_master_key(form.cleaned_data['private_key'])
            if master_key is None:
                form.add_error(None, "Invalid private key! Unable to encrypt secret data.")

            # Create and encrypt the new Secret
            else:
                secret = form.save(commit=False)
                secret.plaintext = str(form.cleaned_data['plaintext'])
                secret.encrypt(master_key)
                secret.save()

                messages.success(request, "Added new secret: {0}".format(secret))
                if '_addanother' in request.POST:
                    return redirect('secrets:secret_add')
                else:
                    return redirect('secrets:secret', pk=secret.pk)

    else:
        form = SecretForm(instance=secret)

    return render(request, 'secrets/secret_edit.html', {
        'secret': secret,
        'form': form,
        'cancel_url': device.get_absolute_url(),
    })


@permission_required('secrets.change_secret')
@userkey_required()
def secret_edit(request, pk):

    secret = get_object_or_404(Secret, pk=pk)
    uk = UserKey.objects.get(user=request.user)

    if request.method == 'POST':
        form = SecretForm(request.POST, instance=secret)
        if form.is_valid():

            # Re-encrypt the Secret if a plaintext has been specified.
            if form.cleaned_data['plaintext']:

                # Retrieve the master key from the current user's UserKey
                master_key = uk.get_master_key(form.cleaned_data['private_key'])
                if master_key is None:
                    form.add_error(None, "Invalid private key! Unable to encrypt secret data.")

                # Create and encrypt the new Secret
                else:
                    secret = form.save(commit=False)
                    secret.plaintext = str(form.cleaned_data['plaintext'])
                    secret.encrypt(master_key)
                    secret.save()

            else:
                secret = form.save()

            messages.success(request, "Modified secret {0}".format(secret))
            return redirect('secrets:secret', pk=secret.pk)

    else:
        form = SecretForm(instance=secret)

    return render(request, 'secrets/secret_edit.html', {
        'secret': secret,
        'form': form,
        'cancel_url': reverse('secrets:secret', kwargs={'pk': secret.pk}),
    })


class SecretDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'secrets.delete_secret'
    model = Secret
    redirect_url = 'secrets:secret_list'


@permission_required('secrets.add_secret')
@userkey_required()
def secret_import(request):

    uk = UserKey.objects.get(user=request.user)

    if request.method == 'POST':
        form = SecretImportForm(request.POST)
        if form.is_valid():

            new_secrets = []

            # Retrieve the master key from the current user's UserKey
            master_key = uk.get_master_key(form.cleaned_data['private_key'])
            if master_key is None:
                form.add_error(None, "Invalid private key! Unable to encrypt secret data.")

            else:
                try:
                    with transaction.atomic():
                        for secret in form.cleaned_data['csv']:
                            secret.encrypt(master_key)
                            secret.save()
                            new_secrets.append(secret)

                    table = SecretTable(new_secrets)
                    messages.success(request, "Imported {} new secrets".format(len(new_secrets)))

                    return render(request, 'import_success.html', {
                        'table': table,
                    })

                except IntegrityError as e:
                    form.add_error('csv', "Record {}: {}".format(len(new_secrets) + 1, e.__cause__))

    else:
        form = SecretImportForm()

    return render(request, 'secrets/secret_import.html', {
        'form': form,
        'cancel_url': reverse('secrets:secret_list'),
    })


class SecretBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'secrets.change_secret'
    cls = Secret
    form = SecretBulkEditForm
    template_name = 'secrets/secret_bulk_edit.html'
    default_redirect_url = 'secrets:secret_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['role', 'name']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} secrets".format(updated_count))


class SecretBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'secrets.delete_secret'
    cls = Secret
    form = SecretBulkDeleteForm
    default_redirect_url = 'secrets:secret_list'
