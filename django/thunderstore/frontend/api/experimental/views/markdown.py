from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.frontend.api.experimental.serializers.markdown import (
    RenderMarkdownParamsSerializer,
    RenderMarkdownResponseSerializer,
)
from thunderstore.markdown.templatetags.markdownify import render_markdown
from thunderstore.repository.package_upload import MAX_README_SIZE


class RenderMarkdownApiView(APIView):
    serializer_class = RenderMarkdownResponseSerializer
    permission_classes = []

    @swagger_auto_schema(
        request_body=RenderMarkdownParamsSerializer,
        responses={200: RenderMarkdownResponseSerializer()},
        operation_id="experimental.frontend.render-markdown",
    )
    def post(self, request, *args, **kwargs):
        validator = RenderMarkdownParamsSerializer(data=request.data)
        validator.is_valid(raise_exception=True)

        markdown = validator.validated_data["markdown"]
        if len(markdown) > MAX_README_SIZE:
            raise ValidationError("Max markdown size exceeded")

        rendered = render_markdown(markdown)

        serializer = RenderMarkdownResponseSerializer(
            {
                "html": rendered,
            },
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
