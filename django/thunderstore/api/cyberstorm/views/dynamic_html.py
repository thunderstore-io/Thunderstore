from django.http import Http404
from django.utils.html import escapejs
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView

from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.frontend.models import DynamicHTML, DynamicPlacement


class CyberstormDynamicHTMLResponseSerializer(serializers.Serializer):
    dynamic_htmls = serializers.ListField(child=serializers.CharField())


class DynamicHTMLAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    """
    Return Cyberstorm dynamic html placement contents as prerendered HTML.
    """

    serializer_class = CyberstormDynamicHTMLResponseSerializer

    def get_object(self):
        if (
            self.kwargs["placement"].startswith("cyberstorm_")
            and self.kwargs["placement"] in DynamicPlacement.options()
        ):
            dynamic_htmls = DynamicHTML.objects.filter(
                placement=self.kwargs["placement"],
                is_active=True,
            ).order_by("ordering")
            if len(dynamic_htmls) != 0:
                return {"dynamic_htmls": [escapejs(dh.content) for dh in dynamic_htmls]}
        raise Http404
