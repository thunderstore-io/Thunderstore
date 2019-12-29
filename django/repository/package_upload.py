import json
import io
from typing import Union

from PIL import Image
from zipfile import ZipFile, BadZipFile

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from repository.models import PackageVersion, Package, UploaderIdentity
from repository.package_manifest import ManifestV1Serializer

MAX_PACKAGE_SIZE = 1024 * 1024 * 500
MAX_ICON_SIZE = 1024 * 1024 * 6
MAX_TOTAL_SIZE = 1024 * 1024 * 1024 * 500


class PackageUploadForm(forms.ModelForm):
    class Meta:
        model = PackageVersion
        fields = ["file"]

    def __init__(self, user, identity, *args, **kwargs):
        super(PackageUploadForm, self).__init__(*args, **kwargs)
        self.user: User = user
        self.identity: UploaderIdentity = identity
        self.manifest: Union[dict, None] = None
        self.icon: Union[ContentFile, None] = None
        self.readme: Union[str, None] = None

    def validate_manifest(self, manifest_str):
        try:
            manifest_data = json.loads(manifest_str)
        except json.decoder.JSONDecodeError as exc:
            raise ValidationError(f"Unable to parse manifest.json: {exc}")

        serializer = ManifestV1Serializer(
            user=self.user,
            uploader=self.identity,
            data=manifest_data,
        )
        serializer.is_valid(raise_exception=True)
        self.manifest = serializer.validated_data

    def validate_icon(self, icon):
        try:
            self.icon = ContentFile(icon)
        except Exception:
            raise ValidationError("Unknown error while processing icon.png")

        if self.icon.size > MAX_ICON_SIZE:
            raise ValidationError(f"icon.png filesize is too big, current maximum is {MAX_ICON_SIZE} bytes")

        try:
            image = Image.open(io.BytesIO(icon))
        except Exception:
            raise ValidationError("Unsupported or corrupt icon, must be png")

        if image.format != "PNG":
            raise ValidationError("Icon must be in png format")

        if not (image.size[0] == 256 and image.size[1] == 256):
            raise ValidationError("Invalid icon dimensions, must be 256x256")

    def validate_readme(self, readme):
        readme = readme.decode("utf-8")
        max_length = 32768
        if len(readme) > max_length:
            raise ValidationError(f"README.md is too long, max: {max_length}")
        self.readme = readme

    def clean_file(self):
        file = self.cleaned_data.get("file", None)
        if not file:
            raise ValidationError("Must upload a file")

        if file.size > MAX_PACKAGE_SIZE:
            raise ValidationError(f"Too large package, current maximum is {MAX_PACKAGE_SIZE} bytes")

        current_total = 0
        for version in PackageVersion.objects.all():
            current_total += version.file.size
        if file.size + current_total > MAX_TOTAL_SIZE:
            raise ValidationError(f"The server has reached maximum total storage used, and can't receive new uploads")

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

                try:
                    readme = unzip.read("README.md")
                    self.validate_readme(readme)
                except KeyError:
                    raise ValidationError("Package is missing README.md")

        except (BadZipFile, NotImplementedError):
            raise ValidationError("Invalid zip file format")

        return file

    def save(self, *args, **kwargs):
        self.instance.name = self.manifest["name"]
        self.instance.version_number = self.manifest["version_number"]
        self.instance.website_url = self.manifest["website_url"]
        self.instance.description = self.manifest["description"]
        self.instance.readme = self.readme
        self.instance.package = Package.objects.get_or_create(
            owner=self.identity,
            name=self.instance.name,
        )[0]
        self.instance.icon.save("icon.png", self.icon)
        instance = super(PackageUploadForm, self).save()
        for reference in self.manifest["dependencies"]:
            instance.dependencies.add(reference.instance)
        return instance
