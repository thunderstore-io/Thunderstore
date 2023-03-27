from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import RetrieveAPIView

from thunderstore.wiki.api.experimental.serializers import WikiPageSerializer
from thunderstore.wiki.models import WikiPage


class WikiPageApiView(RetrieveAPIView):
    queryset = WikiPage.objects.all()
    serializer_class = WikiPageSerializer

    @swagger_auto_schema(
        operation_id="experimental_wiki_page_read",
        operation_summary="Get a wiki page",
        operation_description="Returns a wiki page object",
        tags=["wiki"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
