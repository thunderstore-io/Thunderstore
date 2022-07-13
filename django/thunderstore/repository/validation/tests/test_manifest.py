import json
from typing import Any, Dict, Union

import pytest
from django.core.exceptions import ValidationError

from thunderstore.repository.models import TeamMember
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.repository.validation.manifest import validate_manifest


@pytest.mark.django_db
def test_validate_manifest_unicode_error(
    team_member: TeamMember,
) -> None:
    manifest = bytes.fromhex("8081")
    with pytest.raises(
        ValidationError,
        match="Make sure the manifest.json is UTF-8 compatible",
    ):
        validate_manifest(
            format_spec=PackageFormats.v0_1,
            user=team_member.user,
            team=team_member.team,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_invalid_json(
    team_member: TeamMember,
) -> None:
    manifest = "{this is not valid json".encode("utf-8")
    with pytest.raises(
        ValidationError,
        match="Unable to parse manifest.json:",
    ):
        validate_manifest(
            format_spec=PackageFormats.v0_1,
            user=team_member.user,
            team=team_member.team,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_serializer_errors(
    team_member: TeamMember,
    manifest_v1_data: Dict[str, Any],
) -> None:
    del manifest_v1_data["name"]
    manifest = json.dumps(manifest_v1_data).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match="name: This field is required.",
    ):
        validate_manifest(
            format_spec=PackageFormats.v0_1,
            user=team_member.user,
            team=team_member.team,
            manifest_data=manifest,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("fieldname", ("description", "website_url"))
@pytest.mark.parametrize("testdata", (42, 42.432, False, True))
def test_validate_manifest_number_in_charfield_fails(
    team_member: TeamMember,
    manifest_v1_data: Dict[str, Any],
    fieldname: str,
    testdata: Union[int, float, bool],
) -> None:
    manifest_v1_data[fieldname] = testdata
    manifest = json.dumps(manifest_v1_data).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match=f"{fieldname}: Not a valid string.",
    ):
        validate_manifest(
            format_spec=PackageFormats.v0_1,
            user=team_member.user,
            team=team_member.team,
            manifest_data=manifest,
        )


@pytest.mark.django_db
def test_validate_manifest_pass(
    team_member: TeamMember,
    manifest_v1_data: Dict[str, Any],
) -> None:
    manifest = json.dumps(manifest_v1_data).encode("utf-8")
    assert isinstance(
        validate_manifest(
            format_spec=PackageFormats.v0_1,
            user=team_member.user,
            team=team_member.team,
            manifest_data=manifest,
        ),
        dict,
    )


@pytest.mark.parametrize("format_spec", PackageFormats.values)
def test_validate_manifest_fail_for_unsupported_formats(
    format_spec: PackageFormats,
) -> None:
    if format_spec == PackageFormats.v0_1:
        return  # Skip the currently active format as it should work
    with pytest.raises(ValidationError, match="Unsupported package format"):
        validate_manifest(
            format_spec=format_spec,
            user=None,  # type: ignore
            team=None,  # type: ignore
            manifest_data=b"",
        )
