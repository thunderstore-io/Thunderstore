import json

import pytest
import requests
from django.db import connection
from django.db.models import F
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from thunderstore.repository.api.experimental.views.package_index import (
    PackageIndexEntry,
    _build_dependency_maps,
    serialize_package_index,
    update_api_experimental_package_index,
)
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion


@pytest.mark.django_db
def test_api_experimental_package_index(api_client: APIClient):
    packages = [PackageVersionFactory() for _ in range(10)]
    response = api_client.get("/api/experimental/package-index/")
    assert response.status_code == 503

    update_api_experimental_package_index()
    response = api_client.get("/api/experimental/package-index/")
    assert response.status_code == 302

    response = requests.get(response["Location"])
    assert response.status_code == 200

    results = [json.loads(x) for x in response.content.decode().split("\n") if x]

    queryset = PackageVersion.objects.filter(pk__in=[x.pk for x in packages]).annotate(
        namespace=F("package__namespace")
    )
    dependency_names, dependency_ids = _build_dependency_maps()
    context = {"dependency_names": dependency_names, "dependency_ids": dependency_ids}
    expected = [PackageIndexEntry(instance=x, context=context).data for x in queryset]
    assert len(results) == len(expected)
    for entry in expected:
        assert entry in results


@pytest.mark.django_db
def test_update_api_experimental_package_index_query_count():
    [PackageVersionFactory() for _ in range(10)]
    assert PackageVersion.objects.count() == 10
    with CaptureQueriesContext(connection) as context:
        update_api_experimental_package_index()
    assert len(context) < 8


@pytest.mark.django_db
def test_serialize_package_index_resolves_dependencies():
    dependant = PackageVersionFactory()
    dependency = PackageVersionFactory()
    dependant.dependencies.add(dependency)

    content = serialize_package_index().decode()
    entries = [json.loads(line) for line in content.split("\n") if line]
    entry = next(e for e in entries if e["name"] == dependant.name)
    assert entry["dependencies"] == [dependency.full_version_name]
