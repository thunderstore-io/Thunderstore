import pytest
from django.conf import settings
from django.test import Client, RequestFactory

from thunderstore.schema_server.admin import SchemaChannelAdmin
from thunderstore.schema_server.models import SchemaChannel

_BASE_URL = "/djangoadmin/schema_server/schemachannel/"


@pytest.mark.django_db
def test_admin_schema_server_schemachannel_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path=f"{_BASE_URL}?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_schema_server_schemachannel_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path=f"{_BASE_URL}",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_schema_server_schemachannel_detail(
    schema_channel: SchemaChannel,
    admin_client: Client,
) -> None:
    path = f"{_BASE_URL}{schema_channel.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_schema_server_schemachannel_add(
    admin_client: Client,
) -> None:
    path = f"{_BASE_URL}add/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_schema_server_schemachannel_read_only_fields(
    rf: RequestFactory,
    schema_channel: SchemaChannel,
):
    view = SchemaChannelAdmin(SchemaChannel, None)
    fields_without_identifier = [
        x for x in SchemaChannelAdmin.readonly_fields if x != "identifier"
    ]

    assert view.get_readonly_fields(rf.get("/"), None) == fields_without_identifier
    assert (
        view.get_readonly_fields(rf.get("/"), schema_channel)
        == SchemaChannelAdmin.readonly_fields
    )
