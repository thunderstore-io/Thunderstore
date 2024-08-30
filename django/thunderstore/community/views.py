from django.conf import settings
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView

from thunderstore.community.models import Community


class FaviconView(View):
    def get(self, *args, **kwargs):
        return redirect(f"{settings.STATIC_URL}favicon.ico")


class CommunityListView(ListView):
    model = Community

    def get_queryset(self) -> QuerySet[Community]:
        return Community.objects.listed().order_by(
            "-aggregated_fields__package_count", "-datetime_created"
        )
