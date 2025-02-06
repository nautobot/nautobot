import logging

from django.db import NotSupportedError

logger = logging.getLogger(__name__)


def maybe_select_related(queryset, select_fields):
    """Attempt to perform a select_related() on the given queryset, but fail gracefully if not permitted."""
    model = queryset.model

    # Django doesn't allow .select_related() on a QuerySet that had .values()/.values_list() applied, or
    # one that has had union()/intersection()/difference() applied.
    # We can detect and avoid these cases the same way that Django itself does.
    if queryset._fields is not None:
        logger.debug(
            "NOT applying select_related(%s) to %s QuerySet as it includes .values()/.values_list()",
            select_fields,
            model.__name__,
        )
    elif queryset.query.combinator:
        logger.debug(
            "NOT applying select_related(%s) to %s QuerySet as it is a combinator query",
            select_fields,
            model.__name__,
        )
    else:
        logger.debug("Applying .select_related(%s) to %s QuerySet", select_fields, model.__name__)
        # Belt and suspenders - we should have avoided any error cases above, but be safe anyway:
        try:
            queryset = queryset.select_related(*select_fields)
        except (TypeError, ValueError, NotSupportedError) as exc:
            logger.warning(
                "Unexpected error when trying to .select_related() on %s QuerySet: %s",
                model.__name__,
                exc,
            )

    return queryset


def maybe_prefetch_related(queryset, prefetch_fields):
    """Attempt to perform a select_related() on the given queryset, but fail gracefully if not permitted."""
    model = queryset.model

    if queryset.query.combinator:
        logger.debug(
            "NOT applying prefetch_related(%s) to %s QuerySet as it is a combinator query",
            prefetch_fields,
            model.__name__,
        )
    else:
        logger.debug("Applying .prefetch_related(%s) to %s QuerySet", prefetch_fields, model.__name__)
        # Belt and suspenders - we should have avoided any error cases above, but be safe anyway:
        try:
            queryset = queryset.prefetch_related(*prefetch_fields)
        except (AttributeError, TypeError, ValueError, NotSupportedError) as exc:
            logger.warning(
                "Unexpected error when trying to .prefetch_related() on %s QuerySet: %s",
                model.__name__,
                exc,
            )

    return queryset
