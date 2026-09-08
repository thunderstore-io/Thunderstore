import json

import pytest
import requests
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from thunderstore.repository.api.experimental.views.package_index import (
    PackageIndexEntry,
    get_package_index_queryset,
    update_api_experimental_package_index,
)
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion


@pytest.mark.django_db
def test_api_experimental_package_index(api_client: APIClient):
    packages = [PackageVersionFactory() for _ in range(10)]
    for i, version in enumerate(packages):
        version.dependencies.set(packages[:i])
    response = api_client.get("/api/experimental/package-index/")
    assert response.status_code == 503

    update_api_experimental_package_index()
    response = api_client.get("/api/experimental/package-index/")
    assert response.status_code == 302

    response = requests.get(response["Location"])
    assert response.status_code == 200

    results = [json.loads(x) for x in response.content.decode().split("\n") if x]

    queryset = get_package_index_queryset().filter(pk__in=[x.pk for x in packages])
    expected = [PackageIndexEntry(instance=x).data for x in queryset]
    assert len(results) == len(expected)
    for entry in expected:
        assert entry in results

    last = packages[-1]
    entry = next(
        x
        for x in results
        if x["name"] == last.name and x["version_number"] == last.version_number
    )
    assert entry["dependencies"] == [
        x.full_version_name
        for x in sorted(
            packages[:-1],
            key=lambda v: (v.package.namespace.name.lower(), v.package.name.lower()),
        )
    ]


@pytest.mark.django_db
def test_update_api_experimental_package_index_query_count():
    versions = [PackageVersionFactory() for _ in range(10)]
    for i, version in enumerate(versions):
        version.dependencies.set(versions[:i])
    assert PackageVersion.objects.count() == 10
    with CaptureQueriesContext(connection) as context:
        update_api_experimental_package_index()
    assert len(context) < 8
