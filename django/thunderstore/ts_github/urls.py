from django.urls import path

from thunderstore.ts_github.views import SecretScanningEndpoint

system_urls = [
    path(
        "secret-scanning/validate/",
        SecretScanningEndpoint.as_view(),
        name="secret-scanning.validate",
    ),
]
