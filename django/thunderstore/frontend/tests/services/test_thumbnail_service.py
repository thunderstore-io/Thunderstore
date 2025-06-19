from unittest.mock import patch

import pytest
from django.conf import settings

from thunderstore.frontend.services.thumbnail import get_or_create_thumbnail


@pytest.mark.django_db
def test_get_or_create_thumbnail_success(community, dummy_cover_image):
    community.cover_image = dummy_cover_image
    community.save()

    asset_path = community.cover_image.name
    width, height = 100, 100
    thumbnail_url = get_or_create_thumbnail(asset_path, width, height)

    assert thumbnail_url is not None
    assert f"q{settings.THUMBNAIL_QUALITY}_crop" in thumbnail_url
    assert thumbnail_url.endswith(".jpg")


@pytest.mark.django_db
def test_get_or_create_thumbnail_exception(community, dummy_cover_image):
    community.cover_image = dummy_cover_image
    community.save()

    asset_path = community.cover_image.name
    width, height = 100, 100

    path = "thunderstore.frontend.services.thumbnail.get_thumbnailer"
    with patch(path, side_effect=Exception("Test Exception")):
        thumbnail_url = get_or_create_thumbnail(asset_path, width, height)

    assert thumbnail_url is None


@pytest.mark.django_db
@pytest.mark.parametrize("thumbnail_exists", (False, True))
def test_get_or_create_thumbnail_behavior(
    community, dummy_cover_image, thumbnail_exists
):
    community.cover_image = dummy_cover_image
    community.save()

    asset_path = community.cover_image.name
    width, height = 100, 100

    options = {
        "size": (width, height),
        "crop": True,
        "quality": settings.THUMBNAIL_QUALITY,
    }

    # Create the thumbnail if it should exist
    if thumbnail_exists:
        get_or_create_thumbnail(asset_path, width, height)

    path = "easy_thumbnails.files.Thumbnailer.get_thumbnail"
    with patch(path) as mock_get_thumbnailer:
        get_or_create_thumbnail(asset_path, width, height)
        if thumbnail_exists:
            mock_get_thumbnailer.assert_not_called()
        else:
            mock_get_thumbnailer.assert_called_once_with(options, generate=True)
