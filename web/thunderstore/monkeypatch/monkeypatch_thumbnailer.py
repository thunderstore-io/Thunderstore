"""
easy_thumbnails.files.Thumbnailer.thumbnail_exists

def thumbnail_exists(self, thumbnail_name):
    if self.remote_source:
        return False

    if utils.is_storage_local(self.source_storage):
        source_modtime = utils.get_modified_time(
            self.source_storage, self.name)
    else:
        source = self.get_source_cache()
        if not source:
            return False
        source_modtime = source.modified

    if not source_modtime:
        return False

    local_thumbnails = utils.is_storage_local(self.thumbnail_storage)
    if local_thumbnails:
        thumbnail_modtime = utils.get_modified_time(
            self.thumbnail_storage, thumbnail_name)
        if not thumbnail_modtime:
            return False
        return source_modtime <= thumbnail_modtime

    thumbnail = self.get_thumbnail_cache(thumbnail_name)
    if not thumbnail:
        return False
    thumbnail_modtime = thumbnail.modified

    if thumbnail.modified and source_modtime <= thumbnail.modified:
        return thumbnail
    return False
"""

from easy_thumbnails import utils
from easy_thumbnails.files import Thumbnailer


def thumbnail_exists(self, thumbnail_name):
    if self.remote_source:
        return False

    if utils.is_storage_local(self.source_storage):
        source_modtime = utils.get_modified_time(self.source_storage, self.name)
    else:
        source = self.get_source_cache()
        if not source:
            return False
        source_modtime = source.modified

    if not source_modtime:
        return False

    local_thumbnails = utils.is_storage_local(self.thumbnail_storage)
    if local_thumbnails:
        thumbnail_modtime = utils.get_modified_time(
            self.thumbnail_storage, thumbnail_name
        )
        if not thumbnail_modtime:
            return False
        return source_modtime <= thumbnail_modtime

    thumbnail = self.get_thumbnail_cache(thumbnail_name)
    if not thumbnail:
        return False
    thumbnail_modtime = thumbnail.modified

    return thumbnail


Thumbnailer.thumbnail_exists = thumbnail_exists
