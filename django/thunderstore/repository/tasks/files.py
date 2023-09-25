import logging
import tempfile
from zipfile import ZipFile

from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.models import PackageVersion
from thunderstore.storage.models import DataBlobGroup

logger = logging.getLogger(__name__)


@shared_task(queue=CeleryQueues.BackgroundTask)
def extract_package_version_file_tree(
    package_version_id: str,
) -> str:
    package_version: PackageVersion = PackageVersion.objects.get(pk=package_version_id)
    if package_version.file_tree is not None and package_version.file_tree.is_complete:
        logger.warning(
            f"{package_version.full_version_name} already has a file tree, skipping"
        )
        return package_version.file_tree.pk

    logger.info(f"Extracting file tree for package {package_version.full_version_name}")
    with tempfile.TemporaryFile() as local_copy:
        for chunk in package_version.file.chunks():
            local_copy.write(chunk)
        local_copy.seek(0)

        with ZipFile(local_copy) as unzip:
            group: DataBlobGroup = DataBlobGroup.objects.create(
                name=f"File tree of package: {package_version.full_version_name}"
            )
            for entry in unzip.infolist():
                logger.info(f"Processing {entry.filename}")
                if entry.is_dir():
                    continue
                group.add_entry(
                    unzip.read(entry),
                    entry.filename,
                )
            group.set_complete()

    package_version.file_tree = group
    package_version.save(update_fields=("file_tree",))
    logger.info(
        f"File tree for package {package_version.full_version_name} finished processing"
    )
    return group.pk
