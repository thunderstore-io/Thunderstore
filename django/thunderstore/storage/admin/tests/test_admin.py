import pytest
from django.conf import settings
from django.test import Client

from thunderstore.storage.models import DataBlobGroup


def _create_group():
    group: DataBlobGroup = DataBlobGroup.objects.create(name="test 1")
    entry = group.add_entry(b"123", "test 1")
    return (
        entry.blob,
        entry,
        group,
    )


@pytest.mark.django_db
def test_admin_storage_blob_search(admin_client: Client) -> None:
    _create_group()
    resp = admin_client.get(
        path="/djangoadmin/storage/datablob/?q=1",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_storage_blob_detail(admin_client: Client) -> None:
    blob, _, _ = _create_group()
    path = f"/djangoadmin/storage/datablob/{blob.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_storage_blobreference_search(admin_client: Client) -> None:
    _create_group()
    resp = admin_client.get(
        path="/djangoadmin/storage/datablobreference/?q=1",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_storage_blobreference_detail(admin_client: Client) -> None:
    _, reference, _ = _create_group()
    path = f"/djangoadmin/storage/datablobreference/{reference.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_storage_referencegroup_search(admin_client: Client) -> None:
    _create_group()
    resp = admin_client.get(
        path="/djangoadmin/storage/datablobgroup/?q=1",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_storage_referencegroup_detail(admin_client: Client) -> None:
    _, _, group = _create_group()
    path = f"/djangoadmin/storage/datablobgroup/{group.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
