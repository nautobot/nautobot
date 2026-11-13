from types import SimpleNamespace

from django.contrib.contenttypes.models import ContentType

from nautobot.cloud import models
from nautobot.dcim.models import Manufacturer
from nautobot.extras.models import Status


def create_cloud_fixtures(name_prefix):
    """Create a provider with resource types for every cloud model and accounts that all share that provider.

    Factory data spreads resource types and accounts across random providers, so tests that must satisfy the
    provider and account consistency rules create their own fixtures with this helper.
    """
    provider = Manufacturer.objects.create(name=f"{name_prefix} Cloud Provider")

    def resource_types(model, count=2):
        result = []
        for i in range(1, count + 1):
            resource_type = models.CloudResourceType.objects.create(
                name=f"{name_prefix} {model._meta.verbose_name} type {i}", provider=provider
            )
            resource_type.content_types.set([ContentType.objects.get_for_model(model)])
            result.append(resource_type)
        return result

    account_status = Status.objects.get_for_model(models.CloudAccount).first()
    accounts = [
        models.CloudAccount.objects.create(
            name=f"{name_prefix} Account {i}", account_number=str(i), provider=provider, status=account_status
        )
        for i in range(1, 4)
    ]
    return SimpleNamespace(
        provider=provider,
        accounts=accounts,
        account_group_types=resource_types(models.CloudAccountGroup),
        resource_group_types=resource_types(models.CloudResourceGroup),
        network_types=resource_types(models.CloudNetwork),
        service_types=resource_types(models.CloudService),
        account_statuses=list(Status.objects.get_for_model(models.CloudAccount)),
        network_statuses=list(Status.objects.get_for_model(models.CloudNetwork)),
        service_statuses=list(Status.objects.get_for_model(models.CloudService)),
    )
