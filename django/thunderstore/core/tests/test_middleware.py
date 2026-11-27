import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.middleware.common import CommonMiddleware
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient
from whitenoise.middleware import WhiteNoiseFileResponse

from thunderstore.core.middleware import ContentLengthMiddleware


def _process(response):
    middleware = ContentLengthMiddleware(lambda request: response)
    return middleware(RequestFactory().get("/"))


def test_content_length_middleware_sets_missing_header():
    response = _process(HttpResponse("abc"))
    assert response["Content-Length"] == "3"


def test_content_length_middleware_keeps_existing_header():
    response = _process(HttpResponse("abc", headers={"Content-Length": "1"}))
    assert response["Content-Length"] == "1"


def test_content_length_middleware_skips_streaming_response():
    response = _process(StreamingHttpResponse(iter([b"abc"])))
    assert not response.has_header("Content-Length")


def test_content_length_middleware_skips_static_file_not_modified():
    # The response WhiteNoise gives to a conditional request for a static file.
    response = _process(WhiteNoiseFileResponse((), status=304))
    assert not response.has_header("Content-Length")


@pytest.mark.parametrize("status", (204, 304))
def test_content_length_middleware_matches_django_for_bodyless_statuses(status: int):
    # Django's CommonMiddleware sets the header on these too. Stay consistent
    # with it, so the header doesn't depend on which middleware saw the response.
    common_middleware = CommonMiddleware(lambda request: HttpResponse(status=status))
    expected = common_middleware(RequestFactory().get("/"))["Content-Length"]
    assert expected == "0"
    assert _process(HttpResponse(status=status))["Content-Length"] == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    (
        "/api/cyberstorm/community",
        "/api/experimental/current-user",
        "/api/v1/package",
    ),
)
def test_append_slash_redirect_has_content_length(api_client: APIClient, path: str):
    response = api_client.get(path)
    assert response.status_code == 301
    assert response["Location"] == f"{path}/"
    assert response["Content-Length"] == "0"


@pytest.mark.django_db
def test_ssl_redirect_has_content_length(api_client: APIClient, settings):
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_REDIRECT_EXEMPT = []
    response = api_client.get("/api/cyberstorm/community/")
    assert response.status_code == 301
    assert response["Location"].startswith("https://")
    assert response["Content-Length"] == "0"


@pytest.mark.django_db
def test_disallowed_host_response_has_content_length():
    response = APIClient(HTTP_HOST="disallowed.test").get("/api/v1/package/")
    assert response.status_code == 400
    assert len(response.content) > 0
    assert response["Content-Length"] == str(len(response.content))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "status"),
    (
        ("/api/cyberstorm/community/", 200),
        ("/api/cyberstorm/does-not-exist/", 404),
    ),
)
def test_content_length_matches_body(api_client: APIClient, path: str, status: int):
    response = api_client.get(path)
    assert response.status_code == status
    assert len(response.content) > 0
    assert response["Content-Length"] == str(len(response.content))


@pytest.mark.django_db
def test_no_content_response_is_unchanged(api_client: APIClient, user):
    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("api:experimental:auth.delete"))
    assert response.status_code == 204
    assert response.content == b""
    assert response["Content-Length"] == "0"
