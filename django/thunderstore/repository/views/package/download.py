from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from ipware import get_client_ip
from pydantic import BaseModel, ValidationError

from thunderstore.cache.utils import get_cache
from thunderstore.core.utils import replace_cdn
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import PackageVersion

cache = get_cache("downloads")


class DownloadMetaCache(BaseModel):
    id: int
    file: str


def get_download_meta(
    namespace: str, name: str, version_number: str
) -> DownloadMetaCache:
    key = f"{namespace}-{name}-{version_number}"
    if cached_value := cache.get(key):
        try:
            return DownloadMetaCache.parse_obj(cached_value)
        except ValidationError:
            pass

    data = (
        PackageVersion.objects.system()
        .filter(
            package__namespace__name=namespace,
            package__name=name,
            version_number=version_number,
        )
        .values("id", "file")
        .first()
    )
    if not data or not data["file"]:
        raise PackageVersion.DoesNotExist
    meta = DownloadMetaCache(**data)
    cache.set(key, data)
    return meta


class PackageDownloadView(CommunityMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs):
        try:
            meta = get_download_meta(
                namespace=kwargs["owner"],
                name=kwargs["name"],
                version_number=kwargs["version"],
            )
        except PackageVersion.DoesNotExist:
            raise Http404

        client_ip, _ = get_client_ip(self.request)
        PackageVersion.log_download_event(meta.id, client_ip)

        url = PackageVersion._meta.get_field("file").storage.url(meta.file)
        url = self.request.build_absolute_uri(url)
        url = replace_cdn(url, request.GET.get("cdn"))
        return redirect(url)
