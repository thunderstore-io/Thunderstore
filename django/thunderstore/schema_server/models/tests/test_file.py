import time
from datetime import timedelta
from hashlib import sha256

import pytest
from django.utils import timezone

from thunderstore.schema_server.models import SchemaFile
from thunderstore.utils.gzip import gzip_compress, gzip_decompress


def _sha256_hash(data: bytes) -> str:
    hash = sha256()
    hash.update(data)
    return hash.hexdigest()


@pytest.mark.django_db
def test_schema_server_file_compression():
    test_data = b"Hello world, Hello world, Hello world"
    compressed_data = gzip_compress(test_data)
    file = SchemaFile.get_or_create(test_data)
    assert file.file_size == len(test_data)
    assert file.content_encoding == "gzip"
    assert file.gzip_size == len(compressed_data)

    file_data = file.data.read()
    assert file_data == compressed_data
    assert gzip_decompress(file_data) == test_data


@pytest.mark.django_db
def test_schema_server_file_content_type():
    file = SchemaFile.get_or_create(b"Test")
    assert file.content_type == "application/json"


@pytest.mark.django_db
def test_schema_server_file_timestamp():
    file = SchemaFile.get_or_create(b"Test")
    assert timezone.now() - file.last_modified < timedelta(seconds=0.5)

    # TODO: Use freezegun instead of sleep, currently blocked by
    #       https://github.com/spulec/freezegun/issues/331
    time.sleep(0.5)

    # Should return the same file, meaning the timestamp should be old
    file = SchemaFile.get_or_create(b"Test")
    assert timezone.now() - file.last_modified > timedelta(seconds=0.5)


@pytest.mark.django_db
def test_schema_server_file_checksum():
    test_data = b"Hello world, Hello world, Hello world"
    expected_hash = _sha256_hash(test_data)

    file = SchemaFile.get_or_create(test_data)

    # Hash should match the content before encoding
    assert file.checksum_sha256 == expected_hash
    assert expected_hash != _sha256_hash(file.data.read())


@pytest.mark.django_db
@pytest.mark.parametrize("data", (b"Test", b"Hello world"))
def test_schema_server_file_name(data: bytes):
    checksum = _sha256_hash(data)
    file = SchemaFile.get_or_create(data)

    # The file storage backend will add its own identifier before the extension
    # in case of duplicate files, so we check for parts around that
    expected_start = f"schema/sha256/{checksum}.json"
    expected_end = f".gz"

    assert file.data.name.startswith(expected_start)
    assert file.data.name.endswith(expected_end)


@pytest.mark.django_db
def test_schema_server_file_get_or_create_deduplication():
    test_data_a = b"Hello world!"
    test_data_b = b"World hello!"
    assert SchemaFile.objects.count() == 0
    file_a = SchemaFile.get_or_create(test_data_a)
    assert SchemaFile.objects.count() == 1

    # Check that calling with the same data won't create a new object
    assert SchemaFile.get_or_create(test_data_a) == file_a
    assert SchemaFile.objects.count() == 1

    # Check that calling with different data will create a new object
    file_b = SchemaFile.get_or_create(test_data_b)
    assert file_a != file_b
    assert SchemaFile.objects.count() == 2
