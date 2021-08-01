import uuid
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

import pytest
from django.utils import timezone

from thunderstore.core import settings
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.usermedia.consts import MAX_UPLOAD_SIZE, MIN_UPLOAD_SIZE
from thunderstore.usermedia.exceptions import (
    UploadTooLargeException,
    UploadTooSmallException,
)
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.models.usermedia import UserMediaStatus


@pytest.mark.django_db
def test_usermedia_create_upload_too_large(user: UserType):
    with pytest.raises(UploadTooLargeException):
        UserMedia.create_upload(
            user=user,
            filename="testupload",
            size=MAX_UPLOAD_SIZE + 1,
            expiry=None,
        )


@pytest.mark.django_db
def test_usermedia_create_upload_too_small(user: UserType):
    with pytest.raises(UploadTooSmallException):
        UserMedia.create_upload(
            user=user,
            filename="testupload",
            size=MIN_UPLOAD_SIZE - 1,
            expiry=None,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("populate_user", (False, True))
@pytest.mark.parametrize("populate_expiry", (False, True))
def test_usermedia_create_upload(populate_user: bool, populate_expiry: bool):
    owner = UserFactory() if populate_user else None
    expiry = timezone.now() if populate_expiry else None
    usermedia = UserMedia.create_upload(
        user=owner,
        filename="testupload",
        size=MIN_UPLOAD_SIZE,
        expiry=expiry,
    )
    assert usermedia.pk
    assert usermedia.owner == owner
    assert usermedia.expiry == expiry
    assert usermedia.size == MIN_UPLOAD_SIZE
    assert usermedia.status == UserMediaStatus.initial
    assert usermedia.prefix == settings.USERMEDIA_S3_LOCATION
    assert usermedia.key
    assert usermedia.uuid


@pytest.mark.parametrize(
    ["prefix", "uuid", "filename", "expected"],
    [
        (None, uuid.uuid4(), "testfile", "usermedia/{uuid}-testfile"),
        ("", uuid.uuid4(), "testfile", "usermedia/{uuid}-testfile"),
        ("testdir", uuid.uuid4(), "testfile", "testdir/usermedia/{uuid}-testfile"),
        (
            "testdir",
            uuid.uuid4(),
            "another/file",
            "testdir/usermedia/{uuid}-anotherfile",
        ),
        (
            "testdir",
            uuid.uuid4(),
            "another/file.zip",
            "testdir/usermedia/{uuid}-anotherfile.zip",
        ),
        ("test/dir", uuid.uuid4(), "testfile", "test/dir/usermedia/{uuid}-testfile"),
        ("test/dir/", uuid.uuid4(), "testfile", "test/dir/usermedia/{uuid}-testfile"),
        (
            "test/dir////",
            uuid.uuid4(),
            "testfile",
            "test/dir/usermedia/{uuid}-testfile",
        ),
        (
            "test///dir////",
            uuid.uuid4(),
            "testfile",
            "test/dir/usermedia/{uuid}-testfile",
        ),
        (
            "test/././dir//.//",
            uuid.uuid4(),
            "testfile",
            "test/dir/usermedia/{uuid}-testfile",
        ),
        (
            "test.../.././/dir///",
            uuid.uuid4(),
            "testfile",
            "test.../dir/usermedia/{uuid}-testfile",
        ),
        (
            "test.../.././/dir///",
            uuid.uuid4(),
            "testfile😁😁",
            "test.../dir/usermedia/{uuid}-testfile",
        ),
        (
            "test.../.././/dir///",
            uuid.uuid4(),
            'testfile!"¤)=(',
            "test.../dir/usermedia/{uuid}-testfile",
        ),
    ],
)
def test_usermedia_compute_key(
    prefix: Optional[str], uuid: UUID, filename: str, expected: str
):
    usermedia = UserMedia(
        owner=None,
        filename=filename,
        size=MIN_UPLOAD_SIZE,
        prefix=prefix,
        uuid=uuid,
        expiry=None,
    )
    key = usermedia.compute_key()
    formatted_expected = expected.format(uuid=str(uuid))
    assert key == formatted_expected


@pytest.mark.django_db
@pytest.mark.parametrize("has_expiry", (False, True))
def test_usermedia_s3_metadata(has_expiry: bool, settings: Any):

    settings.USERMEDIA_S3_OBJECT_PARAMETERS = {}
    expiry = timezone.now() if has_expiry else None
    usermedia = UserMedia.create_upload(None, "testfile", MIN_UPLOAD_SIZE, expiry)
    metadata = usermedia.s3_metadata

    assert len(metadata) == 2 if has_expiry else 1
    assert metadata["UserMedia"] == str(usermedia.uuid)
    if has_expiry:
        assert metadata["Expiry"] == expiry.isoformat()

    settings.USERMEDIA_S3_OBJECT_PARAMETERS = {"TestParam": "testValue"}

    metadata = usermedia.s3_metadata
    assert len(metadata) == 3 if has_expiry else 2
    assert metadata["UserMedia"] == str(usermedia.uuid)
    assert metadata["TestParam"] == "testValue"
    if has_expiry:
        assert metadata["Expiry"] == expiry.isoformat() if expiry else None


def test_usermedia_has_expired():
    usermedia = UserMedia(
        owner=None,
        filename="test",
        size=MIN_UPLOAD_SIZE,
        prefix="test",
        uuid=uuid,
    )

    usermedia.expiry = None
    assert usermedia.has_expired is False

    usermedia.expiry = timezone.now()
    assert usermedia.has_expired is True

    usermedia.expiry = timezone.now() + timedelta(minutes=1)
    assert usermedia.has_expired is False


@pytest.mark.django_db
def test_usermedia_can_user_write():
    usermedia = UserMedia(
        filename="test",
        size=MIN_UPLOAD_SIZE,
        prefix="test",
        uuid=uuid,
    )

    user1 = UserFactory(is_superuser=True, is_staff=True)
    user2 = UserFactory()

    usermedia.owner = None
    assert usermedia.can_user_write(None) is True
    assert usermedia.can_user_write(user1) is False
    assert usermedia.can_user_write(user2) is False

    usermedia.owner = user1
    assert usermedia.can_user_write(None) is False
    assert usermedia.can_user_write(user1) is True
    assert usermedia.can_user_write(user2) is False

    usermedia.owner = user2
    assert usermedia.can_user_write(None) is False
    assert usermedia.can_user_write(user1) is False
    assert usermedia.can_user_write(user2) is True


@pytest.mark.django_db
def test_usermedia_queryset_active():
    expired = [
        UserMedia.create_upload(None, "a", MIN_UPLOAD_SIZE, timezone.now()),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(seconds=1)
        ),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(days=400)
        ),
    ]
    active = [
        UserMedia.create_upload(None, "a", MIN_UPLOAD_SIZE, None),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(minutes=1)
        ),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(days=400)
        ),
    ]
    active_qs = UserMedia.objects.active()
    assert active_qs.count() == len(active)
    for entry in active:
        assert entry in active_qs
    for entry in expired:
        assert entry not in active_qs


@pytest.mark.django_db
def test_usermedia_queryset_expired():
    expired = [
        UserMedia.create_upload(None, "a", MIN_UPLOAD_SIZE, timezone.now()),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(seconds=1)
        ),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(days=400)
        ),
    ]
    active = [
        UserMedia.create_upload(None, "a", MIN_UPLOAD_SIZE, None),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(minutes=1)
        ),
        UserMedia.create_upload(
            None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(days=400)
        ),
    ]
    expired_qs = UserMedia.objects.expired()
    assert expired_qs.count() == len(expired)
    for entry in active:
        assert entry not in expired_qs
    for entry in expired:
        assert entry in expired_qs
