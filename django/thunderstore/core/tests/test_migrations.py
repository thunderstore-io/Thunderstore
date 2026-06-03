import pytest

from conftest import migrate_db_state
from thunderstore.repository.factories import NamespaceFactory, TeamFactory
from thunderstore.repository.models import Namespace


@pytest.mark.django_db
def test_0055_delete_namespaces_without_team(migrate_db_state):
    migrate_db_state("repository", "0054_alter_chunked_package_cache_index")

    team = TeamFactory.create()
    namespace_with_team = NamespaceFactory.create(team=team)
    namespace_without_team = NamespaceFactory.create(team=None)

    assert namespace_without_team.team is None
    assert Namespace.objects.count() == 2

    migrate_db_state("repository", "0055_delete_namespaces_without_team")

    assert Namespace.objects.count() == 1
    assert namespace_with_team in Namespace.objects.all()
    assert namespace_without_team not in Namespace.objects.all()
