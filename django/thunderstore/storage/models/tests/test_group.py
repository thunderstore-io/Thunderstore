import pytest

from thunderstore.storage.models import DataBlob, DataBlobGroup, DataBlobReference


@pytest.mark.django_db
def test_storage_models_blobgroup():
    content = b"123"
    group: DataBlobGroup = DataBlobGroup.objects.create(name="Test group")

    assert group.name == "Test group"
    assert str(group) == "Test group"
    assert DataBlobReference.objects.count() == 0
    entry = group.add_entry(
        content, "test", content_type="application/json", content_encoding="gzip"
    )
    assert group.entries.count() == 1
    assert DataBlobReference.objects.count() == 1
    assert group.entries.first() == entry

    assert entry.content_type == "application/json"
    assert entry.content_encoding == "gzip"
    assert entry.data == content
    entry2 = group.add_entry(
        content, "test", content_type="application/json", content_encoding="gzip"
    )
    assert DataBlobReference.objects.count() == 2
    assert group.entries.count() == 2
    assert entry != entry2
    assert DataBlob.objects.count() == 1


@pytest.mark.django_db
def test_storage_models_blobgroup_is_completed():
    group: DataBlobGroup = DataBlobGroup.objects.create(name="Test group")
    assert group.is_complete is False
    assert group.add_entry(b"123", "test") is not None
    group.set_complete()
    assert group.is_complete is True
    with pytest.raises(
        RuntimeError, match="Modifying complete groups is not permitted"
    ):
        group.add_entry(b"123", "test")
