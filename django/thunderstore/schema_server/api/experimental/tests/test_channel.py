import pytest
from django.utils.http import http_date
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.schema_server.models import SchemaChannel
from thunderstore.utils.gzip import gzip_decompress


@pytest.mark.django_db
def test_schema_server_api_channel_post_success(
    api_client: APIClient,
    schema_channel: SchemaChannel,
    user: UserType,
):
    assert schema_channel.latest is None
    schema_channel.authorized_users.add(user)
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/experimental/schema/{schema_channel.identifier}/",
        data=b"Foo Bar",
        content_type="application/octet-stream",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    result = response.json()

    schema_channel.refresh_from_db()
    assert schema_channel.latest is not None

    assert result == {
        "channel_identifier": schema_channel.identifier,
        "checksum_sha256": schema_channel.latest.file.checksum_sha256,
    }


@pytest.mark.django_db
def test_schema_server_api_channel_post_fail_permission_denied(
    api_client: APIClient,
    schema_channel: SchemaChannel,
    user: UserType,
):
    assert schema_channel.latest is None
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/experimental/schema/{schema_channel.identifier}/",
        data=b"Foo Bar",
        content_type="application/octet-stream",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_schema_server_api_channel_post_fail_no_body(
    api_client: APIClient,
    schema_channel: SchemaChannel,
    user: UserType,
):
    schema_channel.authorized_users.add(user)
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/experimental/schema/{schema_channel.identifier}/",
        content_type="application/octet-stream",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 400
    assert b"Request body was empty" in response.content


@pytest.mark.django_db
def test_schema_server_api_channel_post_fail_empty_body(
    api_client: APIClient,
    schema_channel: SchemaChannel,
    user: UserType,
):
    schema_channel.authorized_users.add(user)
    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/experimental/schema/{schema_channel.identifier}/",
        data=b"",
        content_type="application/octet-stream",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 400
    assert b"Request body was empty" in response.content


@pytest.mark.django_db
def test_schema_server_api_channel_post_fail_not_found_channel(
    api_client: APIClient,
):
    response = api_client.post(
        f"/api/experimental/schema/foo/",
        data=b"Hello",
        content_type="application/octet-stream",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_schema_server_api_channel_latest_get_new(
    api_client: APIClient,
    schema_channel: SchemaChannel,
):
    version = schema_channel._add_new_version(b"Foo")
    last_modified = int(version.file.last_modified.timestamp())

    response = api_client.get(
        f"/api/experimental/schema/{schema_channel.identifier}/latest/"
    )
    assert response.status_code == 200
    assert response["Content-Encoding"] == "gzip"
    assert response["Last-Modified"] == http_date(last_modified)
    assert gzip_decompress(response.content) == b"Foo"


@pytest.mark.django_db
def test_schema_server_api_channel_latest_get_cached(
    api_client: APIClient,
    schema_channel: SchemaChannel,
):
    version = schema_channel._add_new_version(b"Foo")
    last_modified = int(version.file.last_modified.timestamp())

    response = api_client.get(
        f"/api/experimental/schema/{schema_channel.identifier}/latest/",
        HTTP_IF_MODIFIED_SINCE=http_date(last_modified),
    )
    assert response.status_code == 304


@pytest.mark.django_db
def test_schema_server_api_channel_latest_get_not_found_channel(
    api_client: APIClient,
):
    response = api_client.get(f"/api/experimental/schema/foo/latest/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_schema_server_api_channel_latest_get_not_found_version(
    api_client: APIClient,
    schema_channel: SchemaChannel,
):
    response = api_client.get(
        f"/api/experimental/schema/{schema_channel.identifier}/latest/"
    )
    assert response.status_code == 404
