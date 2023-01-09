import io
import json

import pytest
import requests
from django.core.files import File
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.modpacks.models import LegacyProfile
from thunderstore.modpacks.models.legacyprofile import LEGACYPROFILE_STORAGE_CAP


@pytest.mark.django_db
def test_experimental_api_legacyprofile_create(api_client: APIClient) -> None:
    assert LegacyProfile.objects.count() == 0
    test_content = b"hunter2"
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        data=test_content,
        content_type="application/octet-stream",
    )
    assert response.status_code == 200
    result = json.loads(response.content.decode())
    assert "key" in result
    assert LegacyProfile.objects.count() == 1
    obj = LegacyProfile.objects.get(id=result["key"])
    assert obj.file.read() == test_content


@pytest.mark.django_db
def test_experimental_api_legacyprofile_deduplicate(api_client: APIClient) -> None:
    assert LegacyProfile.objects.count() == 0
    test_content = b"hunter2"
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        data=test_content,
        content_type="application/octet-stream",
    )
    assert LegacyProfile.objects.count() == 1
    first_key = response.json()["key"]
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        data=test_content,
        content_type="application/octet-stream",
    )
    assert LegacyProfile.objects.count() == 1
    assert response.json()["key"] == first_key
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        data=b"hunter3",
        content_type="application/octet-stream",
    )
    assert LegacyProfile.objects.count() == 2
    assert response.json()["key"] != first_key


@pytest.mark.django_db
def test_experimental_api_legacyprofile_create_without_body(
    api_client: APIClient,
) -> None:
    assert LegacyProfile.objects.count() == 0
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        content_type="application/octet-stream",
    )
    assert response.status_code == 400
    assert b"Request body was empty" in response.content
    assert LegacyProfile.objects.count() == 0


@pytest.mark.django_db
def test_experimental_api_legacyprofile_create_without_space(
    api_client: APIClient,
) -> None:
    test_content = b"hello world"
    test_file = File(io.BytesIO(test_content), name="test.txt")
    LegacyProfile.objects.create(file=test_file, file_size=LEGACYPROFILE_STORAGE_CAP)
    assert LegacyProfile.objects.count() == 1
    response = api_client.post(
        reverse("api:experimental:legacyprofile.create"),
        data=test_content,
        content_type="application/octet-stream",
    )
    assert response.status_code == 400
    assert (
        b"The server has reached maximum total storage used, and can't receive new uploads"
        in response.content
    )
    assert LegacyProfile.objects.count() == 1


@pytest.mark.django_db
def test_experimental_api_legacyprofile_retrieve(api_client: APIClient) -> None:
    test_content = b"hello world"
    test_file = File(io.BytesIO(test_content), name="test.txt")
    profile = LegacyProfile.objects.create(file=test_file, file_size=test_file.size)
    response = api_client.get(
        reverse(
            "api:experimental:legacyprofile.retrieve",
            kwargs={
                "key": profile.id,
            },
        ),
    )
    assert response.status_code == 302
    response = requests.get(response["Location"])
    assert response.status_code == 200
    assert response.content == test_content
