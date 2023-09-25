import pytest
from django.core.files.base import ContentFile

from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.tasks.files import extract_package_version_file_tree
from thunderstore.storage.models import DataBlobGroup


@pytest.mark.django_db
def test_repository_tasks_extract_package_version_file_tree(
    manifest_v1_package_bytes: bytes,
):
    file = ContentFile(
        manifest_v1_package_bytes,
        name=f"package.zip",
    )
    version = PackageVersionFactory(file=file, file_size=len(manifest_v1_package_bytes))
    group_id = extract_package_version_file_tree.delay(version.pk).wait()
    group = DataBlobGroup.objects.get(pk=group_id)
    assert group.entries.count() == 3
    assert group.entries.filter(name="README.md").exists()
    assert group.entries.filter(name="manifest.json").exists()
    assert group.entries.filter(name="icon.png").exists()

    rerun_id = extract_package_version_file_tree.delay(version.pk).wait()
    assert rerun_id == group_id
