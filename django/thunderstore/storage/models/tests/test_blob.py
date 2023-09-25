import pytest

from thunderstore.storage.models.blob import DataBlob


@pytest.mark.django_db
def test_storage_models_blob_create():
    content = b"123"
    checksum = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    blob = DataBlob.get_or_create(content)
    assert blob.data.read() == b"123"
    assert blob.checksum_sha256 == checksum
    assert blob.data_size == len(content)


@pytest.mark.django_db
def test_storage_models_blob_deduplicate():
    content = b"123"
    assert DataBlob.objects.count() == 0
    blob = DataBlob.get_or_create(content)
    assert blob.data.read() == b"123"
    assert DataBlob.objects.count() == 1
    blob2 = DataBlob.get_or_create(content)
    assert DataBlob.objects.count() == 1
    assert blob == blob2


@pytest.mark.django_db
def test_storage_models_blob_data_url():
    content = b"123"
    checksum = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    blob = DataBlob.get_or_create(content)
    assert f"blob-storage/sha256/{checksum}" in blob.data_url


@pytest.mark.django_db
def test_storage_models_blob_delete_fails_in_transaction():
    blob = DataBlob.get_or_create(b"123")
    with pytest.raises(RuntimeError, match="Must not be called during a transaction"):
        blob.delete()


@pytest.mark.django_db(transaction=True)
def test_storage_models_blob_delete_succeeds_without_transaction():
    blob = DataBlob.get_or_create(b"123")
    blob.delete()
    assert DataBlob.objects.filter(pk=blob.pk).exists() is False
