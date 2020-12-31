import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.repository.models import (
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.package_upload import PackageUploadForm


@pytest.mark.django_db
def test_package_upload(user, manifest_v1_data, icon_raw, community):
    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    identity = UploaderIdentity.get_or_create_for_user(
        manifest_v1_data["author_name"], user
    )
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.package.owner == identity


@pytest.mark.django_db
def test_package_upload_missing_privileges(user, manifest_v1_data, icon_raw, community):
    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    UploaderIdentity.get_or_create_for_user(
        manifest_v1_data["author_name"], UserFactory.create()
    )
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
    )
    assert form.is_valid() is False
    assert len(form.errors["file"]) == 1
    assert form.errors["file"][0] == "Not a member of the team"


@pytest.mark.django_db
def test_package_upload_version_already_exists(
    user, manifest_v1_data, icon_raw, community, package_version
):
    readme = "# Test readme".encode("utf-8")

    UploaderIdentityMember.objects.create(
        user=user,
        identity=package_version.owner,
        role=UploaderIdentityMemberRole.owner,
    )
    manifest_v1_data["name"] = package_version.name
    manifest_v1_data["author_name"] = package_version.owner.name
    manifest_v1_data["version_number"] = package_version.version_number

    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
    )
    assert form.is_valid() is False
    assert len(form.errors["file"]) == 1
    assert (
        form.errors["file"][0] == "Package of the same name and version already exists"
    )


@pytest.mark.django_db
def test_package_upload_with_extra_data(user, community, manifest_v1_data, icon_raw):
    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    category = PackageCategory.objects.create(
        name="Test Category",
        slug="test-category",
        community=community,
    )

    file_data = {"file": SimpleUploadedFile("mod.zip", zip_raw.getvalue())}
    identity = UploaderIdentity.get_or_create_for_user(
        manifest_v1_data["author_name"], user
    )
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community,
        data={
            "categories": [category.pk],
            "has_nsfw_content": True,
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.package.owner == identity
    listing = PackageListing.objects.filter(package=version.package).first()
    assert listing.categories.count() == 1
    assert listing.categories.first() == category
    assert listing.has_nsfw_content is True
