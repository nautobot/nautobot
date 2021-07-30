"""
django-slugger
~~~~~

:copyright: (c) 2017-2018 Dmitry Pechnikov
:license: MIT, see NOTICE for more details.
"""

from functools import reduce
from operator import or_

from django.core import checks
from django.db import models
from django.db.models import Q
from django.utils.text import slugify as django_slugify


class AutoSlugField(models.SlugField):
    """Allows Slug field value to be automatically generated if a value is not provided.

    This field supports all "uniqueness" constraints. A numerical suffix will be added to
    prevent a unique constraint violation. This field also supports max_length, but cannot
    guarantee the uniqueness suffix.
    """
    def __init__(self, populate_from, slugify=None, *args, **kwargs):
        """Generate slug value from the populate_from field.

        Supports custom slug templates using the slugify argument.
        EX:
            ```
            from nautobot.core.fields import AutoSlugField


            def custom_slugify(value):
                return f"custom-{value}"

            class CustomModel(models.Model):
                name = models.CharField(max_length=255)
                slug = AutoSlugField(populate_from='name', slugify=custom_slugify)
            ```

        Args:
            populate_from (str): Field to slugify to create the Slug Field.
            slugify (func, optional): Template that converts populate_from field to string. Defaults to None.
        """
        self.populate_from = populate_from
        self.slugify = slugify or django_slugify

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        kwargs['populate_from'] = self.populate_from

        if self.slugify != django_slugify:
            kwargs['slugify'] = self.slugify

        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = list(self._check_callable_attributes())
        errors.extend(self._check_self_reference())

        return errors

    def _check_callable_attributes(self):
        if self.slugify.__name__ == '<lambda>':
            return [
                checks.Error(
                    '`slugify` argument must be named top-level function.',
                    obj=self,
                    id='slugger.E001',
                )
            ]

        return []

    def _check_self_reference(self):
        if self.populate_from == self.attname:
            return [
                checks.Error(
                    '`populate_from` argument cannot reference its own '
                    'field name.',
                    obj=self,
                    id='slugger.E002',
                )
            ]

        return []

    def formfield(self, **kwargs):
        defaults = {
            'required': False,
        }

        defaults.update(kwargs)

        return super().formfield(**defaults)

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)

        if not value:
            from_field_value = getattr(model_instance, self.populate_from)
            value = self.slugify(from_field_value)

            if any((self.unique, self.unique_for_date,
                    self.unique_for_month, self.unique_for_year,
                    self.model._meta.unique_together)):
                value = self.get_unique_slug(value, model_instance)

            setattr(model_instance, self.attname, value)

        return value[:self.max_length]

    def _get_unique_lookups(self, instance):
        # Combine "uniqueness" lookups into single query to retrieve
        # objects which must have slugs different from this instance

        # slug must be globally unique, do not exclude anything
        if self.unique:
            return Q()

        lookups = []

        # `date` QuerySet filter lookup is not supported for DateField,
        # use separate lookups to handle both DateField and DateTimeField
        if self.unique_for_date:
            lookup_value = getattr(instance, self.unique_for_date)
            lookups.append({
                '%s__day' % self.unique_for_date: lookup_value.day,
                '%s__month' % self.unique_for_date: lookup_value.month,
                '%s__year' % self.unique_for_date: lookup_value.year,
            })

        if self.unique_for_month:
            lookup_value = getattr(instance, self.unique_for_month)
            lookups.append({
                '%s__month' % self.unique_for_month: lookup_value.month,
            })

        if self.unique_for_year:
            lookup_value = getattr(instance, self.unique_for_year)
            lookups.append({
                '%s__year' % self.unique_for_year: lookup_value.year,
            })

        def _get_unique_together_groups():
            for field_group in self.model._meta.unique_together:
                if self.attname in field_group:
                    yield (field_name for field_name in field_group
                           if field_name != self.attname)

        for field_group in _get_unique_together_groups():
            lookups.append({field_name: getattr(instance, field_name)
                            for field_name in field_group})

        return reduce(
            or_,
            (Q(**lookup) for lookup in lookups),
            Q()
        )

    def get_unique_slug(self, slug, instance):
        conflicts = self.model._default_manager.filter(
            ~Q(pk=instance.pk),
            self._get_unique_lookups(instance),
        )

        taken_slugs = sorted(conflicts.filter(
            **{'%s__regex' % self.attname: r'^%s(-\d+)?$' % slug}
        ).values_list(self.attname, flat=True))

        if slug not in taken_slugs:
            return slug

        # generated slug is taken, remove it to ease searching for suffix
        taken_slugs.remove(slug)

        i = 1
        for value in taken_slugs:
            if not value.endswith(str(i)):
                break

            i += 1

        return '%s-%s' % (slug, i)

