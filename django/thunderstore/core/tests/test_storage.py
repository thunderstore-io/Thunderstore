import os
import re
from typing import List
from unittest.mock import patch

import pytest
from django.core.files.storage import default_storage
from django.test import override_settings
from PIL import Image  # type: ignore

from thunderstore.core.storage import get_storage_class_or_stub
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models.package_version import get_version_png_filepath


def check_files_exist(list_of_files: List[str], original_file_name: str) -> dict:
    file_root, file_ext = original_file_name.rsplit(".", 1)
    pattern = re.compile(
        rf"{re.escape(file_root)}_[a-zA-Z0-9]{{7}}\.{re.escape(file_ext)}"
    )

    if len(list_of_files) > 0:
        original_count = len([x for x in list_of_files if x == original_file_name])
        duplicate_count = len([x for x in list_of_files if pattern.match(x)])
    else:
        original_count = 0
        duplicate_count = 0

    return {
        "original_exists": original_count > 0,
        "duplicate_exists": duplicate_count > 0,
        "original_count": original_count,
        "duplicate_count": duplicate_count,
    }


def test_get_storage_class_or_stub(mocker) -> None:
    assert get_storage_class_or_stub("non.stub.class") == "non.stub.class"
    mocker.patch("sys.argv", ["manage.py", "migrate"])
    assert (
        get_storage_class_or_stub("non.stub.class")
        == "thunderstore.utils.makemigrations.StubStorage"
    )


@override_settings(
    DEFAULT_FILE_STORAGE="thunderstore.core.storage.MirroredS3Storage",
    S3_MIRRORS=(
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
)
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


@override_settings(
    DEFAULT_FILE_STORAGE="thunderstore.core.storage.MirroredS3Storage",
    S3_MIRRORS=(
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
)
@pytest.mark.django_db
def test_mirrored_storage_duplicate_file_name(dummy_image: Image) -> None:
    pv = PackageVersionFactory(icon=None, name="MirrorStorageTest")
    pv.icon = dummy_image
    pv.save()
    icon_path = get_version_png_filepath(pv, "")
    original_file_name = os.path.basename(icon_path)

    files_in_default_storage = default_storage.listdir("repository/icons")[1]
    files_in_mirror_storage = [
        mirror_storage.listdir("repository/icons")[1]
        for mirror_storage in default_storage.mirrors
    ][
        0
    ]  # Assume only one mirror in test setup

    default_storage_results = check_files_exist(
        files_in_default_storage, original_file_name
    )
    assert default_storage_results["original_exists"]
    assert not default_storage_results["duplicate_exists"]
    assert default_storage_results["original_count"] == 1
    assert default_storage_results["duplicate_count"] == 0

    mirror_storage_results = check_files_exist(
        files_in_mirror_storage, original_file_name
    )
    assert mirror_storage_results["original_exists"]
    assert not mirror_storage_results["duplicate_exists"]
    assert mirror_storage_results["original_count"] == 1
    assert mirror_storage_results["duplicate_count"] == 0

    # Create a duplicate
    pv.icon = dummy_image
    pv.save()

    updated_files_in_default_storage = default_storage.listdir("repository/icons")[1]
    updated_files_in_mirror_storage = [
        mirror_storage.listdir("repository/icons")[1]
        for mirror_storage in default_storage.mirrors
    ][0]

    default_storage_results = check_files_exist(
        updated_files_in_default_storage, original_file_name
    )
    assert default_storage_results["original_exists"]
    assert default_storage_results["duplicate_exists"]
    assert default_storage_results["original_count"] == 1
    assert default_storage_results["duplicate_count"] == 1

    mirror_storage_results = check_files_exist(
        updated_files_in_mirror_storage, original_file_name
    )
    assert mirror_storage_results["original_exists"]
    assert mirror_storage_results["duplicate_exists"]
    assert mirror_storage_results["original_count"] == 1
    assert mirror_storage_results["duplicate_count"] == 1

    # Cleanup duplicate file from default_storage and mirrors
    pv.icon.delete()

    # Cleanup the original file
    default_storage.delete(icon_path)
    for mirror_storage in default_storage.mirrors:
        mirror_storage.delete(icon_path)


@override_settings(
    DEFAULT_FILE_STORAGE="thunderstore.core.storage.MirroredS3Storage",
    S3_MIRRORS=(
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
)
@pytest.mark.django_db
@patch("thunderstore.cache.utils.get_cache")
def test_mirrored_storage_cache_lock(mock_get_cache, dummy_image: Image) -> None:
    mock_cache = mock_get_cache.return_value
    mock_lock = mock_cache.lock.return_value
    mock_lock.acquire.return_value = True

    pv = PackageVersionFactory(icon=None, name="MirrorStorageTest")
    icon_path = get_version_png_filepath(pv, "")

    pv.icon = dummy_image
    pv.save()

    key = f"mirror_storage_cache_{icon_path}"
    mock_cache.lock.assert_called_once_with(key, timeout=30, blocking_timeout=None)

    pv.icon.delete()
