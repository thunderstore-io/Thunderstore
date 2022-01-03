from django.urls import path

from thunderstore.special import views

special_urls = [
    path(
        "secret-scanning/validate/",
        views.secret_scanning_endpoint,
        name="secret-scanning.validate",
    ),
]
