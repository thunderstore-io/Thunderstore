from django.urls import path

from thunderstore.github.views import SecretScanningEndpoint

github_urls = [
    path(
        "secret-scanning/validate/",
        SecretScanningEndpoint.as_view(),
        name="secret-scanning.validate",
    ),
]
