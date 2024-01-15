from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from ipware import get_client_ip

from thunderstore.core.utils import replace_cdn
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import PackageVersion


class PackageDownloadView(CommunityMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs):
        obj = get_object_or_404(
            PackageVersion,
            package__owner__name=kwargs["owner"],
            package__name=kwargs["name"],
            version_number=kwargs["version"],
        )
        client_ip, _ = get_client_ip(self.request)
        PackageVersion.log_download_event(obj.id, client_ip)

        url = self.request.build_absolute_uri(obj.file.url)
        url = replace_cdn(url, request.GET.get("cdn"))
        return redirect(url)
