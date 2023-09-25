import logging
from typing import IO, Any
from zipfile import ZipFile

from thunderstore.storage.models import DataBlobGroup

logger = logging.getLogger(__name__)


def create_file_tree_from_zip_data(
    name: str,
    zip_data: IO[Any],
) -> DataBlobGroup:
    with ZipFile(zip_data) as unzip:
        group: DataBlobGroup = DataBlobGroup.objects.create(name=name)
        for entry in unzip.infolist():
            logger.info(f"Processing {entry.filename}")
            if entry.is_dir():
                continue
            group.add_entry(unzip.read(entry), entry.filename)
        group.set_complete()
    return group
