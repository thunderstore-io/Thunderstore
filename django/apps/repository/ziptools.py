import json
from zipfile import ZipFile, BadZipFile

from django import forms
from django.core.exceptions import ValidationError

from repository.models import PackageVersion

MAX_PACKAGE_SIZE = 1024 * 1024 * 50


class PackageVersionForm(forms.ModelForm):
    class Meta:
        model = PackageVersion
        fields = ["file"]

    def validate_manifest(self, manifest):
        try:
            decoded = json.loads(manifest)
            if "name" not in decoded:
                raise ValidationError("manifest.json must contain a name")
            max_length = PackageVersion._meta.get_field("name").max_length
            if len(decoded["name"]) > max_length:
                raise ValidationError(f"Package name is too long, max: {max_length}")
            # TODO: allowed characters validation a-zA-Z0-9_

            if "version_number" not in decoded:
                raise ValidationError("manifest.json must contain version")
            max_length = PackageVersion._meta.get_field("version_number").max_length
            if len(decoded["version_number"]) > max_length:
                raise ValidationError(f"Package version number is too long, max: {max_length}")
            # TODO: validate version number format

            max_length = PackageVersion._meta.get_field("website_url").max_length
            if len(decoded.get("website_url", "")) > max_length:
                raise ValidationError(f"Package website url is too long, max: {max_length}")
        except json.decoder.JSONDecodeError:
            raise ValidationError("Package manifest.json is in invalid format")

    def validate_icon(self, icon):
        pass
        # TODO: Add icon validation
        # raise ValidationError("Package contains invalid icon.png")

    def clean_file(self):
        file = self.cleaned_data.get("file", None)
        if not file:
            raise ValidationError("Must upload a file")

        if file._size > MAX_PACKAGE_SIZE:
            raise ValidationError(f"Too large package, current maximum is {MAX_PACKAGE_SIZE} bytes")

        try:
            with ZipFile(file) as unzip:

                if unzip.testzip():
                    raise ValidationError("Corrupted zip file")

                try:
                    manifest = unzip.read("manifest.json")
                    self.validate_manifest(manifest)
                except KeyError:
                    raise ValidationError("Package is missing manifest.json")

                try:
                    icon = unzip.read("icon.png")
                    self.validate_icon(icon)
                except KeyError:
                    raise ValidationError("Package is missing icon.png")
        except (BadZipFile, NotImplementedError):
            raise ValidationError("Invalid zip file format")

        return file
