import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings
from PIL import Image  # type: ignore

from thunderstore.core.storage import MirroredS3Storage, get_storage_class_or_stub
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models.package_version import get_version_png_filepath

MIRROR_CONFIG = {
    "access_key": "thunderstore",
    "secret_key": "thunderstore",
    "region_name": "",
    "bucket_name": "test",
    "location": "test",
    "custom_domain": "localhost:9000/thunderstore",
    "endpoint_url": "http://minio:9000/",
    "url_protocol": "http:",
    "file_overwrite": True,
    "default_acl": "",
    "object_parameters": {},
}

SECOND_MIRROR_CONFIG = {**MIRROR_CONFIG, "location": "test-second-mirror"}


def test_get_storage_class_or_stub(mocker) -> None:
    assert get_storage_class_or_stub("non.stub.class") == "non.stub.class"
    mocker.patch("sys.argv", ["manage.py", "migrate"])
    assert (
        get_storage_class_or_stub("non.stub.class")
        == "thunderstore.utils.makemigrations.StubStorage"
    )


@override_settings(
    DEFAULT_FILE_STORAGE="thunderstore.core.storage.MirroredS3Storage",
    S3_MIRRORS=(MIRROR_CONFIG,),
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
    S3_MIRRORS=({**MIRROR_CONFIG, "file_overwrite": False},),
)
@pytest.mark.django_db
def test_mirrored_storage_with_conflict(dummy_image: Image) -> None:
    pv = PackageVersionFactory(icon=None, name="MirrorStorageTest")
    icon_path = get_version_png_filepath(pv, "")

    default_storage.save(icon_path, ContentFile(b"collision"))
    try:
        pv.icon = dummy_image
        pv.save()

        stored_name = pv.icon.name
        assert (
            stored_name != icon_path
        ), "expected the main storage to rename the saved file"
        assert default_storage.exists(stored_name)
        for mirror_storage in default_storage.mirrors:
            assert mirror_storage.exists(stored_name)
    finally:
        default_storage.delete(icon_path)
        pv.icon.delete()
