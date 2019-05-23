import json
import re

from django.core.exceptions import ValidationError

from repository.models import PackageVersion, Package


NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\_]+$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class Manifest:
    def __init__(self, data_dict):
        self.data_dict = data_dict

    @property
    def name(self):
        return self.data_dict.get("name", None)

    @property
    def version_number(self):
        return self.data_dict.get("version_number", None)


def validate_field_name(name):
    """
    Validate a package name, and return any errors that are found.

    :param name: The name which to validate
    :type name: str
    :return: List of found validation errors
    :rtype: list of ValidationError
    """
    if name is None:
        return [ValidationError("The manifest field 'name' is missing")]

    errors = []

    max_length = PackageVersion._meta.get_field("version_number").max_length
    if len(name) > max_length:
        errors.append(ValidationError("The manifest field 'name' is too long"))

    if not re.match(NAME_PATTERN, name):
        errors.append(
            ValidationError("Package names can only contain a-Z A-Z 0-9 _ characers")
        )

    return errors


def validate_field_version_number(manifest):
    """
    Validate the version number field of the supplied manifest object, and
    return any errors that are found.

    :param manifest: The manifest which to validate
    :type manifest: Manifest
    :return: List of found validation errors
    :rtype: list of ValidationError
    """
    if manifest.version_number is None:
        return [ValidationError("The manifest field 'version_number' is missing")]

    errors = []

    max_length = PackageVersion._meta.get_field("version_number").max_length
    if len(manifest.version_number) > max_length:
        errors.append(
            ValidationError(f"The manifest field 'version_number' is too long")
        )

    if not re.match(VERSION_PATTERN, manifest.version_number):
        errors.append(
            ValidationError(
                "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"
            )
        )


def validate_field_website_url(manifest):
    if "website_url" not in manifest:
        raise ValidationError(
            "manifest.json must contain a website_url (Leave empty string if none)"
        )
    max_length = PackageVersion._meta.get_field("website_url").max_length
    if len(manifest.get("website_url", "")) > max_length:
        raise ValidationError(f"Package website url is too long, max: {max_length}")


def validate_field_description(manifest):
    if "description" not in manifest:
        raise ValidationError("manifest.json must contain a description")
    max_length = PackageVersion._meta.get_field("description").max_length
    if len(manifest.get("description", "")) > max_length:
        raise ValidationError(f"Package description is too long, max: {max_length}")


def validate_generic(uploader, manifest):
    """
    Perform generic validation checks on the manifest, and return any errors
    that are found.

    :param uploader: The user who uploaded the manifest
    :type uploader: django.contrib.auth.models.User
    :param manifest: The manifest which to validate
    :type manifest: Manifest
    :return: List of found validation errors
    :rtype: list of ValidationError
    """
    errors = []

    same_version_exists = Package.objects.filter(
        owner=uploader,
        name=manifest["name"],
        versions__version_number=manifest.version_number,
    ).exists()
    if same_version_exists:
        errors.append(
            ValidationError("Package of the same name and version already exists")
        )

    return errors


def validate_dependencies(manifest):
    if "dependencies" not in manifest:
        raise ValidationError("manifest.json must contain a dependencies field")

    dependency_strings = manifest["dependencies"]

    if type(dependency_strings) is not list:
        raise ValidationError("The dependencies manifest.json field should be a list")
    if len(dependency_strings) > 100:
        raise ValidationError(
            "Currently only a maximum of 100 dependencies are supported"
        )

    dependencies = []
    for dependency_string in dependency_strings:
        dependency = resolve_dependency(dependency_string)
        dependencies.append(dependency)

    for dependency_a in dependencies:
        for dependency_b in dependencies:
            if dependency_a == dependency_b:
                continue
            if dependency_a.package == dependency_b.package:
                raise ValidationError(
                    "Cannot depend on multiple versions of the same package"
                )


def resolve_dependency(self, dependency_string):
    dependency_parts = dependency_string.split("-")
    if len(dependency_parts) != 3:
        raise ValidationError(f"Dependency {dependency_string} is in invalid format")

    owner_name = dependency_parts[0]
    package_name = dependency_parts[1]
    package_version = dependency_parts[2]

    dependency = PackageVersion.objects.filter(
        package__owner__name=owner_name,
        package__name=package_name,
        version_number=package_version,
    ).first()

    if not dependency:
        raise ValidationError(
            f"Could not find a package matching the dependency {dependency_string}"
        )

    if (
        dependency.package.owner == self.user
        and dependency.name == self.manifest["name"]
    ):
        raise ValidationError(f"Depending on self is not allowed. {dependency_string}")

    return dependency


def process_manifest(uploader, raw_manifest):
    errors = []
    try:
        manifest = Manifest(json.loads(raw_manifest))
        errors.extend(validate_field_name(manifest))
        errors.extend(validate_field_version_number(manifest))
        errors.extend(validate_field_description(manifest))
        errors.extend(validate_field_website_url(manifest))
        errors.extend(validate_generic(manifest))
        errors.extend(validate_dependencies(manifest))
    except json.decoder.JSONDecodeError:
        errors.append(ValidationError("manifest.json does not appear to be valid JSON"))
    return errors
