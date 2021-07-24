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
