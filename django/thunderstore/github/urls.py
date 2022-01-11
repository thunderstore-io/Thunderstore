from django.urls import path

from thunderstore.special.views import SecretScanningEndpoint

special_urls = [
    path(
        "secret-scanning/validate/",
        SecretScanningEndpoint.as_view(),
        name="secret-scanning.validate",
    ),
]
