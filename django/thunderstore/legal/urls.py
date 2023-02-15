from django.urls import path

from thunderstore.legal.views import (
    LegalContractHistoryView,
    LegalContractVersionView,
    LegalContractView,
)

legal_urls = [
    path("c/<str:contract>/", LegalContractView.as_view(), name="contract"),
    path(
        "c/<str:contract>/history/",
        LegalContractHistoryView.as_view(),
        name="contract.history",
    ),
    path(
        "c/<str:contract>/v/<str:version>/",
        LegalContractVersionView.as_view(),
        name="contract.version",
    ),
]
