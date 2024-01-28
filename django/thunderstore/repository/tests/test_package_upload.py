import io
import json
from typing import List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.repository.models import Team
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.repository.package_upload import PackageUploadForm


def _build_package(
    files: List[Tuple[str, bytes]],
) -> SimpleUploadedFile:
    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)
    return SimpleUploadedFile("mod.zip", zip_raw.getvalue())


@pytest.mark.django_db
@pytest.mark.parametrize("changelog", (None, "# Test changelog"))
def test_package_upload(
    user, manifest_v1_data, package_icon_bytes: bytes, community, changelog
):
    readme = "# Test readme"
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme.encode("utf-8")),
        ("icon.png", package_icon_bytes),
        ("manifest.json", manifest),
    ]
    if changelog:
        files.append(("CHANGELOG.md", changelog.encode("utf-8")))

    team = Team.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        files={"file": _build_package(files)},
        community=community,
        data={
            "team": team.name,
            "communities": [community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.readme == readme
    assert version.changelog == changelog
    assert version.package.owner == team
    assert version.format_spec == PackageFormats.get_active_format()
    assert version.package.namespace == team.get_namespace()
    assert version.package.namespace.name == team.name
    assert version.file_tree is not None
    assert version.file_tree.entries.count() == 3 if changelog is None else 4
    assert version.installers.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("changelog", (None, "# Test changelog"))
def test_package_upload_with_extra_data(
    user, community, manifest_v1_data, package_icon_bytes: bytes, changelog
):
    readme = "# Test readme"
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme.encode("utf-8")),
        ("icon.png", package_icon_bytes),
        ("manifest.json", manifest),
    ]
    if changelog:
        files.append(("CHANGELOG.md", changelog.encode("utf-8")))

    category = PackageCategory.objects.create(
        name="Test Category",
        slug="test-category",
        community=community,
    )

    team = Team.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        files={"file": _build_package(files)},
        community=community,
        data={
            "categories": [category.pk],
            "has_nsfw_content": True,
            "team": team.name,
            "communities": [community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.readme == readme
    assert version.changelog == changelog
    assert version.package.owner == team
    assert version.format_spec == PackageFormats.get_active_format()
    listing = PackageListing.objects.filter(package=version.package).first()
    assert listing.categories.count() == 1
    assert listing.categories.first() == category
    assert listing.has_nsfw_content is True
    assert version.file_tree is not None
    assert version.file_tree.entries.count() == 3 if changelog is None else 4
    assert version.installers.count() == 0


@pytest.mark.django_db
def test_package_upload_with_installers(
    user, community, manifest_v1_data, package_icon_bytes, package_installer
):
    readme = "# Test readme"
    manifest_v1_data["installers"] = [{"identifier": package_installer.identifier}]
    manifest = json.dumps(manifest_v1_data).encode("utf-8")

    files = [
        ("README.md", readme.encode("utf-8")),
        ("icon.png", package_icon_bytes),
        ("manifest.json", manifest),
    ]

    team = Team.get_or_create_for_user(user)
    form = PackageUploadForm(
        user=user,
        files={"file": _build_package(files)},
        community=community,
        data={
            "team": team.name,
            "communities": [community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.name == manifest_v1_data["name"]
    assert version.readme == readme
    assert version.changelog is None
    assert version.package.owner == team
    assert version.format_spec == PackageFormats.get_active_format()
    assert version.package.namespace == team.get_namespace()
    assert version.package.namespace.name == team.name
    assert version.file_tree is not None
    assert version.file_tree.entries.count() == 3
    assert version.installers.count() == 1
    assert version.installers.first() == package_installer
