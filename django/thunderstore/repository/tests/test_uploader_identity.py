import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.factories import (
    UploaderIdentityFactory,
    UploaderIdentityMemberFactory,
)
from thunderstore.repository.models import UploaderIdentity


@pytest.mark.parametrize(
    "role, expected",
    [
        ["owner", True],
        ["member", True],
        [None, False],
    ],
)
def test_uploader_identity_can_user_upload(user, role, expected):
    identity = UploaderIdentityFactory.create()
    if role:
        UploaderIdentityMemberFactory.create(
            user=user,
            identity=identity,
            role=role,
        )
    assert identity.can_user_upload(user) == expected


@pytest.mark.parametrize(
    "author_name, should_fail",
    (
        ("SomeAuthor", False),
        ("Some-Author", False),
        ("Som3-Auth0r", False),
        ("Som3_Auth0r", False),
        ("Some.Author", False),
        ("Some@Author", True),
    ),
)
def test_uploader_identity_creation(user, author_name, should_fail):
    user.username = author_name
    if should_fail:
        with pytest.raises(ValidationError):
            UploaderIdentity.get_or_create_for_user(user)
    else:
        identity = UploaderIdentity.get_or_create_for_user(user)
        assert identity.name == author_name
