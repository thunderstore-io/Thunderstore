from typing import Any

import pytest

from thunderstore.usermedia.exceptions import S3ConfigurationException
from thunderstore.usermedia.s3_client import get_s3_client


@pytest.mark.parametrize("disable_endpoint", (False, True))
@pytest.mark.parametrize("disable_access_key", (False, True))
@pytest.mark.parametrize("disable_secret", (False, True))
def test_get_s3_client_missing_settings(
    disable_endpoint: bool,
    disable_access_key: bool,
    disable_secret: bool,
    settings: Any,
) -> None:
    if disable_endpoint:
        settings.USERMEDIA_S3_ENDPOINT_URL = ""
    if disable_access_key:
        settings.USERMEDIA_S3_ACCESS_KEY_ID = ""
    if disable_secret:
        settings.USERMEDIA_S3_SECRET_ACCESS_KEY = ""
    if any((disable_endpoint, disable_access_key, disable_secret)):
        with pytest.raises(S3ConfigurationException):
            get_s3_client()
    else:
        assert get_s3_client() is not None


@pytest.mark.parametrize("for_signing", (False, True))
def test_get_s3_client(for_signing: bool, settings: Any) -> None:
    signing_url = "http://signingurl.localhost"
    normal_url = "http://normalurl.localhost"
    settings.USERMEDIA_S3_ENDPOINT_URL = normal_url
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = signing_url

    client = get_s3_client(for_signing=for_signing)
    if for_signing:
        assert client.meta.endpoint_url == signing_url
    else:
        assert client.meta.endpoint_url == normal_url
