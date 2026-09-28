"""Tests for `Model.sensitive_fields`, which blocks ORM retrieval of a declared field's value.

The mechanism tests below deliberately target `Manufacturer.description`, an ordinary non-secret field
temporarily declared sensitive, rather than a real credential. The mechanism is field-agnostic: the block
happens at attribute access and at query construction, long before the value's identity matters, so a benign
field exercises exactly the same code paths. Targeting one keeps this file's coverage independent of any single
model's adoption of the feature, allows the negative control below to assert that a same-named field on a
different model is unaffected, and means these tests do not have to be rewritten when `Token`'s own adoption
details change.

Where a real sensitive field is used (`Token.key`), the assertions are that access is *blocked*, that a
filter still resolves, or that an opt-in path returns a value of the expected length. The key is always one
the test generated through `create()`, never a deployment's own credential, and a value read back from the
database is asserted by its length or by the documented `__str__` suffix rather than by its content. Nothing
here records a usable credential or demonstrates a way to obtain one.
"""

from io import StringIO
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db.models import F, Max, Q
from django.db.models.functions import Concat, Lower
from django.template import Context, Template
from django.test import override_settings, TestCase

from nautobot.core.exceptions import SensitiveFieldError
from nautobot.core.testing.utils import temporarily_sensitive_fields
from nautobot.dcim.models import DeviceType, Manufacturer
from nautobot.extras.models import Relationship
from nautobot.users.models import Token

User = get_user_model()


