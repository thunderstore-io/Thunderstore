import pytest

from thunderstore.permissions.models import VisibilityFlags
from thunderstore.permissions.models.tests._utils import (
    FLAG_FIELDS,
    get_flags_cartesian_product,
)


@pytest.mark.django_db
def test_visibility_flags_queryset_create_public():
    flags: VisibilityFlags = VisibilityFlags.objects.create_public()
    assert flags.public_list is True
    assert flags.public_detail is True
    assert flags.owner_list is True
    assert flags.owner_detail is True
    assert flags.moderator_list is True
    assert flags.moderator_detail is True
    assert flags.admin_list is True
    assert flags.admin_detail is True

    # Slight future proofing this test in case new fields are added
    for field in FLAG_FIELDS:
        assert getattr(flags, field) is True


@pytest.mark.django_db
@pytest.mark.parametrize("fields", get_flags_cartesian_product())
def test_visibility_flags_str(fields):
    flags = VisibilityFlags(**fields)
    stringified = str(flags)
    for name, val in fields.items():
        if val is True:
            assert name in stringified
        else:
            assert name not in stringified

    if not any(fields.values()):
        assert stringified == "None"
