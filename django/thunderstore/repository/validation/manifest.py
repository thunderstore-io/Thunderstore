import json

from django.core.exceptions import ValidationError

from thunderstore.core.types import UserType
from thunderstore.repository.models import Team
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.repository.package_manifest import ManifestV1Serializer
from thunderstore.repository.utils import unpack_serializer_errors


def validate_manifest(
    format_spec: PackageFormats, user: UserType, team: Team, manifest_data: bytes
):
    if format_spec not in PackageFormats.get_supported_formats():
        raise ValidationError(f"Unsupported package format: {format_spec}")

    try:
        manifest_json = json.loads(manifest_data)
    except UnicodeDecodeError as exc:
        raise ValidationError(
            [
                f"Unable to parse manifest.json: {exc}\n",
                "Make sure the manifest.json is UTF-8 compatible",
            ],
        )
    except json.decoder.JSONDecodeError as exc:
        raise ValidationError(f"Unable to parse manifest.json: {exc}")

    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_json,
    )
    if serializer.is_valid():
        return serializer.validated_data
    else:
        errors = unpack_serializer_errors("manifest.json", serializer.errors)
        errors = ValidationError([f"{key}: {value}" for key, value in errors.items()])
        raise errors
