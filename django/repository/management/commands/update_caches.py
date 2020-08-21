from django.core.management.base import BaseCommand
from django.test.client import RequestFactory
from django.conf import settings

from repository.api.v1.viewsets import PackageViewSet

from repository.api.experimental.views import PackageListApiView


class Command(BaseCommand):
    help = "Updates repository specific caches"

    def handle(self, *args, **kwargs):
        print("Updating caches")
        self.update_v1()
        self.update_experimental()
        print("Caches updated!")

    def update_v1(self):
        request = RequestFactory().get("/api/v1/package/", SERVER_NAME=settings.SERVER_NAME)
        view = PackageViewSet.as_view({"get": "list"})
        PackageViewSet.update_cache(view, request)

    def update_experimental(self):
        request = RequestFactory().get("/api/experimental/package/", SERVER_NAME=settings.SERVER_NAME)
        view = PackageListApiView.as_view()
        PackageListApiView.update_cache(view, request)
