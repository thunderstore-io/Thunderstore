import json
from typing import Any, Dict

import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.models import UploaderIdentityMember
from thunderstore.repository.validation.manifest import validate_manifest


@pytest.mark.django_db
def test_validate_manifest_unicode_error(
    uploader_identity_member: UploaderIdentityMember,
) -> None:
    manifest = bytes.fromhex("8081")
    with pytest.raises(
        ValidationError,
        match="Make sure the manifest.json is UTF-8 compatible",
    ):
        validate_manifest(
            user=uploader_identity_member.user,
            uploader=uploader_identity_member.identity,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_invalid_json(
    uploader_identity_member: UploaderIdentityMember,
) -> None:
    manifest = "{this is not valid json".encode("utf-8")
    with pytest.raises(
        ValidationError,
        match="Unable to parse manifest.json:",
    ):
        validate_manifest(
            user=uploader_identity_member.user,
            uploader=uploader_identity_member.identity,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_serializer_errors(
    uploader_identity_member: UploaderIdentityMember,
    manifest_v1_data: Dict[str, Any],
) -> None:
    del manifest_v1_data["name"]
    manifest = json.dumps(manifest_v1_data).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match="name: This field is required.",
    ):
        validate_manifest(
            user=uploader_identity_member.user,
            uploader=uploader_identity_member.identity,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_pass(
    uploader_identity_member: UploaderIdentityMember,
    manifest_v1_data: Dict[str, Any],
) -> None:
    manifest = json.dumps(manifest_v1_data).encode("utf-8")
    assert isinstance(
        validate_manifest(
            user=uploader_identity_member.user,
            uploader=uploader_identity_member.identity,
            manifest_data=manifest,
        ),
        dict,
    )
