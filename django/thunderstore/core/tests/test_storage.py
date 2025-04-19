from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.test import override_settings
from PIL import Image  # type: ignore

from thunderstore.core.storage import get_storage_class_or_stub
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models.package_version import get_version_png_filepath

mirrored_storage_settings = {
    "DEFAULT_FILE_STORAGE": "thunderstore.core.storage.MirroredS3Storage",
    "S3_MIRRORS": (
        {
            "access_key": "thunderstore",
            "secret_key": "thunderstore",
            "region_name": "",
            "bucket_name": "test",
            "location": "test",
            "custom_domain": "localhost:9000/thunderstore",
            "endpoint_url": "http://minio:9000/",
            "secure_urls": False,
            "file_overwrite": True,
            "default_acl": "",
            "object_parameters": {},
        },
    ),
}


def test_get_storage_class_or_stub(mocker) -> None:
    assert get_storage_class_or_stub("non.stub.class") == "non.stub.class"
    mocker.patch("sys.argv", ["manage.py", "migrate"])
    assert (
        get_storage_class_or_stub("non.stub.class")
        == "thunderstore.utils.makemigrations.StubStorage"
    )


@override_settings(**mirrored_storage_settings)
@pytest.mark.django_db
def test_mirrored_storage(dummy_image: Image) -> None:
    pv = PackageVersionFactory(icon=None, name="MirrorStorageTest")
    icon_path = get_version_png_filepath(pv, "")

    assert hasattr(default_storage, "mirrors")
    assert not default_storage.exists(icon_path)
    for mirror_storage in default_storage.mirrors:
        assert not mirror_storage.exists(icon_path)

    pv.icon = dummy_image
    pv.save()
    assert default_storage.exists(icon_path)
    for mirror_storage in default_storage.mirrors:
        assert mirror_storage.exists(icon_path)

    pv.icon.delete()
    assert not default_storage.exists(icon_path)
    for mirror_storage in default_storage.mirrors:
        assert not mirror_storage.exists(icon_path)


def setup_package_version(dummy_image):
    pv = PackageVersionFactory(icon=None, name="MirrorStorageTest")
    icon_path = get_version_png_filepath(pv, "")
    pv.icon = dummy_image
    return pv, icon_path


@override_settings(**mirrored_storage_settings)
@pytest.mark.django_db
def test_mirrored_storage_save_lock_failure(dummy_image: Image) -> None:
    """Test that save operation raises an exception if another save is in progress."""

    message = "Another save operation is in progress for this file."
    pv, icon_path = setup_package_version(dummy_image)
    pv.icon = dummy_image
    cache.add(f"cache_mirror_storage_{icon_path}", "LOCKED", timeout=5)

    with pytest.raises(Exception, match=message):
        pv.save()

    assert cache.get(f"cache_mirror_storage_{icon_path}") == "LOCKED"


@override_settings(**mirrored_storage_settings)
@pytest.mark.django_db
@patch("thunderstore.core.storage.TemporarySpooledCopy")
@patch("django.core.cache.cache.add")
@patch("django.core.cache.cache.delete")
def test_mirrored_storage_save_cleanup_on_exception(
    mock_cache_delete, mock_cache_add, mock_temporary_spooled_copy, dummy_image: Image
) -> None:
    """Test that the lock is released even if an exception occurs during save."""

    message = "Error"
    mock_temporary_spooled_copy.side_effect = Exception(message)
    mock_cache_add.return_value = True
    pv, icon_path = setup_package_version(dummy_image)

    with pytest.raises(Exception, match=message):
        pv.save()

    mock_cache_delete.assert_called_once_with(f"cache_mirror_storage_{icon_path}")
    assert cache.get(f"cache_mirror_storage_{icon_path}") is None
