import pytest

from repository.models import Package, UploaderIdentity


@pytest.fixture()
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )


@pytest.fixture()
def uploader_identity():
    return UploaderIdentity.objects.create(
        name="Test Identity"
    )


@pytest.fixture()
def package(uploader_identity):
    return Package.objects.create(
        owner=uploader_identity,
        name="Test Package",
    )
