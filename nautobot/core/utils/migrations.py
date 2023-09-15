import sys
from django.db import models


def check_for_duplicates_with_natural_key_fields_in_migration(model_class, natural_key_fields):
    """
    Migration helper method to raise a RuntimeError if the existing model_class data contains incorrigible duplicate records.

    Args:
        model_class: Nautobot model class (Device, VirtualChassis and etc)
        natural_key_fields: Names of the fields serving as natural keys for the model_class.
    """
    duplicate_records = (
        model_class.objects.values(*natural_key_fields)
        .order_by()
        .annotate(count=models.Count("pk"))
        .filter(count__gt=1)
    )
    print("\n    Checking for duplicate records ...")
    if duplicate_records.exists():
        if len(natural_key_fields) > 1:
            print(
                f"    Duplicate {model_class.__name__} attributes '{*natural_key_fields,}' detected: {list(duplicate_records.values_list(*natural_key_fields))}",
                file=sys.stderr,
            )
        else:
            print(
                f"    Duplicate {model_class.__name__} attribute '{natural_key_fields[0]}' detected: {list(duplicate_records.values_list(natural_key_fields[0], flat=True))}",
                file=sys.stderr,
            )
        print(
            f"    Unable to proceed with migrations; in Nautobot 2.0+ attribute(s) {natural_key_fields} for these records must be unique.",
            file=sys.stderr,
        )
        raise RuntimeError("Duplicate records must be manually resolved before migrating.")
