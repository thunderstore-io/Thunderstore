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


def assert_default_visibility(visibility: VisibilityFlags):
    assert visibility.public_detail is True
    assert visibility.public_list is True
    assert visibility.owner_detail is True
    assert visibility.owner_list is True
    assert visibility.moderator_detail is True
    assert visibility.moderator_list is True
    assert visibility.admin_detail is True
    assert visibility.admin_list is True


def assert_visibility_is_public(visibility: VisibilityFlags) -> None:
    assert visibility.public_list is True
    assert visibility.public_detail is True
    assert visibility.owner_list is True
    assert visibility.owner_detail is True
    assert visibility.moderator_list is True
    assert visibility.moderator_detail is True


def assert_visibility_is_not_public(visibility: VisibilityFlags) -> None:
    assert visibility.public_list is False
    assert visibility.public_detail is False
    assert visibility.owner_list is True
    assert visibility.owner_detail is True
    assert visibility.moderator_list is True
    assert visibility.moderator_detail is True


def assert_visibility_is_not_visible(visibility: VisibilityFlags) -> None:
    assert visibility.public_list is False
    assert visibility.public_detail is False
    assert visibility.owner_list is False
    assert visibility.owner_detail is False
    assert visibility.moderator_list is False
    assert visibility.moderator_detail is False


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
