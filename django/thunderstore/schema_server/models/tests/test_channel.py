import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from thunderstore.core.types import UserType
from thunderstore.schema_server.models import SchemaChannel


@pytest.mark.django_db
def test_schema_server_schemachannel_identifier_readonly():
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    with pytest.raises(ValidationError, match="Field 'identifier' is read only"):
        channel.identifier = "nest"
        channel.save()


@pytest.mark.django_db
def test_schema_server_schemachannel_update_channel_authorized(user: UserType):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    channel.authorized_users.add(user)
    file = SchemaChannel.update_channel(user, channel.identifier, b"Test")
    assert file is not None


@pytest.mark.django_db
def test_schema_server_schemachannel_update_channel_unauthorized(
    user: UserType,
    admin_user: UserType,
):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    with pytest.raises(PermissionDenied):
        SchemaChannel.update_channel(None, channel.identifier, b"Test")
    with pytest.raises(PermissionDenied):
        SchemaChannel.update_channel(user, channel.identifier, b"Test")
    with pytest.raises(PermissionDenied):
        SchemaChannel.update_channel(admin_user, channel.identifier, b"Test")


@pytest.mark.django_db
@pytest.mark.parametrize("identifier", ("test", "set"))
def test_schema_server_schemachannel_str(identifier: str):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier=identifier)
    assert str(channel) == identifier


@pytest.mark.django_db
def test_schema_server_schemachannel_latest(user: UserType):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    channel.authorized_users.add(user)
    assert channel.latest is None
    file_1 = SchemaChannel.update_channel(user, channel.identifier, b"Test")
    channel.refresh_from_db()
    assert channel.latest == file_1
    file_2 = SchemaChannel.update_channel(user, channel.identifier, b"Set")
    channel.refresh_from_db()
    assert channel.latest == file_2


@pytest.mark.django_db
def test_schema_server_schemachannel_deduplication(user: UserType):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    channel.authorized_users.add(user)
    assert channel.latest is None
    file_1 = SchemaChannel.update_channel(user, channel.identifier, b"Foo")
    file_2 = SchemaChannel.update_channel(user, channel.identifier, b"Bar")
    file_3 = SchemaChannel.update_channel(user, channel.identifier, b"Foo")
    assert file_1 != file_2
    assert file_2 != file_3
    assert file_1.file != file_2.file
    assert file_1.file == file_3.file


@pytest.mark.django_db
def test_schema_server_schemachannelfile_str(user: UserType):
    channel: SchemaChannel = SchemaChannel.objects.create(identifier="test")
    channel.authorized_users.add(user)
    file = SchemaChannel.update_channel(user, channel.identifier, b"Foo")
    expected = f"{file.datetime_created.isoformat()} {file.file.checksum_sha256}"
    assert str(file) == expected
