import itertools

from django.db import models

from thunderstore.permissions.models import VisibilityFlags

FLAG_FIELDS = [
    field.name
    for field in VisibilityFlags._meta.get_fields()
    if isinstance(field, models.BooleanField)
]


def assert_all_visible(visibility: VisibilityFlags):
    for field in FLAG_FIELDS:
        assert getattr(visibility, field) is True


def get_flags_cartesian_product():
    """
    Returns all possible combinations for visibility flag field values to be
    used with fixtures.
    """
    if len(FLAG_FIELDS) > 10:  # pragma: no cover
        # Just to make sure we don't accidentally introduce exponential test
        # case counts without noticing it.
        raise ValueError(
            "Excessive amount of visibility flags detected for test fixtures, "
            "rework me to not use cartesian product!\n"
            f"Would have generated {2**len(FLAG_FIELDS)} tests!"
        )

    return (
        dict(zip(FLAG_FIELDS, vals))
        for vals in itertools.product(*((False, True) for _ in range(len(FLAG_FIELDS))))
    )
