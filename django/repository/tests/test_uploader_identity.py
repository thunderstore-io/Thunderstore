import pytest

from repository.factories import UploaderIdentityFactory, UploaderIdentityMemberFactory


@pytest.mark.parametrize(
    "role, expected",
    [
        ["owner", True],
        ["member", True],
        [None, False],
    ]
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
