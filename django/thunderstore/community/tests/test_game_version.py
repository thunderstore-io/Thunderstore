import pytest
from django.db import IntegrityError

from thunderstore.community.models import Community, GameVersion, ReleaseGroup


@pytest.mark.django_db
def test_release_group_unique_constraint(community):
    ReleaseGroup.objects.create(community=community, slug="1.0", display_name="1.0.x")
    with pytest.raises(IntegrityError):
        ReleaseGroup.objects.create(
            community=community, slug="1.0", display_name="Duplicate Slug"
        )


@pytest.mark.django_db
def test_release_group_str(community: Community) -> None:
    group_1 = ReleaseGroup.objects.create(
        community=community, slug="1.0", display_name="1.0.x"
    )
    assert str(group_1) == f"{community.name} -> 1.0.x"

    group_2 = ReleaseGroup.objects.create(
        community=community,
        slug="2.0",
        display_name="2.0.x",
        release_name="Test Release",
    )
    assert str(group_2) == f"{community.name} -> 2.0.x (Test Release)"


@pytest.mark.django_db
def test_game_version_unique_constraint(community):
    group = ReleaseGroup.objects.create(
        community=community, slug="1.0", display_name="1.0.x"
    )
    GameVersion.objects.create(
        community=community,
        release_group=group,
        version="1.0.0",
    )
    with pytest.raises(IntegrityError):
        GameVersion.objects.create(
            community=community,
            release_group=group,
            version="1.0.0",
        )


@pytest.mark.django_db
def test_game_version_str(community: Community) -> None:
    group = ReleaseGroup.objects.create(
        community=community, slug="1.0", display_name="1.0.x"
    )
    version_1 = GameVersion.objects.create(
        community=community,
        release_group=group,
        version="1.0.0",
        release_name="Test Release",
    )
    assert str(version_1) == f"{community.name} -> 1.0.0 (Test Release)"

    version_2 = GameVersion.objects.create(
        community=community,
        release_group=group,
        version="1.0.1",
    )
    assert str(version_2) == f"{community.name} -> 1.0.1"


@pytest.mark.django_db
def test_game_version_display_name(community: Community) -> None:
    group = ReleaseGroup.objects.create(
        community=community, slug="1.0", display_name="1.0.x"
    )
    version_1 = GameVersion.objects.create(
        community=community,
        release_group=group,
        version="1.0.0",
        release_name="Test Release",
    )
    assert version_1.display_name == "1.0.0 - Test Release"
    version_2 = GameVersion.objects.create(
        community=community,
        release_group=group,
        version="1.0.1",
    )
    assert version_2.display_name == "1.0.1"
