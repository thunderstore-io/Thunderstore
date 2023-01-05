import copy

from django.template import Library, TemplateSyntaxError
from django.template.base import FilterExpression
from django.template.defaulttags import URLNode, url

register = Library()


def should_use_old_urls(context):
    return "community" not in context or context["community"].main_site


class CommunityUrlNameResolver:
    def __init__(self, view_name: FilterExpression):
        self.view_name = view_name

    def resolve(self, context, ignore_failures=False):
        prefix = (
            "old_urls:" if should_use_old_urls(context) else "communities:community:"
        )
        return f"{prefix}{self.view_name.resolve(context, ignore_failures)}"


class CommunityIdentifierNode:
    def resolve(self, context):
        return context["community"].identifier


class CommunityURLNode(URLNode):
    def render(self, context):
        if not should_use_old_urls(context):
            # Django template caching will result in unintended side effects
            # if we don't copy the instance before modifying it
            kwargs = copy.deepcopy(self.kwargs)
            # noinspection PyTypeChecker
            kwargs.setdefault("community_identifier", CommunityIdentifierNode())
            node = URLNode(self.view_name, self.args, kwargs, self.asvar)
            return node.render(context)
        return super().render(context)


@register.tag
def community_url(parser, token):
    url_node = url(parser, token)
    if url_node.args:
        raise TemplateSyntaxError("Only kwargs are supported by 'community_url'")

    # noinspection PyTypeChecker
    return CommunityURLNode(
        CommunityUrlNameResolver(url_node.view_name),
        [],
        url_node.kwargs,
        url_node.asvar,
    )
