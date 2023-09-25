import pytest

from thunderstore.storage.models.blob import DataBlob
from thunderstore.storage.models.reference import DataBlobReference


@pytest.mark.django_db
def test_storage_models_blobreference_create():
    content = b"123"
    checksum = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    reference = DataBlobReference.create(
        content,
        name="Test",
        content_type="application/json",
        content_encoding="gzip",
    )
    assert str(reference) == "Test"
    assert reference.data == content
    assert reference.data_checksum_sha256 == checksum
    assert reference.name == "Test"
    assert reference.content_type == "application/json"
    assert reference.content_encoding == "gzip"
    assert reference.data_size == len(content)
    assert f"blob-storage/sha256/{checksum}" in reference.data_url


@pytest.mark.django_db
def test_storage_models_blobreference_deduplicate():
    content = b"123"
    assert DataBlob.objects.count() == 0
    assert DataBlobReference.objects.count() == 0
    reference_1 = DataBlobReference.create(content)
    assert DataBlob.objects.count() == 1
    assert DataBlobReference.objects.count() == 1
    reference_2 = DataBlobReference.create(content)
    assert DataBlob.objects.count() == 1
    assert DataBlobReference.objects.count() == 2
    assert reference_1.blob == reference_2.blob
    assert reference_1 != reference_2


@pytest.mark.django_db
def test_storage_models_blobreference_data_setter():
    content = b"123"
    reference = DataBlobReference.create(content)
    blob1 = reference.blob
    assert DataBlob.objects.count() == 1
    assert DataBlobReference.objects.count() == 1
    reference.data = b"123"
    assert DataBlob.objects.count() == 1
    assert DataBlobReference.objects.count() == 1
    reference.data = b"234"
    assert DataBlob.objects.count() == 2
    assert DataBlobReference.objects.count() == 1
    assert reference.blob != blob1
