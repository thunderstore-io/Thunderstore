from abyss.django import AbyssMiddleware
from django.http import HttpRequest
from django.utils import timezone


class TracingMiddleware(AbyssMiddleware):
    STORAGE_CLASS = "thunderstore.abyss.storage.get_abyss_storage"
    FILENAME_PREFIX = "traces/"

    def build_filename_for_request(self, request: HttpRequest) -> str:
        timestamp = timezone.now().isoformat().replace(":", "-")
        path_stamp = request.path.strip("/").replace("/", "-")
        prefix = self.FILENAME_PREFIX or ""
        return f"{prefix}{timestamp}_{path_stamp}.tracing"

    def should_profile_request(self, request: HttpRequest):
        base = super().should_profile_request(request)
        return (
            base
            and hasattr(request, "user")
            and (request.user.is_staff or request.user.is_superuser)
        )
