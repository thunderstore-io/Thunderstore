import json

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.services.package_listing import report_package_listing
from thunderstore.community.api.experimental.serializers import (
    PackageListingReportRequestSerializer,
)
from thunderstore.community.factories import PackageListingFactory
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.ts_reports.admin import PackageReportAdmin
from thunderstore.ts_reports.admin.package_report import set_active, set_inactive
from thunderstore.ts_reports.models import PackageReport


@pytest.mark.django_db
def test_api_package_listing_report_requires_login(
    api_client: APIClient,
):
    listing = PackageListingFactory()
    version = listing.package.latest

    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps(
            {
                "version": version.pk,
                "reason": "Spam",
                "description": "",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.data["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_api_package_listing_report(
    api_client: APIClient,
    user: UserType,
):
    listing = PackageListingFactory()
    version = listing.package.latest

    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps({"version": version.pk, "reason": "Spam", "description": ""}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert PackageReport.objects.count() == 1


@pytest.mark.django_db
def test_api_package_listing_report_denied(
    api_client: APIClient,
    user: UserType,
):
    listing = PackageListingFactory()
    version = listing.package.latest

    api_client.force_authenticate(user)

    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps({"version": -1, "reason": "Spam", "description": ""}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.data["version"][0] == 'Invalid pk "-1" - object does not exist.'

    response = api_client.post(
        f"/api/experimental/package-listing/{-1}/report/",
        json.dumps({"version": version.pk, "reason": "Spam", "description": ""}),
        content_type="application/json",
    )

    assert response.status_code == 404

    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps({"version": version.pk, "reason": "", "description": ""}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.data["reason"][0] == "This field may not be blank."

    assert PackageReport.objects.count() == 0


@pytest.mark.django_db
def test_package_listing_report_serializer():
    listing = PackageListingFactory()
    version = listing.package.latest

    data = {
        "version": version.pk,
        "reason": "Spam",
        "description": "This is spam.",
    }
    serializer = PackageListingReportRequestSerializer(data=data)

    assert serializer.is_valid() is True

    serialized = serializer.data
    assert serialized["version"] == version.pk
    assert serialized["reason"] == "Spam"
    assert serialized["description"] == "This is spam."

    deserialized = serializer.validated_data
    assert deserialized["version"] == version
    assert deserialized["reason"] == "Spam"
    assert deserialized["description"] == "This is spam."


@pytest.mark.django_db
def test_report_package_listing(user: UserType):
    version = PackageVersionFactory()
    package = version.package
    listing = PackageListingFactory(package=package)

    with pytest.raises(PermissionValidationError) as exc:
        report_package_listing(
            agent=None,
            reason="Spam",
            package=package,
            package_listing=listing,
            package_version=version,
            description="",
        )
    assert "Must be authenticated" in str(exc.value)

    report_package_listing(
        agent=user,
        reason="Spam",
        package=package,
        package_listing=listing,
        package_version=version,
        description="This is spam.",
    )

    assert PackageReport.objects.count() == 1
    report = PackageReport.objects.first()
    assert report.submitted_by == user
    assert report.package == package
    assert report.package_listing == listing
    assert report.package_version == version
    assert report.reason == "Spam"
    assert report.description == "This is spam."


@pytest.mark.django_db
def test_handle_user_report():
    version1 = PackageVersionFactory()
    version2 = PackageVersionFactory()
    package1 = version1.package
    package2 = version2.package

    listing1 = PackageListingFactory(package=package1)
    listing2 = PackageListingFactory(package=package2)

    with pytest.raises(ValidationError) as exc:
        PackageReport.handle_user_report(
            reason="Spam",
            submitted_by=None,
            package=package1,
            package_listing=listing2,
            package_version=version1,
            description="",
        )
    assert "Package mismatch!" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        PackageReport.handle_user_report(
            reason="Spam",
            submitted_by=None,
            package=package1,
            package_listing=listing1,
            package_version=version2,
            description="",
        )
    assert "Package mismatch!" in str(exc.value)


@pytest.mark.django_db
def test_package_report_str():
    package_report = PackageReport.objects.create(
        category="UserReport",
        reason="Spam",
        package=PackageFactory(),
    )

    assert package_report.__str__() == "UserReport : Spam"


@pytest.mark.django_db
def test_package_report_active_manager():
    package_report = PackageReport.objects.create(
        category="UserReport",
        reason="Spam",
        package=PackageFactory(),
    )

    assert PackageReport.objects.active().count() == 1

    package_report.is_active = False
    package_report.save()

    assert PackageReport.objects.active().count() == 0


@pytest.mark.django_db
def test_package_report_admin_actions():
    reports = [
        PackageReport.objects.create(
            category="UserReport",
            reason="Spam",
            package=PackageFactory(),
        )
        for i in range(5)
    ]

    modeladmin = PackageReportAdmin(PackageReport, None)

    set_inactive(modeladmin, None, PackageReport.objects.all())

    for entry in reports:
        entry.refresh_from_db()
        assert entry.is_active == False

    set_active(modeladmin, None, PackageReport.objects.all())

    for entry in reports:
        entry.refresh_from_db()
        assert entry.is_active == True


@pytest.mark.django_db
def test_package_report_admin_fields():
    version = PackageVersionFactory()
    package = version.package
    listing = PackageListingFactory(package=package)
    report = PackageReport.objects.create(
        category="UserReport",
        reason="Spam",
        package=package,
        package_listing=listing,
        package_version=version,
    )

    modeladmin = PackageReportAdmin(PackageReport, None)

    assert modeladmin.get_details(report) == "UserReport : Spam"
    assert (
        modeladmin.link_package(report)
        == f'<a href="/djangoadmin/repository/package/{package.pk}/change/">{package.full_package_name}</a>'
    )
    assert (
        modeladmin.link_listing(report)
        == f'<a href="/djangoadmin/community/packagelisting/{listing.pk}/change/">{listing.community.name}</a>'
    )
    assert (
        modeladmin.link_version(report)
        == f'<a href="/djangoadmin/repository/packageversion/{version.pk}/change/">{version.version_number}</a>'
    )


@pytest.mark.django_db
def test_package_report_admin_search(rf):
    version = PackageVersionFactory()
    package = version.package
    listing = PackageListingFactory(package=package)
    report = PackageReport.objects.create(
        category="UserReport",
        reason="Spam",
        package=package,
        package_listing=listing,
        package_version=version,
    )

    modeladmin = PackageReportAdmin(PackageReport, None)

    request = rf.get("/admin/")
    request.user = UserFactory(is_superuser=True)
    queryset = PackageReport.objects.all()

    results, used_custom = modeladmin.get_search_results(
        request, queryset, package.name
    )
    assert report in results
    assert used_custom is False

    results, used_custom = modeladmin.get_search_results(
        request, queryset, package.full_package_name
    )
    assert report in results
    assert used_custom is False

    results, used_custom = modeladmin.get_search_results(
        request, queryset, f"listing:{listing.pk}"
    )
    assert report in results
    assert used_custom is True

    results, used_custom = modeladmin.get_search_results(
        request, queryset, f"package:{package.pk}"
    )
    assert report in results
    assert used_custom is True

    results, used_custom = modeladmin.get_search_results(
        request, queryset, f"version:{version.pk}"
    )
    assert report in results
    assert used_custom is True

    results, used_custom = modeladmin.get_search_results(
        request, queryset, f"listing:-1"
    )
    assert report not in results
    assert used_custom is True
