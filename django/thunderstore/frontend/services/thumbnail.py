from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from easy_thumbnails.files import get_thumbnailer


@dataclass
class Thumbnail:
    storage_path: Optional[str] = None
    url: Optional[str] = None


def get_or_create_thumbnail(
    asset_path: str, width: int, height: int
) -> Optional[Thumbnail]:
    try:
        thumbnailer = get_thumbnailer(asset_path)

        thumbnail_options = {
            "size": (width, height),
            "crop": True,
            "quality": settings.THUMBNAIL_QUALITY,
        }

        thumbnail_name = thumbnailer.get_thumbnail_name(thumbnail_options)
        if thumbnailer.source_storage.exists(thumbnail_name):
            url = thumbnailer.source_storage.url(thumbnail_name)
            return Thumbnail(storage_path=thumbnail_name, url=url)
        else:
            thumbnail = thumbnailer.get_thumbnail(thumbnail_options, generate=True)
            return Thumbnail(storage_path=thumbnail.name, url=thumbnail.url)
    except Exception:
        return None
