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
from thunderstore.repository.factories import (
    PackageFactory,
    PackageVersionFactory,
    TeamFactory,
)
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
def test_get_package_index_queryset__dependency_names_ordered():
    version = PackageVersionFactory()

    teams = {}
    packages = {}
    for namespace, name, version_number in (
        ("Zeta", "Mod", "1.0.0"),
        ("alpha", "zed", "1.0.0"),
        ("alpha", "Bee", "2.0.0"),
        ("Beta", "mod", "1.0.0"),
        ("alpha", "Bee", "1.0.0"),
    ):
        if namespace not in teams:
            teams[namespace] = TeamFactory(name=namespace)
        if (namespace, name) not in packages:
            packages[(namespace, name)] = PackageFactory(
                owner=teams[namespace],
                namespace=teams[namespace].get_namespace(),
                name=name,
            )
        dependency = PackageVersionFactory(
            package=packages[(namespace, name)],
            name=name,
            version_number=version_number,
        )
        version.dependencies.add(dependency)

    entry = get_package_index_queryset().get(pk=version.pk)

    assert entry._dependency_names == [
        "alpha-Bee-1.0.0",
        "alpha-Bee-2.0.0",
        "alpha-zed-1.0.0",
        "Beta-mod-1.0.0",
        "Zeta-Mod-1.0.0",
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
