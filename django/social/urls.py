from django.urls import path

from .views import LinkedAccountsView

settings_urls = [
    path('linked-accounts/', LinkedAccountsView.as_view(), name="settings.linked-accounts")
]
