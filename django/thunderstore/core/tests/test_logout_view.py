import pytest
from django.conf import settings
from django.urls import reverse

from thunderstore.core.urls import CustomLogoutView


def test_next_page_is_root():
    view = CustomLogoutView()
    assert view.next_page == "/"


def test_success_url_allowed_hosts_matches_settings():
    view = CustomLogoutView()
    expected = set(settings.LOGOUT_ALLOWED_REDIRECT_HOSTS)
    assert view.success_url_allowed_hosts == expected


def test_success_url_allowed_hosts_is_set():
    view = CustomLogoutView()
    assert isinstance(view.success_url_allowed_hosts, set)


@pytest.mark.django_db
def test_logout_redirects_to_root_by_default(client, community_site):
    url = reverse("logout")
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_logout_redirects_to_allowed_host(client, community_site, monkeypatch):
    monkeypatch.setattr(
        CustomLogoutView,
        "success_url_allowed_hosts",
        {"allowed.example.com"},
    )
    url = reverse("logout")
    redirect_url = "https://allowed.example.com/some-path"
    response = client.get(
        f"{url}?next={redirect_url}",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302
    assert response.url == redirect_url


@pytest.mark.django_db
def test_logout_rejects_disallowed_host(client, community_site, monkeypatch):
    monkeypatch.setattr(
        CustomLogoutView,
        "success_url_allowed_hosts",
        {"allowed.example.com"},
    )
    url = reverse("logout")
    response = client.get(
        f"{url}?next=https://evil.example.com/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302
    assert response.url == url


@pytest.mark.django_db
def test_logout_rejects_disallowed_host_follow_redirect(
    client, community_site, monkeypatch
):
    monkeypatch.setattr(
        CustomLogoutView,
        "success_url_allowed_hosts",
        {"allowed.example.com"},
    )
    url = reverse("logout")
    response = client.get(
        f"{url}?next=https://evil.example.com/",
        HTTP_HOST=community_site.site.domain,
        follow=True,
    )
    assert response.status_code == 200
    assert response.request["PATH_INFO"] == "/"