@override_settings(STRICT_SENSITIVE_FIELDS=True)
class SensitiveFieldsMechanismTest(TestCase):
    """Exercise the mechanism against a benign field temporarily declared sensitive, in strict mode."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="Test Manufacturer", description="not a secret")
        cls.device_type = DeviceType.objects.create(manufacturer=cls.manufacturer, model="Test Device Type")

    def test_attribute_access_on_loaded_instance_is_blocked(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.get(pk=self.manufacturer.pk)
            self.assertNotIn("description", instance.__dict__)
            with self.assertRaises(SensitiveFieldError):
                instance.description  # useless-expression -- reading it is the operation under test

    def test_value_assigned_in_python_remains_readable(self):
        # The protection is on values coming out of the database. A value the caller supplied is theirs.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer(name="In Memory", description="assigned in python")
            self.assertEqual(instance.description, "assigned in python")

    def test_created_instance_remains_readable(self):
        # `objects.create()` must keep working: a great deal of existing code creates an object and then
        # reads back the field it just supplied or that `save()` generated.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.create(name="Just Created", description="fresh")
            self.assertEqual(instance.description, "fresh")

    def test_projection_is_blocked(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            queryset = Manufacturer.objects.all()
            with self.subTest("values"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values("description"))
            with self.subTest("values_list"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values_list("description"))
            with self.subTest("values_list flat"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values_list("description", flat=True))
            with self.subTest("distinct_values_list"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.distinct_values_list("description", flat=True))
            with self.subTest("annotate F"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.annotate(exfiltrated=F("description")))
            with self.subTest("annotate aggregate"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.annotate(exfiltrated=Max("description")))
            with self.subTest("annotate nested function"):
                # Bare strings inside a `Func` are coerced to `F` by Django, so the expression walk must
                # reach them too.
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.annotate(exfiltrated=Concat("name", "description")))
            with self.subTest("alias"):
                # Checked separately from annotate, or `alias(...).values(...)` walks straight through.
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.alias(exfiltrated=F("description")).values("exfiltrated"))
            with self.subTest("aggregate"):
                with self.assertRaises(SensitiveFieldError):
                    queryset.aggregate(Max("description"))
            with self.subTest("order_by"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.order_by("description"))
            with self.subTest("distinct on"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.distinct("description"))

    def test_expression_projections_are_blocked(self):
        # A non-string argument is skipped by the lookup-path check by design, so these prove the
        # expression checker really does cover it rather than the value slipping through unexamined.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            queryset = Manufacturer.objects.all()
            with self.subTest("values_list(F(...))"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values_list(F("description")))
            with self.subTest("values_list(Lower(...))"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values_list(Lower("description")))
            with self.subTest("values_list(Lower(...), flat=True)"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.values_list(Lower("description"), flat=True))
            with self.subTest("order_by(F(...).desc())"):
                with self.assertRaises(SensitiveFieldError):
                    list(queryset.order_by(F("description").desc()))

    def test_a_q_object_in_an_annotation_is_permitted(self):
        # `Q` is neither a `Combinable` nor a source-expression tree, so the expression checker passes over
        # it. That is deliberate rather than an oversight: this yields a boolean, disclosing exactly what
        # `filter(description=...)` already discloses, and filtering by a sensitive field stays permitted
        # because token authentication depends on it.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            rows = list(
                Manufacturer.objects.filter(pk=self.manufacturer.pk)
                .annotate(matched=Q(description="not a secret"))
                .values("matched")
            )
            self.assertEqual(rows, [{"matched": True}])

    def test_ordering_by_an_expression_on_a_benign_field_still_works(self):
        # The counterpart to the above: skipping non-strings in the lookup-path check is what keeps
        # ordinary expression ordering working, so it must not have become collateral damage.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            self.assertIn(
                self.manufacturer,
                list(Manufacturer.objects.order_by(F("name").desc())),
            )

    def test_bare_values_omits_the_field_rather_than_raising(self):
        # Bare `values()`/`values_list()` are called routinely by generic code; raising would make any
        # model with a sensitive field unusable with them.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            row = Manufacturer.objects.filter(pk=self.manufacturer.pk).values().first()
            self.assertIn("name", row)
            self.assertNotIn("description", row)

    def test_traversal_from_another_model_is_blocked(self):
        # The sensitive field belongs to a model several joins away from the queryset's own model, so the
        # check cannot live on the owning model's manager.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            with self.assertRaises(SensitiveFieldError):
                list(DeviceType.objects.values_list("manufacturer__description", flat=True))

    def test_only_still_blocks_attribute_access(self):
        # `only()` asks for the column explicitly, but the value is dropped when the instance is built.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.only("pk", "description").get(pk=self.manufacturer.pk)
            with self.assertRaises(SensitiveFieldError):
                instance.description  # useless-expression -- reading it is the operation under test

    def test_select_related_still_blocks_attribute_access(self):
        # `select_related` builds the related instance from the joined row rather than through its manager.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            device_type = DeviceType.objects.select_related("manufacturer").get(pk=self.device_type.pk)
            with self.assertRaises(SensitiveFieldError):
                device_type.manufacturer.description  # useless-expression -- the operation under test

    def test_refresh_from_db_reblocks(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.with_sensitive_fields("description").get(pk=self.manufacturer.pk)
            self.assertEqual(instance.description, "not a secret")
            instance.refresh_from_db()
            with self.assertRaises(SensitiveFieldError):
                instance.description  # useless-expression -- reading it is the operation under test

    def test_refresh_from_db_naming_a_sensitive_field_warns(self):
        # Asking for the field by name is the one case where the caller clearly expected to get the value,
        # so the discard is surfaced rather than silent.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.with_sensitive_fields("description").get(pk=self.manufacturer.pk)
            with self.assertLogs("nautobot.core.models", level="WARNING") as logs:
                instance.refresh_from_db(fields=["description"])
            self.assertIn("description", logs.output[0])
            with self.assertRaises(SensitiveFieldError):
                instance.description  # useless-expression -- reading it is the operation under test

    def test_refresh_from_db_without_naming_a_sensitive_field_does_not_warn(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.get(pk=self.manufacturer.pk)
            with self.assertNoLogs("nautobot.core.models", level="WARNING"):
                instance.refresh_from_db()
                instance.refresh_from_db(fields=["name"])

    def test_opt_in_methods_are_not_auto_called_by_a_django_template(self):
        # A Django template auto-calls any callable it resolves, and `with_sensitive_fields()` takes no
        # required arguments, so without `do_not_call_in_templates` it would opt in to every sensitive field.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            context = Context(
                {
                    "qs": Manufacturer.objects.filter(pk=self.manufacturer.pk),
                    "obj": Manufacturer.objects.get(pk=self.manufacturer.pk),
                }
            )
            rendered = Template("{{ qs.with_sensitive_fields }}|{{ obj.get_sensitive_field }}").render(context)
            self.assertNotIn("not a secret", rendered)
            # The lookup resolves to the uncalled method, so nothing downstream of it can be opted in either.
            for template_str in (
                "{% for m in qs.with_sensitive_fields %}{{ m.description }}{% endfor %}",
                "{{ qs.with_sensitive_fields.first.description }}",
            ):
                with self.subTest(template=template_str):
                    try:
                        rendered = Template(template_str).render(context)
                    except TypeError:
                        continue  # Django's `for` tag refusing to iterate the method is also a refusal.
                    self.assertNotIn("not a secret", rendered)

    def test_filtering_is_permitted(self):
        # Filtering is intentionally allowed. The contract is that the value is never returned, not that
        # the column cannot be referenced, and API token authentication looks a token up by its key.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            self.assertTrue(Manufacturer.objects.filter(description="not a secret").exists())
            self.assertTrue(Manufacturer.objects.filter(description__startswith="not").exists())
            self.assertEqual(Manufacturer.objects.get(description="not a secret").pk, self.manufacturer.pk)
            self.assertFalse(
                Manufacturer.objects.filter(pk=self.manufacturer.pk).exclude(description="not a secret").exists()
            )

    def test_save_and_validate_loaded_instance(self):
        # `full_clean()` reads every field's value directly, so a withheld field has to be excluded or
        # every update of a loaded instance would fail.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.get(pk=self.manufacturer.pk)
            instance.name = "Renamed Manufacturer"
            instance.validated_save()
        instance.refresh_from_db()
        self.assertEqual(instance.name, "Renamed Manufacturer")
        # The withheld column was left alone rather than blanked out.
        self.assertEqual(instance.description, "not a secret")

    def test_queryset_opt_in(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.with_sensitive_fields("description").get(pk=self.manufacturer.pk)
            self.assertEqual(instance.description, "not a secret")

    def test_queryset_opt_in_does_not_leak_to_a_sibling_queryset(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            base = Manufacturer.objects.all()
            opted_in = base.with_sensitive_fields("description")
            self.assertEqual(opted_in.get(pk=self.manufacturer.pk).description, "not a secret")
            with self.assertRaises(SensitiveFieldError):
                list(base.values_list("description", flat=True))

    def test_instance_opt_in(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.get(pk=self.manufacturer.pk)
            with self.assertNumQueries(1):
                self.assertEqual(instance.get_sensitive_field("description"), "not a secret")
            with self.assertNumQueries(0):
                self.assertEqual(instance.get_sensitive_field("description"), "not a secret")

    def test_opt_in_rejects_a_field_that_is_not_declared_sensitive(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            with self.assertRaises(ValueError):
                Manufacturer.objects.with_sensitive_fields("name")
            with self.assertRaises(ValueError):
                Manufacturer.objects.get(pk=self.manufacturer.pk).get_sensitive_field("name")

    def test_a_misdeclared_sensitive_field_refuses_to_install(self):
        # A name that cannot be resolved to a protectable field must fail loudly. Silently skipping it
        # would leave a model advertising a protection it does not have, which is the one outcome a
        # security control must never produce.
        for field_name, reason in (
            ("no_such_field", "not a field at all"),
            ("id", "primary key"),
            ("device_types", "reverse relation"),
        ):
            with self.subTest(field=field_name, reason=reason):
                with self.assertRaises(ImproperlyConfigured):
                    with temporarily_sensitive_fields(Manufacturer, field_name):
                        pass

    def test_opt_in_requires_a_field_name(self):
        # A blanket opt-in would hide which value a call site discloses, and would silently widen to any
        # sensitive field the model gained later.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            with self.assertRaises(ValueError):
                Manufacturer.objects.with_sensitive_fields()

    def test_natural_key_does_not_default_to_a_sensitive_unique_field(self):
        # `natural_key_field_lookups` otherwise falls back to the first `unique=True` field, and a natural
        # key is rendered into composite keys, CSV exports and URLs, so a secret must never become one.
        # `Manufacturer.name` is its only unique field, so once it is excluded the model has no intrinsic
        # natural key at all and the existing "declare natural_key_field_names explicitly" error is raised.
        # Failing loudly is the correct outcome here; silently publishing the secret is the bug avoided.
        self.assertIn("name", Manufacturer.natural_key_field_lookups)
        with temporarily_sensitive_fields(Manufacturer, "name"):
            with self.assertRaises(AttributeError):
                Manufacturer.natural_key_field_lookups  # useless-expression -- under test

    def test_a_same_named_field_on_another_model_is_unaffected(self):
        # Guards against matching on the field name alone: the lookup path is resolved against its owning
        # model, so an unrelated model that happens to share a field name keeps working.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            self.assertIsInstance(list(Relationship.objects.values_list("description", flat=True)), list)
            self.assertIsInstance(list(DeviceType.objects.values_list("comments", flat=True)), list)


class SensitiveFieldsNonStrictTest(TestCase):
    """Verify that with `STRICT_SENSITIVE_FIELDS` disabled, reading a sensitive field behaves as it always did.

    This is the default configuration for Nautobot 3.x, so these are the backwards-compatibility guarantees.
    """

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="Non Strict Manufacturer", description="readable")
        cls.user = User.objects.create_user(username="non-strict-testuser")
        cls.token = Token.objects.create(user=cls.user)

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_attribute_access_is_permitted(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            self.assertEqual(Manufacturer.objects.get(pk=self.manufacturer.pk).description, "readable")

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_projections_are_permitted(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            queryset = Manufacturer.objects.filter(pk=self.manufacturer.pk)
            self.assertEqual(list(queryset.values_list("description", flat=True)), ["readable"])
            self.assertEqual(queryset.values("description").first(), {"description": "readable"})
            self.assertEqual(queryset.annotate(copied=F("description")).first().copied, "readable")
            self.assertEqual(queryset.aggregate(Max("description"))["description__max"], "readable")
            self.assertEqual(
                list(queryset.order_by("description").values_list("pk", flat=True)), [self.manufacturer.pk]
            )

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_bare_values_still_includes_the_field(self):
        with temporarily_sensitive_fields(Manufacturer, "description"):
            row = Manufacturer.objects.filter(pk=self.manufacturer.pk).values().first()
            self.assertIn("description", row)

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_deferred_field_still_lazy_loads(self):
        # With the setting off, a genuinely deferred field must still load on access rather than raising.
        with temporarily_sensitive_fields(Manufacturer, "description"):
            instance = Manufacturer.objects.only("pk").get(pk=self.manufacturer.pk)
            self.assertEqual(instance.description, "readable")

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_token_key_is_readable(self):
        # The behavior every existing caller of `Token.key` depends on, including `docker-entrypoint.sh`.
        self.assertEqual(len(Token.objects.get(pk=self.token.pk).key), 40)
        self.assertEqual(len(Token.objects.filter(pk=self.token.pk).values_list("key", flat=True).first()), 40)
        self.assertEqual(
            len(User.objects.filter(pk=self.user.pk).values_list("tokens__key", flat=True).first()),
            40,
        )

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_opt_in_methods_still_work(self):
        # The opt-in API must be usable regardless of the setting, so callers can adopt it before the
        # default changes without having to branch on configuration.
        self.assertEqual(len(Token.objects.with_sensitive_fields("key").get(pk=self.token.pk).key), 40)
        self.assertEqual(len(Token.objects.get(pk=self.token.pk).get_sensitive_field("key")), 40)

    @override_settings(STRICT_SENSITIVE_FIELDS=False)
    def test_natural_key_fallback_is_unchanged(self):
        # Changing a model's natural key changes its composite keys, so that is gated on the setting too.
        with temporarily_sensitive_fields(Manufacturer, "name"):
            self.assertIn("name", Manufacturer.natural_key_field_lookups)


@override_settings(STRICT_SENSITIVE_FIELDS=True)
class TokenSensitiveKeyTest(TestCase):
    """`Token.key` is declared sensitive, so verify the paths that matter for API tokens specifically."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="sensitive-fields-testuser")
        cls.token = Token.objects.create(user=cls.user)

    def test_key_is_readable_on_the_created_instance(self):
        # `Token.objects.create()` returning a usable key is what keeps the existing test suite and the
        # token provisioning API working; the value was assigned by `save()`, not loaded from the database.
        self.assertEqual(len(self.token.key), 40)

    def test_key_is_not_readable_on_a_reloaded_token(self):
        reloaded = Token.objects.get(pk=self.token.pk)
        with self.assertRaises(SensitiveFieldError):
            reloaded.key  # useless-expression -- reading it is the operation under test

    def test_key_cannot_be_projected(self):
        with self.assertRaises(SensitiveFieldError):
            list(Token.objects.values_list("key", flat=True))

    def test_key_cannot_be_reached_by_traversal_from_user(self):
        # `UserQuerySet` is deliberately not a `RestrictedQuerySet`, so this proves the check is installed
        # broadly enough to cover a query that starts on a different model's queryset class.
        with self.assertRaises(SensitiveFieldError):
            list(User.objects.values_list("tokens__key", flat=True))

    def test_token_can_still_be_looked_up_by_key(self):
        # API token authentication does `Token.objects.get(key=...)`, which must keep working.
        self.assertEqual(Token.objects.get(key=self.token.key).pk, self.token.pk)

    def test_str_shows_the_key_suffix_when_the_key_is_available(self):
        # Existing behavior: the last 6 characters are shown. Preserved for now.
        self.assertEqual(str(self.token), f"{self.token.key[-6:]} ({self.user})")
        opted_in = Token.objects.with_sensitive_fields("key").get(pk=self.token.pk)
        self.assertEqual(str(opted_in), f"{self.token.key[-6:]} ({self.user})")

    def test_str_falls_back_when_the_key_is_withheld(self):
        # `__str__` is called from the admin, from form error messages and from `repr`, so it must not
        # raise for an instance that was loaded without opting in.
        reloaded = Token.objects.get(pk=self.token.pk)
        self.assertEqual(str(reloaded), f"Token {self.token.pk} ({self.user})")
        self.assertNotIn(self.token.key[-6:], str(reloaded))

    def test_dumpdata_serializes_sensitive_fields(self):
        """Django's serializers must be able to read sensitive fields, so `dumpdata` keeps working.

        Anyone able to run a management command can already read the column through `nbshell`, so
        refusing to serialize it protects nothing and would instead leave a truncated, unusable dump.
        """
        output = StringIO()
        call_command("dumpdata", "users.Token", format="json", stdout=output)
        records = json.loads(output.getvalue())

        self.assertTrue(records)
        self.assertIn("key", records[0]["fields"])
        self.assertEqual(len(records[0]["fields"]["key"]), 40)

        # The exemption must not outlive the command.
        with self.assertRaises(SensitiveFieldError):
            self.assertIsNone(Token.objects.get(pk=self.token.pk).key)

    def test_user_password_is_kept_on_the_instance(self):
        """`User.password` is sensitive but kept on the instance, so authentication costs no extra query.

        Django reads `self.password` when verifying a password and when validating a session, the latter
        on every session-authenticated request. Withholding it would make each of those re-fetch the
        value, so the field opts out of the instance scrub while remaining refused to templates and to
        query projections. A regression here would show up as a per-request query rather than an error,
        which is why the query count is asserted and not just the behavior.
        """
        user = User.objects.create_user(username="password-kept-testuser", password="s3cret-probe-value")  # noqa: S106
        reloaded = User.objects.get(pk=user.pk)

        self.assertIn("password", reloaded.__dict__)
        with self.assertNumQueries(0):
            self.assertTrue(reloaded.has_usable_password())
            self.assertTrue(reloaded.check_password("s3cret-probe-value"))
            self.assertFalse(reloaded.check_password("not-the-password"))
            self.assertEqual(len(reloaded.get_session_auth_hash()), 64)

    def test_user_password_is_still_refused_in_query_projections(self):
        """Keeping the value on the instance must not weaken the projection check."""
        with self.assertRaises(SensitiveFieldError):
            list(User.objects.values_list("password", flat=True))
        with self.assertRaises(SensitiveFieldError):
            list(Token.objects.values_list("user__password", flat=True))

    def test_another_models_key_field_is_unaffected(self):
        # `Relationship` also has a field named `key`, and it must stay readable. This is the negative
        # control for the real declaration rather than a temporarily patched one.
        self.assertIsInstance(list(Relationship.objects.values_list("key", flat=True)), list)

    def test_queryset_opt_in_returns_the_key(self):
        # The token UI page and the REST API both rely on this, scoped to the requesting user's own tokens.
        opted_in = Token.objects.with_sensitive_fields("key").get(pk=self.token.pk)
        self.assertEqual(len(opted_in.key), 40)

    def test_instance_opt_in_returns_the_key(self):
        reloaded = Token.objects.get(pk=self.token.pk)
        self.assertEqual(len(reloaded.get_sensitive_field("key")), 40)

    def test_superuser_token_reconciliation_pattern(self):
        """Exercise the key-reconciliation logic that `docker/docker-entrypoint.sh` runs on container start.

        That script provisions a superuser and forces its token to `NAUTOBOT_SUPERUSER_API_TOKEN`. It runs
        outside the test suite, in a shell heredoc, so this covers its logic here: comparing the stored key
        without retrieving it, and persisting a replacement onto an instance loaded from the database.

        Both settings are exercised, because the script has to work on a 3.x deployment using the default
        and on one that has opted in early, without the script branching on configuration.
        """
        for strict in (False, True):
            with self.subTest(strict=strict), override_settings(STRICT_SENSITIVE_FIELDS=strict):
                desired_key = Token.generate_key()
                token = Token.objects.filter(user=self.user)[0]

                self.assertFalse(Token.objects.filter(pk=token.pk, key=desired_key).exists())
                token.key = desired_key
                token.save()

                # The assignment must actually persist. `Model.save()` narrows `update_fields` to loaded
                # fields when an instance has deferred ones, so a withheld-then-reassigned field has to be
                # back in that set.
                self.assertTrue(Token.objects.filter(pk=token.pk, key=desired_key).exists())

                # Re-running must detect that no change is needed rather than rewriting the key, which is
                # what the comparison in the script is for.
                again = Token.objects.filter(user=self.user)[0]
                self.assertTrue(Token.objects.filter(pk=again.pk, key=desired_key).exists())

    def test_token_can_be_updated_and_validated_after_reloading(self):
        # `full_clean()` reads every field for the `unique=True` check on `key`, so updating a reloaded
        # token would fail without the withheld-field exclusion.
        reloaded = Token.objects.get(pk=self.token.pk)
        reloaded.description = "Updated description"
        reloaded.validated_save()
        self.assertEqual(Token.objects.get(pk=self.token.pk).description, "Updated description")
        # The key column was left intact rather than blanked or regenerated by `save()`.
        self.assertTrue(Token.objects.filter(pk=self.token.pk, key=self.token.key).exists())
