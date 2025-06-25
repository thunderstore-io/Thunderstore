import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import path
from rest_framework.views import APIView

from thunderstore.core.exceptions import PermissionValidationError


class PermissionValidationErrorPublicView(APIView):
    def get(self, request):
        raise PermissionValidationError(
            "Public PermissionValidationError", is_public=True
        )


class PermissionValidationErrorNonPublicView(APIView):
    def get(self, request):
        raise PermissionValidationError(
            "Non-public PermissionValidationError", is_public=False
        )


class DjangoValidationErrorView(APIView):
    def get(self, request):
        raise DjangoValidationError("DjangoValidationError")


class PermissionErrorView(APIView):
    def get(self, request):
        raise PermissionError("PermissionError")


class UnhandledErrorView(APIView):
    def get(self, request):
        raise RuntimeError("RuntimeError")


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "error/permission-validation-public/",
        PermissionValidationErrorPublicView.as_view(),
    ),
    path(
        "error/permission-validation-nonpublic/",
        PermissionValidationErrorNonPublicView.as_view(),
    ),
    path("error/django-validation/", DjangoValidationErrorView.as_view()),
    path("error/permission/", PermissionErrorView.as_view()),
    path("error/unhandled-runtime/", UnhandledErrorView.as_view()),
]


@pytest.mark.urls("thunderstore.core.tests.test_api_exceptions")
@pytest.mark.django_db
def test_permission_validation_error_public(api_client):
    resp = api_client.get("/error/permission-validation-public/")
    assert resp.status_code == 403
    assert resp.json() == {"non_field_errors": ["Public PermissionValidationError"]}


@pytest.mark.urls("thunderstore.core.tests.test_api_exceptions")
@pytest.mark.django_db
def test_permission_validation_error_nonpublic(api_client):
    resp = api_client.get("/error/permission-validation-nonpublic/")
    assert resp.status_code == 403
    assert resp.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.urls("thunderstore.core.tests.test_api_exceptions")
@pytest.mark.django_db
def test_django_validation_error(api_client):
    resp = api_client.get("/error/django-validation/")
    assert resp.status_code == 400
    assert resp.json() == {"non_field_errors": ["DjangoValidationError"]}


@pytest.mark.urls("thunderstore.core.tests.test_api_exceptions")
@pytest.mark.django_db
def test_permission_error(api_client):
    resp = api_client.get("/error/permission/")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "PermissionError"}


@pytest.mark.urls("thunderstore.core.tests.test_api_exceptions")
@pytest.mark.django_db
def test_unhandled_exception(api_client):
    resp = api_client.get("/error/unhandled-runtime/")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error"}
