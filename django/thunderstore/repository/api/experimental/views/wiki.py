from django.db import transaction
from django.db.models import QuerySet
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response

from thunderstore.repository.models import Package, PackageWiki
from thunderstore.repository.package_reference import PackageReference
from thunderstore.wiki.api.experimental.serializers import (
    WikiPageSerializer,
    WikiPageUpsertSerializer,
    WikiSerializer,
)
from thunderstore.wiki.models import Wiki, WikiPage


class PackageWikiApiView(RetrieveAPIView):
    queryset = Wiki.objects.all().prefetch_related("pages")
    serializer_class = WikiSerializer

    def get_object(self) -> Wiki:
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_package(self) -> Package:
        try:
            reference = PackageReference(
                namespace=self.kwargs["namespace"],
                name=self.kwargs["name"],
            )
        except ValueError as e:
            raise ValidationError(str(e))
        obj = get_object_or_404(
            Package.objects.active(), **reference.get_filter_kwargs()
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def filter_queryset(self, queryset: QuerySet[Wiki]) -> QuerySet[Wiki]:
        return queryset.filter(
            package_wiki__package__name=self.kwargs["name"],
            package_wiki__package__namespace=self.kwargs["namespace"],
        )

    @swagger_auto_schema(
        operation_id="experimental_package_wiki_read",
        operation_summary="Get a list of all wiki pages",
        operation_description=(
            "Returns an index of all the pages included in the wiki"
        ),
        tags=["wiki"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @swagger_auto_schema(
        request_body=WikiPageUpsertSerializer,
        responses={200: WikiPageSerializer()},
        operation_id="experimental_package_wiki_write",
        operation_summary="Create or update a wiki page",
        operation_description=(
            "Creates a new wiki page if a submission is made without the ID "
            "field set. If the ID field is set, the respective page will be "
            "updated instead."
        ),
        tags=["wiki"],
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        package = self.get_package()
        package.ensure_user_can_manage_wiki(request.user)
        request_serializer = WikiPageUpsertSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        wiki = PackageWiki.get_for_package(package, create=True).wiki
        page_data = request_serializer.validated_data
        if "id" in page_data:
            page = get_object_or_404(wiki.pages.all(), pk=page_data["id"])
        else:
            page = WikiPage(wiki=wiki)
        page.markdown_content = page_data["markdown_content"]
        page.title = page_data["title"]
        page.save()
        page.refresh_from_db()
        serializer = WikiPageSerializer(
            instance=page,
        )
        return Response(serializer.data)
