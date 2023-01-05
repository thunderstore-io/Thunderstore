from django.template import Library, TemplateSyntaxError
from django.template.base import Node
from django.template.defaulttags import url
from django.utils.html import conditional_escape

from thunderstore.frontend.url_reverse import get_community_url_reverse_args

register = Library()


class CommunityURLNode(Node):
    def __init__(self, view_name, kwargs):
        self.view_name = view_name
        self.kwargs = kwargs

    def render(self, context):
        from django.urls import reverse

        url = reverse(
            **get_community_url_reverse_args(
                community=context.get("community"),
                viewname=self.view_name.resolve(context),
                kwargs={k: v.resolve(context) for k, v in self.kwargs.items()},
            )
        )
        return conditional_escape(url) if context.autoescape else url


@register.tag
def community_url(parser, token):
    url_node = url(parser, token)
    if url_node.args:
        raise TemplateSyntaxError("Only kwargs are supported by 'community_url'")
    if url_node.asvar:
        raise TemplateSyntaxError("'as' is not supported by 'community_url'")

    return CommunityURLNode(
        view_name=url_node.view_name,
        kwargs=url_node.kwargs,
    )
