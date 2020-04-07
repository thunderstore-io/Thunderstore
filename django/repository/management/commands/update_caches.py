from django.core.management.base import BaseCommand
from django.test.client import RequestFactory

from repository.api.v1.viewsets import PackageViewSet


class Command(BaseCommand):
    help = "Updates repository specific caches"

    def handle(self, *args, **kwargs):
        print("Updating caches")
        request = RequestFactory().get("/api/v1/package/")
        view = PackageViewSet.as_view({"get": "list"})
        PackageViewSet.update_cache(view, request)
        print("Caches updated!")
