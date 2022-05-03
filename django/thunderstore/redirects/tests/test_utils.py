import re

import pytest
from django.http import HttpRequest
from django.test import override_settings

from thunderstore.redirects.utils import LegacyUrlHandler, solve_community_identifier


@pytest.mark.django_db
@pytest.mark.parametrize(
    "host_string",
    (
        ("riskofrain2", "thunderstore.temp"),
        ("riskofrain2", "bad.host.thunderstore.temp"),
        ("riskofrain2", "double.bad.host.thunderstore.temp"),
        ("dsp", "dsp.thunderstore.temp"),
    ),
)
@override_settings(
    ALLOWED_HOSTS=[
        "thunderstore.temp",
        "dsp.thunderstore.temp",
        "bad.host.thunderstore.temp",
        "double.bad.host.thunderstore.temp",
    ]
)
def test_solve_community_identifier(host_string: tuple) -> None:
    r = HttpRequest()
    r.META["HTTP_HOST"] = host_string[1]
    assert solve_community_identifier(r) == host_string[0]


@pytest.mark.django_db
def test_legacy_url_handler() -> None:
    handler = LegacyUrlHandler(HttpRequest())
    result = re.search(
        "/([^/]*?)/([^/]*?)/([^/]*?)/$", "/test_owner/test_name/test_version/"
    )
    handler.get_reverse_data_packages_list_by_dependency(result)
    assert handler.reverse_kwargs["owner"] == "test_owner"
    assert handler.reverse_kwargs["name"] == "test_name"
    handler.reverse_kwargs = {}
    handler.get_reverse_data_packages_version_detail(result)
    assert handler.reverse_kwargs["owner"] == "test_owner"
    assert handler.reverse_kwargs["name"] == "test_name"
    assert handler.reverse_kwargs["version"] == "test_version"
    handler.reverse_kwargs = {}
    handler.get_reverse_data_packages_detail(result)
    assert handler.reverse_kwargs["owner"] == "test_owner"
    assert handler.reverse_kwargs["name"] == "test_name"
    handler.reverse_kwargs = {}
    handler.get_reverse_data_packages_list_by_owner(result)
    assert handler.reverse_kwargs["owner"] == "test_owner"
