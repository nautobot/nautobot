# Sensitive Model Fields

+++ 3.2.5

A model derived from `BaseModel` can declare that certain fields hold values the ORM must not hand back, by listing them in `sensitive_fields`:

```python
from nautobot.apps.models import BaseModel


class Token(BaseModel):
    key = models.CharField(max_length=40, unique=True)

    sensitive_fields = ("key",)
```

Declaring a field this way means user-authored Jinja2 templates can never read it, and that code which legitimately needs the value has to ask for it explicitly rather than getting it by accident.

Use this for a field that holds a credential or a comparable secret: an API token, a signing key, a password hash. Do not use it for a field that is merely uninteresting or internal, since that is what a leading underscore in the field name (e.g., `_key`) already conveys.

Every name must resolve to a concrete, non-relational, non-primary-key field on that model. A name that does not raises `ImproperlyConfigured` as the model class is prepared, which stops Nautobot from starting. That is deliberate: the alternative to failing here is a model that advertises a protection it does not actually have, which is exactly what a typo would produce.

A companion system check (`nautobot.core.E011`) reports a model that declares `sensitive_fields` but whose default queryset cannot enforce them; see [For App authors writing a custom queryset](#for-app-authors-writing-a-custom-queryset) below.

## What gets blocked

!!! note
    Both of the protections in this section are ORM-side, and so are governed by `STRICT_SENSITIVE_FIELDS`, which defaults to `False` ([below](#the-strict_sensitive_fields-setting)). User-authored template access is not governed by this setting and is unconditionally denied.

**Reading the attribute.** The value is dropped as each object is built from a database row, so reading the attribute raises `SensitiveFieldError`. This includes lookups, `only()`, `select_related()`, `prefetch_related()`, `in_bulk()`, `raw()` and `refresh_from_db()`.

**Projecting the value through a query.** Some queries never build objects at all, so the query methods that select columns into results are checked separately: `values()`, `values_list()`, `annotate()`, `alias()`, `aggregate()`, `order_by()` and `distinct()`. This also covers reaching the field indirectly from an unrelated model, so `User.objects.values_list("tokens__key")` is refused just as `Token.objects.values_list("key")` is.

!!! note
    Called with no arguments, `values()` and `values_list()` will only return the model's non-sensitive fields.

## What stays allowed

**Filtering.** You can still look an object up by a sensitive field. The guarantee is that the value is never returned to you, not that the column cannot be referenced, and API token authentication depends on being able to find a token by its key:

```python
>>> Token.objects.get(key=key_from_request_header)   # works
<Token: ...>
>>> Token.objects.get(pk=pk).key                     # raises SensitiveFieldError
```

**Values your own code assigned.** The protection applies to values coming *out of* the database. An object you just constructed or saved still reads back normally, which is why creating a token and then using its key works exactly as before:

```python
>>> token = Token.objects.create(user=user)
>>> token.key            # works: your code generated this value
'4a1b...'
```

**Saving and validating.** Saving an object whose sensitive value was withheld leaves that column untouched rather than blanking it, and `validated_save()` skips validating a field whose value is not present. A value you *did* assign is validated as normal, including uniqueness.

## Reading a value on purpose

Two methods are provided to opt in explicitly.

```python
# Query level. No additional query; use this when fetching more than one object.
Token.objects.with_sensitive_fields("key").get(pk=pk).key

# Instance level, for an object you already hold. Costs one additional query.
token.get_sensitive_field("key")
```

`with_sensitive_fields()` accepts any number of field names but requires at least one. There is deliberately no way to opt in to every sensitive field at once: naming the field is what lets a reader (or a reviewer, or a `grep`) see which value a given call site discloses, and a blanket opt-in would also silently widen to cover any sensitive field the model gained later. Passing a name the model has not declared sensitive raises `ValueError`.

The instance method's extra query is deliberate. Opting in to reading a credential should not look free.

## Catching the error

`SensitiveFieldError` is importable from the App interface, and subclasses Django's `FieldError` so that generic code already handling an unusable field reference degrades sensibly rather than returning a 500:

```python
from nautobot.apps.exceptions import SensitiveFieldError
```

It is deliberately *not* an `AttributeError`. Making it one would cause `hasattr(obj, "key")` to return `False` and `getattr(obj, "key", "")` to return the default, so generic code and Django templates would silently render nothing where a value was withheld. Failing loudly is the intent.

## Fields the framework reads constantly

Some sensitive fields are read by framework internals on a hot path. `User.password` is the example in core: Django reads it directly when verifying a password and when validating a session, the latter on every session-authenticated request. Withholding it from the instance would mean re-fetching it per request for no benefit, since the disclosure route worth closing is the template one.

List such a field in `sensitive_fields_kept_on_instance` as well, which must be a subset of `sensitive_fields`:

```python
class User(BaseModel, AbstractUser):
    sensitive_fields = ("password",)
    sensitive_fields_kept_on_instance = ("password",)
```

The value is then left on a database-loaded instance and Python reads the attribute normally, while templates and query projections are still refused. Reach for this only when a field really is read routinely by code you do not control; withholding by default is what forces a caller to opt in deliberately.

## The `STRICT_SENSITIVE_FIELDS` setting

The two ORM-side protections above are governed by [`STRICT_SENSITIVE_FIELDS`](../../user-guide/administration/configuration/settings.md#strict_sensitive_fields), which defaults to `False`.

**Template access is never governed by this setting.** A user-authored template is refused a sensitive field whether the setting is on or off.

!!! note
    The `STRICT_SENSITIVE_FIELDS` setting is expected to default to `True` in a future major release.

## Limitations

This reduces accidental exposure through generic machinery. It is not a sandbox, and the documentation for the setting says so plainly. Anyone who can author a Job or open `nautobot-server nbshell` runs arbitrary Python and can reach the column through raw SQL.

Specifically:

- Raw SQL is not checked, including `extra()`, `raw()` with a column alias, and `RawSQL()`.
- A query that *starts* on a model whose queryset is a plain `django.db.models.QuerySet`, such as one of Django's own built-in models, can still project a sensitive field by traversing a relation to it. Reading it off an object is still refused.
- `nautobot-server dumpdata` is deliberately exempt and serializes these values, so that backup and database migration workflows keep working. Running any management command already implies enough access to read the column directly, so refusing would protect nothing.
- Migrations are unaffected by design, since historical models do not inherit `BaseModel`. A data migration can read the column.
- A `ModelForm`, a Django admin `list_display`, or Django's own serializers will raise if given a sensitive field without an opt-in queryset.
- `hasattr()` raises rather than returning `False`, as described above.

## For App authors writing a custom queryset

Enforcement is inherited, so an App model built on `BaseModel` and an App queryset built on `RestrictedQuerySet` both pick it up with no extra work. If an App defines a queryset class from scratch rather than building on Nautobot's, mix in `SensitiveFieldsQuerySetMixin` to get the projection checks:

```python
from nautobot.apps.models import SensitiveFieldsQuerySetMixin
```

Note that a custom manager which overrides `get_queryset()` without calling `super()` will not pick up the protections.

`nautobot-server check` reports this as `nautobot.core.E011` for any model that declares `sensitive_fields` while its default queryset lacks the mixin. Such a model still withholds the values from loaded instances, but `values()`, `values_list()`, `annotate()`, `alias()`, `aggregate()`, `order_by()` and `distinct()` will return them.
