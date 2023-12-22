from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404

from thunderstore.community.api.experimental.views._utils import (
    CustomCursorPagination,
    CustomListAPIView,
)
from thunderstore.community.models import Community
from thunderstore.frontend.api.experimental.serializers.views import (
    PackageCategorySerializer,
)


class PackageCategoriesExperimentalApiView(CustomListAPIView):
    pagination_class = CustomCursorPagination
    serializer_class = PackageCategorySerializer

    def get_queryset(self):
        community_identifier = self.kwargs.get("community")
        community = get_object_or_404(Community, identifier=community_identifier)
        return community.package_categories

    @swagger_auto_schema(tags=["experimental"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
