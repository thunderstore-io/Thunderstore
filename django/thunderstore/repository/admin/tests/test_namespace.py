import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.models import Namespace


@pytest.mark.django_db
def test_admin_namespace_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/namespace/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_namespace_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/namespace/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_namespace_detail(
    namespace: Namespace,
    admin_client: Client,
) -> None:
    path = f"/djangoadmin/repository/namespace/{namespace.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
