# The Nautobot Python Shell

Nautobot includes a Python management shell within which objects can be directly queried, created, modified, and deleted. To enter the shell, run the following command:

```no-highlight
nautobot-server nbshell
```

This will launch a lightly customized version of [the built-in Django shell](https://docs.djangoproject.com/en/stable/ref/django-admin/#shell) with all relevant Nautobot models pre-loaded. (If desired, the stock Django shell is also available by executing `nautobot-server shell`.)

```no-highlight
nautobot-server nbshell
```

Example output:

```no-highlight
### Nautobot interactive shell (localhost)
### Python 3.6.9 | Django 3.1 | Nautobot 1.0.0
### lsmodels() will show available models. Use help(<model>) for more info.
```

The function `lsmodels()` will print a list of all available Nautobot models:

```python
>>> lsmodels()
DCIM:
  ConsolePort
  ConsolePortTemplate
  ConsoleServerPort
  ConsoleServerPortTemplate
  Device
  ...
```

!!! warning
    The Nautobot shell affords direct access to Nautobot data and function with very little validation in place. As such, it is crucial to ensure that only authorized, knowledgeable users are ever granted access to it. Never perform any action in the management shell without having a full backup in place.

## Querying Objects

Objects are retrieved from the database using a [Django queryset](https://docs.djangoproject.com/en/stable/topics/db/queries/#retrieving-objects). The base queryset for an object takes the form `<model>.objects.all()`, which will return a (truncated) list of all objects of that type.

```python
>>> Device.objects.all()
<QuerySet [<Device: TestDevice1>, <Device: TestDevice2>, <Device: TestDevice3>,
<Device: TestDevice4>, <Device: TestDevice5>, '...(remaining elements truncated)...']>
```

Use a `for` loop to cycle through all objects in the list:

```python
>>> for device in Device.objects.all():
...   print(device.name, device.device_type)
...
('TestDevice1', <DeviceType: PacketThingy 9000>)
('TestDevice2', <DeviceType: PacketThingy 9000>)
('TestDevice3', <DeviceType: PacketThingy 9000>)
('TestDevice4', <DeviceType: PacketThingy 9000>)
('TestDevice5', <DeviceType: PacketThingy 9000>)
...
```

To count all objects matching the query, replace `all()` with `count()`:

```python
>>> Device.objects.count()
1274
```

To retrieve a particular object (typically by its primary key or other unique field), use `get()`:

```python
>>> Site.objects.get(pk="8a2c9c3b-076e-4688-8a0b-89362f343a26")
<Site: Test Lab>
```

### Filtering Querysets

In most cases, you will want to retrieve only a specific subset of objects. To filter a queryset, replace `all()` with `filter()` and pass one or more keyword arguments. For example:

```python
>>> Device.objects.filter(status__slug="active")
<QuerySet [<Device: TestDevice1>, <Device: TestDevice2>, <Device: TestDevice3>,
<Device: TestDevice8>, <Device: TestDevice9>, '...(remaining elements truncated)...']>
```

Querysets support slicing to return a specific range of objects.

```python
>>> Device.objects.filter(status__slug="active")[:3]
<QuerySet [<Device: TestDevice1>, <Device: TestDevice2>, <Device: TestDevice3>]>
```

The `count()` method can be appended to the queryset to return a count of objects rather than the full list.

```python
>>> Device.objects.filter(status__slug="active").count()
982
```

Relationships with other models can be traversed by concatenating attribute names with a double-underscore. For example, the following will return all devices assigned to the tenant named "Pied Piper."

```python
>>> Device.objects.filter(tenant__name="Pied Piper")
```

This approach can span multiple levels of relations. For example, the following will return all IP addresses assigned to a device in North America:

```python
>>> IPAddress.objects.filter(interface__device__site__region__slug="north-america")
```

!!! note
    While the above query is functional, it's not very efficient. There are ways to optimize such requests, however they are out of scope for this document. For more information, see the [Django queryset method reference](https://docs.djangoproject.com/en/stable/ref/models/querysets/) documentation.

Reverse relationships can be traversed as well. For example, the following will find all devices with an interface named "em0":

```python
>>> Device.objects.filter(interfaces__name="em0")
```

Character fields can be filtered against partial matches using the `contains` or `icontains` field lookup (the later of which is case-insensitive).

```python
>>> Device.objects.filter(name__icontains="testdevice")
```

Similarly, numeric fields can be filtered by values less than, greater than, and/or equal to a given value.

```python
>>> VLAN.objects.filter(vid__gt=2000)
```

Multiple filters can be combined to further refine a queryset.

```python
>>> VLAN.objects.filter(vid__gt=2000, name__icontains="engineering")
```

To return the inverse of a filtered queryset, use `exclude()` instead of `filter()`.

```python
>>> Device.objects.count()
4479
>>> Device.objects.filter(status="active").count()
4133
>>> Device.objects.exclude(status="active").count()
346
```

!!! info
    The examples above are intended only to provide a cursory introduction to queryset filtering. For an exhaustive list of the available filters, please consult the [Django queryset API documentation](https://docs.djangoproject.com/en/stable/ref/models/querysets/).

## Creating and Updating Objects

New objects can be created by instantiating the desired model, defining values for all required attributes, and calling `validated_save()` on the instance. For example, we can create a new VLAN by specifying its numeric ID, name, and assigned site:

```python
>>> lab1 = Site.objects.get(pk="8a2c9c3b-076e-4688-8a0b-89362f343a26")
>>> myvlan = VLAN(vid=123, name="MyNewVLAN", site=lab1)
>>> myvlan.validated_save()
```

Alternatively, the above can be performed as a single operation. (Note, however, that `validated_save()` does _not_ return the new instance for reuse.)

```python
>>> VLAN(vid=123, name="MyNewVLAN", site=Site.objects.get(pk="8a2c9c3b-076e-4688-8a0b-89362f343a26")).validated_save()
```

To modify an existing object, we retrieve it, update the desired field(s), and call `validated_save()` again.

```python
>>> vlan = VLAN.objects.get(pk="b4b4344f-f6bb-4ceb-85bc-4f169c753157")
>>> vlan.name
'MyNewVLAN'
>>> vlan.name = 'BetterName'
>>> vlan.validated_save()
>>> VLAN.objects.get(pk="b4b4344f-f6bb-4ceb-85bc-4f169c753157").name
'BetterName'
```

!!! warning
    It is recommended to make use of the `validated_save()` convenience method which exists on all core models. While the Django `save()` method still exists, the `validated_save()` method saves the instance data but first enforces model validation logic. Simply calling `save()` on the model instance **does not** enforce validation automatically and may lead to bad data. See the development [best practices](../development/best-practices.md).

!!! warning
    The Django ORM provides methods to create/edit many objects at once, namely `bulk_create()` and `update()`. These are best avoided in most cases as they bypass a model's built-in validation and can easily lead to database corruption if not used carefully.

## Deleting Objects

To delete an object, simply call `delete()` on its instance. This will return a dictionary of all objects (including related objects) which have been deleted as a result of this operation.

```python
>>> vlan
<VLAN: 123 (BetterName)>
>>> vlan.delete()
(1, {'ipam.VLAN': 1})
```

To delete multiple objects at once, call `delete()` on a filtered queryset. It's a good idea to always sanity-check the count of selected objects _before_ deleting them.

```python
>>> Device.objects.filter(name__icontains='test').count()
27
>>> Device.objects.filter(name__icontains='test').delete()
(35, {'dcim.DeviceBay': 0, 'dcim.InterfaceConnection': 4,
'extras.ImageAttachment': 0, 'dcim.Device': 27, 'dcim.Interface': 4,
'dcim.ConsolePort': 0, 'dcim.PowerPort': 0})
```

!!! warning
    Deletions are immediate and irreversible. Always consider the impact of deleting objects carefully before calling `delete()` on an instance or queryset.

## Change Logging and Webhooks

Note that Nautobot's change logging and webhook processing features operate under the context of an HTTP request. As such, these functions do not work automatically when using the ORM directly, either through the `nbshell` or otherwise. A special context manager is provided to allow these features to operate under an emulated HTTP request context. This context manager must be explicitly invoked for change log entries and webhooks to be created when interacting with objects through the ORM. Here is an example using the `web_request_context` context manager within the nbshell:

```python
>>> from nautobot.extras.context_managers import web_request_context
>>> user = User.objects.get(username="admin")
>>> with web_request_context(user):
...     lax = Site(name="LAX")
...     lax.validated_save()
```

A `User` object must be provided. A `WSGIRequest` may optionally be passed and one will automatically be created if not provided.
