import pytest

from thunderstore.core.management.commands.content.base import ContentPopulatorContext
from thunderstore.core.management.commands.content.package import (
    PackagePopulator,
    desired_pinned,
)
from thunderstore.repository.models import Package, Team


@pytest.mark.django_db
def test_package_populator_applies_pinned_status_to_existing_packages() -> None:
    team = Team.create(name="Test_Team_1")
    package = Package.objects.create(
        owner=team,
        name="Test_Package_0",
        namespace=team.get_namespace(),
    )
    expected = desired_pinned(package)
    package.is_pinned = not expected
    package.save(update_fields=("is_pinned",))

    context = ContentPopulatorContext(teams=[team], package_count=2)
    populator = PackagePopulator()
    populator.populate(context)
    populator.update_context(context)

    created = Package.objects.get(owner=team, name="Test_Package_1")
    assert {item.pk for item in context.packages} == {package.pk, created.pk}

    populator.populate(context)
    populator.update_context(context)

    package.refresh_from_db()
    created.refresh_from_db()
    assert package.is_pinned is expected
    assert created.is_pinned is desired_pinned(created)
    assert {item.pk for item in context.packages} == {package.pk, created.pk}
