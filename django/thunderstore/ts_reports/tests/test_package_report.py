import json

import pytest
from rest_framework.test import APIClient

from thunderstore.community.api.experimental.serializers import (
    PackageListingReportRequestSerializer,
)
from thunderstore.community.factories import PackageListingFactory
from thunderstore.core.types import UserType
from thunderstore.ts_reports.models import PackageReport


@pytest.mark.django_db
def test_api_package_listing_report_requires_login(
    api_client: APIClient,
):
    listing = PackageListingFactory()
    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps(
            {
                "package_version_id": listing.package.latest.pk,
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
        json.dumps(
            {"package_version_id": version.pk, "reason": "Spam", "description": ""}
        ),
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
        json.dumps({"package_version_id": -1, "reason": "Spam", "description": ""}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.data["package_version_id"][0] == "Object not found"

    response = api_client.post(
        f"/api/experimental/package-listing/{-1}/report/",
        json.dumps(
            {"package_version_id": version.pk, "reason": "Spam", "description": ""}
        ),
        content_type="application/json",
    )

    assert response.status_code == 404

    response = api_client.post(
        f"/api/experimental/package-listing/{listing.pk}/report/",
        json.dumps({"package_version_id": version.pk, "reason": "", "description": ""}),
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
        "package_version_id": version.pk,
        "reason": "Spam",
        "description": "This is spam.",
    }
    serializer = PackageListingReportRequestSerializer(data=data)

    assert serializer.is_valid() is True

    serialized = serializer.data
    assert serialized["package_version_id"] == str(version.pk)
    assert serialized["reason"] == "Spam"
    assert serialized["description"] == "This is spam."

    deserialized = serializer.validated_data
    assert deserialized["package_version_id"] == version
    assert deserialized["reason"] == "Spam"
    assert deserialized["description"] == "This is spam."
