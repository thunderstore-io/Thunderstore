import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

from thunderstore.repository.factories import NamespaceFactory, TeamFactory
from thunderstore.repository.models import Namespace


@pytest.fixture
def migrate_db_state():
    def _run_migration(app_name: str, migration: str):
        executor = MigrationExecutor(connection)
        executor.migrate([(app_name, migration)])
        executor.loader.build_graph()

        assert MigrationRecorder.Migration.objects.filter(
            app=app_name, name=migration
        ).exists()

    return _run_migration


@pytest.mark.django_db
def test_0055_delete_namespaces_without_team(migrate_db_state):
    team = TeamFactory.create()
    namespace_with_team = NamespaceFactory.create(team=team)
    namespace_without_team = NamespaceFactory.create(team=None)

    assert namespace_without_team.team is None
    assert Namespace.objects.count() == 2

    migrate_db_state("repository", "0054_alter_chunked_package_cache_index")
    migrate_db_state("repository", "0055_delete_namespaces_without_team")

    assert Namespace.objects.count() == 1
    assert namespace_with_team in Namespace.objects.all()
    assert namespace_without_team not in Namespace.objects.all()
