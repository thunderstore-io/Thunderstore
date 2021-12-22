from django.urls import path

from thunderstore.security import views

urlpatterns = [
    path("webhooks/github/ss/", views.secret_scanning_endpoint, name="packages.list"),
]
