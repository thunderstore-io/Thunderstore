from typing import Callable, List

import pytest
from django.db import DatabaseError, transaction
from django.db.models import QuerySet

from thunderstore.permissions.mixins import VisibilityMixin
from thunderstore.permissions.models import VisibilityFlags
from thunderstore.permissions.models.tests._utils import (
    assert_all_visible,
    get_flags_cartesian_product,
)
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_formats import PackageFormats


@pytest.mark.django_db
def test_visibility_mixin_autocreates_flags():
    a = PackageVersionFactory()
    assert a.visibility is not None
    assert_all_visible(a.visibility)

    b = PackageVersion.objects.create(
        package=a.package,
        format_spec=PackageFormats.get_active_format(),
        name=a.name,
        version_number=f"{a.version_number[:-1]}1",
        website_url="",
        readme="",
        file=a.file,
        file_size=a.file_size,
        icon=a.icon,
    )
    assert b.visibility is not None
    assert_all_visible(b.visibility)

    c = PackageVersion(
        package=a.package,
        format_spec=PackageFormats.get_active_format(),
        name=a.name,
        version_number=f"{a.version_number[:-1]}2",
        website_url="",
        readme="",
        file=a.file,
        file_size=a.file_size,
        icon=a.icon,
    )
    assert c.visibility is None
    c.save()
    assert c.visibility is not None
    assert_all_visible(c.visibility)


@pytest.fixture(scope="module")
def visibility_objs(django_db_setup, django_db_blocker):
    """
    Sets up module-scoped db fixtures for visibility rule testing in order to
    avoid re-creating hundreds of objects every test. The downside is that
    the db state management has to be manual.
    """
    with django_db_blocker.unblock():
        try:
            with transaction.atomic():
                # TODO: Use some other model than PackageVersion as it's not
                #       the most efficient. Also use bulk create to save time.
                yield [
                    PackageVersionFactory(
                        visibility=VisibilityFlags.objects.create(**fields)
                    )
                    for fields in get_flags_cartesian_product()
                ]
                raise DatabaseError("Forced rollback")
        except DatabaseError:
            pass


def assert_visibility_matches(
    objs: List[VisibilityMixin],
    expected_visibility: Callable[[VisibilityMixin], bool],
    results: QuerySet[VisibilityMixin],
):
    for entry in objs:
        if expected_visibility(entry):
            assert entry in results, f"Expected match missing: {entry.visibility}"
        else:
            assert entry not in results, f"Unexpected match found: {entry.visibility}"


def test_visibility_queryset_public_list(visibility_objs: List[VisibilityMixin]):
    def is_public_list(obj: VisibilityMixin) -> bool:
        return obj.visibility.public_list

    model_cls = type(visibility_objs[0])
    assert_visibility_matches(
        objs=visibility_objs,
        expected_visibility=is_public_list,
        results=model_cls.objects.public_list(),
    )


def test_visibility_queryset_public_detail(visibility_objs: List[VisibilityMixin]):
    def is_public_detail(obj: VisibilityMixin) -> bool:
        return obj.visibility.public_detail

    model_cls = type(visibility_objs[0])
    assert_visibility_matches(
        objs=visibility_objs,
        expected_visibility=is_public_detail,
        results=model_cls.objects.public_detail(),
    )


@pytest.mark.parametrize("is_owner", (False, True))
@pytest.mark.parametrize("is_moderator", (False, True))
@pytest.mark.parametrize("is_admin", (False, True))
def test_visibility_queryset_visible_list(
    visibility_objs: List[VisibilityMixin],
    is_owner: bool,
    is_moderator: bool,
    is_admin: bool,
):
    def is_visible(obj: VisibilityMixin) -> bool:
        return (
            obj.visibility.public_list is True
            or (obj.visibility.owner_list and is_owner)
            or (obj.visibility.moderator_list and is_moderator)
            or (obj.visibility.admin_list and is_admin)
        )

    model_cls = type(visibility_objs[0])
    assert_visibility_matches(
        objs=visibility_objs,
        expected_visibility=is_visible,
        results=model_cls.objects.visible_list(is_owner, is_moderator, is_admin),
    )


@pytest.mark.parametrize("is_owner", (False, True))
@pytest.mark.parametrize("is_moderator", (False, True))
@pytest.mark.parametrize("is_admin", (False, True))
def test_visibility_queryset_visible_detail(
    visibility_objs: List[VisibilityMixin],
    is_owner: bool,
    is_moderator: bool,
    is_admin: bool,
):
    def is_visible(obj: VisibilityMixin) -> bool:
        return (
            obj.visibility.public_detail is True
            or (obj.visibility.owner_detail and is_owner)
            or (obj.visibility.moderator_detail and is_moderator)
            or (obj.visibility.admin_detail and is_admin)
        )

    model_cls = type(visibility_objs[0])
    assert_visibility_matches(
        objs=visibility_objs,
        expected_visibility=is_visible,
        results=model_cls.objects.visible_detail(is_owner, is_moderator, is_admin),
    )
